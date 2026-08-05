"""AI-powered DataHub relevance gate.

Before any DataHub retrieval, search, GraphQL request, or RAG pipeline runs,
an LLM classifies whether the user's message is about DataHub metadata. Only
high-confidence DataHub questions proceed to the pipeline; clearly unrelated
questions get a polite refusal and ambiguous questions ask for clarification.

This deliberately avoids pure rule-based / keyword-based detection - the
decision is delegated to the LLM.
"""

import re
from enum import StrEnum

import structlog

from guardrails.scope import _is_vietnamese
from llm.base import BaseLLM

log = structlog.get_logger()


class DataHubRelevance(StrEnum):
    DATAHUB = "DATAHUB"
    NON_DATAHUB = "NON_DATAHUB"
    UNCERTAIN = "UNCERTAIN"


CLASSIFIER_SYSTEM_PROMPT = (
    "You are an intent router. Your only job is to decide whether a user "
    "message is asking about DataHub metadata.\n\n"
    "DataHub metadata includes: datasets, tables, dashboards, charts, glossary "
    "terms, schema/columns, lineage (upstream/downstream), domain, ownership, "
    "tags, documentation, and any other assets catalogued in a DataHub instance.\n\n"
    "Examples of DataHub questions:\n"
    "- 'dim_warehouse có các trường nào?'\n"
    "- 'OEE là gì?'\n"
    "- 'dataset sales.orders thuộc về domain nào?'\n"
    "- 'Ai sở hữu dataset customer?'\n"
    "- 'Data lineage của dataset sales_order'\n"
    "- 'glossary term 3-way matching là gì?'\n"
    "- 'có bao nhiêu datasets trong hệ thống?'\n"
    "- 'dataset nào có tag PII?'\n\n"
    "Examples of NON-DataHub questions:\n"
    "- 'viết code bubble sort bằng Python'\n"
    "- 'Which number is larger, 9.11 or 9.8?'\n"
    "- 'thủ đô của Pháp là gì?'\n"
    "- 'cách nấu phở'\n"
    "- 'hôm nay là thứ mấy?'\n\n"
    "Reply with EXACTLY one JSON object and nothing else, using this shape:\n"
    '{"relevance": "DATAHUB|NON_DATAHUB|UNCERTAIN"}\n\n'
    "- DATAHUB if the message is clearly about DataHub metadata, datasets, "
    "schema, lineage, glossary, ownership, tags, domains, or data discovery.\n"
    "- NON_DATAHUB if the message is clearly outside DataHub: coding or "
    "algorithms in any language, math puzzles, general knowledge, news, "
    "weather, trivia, recipes, health, or any world knowledge.\n"
    "- UNCERTAIN only if you truly cannot decide."
)


REFUSAL_RESPONSES_VN = [
    "Xin lỗi, mình chỉ hỗ trợ các câu hỏi liên quan đến DataHub và dữ liệu "
    "metadata của hệ thống. Bạn có thể hỏi mình về dataset, schema, lineage, "
    "glossary, owner hoặc các thông tin khác trong DataHub.",
    "Mình hiện được thiết kế để hỗ trợ tra cứu và giải đáp thông tin trong "
    "DataHub. Với câu hỏi này mình chưa thể hỗ trợ, nhưng rất sẵn lòng giúp "
    "bạn về dataset, lineage, schema, documentation hoặc metadata.",
]

REFUSAL_RESPONSES_EN = [
    "Sorry, I only support questions about DataHub and the system's metadata. "
    "You can ask me about datasets, schema, lineage, glossary, owners, or "
    "other information in DataHub.",
]

_CLARIFICATION_VN = (
    "Mình chưa chắc câu hỏi của bạn có liên quan đến DataHub hay không. Bạn có "
    "thể làm rõ thêm về dataset, schema, lineage, glossary, owner hoặc thông tin "
    "metadata cụ thể mà bạn cần không?"
)

_CLARIFICATION_EN = (
    "I'm not sure your question is related to DataHub. Could you clarify which "
    "dataset, schema, lineage, glossary term, or metadata you are looking for?"
)


def parse_relevance(raw: str) -> DataHubRelevance:
    """Parse the LLM's single-token reply into a ``DataHubRelevance``.

    Tolerates JSON wrapping (Fireworks forces ``json_object``) and extra
    whitespace. Returns ``UNCERTAIN`` when no recognized token is present.
    """
    if not raw:
        return DataHubRelevance.UNCERTAIN
    text = re.sub(r"[^A-Za-z]", "", raw.upper())
    # NON_DATAHUB must be checked before DATAHUB (it contains "DATAHUB").
    if "NON_DATAHUB" in text:
        return DataHubRelevance.NON_DATAHUB
    if "UNCERTAIN" in text or "UNSURE" in text:
        return DataHubRelevance.UNCERTAIN
    if "DATAHUB" in text:
        return DataHubRelevance.DATAHUB
    return DataHubRelevance.UNCERTAIN


def refusal_response(question: str) -> str:
    import random

    if _is_vietnamese(question):
        return random.choice(REFUSAL_RESPONSES_VN)
    return random.choice(REFUSAL_RESPONSES_EN)


def clarification_response(question: str) -> str:
    return _CLARIFICATION_VN if _is_vietnamese(question) else _CLARIFICATION_EN


async def classify_datahub_relevance(llm: BaseLLM, question: str) -> DataHubRelevance:
    """Ask the LLM whether ``question`` is about DataHub metadata.

    In mock/test mode the classifier cannot emit a reliable token, so it
    short-circuits to ``DATAHUB`` (let the existing heuristic pipeline decide)
    rather than blocking real queries.
    """
    from config.settings import settings

    if settings.USE_MOCK_LLM:
        return DataHubRelevance.DATAHUB
    try:
        raw = await llm.generate(
            question,
            system_prompt=CLASSIFIER_SYSTEM_PROMPT,
        )
    except Exception:  # noqa: BLE001
        log.exception("ai_intent_classifier_failed", question=question[:100])
        return DataHubRelevance.UNCERTAIN
    relevance = parse_relevance(raw)
    log.info("ai_intent_classifier", question=question[:100], relevance=relevance.value)
    return relevance
