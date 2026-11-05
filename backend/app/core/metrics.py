"""Prometheus 指标定义与埋点助手。"""
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST

# 请求
REQUEST_COUNT = Counter(
    "tcm_requests_total", "Total requests", ["method", "path", "status"]
)
REQUEST_LATENCY = Histogram(
    "tcm_request_latency_seconds", "Request latency", ["method", "path"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10),
)

# LLM
LLM_CALL_COUNT = Counter("tcm_llm_calls_total", "LLM calls", ["model", "scene", "outcome"])
LLM_LATENCY = Histogram("tcm_llm_latency_seconds", "LLM latency", ["model", "scene"])
LLM_TOKENS = Counter("tcm_llm_tokens_total", "LLM tokens", ["model", "type"])

# 检索
GRAPH_SEARCH_LATENCY = Histogram(
    "tcm_graph_search_latency_seconds", "Graph search latency",
    buckets=(0.01, 0.05, 0.1, 0.2, 0.5, 1, 2),
)
VECTOR_SEARCH_LATENCY = Histogram("tcm_vector_search_latency_seconds", "Vector search latency")
GRAPH_SEARCH_HITS = Counter("tcm_graph_search_hits_total", "Graph search hits")

# 护栏
SAFETY_CHECK_COUNT = Counter("tcm_safety_checks_total", "Safety checks", ["stage", "result"])

# 队列
QUEUE_DEPTH = Gauge("tcm_celery_queue_depth", "Celery queue depth")


def render_metrics() -> bytes:
    return generate_latest()
TURN_FAILURES = Counter("tcm_consultation_failures_total", "Failed SSE consultation turns")
