"""Deterministic domain-scoped semantic discovery.

Vietnamese natural-language discovery questions ("dataset nào phục vụ kiểm tra
WIP giữa MES và SAP?", "dataset staging vật tư (material) trong DMS ở đâu?")
name a business concept that maps onto the *English / technical* tokens of the
target entity's name (``Báo cáo check WIP MES_SAP``, ``dms.stg.stg_material``,
``mrp_stock_req``). Full-sentence vector/keyword search ranks unrelated
entities above those targets because the query words do not literally appear in
the entity content.

This module expands the question through a Vietnamese<->English domain synonym
table plus acronym extraction (WIP, MES, SAP, MRP, DMS, PFEP...), then scores
catalog entities by how many expanded tokens appear in their name and URN path.
It is deterministic, cheap and never calls an LLM: it slots into the retrieval
fast path as a fallback after vector search, and only fires for discovery
sentences (no exact entity name quoted).
"""

from __future__ import annotations

import re
from collections.abc import Sequence

import structlog

from database.models import Entity
from database.repositories.entity_repository import EntityRepository
from retrieval.fuzzy import ascii_fold

log = structlog.get_logger()

# Vietnamese -> English domain vocabulary. Keys are ASCII-folded substrings of
# the question; values are the English/technical tokens that appear in catalog
# entity names / URNs. Longer, more specific keys are tried first so
# "đơn hàng bán" is not split into "đơn hàng" + "bán".
SYNONYMS: dict[str, tuple[str, ...]] = {
    "dự báo cung cấp hàng tuần": ("weekly supply forecast", "supply capacity"),
    "du bao cung cap hang tuan": ("weekly supply forecast", "supply capacity"),
    "tính nhu cầu linh kiện": ("mrp", "component", "requirement", "part"),
    "tinh nhu cau linh kien": ("mrp", "component", "requirement", "part"),
    "đơn hàng bán": ("lead", "sales order", "order"),
    "don hang ban": ("lead", "sales order", "order"),
    "cung cấp hàng tuần": ("weekly supply", "supply"),
    "cung cap hang tuan": ("weekly supply", "supply"),
    "nhu cầu linh kiện": ("component requirement", "mrp", "part"),
    "nhu cau linh kien": ("component requirement", "mrp", "part"),
    "kiểm tra wip": ("wip", "check"),
    "kiem tra wip": ("wip", "check"),
    "staging": ("stg",),
    "thô": ("raw", "stg"),
    "tho": ("raw", "stg"),
    "nguyên vật liệu": ("material",),
    "nguyen vat lieu": ("material",),
    "vật tư": ("material",),
    "vat tu": ("material",),
    "linh kiện": ("component", "part"),
    "linh kien": ("component", "part"),
    "nhu cầu": ("requirement", "demand", "req"),
    "nhu cau": ("requirement", "demand", "req"),
    "cung cấp": ("supply",),
    "cung cap": ("supply",),
    "hàng tuần": ("weekly",),
    "hang tuan": ("weekly",),
    "dự báo": ("forecast", "survey", "capacity"),
    "du bao": ("forecast", "survey", "capacity"),
    "đơn hàng": ("order",),
    "don hang": ("order",),
    "khách hàng": ("customer", "contact"),
    "khach hang": ("customer", "contact"),
    "kiểm tra": ("check",),
    "kiem tra": ("check",),
    "bán": ("sale", "lead"),
    "ban": ("sale", "lead"),
    "dữ liệu bán": ("sales", "sale"),
    "du lieu ban": ("sales", "sale"),
    # English technical tokens that users write verbatim in the question but
    # carry no Vietnamese synonym. They match catalog names directly ("có báo
    # cáo nào về capacity của nhà cung cấp (vendor) không?" -> the capacity
    # dashboards). The keys are ASCII-folded so "Capacity" / "CAPACITY" hit.
    "capacity": ("capacity",),
    "supplier": ("supplier",),
    "vendor": ("vendor", "supplier"),
    "survey": ("survey",),
}

# Acronyms that never appear verbatim in the question are still meaningful
# domain tokens; they are pulled from the synonym expansions above. Plain
# acronyms already written in the question (WIP, MES, SAP, MRP, DMS) are
# extracted directly from the text.
_ACRONYM_RE = re.compile(r"\b[A-Z]{2,8}(?:[-_][A-Z0-9]+)*\b")

# Discovery sentences carry no exact catalog identifier; if one is present the
# resolver should already have handled it.
_EXACT_NAME_RE = re.compile(
    r"""["'“”‘’][^"'“”‘’]{2,80}["'“”‘’]|"""
    r"[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+|"
    r"tên chính xác|ten chinh xac|có tên|co ten|tên là|ten la|named",
    re.I,
)


def _is_discovery_sentence(question: str) -> bool:
    if _EXACT_NAME_RE.search(question):
        return False
    markers = (
        "nào", "nao", "gì", "gi ", "ở đâu", "o dau", "nằm ở đâu", "nam o dau",
        "chứa", "chua", "có báo cáo", "co bao cao", "có dashboard",
        "co dashboard", "có report", "co report", "có dataset", "co dataset",
        "tìm", "tim ", "liệt kê", "liet ke", "phục vụ", "phuc vu",
        "which", "what ", "how ", "where",
        "→", "->", "➔", "⇒", "chuỗi", "chained",
    )
    return any(m in question.lower() for m in markers)


def expand_query_tokens(question: str) -> set[str]:
    """Expand a discovery question into candidate English/technical tokens.

    Returns an ASCII-folded set of tokens: acronyms written in the question plus
    the synonym-table expansions. Tokens shorter than 2 characters are dropped.
    """
    folded = ascii_fold(question)
    tokens: set[str] = set()
    for key in sorted(SYNONYMS, key=lambda k: -len(k)):
        if key in folded:
            tokens.update(t for t in SYNONYMS[key] if t)
    tokens.update(m.lower() for m in _ACRONYM_RE.findall(question) if len(m) >= 2)
    return {t for t in tokens if len(t) >= 2}


def score_entity(tokens: set[str], entity: Entity) -> float:
    """Number of expanded query tokens found in the entity's name + URN path.

    Name matches count double (the name is the strongest signal); URN-path
    matches (``dms.stg.stg_material``) count single. Returns 0 when no token
    matches.
    """
    name = ascii_fold(entity.name or entity.display_name or "")
    urn = ascii_fold(entity.urn)
    hits = 0.0
    for t in tokens:
        if t in name:
            hits += 2.0
        elif t in urn:
            hits += 1.0
    return hits


class TokenDiscovery:
    """Discovery fallback: rank datasets/dashboards by query-token overlap."""

    def __init__(self, repo: EntityRepository) -> None:
        self._repo = repo
        self._entities: dict[str, list[Entity]] = {}

    async def _load(self, entity_type: str) -> Sequence[Entity]:
        if entity_type not in self._entities:
            self._entities[entity_type] = list(await self._repo.list_all(
                entity_type, limit=100000,
            ))
        return self._entities[entity_type]

    async def discover(
        self, question: str, top_k: int = 8,
        entity_types: Sequence[str] = ("dataset", "dashboard"),
        min_hits: float = 3.0,
        trace_id: str | None = None,
    ) -> list[Entity]:
        """Return the strongest token-matched entities, or [] if no discovery
        signal is present."""
        if not _is_discovery_sentence(question):
            return []
        tokens = expand_query_tokens(question)
        if not tokens:
            return []
        scored: list[tuple[float, Entity]] = []
        for etype in entity_types:
            for e in await self._load(etype):
                if getattr(e, "deleted", False):
                    continue
                hits = score_entity(tokens, e)
                if hits >= min_hits:
                    scored.append((hits, e))
        scored.sort(key=lambda t: (-t[0], t[1].urn))
        # Dedup by name: same-named fact tables live in many schemas
        # ("fact_supplier_capacity" exists in HP/INDO/INDIA reports, so 8+ copies
        # tie at the same token score). Flooding the top-k with identical names
        # pushes the genuinely distinct targets (e.g. the redshift
        # rpt_survey_weekly_supply_capacity) past the cutoff. Keep one copy of
        # each name — the strongest (highest hits, then first URN).
        best_by_name: dict[str, tuple[float, Entity]] = {}
        for hits, e in scored:
            key = (e.name or e.display_name or "").strip().lower()
            if not key:
                continue
            if key not in best_by_name or (
                hits > best_by_name[key][0]
            ):
                best_by_name[key] = (hits, e)
        deduped = sorted(
            best_by_name.values(), key=lambda t: (-t[0], t[1].urn),
        )
        top = [e for _, e in deduped[:top_k]]
        log.info("token_discovery", trace_id=trace_id, question=question[:100],
                 tokens=sorted(tokens)[:12], candidates=len(scored),
                 unique=len(deduped), top=len(top))
        return top
