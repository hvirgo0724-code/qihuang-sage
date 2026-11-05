"""大模型与 Embedding 客户端（LangChain + DashScope 兼容 OpenAI 协议）。"""
import logging
import time
from functools import lru_cache
from typing import Any, Optional

from app.core.config import settings
from app.core.langsmith import llm_trace
from opentelemetry import trace
from app.core.metrics import LLM_CALL_COUNT, LLM_LATENCY, LLM_TOKENS

logger = logging.getLogger("app.llm")
EMBEDDING_BATCH_SIZE = 10


def llm_configured() -> bool:
    key = (settings.llm_api_key or "").strip()
    if not key:
        return False
    # 识别占位/示例 key，避免误走真实调用导致 401 噪声
    lowered = key.lower()
    if any(marker in lowered for marker in ("your-", "your_", "placeholder", "change-me", "example", "sk-xxx")):
        return False
    return True


@lru_cache
def _text_llm(model: str):
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=model,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        temperature=0.3,
        timeout=settings.llm_timeout_seconds,
        max_retries=settings.llm_max_retries,
    )


@lru_cache
def _vision_llm(model: str):
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=model,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        temperature=0.2,
        timeout=settings.vision_timeout_seconds,
        max_retries=settings.llm_max_retries,
    )


@lru_cache
def _embeddings():
    from langchain_openai import OpenAIEmbeddings

    return OpenAIEmbeddings(
        model=settings.embedding_model,
        api_key=settings.llm_api_key,
        base_url=settings.embedding_base_url,
        check_embedding_ctx_length=False,
        chunk_size=EMBEDDING_BATCH_SIZE,
        request_timeout=settings.llm_timeout_seconds,
        max_retries=settings.llm_max_retries,
    )


def text_llm(model: Optional[str] = None):
    return _text_llm(model or settings.text_model)


def vision_llm(model: Optional[str] = None):
    return _vision_llm(model or settings.vision_model)


def embeddings_client():
    return _embeddings()


def embed_texts(texts: list[str]) -> list[list[float]]:
    """批量向量化；返回与输入等长的向量列表。失败抛异常由上层处理。"""
    if not texts:
        return []
    emb = embeddings_client()
    # DashScope v3/v4 每次请求最多 10 条文本；同一次调用按批串行执行。
    vectors = []
    for offset in range(0, len(texts), EMBEDDING_BATCH_SIZE):
        batch = texts[offset:offset + EMBEDDING_BATCH_SIZE]
        batch_vectors = emb.embed_documents(batch)
        if len(batch_vectors) != len(batch):
            raise ValueError("embedding response count does not match input count")
        vectors.extend(batch_vectors)
    # 统一裁剪到配置维度，避免模型维度漂移导致 Milvus 写入失败
    dim = settings.embedding_dim
    return [v[:dim] + [0.0] * (dim - len(v)) if len(v) < dim else v[:dim] for v in vectors]


def _count_tokens(response: Any, model: str) -> None:
    try:
        usage = getattr(response, "usage_metadata", None) or {}
        if usage.get("input_tokens"):
            LLM_TOKENS.labels(model, "input").inc(usage["input_tokens"])
        if usage.get("output_tokens"):
            LLM_TOKENS.labels(model, "output").inc(usage["output_tokens"])
    except Exception:
        pass


def invoke_text(messages: list[dict], model: Optional[str] = None, scene: str = "general") -> str:
    """调用文本 LLM，带失败切换备用模型。返回文本内容。"""
    models = [model or settings.text_model]
    if settings.text_model_fallback and settings.text_model_fallback not in models:
        models.append(settings.text_model_fallback)

    last_err: Exception | None = None
    for m in models:
        start = time.time()
        try:
            llm = _text_llm(m)
            with trace.get_tracer(__name__).start_as_current_span(f"llm.{scene}"), llm_trace(scene):
                resp = llm.invoke(messages)
            LLM_CALL_COUNT.labels(m, scene, "success").inc()
            _count_tokens(resp, m)
            return resp.content if hasattr(resp, "content") else str(resp)
        except Exception as e:  # noqa: BLE001
            last_err = e
            LLM_CALL_COUNT.labels(m, scene, "error").inc()
            logger.warning("LLM invoke failed model=%s scene=%s err=%s", m, scene, e)
        finally:
            LLM_LATENCY.labels(m, scene).observe(time.time() - start)
    raise RuntimeError("all LLM models failed") from last_err


def stream_text(messages: list[dict], model: Optional[str] = None, scene: str = "general"):
    """真实模型增量输出；已经输出内容后不切换模型，避免重复或拼接回复。"""
    from contextlib import closing
    models = [model or settings.text_model]
    if settings.text_model_fallback and settings.text_model_fallback not in models:
        models.append(settings.text_model_fallback)
    last_err = None
    for name in models:
        started, emitted, outcome = time.perf_counter(), False, "error"
        try:
            with trace.get_tracer(__name__).start_as_current_span(f"llm.{scene}"), llm_trace(scene):
                with closing(_text_llm(name).stream(messages)) as chunks:
                    for chunk in chunks:
                        _count_tokens(chunk, name)
                        if isinstance(chunk.content, str) and chunk.content:
                            emitted = True
                            yield chunk.content
            outcome = "success"
            return
        except GeneratorExit:
            outcome = "cancelled"
            raise
        except Exception as exc:
            last_err = exc
            if emitted:
                raise
            logger.warning("LLM stream failed model=%s scene=%s", name, scene)
        finally:
            LLM_CALL_COUNT.labels(name, scene, outcome).inc()
            LLM_LATENCY.labels(name, scene).observe(time.perf_counter() - started)
    raise RuntimeError("all LLM models failed") from last_err


def _vision_error_reason(error: Exception) -> str:
    """Return safe diagnostics without echoing provider bodies or image data."""
    status = getattr(error, "status_code", None)
    if status in (401, 403):
        return "认证或模型权限不足，请检查 API Key 和模型授权"
    if status == 429:
        return "请求限流或额度不足，请稍后重试并检查模型额度"
    if status in (400, 404, 422):
        return f"模型或请求参数不兼容（HTTP {status}），请检查视觉模型配置"
    if "timeout" in type(error).__name__.lower():
        return "模型响应超时，请稍后重试或调整 VISION_TIMEOUT_SECONDS"
    if "connection" in type(error).__name__.lower():
        return "无法连接模型服务，请检查网络和服务地址"
    if isinstance(error, ValueError):
        return "模型未返回有效文本"
    return "模型服务调用失败，请查看服务端日志"


def invoke_vision(messages: list[dict], model: Optional[str] = None, scene: str = "inspection") -> str:
    """调用多模态 LLM，带备用模型降级。"""
    models = [model or settings.vision_model]
    if settings.vision_model_fallback and settings.vision_model_fallback not in models:
        models.append(settings.vision_model_fallback)

    last_err: Exception | None = None
    failures = []
    for m in models:
        start = time.time()
        try:
            llm = _vision_llm(m)
            with trace.get_tracer(__name__).start_as_current_span(f"llm.{scene}"), llm_trace(scene):
                resp = llm.invoke(messages)
            if not isinstance(resp.content, str) or not resp.content.strip():
                raise ValueError("empty vision response")
            LLM_CALL_COUNT.labels(m, scene, "success").inc()
            _count_tokens(resp, m)
            return resp.content if hasattr(resp, "content") else str(resp)
        except Exception as e:  # noqa: BLE001
            last_err = e
            LLM_CALL_COUNT.labels(m, scene, "error").inc()
            reason = _vision_error_reason(e)
            failures.append(f"{m}：{reason}")
            logger.warning("Vision LLM failed model=%s scene=%s error_type=%s status=%s", m, scene, type(e).__name__, getattr(e, "status_code", None))
        finally:
            LLM_LATENCY.labels(m, scene).observe(time.time() - start)
    raise RuntimeError("图像分析失败；" + "；".join(failures)) from last_err
