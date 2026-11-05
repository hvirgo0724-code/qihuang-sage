"""Celery 异步任务：图片识别、图谱导入、向量重建、批量导出（幂等、可观测）。"""
import json
import logging
from datetime import datetime

from app.core.database import SessionLocal
from app.models.entities import AsyncJob, TcmImage
from app.services import image_analysis_service
from app.tasks.celery_app import celery_app

logger = logging.getLogger("app.tasks")


def _set_job(job_id: str, status: str, progress: int, result=None, error=None) -> None:
    db = SessionLocal()
    try:
        job = db.get(AsyncJob, job_id)
        if job:
            job.status = status
            job.progress = progress
            if result is not None:
                job.result = result
            if error is not None:
                job.error = error
            if status in ("success", "failed"):
                job.finish_time = datetime.now()
            db.commit()
    finally:
        db.close()


@celery_app.task(bind=True, name="tasks.analyze_image", max_retries=2)
def analyze_image_task(self, job_id: str, image_id: int, image_path: str, image_type: str, session_id: int) -> dict:
    _set_job(job_id, "running", 20)
    db = SessionLocal()
    try:
        result = image_analysis_service.analyze(image_path, image_type)
        img = db.get(TcmImage, image_id)
        if img:
            img.analysis_result = result
            img.quality_pass = True
            db.commit()
        _set_job(job_id, "success", 100, result=result)
        return {"image_id": image_id, "result": result}
    except Exception as e:  # noqa: BLE001
        logger.error("analyze_image failed job=%s err=%s", job_id, e)
        _set_job(job_id, "failed", 100, error=str(e))
        raise
    finally:
        db.close()


@celery_app.task(bind=True, name="tasks.graph_import", max_retries=1)
def graph_import_task(self, job_id: str) -> dict:
    _set_job(job_id, "running", 30)
    try:
        from app.scripts.init_knowledge import run_all

        result = run_all()
        _set_job(job_id, "success", 100, result=result)
        return result
    except Exception as e:  # noqa: BLE001
        logger.error("graph_import failed job=%s err=%s", job_id, e)
        _set_job(job_id, "failed", 100, error=str(e))
        raise


@celery_app.task(bind=True, name="tasks.vector_rebuild", max_retries=1)
def vector_rebuild_task(self, job_id: str) -> dict:
    _set_job(job_id, "running", 30)
    try:
        from app.scripts.init_knowledge import build_vectors

        count = build_vectors()
        _set_job(job_id, "success", 100, result={"vectors": count})
        return {"vectors": count}
    except Exception as e:  # noqa: BLE001
        logger.error("vector_rebuild failed job=%s err=%s", job_id, e)
        _set_job(job_id, "failed", 100, error=str(e))
        raise


@celery_app.task(bind=True, name="tasks.export_data", max_retries=1)
def export_task(self, job_id: str, user_id: int) -> dict:
    """导出用户个人数据（数据导出权），结果落 async_job.result。"""
    _set_job(job_id, "running", 30)
    db = SessionLocal()
    try:
        from app.models.entities import ConsultationSession, SyndromeAnalysis
        from app.core.security import decrypt_plaintext

        sessions = (
            db.query(ConsultationSession)
            .filter(ConsultationSession.user_id == user_id)
            .order_by(ConsultationSession.start_time.asc())
            .all()
        )
        data = {
            "user_id": user_id,
            "sessions": [],
        }
        for s in sessions:
            analysis = (
                db.query(SyndromeAnalysis)
                .filter(SyndromeAnalysis.session_id == s.session_id)
                .first()
            )
            data["sessions"].append({
                "session_id": s.session_id,
                "complaint": decrypt_plaintext(s.complaint) or s.complaint,
                "risk_level": s.risk_level,
                "status": s.status,
                "start_time": s.start_time.isoformat() if s.start_time else None,
                "analysis": {
                    "syndrome": analysis.syndrome,
                    "evidence": analysis.evidence,
                    "treatment_principle": analysis.treatment_principle,
                    "formula_suggestions": analysis.formula_suggestions,
                } if analysis else None,
            })
        _set_job(job_id, "success", 100, result={"type": "export", "data": data, "format": "json"})
        return {"exported_sessions": len(data["sessions"])}
    except Exception as e:  # noqa: BLE001
        logger.error("export failed job=%s err=%s", job_id, e)
        _set_job(job_id, "failed", 100, error=str(e))
        raise
    finally:
        db.close()

@celery_app.task(name="tasks.expire_memory")
def expire_memory():
    from sqlalchemy import text
    from app.core.memory import memory_engine
    # Bounded batches avoid long locks; expired rows are already invisible to reads.
    with memory_engine().begin() as conn:
        result = conn.execute(text("""DELETE FROM agent_memory WHERE ctid IN
            (SELECT ctid FROM agent_memory WHERE expires_at <= CURRENT_TIMESTAMP
             LIMIT 10000 FOR UPDATE SKIP LOCKED)"""))
        return {"deleted": result.rowcount}
