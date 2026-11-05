"""Initialize before serving requests; worker initializes after fork."""
from app.core.config import settings
_provider = None


def init_tracing(service_name="tcm-backend"):
    global _provider
    if _provider is not None or not settings.otel_exporter_otlp_endpoint:
        return
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.redis import RedisInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from app.core.database import engine
    from app.core.memory import memory_engine
    _provider = TracerProvider(resource=Resource.create({"service.name": service_name,
        "deployment.environment": settings.app_env}),
        sampler=ParentBased(TraceIdRatioBased(settings.otel_sample_ratio)))
    _provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(
        endpoint=settings.otel_exporter_otlp_endpoint,
        insecure=settings.otel_exporter_otlp_endpoint.startswith("http://"))))
    trace.set_tracer_provider(_provider)
    RedisInstrumentor().instrument()
    HTTPXClientInstrumentor().instrument()
    SQLAlchemyInstrumentor().instrument(engines=[engine, memory_engine()])


def instrument_app(app):
    init_tracing()
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    FastAPIInstrumentor.instrument_app(app, excluded_urls="healthz,readyz,metrics")


def shutdown_tracing():
    if _provider:
        _provider.shutdown()
