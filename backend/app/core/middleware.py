"""Pure ASGI telemetry includes streaming duration and failures."""
from time import perf_counter
import logging
from uuid import uuid4
from opentelemetry import trace
from app.core.logging import trace_id_var, session_id_var, user_id_var, tenant_id_var
from app.core.metrics import REQUEST_COUNT, REQUEST_LATENCY


class RequestTelemetry:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        span = trace.get_current_span().get_span_context()
        tid = f"{span.trace_id:032x}" if span.is_valid else uuid4().hex
        tokens = [(var, var.set(value)) for var, value in (
            (trace_id_var, tid), (session_id_var, ""), (user_id_var, ""), (tenant_id_var, "0"))]
        started, status = perf_counter(), 500

        async def send_response(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                message.setdefault("headers", []).append((b"x-trace-id", tid.encode()))
            await send(message)

        try:
            await self.app(scope, receive, send_response)
        except Exception:
            status = 500
            logging.getLogger("app.http").exception("request_failed")
            raise
        finally:
            path = getattr(scope.get("route"), "path", "unmatched")
            elapsed = perf_counter() - started
            if path not in {"/metrics", "/healthz", "/readyz"}:
                REQUEST_COUNT.labels(scope["method"], path, status).inc()
                REQUEST_LATENCY.labels(scope["method"], path).observe(elapsed)
                logging.getLogger("app.http").info("request_completed", extra={
                    "route": path, "status": status, "duration_seconds": elapsed})
            for var, token in reversed(tokens):
                var.reset(token)
