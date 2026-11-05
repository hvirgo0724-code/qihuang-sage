"""安全原语：bcrypt 口令散列、JWT 签发/校验、字段级 AES-256-GCM 加解密。"""
import base64
import os
import time
from typing import Any, Optional

import bcrypt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from jose import JWTError, jwt

from app.core.config import settings

_ENC_PREFIX = "encv1:"
# AES-GCM 与 JWT 共用的基础随机密钥派生
_aes_key: Optional[bytes] = None


def _get_aes_key() -> bytes:
    global _aes_key
    if _aes_key is None:
        raw = settings.encryption_key.encode("utf-8")
        # 允许直接用 base64 提供 32 字节密钥，否则以 sha256 派生 32 字节
        try:
            decoded = base64.b64decode(raw, validate=True)
            if len(decoded) >= 32:
                _aes_key = decoded[:32]
            else:
                raise ValueError
        except Exception:
            import hashlib

            _aes_key = hashlib.sha256(raw).digest()
    return _aes_key


# ---------------- 口令散列 ----------------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


# ---------------- JWT ----------------
def create_access_token(subject: str, extra: Optional[dict] = None) -> str:
    now = int(time.time())
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": now + settings.jwt_access_token_expire_minutes * 60,
        "type": "access",
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: str) -> str:
    now = int(time.time())
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + settings.jwt_refresh_token_expire_days * 86400,
        "type": "refresh",
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None


# ---------------- 字段级加密 AES-256-GCM ----------------
def encrypt_plaintext(value: str) -> str:
    if not value:
        return value
    nonce = os.urandom(12)
    ciphertext = AESGCM(_get_aes_key()).encrypt(nonce, value.encode("utf-8"), None)
    return _ENC_PREFIX + base64.b64encode(nonce + ciphertext).decode("utf-8")


def decrypt_plaintext(value: Optional[str]) -> Optional[str]:
    if not value:
        return value
    if not value.startswith(_ENC_PREFIX):
        return value
    try:
        raw = base64.b64decode(value[len(_ENC_PREFIX):])
        nonce, ciphertext = raw[:12], raw[12:]
        return AESGCM(_get_aes_key()).decrypt(nonce, ciphertext, None).decode("utf-8")
    except Exception:
        return None


def encrypt_dict_fields(data: dict, fields: list[str]) -> dict:
    """就地加密指定字段（仅用于落库前的健康数据）。"""
    out = dict(data)
    for f in fields:
        if f in out and out[f] is not None:
            out[f] = encrypt_plaintext(str(out[f]))
    return out


# ---------------- 脱敏 ----------------
def mask_text(value: str) -> str:
    """审计日志脱敏：仅保留首尾，中间打码。"""
    if not value:
        return value
    if len(value) <= 4:
        return "*" * len(value)
    return value[:2] + "*" * (len(value) - 4) + value[-2:]