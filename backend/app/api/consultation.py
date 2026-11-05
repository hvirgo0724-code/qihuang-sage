"""问诊路由：会话、图片上传（质检+异步识别）、SSE 对话、报告、消息、历史。"""
import logging
from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.logging import get_trace_id
from app.models.entities import AsyncJob, TcmImage, User, SyndromeAnalysis, ReportReview
from app.schemas.schemas import (
    ChatRequest,
    ImageUploadOut,
    MessageOut,
    SessionCreate,
    SessionOut,
)
from app.services import audit_service, consultation_service, image_analysis_service

logger = logging.getLogger("app.consultation-api")
router = APIRouter(prefix="/consultation", tags=["consultation"])

UPLOAD_DIR = "/app/uploads"


@router.delete("/{session_id}", status_code=204)
def delete_session(session_id: int, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    from sqlalchemy import text
    from app.core.memory import session_lock, SessionBusy, memory_engine
    from app.models.entities import ConsultationSession, Feedback, SafetyAuditLog
    session = db.query(ConsultationSession).filter(
        ConsultationSession.session_id == session_id,
        ConsultationSession.user_id == user.user_id,
        ConsultationSession.tenant_id == user.tenant_id).first()
    if not session:
        raise HTTPException(404, detail="会话不存在或无权访问")
    try:
        with session_lock(user.tenant_id, user.user_id, session_id):
            analysis_ids = db.query(SyndromeAnalysis.analysis_id).filter(
                SyndromeAnalysis.session_id == session_id)
            db.query(Feedback).filter(Feedback.user_id == user.user_id,
                                      Feedback.analysis_id.in_(analysis_ids)).delete(synchronize_session=False)
            db.query(SafetyAuditLog).filter(SafetyAuditLog.session_id == session_id).update(
                {SafetyAuditLog.raw_text: None}, synchronize_session=False)
            db.delete(session)
            db.flush()
            with memory_engine().begin() as conn:
                conn.execute(text("DELETE FROM agent_memory WHERE tenant_id=:tenant AND user_id=:user "
                                  "AND kind='short' AND namespace=:namespace"),
                             {"tenant": user.tenant_id, "user": user.user_id, "namespace": str(session_id)})
            db.commit()
    except SessionBusy:
        db.rollback()
        raise HTTPException(409, detail="本次问诊正在处理，请稍后再删除")
    except Exception:
        db.rollback()
        raise
    audit_service.record(db, "delete", "consultation_session", str(session_id))


@router.post("/session", response_model=SessionOut)
def create_session(
    data: SessionCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    s = consultation_service.create_session(db, user.user_id, data.complaint, get_trace_id(), user.tenant_id)
    audit_service.record(db, "create", "consultation_session", str(s.session_id))
    return SessionOut(
        session_id=s.session_id, status=s.status, complaint=s.complaint,
        risk_level=s.risk_level, start_time=s.start_time, end_time=s.end_time, trace_id=s.trace_id,
    )


@router.post("/{session_id}/image", response_model=ImageUploadOut)
def upload_image(
    session_id: int,
    image_type: str = Form(...),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if image_type not in ("tongue", "face"):
        raise HTTPException(status_code=400, detail="image_type 须为 tongue 或 face")
    session = consultation_service.get_session(db, session_id, user.user_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在或无权访问")

    data = file.file.read()
    # 质量预检 + 归一化
    try:
        ok, msg = image_analysis_service.precheck_image(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    import os
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    filename = f"{uuid4().hex}.jpg"
    file_path = os.path.join(UPLOAD_DIR, filename)
    with open(file_path, "wb") as f:
        f.write(image_analysis_service.normalize_image(data))

    image = TcmImage(
        session_id=session_id, image_type=image_type, file_path=file_path, quality_pass=ok
    )
    db.add(image)
    db.commit()
    db.refresh(image)

    if not ok:
        # 质检不通过：不进入识别流程，返回明确提示（图片记录已留档 quality_pass=false）
        raise HTTPException(status_code=400, detail=msg)
    job_id = uuid4().hex
    db.add(AsyncJob(job_id=job_id, job_type="image_analysis", status="pending", progress=0,
                    params={"image_id": image.image_id, "session_id": session_id}, trace_id=get_trace_id()))
    db.commit()

    from app.tasks.jobs import analyze_image_task

    try:
        analyze_image_task.delay(job_id=job_id, image_id=image.image_id,
                                 image_path=file_path, image_type=image_type, session_id=session_id)
    except Exception:
        logger.exception("image_task_dispatch_failed job_id=%s", job_id)
        job = db.get(AsyncJob, job_id)
        job.status = "failed"
        job.error = "识别任务提交失败，请稍后重试"
        job.finish_time = datetime.now()
        db.commit()
        raise HTTPException(status_code=503, detail="图片识别服务暂不可用，请稍后重试")
    audit_service.record(db, "create", "tcm_image", str(image.image_id))
    return ImageUploadOut(job_id=job_id, image_id=image.image_id)


@router.post("/{session_id}/chat")
def chat(
    session_id: int,
    data: ChatRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = consultation_service.get_session(db, session_id, user.user_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在或无权访问")

    from app.core.logging import session_id_var

    session_id_var.set(str(session_id))

    def gen():
        # Own the SQLAlchemy session for the full SSE lifetime (including disconnect).
        from app.core.database import SessionLocal
        from app.core.logging import user_id_var, tenant_id_var
        user_id_var.set(str(user.user_id))
        tenant_id_var.set(str(user.tenant_id))
        with SessionLocal() as stream_db:
            owned = consultation_service.get_session(stream_db, session_id, user.user_id)
            if owned:
                yield from consultation_service.chat_stream(stream_db, owned, data.message)

    async def stream():
        from contextvars import copy_context
        import anyio
        ctx, iterator, sentinel = copy_context(), gen(), object()
        try:
            while True:
                chunk = await anyio.to_thread.run_sync(ctx.run, next, iterator, sentinel)
                if chunk is sentinel:
                    break
                yield chunk
        finally:
            with anyio.CancelScope(shield=True):
                await anyio.to_thread.run_sync(ctx.run, iterator.close)

    return StreamingResponse(stream(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    })


@router.get("/{session_id}/result")
def get_result(session_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    session = consultation_service.get_session(db, session_id, user.user_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在或无权访问")
    analysis = consultation_service.get_latest_analysis(db, session_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="暂无辨证报告")
    from app.services.report_review_service import patient_result
    return patient_result(db, analysis)


@router.get("/{session_id}/messages", response_model=list[MessageOut])
def get_messages(session_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    session = consultation_service.get_session(db, session_id, user.user_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在或无权访问")
    records = consultation_service.list_messages(db, session_id)
    from app.services.inquiry_choices import build_choices
    # Upgrade the last unanswered historical question to the current button schema.
    last_question = next((r for r in reversed(records) if r.type != "image"), None)
    choice_meta = None
    if (session.status == "ongoing" and last_question is not None
            and last_question.role == "assistant" and last_question.type == "text"):
        choice_meta = {**(last_question.meta or {}), "choices": build_choices(last_question.content or "")}
    return [MessageOut(
        record_id=r.record_id, role=r.role, type=r.type,
        content="报告已生成，请进入报告页面查看审核状态。" if r.type == "result" else r.content,
        meta=None if r.type == "result" else choice_meta if r is last_question and choice_meta is not None else r.meta,
        create_time=r.create_time,
    ) for r in records]


@router.get("/me", response_model=list[SessionOut])
def my_sessions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sessions = consultation_service.list_sessions(db, user.user_id)
    latest = (db.query(SyndromeAnalysis.session_id,
                      func.max(SyndromeAnalysis.analysis_id).label("analysis_id"))
              .filter(SyndromeAnalysis.session_id.in_([s.session_id for s in sessions]))
              .group_by(SyndromeAnalysis.session_id).subquery())
    reports = {row.session_id: row for row in db.query(
        latest.c.session_id, latest.c.analysis_id, ReportReview.status
    ).outerjoin(ReportReview, ReportReview.analysis_id == latest.c.analysis_id).all()}
    return [SessionOut(
        session_id=s.session_id, status=s.status, complaint=s.complaint,
        risk_level=s.risk_level, start_time=s.start_time, end_time=s.end_time, trace_id=s.trace_id,
        report_status=("confirmed" if reports[s.session_id].status == "confirmed" else "pending")
                      if s.session_id in reports else None,
        analysis_id=reports[s.session_id].analysis_id if s.session_id in reports else None,
    ) for s in sessions]
