"""Deterministic proposals from background fields; never auto-save diagnoses."""
FIELDS = {
    "allergies": ("过敏史", ("allergies", "allergy", "过敏史")),
    "chronic_diseases": ("既往病史", ("chronic_diseases", "conditions", "medical_history", "既往史", "慢性病")),
    "medication_history": ("长期用药", ("medication_history", "medication", "medications", "长期用药")),
}


def collect_candidates(profile, snapshots, saved):
    candidates = {}
    sources = [(profile, "健康画像")] + [(slots, f"问诊 {sid} 的信息整理（请核实）") for sid, slots in snapshots]
    existing = {r["memory_key"]: r["value"].get("content", "") for r in saved}
    for data, source in sources:
        for key, (title, aliases) in FIELDS.items():
            if key in candidates:
                continue
            for alias in aliases:
                value = data.get(alias)
                if isinstance(value, list) and all(isinstance(x, str) for x in value):
                    value = "、".join(value)
                if not isinstance(value, str) or not value.strip():
                    continue
                if value.strip() in {"不清楚", "暂不提供", "未知", "有（请补充病史）", "有（请补充药名）"}:
                    continue
                content = f"{title}：{value.strip()}"[:2000]
                candidates[key] = {"key": key, "content": content, "source": source,
                                   "previous": existing.get(key)}
                break
    return [r for r in candidates.values() if r["content"] != r["previous"]]
