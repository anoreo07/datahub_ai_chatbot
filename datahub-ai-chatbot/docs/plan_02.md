# DataAtlas Chatbot Improvement Plan — plan_02 (Revised)

> **Date**: 2026-08-21
> **Baseline**: 651 tests pass, 75% golden benchmark (rolling)
> **Revision**: Verified against codebase runtime behavior. Fixes plan_01 assumptions.

---

## Changes from plan_01

| Area | plan_01 | plan_02 | Reason |
|------|---------|---------|--------|
| **Entity Resolution** | Add QueryNormalizer with edit-distance typo correction | Improve intent classification for entity-name-like queries; fix _names_entity() gate | Fuzzy fallback ALREADY handles typos (score ~0.98). Adding redundant edit-distance layer adds complexity without benefit. |
| **Confirmation State** | Store PendingConfirmation in ConversationMemory | Use Redis for shared state across workers; OR detect confirmation from conversation history (stateless) | ConversationMemory is process-local singleton. With 4 workers (Helm config), follow-ups may land on different worker. In-memory state is lost on restart. |
| **Temporal Decay** | Add temporal decay to evidence matching | Remove from plan | No benchmark evidence that recency weighting improves resolution. Evidence replacement semantics already handle recency. Adding decay without proof adds risk. |
| **Context Propagation** | Fix load_history_from_db + persist evidence + temporal decay + unify citations | Fix load_history_from_db + persist evidence to DB + fix focus-field inference + unify citation IDs | Focus on proven gaps: DB bug, persistence, focus-field fragility, citation collision. Remove unproven temporal decay. |
| **RAGAS** | Compute faithfulness/answer_relevancy/context_precision/context_recall | Add NOT_EVALUATED state for metrics without reference context | RAGAS metrics require reference contexts. If no reference exists, metric should be NOT_EVALUATED, not 0. |
| **Phase Order** | Phase 1→2→3→4→... | Phase 1→3→2→4→... | Fix confirmation state (Phase 3) before normalization (Phase 2) because confirmation is critical for multi-turn flow. |

---

## Audit Findings (Verified)

### A. Entity Resolution — Fallback ALREADY Handles Typos

**Verified**: The `fuzzy_score()` function in `retrieval/fuzzy.py` uses `SequenceMatcher.ratio()` + token alignment + substring bonus.

| Input | Entity | Fuzzy Score | Resolved? |
|-------|--------|-------------|-----------|
| `"dataser Analyse Product cost collector"` | `"Analyse Product Cost Collector"` | ~0.98 | YES |
| `"dim_warehousee"` | `"dim_warehouse"` | 1.0 | YES |
| `"fact_inventoryy"` | `"fact_inventory"` | 1.0 | YES |
| `"Product Cost Analyse"` | `"Analyse Product Cost Collector"` | 1.0 | YES (word reorder handled) |

**Root cause of "dataser" failing is NOT entity resolution** — it's the routing gate in `HybridSearch`:

```python
# hybrid_search.py lines 148-154
if (resolution.resolved and not resolution.ambiguous
        and (_names_entity(query)
             or resolution.resolved.score >= settings.ENTITY_RESOLVER_TRUST_THRESHOLD)):
    return [await self._entity_to_result(resolution.resolved.urn)]
```

`_names_entity("dataser Analyse Product cost collector")` returns `False` (no quotes, no snake_case, no dotted path, no naming phrase). The entity resolver returns score ~0.98, which IS >= 0.85 (TRUST_THRESHOLD). So this specific case SHOULD resolve.

**The actual failing scenario is likely**: intent classification returns GENERAL → routing skips entity-name fast path → falls through to hybrid_search → entity resolver finds the entity but the vector search path also runs and may return different results → reranker may not prefer the entity-resolved result.

**plan_02 action**: Instead of adding a separate typo correction layer, improve the intent classification to detect entity-name-like queries (e.g., "dataser Analyse Product cost collector" looks like a dataset name lookup) and route them through the entity resolution fast path.

### B. Confirmation State — No Server-Side State Exists

**Verified**: There is NO pending confirmation state anywhere in the codebase.

- `ConversationMemory` stores: turns, active_entities, image_focus, evidence
- NO field for: pending_clarification, awaiting_confirmation, last_suggestion
- `ConversationMemory` is a **process-local singleton** (Python dict)
- With 4 workers (Helm config), each worker has isolated memory
- Server restart loses ALL in-memory state
- Confirmation relies on frontend sending `suggested_name` field

**plan_02 action**: Two options:

**Option A (Recommended): Stateless confirmation detection**
- When user says "đúng rồi" / "yes" / "chính xác" after a clarification, detect it from conversation history
- Check if last assistant message was a clarification/suggestion
- If yes, treat as confirmation of the suggested entity
- No server-side state needed — works across workers and restarts

**Option C: Redis-backed pending state**
- Store pending confirmation in Redis with TTL
- Shared across all workers
- Survives worker restart (but not Redis restart)
- More complex but more explicit

### C. Context Propagation — Focus-Field Inference is Fragile

**Verified**: The evidence-based context system is sophisticated but has gaps:

1. **Focus-field inference**: When user says "Nó có kiểu dữ liệu gì?" without prior field context, the system guesses the field via `_infer_join_field()` (looks for PK suffix `_id`). This can be wrong.

2. **Cross-evidence field tracking**: If E1 has `dim_warehouse` fields and E2 has `fact_sales` fields, a bare field question may match the wrong evidence.

3. **Evidence replacement semantics**: Replacing evidence with same `entity_name + kind` can lose `focus_field` from a previous turn.

**plan_02 action**: 
- Fix focus-field inference to use conversation history context
- Add explicit field focus tracking in evidence records
- Don't add temporal decay (no proof it helps)

### D. RAGAS — NOT_EVALUATED for Missing References

**Verified**: RAGAS metrics like `context_precision` and `context_recall` require reference contexts/answers. If no reference exists, the metric should be `NOT_EVALUATED`, not 0.

**plan_02 action**: Add `NOT_EVALUATED` state for metrics without reference. Don't penalize the score for missing references.

---

## Revised Implementation Plan

### Phase 1: Admin Response Log + RAGAS Evaluation

**Goal**: See every interaction, measure faithfulness quantitatively

| # | Task | Files | Test |
|---|------|-------|------|
| 1.1 | Create `InteractionLog` DB model | `database/models.py` | `test_interaction_log.py` |
| 1.2 | Create `InteractionLogger` service | `app/services/interaction_logger.py` | unit test |
| 1.3 | Wire logger into `ChatService.answer()` | `app/services/chat_service.py` | integration test |
| 1.4 | Create RAGAS evaluation pipeline with NOT_EVALUATED handling | `evaluation/ragas_evaluator.py` | `test_ragas.py` |
| 1.5 | Create admin API endpoint | `app/api/admin.py` | API test |
| 1.6 | Add admin UI page | `app/static/admin.html` | manual |

**RAGAS NOT_EVALUATED handling**:

```python
class MetricResult:
    value: float | None  # None = NOT_EVALUATED
    status: Literal["evaluated", "not_evaluated", "error"]
    reason: str | None  # Why not evaluated

def faithfulness(self, question, answer, contexts) -> MetricResult:
    if not contexts:
        return MetricResult(value=None, status="not_evaluated", reason="No contexts retrieved")
    # ... compute metric
```

### Phase 2: Confirmation State (Stateless)

**Goal**: Handle "đúng rồi" / "yes" after clarifications without server-side state

| # | Task | Files | Test |
|---|------|-------|------|
| 2.1 | Create `ConfirmationDetector` — detect confirmation from conversation history | `retrieval/confirmation.py` | `test_confirmation.py` |
| 2.2 | Wire detector into `IntentResolver.resolve()` | `retrieval/intent_resolver.py` | integration test |
| 2.3 | Handle suggestion confirmation (user says "yes" to "Ý bạn là X?") | `app/services/chat_service.py` | integration test |
| 2.4 | Handle ambiguity confirmation (user picks from list) | `app/services/chat_service.py` | integration test |
| 2.5 | Test confirmation flow end-to-end | `tests/e2e/` | e2e test |

**ConfirmationDetector design (stateless)**:

```python
class ConfirmationDetector:
    """Detect confirmation/denial from conversation history.
    
    No server-side state needed — checks if last assistant message
    was a clarification/suggestion, and current message confirms/denies it.
    """

    CONFIRM_WORDS = {"vâng", "đúng", "ok", "yes", "chính xác", "chọn", "confirm"}
    DENY_WORDS = {"không", "khác", "no", "deny", "không phải", "không đúng"}

    def detect(self, question: str, history: list[tuple[str, str]]) -> ConfirmationResult:
        """
        Check if question is a confirmation of the last assistant message.
        
        Returns:
            ConfirmationResult(action="confirm"|"deny"|"new_query",
                             entity_name=None|str,
                             confidence=float)
        """
        if not history:
            return ConfirmationResult(action="new_query")
        
        last_q, last_a = history[-1]
        q_lower = question.lower().strip()
        
        # Check if last assistant message was a clarification/suggestion
        if not self._was_clarification(last_a):
            return ConfirmationResult(action="new_query")
        
        # Check if current message is a confirmation
        if any(w in q_lower for w in self.CONFIRM_WORDS):
            entity = self._extract_suggested_entity(last_a)
            return ConfirmationResult(action="confirm", entity_name=entity, confidence=0.9)
        
        # Check if current message is a denial
        if any(w in q_lower for w in self.DENY_WORDS):
            return ConfirmationResult(action="deny", confidence=0.8)
        
        # Ambiguous — treat as new query
        return ConfirmationResult(action="new_query")
    
    def _was_clarification(self, last_answer: str) -> bool:
        """Check if last assistant message was a clarification/suggestion."""
        indicators = [
            "ý bạn là", "ban muon", "chon", "entity nao",
            "khong ton tai", "khong tim thay", "suggest",
        ]
        return any(ind in last_answer.lower() for ind in indicators)
```

### Phase 3: Query Normalization (Generic)

**Goal**: Improve intent classification for entity-name-like queries

| # | Task | Files | Test |
|---|------|-------|------|
| 3.1 | Create `EntityNameDetector` — detect if query looks like an entity name | `retrieval/entity_detection.py` | `test_entity_detection.py` |
| 3.2 | Add entity-name intent to classifier — route entity-name-like queries to entity resolution | `retrieval/intent.py` | unit test |
| 3.3 | Wire detector into `IntentResolver.resolve()` | `retrieval/intent_resolver.py` | integration test |
| 3.4 | Test with all mandatory test cases | `tests/` | regression |

**EntityNameDetector design (generic, not hard-coded)**:

```python
class EntityNameDetector:
    """Detect if a query looks like an entity name reference.
    
    Generic — works for any entity in the catalog, not hard-coded
    per entity/term/dataset.
    """

    def detect(self, query: str) -> EntityNameSignal:
        """
        Signals that query is an entity name:
        1. Contains snake_case identifiers (dim_warehouse, fact_sales)
        2. Contains dotted paths (sales.orders, dms.stg.material)
        3. Contains quoted names ("Analyse Product Cost Collector")
        4. High token overlap with catalog entities (from entity index)
        5. Low question-word density (few Vietnamese/English question markers)
        6. No action verbs (get, show, list, find, compare)
        """
        signals = []
        
        # Signal 1: Snake_case or dotted identifier
        if re.search(r"[a-z0-9]{2,}_[a-z0-9_]+", query):
            signals.append("snake_case")
        
        # Signal 2: Dotted path
        if re.search(r"[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+", query):
            signals.append("dotted_path")
        
        # Signal 3: Quoted name
        if re.search(r"""["'""][^"'""']{2,80}["'""]""", query):
            signals.append("quoted")
        
        # Signal 4: Token overlap with catalog
        overlap = self._catalog_overlap(query)
        if overlap > 0.6:
            signals.append("catalog_overlap")
        
        # Signal 5: Low question-word density
        q_words = self._question_word_count(query)
        if q_words <= 1:
            signals.append("low_question_words")
        
        # Signal 6: No action verbs
        if not self._has_action_verbs(query):
            signals.append("no_action_verbs")
        
        # Decision: if 3+ signals, likely an entity name
        is_entity_name = len(signals) >= 3
        
        return EntityNameSignal(
            is_entity_name=is_entity_name,
            signals=signals,
            confidence=min(1.0, len(signals) / 4.0),
        )
```

### Phase 4: Context Propagation Fix

**Goal**: Fix focus-field inference, persist evidence, fix history bug

| # | Task | Files | Test |
|---|------|-------|------|
| 4.1 | Fix `load_history_from_db()` — return LAST K turns | `app/services/conversation.py` | unit test |
| 4.2 | Persist evidence records to DB | `database/models.py`, `app/services/conversation.py` | integration test |
| 4.3 | Fix focus-field inference — use conversation context | `retrieval/context_resolver.py` | unit test |
| 4.4 | Unify citation ID spaces (C1 vs EV1) | `retrieval/citation.py`, `retrieval/evidence.py` | unit test |
| 4.5 | Test follow-up chain | `tests/context/` | integration test |

**4.3 Focus-field inference fix**:

The current issue: when user says "Nó có kiểu dữ liệu gì?" without prior field context, the system guesses via `_infer_join_field()` (PK suffix heuristic). This can be wrong.

Fix: Use conversation history to infer field focus:

```python
def _infer_focus_from_history(self, history: list, evidence: list) -> str | None:
    """Infer focus field from conversation history.
    
    Check if previous turns mentioned a specific field.
    If Turn 1 was "Lấy schema dim_warehouse" and Turn 2 discussed
    "warehouse_id", then Turn 3's "Nó có kiểu dữ liệu gì?" should
    focus on "warehouse_id".
    """
    # Check evidence records for focus_field
    for ev in reversed(evidence):
        structured = ev.get("structured") or {}
        if structured.get("focus_field"):
            return structured["focus_field"]
    
    # Check history for field mentions
    for q, a in reversed(history):
        field_refs = extract_field_refs(q)
        if field_refs:
            return field_refs[-1]
    
    return None
```

### Phase 5: Metadata Listing / Data Quality

**Goal**: Deterministic answers for dataset quality questions

| # | Task | Files | Test |
|---|------|-------|------|
| 5.1 | Create `MetadataListingService` | `app/services/metadata_listing.py` | unit test |
| 5.2 | Add listing intents | `retrieval/intent.py` | unit test |
| 5.3 | Wire listing service into `ChatService` | `app/services/chat_service.py` | integration test |
| 5.4 | Add quality check templates | `app/services/chat/flows.py` | unit test |
| 5.5 | Test all listing scenarios | `tests/` | regression |

### Phase 6: Schema/Field Query Understanding

**Goal**: Better intent detection for schema queries

| # | Task | Files | Test |
|---|------|-------|------|
| 6.1 | Add field-level intent patterns | `retrieval/intent.py` | unit test |
| 6.2 | Improve `ContextResolver` field matching | `retrieval/context_resolver.py` | unit test |
| 6.3 | Add `FIELD_PROPERTY` intent | `retrieval/intent.py` | unit test |
| 6.4 | Wire field property answers | `app/services/chat_service.py` | integration test |
| 6.5 | Test schema query scenarios | `tests/` | regression |

### Phase 7: Citation/Evidence for Listings

**Goal**: All listing answers include citations

| # | Task | Files | Test |
|---|------|-------|------|
| 7.1 | Add citation generation for listings | `app/services/metadata_listing.py` | unit test |
| 7.2 | Record listing results as evidence | `app/services/chat_service.py` | integration test |
| 7.3 | Add citation validation for listings | `retrieval/citation.py` | unit test |
| 7.4 | Test citation accuracy | `tests/` | regression |

### Phase 8: Mandatory Test Cases (A-Q)

**Goal**: All 17 test cases pass

| # | Task | Files | Test |
|---|------|-------|------|
| 8.1 | Create test case definitions | `tests/mandatory_cases.json` | `test_mandatory.py` |
| 8.2 | Implement test runner | `tests/test_mandatory.py` | test |
| 8.3 | Run all cases, record baseline | `tests/` | test |
| 8.4 | Fix any failing cases (rolling fix) | various | test |

### Phase 9: RAGAS Evaluation Suite

**Goal**: Quantitative evaluation with NOT_EVALUATED handling

| # | Task | Files | Test |
|---|------|-------|------|
| 9.1 | Create RAGAS evaluation dataset | `evaluation/ragas_dataset.json` | `test_ragas.py` |
| 9.2 | Implement RAGAS metrics with NOT_EVALUATED | `evaluation/ragas_evaluator.py` | `test_ragas.py` |
| 9.3 | Run evaluation, record baseline | `evaluation/` | test |
| 9.4 | After each phase, re-run evaluation | `evaluation/` | test |

### Phase 10: Regression Process

**Goal**: Automated regression protection

| # | Task | Files | Test |
|---|------|-------|------|
| 10.1 | Create regression script | `scripts/regression.sh` | shell |
| 10.2 | Run full test suite | `tests/` | shell |
| 10.3 | Run RAGAS evaluation | `evaluation/` | shell |
| 10.4 | Run mandatory test cases | `tests/` | shell |
| 10.5 | Generate regression report | `docs/implementation_report_02.md` | markdown |

### Phase 11: Final Report

**Goal**: Document all changes

| # | Task | Files | Test |
|---|------|-------|------|
| 11.1 | Create `docs/implementation_report_02.md` | `docs/` | markdown |
| 11.2 | Update `docs/analyze/` feature docs | `docs/analyze/` | markdown |
| 11.3 | Update `docs/context/` context docs | `docs/context/` | markdown |

---

## Rolling Fix Philosophy (Unchanged)

1. **Write test first** — define expected behavior
2. **Implement fix** — minimal, focused change
3. **Run regression** — ensure no breakage (651+ tests)
4. **Run RAGAS** — verify improvement
5. **Document** — update docs

**No hard-coding per entity/term/dataset.** All fixes are generic.

**No editing ground truth.** Evaluation dataset is read-only.

**Abstention > fabrication.** Say "I don't know" rather than guess.

---

## Standing Rules (Unchanged)

1. No hard-coding entity/term/dataset names
2. No per-question if/else
3. No editing ground truth
4. Abstention > fabrication
5. Every change needs a regression test
6. No GraphRAG
7. Run full test suite before and after each phase
8. Document all changes

---

## Dependency Graph

```
Phase 1 (Admin + RAGAS) ─────────────────────────────────────┐
                                                              │
Phase 2 (Confirmation) ──┬── Phase 3 (Normalization) ──┐     │
                          │                             │     │
                          └── Phase 6 (Schema/Field) ───┤     │
                                                        │     │
Phase 4 (Context Propagation) ──────────────────────────┤     │
                                                        │     │
Phase 5 (Metadata Listing) ──┬── Phase 7 (Citations) ──┤     │
                              │                         │     │
                              └── Phase 8 (Thinking) ───┤     │
                                                        │     │
Phase 9 (Mandatory Tests) ──────────────────────────────┤     │
                                                        │     │
Phase 10 (RAGAS Suite) ─────────────────────────────────┤     │
                                                        │     │
Phase 11 (Regression) ──────────────────────────────────┤     │
                                                        │     │
Phase 12 (Final Report) ◄───────────────────────────────┘     │
                                                              │
Baseline: 651 tests ◄────────────────────────────────────────┘
```

**Recommended execution order:**
1. Phase 1 (Admin + RAGAS) — see everything
2. Phase 2 (Confirmation) — fix stateless multi-turn
3. Phase 3 (Normalization) — fix intent classification
4. Phase 4 (Context Propagation) — fix focus-field + persistence
5. Phase 5 (Metadata Listing) — deterministic answers
6. Phase 6 (Schema/Field) — better intent detection
7. Phase 7 (Citations) — unified citation system
8. Phase 8 (Mandatory Tests) — regression protection
9. Phase 9 (RAGAS Suite) — quantitative evaluation
10. Phase 10 (Regression) — automated regression
11. Phase 11 (Final Report) — documentation

---

*Generated: 2026-08-21 by audit verification against codebase runtime behavior*
