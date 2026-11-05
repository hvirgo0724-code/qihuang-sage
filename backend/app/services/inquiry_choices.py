"""Optional answer aids for topics explicitly asked in the current follow-up.

Choices are observations, never diagnoses. No answer is selected implicitly.
Unmatched questions remain free text; image-derived findings are not re-asked.
"""
import re

TOPICS = [
    ("location", "不适部位", r"部位|哪里|哪儿", ["头部", "咽喉", "胸部", "胃部", "腹部", "腰部", "关节", "全身"]),
    ("sensation", "不适感受", r"什么样的不适|不适.*感|胀、痛|疼痛性质|胀痛|刺痛|昏沉|紧绷", ["胀痛", "刺痛", "昏沉", "紧绷", "酸", "闷", "乏力", "头晕"]),
    ("fever", "发热情况", r"发热|发烧|体温", ["没有发热", "感觉发热，未测体温", "已测体温（请补充数值）"]),
    ("mouth", "口腔感受", r"口干|口苦|口黏|口粘", ["无明显异常", "口干", "口苦", "口黏"]),
    ("sex", "性别", r"性别", ["男", "女", "其他", "暂不提供"]),
    ("age", "年龄", r"年龄|几岁|多大年纪", []),
    ("menstruation", "月经情况（适用时填写）", r"月经|痛经", ["规律", "不规律", "痛经", "已绝经", "不适用"]),
    ("conditions", "既往史", r"慢性病|既往.*(?:病|史|高血压|偏头痛)|基础疾病|类似发作史|头部外伤|手术史", ["无已知相关病史", "有（请补充病史）"]),
    ("medication", "长期用药", r"服用.*药|用药|药物", ["无长期用药", "有（请补充药名）"]),
    ("duration", "病程", r"病程|多久|多长时间", ["今天开始", "几天", "数周", "数月及以上"]),
    ("cold_hot", "寒热感受", r"怕冷|怕热|寒热", ["怕冷", "怕热", "时冷时热", "无明显异常"]),
    ("sweat", "出汗情况", r"出汗|汗多|盗汗", ["无明显异常", "比平时多", "比平时少", "睡着后出汗"]),
    ("appetite", "食欲", r"饮食|食欲|胃口", ["正常", "食欲下降", "容易饥饿", "进食后不适"]),
    ("sleep", "睡眠", r"睡眠|入睡|失眠", ["正常", "入睡困难", "容易醒", "早醒", "多梦", "嗜睡"]),
    ("stool", "大便", r"二便|大便|排便", ["正常", "干硬或排便困难", "稀软或腹泻", "干稀交替", "黏滞", "次数增多"]),
    ("urine", "小便", r"二便|小便|排尿", ["正常", "次数增多", "量减少", "颜色偏深", "排尿灼热或不适"]),
    ("thirst", "口渴", r"口渴|饮水|口干", ["无明显异常", "口干想喝水", "口干但不想喝水"]),
    ("energy", "精力", r"精力|乏力|疲劳", ["正常", "容易疲劳", "休息后仍疲劳"]),
    ("mood", "情绪", r"情志|情绪|压力", ["平稳", "压力较大", "烦躁", "紧张焦虑", "低落"]),
]


def build_choices(reply: str) -> list[dict]:
    # Only question/request clauses, so summaries do not turn into new questions.
    clauses = re.findall(r"[^。！？!?\n]*[？?]|[^。！？!?\n]*(?:请描述|请补充|请继续描述|请告知|请尽量|请.*说说)[^。！？!?\n]*", reply)
    questions = " ".join(clauses)
    multiple = {"location", "sensation", "mouth", "sweat", "sleep", "stool", "urine", "mood", "menstruation"}
    result = []
    for key, label, pattern, options in TOPICS:
        if not re.search(pattern, questions):
            continue
        result.append({"id": key, "label": label,
                       "options": options + ["不清楚", "其他（请补充）"] if options else [],
                       "multiple": key in multiple,
                       "input_type": "age" if key == "age" else None})
    return result
