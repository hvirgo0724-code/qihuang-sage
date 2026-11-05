"""认证与数据权利：注册/登录/刷新/画像（加密）/数据删除。"""
import logging
from datetime import datetime
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decrypt_plaintext,
    encrypt_plaintext,
    hash_password,
    verify_password,
)
from app.models.entities import OperationLog, User, UserProfile
from app.schemas.schemas import (
    LoginRequest,
    ProfileOut,
    ProfileUpdate,
    RegisterRequest,
    TokenResponse,
    UserOut,
)

logger = logging.getLogger("app.auth")


def _user_out(u: User) -> UserOut:
    return UserOut(
        user_id=u.user_id, username=u.username, nickname=u.nickname, avatar=u.avatar,
        gender=u.gender, age=u.age, role=u.role, tenant_id=u.tenant_id,
        data_consent_at=u.data_consent_at,
    )


def _tokens(u: User) -> TokenResponse:
    access = create_access_token(str(u.user_id), extra={"role": u.role, "tenant_id": u.tenant_id})
    refresh = create_refresh_token(str(u.user_id))
    return TokenResponse(access_token=access, refresh_token=refresh, user=_user_out(u))


def register(db: Session, data: RegisterRequest) -> TokenResponse:
    if not data.consent:
        raise HTTPException(status_code=400, detail="需先同意健康数据授权")
    exists = db.query(User).filter(User.username == data.username).first()
    if exists:
        raise HTTPException(status_code=409, detail="用户名已存在")
    user = User(
        tenant_id=0,
        username=data.username,
        password_hash=hash_password(data.password),
        nickname=data.nickname,
        gender=data.gender,
        age=data.age,
        data_consent_at=datetime.now() if data.consent else None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.add(UserProfile(user_id=user.user_id))
    db.commit()
    return _tokens(user)


def login(db: Session, data: LoginRequest) -> TokenResponse:
    user = db.query(User).filter(User.username == data.username).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if user.status != "active":
        raise HTTPException(status_code=403, detail="账号已停用")
    return _tokens(user)


def refresh(db: Session, refresh_token: str) -> TokenResponse:
    from app.core.security import decode_token

    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="无效的刷新令牌")
    user = db.get(User, int(payload["sub"]))
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    return _tokens(user)


def get_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


def get_profile(db: Session, user_id: int) -> ProfileOut:
    p = db.get(UserProfile, user_id)
    if not p:
        return ProfileOut(user_id=user_id)
    return ProfileOut(
        user_id=user_id, height=p.height, weight=p.weight,
        allergies=decrypt_plaintext(p.allergies),
        chronic_diseases=decrypt_plaintext(p.chronic_diseases),
        medication_history=decrypt_plaintext(p.medication_history),
        remark=decrypt_plaintext(p.remark),
    )


def update_profile(db: Session, user_id: int, data: ProfileUpdate) -> ProfileOut:
    p = db.get(UserProfile, user_id)
    if not p:
        p = UserProfile(user_id=user_id)
        db.add(p)
    if data.height is not None:
        p.height = data.height
    if data.weight is not None:
        p.weight = data.weight
    if data.allergies is not None:
        p.allergies = encrypt_plaintext(data.allergies)
    if data.chronic_diseases is not None:
        p.chronic_diseases = encrypt_plaintext(data.chronic_diseases)
    if data.medication_history is not None:
        p.medication_history = encrypt_plaintext(data.medication_history)
    if data.remark is not None:
        p.remark = encrypt_plaintext(data.remark)
    db.commit()
    return get_profile(db, user_id)


def delete_user_data(db: Session, user_id: int) -> None:
    """清除个人健康业务数据，保留账号、凭据、角色及登录能力。"""
    user = db.get(User, user_id)
    if not user:
        return
    from app.core.memory import memory_engine
    from sqlalchemy import text
    from app.models.entities import ConsultationSession, Feedback, SafetyAuditLog
    scope = {'tenant': user.tenant_id, 'user': user.user_id}
    try:
        sessions = db.query(ConsultationSession).filter(
            ConsultationSession.user_id == user_id,
            ConsultationSession.tenant_id == user.tenant_id).all()
        session_ids = [session.session_id for session in sessions]
        if session_ids:
            # Retain safety audit metadata, but remove health text belonging to these sessions.
            db.query(SafetyAuditLog).filter(SafetyAuditLog.session_id.in_(session_ids)).update(
                {SafetyAuditLog.raw_text: None}, synchronize_session=False)
        for session in sessions:
            db.delete(session)  # 级联删除消息、图像记录、报告和接诊记录
        profile = db.get(UserProfile, user_id)
        if profile:
            db.delete(profile)
        db.query(Feedback).filter(Feedback.user_id == user_id).delete(synchronize_session=False)
        # Check ORM and database constraints before committing memory removal.
        db.flush()
        with memory_engine().begin() as conn:
            conn.execute(text('DELETE FROM agent_memory WHERE tenant_id=:tenant AND user_id=:user'), scope)
        db.commit()
    except Exception:
        db.rollback()
        raise
    logger.info("user data deleted user_id=%s", user_id)
