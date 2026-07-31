"""RAG evaluation runner."""
import datetime
from dataclasses import dataclass, field
from typing import Any

import structlog

from evaluation.golden_dataset import GoldenDataset, GoldenSample
from evaluation.metrics import (
    MetricResult,
    compute_answer_accuracy,
    compute_entity_recall,
    compute_faithfulness,
    compute_no_answer_accuracy,
)

log = structlog.get_logger()


@dataclass
class SampleResult:
    question: str
    expected_intent: str
    actual_intent: str
    expected_entities: list[str]
    actual_entities: list[str]
    expected_no_answer: bool
    actual_answer: str
    actual_confidence: str
    entity_recall: dict
    answer_accuracy: dict
    no_answer_accuracy: dict
    faithfulness: dict
    intent_match: bool
    error: str | None = None


@dataclass
class EvaluationReport:
    timestamp: str
    dataset_name: str
    total_samples: int
    results: list[SampleResult] = field(default_factory=list)

    @property
    def entity_recall(self) -> MetricResult:
        total = len(self.results)
        passed = sum(1 for r in self.results if r.entity_recall.get("recall", 0) >= 0.5)
        avg = sum(r.entity_recall.get("recall", 0) for r in self.results) / total if total else 0.0
        return MetricResult(name="Entity Recall", value=avg, total=total, passed=passed)

    @property
    def answer_accuracy(self) -> MetricResult:
        total = len(self.results)
        passed = sum(1 for r in self.results if r.answer_accuracy.get("accuracy", 0) >= 0.5)
        avg = sum(r.answer_accuracy.get("accuracy", 0) for r in self.results) / total if total else 0.0
        return MetricResult(name="Answer Accuracy", value=avg, total=total, passed=passed)

    @property
    def no_answer_accuracy(self) -> MetricResult:
        total = len(self.results)
        passed = sum(1 for r in self.results if r.no_answer_accuracy.get("correct", False))
        avg = passed / total if total else 0.0
        return MetricResult(name="No-Answer Accuracy", value=avg, total=total, passed=passed)

    @property
    def faithfulness(self) -> MetricResult:
        scores = [r.faithfulness.get("faithfulness", 0) for r in self.results if r.faithfulness]
        total = len(scores)
        passed = sum(1 for s in scores if s >= 0.7)
        avg = sum(scores) / total if total else 0.0
        return MetricResult(name="Faithfulness", value=avg, total=total, passed=passed)

    @property
    def intent_accuracy(self) -> MetricResult:
        total = len(self.results)
        passed = sum(1 for r in self.results if r.intent_match)
        avg = passed / total if total else 0.0
        return MetricResult(name="Intent Accuracy", value=avg, total=total, passed=passed)

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "dataset_name": self.dataset_name,
            "total_samples": self.total_samples,
            "metrics": {
                "entity_recall": {"value": self.entity_recall.value, "passed": self.entity_recall.passed,
                                  "total": self.entity_recall.total},
                "answer_accuracy": {"value": self.answer_accuracy.value, "passed": self.answer_accuracy.passed,
                                    "total": self.answer_accuracy.total},
                "no_answer_accuracy": {"value": self.no_answer_accuracy.value,
                                       "passed": self.no_answer_accuracy.passed,
                                       "total": self.no_answer_accuracy.total},
                "faithfulness": {"value": self.faithfulness.value, "passed": self.faithfulness.passed,
                                 "total": self.faithfulness.total},
                "intent_accuracy": {"value": self.intent_accuracy.value, "passed": self.intent_accuracy.passed,
                                    "total": self.intent_accuracy.total},
            },
            "samples": [
                {
                    "question": r.question,
                    "expected_intent": r.expected_intent,
                    "actual_intent": r.actual_intent,
                    "intent_match": r.intent_match,
                    "expected_entities": r.expected_entities,
                    "actual_entities": r.actual_entities,
                    "entity_recall": r.entity_recall.get("recall", 0),
                    "answer_accuracy": r.answer_accuracy.get("accuracy", 0),
                    "no_answer_correct": r.no_answer_accuracy.get("correct", False),
                    "faithfulness": r.faithfulness.get("faithfulness", 0),
                    "error": r.error,
                }
                for r in self.results
            ],
        }

    def print_summary(self) -> None:
        print(f"\n{'=' * 60}")
        print(f"Evaluation Report: {self.dataset_name}")
        print(f"Timestamp: {self.timestamp}")
        print(f"Total Samples: {self.total_samples}")
        print(f"{'=' * 60}")
        for metric in [self.entity_recall, self.answer_accuracy, self.no_answer_accuracy,
                        self.faithfulness, self.intent_accuracy]:
            print(f"  {metric.name}: {metric.value:.2%} ({metric.passed}/{metric.total})")
        print(f"{'=' * 60}")


class Evaluator:
    def __init__(self, chat_service: Any) -> None:
        self._chat_service = chat_service

    async def evaluate(self, dataset: GoldenDataset) -> EvaluationReport:
        results: list[SampleResult] = []
        for sample in dataset.samples:
            result = await self._evaluate_sample(sample)
            results.append(result)
        return EvaluationReport(
            timestamp=datetime.datetime.now(datetime.UTC).isoformat(),
            dataset_name=dataset.name,
            total_samples=len(dataset.samples),
            results=results,
        )

    async def _evaluate_sample(self, sample: GoldenSample) -> SampleResult:
        try:
            response = await self._chat_service.answer(sample.question)
        except Exception as e:
            log.error("evaluation_sample_error", question=sample.question[:50], error=str(e))
            return SampleResult(
                question=sample.question,
                expected_intent=sample.expected_intent,
                actual_intent="",
                expected_entities=sample.expected_entities,
                actual_entities=[],
                expected_no_answer=sample.expected_no_answer,
                actual_answer="",
                actual_confidence="low",
                entity_recall={"recall": 0.0, "precision": 0.0, "f1": 0.0, "matched": [], "expected": sample.expected_entities},
                answer_accuracy={"accuracy": 0.0, "matched_terms": [], "missing_terms": sample.expected_answer_contains},
                no_answer_accuracy=compute_no_answer_accuracy(sample.expected_no_answer, "", "low"),
                faithfulness={"faithfulness": 0.0, "supported": 0, "unsupported": [], "total_sentences": 0},
                intent_match=False,
                error=str(e),
            )

        actual_entities = []
        if hasattr(response, "entities") and response.entities:
            actual_entities = [e.urn if hasattr(e, "urn") else str(e) for e in response.entities]
        actual_confidence = getattr(response, "confidence", "low")

        entity_recall = compute_entity_recall(sample.expected_entities, actual_entities)
        answer_accuracy = compute_answer_accuracy(sample.expected_answer_contains, response.answer)
        no_answer_accuracy = compute_no_answer_accuracy(sample.expected_no_answer, response.answer, actual_confidence)
        faithfulness = compute_faithfulness(response.answer, str(getattr(response, "answer", "")))
        intent_match = sample.expected_intent == getattr(response, "intent", "")

        return SampleResult(
            question=sample.question,
            expected_intent=sample.expected_intent,
            actual_intent=getattr(response, "intent", ""),
            expected_entities=sample.expected_entities,
            actual_entities=actual_entities,
            expected_no_answer=sample.expected_no_answer,
            actual_answer=response.answer[:500] if hasattr(response, "answer") else "",
            actual_confidence=actual_confidence,
            entity_recall=entity_recall,
            answer_accuracy=answer_accuracy,
            no_answer_accuracy=no_answer_accuracy,
            faithfulness=faithfulness,
            intent_match=intent_match,
        )
