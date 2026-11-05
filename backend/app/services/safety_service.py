"""医疗内容安全护栏：输入层（急危重症/越权/无关诉求）、输出层（确定性诊断/剂量/免责）。"""
import json
import logging
from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from app.core import llm
from app.core.logging import get_trace_id, session_id_var
from app.core.metrics import SAFETY_CHECK_COUNT
from app.core.security import mask_text
from app.models.entities import SafetyAuditLog

logger = logging.getLogger("app.safety")

# 急危重症红线（规则为主，命中即 emergency）
RED_FLAG_PATTERNS = [
    "胸痛", "胸闷剧烈", "呼吸困难", "喘不上气", "喘不过气", "气促", "窒息",
    "意识障碍", "昏迷", "晕厥", "抽搐", "高热惊厥", "剧烈腹痛", "大出血",
    "呕血", "咯血", "便血", "孕产妇急症", "胎动异常", "想自杀", "自伤",
    "不想活", "自杀", "偏瘫", "口角歪斜", "半身不遂", "心梗", "心绞痛", "脑梗",
    "心肌梗死", "急性", "休克", "窒息", "濒死",
]

# 输出层禁止的确定性诊断措辞
FORBIDDEN_OUTPUT = ["确诊", "你得了", "你患有", "诊断结果为", "一定是", "绝对是"]
# 输出层禁止的处方级措辞
FORBIDDEN_DOSE = ["每日", "每次", "口服", "煎服", "克", "g", "剂量为", "处方"]


@dataclass
class SafetyResult:
    stage: str
    result: str  # pass / block / escalate / emergency
    hit_rule: Optional[str] = None
    action: Optional[str] = None


def check_input(text: str, db: Session) -> SafetyResult:
    """输入层护栏：急危重症 -> emergency；越权/无关 -> block；否则 pass。"""
    if not text:
        return SafetyResult("input", "pass")
    for kw in RED_FLAG_PATTERNS:
        if kw in text:
            res = SafetyResult("input", "emergency", hit_rule=f"急危重症识别:{kw}", action="引导立即就医")
            _audit(db, res, text)
            return res
    # 越权诱导 / 无关诉求
    if any(k in text for k in ["开个治癌症的方子", "给我配药", "开药方", "治癌症", "治愈癌症"]):
        res = SafetyResult("input", "block", hit_rule="诱导越权用药", action="引导回医疗咨询边界")
        _audit(db, res, text)
        return res
    _audit(db, SafetyResult("input", "pass"), text)
    return SafetyResult("input", "pass")


def check_output(text: str, db: Session) -> SafetyResult:
    """输出层护栏：确定性诊断/处方剂量措辞 -> block 以触发重写；否则 pass。"""
    for w in FORBIDDEN_OUTPUT:
        if w in text:
            res = SafetyResult("output", "block", hit_rule=f"确定性诊断措辞:{w}", action="重写")
            _audit(db, res, text)
            return res
    # 剂量：仅在疑似处方语境下拦截，科普剂量说明允许（方剂建议不再给具体克数，故严格拦截数字+克）
    import re
    if re.search(r"\d+\s*克", text) or any(k in text for k in ["每日服用", "每次服用"]):
        res = SafetyResult("output", "block", hit_rule="处方级剂量", action="重写")
        _audit(db, res, text)
        return res
    _audit(db, SafetyResult("output", "pass"), text)
    return SafetyResult("output", "pass")


def _audit(db: Session, res: SafetyResult, raw_text: str) -> None:
    SAFETY_CHECK_COUNT.labels(res.stage, res.result).inc()
    sprime_id = session_id_var.get() or None
    entry = SafetyAuditLog(
        session_id=int(sprime_id) if sprime_id else None,
        stage=res.stage,
        check_result=("emergency" if res.result == "emergency" else res.result),
        hit_rule=res.hit_rule,
        raw_text=mask_text(raw_text)[:500],
        action=res.action,
    )
    db.add(entry)
    db.commit()


def emergency_guidance() -> str:
    return (
        "【紧急提示】根据你的描述，出现了需要立即就医的征象。请立即拨打 120 或前往最近的医院急诊科，"
        "不要自行处理、不要拖延。本系统无法提供急危重症的诊断与处置建议。"
    )


def low_confidence_note() -> str:
    return "（图像识别仅供参考，置信度不足，已引导以口述症状为准。）"