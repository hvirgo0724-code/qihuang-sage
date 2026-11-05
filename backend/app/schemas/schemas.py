"""Pydantic v2 输入/输出 Schema（与前端契约、图谱字段严格对齐）。"""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------- 认证 ----------------
class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    nickname: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[int] = Field(default=None, ge=0, le=150)
    consent: bool = False


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    user_id: int
    username: str
    nickname: Optional[str] = None
    avatar: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[int] = None
    role: str = "USER"
    tenant_id: int = 0
    data_consent_at: Optional[datetime] = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: UserOut


class ProfileUpdate(BaseModel):
    height: Optional[float] = None
    weight: Optional[float] = None
    allergies: Optional[str] = None
    chronic_diseases: Optional[str] = None
    medication_history: Optional[str] = None
    remark: Optional[str] = None


class ProfileOut(BaseModel):
    user_id: int
    height: Optional[float] = None
    weight: Optional[float] = None
    allergies: Optional[str] = None
    chronic_diseases: Optional[str] = None
    medication_history: Optional[str] = None
    remark: Optional[str] = None


# ---------------- 问诊 ----------------
class SessionCreate(BaseModel):
    complaint: Optional[str] = None


class SessionOut(BaseModel):
    session_id: int
    status: str
    complaint: Optional[str] = None
    risk_level: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    trace_id: Optional[str] = None
    report_status: Optional[str] = None
    analysis_id: Optional[int] = None


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)


class MessageOut(BaseModel):
    record_id: int
    role: str
    type: str
    content: Optional[str] = None
    meta: Optional[dict] = None
    create_time: datetime


class ImageUploadOut(BaseModel):
    job_id: str
    image_id: int


class JobOut(BaseModel):
    job_id: str
    job_type: str
    status: str
    progress: int = 0
    result: Optional[dict] = None
    error: Optional[str] = None
    trace_id: Optional[str] = None


# ---------------- 辨证报告 ----------------
class EvidenceItem(BaseModel):
    source: str
    description: str
    weight: float = 1.0


class FormulaSuggestion(BaseModel):
    name: str
    source: str
    effects: list[str] = []
    indications: list[str] = []
    contraindications: Optional[str] = None
    dosage_note: Optional[str] = None
    note: str = ""


class GraphRef(BaseModel):
    label: str
    name: str
    source: str
    description: str


class SyndromeReport(BaseModel):
    syndrome: Optional[str] = None
    confidence: Optional[float] = None
    evidence: list[EvidenceItem] = []
    differential: list[str] = []
    treatment_principle: Optional[str] = None
    formula_suggestions: list[FormulaSuggestion] = []
    diet_advice: list[str] = []
    acupoint_advice: list[str] = []
    lifestyle_advice: list[str] = []
    risk_level: str = "low"
    emergency_flag: bool = False
    disclaimer: str = ""
    graph_refs: list[GraphRef] = []


# ---------------- 知识库 ----------------
class SearchItem(BaseModel):
    type: str
    name: str
    title: str
    description: str
    source: str


class SearchResponse(BaseModel):
    items: list[SearchItem]
    total: int


class KnowledgeNode(BaseModel):
    name: str
    label: str
    properties: dict[str, Any] = {}


class Neighbor(BaseModel):
    relation: str
    related: KnowledgeNode


class NodeDetail(BaseModel):
    node: KnowledgeNode
    neighbors: list[Neighbor] = []


class GraphStats(BaseModel):
    herbs: int = 0
    formulas: int = 0
    syndromes: int = 0
    symptoms: int = 0


# ---------------- 反馈 ----------------
class FeedbackCreate(BaseModel):
    analysis_id: Optional[int] = None
    rating: int = Field(ge=1, le=5)
    comment: Optional[str] = None
    correct: Optional[bool] = None


class FeedbackOut(BaseModel):
    feedback_id: int


# ---------------- 管理 ----------------
class AuditLogOut(BaseModel):
    log_id: int
    session_id: Optional[int] = None
    stage: str
    check_result: str
    hit_rule: Optional[str] = None
    raw_text: Optional[str] = None
    action: Optional[str] = None
    create_time: datetime


class OperationLogOut(BaseModel):
    op_id: int
    user_id: Optional[int] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    result: Optional[str] = None
    ip: Optional[str] = None
    trace_id: Optional[str] = None
    create_time: datetime


class Paginated(BaseModel):
    items: list[Any]
    total: int


class PromptOut(BaseModel):
    version_id: int
    scene: str
    version: str
    status: str
    changelog: Optional[str] = None
    create_time: datetime


class PromptCreate(BaseModel):
    scene: str
    content: str
    changelog: Optional[str] = None


class EvalDatasetOut(BaseModel):
    dataset_id: int
    name: str
    scene: Optional[str] = None
    sample_count: int = 0


class EvalRunOut(BaseModel):
    run_id: int
    dataset_id: int
    prompt_version: Optional[str] = None
    metrics: Optional[dict] = None
    create_time: datetime


class EvalRunRequest(BaseModel):
    dataset_id: int


# ---------------- 健康 ----------------
class HealthOut(BaseModel):
    status: str
    version: str = "1.0.0"
