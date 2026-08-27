"""Tests for RAGAS evaluation pipeline — database, logging, evaluator, API, security."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_session():
    """Mock AsyncSession for database interaction tests."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.execute = AsyncMock()
    return session


# ---------------------------------------------------------------------------
# A. DATABASE — InteractionLog model schema
# ---------------------------------------------------------------------------

class TestInteractionLogModel:
    """Verify InteractionLog model has all required columns."""

    def test_model_exists(self):
        from database.models import InteractionLog
        assert InteractionLog.__tablename__ == "interaction_logs"

    def test_has_evaluation_status(self):
        from database.models import InteractionLog
        assert hasattr(InteractionLog, "evaluation_status")

    def test_has_retrieved_contexts(self):
        from database.models import InteractionLog
        assert hasattr(InteractionLog, "retrieved_contexts")

    def test_has_ragas_columns(self):
        from database.models import InteractionLog
        for col in [
            "faithfulness", "faithfulness_status",
            "answer_relevancy", "answer_relevancy_status",
            "context_precision", "context_precision_status",
            "context_recall", "context_recall_status",
        ]:
            assert hasattr(InteractionLog, col), f"Missing {col}"

    def test_has_human_review_columns(self):
        from database.models import InteractionLog
        for col in ["human_review", "human_review_note", "human_reviewed_at"]:
            assert hasattr(InteractionLog, col), f"Missing {col}"

    def test_has_evaluated_at(self):
        from database.models import InteractionLog
        assert hasattr(InteractionLog, "evaluated_at")

    def test_has_evaluation_model(self):
        from database.models import InteractionLog
        assert hasattr(InteractionLog, "evaluation_model")


# ---------------------------------------------------------------------------
# B. INTERACTION LOGGING — log_request, log_response, context persistence
# ---------------------------------------------------------------------------

class TestInteractionLogging:

    @pytest.mark.asyncio
    async def test_log_request_creates_entry(self, mock_session):
        from app.services.interaction_logger import InteractionLogger
        from database.models import InteractionLog

        logger = InteractionLogger(mock_session)
        await logger.log_request(
            trace_id="t1", question="test?", user_id="u1", conversation_id="c1"
        )
        mock_session.add.assert_called_once()
        added = mock_session.add.call_args[0][0]
        assert isinstance(added, InteractionLog)
        assert added.trace_id == "t1"
        assert added.question == "test?"
        assert added.intent == "pending"

    @pytest.mark.asyncio
    async def test_log_response_sets_context(self, mock_session):
        from app.services.interaction_logger import InteractionLogger

        entry = MagicMock()
        entry.evaluation_status = "NOT_EVALUATED"
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = entry
        mock_session.execute.return_value = result_mock

        logger = InteractionLogger(mock_session)
        await logger.log_response(
            trace_id="t1",
            answer="answer text",
            intent="GENERAL",
            retrieved_contexts=["ctx1", "ctx2"],
        )
        assert entry.retrieved_contexts == {"contexts": ["ctx1", "ctx2"]}
        assert entry.evaluation_status == "PENDING"

    @pytest.mark.asyncio
    async def test_log_response_no_context_keeps_status(self, mock_session):
        from app.services.interaction_logger import InteractionLogger

        entry = MagicMock()
        entry.evaluation_status = "NOT_EVALUATED"
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = entry
        mock_session.execute.return_value = result_mock

        logger = InteractionLogger(mock_session)
        await logger.log_response(
            trace_id="t1", answer="answer", intent="GREETING",
        )
        # Without context, evaluation_status stays NOT_EVALUATED
        assert entry.evaluation_status == "NOT_EVALUATED"

    @pytest.mark.asyncio
    async def test_update_ragas_sets_evaluated_at(self, mock_session):
        from app.services.interaction_logger import InteractionLogger

        entry = MagicMock()
        entry.faithfulness_status = None
        entry.answer_relevancy_status = None
        entry.context_precision_status = None
        entry.context_recall_status = None
        entry.evaluation_status = "RUNNING"
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = entry
        mock_session.execute.return_value = result_mock

        logger = InteractionLogger(mock_session)
        await logger.update_ragas_scores(
            trace_id="t1", faithfulness=0.9, faithfulness_status="COMPLETED"
        )
        assert entry.faithfulness == 0.9
        assert entry.evaluated_at is not None

    @pytest.mark.asyncio
    async def test_set_evaluation_status(self, mock_session):
        from app.services.interaction_logger import InteractionLogger

        entry = MagicMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = entry
        mock_session.execute.return_value = result_mock

        logger = InteractionLogger(mock_session)
        await logger.set_evaluation_status("t1", "RUNNING")
        assert entry.evaluation_status == "RUNNING"

    @pytest.mark.asyncio
    async def test_set_human_review(self, mock_session):
        from app.services.interaction_logger import InteractionLogger

        entry = MagicMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = entry
        mock_session.execute.return_value = result_mock

        logger = InteractionLogger(mock_session)
        await logger.set_human_review("t1", "accepted", note="Looks good")
        assert entry.human_review == "accepted"
        assert entry.human_review_note == "Looks good"
        assert entry.human_reviewed_at is not None


# ---------------------------------------------------------------------------
# C. RAGAS EVALUATOR — input validation, edge cases, failure handling
# ---------------------------------------------------------------------------

class TestRAGASEvaluator:

    def test_no_contexts_returns_not_evaluated(self):
        import asyncio

        from evaluation.ragas_evaluator import evaluate_interaction

        result = asyncio.run(evaluate_interaction(
            question="q", answer="a", retrieved_contexts=[]
        ))
        assert result.faithfulness_status == "NOT_EVALUATED"
        assert result.error is not None

    def test_no_llm_returns_failed(self):
        import asyncio

        from evaluation.ragas_evaluator import evaluate_interaction

        with patch("config.settings.settings") as mock_settings:
            mock_settings.GEMINI_API_KEY = ""
            result = asyncio.run(evaluate_interaction(
                question="q", answer="a", retrieved_contexts=["context"]
            ))
            assert result.faithfulness_status == "FAILED"
            assert result.error is not None
            assert "GEMINI_API_KEY" in result.error

    def test_ragas_result_dataclass(self):
        from evaluation.ragas_evaluator import RAGASResult
        r = RAGASResult()
        assert r.faithfulness is None
        assert r.faithfulness_status == "NOT_EVALUATED"
        assert r.error is None
        assert r.raw_scores == {}


# ---------------------------------------------------------------------------
# D. SECURITY — no credentials in interaction data
# ---------------------------------------------------------------------------

class TestSecurityNoCredentials:

    SENSITIVE_PATTERNS = [
        "Bearer ", "authorization", "jwt", "api_key",
        "password", "secret", "connection_string",
        "DATAHUB_TOKEN", "FIREWORKS_API_KEY",
    ]

    def test_interaction_logger_no_sensitive_data(self):
        """Verify InteractionLogger code does not store raw auth headers."""
        import inspect

        from app.services.interaction_logger import InteractionLogger

        source = inspect.getsource(InteractionLogger)
        for pattern in self.SENSITIVE_PATTERNS:
            assert pattern.lower() not in source.lower(), (
                f"InteractionLogger contains sensitive pattern: {pattern}"
            )

    def test_admin_api_no_sensitive_in_response(self):
        """Verify admin API endpoints do not expose credentials."""
        from app.api.admin import router
        source = str(router.routes)
        for pattern in ["Bearer", "api_key", "password", "secret"]:
            assert pattern.lower() not in source.lower(), (
                f"Admin API contains sensitive pattern: {pattern}"
            )

    def test_ragas_evaluator_no_credential_leak(self):
        """Verify RAGAS evaluator does not log or return credentials."""
        import inspect

        from evaluation.ragas_evaluator import RAGASResult, evaluate_interaction

        source = inspect.getsource(evaluate_interaction)
        assert "Bearer" not in source
        assert "api_key" not in source.lower() or "settings" in source.lower()

        # RAGASResult should not have any credential fields
        result = RAGASResult()
        assert not hasattr(result, "token")
        assert not hasattr(result, "api_key")


# ---------------------------------------------------------------------------
# E. MIGRATION — verify migration file exists and is valid
# ---------------------------------------------------------------------------

class TestMigration:

    def test_migration_file_exists(self):
        import os
        path = "database/migrations/versions/7_add_ragas_evaluation.py"
        assert os.path.exists(path), f"Migration file not found: {path}"

    def test_migration_has_upgrade(self):
        path = "database/migrations/versions/7_add_ragas_evaluation.py"
        with open(path) as f:
            content = f.read()
        assert "def upgrade()" in content
        assert "def downgrade()" in content
        assert "interaction_logs" in content
        assert "evaluation_status" in content
        assert "retrieved_contexts" in content
        assert "evidence_records" in content

    def test_migration_revision_chain(self):
        path = "database/migrations/versions/7_add_ragas_evaluation.py"
        with open(path) as f:
            content = f.read()
        assert "7_add_ragas_evaluation" in content
        assert "6_add_image_storage" in content
