"""Entity suggestion and typo correction service."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


@dataclass
class EntityCorrection:
    """Represents an automatic typo/alias correction applied to an entity query."""
    original_name: str
    corrected_name: str
    confidence: float
    entity_type: str = "dataset"
    correction_type: str = "fuzzy"  # "fuzzy", "abbreviation", "case_insensitive", "alias"


@dataclass
class EntityResolutionResult:
    """Encapsulates the output of entity resolution including corrections and notes."""
    entities: list[Any] = field(default_factory=list)
    corrections: list[EntityCorrection] = field(default_factory=list)
    confidence: float = 1.0
    resolved_via: str = "exact"  # "exact", "fuzzy", "abbreviation", "alias", "expansion"
    correction_note: str | None = None


class EntitySuggestionService:
    """Service to generate clear user-facing notes and multi-candidate suggestions."""

    @staticmethod
    def build_correction_note(corrections: list[EntityCorrection], language: str = "vi") -> str:
        """Format an inline markdown blockquote informing user about corrected typo."""
        if not corrections:
            return ""

        meaningful = [
            c for c in corrections
            if c.original_name.strip() and c.corrected_name.strip()
            and c.original_name.strip().lower() != c.corrected_name.strip().lower()
        ]
        if not meaningful:
            return ""

        notes: list[str] = []
        for c in meaningful:
            notes.append(
                f"Kết quả dưới đây là của **{c.corrected_name}** (thay vì *{c.original_name}*)"
            )
        body = "; ".join(notes)
        if language == "en":
            orig = meaningful[0].original_name
            corr = meaningful[0].corrected_name
            return (
                f"> ⚠️ **Note**: Entity name corrected. "
                f"Showing results for **{corr}** (instead of *{orig}*).\n\n"
            )
        return f"> ⚠️ **Lưu ý**: Bạn có vẻ nhập nhầm tên thực thể. {body}.\n\n"


    @staticmethod
    def format_multiple_suggestions(user_input: str, candidates: list[tuple[str, float]]) -> str:
        """Format a list of likely candidates when confidence is low or multiple match."""
        if not candidates:
            return f"Không tìm thấy thực thể phù hợp với '{user_input}'."
        cand_lines = "\n".join(
            f"- **{name}** (độ khớp: {int(round(score * 100))}%)"
            for name, score in candidates[:5]
        )
        return (
            f"Không tìm thấy thực thể chính xác cho **{user_input}** trong catalog.\n"
            f"Có thể bạn đang muốn tìm một trong các thực thể sau:\n\n{cand_lines}\n\n"
            f"Vui lòng chọn hoặc gõ lại tên chính xác."
        )
