"""Comprehensive pipeline evaluator -- runs reference samples through the full pipeline.

Captures pipeline traces, computes system metrics, runs RAGAS, classifies root causes,
and produces EvaluationReport with full diagnostics.
"""

from __future__ import annotations

import datetime as _dt
from typing import Any, Callable, Awaitable

import structlog

from evaluation.models import (
    EvaluationReport,
    EvaluationResult,
    FailureLayer,
    FailureReason,
    PipelineStep,
    PipelineTrace,
    ReferenceDataset,
    ReferenceSample,
    RootCause,
    SystemMetrics,
)
from evaluation.diagnostics import classify_root_cause
from evaluation.system_metrics import compute_system_metrics, compute_metrics_from_answer_only
from evaluation.ragas_evaluator import evaluate_interaction, RAGASResult

log = structlog.get_logger(__name__)


class PipelineEvaluator:
    """Runs evaluation samples through the full pipeline and captures traces."""

    def __init__(
        self,
        chat_service_fn: Callable[..., Awaitable[Any]],
        *,
        ragas_enabled: bool = True,
        ragas_timeout: float = 45.0,
        capture_traces: bool = True,
    ):
        self._chat_fn = chat_service_fn
        self._ragas_enabled = ragas_enabled
        self._ragas_timeout = ragas_timeout
        self._capture_traces = capture_traces

    async def evaluate(
        self,
        dataset: ReferenceDataset,
        *,
        on_progress: Callable[[int, int], Awaitable[None]] | None = None,
    ) -> EvaluationReport:
        results: list[EvaluationResult] = []
        for idx, sample in enumerate(dataset.samples):
            try:
                result = await self._evaluate_sample(sample)
                results.append(result)
            except Exception as exc:
                log.warning("eval_sample_error", sample_id=sample.id, error=str(exc))
                results.append(EvaluationResult(
                    sample_id=sample.id,
                    question=sample.question,
                    root_cause=RootCause(
                        primary_layer=FailureLayer.EVALUATION,
                        primary_reason=FailureReason.EVALUATION_ERROR,
                        detail=str(exc),
                    ),
                    evaluation_error=str(exc),
                    timestamp=_dt.datetime.now(_dt.timezone.utc).isoformat(),
                ))
            if on_progress:
                await on_progress(idx + 1, len(dataset.samples))

        return EvaluationReport(
            name=f"eval_{dataset.name}_{_dt.datetime.now(_dt.timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            timestamp=_dt.datetime.now(_dt.timezone.utc).isoformat(),
            dataset_name=dataset.name,
            dataset_version=dataset.version,
            total_samples=len(dataset.samples),
            results=results,
        )

    async def _evaluate_sample(self, sample: ReferenceSample) -> EvaluationResult:
        trace = PipelineTrace(trace_id=sample.id, question=sample.question)

        # Step 1: Run the chat pipeline
        step_chat = PipelineStep(step_name="chat_pipeline")
        try:
            response = await self._chat_fn(sample.question)
            step_chat.status = "ok"
            step_chat.output_summary = f"intent={getattr(response, 'intent', '')}, confidence={getattr(response, 'confidence', '')}"
        except Exception as exc:
            step_chat.status = "error"
            step_chat.error = str(exc)
            trace.add_step(step_chat)
            return self._build_error_result(sample, trace, exc)
        trace.add_step(step_chat)

        # Extract data from response
        answer_text = getattr(response, "answer", "")
        intent = getattr(response, "intent", "")
        confidence = getattr(response, "confidence", "low")
        entities = getattr(response, "entities", [])
        citations = getattr(response, "citations", [])

        actual_entity_urns = [
            e.urn if hasattr(e, "urn") else str(e) for e in entities
        ] if entities else []
        actual_citation_urns = [
            c.entity_urn for c in citations if hasattr(c, "entity_urn")
        ] if citations else []

        trace.intent_detected = intent
        trace.entity_resolved_urn = actual_entity_urns[0] if actual_entity_urns else None
        trace.entity_resolved_name = (
            entities[0].name if entities and hasattr(entities[0], "name") else None
        )
        trace.entity_candidates = actual_entity_urns
        trace.citation_urns = actual_citation_urns
        trace.citation_ids = [c.id if hasattr(c, "id") else "" for c in citations]
        trace.answer_text = answer_text[:500]
        trace.confidence = confidence
        trace.retrieval_results_count = getattr(response, "result_count", 0) or len(entities)

        # Step 2: Compute system metrics
        step_metrics = PipelineStep(step_name="system_metrics")
        retrieved_contexts = self._extract_contexts(response)
        system_metrics = compute_system_metrics(
            trace=trace,
            reference=sample.expected,
            answer_text=answer_text,
            confidence=confidence,
            retrieved_contexts=retrieved_contexts,
            citation_urns=actual_citation_urns,
        )
        step_metrics.status = "ok"
        step_metrics.metadata = system_metrics.to_dict()
        trace.add_step(step_metrics)

        # Step 3: RAGAS evaluation (optional)
        ragas_faithfulness = None
        ragas_answer_relevancy = None
        ragas_context_precision = None
        ragas_context_recall = None
        ragas_model = ""
        ragas_error = None

        if self._ragas_enabled and retrieved_contexts:
            step_ragas = PipelineStep(step_name="ragas_evaluation")
            try:
                ragas_result: RAGASResult = await evaluate_interaction(
                    question=sample.question,
                    answer=answer_text,
                    retrieved_contexts=retrieved_contexts,
                    reference=sample.expected.answer_contains[0] if sample.expected.answer_contains else None,
                    timeout_seconds=self._ragas_timeout,
                )
                ragas_faithfulness = ragas_result.faithfulness
                ragas_answer_relevancy = ragas_result.answer_relevancy
                ragas_context_precision = ragas_result.context_precision
                ragas_context_recall = ragas_result.context_recall
                ragas_model = ragas_result.evaluation_model
                ragas_error = ragas_result.error
                step_ragas.status = "ok" if not ragas_result.error else "error"
                step_ragas.metadata = ragas_result.raw_scores
                step_ragas.error = ragas_result.error
            except Exception as exc:
                step_ragas.status = "error"
                step_ragas.error = str(exc)
                ragas_error = str(exc)
            trace.add_step(step_ragas)

        # Step 4: Classify root cause
        step_diag = PipelineStep(step_name="root_cause_classification")
        root_cause = classify_root_cause(
            trace=trace,
            reference=sample.expected,
            system_metrics=system_metrics,
            answer_text=answer_text,
            confidence=confidence,
            retrieved_contexts=retrieved_contexts,
            ragas_faithfulness=ragas_faithfulness,
        )
        step_diag.status = "ok"
        step_diag.metadata = root_cause.to_dict()
        trace.add_step(step_diag)

        return EvaluationResult(
            sample_id=sample.id,
            question=sample.question,
            system_metrics=system_metrics,
            ragas_faithfulness=ragas_faithfulness,
            ragas_faithfulness_status="COMPLETED" if ragas_faithfulness is not None else "NOT_EVALUATED",
            ragas_answer_relevancy=ragas_answer_relevancy,
            ragas_answer_relevancy_status="COMPLETED" if ragas_answer_relevancy is not None else "NOT_EVALUATED",
            ragas_context_precision=ragas_context_precision,
            ragas_context_precision_status="COMPLETED" if ragas_context_precision is not None else "NOT_EVALUATED",
            ragas_context_recall=ragas_context_recall,
            ragas_context_recall_status="COMPLETED" if ragas_context_recall is not None else "NOT_EVALUATED",
            root_cause=root_cause,
            pipeline_trace=trace if self._capture_traces else None,
            evaluation_model=ragas_model,
            evaluation_error=ragas_error,
            timestamp=_dt.datetime.now(_dt.timezone.utc).isoformat(),
        )

    def _build_error_result(
        self, sample: ReferenceSample, trace: PipelineTrace, exc: Exception,
    ) -> EvaluationResult:
        return EvaluationResult(
            sample_id=sample.id,
            question=sample.question,
            system_metrics=SystemMetrics(),
            root_cause=RootCause(
                primary_layer=FailureLayer.EVALUATION,
                primary_reason=FailureReason.EVALUATION_ERROR,
                detail=str(exc), confidence=1.0,
            ),
            pipeline_trace=trace,
            evaluation_error=str(exc),
            timestamp=_dt.datetime.now(_dt.timezone.utc).isoformat(),
        )

    def _extract_contexts(self, response: Any) -> list[str]:
        contexts = []
        if hasattr(response, "retrieved_contexts") and response.retrieved_contexts:
            for ctx in response.retrieved_contexts:
                if isinstance(ctx, str):
                    contexts.append(ctx)
                elif hasattr(ctx, "content"):
                    contexts.append(ctx.content)
                else:
                    contexts.append(str(ctx))
        if not contexts and hasattr(response, "citations") and response.citations:
            for cit in response.citations:
                if hasattr(cit, "entity_name"):
                    contexts.append(cit.entity_name)
        return contexts


class RetrospectiveEvaluator:
    """Evaluates existing interaction logs (no pipeline trace, limited metrics)."""

    async def evaluate_from_logs(
        self,
        interactions: list[dict[str, Any]],
        reference_samples: list[ReferenceSample],
    ) -> EvaluationReport:
        ref_map = {s.question: s for s in reference_samples}
        results: list[EvaluationResult] = []

        for interaction in interactions:
            question = interaction.get("question", "")
            answer = interaction.get("answer", "")
            confidence = interaction.get("confidence", "low")
            reference = ref_map.get(question)

            system_metrics = compute_metrics_from_answer_only(
                answer_text=answer,
                confidence=confidence,
                reference=reference.expected if reference else None,
            )

            root_cause = RootCause(primary_layer=FailureLayer.UNKNOWN, confidence=None)
            if reference:
                root_cause = classify_root_cause(
                    trace=PipelineTrace(
                        trace_id=interaction.get("trace_id", ""),
                        question=question,
                        intent_detected=interaction.get("intent", ""),
                    ),
                    reference=reference.expected,
                    system_metrics=system_metrics,
                    answer_text=answer,
                    confidence=confidence,
                    retrieved_contexts=[],
                )

            results.append(EvaluationResult(
                sample_id=interaction.get("trace_id", ""),
                question=question,
                system_metrics=system_metrics,
                ragas_faithfulness=interaction.get("faithfulness"),
                ragas_faithfulness_status=interaction.get("faithfulness_status", "NOT_EVALUATED"),
                ragas_answer_relevancy=interaction.get("answer_relevancy"),
                ragas_answer_relevancy_status=interaction.get("answer_relevancy_status", "NOT_EVALUATED"),
                ragas_context_precision=interaction.get("context_precision"),
                ragas_context_precision_status=interaction.get("context_precision_status", "NOT_EVALUATED"),
                ragas_context_recall=interaction.get("context_recall"),
                ragas_context_recall_status=interaction.get("context_recall_status", "NOT_EVALUATED"),
                root_cause=root_cause,
                evaluation_model=interaction.get("evaluation_model", ""),
                timestamp=interaction.get("created_at", ""),
            ))

        return EvaluationReport(
            name="retrospective_eval",
            timestamp=_dt.datetime.now(_dt.timezone.utc).isoformat(),
            dataset_name="retrospective",
            dataset_version="1.0",
            total_samples=len(results),
            results=results,
        )
