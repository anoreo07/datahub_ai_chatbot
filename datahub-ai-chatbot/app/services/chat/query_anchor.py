"""query_anchor.py

QueryAnchor là "hợp đồng" giữa các stage trong pipeline:
"Người dùng đang hỏi về entity này, không được trả lời về entity khác."

Mọi bước trong ChatService phải nhận và pass QueryAnchor.
Nếu bất kỳ bước nào produce output về entity khác -> ghi nhận hoặc xử lý theo AnchorViolation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class AnchorSource(Enum):
    EXPLICIT_MENTION = "explicit_mention"  # User nói tên entity trực tiếp
    ANAPHORA = "anaphora"  # User dùng "nó", "dataset này"
    CONTEXT_INHERIT = "context_inherit"  # Kế thừa từ turn trước
    INFERRED = "inferred"  # Intent classifier suy ra


class AnchorConfidence(Enum):
    HIGH = "high"  # Exact match trong DB
    MEDIUM = "medium"  # Fuzzy match hoặc alias
    LOW = "low"  # Inferred từ context


@dataclass
class EntityAnchor:
    """Một entity được anchor trong query."""

    raw_mention: str  # Cái user gõ: "PVB QDAT"
    resolved_urn: str | None = None  # URN thực tế nếu đã resolve
    resolved_name: str | None = None  # Tên thực tế: "PVB QDAT Platform"
    entity_type: str | None = None  # "dataset", "dashboard", etc.
    source: AnchorSource = AnchorSource.EXPLICIT_MENTION
    confidence: AnchorConfidence = AnchorConfidence.LOW
    is_fuzzy_match: bool = False
    fuzzy_distance: int = 0


@dataclass
class QueryAnchor:
    """Anchor cho toàn bộ request.

    Được tạo một lần tại đầu pipeline, truyền xuống tất cả stages.
    """

    original_query: str
    anchors: list[EntityAnchor] = field(default_factory=list)
    conversation_id: str | None = None
    inherited_from_turn: int | None = None  # Turn index nếu là anaphora

    @property
    def primary_anchor(self) -> EntityAnchor | None:
        """Entity chính trong query."""
        if not self.anchors:
            return None
        # Ưu tiên theo confidence rồi source
        return sorted(
            self.anchors,
            key=lambda a: (
                a.confidence == AnchorConfidence.HIGH,
                a.source == AnchorSource.EXPLICIT_MENTION,
            ),
            reverse=True,
        )[0]

    @property
    def anchor_urns(self) -> set[str]:
        """Set tất cả URNs đã anchor."""
        return {a.resolved_urn for a in self.anchors if a.resolved_urn}

    @property
    def anchor_names(self) -> set[str]:
        """Set tất cả tên entity đã anchor (lowercase)."""
        names: set[str] = set()
        for a in self.anchors:
            if a.resolved_name:
                names.add(a.resolved_name.lower())
            if a.raw_mention:
                names.add(a.raw_mention.lower())
        return names

    def is_free_query(self) -> bool:
        """Query không mention entity cụ thể (câu hỏi chung)."""
        return len(self.anchors) == 0 or all(
            a.confidence == AnchorConfidence.LOW and not a.raw_mention.strip() for a in self.anchors
        )

    def add_anchor(self, anchor: EntityAnchor) -> None:
        self.anchors.append(anchor)


class AnchorViolation(Exception):  # noqa: N818
    """Raise khi một stage trong pipeline produce output về entity khác với entity đã anchor."""


    def __init__(
        self,
        stage: str,
        anchor: QueryAnchor,
        offending_entity: str,
        detail: str = "",
    ) -> None:
        self.stage = stage
        self.anchor = anchor
        self.offending_entity = offending_entity
        self.detail = detail
        super().__init__(
            f"[AnchorViolation] Stage '{stage}': "
            f"Expected entity from anchor {anchor.anchor_names}, "
            f"got '{offending_entity}'. {detail}"
        )
