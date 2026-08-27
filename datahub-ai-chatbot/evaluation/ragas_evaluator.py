"""RAGAS evaluation using the ragas library with Google Gemini backend.

Wraps the ragas library (v0.4.3) with Google Gemini Flash-Lite models.
Supports failover between 2 Gemini models — if one fails, the other takes over.

Uses ragas 0.4.3's llm_factory() with OpenAI-compatible endpoint at
https://generativelanguage.googleapis.com/v1beta/openai/.

Model rotation:
  Model 1 (gemini-3.1-flash-lite) → Model 2 (gemini-3.5-flash-lite) → Model 1 ...
After each failure, the failing model is skipped for SKIP_COOLDOWN seconds.
"""

from __future__ import annotations

import asyncio
import sys
import time
import types
from dataclasses import dataclass, field
from typing import Any

import structlog

log = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Monkey-patch: ragas 0.4.3 imports langchain_community.chat_models.vertexai
# which is not installed and not needed.  Satisfy the import before ragas loads.
# ---------------------------------------------------------------------------
_VERTEXAI_MOD = "langchain_community.chat_models.vertexai"
if _VERTEXAI_MOD not in sys.modules:
    _fake = types.ModuleType(_VERTEXAI_MOD)
    _fake.ChatVertexAI = None  # type: ignore[attr-defined]
    sys.modules[_VERTEXAI_MOD] = _fake

# Now safe to import ragas ---------------------------------------------------
from ragas.dataset_schema import SingleTurnSample  # noqa: E402
from ragas.evaluation import evaluate as ragas_evaluate  # noqa: E402
from ragas.llms import llm_factory  # noqa: E402
from ragas.metrics import (  # noqa: E402
    AnswerRelevancy,
    ContextPrecision,
    ContextRecall,
    Faithfulness,
)

# ---------------------------------------------------------------------------
# Model rotation state
# ---------------------------------------------------------------------------
SKIP_COOLDOWN = 10  # seconds to skip a failed model before retrying
_model_skip_until: dict[str, float] = {}  # model_id -> timestamp when skip expires
_current_model_idx = 0  # index into the model list

# Gemini OpenAI-compatible endpoint
_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"


class _OllamaEmbeddingsWrapper:
    """Wrapper to make ragas OpenAIEmbeddings compatible with BaseRagasEmbeddings interface."""

    def __init__(self, ragas_embeddings):
        self._emb = ragas_embeddings

    def embed_query(self, text: str) -> list[float]:
        return self._emb.embed_text(text)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._emb.embed_texts(texts)

    async def aembed_query(self, text: str) -> list[float]:
        return await self._emb.aembed_text(text)

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        return await self._emb.aembed_texts(texts)


def _get_available_models() -> list[str]:
    """Return list of configured Gemini model IDs (at least 1)."""
    from config.settings import settings

    models = []
    if settings.GEMINI_MODEL_1:
        models.append(settings.GEMINI_MODEL_1)
    if settings.GEMINI_MODEL_2:
        models.append(settings.GEMINI_MODEL_2)
    return models


def _pick_model() -> str | None:
    """Pick the next available model using round-robin with skip-on-failure."""
    models = _get_available_models()
    if not models:
        return None

    now = time.time()
    # Filter out models currently in cooldown
    available = [m for m in models if _model_skip_until.get(m, 0) <= now]
    if not available:
        # All models in cooldown — try the one closest to expiring
        return min(models, key=lambda m: _model_skip_until.get(m, 0))

    global _current_model_idx
    _current_model_idx = _current_model_idx % len(available)
    model = available[_current_model_idx]
    _current_model_idx += 1
    return model


def _mark_model_failed(model_id: str) -> None:
    """Put a model into cooldown."""
    _model_skip_until[model_id] = time.time() + SKIP_COOLDOWN
    log.warning("ragas_model_cooldown", model=model_id, cooldown_seconds=SKIP_COOLDOWN)


def _mark_model_ok(model_id: str) -> None:
    """Clear cooldown for a model (success resets skip)."""
    _model_skip_until.pop(model_id, None)


# ---------------------------------------------------------------------------
# Evaluation result dataclass
# ---------------------------------------------------------------------------
@dataclass
class RAGASResult:
    """Result of a single RAGAS evaluation run."""

    faithfulness: float | None = None
    faithfulness_status: str = "NOT_EVALUATED"
    answer_relevancy: float | None = None
    answer_relevancy_status: str = "NOT_EVALUATED"
    context_precision: float | None = None
    context_precision_status: str = "NOT_EVALUATED"
    context_recall: float | None = None
    context_recall_status: str = "NOT_EVALUATED"
    evaluation_model: str = ""
    error: str | None = None
    raw_scores: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# LLM + metrics builder per model
# ---------------------------------------------------------------------------
def _build_ragas_metrics(model_id: str) -> dict | None:
    """Build ragas metric instances for a given Gemini model.

    Returns a dict of metric instances or None if build failed.
    Uses Ollama embeddings for AnswerRelevancy via OpenAI-compatible endpoint.
    """
    from config.settings import settings

    api_key = settings.GEMINI_API_KEY
    if not api_key:
        log.warning("ragas_llm_no_gemini_key")
        return None

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key, base_url=_GEMINI_BASE_URL)

        ragas_llm = llm_factory(model_id, provider="openai", client=client)

        # Build embeddings using Ollama (OpenAI-compatible endpoint)
        ollama_client = OpenAI(
            api_key="ollama",
            base_url=settings.OLLAMA_BASE_URL,
        )
        from ragas.embeddings import OpenAIEmbeddings
        ragas_emb = OpenAIEmbeddings(
            client=ollama_client,
            model=settings.EMBEDDING_MODEL,
        )
        embeddings = _OllamaEmbeddingsWrapper(ragas_emb)

        return {
            "faithfulness": Faithfulness(llm=ragas_llm),
            "answer_relevancy": AnswerRelevancy(llm=ragas_llm, embeddings=embeddings),
            "context_precision": ContextPrecision(llm=ragas_llm),
            "context_recall": ContextRecall(llm=ragas_llm),
        }
    except Exception as exc:
        log.warning("ragas_metrics_init_failed", model=model_id, error=str(exc))
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
async def evaluate_interaction(
    *,
    question: str,
    answer: str,
    retrieved_contexts: list[str],
    reference: str | None = None,
    timeout_seconds: float = 45.0,
) -> RAGASResult:
    """Evaluate a single chat interaction using RAGAS metrics.

    Tries Gemini models in round-robin with failover:
      Model 1 → fail → Model 2 → fail → skip all for cooldown → retry.

    Rules:
    - If no retrieved_contexts → all metrics NOT_EVALUATED.
    - If no reference → context_recall NOT_EVALUATED.
    - If no API key configured → all metrics FAILED.
    - Evaluation failure never raises; returns FAILED status.
    """
    # Guard: no context means nothing to evaluate
    if not retrieved_contexts:
        return RAGASResult(
            faithfulness_status="NOT_EVALUATED",
            answer_relevancy_status="NOT_EVALUATED",
            context_precision_status="NOT_EVALUATED",
            context_recall_status="NOT_EVALUATED",
            error="No retrieved contexts available for evaluation",
        )

    from config.settings import settings

    if not settings.GEMINI_API_KEY:
        return RAGASResult(
            faithfulness_status="FAILED",
            answer_relevancy_status="FAILED",
            context_precision_status="FAILED",
            context_recall_status="FAILED",
            error="GEMINI_API_KEY not configured",
        )

    sample = SingleTurnSample(
        user_input=question,
        response=answer,
        retrieved_contexts=retrieved_contexts,
        reference=reference,
    )

    models = _get_available_models()
    if not models:
        return RAGASResult(
            faithfulness_status="FAILED",
            answer_relevancy_status="FAILED",
            context_precision_status="FAILED",
            context_recall_status="FAILED",
            error="No GEMINI_MODEL configured",
        )

    # Try each model with failover
    last_error = ""
    for attempt in range(len(models)):
        model_id = _pick_model()
        if model_id is None:
            break

        metrics = _build_ragas_metrics(model_id)
        if metrics is None:
            _mark_model_failed(model_id)
            last_error = f"Failed to build metrics for {model_id}"
            continue

        # Faithfulness and AnswerRelevancy always run (no reference needed)
        metric_list = [metrics["faithfulness"], metrics["answer_relevancy"]]
        # ContextPrecision and ContextRecall need reference
        if reference:
            metric_list.append(metrics["context_precision"])
            metric_list.append(metrics["context_recall"])

        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(_run_ragas_sync, sample, metric_list, model_id),
                timeout=timeout_seconds,
            )
            if result.error and "FAILED" in result.faithfulness_status:
                # Evaluation failed — try next model
                _mark_model_failed(model_id)
                last_error = result.error
                log.warning(
                    "ragas_model_failed",
                    model=model_id,
                    error=result.error,
                    attempt=attempt + 1,
                )
                continue

            # Success — clear cooldown for this model
            _mark_model_ok(model_id)
            return result

        except asyncio.TimeoutError:
            _mark_model_failed(model_id)
            last_error = f"RAGAS evaluation timed out after {timeout_seconds}s on {model_id}"
            log.warning("ragas_evaluation_timeout", model=model_id, timeout=timeout_seconds)
        except Exception as exc:
            _mark_model_failed(model_id)
            last_error = f"{model_id}: {exc}"
            log.warning("ragas_evaluation_error", model=model_id, error=str(exc))

    # All models failed
    return RAGASResult(
        faithfulness_status="FAILED",
        answer_relevancy_status="FAILED",
        context_precision_status="FAILED",
        context_recall_status="FAILED" if reference else "NOT_EVALUATED",
        error=f"All Gemini models failed. Last error: {last_error}",
    )


async def evaluate_conversation_turn(
    *,
    question: str,
    answer: str,
    retrieved_contexts: list[str],
    conversation_history: list[dict] | None = None,
    reference: str | None = None,
    timeout_seconds: float = 45.0,
) -> RAGASResult:
    """Evaluate a single turn within a conversation context.

    Builds a question that includes conversation history so RAGAS can assess
    context retention and entity continuity across turns.
    """
    if not retrieved_contexts:
        return RAGASResult(
            faithfulness_status="NOT_EVALUATED",
            answer_relevancy_status="NOT_EVALUATED",
            context_precision_status="NOT_EVALUATED",
            context_recall_status="NOT_EVALUATED",
            error="No retrieved contexts available for evaluation",
        )

    # Build enriched question with conversation history for RAGAS
    enriched_question = question
    if conversation_history:
        history_parts = []
        for h in conversation_history:
            history_parts.append(f"User: {h.get('question', '')}")
            history_parts.append(f"Assistant: {h.get('answer', '')[:300]}")
        history_text = "\n".join(history_parts)
        enriched_question = f"Conversation history:\n{history_text}\n\nCurrent question: {question}"

    return await evaluate_interaction(
        question=enriched_question,
        answer=answer,
        retrieved_contexts=retrieved_contexts,
        reference=reference,
        timeout_seconds=timeout_seconds,
    )


def _run_ragas_sync(
    sample: SingleTurnSample, metrics: list, model_id: str
) -> RAGASResult:
    """Run ragas evaluate synchronously (called from thread)."""
    try:
        from ragas import EvaluationDataset

        eval_dataset = EvaluationDataset(samples=[sample])
        result = ragas_evaluate(dataset=eval_dataset, metrics=metrics, show_progress=False)

        # result.scores is a list of dicts, one per sample
        scores: dict[str, Any] = {}
        if result.scores and isinstance(result.scores, list) and len(result.scores) > 0:
            scores = result.scores[0]
        elif isinstance(result.scores, dict):
            scores = result.scores

        return RAGASResult(
            faithfulness=scores.get("faithfulness"),
            faithfulness_status="COMPLETED" if scores.get("faithfulness") is not None else "NOT_EVALUATED",
            answer_relevancy=scores.get("answer_relevancy"),
            answer_relevancy_status="COMPLETED" if scores.get("answer_relevancy") is not None else "NOT_EVALUATED",
            context_precision=scores.get("context_precision"),
            context_precision_status="COMPLETED" if scores.get("context_precision") is not None else "NOT_EVALUATED",
            context_recall=scores.get("context_recall"),
            context_recall_status="COMPLETED" if scores.get("context_recall") is not None else (
                "NOT_EVALUATED" if not sample.reference else "FAILED"
            ),
            evaluation_model=model_id,
            raw_scores=scores,
        )
    except Exception as exc:
        return RAGASResult(
            faithfulness_status="FAILED",
            answer_relevancy_status="FAILED",
            context_precision_status="FAILED",
            context_recall_status="FAILED",
            evaluation_model=model_id,
            error=str(exc),
        )
