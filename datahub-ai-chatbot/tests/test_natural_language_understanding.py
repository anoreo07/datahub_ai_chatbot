"""Comprehensive Natural Language Understanding test suite."""

import pytest

from app.services.chat.entity_suggestion import (
    EntityCorrection,
    EntitySuggestionService,
)
from app.services.chat.question_analysis import QuestionAnalysisService
from app.services.chat.synonym_expander import SynonymExpander
from retrieval.coreference import has_anaphora, resolve_entity_reference
from retrieval.fuzzy import fuzzy_score
from retrieval.intent import QueryIntent, classify_intent


class TestSectionACasualVsFormalQueries:
    """Test Intent Detection with casual, spoken Vietnamese vs formal queries."""

    @pytest.mark.parametrize(
        ("query", "expected_intent"),
        [
            # Lineage variations
            ("Bảng này được tạo ra từ bảng nào?", QueryIntent.LINEAGE),
            ("Nó lấy dữ liệu từ đâu?", QueryIntent.LINEAGE),
            ("Data chảy từ bảng nào sang bảng này?", QueryIntent.LINEAGE),
            ("bảng nào feed vào fact_orders", QueryIntent.LINEAGE),
            ("upstream của dim_customer là gì?", QueryIntent.LINEAGE),

            # Glossary / Metric variations
            ("Công thức tính Coverage date là gì?", QueryIntent.TERM_DEFINITION),
            ("Hiểu sao về term MRP?", QueryIntent.TERM_DEFINITION),
            ("Tính Net Revenue như thế nào?", QueryIntent.TERM_DEFINITION),
            ("Cho biết ý nghĩa của chỉ số EBITDA", QueryIntent.TERM_DEFINITION),
            ("Định nghĩa thuật ngữ Component Demand", QueryIntent.TERM_DEFINITION),

            # Schema / Field variations
            ("Bảng dim_customer có những cột nào?", QueryIntent.SCHEMA_LOOKUP),
            ("cấu trúc bảng fact_orders", QueryIntent.SCHEMA_LOOKUP),
            ("sales_order có bao nhiêu trường?", QueryIntent.SCHEMA_LOOKUP),
            ("cho xem các field của bảng dim_product", QueryIntent.SCHEMA_LOOKUP),

            # Owner variations
            ("Ai phụ trách dataset này?", QueryIntent.OWNER_LOOKUP),
            ("Ai là chủ sở hữu của dim_warehouse?", QueryIntent.OWNER_LOOKUP),
            ("Ai maintain bảng fact_sales?", QueryIntent.OWNER_LOOKUP),
            ("Team nào quản lý dataset này?", QueryIntent.OWNER_LOOKUP),

            # Quality variations
            ("Dữ liệu bảng này có tốt không?", QueryIntent.QUALITY_CHECK),
            ("có nhiều null không?", QueryIntent.QUALITY_CHECK),
            ("kiểm tra data quality cho dim_user", QueryIntent.QUALITY_CHECK),
            ("dữ liệu đã mới chưa, freshness thế nào?", QueryIntent.QUALITY_CHECK),
        ],
    )
    def test_intent_accuracy(self, query: str, expected_intent: QueryIntent) -> None:
        detected = classify_intent(query)
        assert detected == expected_intent, (
            f"Query '{query}' detected as {detected}, expected {expected_intent}"
        )



class TestSectionBTypoAndCorrectionNote:
    """Test Entity Correction note format and fuzzy resolution."""

    def test_exact_match_no_correction_note(self) -> None:
        corrections = [
            EntityCorrection(
                original_name="dim_warehouse",
                corrected_name="dim_warehouse",
                confidence=1.0,
            )
        ]
        note = EntitySuggestionService.build_correction_note(corrections)
        assert note == ""

    def test_single_typo_correction_note(self) -> None:
        corrections = [
            EntityCorrection(
                original_name="dim_BaoCeoLayout",
                corrected_name="dim_BaoCaoLayout",
                confidence=0.94,
                correction_type="fuzzy",
            )
        ]
        note = EntitySuggestionService.build_correction_note(corrections)
        assert "> ⚠️ **Lưu ý**:" in note
        assert "**dim_BaoCaoLayout**" in note
        assert "*dim_BaoCeoLayout*" in note

    def test_fuzzy_score_above_adaptive_threshold(self) -> None:
        score = fuzzy_score("dim_BaoCeoLayout", "dim_BaoCaoLayout")
        assert score >= 0.85

        score_snake = fuzzy_score("fact_sales_ordr", "fact_sales_order")
        assert score_snake >= 0.85


class TestSectionCAnaphoraResolution:
    """Test multi-turn context and coreference resolution."""

    def test_has_anaphora_detection(self) -> None:
        assert has_anaphora("Nó lấy dữ liệu từ đâu?") is True
        assert has_anaphora("Schema của nó là gì?") is True
        assert has_anaphora("Bảng này thuộc domain nào?") is True
        assert has_anaphora("dim_warehouse có schema gì?") is False

    def test_resolve_entity_reference_from_history(self) -> None:
        history = [
            ("Schema của dim_warehouse là gì?", "Bảng có 10 cột"),
            ("warehouse_id là gì?", "Mã định danh kho"),
        ]
        resolved = resolve_entity_reference(history)
        assert resolved == "dim_warehouse"

    def test_question_analysis_anaphora_rewrite(self) -> None:
        history = [
            ("Schema của dim_warehouse là gì?", "Bảng có 10 cột"),
        ]
        rewritten = QuestionAnalysisService.resolve_anaphora_with_context(
            "Ai là người sở hữu nó?", history,
        )
        assert "dim_warehouse" in rewritten


class TestSectionDSynonymExpander:
    """Test business & technical synonym and abbreviation expansion."""

    def setup_method(self) -> None:
        self.expander = SynonymExpander()

    def test_abbreviation_expansion(self) -> None:
        expanded = self.expander.expand_query("tìm bc doanh thu")
        assert any("baocao" in term or "bao cao" in term for term in expanded)

    def test_concept_synonyms(self) -> None:
        norm = self.expander.normalize_query("Bảng này lấy dữ liệu từ đâu???")
        assert "?" not in norm
