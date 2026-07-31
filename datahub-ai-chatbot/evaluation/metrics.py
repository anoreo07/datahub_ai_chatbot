"""Quality metrics for RAG evaluation."""
import re
from dataclasses import dataclass, field


@dataclass
class MetricResult:
    name: str
    value: float
    total: int
    passed: int
    details: list[dict] = field(default_factory=list)


def compute_entity_recall(
    expected_entities: list[str],
    actual_entities: list[str],
) -> dict:
    expected_set = set(expected_entities)
    actual_set = set(actual_entities)
    if not expected_set:
        return {"recall": 1.0, "precision": 1.0, "f1": 1.0, "matched": 0, "expected": 0}
    matched = expected_set & actual_set
    recall = len(matched) / len(expected_set) if expected_set else 1.0
    precision = len(matched) / len(actual_set) if actual_set else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    return {"recall": recall, "precision": precision, "f1": f1, "matched": list(matched), "expected": list(expected_set)}


def compute_answer_accuracy(expected_contains: list[str], actual_answer: str) -> dict:
    if not expected_contains:
        return {"accuracy": 1.0, "matched_terms": [], "missing_terms": []}
    actual_lower = actual_answer.lower()
    matched = [t for t in expected_contains if t.lower() in actual_lower]
    missing = [t for t in expected_contains if t.lower() not in actual_lower]
    accuracy = len(matched) / len(expected_contains) if expected_contains else 1.0
    return {"accuracy": accuracy, "matched_terms": matched, "missing_terms": missing}


def compute_no_answer_accuracy(
    expected_no_answer: bool,
    actual_answer: str,
    actual_confidence: str,
    no_answer_phrases: list[str] | None = None,
) -> dict:
    phrases = no_answer_phrases or [
        "không tìm thấy", "không có", "không thể", "xin lỗi",
        "không biết", "không đủ", "I don't know", "cannot",
        "not enough", "not found", "no information",
    ]
    is_no_answer = any(p in actual_answer.lower() for p in phrases) or actual_confidence == "low"
    correct = is_no_answer if expected_no_answer else not is_no_answer
    return {
        "correct": correct,
        "expected_no_answer": expected_no_answer,
        "actual_no_answer": is_no_answer,
        "actual_confidence": actual_confidence,
    }


def compute_faithfulness(answer: str, context_text: str) -> dict:
    answer_sentences = re.split(r'(?<=[.!?])\s+', answer.strip())
    if not answer_sentences:
        return {"faithfulness": 1.0, "supported": 0, "unsupported": [], "total_sentences": 0}
    context_lower = context_text.lower()
    supported = 0
    unsupported = []
    for sentence in answer_sentences:
        sentence = sentence.strip()
        if not sentence or len(sentence) < 5:
            continue
        key_words = [w for w in re.findall(r'\b[a-zA-Z]{4,}\b', sentence) if w.lower() not in
                     {"this", "that", "with", "from", "have", "been", "were", "what", "when", "where", "there"}]
        if not key_words:
            supported += 1
            continue
        overlap = sum(1 for w in key_words if w.lower() in context_lower)
        ratio = overlap / len(key_words)
        supported += 1
        if ratio < 0.3:
            unsupported.append(sentence)
    faithfulness = (len(answer_sentences) - len(unsupported)) / len(answer_sentences) if answer_sentences else 0.0
    return {"faithfulness": faithfulness, "supported": len(answer_sentences) - len(unsupported),
            "unsupported": unsupported, "total_sentences": len(answer_sentences)}
