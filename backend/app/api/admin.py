"""管理后台路由（role=ADMIN）：审计日志、图谱统计/导入、提示词版本、评测。"""
import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core.database import get_db
from app.core.logging import get_trace_id
from app.models.entities import (
    AsyncJob,
    EvalDataset,
    EvalRun,
    OperationLog,
    PromptVersion,
    SafetyAuditLog,
    User,
)
from app.schemas.schemas import (
    AuditLogOut,
    EvalDatasetOut,
    EvalRunOut,
    EvalRunRequest,
    GraphStats,
    OperationLogOut,
    Paginated,
    PromptCreate,
    PromptOut,
)
from app.services import knowledge_service, safety_service

logger = logging.getLogger("app.admin")
router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/graph/stats", response_model=GraphStats)
def graph_stats(db: Session = Depends(get_db)):
    return GraphStats(**knowledge_service.stats())


@router.post("/graph/import")
def graph_import(db: Session = Depends(get_db)):
    job_id = uuid4().hex
    db.add(AsyncJob(job_id=job_id, job_type="graph_import", status="pending", progress=0,
                    params={}, trace_id=get_trace_id()))
    db.commit()
    from app.tasks.jobs import graph_import_task

    graph_import_task.delay(job_id=job_id)
    return {"job_id": job_id}


@router.post("/graph/vector-rebuild")
def vector_rebuild(db: Session = Depends(get_db)):
    job_id = uuid4().hex
    db.add(AsyncJob(job_id=job_id, job_type="vector_rebuild", status="pending", progress=0,
                    params={}, trace_id=get_trace_id()))
    db.commit()
    from app.tasks.jobs import vector_rebuild_task

    vector_rebuild_task.delay(job_id=job_id)
    return {"job_id": job_id}


@router.get("/auditlogs", response_model=Paginated)
def audit_logs(page: int = 1, page_size: int = 20, db: Session = Depends(get_db)):
    total = db.query(func.count(SafetyAuditLog.log_id)).scalar()
    rows = (
        db.query(SafetyAuditLog)
        .order_by(SafetyAuditLog.create_time.desc())
        .offset((page - 1) * page_size).limit(page_size).all()
    )
    items = [AuditLogOut(
        log_id=r.log_id, session_id=r.session_id, stage=r.stage,
        check_result=r.check_result, hit_rule=r.hit_rule, raw_text=r.raw_text,
        action=r.action, create_time=r.create_time,
    ) for r in rows]
    return Paginated(items=items, total=total)


@router.get("/operationlogs", response_model=Paginated)
def operation_logs(page: int = 1, page_size: int = 20, db: Session = Depends(get_db)):
    total = db.query(func.count(OperationLog.op_id)).scalar()
    rows = (
        db.query(OperationLog)
        .order_by(OperationLog.create_time.desc())
        .offset((page - 1) * page_size).limit(page_size).all()
    )
    items = [OperationLogOut(
        op_id=r.op_id, user_id=r.user_id, action=r.action, resource_type=r.resource_type,
        resource_id=r.resource_id, result=r.result, ip=r.ip, trace_id=r.trace_id,
        create_time=r.create_time,
    ) for r in rows]
    return Paginated(items=items, total=total)


@router.get("/prompts", response_model=list[PromptOut])
def list_prompts(db: Session = Depends(get_db)):
    rows = db.query(PromptVersion).order_by(PromptVersion.create_time.desc()).all()
    return [PromptOut(
        version_id=r.version_id, scene=r.scene, version=r.version,
        status=r.status, changelog=r.changelog, create_time=r.create_time,
    ) for r in rows]


@router.post("/prompts", response_model=PromptOut)
def create_prompt(data: PromptCreate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    count = db.query(func.count(PromptVersion.version_id)).filter(PromptVersion.scene == data.scene).scalar()
    version = f"v{count + 1}"
    p = PromptVersion(
        scene=data.scene, version=version, content=data.content,
        status="draft", changelog=data.changelog, operator_id=admin.user_id,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return PromptOut(version_id=p.version_id, scene=p.scene, version=p.version,
                     status=p.status, changelog=p.changelog, create_time=p.create_time)


@router.post("/prompts/{version_id}/activate")
def activate_prompt(version_id: int, db: Session = Depends(get_db)):
    p = db.get(PromptVersion, version_id)
    if not p:
        raise HTTPException(status_code=404, detail="版本不存在")
    # 同场景其它 active 退为 retired
    db.query(PromptVersion).filter(PromptVersion.scene == p.scene, PromptVersion.status == "active").update({"status": "retired"})
    p.status = "active"
    db.commit()
    return {"status": "ok", "version": p.version}


@router.get("/evals", response_model=list[EvalDatasetOut])
def list_evals(db: Session = Depends(get_db)):
    rows = db.query(EvalDataset).all()
    return [EvalDatasetOut(
        dataset_id=r.dataset_id, name=r.name, scene=r.scene,
        sample_count=len(r.samples) if isinstance(r.samples, list) else 0,
    ) for r in rows]


@router.post("/evals/run", response_model=EvalRunOut)
def run_eval(data: EvalRunRequest, db: Session = Depends(get_db)):
    ds = db.get(EvalDataset, data.dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="评测集不存在")
    metrics = _evaluate(ds.samples)
    run = EvalRun(dataset_id=ds.dataset_id, metrics=metrics)
    db.add(run)
    db.commit()
    db.refresh(run)
    return EvalRunOut(run_id=run.run_id, dataset_id=run.dataset_id,
                      prompt_version=run.prompt_version, metrics=run.metrics, create_time=run.create_time)


@router.get("/evals/runs", response_model=list[EvalRunOut])
def list_eval_runs(db: Session = Depends(get_db)):
    rows = db.query(EvalRun).order_by(EvalRun.create_time.desc()).limit(100).all()
    return [EvalRunOut(run_id=r.run_id, dataset_id=r.dataset_id,
                       prompt_version=r.prompt_version, metrics=r.metrics, create_time=r.create_time) for r in rows]


def _evaluate(samples: list) -> dict:
    """护栏评测：对每个样本跑输入层护栏，对比期望标签，统计准确率/召回。"""
    if not samples:
        return {"accuracy": 0.0, "recall": 0.0, "precision": 0.0, "total": 0}
    tp = fp = tn = fn = 0
    for s in samples:
        text = s.get("text", "")
        expected = s.get("risk", "pass")  # pass / emergency
        res = _safe_check_without_db(text)
        predicted = "emergency" if res == "emergency" else "pass"
        if expected == "emergency" and predicted == "emergency":
            tp += 1
        elif expected == "emergency":
            fn += 1
        elif predicted == "emergency":
            fp += 1
        else:
            tn += 1
    total = len(samples)
    accuracy = (tp + tn) / total
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    return {"accuracy": round(accuracy, 4), "recall": round(recall, 4),
            "precision": round(precision, 4), "total": total}


def _safe_check_without_db(text: str) -> str:
    for kw in safety_service.RED_FLAG_PATTERNS:
        if kw in text:
            return "emergency"
    return "pass"