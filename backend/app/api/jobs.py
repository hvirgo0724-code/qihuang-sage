"""异步任务状态查询路由。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.entities import AsyncJob
from app.schemas.schemas import JobOut

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.get(AsyncJob, job_id)
    if not job:
        return JobOut(job_id=job_id, job_type="unknown", status="not_found")
    return JobOut(
        job_id=job.job_id, job_type=job.job_type, status=job.status,
        progress=job.progress, result=job.result, error=job.error, trace_id=job.trace_id,
    )