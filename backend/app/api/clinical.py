"""Patient consent, assigned physician access, and human consultation."""
import os
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.core.database import get_db
from app.core.security import hash_password
from app.models.entities import (User, ConsultationSession, ConsultationRecord,
    SyndromeAnalysis, TcmImage, ClinicalEncounter, ClinicalMessage, ReportReview)
from app.schemas.schemas import SyndromeReport
from app.services.consultation_service import get_latest_analysis, analysis_to_report
from app.services import audit_service

router = APIRouter(prefix="/clinical", tags=["人工接诊"])


def doctor(user: User = Depends(get_current_user)):
    if user.role != "DOCTOR":
        raise HTTPException(403, "需要医生权限")
    return user


class RequestEncounter(BaseModel):
    doctor_id: int
    consent: Literal[True]


class TextInput(BaseModel):
    content: str = Field(min_length=1, max_length=10000)

    @field_validator("content")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("内容不能为空")
        return value.strip()


class DoctorInput(BaseModel):
    username: str = Field(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_.-]+$")
    nickname: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=12, max_length=72)

    @field_validator("password")
    @classmethod
    def password_bytes(cls, value):
        if len(value.encode()) > 72:
            raise ValueError("密码不能超过 72 字节")
        return value


class ReportEdit(BaseModel):
    revision: int = Field(ge=0)
    report: SyndromeReport


class ReportConfirm(BaseModel):
    revision: int = Field(ge=1)


def review_state(db, report):
    if not report:
        return None
    row = db.get(ReportReview, report.analysis_id)
    return {"analysis_id": report.analysis_id, "status": row.status if row else "pending",
            "revision": row.revision if row else 0,
            "report": row.report if row else analysis_to_report(report)}


def editable_report(db, user, session_id, analysis_id):
    # Serialize approval with report publication, and always verify latest version.
    session = db.query(ConsultationSession).filter_by(session_id=session_id).with_for_update().first()
    row = encounter(db, user, session_id)
    if row.status not in ("active", "closed"):
        raise HTTPException(409, "请先接受接诊")
    analysis = (db.query(SyndromeAnalysis).filter_by(session_id=session_id)
                .order_by(SyndromeAnalysis.analysis_id.desc()).with_for_update().first())
    if not analysis or analysis.analysis_id != analysis_id:
        raise HTTPException(409, "报告版本已变化，请刷新后审核最新报告")
    review = db.query(ReportReview).filter_by(analysis_id=analysis_id).populate_existing().with_for_update().first()
    if review and review.status == "confirmed":
        raise HTTPException(409, "报告已确认发布，不能覆盖已发布版本")
    return session, analysis, review


@router.put("/sessions/{session_id}/reports/{analysis_id}")
def edit_report(session_id: int, analysis_id: int, body: ReportEdit,
                user=Depends(doctor), db: Session = Depends(get_db)):
    _, analysis, review = editable_report(db, user, session_id, analysis_id)
    if body.revision != (review.revision if review else 0):
        raise HTTPException(409, "草稿已更新，请刷新后修改")
    if not review:
        review = ReportReview(analysis_id=analysis_id, revision=0, status="pending")
        db.add(review)
    review.report = body.report.model_dump()
    review.revision += 1
    db.flush()
    audit_service.record(db, "edit_report_draft", "syndrome_analysis", str(analysis_id))
    return review_state(db, analysis)


@router.post("/sessions/{session_id}/reports/{analysis_id}/confirm")
def confirm_report(session_id: int, analysis_id: int, body: ReportConfirm,
                   user=Depends(doctor), db: Session = Depends(get_db)):
    session, analysis, review = editable_report(db, user, session_id, analysis_id)
    if not review or review.revision != body.revision:
        raise HTTPException(409, "请保存草稿并确认最新版本")
    if not review.report.get("syndrome") or not review.report.get("treatment_principle"):
        raise HTTPException(422, "请补充辨证结论和调养原则后确认")
    review.status, review.confirmed_by, review.confirmed_at = "confirmed", user.user_id, datetime.now()
    session.status, session.end_time = "completed", datetime.now()
    db.add(ClinicalMessage(session_id=session_id, author_id=user.user_id, author_role="DOCTOR",
                           content="辨证报告已由医生审核确认，请前往报告页面查看正式报告。"))
    audit_service.record(db, "confirm_report", "syndrome_analysis", str(analysis_id))
    db.flush()
    return review_state(db, analysis)


def own_session(db, user, session_id):
    row = db.query(ConsultationSession).filter_by(session_id=session_id,
        user_id=user.user_id, tenant_id=user.tenant_id).with_for_update().first()
    if not row:
        raise HTTPException(404, "问诊不存在")
    return row


def encounter(db, user, session_id):
    row = db.query(ClinicalEncounter).filter_by(session_id=session_id,
        tenant_id=user.tenant_id).with_for_update().first()
    if not row or not (row.patient_id == user.user_id or
        (user.role == "DOCTOR" and row.doctor_id == user.user_id and row.status != "cancelled")):
        raise HTTPException(404, "接诊不存在或未授权")
    return row


def packed(row):
    return {key: getattr(row, key) for key in ("session_id", "doctor_id", "patient_id",
        "status", "consent_at", "accepted_at", "closed_at", "review", "reviewed_at")}


@router.get("/doctors")
def doctors(user=Depends(get_current_user), db: Session = Depends(get_db)):
    return [{"user_id": u.user_id, "nickname": u.nickname or u.username}
        for u in db.query(User).filter_by(tenant_id=user.tenant_id, role="DOCTOR", status="active").all()]


@router.get("/admin/doctors")
def admin_doctors(user=Depends(require_admin), db: Session = Depends(get_db)):
    return [{"user_id": u.user_id, "username": u.username, "nickname": u.nickname, "status": u.status}
        for u in db.query(User).filter_by(tenant_id=user.tenant_id, role="DOCTOR").all()]


@router.post("/admin/doctors", status_code=201)
def create_doctor(body: DoctorInput, user=Depends(require_admin), db: Session = Depends(get_db)):
    row = User(tenant_id=user.tenant_id, username=body.username, nickname=body.nickname,
        password_hash=hash_password(body.password), role="DOCTOR", status="active")
    db.add(row)
    try:
        db.flush()
        audit_service.record(db, "create_doctor", "user", str(row.user_id))
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "用户名已存在")
    return {"user_id": row.user_id}


@router.post("/sessions/{session_id}/request", status_code=201)
def request_encounter(session_id: int, body: RequestEncounter, user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "USER":
        raise HTTPException(403, "请使用患者账号申请接诊")
    own_session(db, user, session_id)
    physician = db.query(User).filter_by(user_id=body.doctor_id, tenant_id=user.tenant_id,
        role="DOCTOR", status="active").first()
    if not physician:
        raise HTTPException(404, "医生不可用")
    previous = db.get(ClinicalEncounter, session_id)
    if previous and previous.status != "cancelled":
        raise HTTPException(409, "该问诊已申请过人工接诊，请新建问诊再次申请")
    if previous:
        row = previous
        row.doctor_id, row.status, row.consent_at = physician.user_id, "requested", datetime.now()
        row.accepted_at = row.closed_at = row.reviewed_at = row.review = None
    else:
        row = ClinicalEncounter(session_id=session_id, tenant_id=user.tenant_id,
            patient_id=user.user_id, doctor_id=physician.user_id, status="requested")
        db.add(row)
    db.flush()
    audit_service.record(db, "request_encounter", "consultation", str(session_id))
    return packed(row)


@router.get("/cases")
def cases(user=Depends(doctor), db: Session = Depends(get_db)):
    rows = db.query(ClinicalEncounter, ConsultationSession, User).join(ConsultationSession,
        ClinicalEncounter.session_id == ConsultationSession.session_id).join(User,
        ClinicalEncounter.patient_id == User.user_id).filter(ClinicalEncounter.tenant_id == user.tenant_id,
        ClinicalEncounter.doctor_id == user.user_id, ClinicalEncounter.status != "cancelled").order_by(
        ClinicalEncounter.consent_at.desc()).limit(200).all()
    return [{**packed(e), "patient_name": p.nickname or p.username, "complaint": s.complaint,
             "report_status": (review_state(db, get_latest_analysis(db, s.session_id)) or {}).get("status")}
            for e, s, p in rows]


@router.get("/sessions/{session_id}")
def detail(session_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    # Patients may query before requesting, but may never probe another patient's session.
    if user.role != "DOCTOR":
        own_session(db, user, session_id)
        if not db.get(ClinicalEncounter, session_id):
            return None
    row = encounter(db, user, session_id)
    result = packed(row)
    result["messages"] = [{"message_id": m.message_id, "author_role": m.author_role,
        "content": m.content, "created_at": m.created_at} for m in db.query(ClinicalMessage)
        .filter_by(session_id=session_id).order_by(ClinicalMessage.message_id).all()]
    if user.role == "DOCTOR":
        result["records"] = [{"role": r.role, "content": r.content, "type": r.type} for r in
            db.query(ConsultationRecord).filter_by(session_id=session_id).order_by(ConsultationRecord.record_id).all()]
        report = db.query(SyndromeAnalysis).filter_by(session_id=session_id).order_by(SyndromeAnalysis.analysis_id.desc()).first()
        result["report_review"] = review_state(db, report)
        result["report"] = result["report_review"]["report"] if report else None
        result["images"] = [{
            "image_id": i.image_id,
            "image_type": i.image_type,
            "quality_pass": bool(i.quality_pass),
            "analysis_result": i.analysis_result,
        } for i in db.query(TcmImage).filter_by(session_id=session_id).order_by(TcmImage.image_id).all()]
        audit_service.record(db, "read_clinical_case", "consultation", str(session_id))
    return result


@router.get("/sessions/{session_id}/images/{image_id}")
def image(session_id: int, image_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    # encounter() 同时限定「被分配的医生」与「患者本人」，范围不越权。
    encounter(db, user, session_id)
    img = db.get(TcmImage, image_id)
    if not img or img.session_id != session_id:
        raise HTTPException(404, "图片不存在")
    if not os.path.exists(img.file_path):
        raise HTTPException(404, "图片文件已丢失")
    return FileResponse(img.file_path, media_type="image/jpeg")


@router.post("/sessions/{session_id}/messages", status_code=201)
def message(session_id: int, body: TextInput, user=Depends(get_current_user), db: Session = Depends(get_db)):
    row = encounter(db, user, session_id)
    if row.status != "active":
        raise HTTPException(409, "仅接诊中的会话可以发送消息")
    db.add(ClinicalMessage(session_id=session_id, author_id=user.user_id,
        author_role="DOCTOR" if user.user_id == row.doctor_id else "USER", content=body.content))
    audit_service.record(db, "clinical_message", "consultation", str(session_id))
    return {"status": "sent"}


@router.post("/sessions/{session_id}/accept")
def accept(session_id: int, user=Depends(doctor), db: Session = Depends(get_db)):
    row = encounter(db, user, session_id)
    if row.status != "requested":
        raise HTTPException(409, "该申请已处理")
    row.status, row.accepted_at = "active", datetime.now()
    audit_service.record(db, "accept_encounter", "consultation", str(session_id))
    return packed(row)


@router.put("/sessions/{session_id}/review")
def review(session_id: int, body: TextInput, user=Depends(doctor), db: Session = Depends(get_db)):
    row = encounter(db, user, session_id)
    if row.status != "active":
        raise HTTPException(409, "仅接诊中可以审阅")
    row.review, row.reviewed_at = body.content, datetime.now()
    audit_service.record(db, "review_encounter", "consultation", str(session_id))
    return packed(row)


@router.post("/sessions/{session_id}/close")
def close(session_id: int, user=Depends(doctor), db: Session = Depends(get_db)):
    row = encounter(db, user, session_id)
    if row.status != "active" or not row.review:
        raise HTTPException(409, "请先接诊并填写审阅意见")
    row.status, row.closed_at = "closed", datetime.now()
    audit_service.record(db, "close_encounter", "consultation", str(session_id))
    return packed(row)


@router.post("/sessions/{session_id}/cancel")
def cancel(session_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    own_session(db, user, session_id)
    row = encounter(db, user, session_id)
    row.status, row.closed_at = "cancelled", datetime.now()
    audit_service.record(db, "revoke_clinical_consent", "consultation", str(session_id))
    return packed(row)
