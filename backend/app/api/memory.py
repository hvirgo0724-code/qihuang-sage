from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from app.api.deps import get_current_user
from app.core.memory import MemoryStore
from app.models.entities import User
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.entities import ConsultationSession, ConsultationRecord
from app.services.auth_service import get_profile
from app.services.memory_service import collect_candidates

router = APIRouter(prefix="/memory", tags=["memory"])


class RememberRequest(BaseModel):
    key: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,64}$")
    content: str = Field(min_length=1, max_length=2000)
    consent: Literal[True]

    @field_validator('content')
    @classmethod
    def nonempty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError('记忆内容不能为空')
        return value.strip()


@router.get("")
def list_memory(user: User = Depends(get_current_user)):
    return MemoryStore(user.tenant_id, user.user_id).read("long", "profile")


@router.get("/suggestions")
def suggestions(session_id: int | None = None, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    sessions = db.query(ConsultationSession).filter(
        ConsultationSession.tenant_id == user.tenant_id,
        ConsultationSession.user_id == user.user_id)
    if session_id is not None:
        sessions = sessions.filter(ConsultationSession.session_id == session_id)
    owned = sessions.order_by(ConsultationSession.session_id.desc()).limit(20).all()
    if session_id is not None and not owned:
        raise HTTPException(404, detail="会话不存在或无权访问")
    snapshots = []
    for session in owned:
        records = db.query(ConsultationRecord).filter(
            ConsultationRecord.session_id == session.session_id,
            ConsultationRecord.role == "assistant").order_by(
                ConsultationRecord.record_id.desc()).limit(100).all()
        for record in records:
            if isinstance(record.meta, dict) and isinstance(record.meta.get("slots"), dict):
                snapshots.append((session.session_id, record.meta["slots"]))
                break
    saved = MemoryStore(user.tenant_id, user.user_id).read("long", "profile")
    return collect_candidates(get_profile(db, user.user_id).model_dump(), snapshots, saved)


@router.put("")
def remember(data: RememberRequest, user: User = Depends(get_current_user)):
    try:
        MemoryStore(user.tenant_id, user.user_id).write("long", "profile", data.key,
            {"content": data.content, "source": "user_confirmed"})
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from exc
    return {"saved": True}


@router.delete("/{key}", status_code=204)
def forget(key: str, user: User = Depends(get_current_user)):
    MemoryStore(user.tenant_id, user.user_id).forget(key)
