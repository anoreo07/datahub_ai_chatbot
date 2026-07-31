"""Tests for quality metrics."""
from evaluation.metrics import (
    compute_answer_accuracy,
    compute_entity_recall,
    compute_faithfulness,
    compute_no_answer_accuracy,
)


def test_entity_recall_perfect():
    result = compute_entity_recall(["a", "b"], ["a", "b"])
    assert result["recall"] == 1.0
    assert result["precision"] == 1.0
    assert result["f1"] == 1.0


def test_entity_recall_partial():
    result = compute_entity_recall(["a", "b"], ["a"])
    assert result["recall"] == 0.5
    assert result["precision"] == 1.0


def test_entity_recall_none():
    result = compute_entity_recall(["a", "b"], [])
    assert result["recall"] == 0.0
    assert result["precision"] == 0.0


def test_entity_recall_empty_expected():
    result = compute_entity_recall([], ["a"])
    assert result["recall"] == 1.0
    assert result["precision"] == 1.0


def test_answer_accuracy_perfect():
    result = compute_answer_accuracy(["revenue", "dataset"], "The revenue dataset shows ...")
    assert result["accuracy"] == 1.0
    assert "revenue" in result["matched_terms"]


def test_answer_accuracy_partial():
    result = compute_answer_accuracy(["revenue", "gross", "profit"], "Revenue is total sales.")
    acc = result["accuracy"]
    assert 0.3 <= acc <= 0.34


def test_answer_accuracy_empty():
    result = compute_answer_accuracy([], "Some answer")
    assert result["accuracy"] == 1.0


def test_no_answer_accuracy_correct_refusal():
    result = compute_no_answer_accuracy(True, "Xin lỗi, tôi không tìm thấy dữ liệu.", "low")
    assert result["correct"] is True


def test_no_answer_accuracy_incorrect_refusal():
    result = compute_no_answer_accuracy(False, "Xin lỗi, tôi không tìm thấy dữ liệu.", "low")
    assert result["correct"] is False


def test_no_answer_accuracy_answer_given():
    result = compute_no_answer_accuracy(False, "Doanh thu là 100 tỷ.", "high")
    assert result["correct"] is True


def test_faithfulness_high():
    result = compute_faithfulness(
        "Doanh thu quý 4 là 100 tỷ. Lợi nhuận tăng 20%.",
        "doanh thu quý 4 là 100 tỷ và lợi nhuận tăng 20% theo báo cáo tài chính",
    )
    assert result["faithfulness"] >= 0.5


def test_faithfulness_empty_sentences():
    result = compute_faithfulness("", "some context")
    assert result["faithfulness"] == 1.0


def test_faithfulness_short_sentence():
    result = compute_faithfulness("Hi.", "some context")
    assert result["faithfulness"] == 1.0
