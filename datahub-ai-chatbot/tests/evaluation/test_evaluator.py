"""Tests for the evaluation runner."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from evaluation.evaluator import EvaluationReport, Evaluator
from evaluation.golden_dataset import GoldenDataset, GoldenSample


@pytest.mark.asyncio
async def test_evaluator_empty_dataset():
    chat_service = AsyncMock()
    evaluator = Evaluator(chat_service)
    dataset = GoldenDataset(name="empty", samples=[])
    report = await evaluator.evaluate(dataset)
    assert report.total_samples == 0
    assert report.dataset_name == "empty"


@pytest.mark.asyncio
async def test_evaluator_single_sample():
    chat_service = AsyncMock()
    chat_service.answer = AsyncMock(return_value=MagicMock(
        answer="Revenue dataset has data.",
        intent="DOCUMENT_QA",
        entities=[],
        confidence="high",
    ))
    evaluator = Evaluator(chat_service)
    sample = GoldenSample(
        question="What is revenue?",
        expected_entities=["urn:li:dataset:revenue"],
        expected_intent="DOCUMENT_QA",
    )
    dataset = GoldenDataset(name="test", samples=[sample])
    report = await evaluator.evaluate(dataset)
    assert report.total_samples == 1
    assert len(report.results) == 1
    result = report.results[0]
    assert result.intent_match is True
    assert result.error is None


@pytest.mark.asyncio
async def test_evaluator_handles_error():
    chat_service = AsyncMock()
    chat_service.answer = AsyncMock(side_effect=ValueError("something broke"))
    evaluator = Evaluator(chat_service)
    sample = GoldenSample(question="broken?", expected_intent="GENERAL")
    dataset = GoldenDataset(name="test", samples=[sample])
    report = await evaluator.evaluate(dataset)
    assert report.total_samples == 1
    assert report.results[0].error is not None


def test_report_properties():
    from evaluation.evaluator import SampleResult
    from evaluation.metrics import (
        compute_answer_accuracy,
        compute_entity_recall,
        compute_no_answer_accuracy,
    )
    result = SampleResult(
        question="test?",
        expected_intent="GENERAL",
        actual_intent="GENERAL",
        expected_entities=["a"],
        actual_entities=["a"],
        expected_no_answer=False,
        actual_answer="yes",
        actual_confidence="high",
        entity_recall=compute_entity_recall(["a"], ["a"]),
        answer_accuracy=compute_answer_accuracy([], "yes"),
        no_answer_accuracy=compute_no_answer_accuracy(False, "yes", "high"),
        faithfulness={"faithfulness": 0.9, "supported": 1, "unsupported": [], "total_sentences": 1},
        intent_match=True,
    )
    report = EvaluationReport(timestamp="now", dataset_name="t", total_samples=1, results=[result])
    assert report.entity_recall.value == 1.0
    assert report.answer_accuracy.value == 1.0
    assert report.no_answer_accuracy.value == 1.0
    assert report.faithfulness.value == 0.9
    assert report.intent_accuracy.value == 1.0


def test_report_to_dict():
    from evaluation.evaluator import SampleResult
    from evaluation.metrics import (
        compute_answer_accuracy,
        compute_entity_recall,
        compute_no_answer_accuracy,
    )
    result = SampleResult(
        question="test?",
        expected_intent="GENERAL",
        actual_intent="GENERAL",
        expected_entities=[],
        actual_entities=[],
        expected_no_answer=False,
        actual_answer="ok",
        actual_confidence="high",
        entity_recall=compute_entity_recall([], []),
        answer_accuracy=compute_answer_accuracy([], "ok"),
        no_answer_accuracy=compute_no_answer_accuracy(False, "ok", "high"),
        faithfulness={"faithfulness": 1.0, "supported": 0, "unsupported": [], "total_sentences": 0},
        intent_match=True,
    )
    report = EvaluationReport(timestamp="now", dataset_name="t", total_samples=1, results=[result])
    d = report.to_dict()
    assert d["total_samples"] == 1
    assert d["dataset_name"] == "t"
    assert "metrics" in d
    assert "samples" in d
