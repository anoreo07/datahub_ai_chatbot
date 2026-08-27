"""anchor_builder.py

Responsibility: Phân tích query và conversation history để tạo QueryAnchor.
Chạy TRƯỚC entity resolution, output anchor dùng để validate entity resolution.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from app.services.chat.query_anchor import (
    AnchorConfidence,
    AnchorSource,
    EntityAnchor,
    QueryAnchor,
)

logger = logging.getLogger(__name__)

# Patterns nhận diện entity mention trực tiếp trong câu hỏi tiếng Việt + English
# Dựa trên naming convention của DataHub entities:
# - Prefix: dim_, fact_, stg_, mart_, rpt_, fct_, agg_, raw_
# - PascalCase: BaoCaoLayout, KhachHang
# - UPPER blocks: PVB QDAT, PVB_QDAT_PLATFORM
# - Quoted: "PVB QDAT", `PVB QDAT`

ENTITY_MENTION_PATTERNS = [
    # DataHub naming conventions with prefix
    r"\b(dim_\w+)\b",
    r"\b(fact_\w+)\b",
    r"\b(fct_\w+)\b",
    r"\b(stg_\w+)\b",
    r"\b(mart_\w+)\b",
    r"\b(rpt_\w+)\b",
    r"\b(agg_\w+)\b",
    r"\b(raw_\w+)\b",
    # Quoted names: "PVB QDAT", `PVB QDAT`
    r'"([^"]+)"',
    r"`([^`]+)`",
    r"'([^']+)'",
    # UPPER words separated by space or underscore: PVB QDAT, PVB_QDAT
    r"\b([A-Z]{2,}(?:[\s_]+[A-Z0-9]{2,})+)\b",
    # Single UPPER word with underscore/dash
    r"\b([A-Z]{2,}(?:_[A-Za-z0-9]+)+)\b",
    # PascalCase: BaoCaoLayout
    r"\b([A-Z][a-z0-9]+(?:[A-Z][a-z0-9]+)+)\b",
]

# Stop words to ignore if captured by broad regex
_STOP_WORDS = frozenset(
    {
        "datahub",
        "metadata",
        "dataset",
        "datasets",
        "dashboard",
        "dashboards",
        "glossary",
        "lineage",
        "schema",
        "table",
        "tables",
        "field",
        "fields",
        "report",
        "reports",
        "domain",
        "domains",
        "owner",
        "owners",
        "ai",
    }
)

# Anaphora patterns — người dùng refer đến entity từ turn trước
ANAPHORA_PATTERNS = [
    r"\b(nó|cái này|dataset này|bảng này|cái đó|bảng đó|cái kia|bảng kia)\b",
    r"\b(no|bang nay|dataset nay|bang do)\b",
    r"\b(this dataset|this table|it|this one|that one)\b",
    r"\b(của nó|của cái này|của bảng này|cua no|cua bang nay)\b",
]



class AnchorBuilder:
    """Builder for creating QueryAnchor from query and conversation history."""

    def build(
        self,
        query: str,
        conversation_history: list[dict[str, Any]] | list[tuple[str, str]] | None = None,
    ) -> QueryAnchor:
        """Main entry point. Trả về QueryAnchor cho query hiện tại.

        Thứ tự ưu tiên:
        1. Explicit entity mention trong query
        2. Anaphora -> resolve từ conversation history
        3. No anchor (free query)
        """
        anchor = QueryAnchor(original_query=query)

        # Bước 1: Extract explicit mentions
        explicit_mentions = self._extract_explicit_mentions(query)
        for mention in explicit_mentions:
            anchor.add_anchor(
                EntityAnchor(
                    raw_mention=mention,
                    resolved_urn=None,  # Sẽ được fill sau bởi EntityResolver
                    resolved_name=None,
                    entity_type=None,
                    source=AnchorSource.EXPLICIT_MENTION,
                    confidence=AnchorConfidence.LOW,  # Chưa verify với DB
                )
            )

        # Bước 2: Detect anaphora nếu không có explicit mention
        if not anchor.anchors and conversation_history:
            anaphora_entity = self._resolve_anaphora(query, conversation_history)
            if anaphora_entity:
                anchor.add_anchor(
                    EntityAnchor(
                        raw_mention=anaphora_entity["raw"],
                        resolved_urn=anaphora_entity.get("urn"),
                        resolved_name=anaphora_entity.get("name"),
                        entity_type=anaphora_entity.get("entity_type"),
                        source=AnchorSource.ANAPHORA,
                        confidence=AnchorConfidence.MEDIUM,
                    )
                )
                anchor.inherited_from_turn = anaphora_entity.get("turn_index")

        logger.debug(
            f"[anchor_builder] Query: {query!r} -> "
            f"{len(anchor.anchors)} anchors: "
            f"{[a.raw_mention for a in anchor.anchors]}"
        )
        return anchor

    def _extract_explicit_mentions(self, query: str) -> list[str]:
        """Tìm tất cả entity name patterns trong query."""
        mentions: list[str] = []
        for pattern in ENTITY_MENTION_PATTERNS:
            for match in re.finditer(pattern, query):
                val = match.group(1) if match.groups() else match.group(0)
                val = val.strip()
                if val and val.lower() not in _STOP_WORDS and len(val) >= 2:
                    mentions.append(val)

        # Deduplicate, preserve order
        seen: set[str] = set()
        result: list[str] = []
        for m in mentions:
            if m.lower() not in seen:
                seen.add(m.lower())
                result.append(m)
        return result

    def _resolve_anaphora(
        self,
        query: str,
        history: list[dict[str, Any]] | list[tuple[str, str]],
    ) -> dict[str, Any] | None:
        """Detect anaphora và tìm entity từ turn gần nhất có entity."""
        has_anaphora = any(re.search(p, query, re.IGNORECASE) for p in ANAPHORA_PATTERNS)
        if not has_anaphora:
            return None

        # Trường hợp 1: History là list các dict {"query": str, "answer": str, "entities": list}
        if history and isinstance(history[0], dict):
            for i, turn in enumerate(reversed(history)):  # type: ignore
                entities = turn.get("entities", [])
                if entities:
                    first_ent = entities[0]
                    ent_dict = (
                        first_ent
                        if isinstance(first_ent, dict)
                        else {
                            "name": getattr(first_ent, "name", str(first_ent)),
                            "urn": getattr(first_ent, "urn", None),
                            "entity_type": getattr(first_ent, "entity_type", "dataset"),
                        }
                    )
                    name = ent_dict.get("name") or ent_dict.get("urn") or ""
                    if name:
                        return {
                            "raw": name,
                            "urn": ent_dict.get("urn"),
                            "name": name,
                            "entity_type": ent_dict.get("entity_type", "dataset"),
                            "turn_index": len(history) - 1 - i,
                        }

        # Trường hợp 2: History là list các tuple (user_query, assistant_answer)
        if history and isinstance(history[0], (list, tuple)):
            from retrieval.coreference import resolve_entity_reference

            ent_name = resolve_entity_reference(history)  # type: ignore
            if ent_name:
                return {
                    "raw": ent_name,
                    "urn": None,
                    "name": ent_name,
                    "entity_type": "dataset",
                    "turn_index": len(history) - 1,
                }

        return None
