"""认证与数据权利路由。"""
from uuid import uuid4

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.logging import get_trace_id
from app.models.entities import AsyncJob, User
from app.schemas.schemas import (
    LoginRequest,
    ProfileOut,
    ProfileUpdate,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
)
from app.services import audit_service, auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    return auth_service.register(db, data)


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db), request: Request = None):
    tokens = auth_service.login(db, data)
    audit_service.record(db, "login", "user", str(tokens.user.user_id), ip=_client_ip(request))
    return tokens


@router.post("/refresh", response_model=TokenResponse)
def refresh(data: RefreshRequest, db: Session = Depends(get_db)):
    return auth_service.refresh(db, data.refresh_token)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return auth_service._user_out(user)


@router.get("/me/profile", response_model=ProfileOut)
def get_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return auth_service.get_profile(db, user.user_id)


@router.put("/me/profile", response_model=ProfileOut)
def update_profile(
    data: ProfileUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = auth_service.update_profile(db, user.user_id, data)
    audit_service.record(db, "update", "user_profile", str(user.user_id))
    return result


@router.delete("/me/data")
def delete_data(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    auth_service.delete_user_data(db, user.user_id)
    audit_service.record(db, "delete", "user_health_data", str(user.user_id))
    return {"status": "ok"}


@router.post("/me/export")
def export_data(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """数据导出权：异步导出个人健康数据，返回任务 ID 用于轮询 /jobs/{job_id}。"""
    job_id = uuid4().hex
    db.add(AsyncJob(job_id=job_id, job_type="export", status="pending", progress=0,
                    params={}, trace_id=get_trace_id()))
    db.commit()
    from app.tasks.jobs import export_task

    export_task.delay(job_id=job_id, user_id=user.user_id)
    audit_service.record(db, "export", "user", str(user.user_id))
    return {"job_id": job_id}


def _client_ip(request: Request) -> str:
    return request.client.host if request and request.client else ""
