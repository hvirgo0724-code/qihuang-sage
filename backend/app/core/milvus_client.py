"""Milvus 客户端封装：连接、集合定义、向量写入与稠密检索。

兼容性说明：服务端为 Milvus v3.0.2，客户端已对齐 pymilvus 3.0.x。本模块当前
仍使用传统 ORM API（connections / Collection / utility），该 API 在 pymilvus 3.0.x
中仍提供向后兼容（官方已标记弃用、建议改用 MilvusClient），因此无需在未验证的
环境里贸然重写；后续在可运行环境验证后再迁移到 MilvusClient。
"""
import logging
from typing import Any, Optional

from pymilvus import (
    Collection,
    CollectionSchema,
    DataType,
    FieldSchema,
    connections,
    utility,
)

from app.core.config import settings

logger = logging.getLogger("app.milvus")

_CONNECTED = False
COLLECTION_NAME = "tcm_knowledge"


def _connect() -> None:
    global _CONNECTED
    if _CONNECTED:
        return
    connections.connect(alias="default", host=settings.milvus_host, port=str(settings.milvus_port))
    _CONNECTED = True


def available() -> bool:
    try:
        _connect()
        utility.list_collections()
        return True
    except Exception:
        return False


def _schema() -> CollectionSchema:
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="node_id", dtype=DataType.VARCHAR, max_length=128),
        FieldSchema(name="label", dtype=DataType.VARCHAR, max_length=64),
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=4096),
        FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=settings.embedding_dim),
    ]
    return CollectionSchema(fields, description="中医方剂知识图谱节点向量")


def ensure_collection() -> Collection:
    _connect()
    if not utility.has_collection(COLLECTION_NAME):
        # pymilvus 3.0：通过构造 Collection 并传入 schema 创建集合
        # （旧版 utility.create_collection 已移除）
        Collection(name=COLLECTION_NAME, schema=_schema())
    return Collection(COLLECTION_NAME)


def _index_params(metric: str = "IP") -> dict:
    return {"index_type": "IVF_FLAT", "metric_type": metric, "params": {"nlist": 128}}


def _ensure_loaded(col: Collection) -> None:
    """确保集合已加载；进程重启后 Milvus 内存态丢失需重新 load。"""
    try:
        state = utility.load_state(COLLECTION_NAME)
        if getattr(state, "name", None) == "Loaded":
            return
    except Exception:  # noqa: BLE001
        pass
    try:
        col.load()
    except Exception as e:  # noqa: BLE001
        logger.warning("load collection failed: %s", e)


def create_index(metric: str = "IP") -> None:
    col = ensure_collection()
    if not col.has_index():
        col.create_index("vector", _index_params(metric))
    _ensure_loaded(col)


def upsert_vectors(rows: list[dict[str, Any]]) -> None:
    """rows: [{node_id, label, text, vector}]"""
    if not rows:
        return
    col = ensure_collection()
    # 先写数据再建索引/加载，保证首次导入完成即可检索
    col.insert([
        [r["node_id"] for r in rows],
        [r["label"] for r in rows],
        [r["text"] for r in rows],
        [r["vector"] for r in rows],
    ])
    col.flush()
    create_index()


def drop_all() -> None:
    _connect()
    if utility.has_collection(COLLECTION_NAME):
        utility.drop_collection(COLLECTION_NAME)


def search(query_vector: list[float], top_k: int = 8, label: Optional[str] = None) -> list[dict[str, Any]]:
    """稠密检索，返回 top-k 相似节点；失败抛异常由上层降级。"""
    from app.core.metrics import VECTOR_SEARCH_LATENCY

    col = ensure_collection()
    create_index()
    expr = f'label == "{label}"' if label else None
    with VECTOR_SEARCH_LATENCY.time():
        res = col.search(
            data=[query_vector],
            anns_field="vector",
            param={"metric_type": "IP", "params": {"nprobe": 16}},
            limit=top_k,
            expr=expr,
            output_fields=["node_id", "label", "text"],
        )
    out = []
    for hit in res[0]:
        out.append({"node_id": hit.entity.get("node_id"), "label": hit.entity.get("label"),
                    "text": hit.entity.get("text"), "score": float(hit.distance)})
    return out