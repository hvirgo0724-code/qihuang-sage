"""知识图谱导入与向量初始化（幂等，可重复执行）。

- 将 init/knowledge_graph.cypher 导入 Neo4j
- 将 Formula/Syndrome/Symptom/Herb 文本向量化写入 Milvus
可由 neo4j-init 一次性 job 或 Celery 任务触发。
"""
import logging
import os
from typing import Optional

from app.core import llm, milvus_client, neo4j_client

logger = logging.getLogger("app.init_knowledge")

CYPHER_CANDIDATES = [
    "/init/knowledge_graph.cypher",
    "init/knowledge_graph.cypher",
    "/app/init/knowledge_graph.cypher",
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "init", "knowledge_graph.cypher"),
]


def _find_cypher() -> Optional[str]:
    for p in CYPHER_CANDIDATES:
        if os.path.exists(p):
            return p
    return None


def load_cypher() -> bool:
    """执行 Cypher 种子，返回是否成功。"""
    path = _find_cypher()
    if not path:
        logger.error("cypher seed file not found")
        return False
    try:
        with open(path, "r", encoding="utf-8") as f:
            cypher = f.read()
        # 先剔除整行 // 注释，再按 ; 拆分语句。
        # 若先拆分再按 startswith("//") 过滤，会因每条语句前都有章节注释而整段被丢弃。
        cleaned = "\n".join(
            ln for ln in cypher.splitlines() if not ln.strip().startswith("//")
        )
        statements = [s.strip() for s in cleaned.split(";") if s.strip()]
        with neo4j_client.get_driver().session() as session:
            for stmt in statements:
                session.run(stmt)
        logger.info("cypher seed loaded")
        return True
    except Exception as e:  # noqa: BLE001
        logger.error("load cypher failed: %s", e)
        return False


def _node_text(label: str, props: dict) -> str:
    parts = [str(props.get("name", ""))]
    for key in ("effects", "definition", "indications", "nature", "flavors", "composition", "main_symptoms", "accompanying_symptoms"):
        v = props.get(key)
        if v:
            parts.append("、".join(v) if isinstance(v, list) else str(v))
    return " ".join(parts)


def build_vectors(batch_size: int = 32) -> int:
    """将知识节点向量化写入 Milvus，返回写入条数；embedding 不可用时返回 0（降级）。"""
    if not llm.llm_configured():
        logger.warning("LLM API key not configured, skip vector build")
        return 0
    try:
        milvus_client.ensure_collection()
    except Exception as e:  # noqa: BLE001
        logger.warning("milvus unavailable, skip vector build: %s", e)
        return 0

    labels = ["Formula", "Syndrome", "Symptom", "Herb"]
    total = 0
    for label in labels:
        try:
            rows = neo4j_client.run_query(
                f"MATCH (n:{label}) RETURN n.name AS name, properties(n) AS props"
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("fetch %s failed: %s", label, e)
            continue
        if not rows:
            continue
        texts = [_node_text(label, r["props"]) for r in rows]
        node_ids = [r["name"] for r in rows]
        try:
            vectors = llm.embed_texts(texts)
        except Exception as e:  # noqa: BLE001
            logger.warning("embed %s failed: %s", label, e)
            continue
        batch = [
            {"node_id": nid, "label": label, "text": txt, "vector": vec}
            for nid, txt, vec in zip(node_ids, texts, vectors)
        ]
        try:
            milvus_client.upsert_vectors(batch)
            total += len(batch)
        except Exception as e:  # noqa: BLE001
            logger.warning("upsert %s failed: %s", label, e)
    logger.info("vector build done, total=%s", total)
    return total


def run_all() -> dict:
    cypher_ok = load_cypher()
    vectors = build_vectors() if cypher_ok else 0
    return {"cypher_ok": cypher_ok, "vectors": vectors}


if __name__ == "__main__":
    from app.core.logging import setup_logging

    setup_logging()
    result = run_all()
    print(result)
    if not result["cypher_ok"]:
        raise SystemExit(1)