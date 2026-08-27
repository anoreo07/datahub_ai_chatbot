"""Domain-scoped glossary answering and disambiguation for concept families."""
from __future__ import annotations

import re
import time
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

import structlog

from retrieval.context_builder import build_context
from retrieval.intent import _norm_vn

if TYPE_CHECKING:
    from app.services.chat.context import ChatContext

log = structlog.get_logger()

# Concept families whose glossary terms must be disambiguated by domain.
GLOSSARY_CONCEPT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "demand": ("demand", "nhu cau linh kien"),
}

TERM_DOMAIN_CACHE: dict[str, Any] = {
    "term_domains": None,
    "built_at": 0.0,
}


async def term_domain_map(entity_repo: Any) -> dict[str, set[str]]:
    """Map glossary-term URN -> canonical dataset domains linking to it."""
    cached = TERM_DOMAIN_CACHE.get("term_domains")
    if cached is not None:
        return cached
    term_domains: dict[str, set[str]] = {}
    try:
        datasets = await entity_repo.list_by_type("dataset", limit=100000)
    except Exception:  # noqa: BLE001
        return term_domains
    for e in datasets:
        pl = e.payload or {}
        dom = (pl.get("domain") or "").strip()
        if not dom:
            continue
        for tu in (pl.get("glossary_terms") or []):
            if not tu:
                continue
            term_domains.setdefault(tu, set()).add(dom)
    TERM_DOMAIN_CACHE["term_domains"] = term_domains
    TERM_DOMAIN_CACHE["built_at"] = time.time()
    return term_domains


async def term_linked_datasets(entity_repo: Any) -> dict[str, list[str]]:
    """Map glossary-term URN -> dataset names (across every domain)."""
    key = "term_datasets"
    cached = TERM_DOMAIN_CACHE.get(key)
    if cached is not None:
        return cached
    term_datasets: dict[str, list[str]] = {}
    try:
        datasets = await entity_repo.list_by_type("dataset", limit=100000)
    except Exception:  # noqa: BLE001
        return term_datasets
    for e in datasets:
        pl = e.payload or {}
        name = (e.name or "").strip()
        if not name:
            continue
        for tu in (pl.get("glossary_terms") or []):
            if not tu:
                continue
            term_datasets.setdefault(tu, []).append(name)
    TERM_DOMAIN_CACHE[key] = term_datasets
    return term_datasets


async def glossary_concept_members(entity_repo: Any, concept: str) -> list[dict[str, Any]]:
    """Glossary terms belonging to a concept family (name, description, URN)."""
    keywords = GLOSSARY_CONCEPT_KEYWORDS.get(concept)
    if not keywords:
        return []
    try:
        terms = await entity_repo.list_by_type("glossary_term", limit=100000)
    except Exception:  # noqa: BLE001
        return []
    out: list[dict[str, Any]] = []
    for t in terms:
        name = (t.name or "").strip()
        if not name:
            continue
        blob = _norm_vn(name)
        if any(k in blob for k in keywords):
            pl = t.payload or {}
            out.append({
                "urn": t.urn,
                "name": name,
                "description": (pl.get("description") or "").strip(),
            })
    return out


async def domain_scoped_term_answer(
    question: str,
    ctx: ChatContext,
    results: Sequence[Any],
) -> tuple[str, list[Any], list[Any], str, str] | None:
    """Domain-scoped glossary answer for a concept family."""
    if not results:
        return None
    q = _norm_vn(question)
    if not re.search(
        r"là gì|la gi|nghĩa|nghia|định nghĩa|dinh nghia|giới thiệu|"
        r"so sánh|so sanh|compare|comparison",
        q,
    ):
        return None
    concept = next(
        (c for c, kws in GLOSSARY_CONCEPT_KEYWORDS.items() if any(k in q for k in kws)),
        None,
    )
    if concept is None:
        return None
    entity_repo = ctx.entity_repo
    members = await glossary_concept_members(entity_repo, concept)
    if not members:
        return None
    t_domains = await term_domain_map(entity_repo)

    domains: list[str] = []
    access = getattr(ctx, "access", None)
    if access is not None:
        try:
            domains = await access.detect_requested_domains(question)
        except Exception:  # noqa: BLE001
            domains = []

    def _member_for_domain(domain: str) -> dict[str, Any] | None:
        dkey = _norm_vn(domain)
        for m in members:
            for d in t_domains.get(m["urn"], set()):
                if _norm_vn(d) == dkey:
                    return m
        return None

    def _member_lines(members_: list[dict[str, Any]]) -> str:
        lines = []
        for _i, _m in enumerate(members_, 1):
            _d = ", ".join(sorted(t_domains.get(_m["urn"], set()))) or "chưa xác định"
            lines.append(f"{_i}. **{_m['name']}** (`{_m['urn']}`) — domain: {_d}")
        return "\n".join(lines)

    answer_text: str | None = None
    if len(domains) == 1:
        m = _member_for_domain(domains[0])
        if m:
            _term_ds = await term_linked_datasets(entity_repo)
            _ds = [n for n in _term_ds.get(m["urn"], []) if n]
            answer_text = (
                f"Trong domain **{domains[0]}**, **{concept}** tương ứng với "
                f"thuật ngữ **{m['name']}** (`{m['urn']}`):\n\n{m['description']}"
            )
            if _ds:
                answer_text += f"\n\nLiên quan dataset: **{_ds[0]}**."
        else:
            answer_text = (
                f"Không có thuật ngữ **{concept}** rõ ràng trong domain "
                f"**{domains[0]}** trong DataHub → UNKNOWN."
            )
    elif len(domains) >= 2 and re.search(
        r"so sánh|so sanh|compare|so với|so voi|khác gì|khac gi|khác nhau|"
        r"khac nhau|khác biệt|khac biet|phân biệt|phan biet|khác|khac",
        q,
    ):
        parts = []
        for dom in domains:
            m = _member_for_domain(dom)
            if m:
                _desc = (m.get("description") or "").strip()
                if len(_desc) > 300:
                    _desc = _desc[:300] + "..."
                parts.append(
                    f"- **Domain {dom.upper()}**:\n"
                    f"  Thuật ngữ tương ứng: **{m['name']}** (`{m['urn']}`).\n"
                    f"  *Định nghĩa:* {_desc}"
                )
            else:
                parts.append(
                    f"- **Domain {dom.upper()}**:\n"
                    f"  Hiện chưa có thuật ngữ chuyên biệt cho **{concept}** trong "
                    "DataHub (UNKNOWN). Trong nghiệp vụ bán hàng / thương mại, "
                    "Demand thường đại diện cho nhu cầu thị trường, đơn hàng hoặc "
                    "dự báo doanh số."
                )
        diff_intro = f"Sự khác biệt về định nghĩa **{concept}** giữa các domain:\n\n"
        answer_text = diff_intro + "\n\n".join(parts)
    else:
        named_members = [m for m in members if _norm_vn(m["name"]) in q]
        if len(named_members) == 1:
            m = named_members[0]
            _term_ds = await term_linked_datasets(entity_repo)
            _ds = [n for n in _term_ds.get(m["urn"], []) if n]
            answer_text = f"Thuật ngữ **{m['name']}** (`{m['urn']}`):\n\n{m['description']}"
            if _ds:
                answer_text += f"\n\nLiên quan dataset: **{_ds[0]}**."
        else:
            answer_text = (
                f"Thuật ngữ **{concept}** có nhiều định nghĩa khác nhau trong "
                f"DataHub ({len(members)} term liên quan):\n\n{_member_lines(members)}\n\n"
                "Cần nêu rõ domain (SẢN XUẤT / KINH DOANH / LOGISTIC / ...) để chọn "
                "đúng định nghĩa."
            )
    if not answer_text:
        return None
    citations: list[Any] = []
    docs, context_xml = build_context(results)
    log.info(
        "domain_scoped_glossary",
        question=question[:100],
        concept=concept,
        domains=domains,
        members=len(members),
    )
    return (answer_text, citations, docs, context_xml, "high")
