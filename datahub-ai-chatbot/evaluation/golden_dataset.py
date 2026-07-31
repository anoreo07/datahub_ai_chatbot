"""Golden dataset of ground-truth Q&A pairs for RAG evaluation."""
import datetime
from dataclasses import dataclass, field


@dataclass
class GoldenSample:
    question: str
    expected_answer_contains: list[str] = field(default_factory=list)
    expected_entities: list[str] = field(default_factory=list)
    expected_intent: str = ""
    expected_no_answer: bool = False
    tags: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class GoldenDataset:
    name: str = ""
    description: str = ""
    samples: list[GoldenSample] = field(default_factory=list)
    created_at: str = ""


BUILTIN_SAMPLES: list[GoldenSample] = [
    GoldenSample(
        question="Doanh thu quý 4 năm 2023 là bao nhiêu?",
        expected_entities=["urn:li:dataset:sales_revenue"],
        expected_intent="DOCUMENT_QA",
        tags=["revenue", "dataset"],
        notes="Tests basic dataset content retrieval",
    ),
    GoldenSample(
        question="Ai là owner của dataset revenue?",
        expected_entities=["urn:li:dataset:sales_revenue"],
        expected_intent="OWNER_LOOKUP",
        tags=["owner", "dataset"],
    ),
    GoldenSample(
        question="Revenue Dataset có những field gì?",
        expected_entities=["urn:li:dataset:sales_revenue"],
        expected_intent="SCHEMA_LOOKUP",
        tags=["schema", "dataset"],
    ),
    GoldenSample(
        question="Glossary term Gross Profit là gì?",
        expected_entities=["urn:li:glossaryTerm:GrossProfit"],
        expected_intent="TERM_DEFINITION",
        tags=["glossary"],
    ),
    GoldenSample(
        question="Có entity tên là Customer Segmentation không?",
        expected_entities=["urn:li:dataset:customer_segmentation"],
        expected_intent="ENTITY_EXISTS",
        tags=["existence"],
    ),
    GoldenSample(
        question="Dataset Revenue lấy dữ liệu từ đâu?",
        expected_entities=["urn:li:dataset:sales_revenue"],
        expected_intent="LINEAGE",
        tags=["lineage"],
    ),
    GoldenSample(
        question="Link DataHub của Revenue Dataset?",
        expected_entities=["urn:li:dataset:sales_revenue"],
        expected_intent="DATAHUB_URL",
        tags=["url"],
    ),
    GoldenSample(
        question="Những dataset nào gắn term Gross Profit?",
        expected_entities=["urn:li:glossaryTerm:GrossProfit"],
        expected_intent="TERM_TO_DATASETS",
        tags=["glossary", "dataset"],
    ),
    GoldenSample(
        question="Công ty XYZ không tồn tại có tồn tại không?",
        expected_no_answer=True,
        expected_intent="ENTITY_EXISTS",
        tags=["no-answer", "nonexistent"],
        notes="Should say entity does not exist",
    ),
    GoldenSample(
        question="Màu sắc yêu thích của CEO là gì?",
        expected_no_answer=True,
        expected_intent="GENERAL",
        tags=["no-answer", "unanswerable"],
        notes="Completely unanswerable question not in context",
    ),
    GoldenSample(
        question="Dataset revenue có mấy field?",
        expected_entities=["urn:li:dataset:sales_revenue"],
        expected_intent="SCHEMA_LOOKUP",
        tags=["schema", "dataset"],
    ),
    GoldenSample(
        question="Dashboard Monthly Revenue có gì?",
        expected_entities=["urn:li:dashboard:monthly_revenue"],
        expected_intent="FIND_ENTITY",
        tags=["dashboard"],
    ),
    GoldenSample(
        question="Tổng quan về dữ liệu bán hàng",
        expected_entities=["urn:li:dataset:sales_revenue"],
        expected_intent="GENERAL",
        tags=["general"],
    ),
    GoldenSample(
        question="So sánh doanh thu giữa các quý",
        expected_intent="GENERAL",
        tags=["general"],
    ),
]


def load_golden_dataset(path: str | None = None) -> GoldenDataset:
    if path:
        import json
        with open(path) as f:
            data = json.load(f)
        samples = [GoldenSample(**s) for s in data.get("samples", [])]
        return GoldenDataset(
            name=data.get("name", "Custom"),
            description=data.get("description", ""),
            samples=samples,
            created_at=data.get("created_at", ""),
        )
    return GoldenDataset(
        name="Built-in",
        description="Built-in golden dataset for basic RAG evaluation",
        samples=BUILTIN_SAMPLES,
        created_at=datetime.datetime.now(datetime.UTC).isoformat(),
    )
