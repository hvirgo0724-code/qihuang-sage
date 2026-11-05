"""Neo4j 客户端封装：驱动池、超时、schema 白名单校验、健康探测与降级。"""
import logging
from typing import Any, Optional

from neo4j import Driver, GraphDatabase

from app.core.config import settings
from app.core.metrics import GRAPH_SEARCH_LATENCY, GRAPH_SEARCH_HITS

logger = logging.getLogger("app.neo4j")

_driver: Optional[Driver] = None

# Cypher 生成 schema 白名单：仅允许访问这些标签/关系，防注入与越权查询
ALLOWED_LABELS = {"Herb", "Formula", "Syndrome", "Symptom", "Effect", "Meridian", "Contraindication"}
ALLOWED_RELS = {"CONTAINS", "TREATS", "MANIFESTS", "HAS_EFFECT", "ENTERS", "CONTRADICTS", "INCOMPATIBLE_WITH"}
ALLOWED_KEYS = {"name", "pinyin", "nature", "flavors", "meridians", "effects", "toxicity",
                "daily_dose_range", "contraindications", "source", "aliases", "composition",
                "indications", "usage", "dosage_note", "definition", "main_symptoms",
                "accompanying_symptoms", "tongue", "pulse", "treatment_principle", "formulas",
                "location", "dosage", "is_main", "rule", "category", "updated_at"}


def get_driver() -> Driver:
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
            connection_timeout=5,
            max_connection_lifetime=1800,
        )
    return _driver


def close_driver() -> None:
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None


def available() -> bool:
    try:
        get_driver().verify_connectivity()
        return True
    except Exception:
        return False


def run_query(query: str, params: Optional[dict] = None) -> list[dict[str, Any]]:
    """执行查询并返回记录字典列表；带超时，失败抛异常由上层降级处理。"""
    with GRAPH_SEARCH_LATENCY.time():
        with get_driver().session() as session:
            result = session.run(query, params or {})
            records = [dict(r) for r in result]
            GRAPH_SEARCH_HITS.inc(len(records))
            return records


def validate_cypher(query: str) -> bool:
    """对本地生成的 Cypher 做白名单校验，防止注入/越权。"""
    import re

    if query.strip().upper().startswith(("MATCH", "CALL", "WITH", "RETURN")):
        labels = set(re.findall(r":([A-Za-z]+)", query))
        if labels - ALLOWED_LABELS:
            return False
    return True