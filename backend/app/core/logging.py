"""请求级上下文（trace_id/session_id/user_id/tenant_id）与结构化日志。"""
import logging
import uuid
from contextvars import ContextVar

trace_id_var: ContextVar[str] = ContextVar("trace_id", default="-")
session_id_var: ContextVar[str] = ContextVar("session_id", default="")
user_id_var: ContextVar[str] = ContextVar("user_id", default="")
tenant_id_var: ContextVar[str] = ContextVar("tenant_id", default="0")


def set_trace_id(value: str | None = None) -> str:
    tid = value or uuid.uuid4().hex[:24]
    trace_id_var.set(tid)
    return tid


def get_trace_id() -> str:
    from opentelemetry import trace
    span = trace.get_current_span().get_span_context()
    return f"{span.trace_id:032x}" if span.is_valid else trace_id_var.get()


def _context(logger, method, event):
    from opentelemetry import trace
    span = trace.get_current_span().get_span_context()
    event.update(trace_id=f"{span.trace_id:032x}" if span.is_valid else get_trace_id(),
                 span_id=f"{span.span_id:016x}" if span.is_valid else "",
                 session_id=session_id_var.get(), user_id=user_id_var.get(),
                 tenant_id=tenant_id_var.get())
    return event


def get_logger(name="app"):
    return logging.getLogger(name)


def setup_logging():
    import structlog
    shared = [structlog.contextvars.merge_contextvars, structlog.stdlib.ExtraAdder(), structlog.stdlib.add_log_level,
              structlog.stdlib.add_logger_name, structlog.processors.TimeStamper(fmt="iso"), _context]
    structlog.configure(processors=shared + [structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
                        logger_factory=structlog.stdlib.LoggerFactory(),
                        wrapper_class=structlog.stdlib.BoundLogger, cache_logger_on_first_use=True)
    handler = logging.StreamHandler()
    handler.setFormatter(structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared, processors=[structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                                             structlog.processors.format_exc_info,
                                             structlog.processors.JSONRenderer(ensure_ascii=False)]))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").disabled = True
