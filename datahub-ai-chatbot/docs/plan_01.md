# DataAtlas Chatbot Improvement Plan — Rolling Fix Cycle

> **Date**: 2026-08-21
> **Baseline**: 651 tests pass, 75% golden benchmark (rolling)
> **Goal**: Fix root causes (query normalization, entity resolution, context propagation) + add RAGAS evaluation + admin logging — all generic architectural fixes

---

## Table of Contents

1. [Audit Summary](#audit-summary)
2. [Root Cause Analysis](#root-cause-analysis)
3. [Implementation Plan](#implementation-plan)
   - [Phase 1: Admin Response Log + RAGAS Evaluation](#phase-1-admin-response-log--ragas-evaluation)
   - [Phase 2: Query Normalization + Entity Separation](#phase-2-query-normalization--entity-separation)
   - [Phase 3: Entity Resolution + Confirmation + Pending State](#phase-3-entity-resolution--confirmation--pending-state)
   - [Phase 4: Context Propagation Fix](#phase-4-context-propagation-fix)
   - [Phase 5: Metadata Listing / Data Quality](#phase-5-metadata-listing--data-quality)
   - [Phase 6: Schema/Field Query Understanding](#phase-6-schemafield-query-understanding)
   - [Phase 7: Citation/Evidence for Listings](#phase-7-citationevidence-for-listings)
   - [Phase 8: Thinking/LLM Strategy](#phase-8-thinkingllm-strategy)
   - [Phase 9: Performance Optimization](#phase-9-performance-optimization)
   - [Phase 10: Mandatory Test Cases (A-Q)](#phase-10-mandatory-test-cases-a-q)
   - [Phase 11: RAGAS Evaluation Suite](#phase-11-ragas-evaluation-suite)
   - [Phase 12: Regression Process](#phase-12-regression-process)
   - [Phase 13: Final Report](#phase-13-final-report)
4. [Rolling Fix Philosophy](#rolling-fix-philosophy)
5. [Standing Rules](#standing-rules)

---

## Audit Summary

### Architecture Overview

```
User Question
  → IntentResolver (regex + LLM)
    → ChatService.answer() [2200 lines, ~35 decision points]
      → Entity Resolution (exact URN → name search → fuzzy fallback)
      → Hybrid Search (vector + token discovery)
      → Context Builder (XML for LLM)
      → Answer Generator (Fireworks LLM + guardrails)
        → Citation Validation
        → Confidence Scoring
        → Output Validation
  → ChatResponse
```

### Current State

| Metric | Value |
|--------|-------|
| Tests | 651 passed |
| Golden benchmark | 75% (rolling) |
| ChatService.answer() | ~2200 lines, ~35 decision points |
| Intent patterns | 60+ regex rules |
| Entity types | dataset, dashboard, glossary_term, document |
| DB tables | 13 (entities, chunks, ACL, conversation, RBAC, audit, images) |
| LLM | Fireworks deepseek-v4-flash-0731 |
| Embedding | Ollama nomic-embed-text |
| Vector store | OpenSearch 21,194 docs |

### Key Limitations Found

| Category | Issue | Severity |
|----------|-------|----------|
| **Persistence** | Evidence, active entities NOT persisted to DB — lost on restart | HIGH |
| **Persistence** | `load_history_from_db()` returns FIRST K turns, not LAST K (bug) | HIGH |
| **State** | No persistent confirmation/pending state — clarification is stateless | HIGH |
| **Citations** | Two separate citation systems (context-builder vs evidence-record) using same ID space | HIGH |
| **Evaluation** | No RAGAS evaluation — only basic keyword-overlap faithfulness | HIGH |
| **Logging** | No admin response logging — no interaction audit trail | HIGH |
| **NLP** | All reference/anaphora detection is regex-only, no LLM fallback | MEDIUM |
| **Coreference** | No topic-tracking across turns — last-subject-wins is brittle | MEDIUM |
| **Context** | No diversity/ranking in context selection — potential homogeneity | MEDIUM |
| **Multi-worker** | Singleton ConversationMemory is per-process, not shared | HIGH |

---

## Root Cause Analysis

### Failing Case Trace: "dataser Analyse Product cost collector"

```
"dataser Analyse Product cost collector"
  │
  ▼
classify_intent() → GENERAL (no regex matches)
  │
  ▼
IntentResolver: no_action, tool=hybrid_search
  │
  ▼
HybridSearch.search()
  │
  ├─ EntityResolver.resolve()
  │   ├─ exact URN: no
  │   ├─ name search: no direct match
  │   └─ fuzzy fallback: YES, finds "Analyse Product Cost Collector"
  │       score ~0.85-0.9 (typo "dataser" ignored)
  │
  ├─ _names_entity(query)? → False (no quotes, no snake_case)
  │
  ├─ score >= TRUST_THRESHOLD (0.85)? → Maybe borderline
  │
  └─ If score < 0.85 AND _names_entity()=false → DISCARDED
      Falls through to vector search → may not find entity
  │
  ▼
Clarification returned with candidates → NO PENDING STATE STORED
  │
  ▼
User's next message → FULL PIPELINE RESTARTS from scratch
```

### Root Causes

1. **No query normalization** — "dataser" is not corrected to "dataset" before entity resolution
2. **No entity/question separation** — "analyse" (question word) is mixed with entity name
3. **No pending confirmation state** — clarification is stateless, user must retype everything
4. **No persistent evidence** — context lost on restart or new message
5. **Two citation systems** — context-builder E1 and evidence-record E1 are different things

---

## Implementation Plan

### Phase 1: Admin Response Log + RAGAS Evaluation

**Goal**: See every interaction, measure faithfulness quantitatively

| # | Task | Files | Test |
|---|------|-------|------|
| 1.1 | Create `InteractionLog` DB model | `database/models.py` | `test_interaction_log.py` |
| 1.2 | Create `InteractionLogger` service | `app/services/interaction_logger.py` | unit test |
| 1.3 | Wire logger into `ChatService.answer()` | `app/services/chat_service.py` | integration test |
| 1.4 | Create RAGAS evaluation pipeline | `evaluation/ragas_evaluator.py` | `test_ragas.py` |
| 1.5 | Create admin API endpoint | `app/api/admin.py` | API test |
| 1.6 | Add admin UI page | `app/static/admin.html` | manual |

**1.1 InteractionLog DB Model**

```python
class InteractionLog(Base):
    __tablename__ = "interaction_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    trace_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True)
    conversation_id: Mapped[str] = mapped_column(String(128), index=True)

    # Request
    question: Mapped[str] = mapped_column(Text)
    selected_action: Mapped[str | None]
    model: Mapped[str | None]

    # Intent resolution
    intent: Mapped[str] = mapped_column(String(64))
    message_intent: Mapped[str | None]
    routing_decision: Mapped[str | None]
    confidence: Mapped[str | None]
    chosen_tool: Mapped[str | None]

    # Entity resolution
    entity_hint: Mapped[str | None]
    entity_resolved_name: Mapped[str | None]
    entity_resolved_urn: Mapped[str | None]
    resolution_state: Mapped[str | None]

    # Response
    answer: Mapped[str] = mapped_column(Text)
    ambiguous: Mapped[bool] = mapped_column(default=False)
    insufficient_context: Mapped[bool] = mapped_column(default=False)

    # Quality metrics
    result_count: Mapped[int] = mapped_column(default=0)
    top_score: Mapped[float | None]
    citation_count: Mapped[int] = mapped_column(default=0)
    processing_time_ms: Mapped[int | None]

    # RAGAS scores (computed async)
    faithfulness: Mapped[float | None]
    answer_relevancy: Mapped[float | None]
    context_precision: Mapped[float | None]
    context_recall: Mapped[float | None]

    # Metadata
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
```

**1.2 InteractionLogger Service**

```python
class InteractionLogger:
    async def log_request(self, trace_id, question, user_id, ...):
        """Log request before processing."""

    async def log_response(self, trace_id, answer, intent, ...):
        """Log response after processing."""

    async def compute_ragas(self, trace_id, question, answer, context, evidence):
        """Async RAGAS score computation."""

    async def get_interactions(self, filters, limit, offset):
        """Query interactions for admin UI."""
```

**1.3 Wire into ChatService**

Insert logging at entry and exit points of `answer()`:
- Line ~543: log request (question, user, model, action)
- Line ~2757: log response (answer, intent, confidence, results)
- Async RAGAS computation in background task

**1.4 RAGAS Evaluation Pipeline**

```python
class RAGASEvaluator:
    async def evaluate(self, samples: list[GoldenSample]) -> EvaluationReport:
        """Run RAGAS metrics on golden dataset."""

    async def faithfulness(self, question, answer, contexts) -> float:
        """Is the answer grounded in the contexts?"""

    async def answer_relevancy(self, question, answer) -> float:
        """Does the answer address the question?"""

    async def context_precision(self, question, contexts) -> float:
        """Are the retrieved contexts relevant?"""

    async def context_recall(self, question, answer, reference) -> float:
        """Does the context contain the information needed?"""
```

---

### Phase 2: Query Normalization + Entity Separation

**Goal**: Normalize user input BEFORE intent classification, separate entity names from question words

| # | Task | Files | Test |
|---|------|-------|------|
| 2.1 | Create `QueryNormalizer` class | `retrieval/normalizer.py` | `test_query_normalizer.py` |
| 2.2 | Add configurable typo dictionary | `config/settings.py` | unit test |
| 2.3 | Wire normalizer into `IntentResolver.resolve()` | `retrieval/intent_resolver.py` | integration test |
| 2.4 | Add `NormalizedQuery` dataclass | `retrieval/query_models.py` | unit test |
| 2.5 | Test with all 17 mandatory test cases | `tests/` | regression |

**2.1 QueryNormalizer Pipeline**

```python
class QueryNormalizer:
    """Generic query normalization — NOT hard-coded per entity/term/dataset."""

    def normalize(self, query: str, history: list) -> NormalizedQuery:
        """
        Pipeline:
        1. Unicode normalization (NFKD)
        2. Typo correction (edit distance against entity catalog)
        3. Entity name extraction (from catalog, not guessed)
        4. Question word separation (Vietnamese/English question markers)
        5. Anaphora detection (pronouns, demonstratives)
        """
        steps = [
            self._unicode_normalize,
            self._typo_correct,
            self._extract_entities,
            self._separate_question_words,
            self._detect_anaphora,
        ]
        result = NormalizedQuery(original=query)
        for step in steps:
            result = step(result, history)
        return result
```

**NormalizedQuery Dataclass**

```python
@dataclass
class NormalizedQuery:
    original: str
    normalized: str = ""
    entity_tokens: list[str] = field(default_factory=list)
    question_words: list[str] = field(default_factory=list)
    has_anaphora: bool = False
    anaphora_target: str | None = None
    typo_corrections: dict[str, str] = field(default_factory=dict)
    confidence: float = 0.0
```

**2.2 Typo Correction (Generic)**

```python
# NOT hard-coded — uses entity catalog for correction candidates
def _typo_correct(self, state: NormalizedQuery, history) -> NormalizedQuery:
    tokens = state.original.split()
    corrected = {}
    for i, token in enumerate(tokens):
        # Skip known question words
        if token.lower() in _QUESTION_WORDS:
            continue
        # Find closest entity name token from catalog
        candidates = self._entity_index.find_similar(token, max_dist=2)
        if candidates:
            corrected[token] = candidates[0].name
    state.typo_corrections = corrected
    state.normalized = self._apply_corrections(state.original, corrected)
    return state
```

**2.3 Entity/Question Separation**

```python
def _separate_question_words(self, state: NormalizedQuery, history) -> NormalizedQuery:
    """Separate entity tokens from question words."""
    tokens = state.normalized.split()
    entity_tokens = []
    question_words = []
    for token in tokens:
        if token.lower() in _QUESTION_MARKERS_VN + _QUESTION_MARKERS_EN:
            question_words.append(token)
        elif token.lower() in _ENTITY_STOPWORDS:
            continue  # "dataset", "bảng", "table" — not part of entity name
        else:
            entity_tokens.append(token)
    state.entity_tokens = entity_tokens
    state.question_words = question_words
    return state
```

---

### Phase 3: Entity Resolution + Confirmation + Pending State

**Goal**: Store pending confirmation, allow "yes/no" follow-ups, improve resolution confidence

| # | Task | Files | Test |
|---|------|-------|------|
| 3.1 | Create `PendingConfirmation` dataclass | `retrieval/entity_resolver.py` | unit test |
| 3.2 | Store pending state in `ConversationMemory` | `app/services/conversation.py` | unit test |
| 3.3 | Add "yes/no" detection in `IntentResolver` | `retrieval/intent_resolver.py` | unit test |
| 3.4 | Add entity suggestion as pending | `app/services/chat_service.py` | integration test |
| 3.5 | Improve fuzzy resolution thresholds | `retrieval/hybrid_search.py` | unit test |
| 3.6 | Test confirmation flow end-to-end | `tests/e2e/` | e2e test |

**3.1 PendingConfirmation Dataclass**

```python
@dataclass
class PendingConfirmation:
    confirmation_id: str
    original_query: str
    suggested_entity: str
    suggested_urn: str | None
    candidates: list[dict]  # [{name, urn, score, reason}]
    intent: str
    context: dict  # Additional context for resolution
    created_at: float  # timestamp
    expires_at: float  # TTL
```

**3.2 Storage in ConversationMemory**

```python
class ConversationMemory:
    def set_pending_confirmation(self, uid, cid, pending: PendingConfirmation):
        """Store pending confirmation for next message."""
        conv = self.get_or_create(uid, cid)
        conv.pending_confirmation = pending

    def get_pending_confirmation(self, uid, cid) -> PendingConfirmation | None:
        """Retrieve and consume pending confirmation."""
        conv = self.get_or_create(uid, cid)
        pending = conv.pending_confirmation
        if pending and time.time() > pending.expires_at:
            conv.pending_confirmation = None
            return None
        return pending

    def clear_pending_confirmation(self, uid, cid):
        """Clear pending after use."""
        conv = self.get_or_create(uid, cid)
        conv.pending_confirmation = None
```

**3.3 Yes/No Detection**

```python
# In IntentResolver.resolve()
def _check_pending_confirmation(self, question, history, pending):
    """When pending exists, check if user confirms or denies."""
    if not pending:
        return None

    q = question.lower().strip()
    confirm_words = {"vâng", "ok", "chính xác", "đúng", "yes", "confirm", "chọn"}
    deny_words = {"không", "khác", "no", "deny", "không phải"}

    if any(w in q for w in confirm_words):
        return PendingAction.CONFIRM
    if any(w in q for w in deny_words):
        return PendingAction.DENY
    return None  # Ambiguous — treat as new query
```

**3.5 Improved Fuzzy Resolution**

```python
# In HybridSearch.search()
def _should_trust_resolution(self, resolution, query):
    """Dynamic trust threshold based on entity signal strength."""
    base_threshold = settings.ENTITY_RESOLVER_TRUST_THRESHOLD  # 0.85

    # If query explicitly names an entity (quotes, snake_case, dotted),
    # lower threshold — user is intentionally referencing something
    if _names_entity(query):
        return base_threshold * 0.9  # 0.765

    # If resolution is ambiguous (multiple candidates), require higher confidence
    if resolution.ambiguous:
        return base_threshold * 1.1  # 0.935

    return base_threshold
```

---

### Phase 4: Context Propagation Fix

**Goal**: Fix follow-up context loss, improve evidence-based answers

| # | Task | Files | Test |
|---|------|-------|------|
| 4.1 | Fix `load_history_from_db()` — return LAST K turns | `app/services/conversation.py` | unit test |
| 4.2 | Persist evidence records to DB | `database/models.py`, `app/services/conversation.py` | integration test |
| 4.3 | Add temporal decay to evidence matching | `retrieval/context_resolver.py` | unit test |
| 4.4 | Unify citation ID spaces | `retrieval/citation.py`, `retrieval/evidence.py` | unit test |
| 4.5 | Test follow-up chain | `tests/context/` | integration test |

**4.1 Fix load_history_from_db()**

```python
# BEFORE (bug): returns FIRST K turns
async def load_history_from_db(self, session, uid, cid, last_k=5):
    result = await session.execute(
        select(ConversationHistory)
        .where(user_id=uid, conversation_id=cid)
        .order_by(ConversationHistory.created_at.asc())
        .limit(last_k)
    )
    return [(r.question, r.answer) for r in result.scalars()]

# AFTER (fix): returns LAST K turns
async def load_history_from_db(self, session, uid, cid, last_k=5):
    result = await session.execute(
        select(ConversationHistory)
        .where(user_id=uid, conversation_id=cid)
        .order_by(ConversationHistory.created_at.desc())
        .limit(last_k)
    )
    rows = list(result.scalars())
    rows.reverse()  # chronological order
    return [(r.question, r.answer) for r in rows]
```

**4.2 Persist Evidence to DB**

```python
class EvidenceRecordDB(Base):
    __tablename__ = "evidence_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True)
    conversation_id: Mapped[str] = mapped_column(String(128), index=True)
    evidence_id: Mapped[str] = mapped_column(String(8))  # E1, E2, ...
    kind: Mapped[str] = mapped_column(String(32))
    entity_name: Mapped[str | None]
    entity_urn: Mapped[str | None]
    entity_type: Mapped[str | None]
    tool_name: Mapped[str | None]
    query: Mapped[str | None]
    structured: Mapped[dict | None]  # JSON
    citation: Mapped[dict | None]  # JSON
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
```

**4.3 Temporal Decay**

```python
def _score_evidence(self, evidence: EvidenceRecord, recency: int) -> float:
    """Score evidence with temporal decay — recent evidence scores higher."""
    base_score = 1.0
    decay_rate = 0.1  # 10% decay per turn
    return base_score * (1.0 - decay_rate * recency)
```

**4.4 Unified Citation IDs**

```python
# Context-builder citations: C1, C2, ... (for current search results)
# Evidence citations: EV1, EV2, ... (for prior-turn evidence)
# This prevents ID collisions between the two systems.

# In context_builder.py
def build_context(results):
    for i, result in enumerate(results):
        doc.cid = f"C{i+1}"  # C1, C2, ...

# In evidence.py
def record_evidence(self, uid, cid, evidence):
    evidence.evidence_id = f"EV{len(existing)+1}"  # EV1, EV2, ...
```

---

### Phase 5: Metadata Listing / Data Quality

**Goal**: Deterministic answers for dataset quality questions without LLM

| # | Task | Files | Test |
|---|------|-------|------|
| 5.1 | Create `MetadataListingService` | `app/services/metadata_listing.py` | unit test |
| 5.2 | Add listing intents | `retrieval/intent.py` | unit test |
| 5.3 | Wire listing service into `ChatService` | `app/services/chat_service.py` | integration test |
| 5.4 | Add quality check templates | `app/services/chat/flows.py` | unit test |
| 5.5 | Test all listing scenarios | `tests/` | regression |

**5.1 MetadataListingService**

```python
class MetadataListingService:
    """Generic listing engine — NOT hard-coded per entity/term/dataset."""

    async def list_datasets(self, filters: dict, limit: int = 20) -> list[dict]:
        """List datasets with filters (domain, platform, owner, etc.)."""

    async def count_datasets(self, filters: dict) -> int:
        """Count datasets matching filters."""

    async def list_missing(self, field: str, entity_type: str = "dataset") -> list[dict]:
        """List entities missing a required field (description, owner, domain)."""

    async def list_by_domain(self, domain: str) -> list[dict]:
        """List all datasets in a domain."""

    async def list_by_platform(self, platform: str) -> list[dict]:
        """List all datasets on a platform."""
```

**5.2 Listing Intents**

```python
# In intent.py — add to QueryIntent enum
DATASET_COUNT = "DATASET_COUNT"        # "Có bao nhiêu dataset?"
DATASET_BY_DOMAIN = "DATASET_BY_DOMAIN"  # "Dataset thuộc domain X?"
DATASET_BY_PLATFORM = "DATASET_BY_PLATFORM"  # "Dataset trên platform X?"
MISSING_DESCRIPTION = "MISSING_DESCRIPTION"  # "Dataset nào chưa có description?"
MISSING_OWNER = "MISSING_OWNER"        # "Dataset nào chưa có owner?"
MISSING_DOMAIN = "MISSING_DOMAIN"      # "Dataset nào chưa có domain?"
```

---

### Phase 6: Schema/Field Query Understanding

**Goal**: Better intent detection for schema queries, field-level follow-ups

| # | Task | Files | Test |
|---|------|-------|------|
| 6.1 | Add field-level intent patterns | `retrieval/intent.py` | unit test |
| 6.2 | Improve `ContextResolver` field matching | `retrieval/context_resolver.py` | unit test |
| 6.3 | Add `FIELD_PROPERTY` intent | `retrieval/intent.py` | unit test |
| 6.4 | Wire field property answers | `app/services/chat_service.py` | integration test |
| 6.5 | Test schema query scenarios | `tests/` | regression |

**6.1 Field-Level Intent Patterns**

```python
# In intent.py — add to _RULE_STRINGS
FIELD_PROPERTY: (
    r"(?:kiểu|kieu|loai|type|dtype)\s+dữ\s+liệu|data\s+type|"
    r"mô\s+tả|description|"
    r"nullable|cho\s+phép|trống|"
    r"primary\s+key|khóa\s+chính|"
    r"tag|nhãn|"
    r"glossary|thuật\s+ngữ"
)
```

---

### Phase 7: Citation/Evidence for Listings

**Goal**: All listing answers include citations, evidence records

| # | Task | Files | Test |
|---|------|-------|------|
| 7.1 | Add citation generation for listings | `app/services/metadata_listing.py` | unit test |
| 7.2 | Record listing results as evidence | `app/services/chat_service.py` | integration test |
| 7.3 | Add citation validation for listings | `retrieval/citation.py` | unit test |
| 7.4 | Test citation accuracy | `tests/` | regression |

---

### Phase 8: Thinking/LLM Strategy

**Goal**: Route simple questions away from expensive LLM calls

| # | Task | Files | Test |
|---|------|-------|------|
| 8.1 | Add complexity scoring | `retrieval/intent_resolver.py` | unit test |
| 8.2 | Add deterministic answer paths | `app/services/chat_service.py` | integration test |
| 8.3 | Add LLM cost tracking | `app/services/interaction_logger.py` | unit test |
| 8.4 | Test cost reduction | `tests/` | regression |

---

### Phase 9: Performance Optimization

**Goal**: Optimize for 8500+ datasets, reduce latency

| # | Task | Files | Test |
|---|------|-------|------|
| 9.1 | Add entity index caching | `retrieval/entity_extraction.py` | unit test |
| 9.2 | Optimize fuzzy matching | `retrieval/entity_resolver.py` | unit test |
| 9.3 | Add OpenSearch result caching | `retrieval/hybrid_search.py` | unit test |
| 9.4 | Test latency improvement | `tests/` | benchmark |

---

### Phase 10: Mandatory Test Cases (A-Q)

**Goal**: All 17 test cases pass, regression protected

| # | Task | Files | Test |
|---|------|-------|------|
| 10.1 | Create test case definitions | `tests/mandatory_cases.json` | `test_mandatory.py` |
| 10.2 | Implement test runner | `tests/test_mandatory.py` | test |
| 10.3 | Run all cases, record baseline | `tests/` | test |
| 10.4 | Fix any failing cases | various | test |

**Test Cases (A-Q)**

| ID | Category | Test Case | Expected |
|----|----------|-----------|----------|
| A | Typo | "dataser Analyse Product cost collector" | Resolves to correct entity |
| B | Typo | "dim_warehousee" (extra char) | Suggests "dim_warehouse" |
| C | Typo | "fact_inventoryy" (double char) | Resolves to "fact_inventory_movement" |
| D | Follow-up | Q1: "Schema dim_warehouse?" Q2: "Nó có bao nhiêu field?" | Answers from evidence |
| E | Follow-up | Q1: "Owner dim_warehouse?" Q2: "Còn fact_goods_receipt?" | Inherits owner intent |
| F | Confirmation | Q1: "Analyse Product" (ambiguous) Q2: "Chính xác" | Confirms and answers |
| G | Confirmation | Q1: "Analyse Product" (ambiguous) Q2: "Không, other one" | Denies, asks for clarification |
| H | Listing | "Có bao nhiêu dataset?" | Deterministic count |
| I | Listing | "Dataset thuộc domain Sales?" | Deterministic list |
| J | Listing | "Dataset nào chưa có description?" | Deterministic list |
| K | Schema | "dim_warehouse có field nào?" | Deterministic schema |
| L | Schema | "warehouse_id có kiểu dữ liệu gì?" | Deterministic property |
| M | Field Property | "field nào liên quan đến warehouse?" | Deterministic search |
| N | Citation | Any answer with E1, E2 | Citations valid |
| O | Abstention | "Revenue forecast 2025?" (not in catalog) | "I don't know" |
| P | Grounding | Any answer | No fabricated URNs |
| Q | Multi-hop | "Từ report X → term → dataset → lineage" | Chain walks correctly |

---

### Phase 11: RAGAS Evaluation Suite

**Goal**: Quantitative evaluation of faithfulness, relevancy, precision, recall

| # | Task | Files | Test |
|---|------|-------|------|
| 11.1 | Create RAGAS evaluation dataset | `evaluation/ragas_dataset.json` | `test_ragas.py` |
| 11.2 | Implement RAGAS metrics | `evaluation/ragas_evaluator.py` | `test_ragas.py` |
| 11.3 | Run evaluation, record baseline | `evaluation/` | test |
| 11.4 | After each phase, re-run evaluation | `evaluation/` | test |

**RAGAS Metrics**

| Metric | Description | Target |
|--------|-------------|--------|
| Faithfulness | Is the answer grounded in contexts? | >= 0.85 |
| Answer Relevancy | Does the answer address the question? | >= 0.80 |
| Context Precision | Are retrieved contexts relevant? | >= 0.75 |
| Context Recall | Does context contain needed info? | >= 0.70 |

---

### Phase 12: Regression Process

**Goal**: Automated regression protection

| # | Task | Files | Test |
|---|------|-------|------|
| 12.1 | Create regression script | `scripts/regression.sh` | shell |
| 12.2 | Run full test suite | `tests/` | shell |
| 12.3 | Run RAGAS evaluation | `evaluation/` | shell |
| 12.4 | Run mandatory test cases | `tests/` | shell |
| 12.5 | Generate regression report | `docs/next_improvement_report.md` | markdown |

**Regression Script**

```bash
#!/bin/bash
set -e

echo "=== DataAtlas Regression Suite ==="

# 1. Unit tests
echo "[1/5] Running unit tests..."
.venv/bin/python -m pytest tests/unit/ -q --tb=line

# 2. Retrieval tests
echo "[2/5] Running retrieval tests..."
.venv/bin/python -m pytest tests/retrieval/ -q --tb=line

# 3. Integration tests
echo "[3/5] Running integration tests..."
.venv/bin/python -m pytest tests/integration/ -q --tb=line

# 4. Mandatory test cases
echo "[4/5] Running mandatory test cases (A-Q)..."
.venv/bin/python -m pytest tests/test_mandatory.py -q --tb=short

# 5. RAGAS evaluation
echo "[5/5] Running RAGAS evaluation..."
.venv/bin/python -m evaluation.ragas_evaluator --dataset evaluation/ragas_dataset.json

echo "=== Regression Complete ==="
```

---

### Phase 13: Final Report

**Goal**: Comprehensive documentation of all changes

| # | Task | Files | Test |
|---|------|-------|------|
| 13.1 | Create `docs/next_improvement_report.md` | `docs/` | markdown |
| 13.2 | Update `docs/analyze/` feature docs | `docs/analyze/` | markdown |
| 13.3 | Update `docs/context/` context docs | `docs/context/` | markdown |

---

## Rolling Fix Philosophy

Every change follows this cycle:

```
1. Write test first → define expected behavior
2. Implement fix → minimal, focused change
3. Run regression → ensure no breakage (651+ tests)
4. Run RAGAS → verify improvement
5. Document → update docs
```

**No breaking changes.** Each phase is independently deployable.

**No hard-coding per entity/term/dataset.** All fixes are generic architectural improvements.

**No editing ground truth.** Evaluation dataset is read-only.

**Abstention > fabrication.** When uncertain, the system says "I don't know" rather than guessing.

---

## Standing Rules

1. **No hard-coding entity/term/dataset names** in new code
2. **No per-question if/else** — use generic patterns
3. **No editing ground truth** — evaluation dataset is read-only
4. **Abstention > fabrication** — say "I don't know" rather than guess
5. **Every change needs a regression test**
6. **No GraphRAG** — keep the current architecture
7. **Run full test suite before and after each phase**
8. **Document all changes in `docs/next_improvement_report.md`**

---

## File Changes Summary

| Phase | New Files | Modified Files |
|-------|-----------|----------------|
| 1 | `app/services/interaction_logger.py`, `app/api/admin.py`, `evaluation/ragas_evaluator.py`, `evaluation/ragas_dataset.json` | `database/models.py`, `app/services/chat_service.py`, `app/main.py` |
| 2 | `retrieval/normalizer.py`, `retrieval/query_models.py` | `retrieval/intent_resolver.py`, `config/settings.py` |
| 3 | — | `retrieval/entity_resolver.py`, `app/services/conversation.py`, `retrieval/hybrid_search.py`, `app/services/chat_service.py` |
| 4 | `database/models.py` (EvidenceRecordDB) | `app/services/conversation.py`, `retrieval/context_resolver.py`, `retrieval/citation.py`, `retrieval/evidence.py` |
| 5 | `app/services/metadata_listing.py` | `retrieval/intent.py`, `app/services/chat_service.py`, `app/services/chat/flows.py` |
| 6 | — | `retrieval/intent.py`, `retrieval/context_resolver.py`, `app/services/chat_service.py` |
| 7 | — | `app/services/metadata_listing.py`, `app/services/chat_service.py`, `retrieval/citation.py` |
| 8 | — | `retrieval/intent_resolver.py`, `app/services/chat_service.py` |
| 9 | — | `retrieval/entity_extraction.py`, `retrieval/entity_resolver.py`, `retrieval/hybrid_search.py` |
| 10 | `tests/mandatory_cases.json`, `tests/test_mandatory.py` | — |
| 11 | `evaluation/ragas_evaluator.py`, `evaluation/ragas_dataset.json` | — |
| 12 | `scripts/regression.sh` | — |
| 13 | `docs/next_improvement_report.md` | `docs/analyze/`, `docs/context/` |

---

## Dependencies Between Phases

```
Phase 1 (Admin + RAGAS) ─────────────────────────────────────┐
                                                              │
Phase 2 (Normalization) ──┬── Phase 3 (Confirmation) ──┐     │
                          │                             │     │
                          └── Phase 6 (Schema/Field) ───┤     │
                                                        │     │
Phase 4 (Context Propagation) ──────────────────────────┤     │
                                                        │     │
Phase 5 (Metadata Listing) ──┬── Phase 7 (Citations) ──┤     │
                              │                         │     │
                              └── Phase 8 (Thinking) ───┤     │
                                                        │     │
Phase 9 (Performance) ──────────────────────────────────┤     │
                                                        │     │
Phase 10 (Mandatory Tests) ─────────────────────────────┤     │
                                                        │     │
Phase 11 (RAGAS Suite) ─────────────────────────────────┤     │
                                                        │     │
Phase 12 (Regression) ──────────────────────────────────┤     │
                                                        │     │
Phase 13 (Final Report) ◄───────────────────────────────┘     │
                                                              │
Baseline: 651 tests ◄────────────────────────────────────────┘
```

**Recommended execution order:**
1. Phase 1 (Admin + RAGAS) — see everything
2. Phase 2 (Normalization) — fix root cause
3. Phase 3 (Confirmation) — fix stateless clarification
4. Phase 4 (Context Propagation) — fix follow-up loss
5. Phase 5 (Metadata Listing) — deterministic answers
6. Phase 6 (Schema/Field) — better intent detection
7. Phase 7 (Citations) — unified citation system
8. Phase 8 (Thinking) — cost optimization
9. Phase 9 (Performance) — latency optimization
10. Phase 10 (Mandatory Tests) — regression protection
11. Phase 11 (RAGAS Suite) — quantitative evaluation
12. Phase 12 (Regression) — automated regression
13. Phase 13 (Final Report) — documentation

---

*Generated: 2026-08-21 by audit analysis of datahub-ai-chatbot codebase*
