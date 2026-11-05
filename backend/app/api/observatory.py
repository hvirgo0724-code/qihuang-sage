"""平台观测路由：存活/就绪探针、Prometheus 指标。"""
from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core import milvus_client, neo4j_client
from app.core.database import SessionLocal
from app.core.metrics import CONTENT_TYPE_LATEST, render_metrics
from app.core.redis_client import get_redis
from app.schemas.schemas import HealthOut

router = APIRouter(tags=["observatory"])


@router.get("/healthz", response_model=HealthOut)
def healthz():
    return HealthOut(status="ok")


@router.get("/readyz")
def readyz():
    deps = {"mysql": False, "redis": False, "neo4j": False, "milvus": False}
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        deps["mysql"] = True
    except Exception:
        deps["mysql"] = False
    try:
        get_redis().ping()
        deps["redis"] = True
    except Exception:
        deps["redis"] = False
    deps["neo4j"] = neo4j_client.available()
    deps["milvus"] = milvus_client.available()
    try:
        from app.core.memory import memory_engine
        with memory_engine().connect() as conn:
            conn.execute(text("SELECT 1 FROM agent_memory LIMIT 1"))
        deps["postgres"] = True
    except Exception:
        deps["postgres"] = False
    ready = all(deps.values())
    return JSONResponse(status_code=200 if ready else 503,
                        content={"ready": ready, "dependencies": deps})


@router.get("/metrics")
def metrics():
    return Response(content=render_metrics(), media_type=CONTENT_TYPE_LATEST)