# RAGAS Implementation Baseline

> Generated: 2026-08-21. Code is source of truth.

## Test Baseline

- **Total tests:** 673
- **Passed:** 672
- **Failed:** 1 (pre-existing: `test_me_endpoint_disabled` → 429 rate limit)
- **Duration:** 182s
- **Command:** `pytest tests/ --tb=no -q`

## Component Status

### InteractionLog Model
- **File:** `database/models.py:304-357`
- **Table name:** `interaction_logs`
- **Columns:** 33 (id, trace_id, user_id, conversation_id, question, selected_action, model, intent, message_intent, routing_decision, confidence, chosen_tool, entity_hint, entity_resolved_name, entity_resolved_urn, resolution_state, answer, ambiguous, insufficient_context, result_count, top_score, citation_count, processing_time_ms, faithfulness, faithfulness_status, answer_relevancy, answer_relevancy_status, context_precision, context_precision_status, context_recall, context_recall_status, created_at)
- **Migration:** NONE (tables created via `Base.metadata.create_all()` in `database/session.py:58`)
- **Status:** EXISTS but no formal migration

### InteractionLogger
- **File:** `app/services/interaction_logger.py:17-232`
- **Methods:**
  - `log_request()` (line 30) — **WIRED** into ChatService
  - `log_response()` (line 56) — **WIRED** into ChatService (8 call sites)
  - `update_ragas_scores()` (line 107) — **DEAD CODE** (0 callers)
  - `get_interactions()` (line 145) — Called by admin API
  - `get_interaction()` (line 187) — Called by admin API

### Admin API
- **File:** `app/api/admin.py:1-47`
- **Endpoints:**
  - `GET /api/v1/admin/interactions` (line 14) — list with pagination
  - `GET /api/v1/admin/interactions/{trace_id}` (line 33) — detail
- **Router registration:** `app/main.py:102`
- **Status:** EXIST, functional, no frontend consumer

### Evaluation Package
- **File:** `evaluation/metrics.py:61-84` — `compute_faithfulness()` (keyword-overlap, NOT RAGAS library)
- **File:** `evaluation/evaluator.py:129-192` — `Evaluator` class (CLI only)
- **File:** `evaluation/golden_dataset.py:1-172` — 21 built-in Vietnamese samples
- **File:** `scripts/evaluate.py:1-45` — CLI runner (manual only)
- **RAGAS library:** NOT INSTALLED (ModuleNotFoundError)

### Admin Frontend
- **File:** `frontend/app/(app)/admin/page.tsx:16`
- **Tabs:** Sync, Index, Documents, DataHub, Roles (5 tabs)
- **Missing:** Interactions/RAGAS/Evaluation tab

### Evidence System
- **File:** `app/services/chat/evidence.py:28` — EvidenceService
- **Memory:** `app/services/conversation.py:194` — `get_evidence()`, `persist_evidence()`
- **DB Model:** `database/models.py:359` — EvidenceRecordDB
- **Status:** Evidence is tracked in-memory per conversation, persisted in `evidence_records` table

### Scheduler/Background
- **File:** `workers/scheduler.py:4` — Stub (NotImplementedError)
- **Background tasks:** `asyncio.create_task()` in `app/main.py:68` (healthcheck only)
- **Status:** No evaluation scheduling

## Architecture Notes

1. Tables created via `create_all()` at startup — no formal migration needed for dev, but production needs Alembic
2. Evidence is stored per-conversation in memory + `evidence_records` table
3. Chat pipeline has 8 `log_response()` call sites covering all answer branches
4. No RAGAS library installed — only custom keyword-overlap faithfulness
5. `update_ragas_scores()` is dead code — never called
6. Frontend has no interaction viewing capability
