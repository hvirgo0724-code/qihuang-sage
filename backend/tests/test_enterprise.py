import asyncio
import os
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.core.agents import AgentRuntime, AGENT_TOOLS
from app.core.config import settings
from app.core.logging import trace_id_var
from app.core.middleware import RequestTelemetry
from app.core.metrics import REQUEST_COUNT


class AgentTests(unittest.TestCase):
    def test_w3c_trace_id_and_logging_fields(self):
        import io
        import json
        import logging
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor
        from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
        from app.core.logging import setup_logging
        provider, exporter = TracerProvider(), InMemorySpanExporter()
        provider.add_span_processor(SimpleSpanProcessor(exporter))
        app = FastAPI()
        app.add_middleware(RequestTelemetry)
        @app.get("/trace-test/{item}")
        def endpoint(item: int):
            return {"ok": True}
        FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
        setup_logging()
        output = io.StringIO()
        handler = logging.getLogger().handlers[0]
        previous = handler.setStream(output)
        try:
            tid = "1234567890abcdef1234567890abcdef"
            response = TestClient(app).get("/trace-test/7", headers={
                "traceparent": f"00-{tid}-1234567890abcdef-01"})
            self.assertEqual(response.headers["x-trace-id"], tid)
            records = [json.loads(line) for line in output.getvalue().splitlines()]
            record = next(x for x in records if x.get("event") == "request_completed")
            self.assertEqual(record["trace_id"], tid)
            self.assertEqual(record["route"], "/trace-test/{item}")
            self.assertEqual(record["status"], 200)
            self.assertTrue(exporter.get_finished_spans())
        finally:
            handler.setStream(previous)
            provider.shutdown()

    def test_application_routes(self):
        from fastapi.testclient import TestClient
        from app.main import app
        # No lifespan: these public/auth checks must not require MySQL.
        client = TestClient(app)
        self.assertEqual(client.get("/healthz").status_code, 200)
        self.assertEqual(client.get("/api/v1/memory").status_code, 401)
        self.assertEqual(client.get("/metrics").status_code, 200)

    def test_roles_and_permissions(self):
        self.assertEqual([len(x) for x in AGENT_TOOLS.values()], [4, 3, 1])
        with self.assertRaises(ValueError):
            AgentRuntime().bind("care", execute_sql=lambda: None)
        with self.assertRaises(PermissionError):
            AgentRuntime().call("inquiry", "ask")

    def test_budget_is_enforced_even_after_errors(self):
        runtime = AgentRuntime().bind("care", recommend=lambda: 42)
        # 预算按 agent 独立计：把 care 执行器的预算压到 1，耗尽抛 RuntimeError。
        with patch.object(runtime._executors["care"], "budget", 1):
            self.assertEqual(runtime.call("care", "recommend"), 42)
            with self.assertRaises(RuntimeError):
                runtime.call("care", "recommend")

    def test_langsmith_disabled(self):
        from app.core.langsmith import llm_trace
        with patch.object(settings, "langsmith_tracing", False):
            with patch("app.core.langsmith.client") as client:
                with llm_trace("test"):
                    pass
                client.assert_not_called()


class TelemetryTests(unittest.IsolatedAsyncioTestCase):
    async def test_stream_and_context_cleanup(self):
        messages = []
        async def send(msg):
            messages.append(msg)
        async def app(scope, receive, send):
            scope["route"] = SimpleNamespace(path="/sessions/{id}")
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await asyncio.sleep(0.01)
            await send({"type": "http.response.body", "body": b"done"})
        before = trace_id_var.get()
        await RequestTelemetry(app)({"type": "http", "method": "POST"}, None, send)
        self.assertEqual(trace_id_var.get(), before)
        self.assertEqual(len(dict(messages[0]["headers"])[b"x-trace-id"]), 32)
        self.assertGreater(REQUEST_COUNT.labels("POST", "/sessions/{id}", 200)._value.get(), 0)

    async def test_unhandled_exception_counted(self):
        async def app(scope, receive, send):
            raise RuntimeError("test")
        with self.assertRaises(RuntimeError):
            await RequestTelemetry(app)({"type": "http", "method": "GET"}, None, None)
        self.assertGreater(REQUEST_COUNT.labels("GET", "unmatched", 500)._value.get(), 0)


@unittest.skipUnless(os.getenv("RUN_POSTGRES_TESTS") == "1", "requires isolated PostgreSQL")
class MemoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app.core.memory import memory_engine
        with memory_engine().begin() as conn:
            conn.exec_driver_sql((Path(__file__).resolve().parents[1] / "migrations/001_agent_memory.sql").read_text())

    def setUp(self):
        from app.core.memory import memory_engine
        from sqlalchemy import text
        with memory_engine().begin() as conn:
            conn.execute(text("TRUNCATE agent_memory"))

    def test_persistence_isolation_expiry_and_delete(self):
        from app.core.memory import MemoryStore, memory_engine
        from sqlalchemy import text
        a = MemoryStore(1, 10)
        a.write("short", "7", "slots", {"complaint": "test"})
        with memory_engine().connect() as conn:
            stored = conn.scalar(text("SELECT value FROM agent_memory LIMIT 1"))
            self.assertIn("ciphertext", stored)
            self.assertNotIn("complaint", str(stored))
        self.assertEqual(MemoryStore(1, 10).read("short", "7")[0]["value"], {"complaint": "test"})
        self.assertEqual(MemoryStore(2, 10).read("short", "7"), [])
        self.assertEqual(MemoryStore(1, 11).read("short", "7"), [])
        self.assertEqual(a.read("short", "8"), [])
        a.write("long", "profile", "preference", {"content": "test"})
        a.forget("preference")
        self.assertEqual(a.read("long", "profile"), [])
        with memory_engine().begin() as conn:
            conn.execute(text("UPDATE agent_memory SET expires_at=CURRENT_TIMESTAMP-interval '1 second'"))
        self.assertEqual(a.read("short", "7"), [])

    def test_lock_and_release(self):
        from app.core.memory import session_lock, SessionBusy
        with session_lock(1, 10, 7):
            with self.assertRaises(SessionBusy):
                with session_lock(1, 10, 7):
                    pass
            with session_lock(1, 11, 7):
                pass
        with session_lock(1, 10, 7):
            pass

    def test_upsert_quota(self):
        from app.core.memory import MemoryStore
        store = MemoryStore(1, 10)
        with patch.object(settings, "memory_max_items", 1):
            store.write("long", "profile", "one", {"content": "one"})
            store.write("long", "profile", "one", {"content": "updated"})
            with self.assertRaises(ValueError):
                store.write("long", "profile", "two", {"content": "two"})


if __name__ == "__main__":
    unittest.main()
