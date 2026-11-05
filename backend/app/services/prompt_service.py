"""提示词版本管理：场景化模板的默认内容与 DB 化存取的唯一事实来源。"""
import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.models.entities import PromptVersion, SystemConfig

logger = logging.getLogger("app.prompt")

SCENES = ["inspection", "inquiry", "syndrome", "treatment", "safety"]

# 默认提示词模板（首次建仓用；之后以 DB 为准）
# 三重防幻觉锁：指令层（必须基于输入）+ 提示层空值兜底 + 注意层重复强调
DEFAULT_PROMPTS: dict[str, str] = {
    "inspection": (
        "<指令>你是中医健康助手（非执业医师），基于给定识别结果做通俗解读。</指令>\n"
        "<提示>识别结果：{recognition}</提示>\n"
        "<注意>1) 识别结果中未出现的字段必须用「暂不明确」，禁止编造。2) 措辞使用「可能提示」「倾向于」，禁止确定性诊断。"
        "3) 禁止处方剂量。4) 禁止使用超出识别结果的推断。</注意>"
    ),
    "inquiry": (
        "<指令>你是中医健康助手，基于「十问歌」围绕主诉结构化追问，收集四诊信息。</指令>\n"
        "<提示>已有槽位：{slots}；本轮用户输入：{message}。</提示>\n"
        "<注意>1) 每轮只追问 1~2 个缺失项，禁止一次列出问卷。2) 性别、年龄若仍缺失优先确认。"
        "3) 用户回复「不清楚/不知道/暂不提供」视为该槽位已回应，保留不确定性。"
        "4) 所有追问必须来自槽位缺口，禁止凭空生成问题。5) 输出严格 JSON："
        "{{\"slots\": {{...}}, \"reply\": \"...\", \"ready\": false}}。</注意>"
    ),
    "syndrome": (
        "<指令>你是中医健康助手（非执业医师），基于四诊合参做辨证分析，输出严格 JSON。</指令>\n"
        "<提示>输入证据：{context}</提示>\n"
        "<注意>1) 证据来源必须逐一对应输入中的舌象/面色/主诉/兼症，禁止编造未识别到的症状。"
        "2) 若输入中无明确证据支撑某个证型，该证型不得进入候选项。"
        "3) 置信度必须与证据充分程度一致（证据少=低置信度）。"
        "4) 输出严格 JSON：{{\"syndrome\": \"证型名\", \"evidence\": [{{\"source\": \"舌象|面色|主诉|兼症\", "
        "\"description\": \"依据描述\"}}], \"differential\": [\"鉴别证型\"], \"confidence\": 0.0~1.0}}。</注意>"
    ),
    "treatment": (
        "<指令>你是中医健康助手（非执业医师），基于证型给出养身调养建议（仅供科普）。</指令>\n"
        "<提示>证型：{syndrome}；可用知识：{knowledge}</提示>\n"
        "<注意>1) 方剂只能引用「可用知识」中出现的真实成方，禁止编造方剂名、出处、效应。"
        "2) 图谱返回「图谱中暂未找到直接匹配」时，方剂字段必须为空数组，只能给饮食/起居建议。"
        "3) 禁止任何剂量处方、药物相互作用提示请转诊。4) 必须注明「请勿自行抓药，线下就诊」。"
        "5) 输出严格 JSON：{{\"treatment_principle\": \"治法\", \"formula_suggestions\": [...], "
        "\"diet_advice\": [...], \"acupoint_advice\": [...], \"lifestyle_advice\": []}}。</注意>"
    ),
    "safety": (
        "<指令>你是医疗内容安全审查员，判断文本是否越权。</指令>\n"
        "<提示>待审文本：{text}</提示>\n"
        "<注意>1) 急危重症：胸痛、呼吸困难、意识障碍、高热惊厥、急性剧烈腹痛、大出血、孕产妇急症、自伤自杀。"
        "2) 确定性诊断措辞（如「你得了××病」「这就是××」）。"
        "3) 处方剂量（单位+数值+频次）。"
        "4) 色情暴力无关内容。5) 输出严格 JSON：{{\"risk\": \"emergency|block|pass\", "
        "\"hit_rule\": \"命中规则或空\"}}。</注意>"
    ),
}


def ensure_prompts(db: Session) -> None:
    """启动时幂等建仓：每个场景若无 active 版本，则以默认模板创建 v1。"""
    for scene in SCENES:
        active = (
            db.query(PromptVersion)
            .filter(PromptVersion.scene == scene, PromptVersion.status == "active")
            .first()
        )
        if active is None:
            db.add(PromptVersion(
                scene=scene, version="v1", content=DEFAULT_PROMPTS[scene] if scene != "safety" else DEFAULT_PROMPTS["safety"],
                status="active", changelog="初始默认版本"
            ))
    db.commit()


def get_active_prompt(db: Session, scene: str) -> str:
    p = (
        db.query(PromptVersion)
        .filter(PromptVersion.scene == scene, PromptVersion.status == "active")
        .order_by(PromptVersion.version_id.desc())
        .first()
    )
    if p:
        return p.content
    return DEFAULT_PROMPTS.get(scene, "")


def get_active_prompt_version(db: Session, scene: str) -> str:
    p = (
        db.query(PromptVersion)
        .filter(PromptVersion.scene == scene, PromptVersion.status == "active")
        .order_by(PromptVersion.version_id.desc())
        .first()
    )
    return p.version if p else "default"


def get_disclaimer(db: Session) -> str:
    """免责声明：DB 可覆盖，否则用环境变量默认值。"""
    from app.core.config import settings

    cfg = db.get(SystemConfig, "disclaimer.text")
    if cfg and cfg.config_value:
        return cfg.config_value
    return settings.disclaimer_text


def get_config(db: Session, key: str, default: Optional[str] = None) -> Optional[str]:
    cfg = db.get(SystemConfig, key)
    return cfg.config_value if cfg and cfg.config_value is not None else default
