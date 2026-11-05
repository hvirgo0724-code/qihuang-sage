"""SQLAlchemy ORM 实体（与 init/01_schema.sql 严格对齐）。"""
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    BigInteger,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class Tenant(Base):
    __tablename__ = "tenant"

    tenant_id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    status = Column(String(16), nullable=False, default="active")
    quota = Column(JSON)
    create_time = Column(DateTime, default=datetime.now)


class User(Base):
    __tablename__ = "user"

    user_id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(BigInteger, nullable=False, default=0)
    username = Column(String(64), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    phone = Column(Text)          # 加密
    nickname = Column(String(64))
    avatar = Column(String(512))
    gender = Column(String(8))
    age = Column(Integer)
    role = Column(String(16), nullable=False, default="USER")
    status = Column(String(16), nullable=False, default="active")
    data_consent_at = Column(DateTime)
    create_time = Column(DateTime, default=datetime.now)

    profile = relationship("UserProfile", back_populates="user", uselist=False,
                           cascade="all, delete-orphan", passive_deletes=True)


class UserProfile(Base):
    __tablename__ = "user_profile"

    user_id = Column(BigInteger, ForeignKey("user.user_id", ondelete="CASCADE"), primary_key=True)
    height = Column(Float)
    weight = Column(Float)
    allergies = Column(Text)          # 加密
    chronic_diseases = Column(Text)   # 加密
    medication_history = Column(Text) # 加密
    remark = Column(Text)             # 加密

    user = relationship("User", back_populates="profile")


class ConsultationSession(Base):
    __tablename__ = "consultation_session"

    session_id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(BigInteger, nullable=False, default=0)
    user_id = Column(BigInteger, ForeignKey("user.user_id", ondelete="CASCADE"), nullable=False)
    start_time = Column(DateTime, default=datetime.now)
    end_time = Column(DateTime)
    status = Column(String(16), nullable=False, default="ongoing")
    complaint = Column(Text)
    risk_level = Column(String(16))
    trace_id = Column(String(64))


class ConsultationRecord(Base):
    __tablename__ = "consultation_record"

    record_id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(BigInteger, ForeignKey("consultation_session.session_id", ondelete="CASCADE"), nullable=False)
    role = Column(String(16), nullable=False)
    type = Column(String(16), nullable=False, default="text")
    content = Column(Text)
    meta = Column(JSON)
    create_time = Column(DateTime, default=datetime.now)


class TcmImage(Base):
    __tablename__ = "tcm_image"

    image_id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(BigInteger, ForeignKey("consultation_session.session_id", ondelete="CASCADE"), nullable=False)
    image_type = Column(String(16), nullable=False)
    file_path = Column(String(512), nullable=False)
    quality_pass = Column(Boolean, default=False)
    analysis_result = Column(JSON)
    create_time = Column(DateTime, default=datetime.now)


class SyndromeAnalysis(Base):
    __tablename__ = "syndrome_analysis"

    analysis_id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(BigInteger, ForeignKey("consultation_session.session_id", ondelete="CASCADE"), nullable=False)
    syndrome = Column(String(128))
    evidence = Column(JSON)
    differential = Column(JSON)
    confidence = Column(Float)
    treatment_principle = Column(String(512))
    formula_suggestions = Column(JSON)
    diet_advice = Column(JSON)
    acupoint_advice = Column(JSON)
    lifestyle_advice = Column(JSON)
    risk_level = Column(String(16))
    emergency_flag = Column(Boolean, default=False)
    disclaimer = Column(Text)
    graph_refs = Column(JSON)
    model_name = Column(String(64))
    prompt_version = Column(String(32))
    latency_ms = Column(Integer)
    create_time = Column(DateTime, default=datetime.now)


class ReportReview(Base):
    __tablename__ = "report_review"

    analysis_id = Column(BigInteger, ForeignKey("syndrome_analysis.analysis_id", ondelete="CASCADE"), primary_key=True)
    status = Column(String(16), nullable=False, default="pending")
    revision = Column(Integer, nullable=False, default=1)
    report = Column(JSON, nullable=False)
    confirmed_by = Column(BigInteger)
    confirmed_at = Column(DateTime)


class SafetyAuditLog(Base):
    __tablename__ = "safety_audit_log"

    log_id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(BigInteger)
    stage = Column(String(16), nullable=False)
    check_result = Column(String(16), nullable=False)
    hit_rule = Column(String(128))
    raw_text = Column(Text)
    action = Column(String(64))
    create_time = Column(DateTime, default=datetime.now)


class OperationLog(Base):
    __tablename__ = "operation_log"

    op_id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger)
    tenant_id = Column(BigInteger, nullable=False, default=0)
    action = Column(String(64), nullable=False)
    resource_type = Column(String(64), nullable=False)
    resource_id = Column(String(64))
    result = Column(String(16))
    ip = Column(String(64))
    trace_id = Column(String(64))
    create_time = Column(DateTime, default=datetime.now)


class Feedback(Base):
    __tablename__ = "feedback"

    feedback_id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("user.user_id", ondelete="CASCADE"), nullable=False)
    analysis_id = Column(BigInteger)
    rating = Column(Integer, nullable=False)
    comment = Column(Text)
    correct = Column(Boolean)
    create_time = Column(DateTime, default=datetime.now)


class AsyncJob(Base):
    __tablename__ = "async_job"

    job_id = Column(String(64), primary_key=True)
    job_type = Column(String(32), nullable=False)
    status = Column(String(16), nullable=False, default="pending")
    progress = Column(Integer, default=0)
    params = Column(JSON)
    result = Column(JSON)
    error = Column(Text)
    trace_id = Column(String(64))
    create_time = Column(DateTime, default=datetime.now)
    finish_time = Column(DateTime)


class PromptVersion(Base):
    __tablename__ = "prompt_version"

    version_id = Column(BigInteger, primary_key=True, autoincrement=True)
    scene = Column(String(32), nullable=False)
    version = Column(String(32), nullable=False)
    content = Column(Text, nullable=False)
    status = Column(String(16), nullable=False, default="draft")
    changelog = Column(Text)
    operator_id = Column(BigInteger)
    create_time = Column(DateTime, default=datetime.now)


class EvalDataset(Base):
    __tablename__ = "eval_dataset"

    dataset_id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    scene = Column(String(32))
    samples = Column(JSON, nullable=False)
    create_time = Column(DateTime, default=datetime.now)


class EvalRun(Base):
    __tablename__ = "eval_run"

    run_id = Column(BigInteger, primary_key=True, autoincrement=True)
    dataset_id = Column(BigInteger, nullable=False)
    prompt_version = Column(String(32))
    metrics = Column(JSON)
    create_time = Column(DateTime, default=datetime.now)


class SystemConfig(Base):
    __tablename__ = "system_config"

    config_key = Column(String(64), primary_key=True)
    config_value = Column(Text)
    description = Column(String(255))
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class ClinicalEncounter(Base):
    __tablename__ = "clinical_encounter"
    session_id = Column(BigInteger, ForeignKey("consultation_session.session_id", ondelete="CASCADE"), primary_key=True)
    tenant_id = Column(BigInteger, nullable=False, default=0, index=True)
    patient_id = Column(BigInteger, ForeignKey("user.user_id", ondelete="CASCADE"), nullable=False)
    doctor_id = Column(BigInteger, ForeignKey("user.user_id"), nullable=False, index=True)
    status = Column(String(16), nullable=False, default="requested")
    consent_at = Column(DateTime, default=datetime.now)
    accepted_at = Column(DateTime)
    closed_at = Column(DateTime)
    review = Column(Text)
    reviewed_at = Column(DateTime)


class ClinicalMessage(Base):
    __tablename__ = "clinical_message"
    message_id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    session_id = Column(BigInteger, ForeignKey("clinical_encounter.session_id", ondelete="CASCADE"), nullable=False, index=True)
    author_id = Column(BigInteger, ForeignKey("user.user_id", ondelete="CASCADE"), nullable=False)
    author_role = Column(String(16), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
