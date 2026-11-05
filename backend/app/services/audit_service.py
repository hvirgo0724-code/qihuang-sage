"""操作审计：记录「谁在何时对何数据做了什么」，占用 trace_id。"""
import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.core.logging import get_trace_id, tenant_id_var, user_id_var
from app.models.entities import OperationLog

logger = logging.getLogger("app.audit")


def record(
    db: Session,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    result: Optional[str] = "success",
    ip: Optional[str] = None,
) -> None:
    uid = user_id_var.get() or None
    tid = tenant_id_var.get() or "0"
    db.add(OperationLog(
        user_id=int(uid) if uid else None,
        tenant_id=int(tid),
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        result=result,
        ip=ip,
        trace_id=get_trace_id(),
    ))
    db.commit()