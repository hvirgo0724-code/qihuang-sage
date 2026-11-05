"""PostgreSQL memory; every operation is scoped by authenticated tenant/user."""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from functools import lru_cache
import hashlib
import json
from app.core.security import encrypt_plaintext, decrypt_plaintext

from sqlalchemy import create_engine, text
from app.core.config import settings


@lru_cache
def memory_engine():
    return create_engine(settings.postgres_dsn, pool_pre_ping=True, pool_size=5,
                         max_overflow=5, pool_timeout=5,
                         connect_args={"connect_timeout": 5, "options": "-c statement_timeout=5000"})


class SessionBusy(Exception):
    pass


@contextmanager
def session_lock(tenant_id, user_id, session_id):
    key = int.from_bytes(hashlib.sha256(f"{tenant_id}:{user_id}:{session_id}".encode()).digest()[:8],
                         "big", signed=True)
    # Transaction-scoped lock is automatically released on disconnect/rollback.
    with memory_engine().begin() as conn:
        if not conn.scalar(text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": key}):
            raise SessionBusy("session already has an active turn")
        yield


class MemoryStore:
    def __init__(self, tenant_id: int, user_id: int):
        self.scope = {"tenant": tenant_id, "user": user_id}

    def read(self, kind: str, namespace: str) -> list[dict]:
        with memory_engine().connect() as conn:
            rows = conn.execute(text("""
                SELECT memory_key, value, expires_at FROM agent_memory
                WHERE tenant_id=:tenant AND user_id=:user AND kind=:kind
                  AND namespace=:namespace AND expires_at > CURRENT_TIMESTAMP
                ORDER BY updated_at DESC LIMIT :limit
            """), {**self.scope, "kind": kind, "namespace": namespace,
                    "limit": settings.memory_max_items}).mappings()
            result = []
            for row in rows:
                item = dict(row)
                decrypted = decrypt_plaintext(item["value"]["ciphertext"])
                if decrypted is None:
                    raise ValueError("memory decryption failed")
                item["value"] = json.loads(decrypted)
                item["expires_at"] = item["expires_at"].isoformat()
                result.append(item)
            return result

    def write(self, kind: str, namespace: str, key: str, value: dict):
        payload = json.dumps(value, ensure_ascii=False)
        if len(payload.encode()) > 32768:
            raise ValueError("memory payload exceeds 32 KiB")
        payload = json.dumps({"ciphertext": encrypt_plaintext(payload)})
        ttl = (timedelta(hours=settings.memory_short_ttl_hours) if kind == "short"
               else timedelta(days=settings.memory_long_ttl_days))
        with memory_engine().begin() as conn:
            # Serialize writes per owner to enforce the long-memory quota.
            conn.execute(text("SELECT pg_advisory_xact_lock(:key)"),
                         {"key": int.from_bytes(hashlib.sha256(str(self.scope).encode()).digest()[:8], "big", signed=True)})
            if kind == "long":
                count = conn.scalar(text("""SELECT count(*) FROM agent_memory
                    WHERE tenant_id=:tenant AND user_id=:user AND kind='long'
                    AND expires_at>CURRENT_TIMESTAMP AND memory_key<>:key"""), {**self.scope, "key": key})
                if count >= settings.memory_max_items:
                    raise ValueError("long memory quota exceeded")
            conn.execute(text("""
                INSERT INTO agent_memory(tenant_id,user_id,kind,namespace,memory_key,value,expires_at)
                VALUES (:tenant,:user,:kind,:namespace,:key,CAST(:value AS jsonb),:expires)
                ON CONFLICT (tenant_id,user_id,kind,namespace,memory_key)
                DO UPDATE SET value=EXCLUDED.value, expires_at=EXCLUDED.expires_at,
                              updated_at=CURRENT_TIMESTAMP
            """), {**self.scope, "kind": kind, "namespace": namespace, "key": key,
                    "value": payload, "expires": datetime.now(timezone.utc) + ttl})

    def forget(self, key: str):
        with memory_engine().begin() as conn:
            conn.execute(text("""DELETE FROM agent_memory WHERE tenant_id=:tenant
                AND user_id=:user AND kind='long' AND memory_key=:key"""), {**self.scope, "key": key})
