"""Tests for the golden dataset."""
from evaluation.golden_dataset import BUILTIN_SAMPLES, GoldenSample, load_golden_dataset


def test_builtin_samples_have_questions():
    assert len(BUILTIN_SAMPLES) > 0
    for sample in BUILTIN_SAMPLES:
        assert sample.question


def test_builtin_samples_have_intent():
    for sample in BUILTIN_SAMPLES:
        assert sample.expected_intent


def test_load_builtin_dataset():
    dataset = load_golden_dataset()
    assert dataset.name == "Built-in"
    assert len(dataset.samples) > 0


def test_golden_sample_defaults():
    sample = GoldenSample(question="test?")
    assert sample.expected_answer_contains == []
    assert sample.expected_entities == []
    assert sample.expected_intent == ""
    assert sample.expected_no_answer is False


def test_no_answer_samples():
    no_answer_samples = [s for s in BUILTIN_SAMPLES if s.expected_no_answer]
    assert len(no_answer_samples) >= 2
    for s in no_answer_samples:
        assert s.expected_no_answer is True
