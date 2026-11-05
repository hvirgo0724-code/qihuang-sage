"""FastAPI 应用入口：路由注册、中间件、启动初始化。"""
import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging

logger = logging.getLogger("app.main")


def _create_app() -> FastAPI:
    setup_logging()
    if settings.app_env in {"prod", "production"}:
        if "change-me" in settings.jwt_secret_key or len(settings.jwt_secret_key) < 32:
            raise ValueError("Production requires a strong JWT_SECRET_KEY")
        if "change-me" in settings.encryption_key:
            raise ValueError("Production requires ENCRYPTION_KEY")
        if os.getenv("ADMIN_PASSWORD", "admin123") == "admin123":
            raise ValueError("Production requires ADMIN_PASSWORD")
    app = FastAPI(
        title="岐黄智诊 · 中医智能诊疗协同平台",
        version="1.0.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from app.core.middleware import RequestTelemetry
    app.add_middleware(RequestTelemetry)

    # 路由注册
    from app.api import admin, auth, consultation, feedback, jobs, knowledge, observatory

    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(consultation.router, prefix="/api/v1")
    app.include_router(jobs.router, prefix="/api/v1")
    app.include_router(knowledge.router, prefix="/api/v1")
    app.include_router(feedback.router, prefix="/api/v1")
    app.include_router(admin.router, prefix="/api/v1")
    app.include_router(observatory.router)

    from app.api import memory
    from app.api import clinical
    app.include_router(clinical.router, prefix="/api/v1")
    app.include_router(memory.router, prefix="/api/v1")
    from app.core.tracing import instrument_app
    instrument_app(app)
    return app


app = _create_app()


@app.on_event("startup")
def startup() -> None:
    from app.core.database import SessionLocal
    from app.services.prompt_service import ensure_prompts

    db = SessionLocal()
    try:
        ensure_prompts(db)
        _bootstrap_admin(db)
    finally:
        db.close()
    logger.info("backend started, env=%s", settings.app_env)


def _bootstrap_admin(db) -> None:
    from app.core.security import hash_password
    from app.models.entities import User

    username = os.getenv("ADMIN_USERNAME", "admin")
    password = os.getenv("ADMIN_PASSWORD", "admin123")
    if db.query(User).filter(User.username == username).first() is None:
        db.add(User(
            tenant_id=0, username=username, password_hash=hash_password(password),
            nickname="系统管理员", role="ADMIN",
        ))
        db.commit()
        logger.info("admin user bootstrapped username=%s", username)

@app.on_event("shutdown")
def shutdown():
    from app.core.tracing import shutdown_tracing
    from app.core.memory import memory_engine
    shutdown_tracing()
    memory_engine().dispose()
