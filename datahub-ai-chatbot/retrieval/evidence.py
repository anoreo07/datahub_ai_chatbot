"""Evidence store for the context-propagation layer.

Each DataHub function turn (schema, lineage, owner, glossary, quality, SQL,
impact, dataset lookup...) records the *structured* metadata it actually
produced as an ``EvidenceRecord`` labelled ``E1``, ``E2``, ... onto the
conversation. Follow-up questions that reference this evidence ("schema vừa
lấy", "field đó", "kết quả vừa rồi", "chỉ dựa trên metadata vừa lấy", anaphora
to the image-derived dataset...) are resolved against the evidence store so the
answer is grounded ONLY in what was already collected — never a fresh, silent
cross-catalog semantic re-search.

Design constraints:
* Evidence is a first-class retrieval signal with provenance (tool, query,
  timestamp, citation ``E<i>``), mirroring how a human analyst would cite "the
  metadata I just fetched".
* ``structured`` carries exactly the extraction that was possible at the time:
  schema ``fields``, ``owners``, ``upstreams``/``downstreams``, ``glossary_terms``,
  ``domain``, ``description``, plus ``focus_field`` (the field last discussed)
  and ``image`` metadata. Follow-up handlers never fetch more than this.
* Detection helpers here are deliberately conservative: they recognise
  evidence *references* and the "metadata-only" *constraint*, and leave plain
  anaphora ("nó", "đó") to the existing coreference pipeline unless a matching
  evidence record exists.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any

_REF_PHRASES = [
    r"schema\s+vừa\s+lấy",
    r"schema\s+vu[a]?\s+lay",
    r"metadata\s+vừa\s+lấy",
    r"metadata\s+vu[a]?\s+lay",
    r"kết\s+quả\s+vừa\s+rồi",
    r"ket\s+qua\s+vua\s+roi",
    r"kết\s+quả\s+vừa\s+lấy",
    r"kết\s+quả\s+trên",
    r"field\s+đó",
    r"field\s+do",
    r"trường\s+đó",
    r"truong\s+do",
    r"cột\s+đó",
    # "field warehouse_id đó", "trường warehouse_id đó" — a named field token
    # immediately before a demonstrative still references the evidence store.
    r"field\s+[a-z0-9_.]+\s+đó",
    r"field\s+[a-z0-9_.]+\s+do",
    r"trường\s+[a-z0-9_.]+\s+đó",
    r"truong\s+[a-z0-9_.]+\s+do",
    r"cột\s+[a-z0-9_.]+\s+đó",
    r"schema\s+đó",
    r"schema\s+trên",
    r"metadata\s+đó",
    r"metadata\s+trên",
    r"vừa\s+lấy",
    r"vua\s+lay",
    r"vừa\s+rồi",
    r"vua\s+roi",
    r"vừa\s+tìm",
    r"vua\s+tim",
    r"từ\s+nãy",
    r"tu\s+nay",
    r"chỉ\s+dựa",
    r"chi\s+dua",
    r"chỉ\s+dùng",
    r"chi\s+dung",
    r"based\s+only",
    r"only\s+(?:using|from|based)",
    r"metadata\s+hiện\s+có",
    r"metadata\s+hien\s+co",
    # Image-derived dataset references: the image itself is context, so a
    # follow-up talking about "trong ảnh / ảnh này / hình này" points back at
    # the image evidence recorded at upload time.
    r"trong\s+ảnh",
    r"trong\s+anh",
    r"ảnh\s+này",
    r"anh\s+nay",
    r"ảnh\s+đó",
    r"anh\s+do",
    r"trong\s+(?:bức\s+|tấm\s+)?hình",
    r"hình\s+này",
    r"hinh\s+nay",
]

_context_ref_re = re.compile(
    r"(?:{})".format("|".join(_REF_PHRASES)), re.I,
)

_CONSTRAINT_PHRASES = [
    r"chỉ\s+dựa\s+trên",
    r"chi\s+dua\s+tren",
    r"chỉ\s+dựa\s+vào",
    r"chi\s+dua\s+vao",
    r"chỉ\s+dùng",
    r"chi\s+dung",
    r"chỉ\s+sử\s+dụng",
    r"chi\s+su\s+dung",
    r"chỉ\s+từ",
    r"based\s+only\s+on",
    r"based\s+solely\s+on",
    r"only\s+using",
    r"only\s+from",
    r"only\s+based",
    # Explicit "do not re-search" constraints: the answer must come from
    # metadata already collected, never a fresh catalog search.
    r"không\s+tìm\s+kiếm\s+thêm",
    r"khong\s+tim\s+kiem\s+them",
    r"không\s+search\s+thêm",
    r"khong\s+search\s+them",
    r"không\s+cần\s+tìm\s+thêm",
    r"khong\s+can\s+tim\s+them",
    r"không\s+tìm\s+thêm",
    r"khong\s+tim\s+them",
]

_context_only_re = re.compile(
    r"(?:{}).{0,40}?(?:vừa\s+lấy|vua\s+lay|vừa\s+rồi|vua\s+roi|"
    r"metadata|kết\s+quả|schema)|"
    r"(?:metadata|kết\s+quả|schema).{0,20}?(?:vừa\s+lấy|vua\s+lay)",
    re.I,
)

_ANAPHORA_RE = re.compile(
    r"\b(?:nó|no|đó|do|ấy|ay|này|nay|đây|day|kia|cái\s+trên|bảng\s+này)\b", re.I,
)

_dotted_ref_re = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_.]*")
_snake_ref_re = re.compile(r"(?<![A-Za-z0-9_])[a-z0-9]+(?:_[a-z0-9]+){1,}")

_INTENT_HINTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(
        r"liên\s+kết|lien\s+ket|join\s+key|join|khóa|khoa|"
        r"liên\s+quan\s+.*field", re.I),
        "join"),
    (re.compile(r"glossary|thuật\s+ngữ|thuat\s+ngu|định\s+nghĩa|dinh\s+nghia", re.I), "glossary"),
    (re.compile(r"owner|sở\s+hữu|so\s+huu|thuộc\s+về\s+ai|thuoc\s+ve\s+ai", re.I), "owner"),
    (re.compile(r"domain|lĩnh\s+vực|linh\s+vuc", re.I), "domain"),
    (re.compile(
        r"downstream|upstream|lineage|ảnh\s+hưởng|anh\s+huong|"
        r"nguồn|nguon", re.I),
        "lineage"),
    (re.compile(r"field|field|trường|truong|cột|cot|column|schema", re.I), "schema"),
    (re.compile(r"sql|truy\s+vấn|truy\s+van|query", re.I), "sql"),
    (re.compile(r"quality|chất\s+lượng|chat\s+luong", re.I), "quality"),
]

_PK_SUFFIX_RE = re.compile(r"(?:^|_)(?:pk|primary_key|id|key|code)$", re.I)

# --------------------------------------------------------------------------- #
# Field-level operations
#
# A follow-up ("warehouse_id có kiểu dữ liệu gì?", "field nào liên quan đến
# warehouse?", "warehouse_id có mô tả gì?") targets ONE field and ONE property
# of the referenced schema. ``FieldOp`` is the structured request so the
# evidence layer answers exactly that instead of re-rendering the whole schema.
# --------------------------------------------------------------------------- #
@dataclass
class FieldOp:
    op: str | None = None          # "get_property" | "find_field"
    property: str | None = None    # data_type | native_data_type | description
                                   #   | nullable | is_primary_key | tags | glossary
    field: str | None = None
    keyword: str | None = None     # find_field: the concept to match fields by


_PROPERTY_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("native_data_type", re.compile(
        r"native\s+(?:data\s+)?type|kiểu\s+native|kieu\s+native|kiểu\s+gốc|kieu\s+goc",
        re.I)),
    ("data_type", re.compile(
        r"kiểu\s+dữ\s+liệu|kieu\s+du\s+lieu|data\s*type|datatype|kiểu\s+type|"
        r"kieu\s+type|\btype\b|kiểu\s+gì|kieu\s+gi|kiểu\s+chi|kieu\s+chi|"
        r"là\s+kiểu\s+gì|la\s+kieu\s+gi|là\s+kiểu\s+chi|la\s+kieu\s+chi",
        re.I)),
    ("description", re.compile(
        r"mô\s+tả|mo\s+ta|ý\s+nghĩa|y\s+nghia|có\s+nghĩa|co\s+nghia|"
        r"giải\s+thích|giai\s+thich|description|\bmeaning\b|"
        r"mô\s+tả\s+gì|mo\s+ta\s+gi",
        re.I)),
    ("glossary", re.compile(
        r"glossary|thuật\s+ngữ|thuat\s+ngu",
        re.I)),
    ("nullable", re.compile(
        r"nullable|bắt\s+buộc|bat\s+buoc|để\s+trống|de\s+trong|"
        r"cho\s+phép\s+null|cho\s+phep\s+null|cho\s+phép\s+trống|cho\s+phep\s+trong|"
        r"null\s+không|null\s+ko|null\s+khong|có\s+null|co\s+null|"
        r"có\s+được\s+null|co\s+duoc\s+null|có\s+thể\s+null|co\s+the\s+null",
        re.I)),
    ("is_primary_key", re.compile(
        r"khóa\s+chính|khoa\s+chinh|primary\s+key|\bprimary\s+key\b",
        re.I)),
    ("tags", re.compile(r"\btags?\b|gắn\s+thẻ|gan\s+the", re.I)),
]

_FIND_FIELD_RE = re.compile(
    r"(?:field|trường|truong|cột|cot|column|thuộc\s+tính|thuoc\s+tinh)"
    r"\s+(?:nào|nao)[^?]{0,40}?"
    r"(?:liên\s+quan|lien\s+quan|liên\s+hệ|lien\s+he|relat(?:e|ed)?|chứa|chua|gắn|gan|"
    r"biểu\s+diễn|bieu\s+dien|biểu\s+thị|bieu\s+thi)"
    r"\s*(?:đến|den|to|với|voi)?\s*"
    r"([a-zà-ỹ0-9 _-]+?)(?:[.!?]|$)",
    re.I,
)

_ENTITY_DOT_REF = re.compile(r"([a-z0-9_]+(?:\.[a-z0-9_]+)+)\.([a-z0-9_]+)", re.I)
_FIELD_OF_ENTITY = re.compile(
    r"\b([a-z0-9_]+)\s+(?:của|cua|of|trong)\s+([a-z0-9_]+(?:\.[a-z0-9_]+)*)",
    re.I,
)
# Looser spaced form: "<field> ... <...> ... trong <entity>" (e.g.
# "warehouse_id có kiểu dữ liệu gì trong fact_inventory_movement"). The
# separator must not cross sentence boundaries and must stay short to avoid
# matching across unrelated clauses.
_FIELD_SPACED_IN_ENTITY = re.compile(
    r"\b([a-z0-9_]+)[^.!?]{0,60}?\btrong\s+(?:dataset\s+)?([a-z0-9_]+(?:\.[a-z0-9_]+)*)",
    re.I,
)


def detect_field_property(question: str) -> str | None:
    q = question or ""
    for prop, pattern in _PROPERTY_PATTERNS:
        if pattern.search(q):
            return prop
    return None


def _field_token(
    question: str,
    known_fields: set[str] | frozenset[str] | None = None,
) -> str | None:
    """The most likely field (column) token named in ``question``.

    ``known_fields`` (when provided) is the set of *real* field names present
    in the conversation's evidence / schema. When it is given, a single bare
    word (no underscore, e.g. "quantity") is accepted only if it matches a real
    field name case-insensitively — never guessed from the lexicon.
    """
    q = question or ""
    m = _dotted_ref_re.search(q)
    if m:
        return m.group(0).split(".")[-1]
    norm = {f.lower() for f in (known_fields or ())}
    if norm:
        for tok in re.findall(r"[a-zà-ỹ0-9]+", q.lower()):
            if tok in norm:
                return tok
    refs = extract_field_refs(q)
    if not refs:
        return None
    field = next((r for r in refs if looks_like_a_field(r)), None)
    return field or refs[-1]


def parse_field_operation(
    question: str,
    known_fields: set[str] | frozenset[str] | None = None,
) -> FieldOp | None:
    """Structured request behind a field-level question.

    Returns ``None`` when the question does not target a single field property
    or a field-find operation (so the caller falls through to the generic
    pipeline untouched). ``known_fields`` (real schema field names) lets
    single-word fields like "quantity" be accepted against the actual schema
    instead of being dropped for not looking like a column.
    """
    q = question or ""
    prop = detect_field_property(q)
    if prop:
        field = _field_token(q, known_fields)
        if field:
            return FieldOp(op="get_property", property=prop, field=field)
    m = _FIND_FIELD_RE.search(q)
    if m and m.group(1).strip():
        return FieldOp(op="find_field", keyword=m.group(1).strip())
    return None


def extract_field_entity(question: str) -> tuple[str | None, str | None]:
    """``(entity, field)`` from an explicit ``field của entity`` / ``entity.field``
    / ``field ... trong entity`` reference, or ``(None, None)`` when the question
    does not carry one."""
    q = question or ""
    m = _FIELD_OF_ENTITY.search(q)
    if m:
        return m.group(2), m.group(1)
    m = _ENTITY_DOT_REF.search(q)
    if m:
        return m.group(1), m.group(2)
    m = _FIELD_SPACED_IN_ENTITY.search(q)
    if m:
        return m.group(2), m.group(1)
    return None, None


@dataclass
class EvidenceRecord:
    """Structured metadata extract produced by one turn's DataHub function."""

    evidence_id: str
    kind: str
    entity_name: str
    entity_urn: str | None
    entity_type: str | None
    tool_name: str
    query: str
    structured: dict[str, Any] = field(default_factory=dict)
    citation: str = ""
    source: str = "retrieval"
    timestamp: float = field(default_factory=time.time)
    snippet: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "kind": self.kind,
            "entity_name": self.entity_name,
            "entity_urn": self.entity_urn,
            "entity_type": self.entity_type,
            "tool_name": self.tool_name,
            "query": self.query,
            "structured": self.structured,
            "citation": self.citation or self.evidence_id,
            "source": self.source,
            "timestamp": self.timestamp,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> EvidenceRecord:
        return EvidenceRecord(
            evidence_id=data.get("evidence_id", ""),
            kind=data.get("kind", ""),
            entity_name=data.get("entity_name", ""),
            entity_urn=data.get("entity_urn"),
            entity_type=data.get("entity_type"),
            tool_name=data.get("tool_name", ""),
            query=data.get("query", ""),
            structured=data.get("structured", {}),
            citation=data.get("citation", ""),
            source=data.get("source", "retrieval"),
            timestamp=data.get("timestamp", time.time()),
        )


def has_context_reference(question: str) -> bool:
    """True when the question points back at previously-collected metadata.

    Matches explicit evidence references ("schema vừa lấy", "field đó",
    "kết quả vừa rồi", "chỉ dựa trên metadata..."). Plain anaphora is handled
    by the coreference pipeline, not here.
    """
    q = question or ""
    if _context_ref_re.search(q):
        return True
    if _context_only_re.search(q):
        return True
    return False


def has_context_only_constraint(question: str) -> bool:
    """True when the user constrains the answer to metadata already collected."""
    q = question or ""
    if _context_only_re.search(q):
        return True
    for phrase in _CONSTRAINT_PHRASES:
        if re.search(rf"\b(?:{phrase})\b", q, re.I):
            return True
    return False


def has_anaphora(question: str) -> bool:
    return bool(_ANAPHORA_RE.search(question or ""))


def extract_field_refs(question: str) -> list[str]:
    """Snake_case / dotted identifiers that look like data fields or tables."""
    q = question or ""
    refs: list[str] = []
    for m in _dotted_ref_re.findall(q):
        refs.append(m)
    for m in _snake_ref_re.findall(q):
        if m not in refs:
            refs.append(m)
    return refs


def extract_target_ref(question: str) -> tuple[str | None, str | None]:
    """Split a dotted reference ``dim_warehouse.warehouse_id`` -> (entity, field).

    Returns ``(table_name, field_name)``; the field part may itself be dotted
    when the reference is ``schema.table.field``, in which case the last two
    segments win.
    """
    q = question or ""
    m = _dotted_ref_re.search(q)
    if not m:
        return None, None
    parts = m.group(0).split(".")
    if len(parts) >= 2:
        return ".".join(parts[:-1]), parts[-1]
    return None, None


def detect_evidence_intent(question: str) -> str | None:
    """Classify what the user wants done *with* the referenced evidence."""
    q = question or ""
    for pattern, hint in _INTENT_HINTS:
        if pattern.search(q):
            return hint
    return None


def looks_like_a_field(name: str) -> bool:
    """True when ``name`` is more likely a column than a catalog entity."""
    return bool(_PK_SUFFIX_RE.search(name)) if name else False


def format_fields(fields: list[str], limit: int = 30) -> str:
    clean = [f for f in fields if f]
    if not clean:
        return ""
    joined = ", ".join(clean[:limit])
    if len(clean) > limit:
        joined += f", ... (+{len(clean) - limit})"
    return joined
