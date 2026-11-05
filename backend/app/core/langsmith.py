"""Explicit opt-in; clinical inputs and outputs are hidden."""
from contextlib import contextmanager
from functools import lru_cache
from app.core.config import settings
from app.core.logging import get_trace_id


@lru_cache
def client():
    from langsmith import Client
    return Client(api_key=settings.langsmith_api_key, api_url=settings.langsmith_endpoint,
                  hide_inputs=True, hide_outputs=True)


@contextmanager
def llm_trace(scene):
    from langsmith import tracing_context
    enabled = settings.langsmith_tracing and bool(settings.langsmith_api_key)
    with tracing_context(enabled=enabled, client=client() if enabled else None,
                         project_name=settings.langsmith_project,
                         metadata={"otel_trace_id": get_trace_id(), "scene": scene}):
        yield
