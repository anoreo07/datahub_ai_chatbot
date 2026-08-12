"""Complexity classifier for Thinking Mode.

Decides whether a question is complex enough (system-level, multi-entity,
multi-hop, cross-domain, comparative, planning, multi-constraint) to warrant
the Thinking Mode planner instead of the single-intent fast path.

Deterministic and data-grounded (no LLM dependency): scores weighted lexical
and structural features, then routes a question into Thinking Mode only when
it clearly needs multi-step, multi-source reasoning. Simple single-intent
questions (one entity, one ask) are routed out.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import structlog

from retrieval.thinking.models import KnowledgeSource

log = structlog.get_logger()


@dataclass
class ComplexityVerdict:
    complex: bool = False
    reasons: list[str] = field(default_factory=list)
    sources: list[KnowledgeSource] = field(default_factory=list)
    entity_mentions: list[str] = field(default_factory=list)
    intent_hint: str = "THINKING_GENERAL"


_COMPARE_RE = re.compile(
    r"\b(?:so sánh|so sanh|so với|so voi|compare|comparison|comparing|better|"
    r"recommend|nên dùng|nen dung|phù hợp|phu hop|should (?:use|pick)|"
    r"choose|chọn|chon|lựa chọn|lua chon|versus|\bvs\.?)\b",
    re.I,
)

_OVERVIEW_RE = re.compile(
    r"\b(?:tổng quan|tong quan|overview|kiến trúc|kien truc|architecture|"
    r"coverage|phan bo|fan[- ]?out|fan[- ]?in|toàn hệ thống|toan he thong|"
    r"tổng thể|tong the|overall|landscape|số lượng)\b",
    re.I,
)

_DELETE_RE = re.compile(r"\b(?:xóa|xoá|delete|drop|remove|thay đổi|thay doi|thay)\b", re.I)
_IMPACT_RE = re.compile(
    r"\b(?:ảnh hưởng|anh huong|impact|downstream|được dùng|duoc dung|"
    r"consumer|hỏng|hong|lỗi|loi|bị)\b",
    re.I,
)

_CROSS_DOMAIN_RE = re.compile(
    r"\b(?:cross[- ]domain|chéo|cheo|giữa các domain|giua cac domain|"
    r"liên (?:đến|các) domain|lien (?:den|cac) domain|đa domain|da domain)\b",
    re.I,
)

_PLANNING_RE = re.compile(
    r"\b(?:xây dựng|xa y dung|build|tạo ra|dashboard|pipeline|etl|quy trình|quy trinh)\b",
    re.I,
)

_QUALITY_RE = re.compile(
    r"\b(?:chất lượng|chat luong|quality|kém|kem|sạch|sach)\b",
    re.I,
)

_OWNER_RE = re.compile(r"\b(?:owner|thuộc sở hữu|thuoc so huu)\b", re.I)
_OWNERLESS_RE = re.compile(r"\b(?:thiếu owner|thieu owner|missing owner|không có owner)\b", re.I)

_GLOSSARY_RE = re.compile(r"\b(?:glossary|terms?|khái niệm|khai niem|thuật ngữ|thuat ngu)\b", re.I)
_SCHEMA_RE = re.compile(r"\b(?:schema|fields?|column|cột|cot|join key|khóa nối|khoa noi)\b", re.I)
_LINEAGE_RE = re.compile(r"\b(?:lineage|upstream|downstream|nguồn|nguon)\b", re.I)
_DOC_RE = re.compile(r"\b(?:document|tài liệu|tai lieu)\b", re.I)
_PERMISSION_RE = re.compile(r"\b(?:permission|quyền|quyen|access|acl|authorization)\b", re.I)
_DOWNSTREAM_RE = re.compile(r"\b(?:downstream|được dùng|duoc dung|consumer)\b", re.I)
_UPSTREAM_RE = re.compile(r"\b(?:upstream|nguồn dữ liệu|nguon)\b", re.I)

_CROSS_REF_RE = re.compile(
    r"(?=.*\b(?:term|glossary|dashboard)\b)(?=.*\b(?:dataset|bang|domain)\b)",
    re.I,
)


def _gather_sources(question: str) -> list[KnowledgeSource]:
    out: list[KnowledgeSource] = []
    for pattern, src in [
        (_GLOSSARY_RE, KnowledgeSource.GLOSSARY),
        (_SCHEMA_RE, KnowledgeSource.SCHEMA_FIELD),
        (_LINEAGE_RE, KnowledgeSource.LINEAGE),
        (_QUALITY_RE, KnowledgeSource.DATA_QUALITY),
        (_OWNER_RE, KnowledgeSource.OWNER),
        (_DOC_RE, KnowledgeSource.DOCUMENT),
        (_PERMISSION_RE, KnowledgeSource.PERMISSION),
        (_DOWNSTREAM_RE, KnowledgeSource.DOWNSTREAM),
        (_UPSTREAM_RE, KnowledgeSource.UPSTREAM),
    ]:
        if pattern.search(question) and src not in out:
            out.append(src)
    return out


def _hint(compare: bool, overview: bool, whatif: bool,
          cross: bool, planning: bool) -> str:
    if compare:
        return "THINKING_COMPARISON"
    if overview:
        return "THINKING_OVERVIEW"
    if whatif:
        return "THINKING_IMPACT"
    if cross:
        return "THINKING_CROSS_DOMAIN"
    if planning:
        return "THINKING_PLANNING"
    return "THINKING_GENERAL"


class ComplexityClassifier:
    def evaluate(
        self, question: str, entity_mentions: list[str] | None = None
    ) -> ComplexityVerdict:
        mentions = [m for m in (entity_mentions or []) if (m or "").strip()]
        reasons: list[str] = []
        score = 0

        compare = bool(_COMPARE_RE.search(question))
        overview = bool(_OVERVIEW_RE.search(question))
        whatif = bool(_DELETE_RE.search(question) and _IMPACT_RE.search(question))
        cross = bool(_CROSS_DOMAIN_RE.search(question))
        planning = bool(_PLANNING_RE.search(question))
        ownerless = _OWNERLESS_RE.search(question) is not None
        join_key = bool(re.search(r"\bjoin key\b|khóa nối|khoa noi", question, re.I))
        cross_ref = bool(_CROSS_REF_RE.search(question))

        if compare:
            score += 2
            reasons.append("comparison / selection / suitability language")
        if overview:
            score += 2
            reasons.append("system-level overview / architecture")
        if whatif:
            score += 3
            reasons.append("what-if-delete impact question")
        if cross:
            score += 2
            reasons.append("cross-domain linking")
        if planning:
            score += 1
            reasons.append("planning / building language")
        if join_key:
            score += 2
            reasons.append("schema join-key analysis")
        if ownerless and _QUALITY_RE.search(question):
            score += 2
            reasons.append("multi-constraint owner + quality")
        if cross_ref:
            score += 2
            reasons.append("term/domain/dataset cross-reference")
        if cross_ref and (ownerless or compare):
            score += 1
            reasons.append("cross-reference + selection/constraint")

        if mentions:
            score += min(len(mentions), 2)

        dims = 0
        for pat in (_GLOSSARY_RE, _SCHEMA_RE, _LINEAGE_RE, _QUALITY_RE,
                    _DOC_RE, _PERMISSION_RE):
            if pat.search(question):
                dims += 1
        if dims:
            score += min(dims, 3)
            if dims >= 2:
                reasons.append(f"multi knowledge-source ask ({dims} dimensions)")

        sources = _gather_sources(question)
        complex = score >= 3
        verdict = ComplexityVerdict(
            complex=complex,
            reasons=reasons,
            sources=sources,
            entity_mentions=mentions,
            intent_hint=_hint(compare, overview, whatif, cross, planning),
        )
        if complex:
            log.info("thinking_complexity", complex=True, score=score,
                     intent_hint=verdict.intent_hint,
                     question=question[:120], reasons=reasons)
        return verdict


_default_classifier = ComplexityClassifier()


def evaluate_complexity(
    question: str, entity_mentions: list[str] | None = None
) -> ComplexityVerdict:
    return _default_classifier.evaluate(question, entity_mentions=entity_mentions)
