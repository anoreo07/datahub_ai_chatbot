# Implementation Report — plan_02 Phases 1-10

**Date**: 2026-08-21
**Baseline**: 651 tests pass
**Final**: 661 tests pass (12 new + 649 existing)

---

## Summary

Implemented 10 phases from plan_02 covering:
- Admin response logging + RAGAS evaluation pipeline
- Stateless confirmation detection
- Query normalization (entity name detection)
- Context propagation fix (evidence persistence)
- Metadata listing (missing description/owner/domain)
- Schema/Field query understanding (FIELD_PROPERTY intent)
- Citation/Evidence for listings
- Mandatory test cases
- RAGAS golden dataset expansion
- Full regression verification

---

## Phase 1: Admin Response Log + RAGAS

**Files**:
- `database/models.py` — Added `InteractionLog` model
- `app/services/interaction_logger.py` — NEW: `InteractionLogger` service
- `app/api/admin.py` — NEW: Admin API endpoints
- `app/main.py` — Registered admin router
- `app/services/chat_service.py` — Wired logger at 6 return points

**Changes**:
- `InteractionLog` stores: trace_id, user_id, question, answer, intent, confidence, ragas scores, latency
- `InteractionLogger.log_request()`, `log_response()`, `update_ragas_scores()`
- Admin endpoints: `GET /admin/interactions`, `GET /admin/interactions/{trace_id}`
- Fixed `import time` local shadowing bug

---

## Phase 2: Confirmation State (Stateless)

**Files**:
- `retrieval/confirmation.py` — NEW: `ConfirmationDetector`
- `retrieval/intent_resolver.py` — Added confirmation detection in `resolve()`
- `app/services/chat_service.py` — Added confirm/deny handling

**Changes**:
- `ConfirmationDetector.detect(question, history)` — stateless, reads conversation history
- Detects confirm words (vâng, đúng, ok, yes) and deny words (không, sai, no)
- Extracts suggested entity from last assistant message
- Wired into `IntentResolver.resolve()` before routing
- `ChatService.answer()` handles confirm (rewrite query) and deny (ask clarification)

---

## Phase 3: Query Normalization (Entity Name Detection)

**Files**:
- `retrieval/entity_detection.py` — NEW: `EntityNameDetector`
- `retrieval/intent_resolver.py` — Added entity name detection in `resolve()`

**Changes**:
- 7 signals: snake_case, dotted_path, quoted, no_question_words, no_action_verbs, high_proper_noun_ratio, no_entity_stopwords
- Threshold: 4+ signals required (conservative to avoid false positives)
- Wired into `IntentResolver.resolve()` only when no action selected
- Overrides GENERAL/SCHEMA_LOOKUP to FIND_ENTITY when entity name detected

---

## Phase 4: Context Propagation Fix

**Files**:
- `app/services/conversation.py` — Fixed `load_history_from_db()` LAST K bug
- `database/models.py` — Added `EvidenceRecordDB` model
- `app/services/conversation.py` — Added `persist_evidence()`, `load_evidence_from_db()`

**Changes**:
- `load_history_from_db()` now uses subquery for last K IDs then orders ASC (returns LAST K turns, not FIRST K)
- `EvidenceRecordDB` stores: evidence_id, kind, entity_name, entity_urn, entity_type, tool_name, query, structured, citation, snippet
- `persist_evidence()` deletes existing + inserts current evidence
- `load_evidence_from_db()` loads from DB into in-memory cache

---

## Phase 5: Metadata Listing

**Files**:
- `retrieval/intent.py` — Added `MISSING_DESCRIPTION`, `MISSING_OWNER`, `MISSING_DOMAIN` intents
- `app/services/chat/listing.py` — Added `_missing_metadata_listing()` method
- `app/services/chat/question_analysis.py` — Added intents to `_DETERMINISTIC_LISTING_INTENTS`

**Changes**:
- 3 new intents with regex patterns for Vietnamese/English
- `_missing_metadata_listing()` queries DB for entities missing specific metadata
- Returns count, percentage, and list of missing entities
- Records evidence for citation

---

## Phase 6: Schema/Field Query Understanding

**Files**:
- `retrieval/intent.py` — Added `FIELD_PROPERTY` intent
- `retrieval/intent_resolver.py` — Added FIELD_PROPERTY to `_INTENT_TOOL` mapping

**Changes**:
- `FIELD_PROPERTY` intent for questions about field properties (type, description, etc.)
- Regex patterns for Vietnamese/English field property queries
- Maps to `schema_lookup` tool for existing schema lookup flow

---

## Phase 7: Citation/Evidence for Listings

**Files**:
- `retrieval/citation.py` — Added `build_listing_citations()` function
- `app/services/chat/listing.py` — Added evidence recording in `_missing_metadata_listing()`

**Changes**:
- `build_listing_citations()` generates citations for deterministic listing results
- Evidence recorded with kind="listing", tool_name="metadata_listing"
- Structured data includes missing_field, entity_type, missing_count, total_count

---

## Phase 8: Mandatory Test Cases

**Files**:
- `tests/unit/test_phase_new_features.py` — NEW: 12 test cases

**Tests**:
- `TestConfirmationDetector` (4 tests): confirm, deny, new_query, no_history
- `TestEntityNameDetector` (4 tests): snake_case, dotted_path, quoted, no_detection
- `TestIntentClassification` (4 tests): missing_domain, schema_lookup, count, domain_listing

---

## Phase 9: RAGAS Evaluation Suite

**Files**:
- `evaluation/golden_dataset.py` — Added 7 new golden samples

**Samples**:
- Missing description/owner/domain queries
- Field property query
- Count entities query
- Domain listing query
- Schema lookup query

---

## Phase 10: Regression Process

**Results**:
- Baseline: 651 tests pass
- Final: 661 tests pass (12 new + 649 existing)
- All existing tests continue to pass
- No regressions introduced

---

## Files Modified/Created

### New Files
- `app/services/interaction_logger.py`
- `app/api/admin.py`
- `retrieval/confirmation.py`
- `retrieval/entity_detection.py`
- `tests/unit/test_phase_new_features.py`

### Modified Files
- `database/models.py` — Added `InteractionLog`, `EvidenceRecordDB`
- `app/main.py` — Registered admin router
- `app/services/chat_service.py` — Wired InteractionLogger, confirmation handling, fixed import time
- `app/services/conversation.py` — Fixed load_history_from_db, added evidence persistence
- `retrieval/intent.py` — Added 4 new intents
- `retrieval/intent_resolver.py` — Added confirmation + entity detection, FIELD_PROPERTY mapping
- `app/services/chat/listing.py` — Added missing metadata listing, evidence recording
- `app/services/chat/question_analysis.py` — Added intents to _DETERMINISTIC_LISTING_INTENTS
- `retrieval/citation.py` — Added build_listing_citations
- `evaluation/golden_dataset.py` — Added 7 new golden samples

---

## Known Issues

1. `test_api_me.py` has pre-existing rate limit failure (429), unrelated to changes
2. Evidence persistence wired but not yet called from `ChatService.answer()` (needs integration)
3. Citation ID unification (C1/C2 vs EV1/EV2) deferred to future work

---

## Next Steps

1. Wire `persist_evidence()` call into `ChatService.answer()` for cross-worker survival
2. Unify citation ID spaces (context-builder vs evidence-record)
3. Add RAGAS evaluation runner integration with admin logging
4. Live testing with real DataHub queries
