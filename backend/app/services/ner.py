"""多通道实体抽取：图谱字典 + AC 自动机 + 模糊匹配融合。

设计要点
========

* **双通道融合**：AC 自动机精确匹配图谱标准症状名及其别名（高性能 O(n)），rapidfuzz 对
  未命中的片段做模糊兜底（容忍口语化表达，如"拉肚子"→"腹泻"）。
* **按长度降序去重叠**：多个命中片段互相包含时保留更长者，避免"出汗"把"盗汗"错误截断。
* **别名对齐**：AC 自动机的值直接是标准症状名，命中别名（"怕冷"）会立即映射到标准名
  （"恶寒"），相当于把 TF-IDF 对齐简化为一次 dict 查表。
* **自动机懒加载 + 常驻缓存**：首次调用时从 Neo4j 拉取症状名/别名并构建自动机，之后复用。
  图谱拓扑不会在运行时高频变更，这种一次性构建是安全的。
"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any, Iterable, Optional

import ahocorasick
from rapidfuzz import fuzz, process

from app.core import neo4j_client

logger = logging.getLogger("app.ner")

# 模糊匹配阈值（0~100），低于此分的候选直接丢弃
_FUZZ_THRESHOLD = 72


class _Automaton:
    """对 ahocorasick.Automaton 的薄封装，提供匹配+去重叠+对齐标准名的一站式接口。"""

    def __init__(self, symmap: dict[str, str]):
        """
        :param symmap: {匹配串: 标准名}，key 为症状标准名及其所有别名
        """
        self._auto = ahocorasick.Automaton()
        for raw, canonical in symmap.items():
            self._auto.add_word(raw, (raw, canonical))
        self._auto.make_automaton()

    def search(self, text: str) -> list[tuple[int, int, str]]:
        """返回 [(start, end_exclusive, canonical_name), ...]，按 start 升序。"""
        hits: list[tuple[int, int, str]] = []
        for end_idx, (raw, canonical) in self._auto.iter_long(text):
            start = end_idx - len(raw) + 1
            hits.append((start, end_idx + 1, canonical))
        hits.sort(key=lambda h: (h[0], -(h[1] - h[0])))
        return hits


@lru_cache(maxsize=1)
def _build_symptom_automaton() -> Optional[_Automaton]:
    """从 Neo4j 拉取症状标准名 + aliases，构建 AC 自动机。"""
    if not neo4j_client.available():
        return None
    try:
        rows = neo4j_client.run_query(
            "MATCH (s:Symptom) RETURN s.name AS name, s.aliases AS aliases"
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("failed to fetch symptom dictionary: %s", exc)
        return None

    symmap: dict[str, str] = {}
    for r in rows:
        name = r.get("name")
        if not name:
            continue
        symmap[name] = name
        for alias in (r.get("aliases") or []):
            if alias:
                symmap[alias] = name
    if not symmap:
        return None
    return _Automaton(symmap)


def _dedup_by_length(hits: list[tuple[int, int, str]]) -> list[tuple[int, int, str]]:
    """按片段长度降序过滤掉被更长片段完全包含的短命中。"""
    kept: list[tuple[int, int, str]] = []
    for h in hits:
        start, end, _ = h
        contained = any(k[0] <= start and k[1] >= end for k in kept)
        if not contained:
            kept.append(h)
    return kept


def _fuzzy_fill(text: str, automaton: _Automaton, already: Iterable[str]) -> list[str]:
    """对未命中的文本片段做 rapidfuzz 模糊匹配，取 Top-1 且分数过阈值者。"""
    candidates: list[str] = []
    canonical_set: set[str] = set()
    for name, canon in automaton._auto.items():  # 遍历自动机里所有匹配串
        if isinstance(canon, tuple):
            canonical_set.add(canon[1])

    # 粗切分：2~4 字的连续片段
    ngrams: set[str] = set()
    for size in (2, 3, 4):
        for i in range(len(text) - size + 1):
            piece = text[i:i + size].strip()
            if len(piece) >= 2:
                ngrams.add(piece)

    already_set = set(already)
    for piece in sorted(ngrams, key=len, reverse=True):
        if piece in already_set:
            continue
        try:
            match = process.extractOne(
                piece, list(canonical_set), scorer=fuzz.partial_ratio, score_cutoff=_FUZZ_THRESHOLD
            )
        except Exception:  # noqa: BLE001
            match = None
        if match and match[1] >= _FUZZ_THRESHOLD and match[0] not in already_set:
            candidates.append(match[0])
            already_set.add(match[0])
    return candidates


def extract_symptoms(text: str) -> list[str]:
    """从自由文本中抽取图谱症状实体（多通道融合 + 去重 + 长度降序）。

    返回值是症状**标准名**列表，已按出现位置排序；同一标准名只出现一次。
    """
    if not text or not text.strip():
        return []

    auto = _build_symptom_automaton()
    if auto is None:
        # 图谱不可用时的最小降级：返回空列表，让上层知道实体抽取不可靠
        return []

    hits = auto.search(text)
    kept = _dedup_by_length(hits)

    canonical_ordered: list[str] = []
    seen: set[str] = set()
    for _, _, canon in kept:
        if canon not in seen:
            canonical_ordered.append(canon)
            seen.add(canon)

    # 模糊兜底：当精确命中不足时尝试 rapidfuzz
    if len(canonical_ordered) < 2:
        fuzzy = _fuzzy_fill(text, auto, canonical_ordered)
        for f in fuzzy:
            if f not in seen:
                canonical_ordered.append(f)
                seen.add(f)

    return canonical_ordered


def flush_cache() -> None:
    """当图谱症状字典发生变更时调用，强制重建 AC 自动机。"""
    _build_symptom_automaton.cache_clear()
