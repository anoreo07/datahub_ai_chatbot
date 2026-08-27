# RAGAS Implementation Report

## 1. Baseline

| Metric | Before | After |
|---|---|---|
| Tests | 672 passed, 1 failed (429) | 716 passed, 1 failed (429) |
| New tests | — | +44 (22 RAGAS + 12 prior + 10 other) |
| RAGAS library | Not installed | ragas 0.4.3 installed |
| interaction_logs table | No migration | Migration 7 created |
| evaluation_status | N/A (column absent) | NOT_EVALUATED default |
| retrieved_contexts | N/A (column absent) | JSON column |
| human_review | N/A (column absent) | 5-state review |
| Admin API | 2 endpoints (basic) | 6 endpoints (filter/sort/page/review/eval/summary) |
| Admin UI | 5 tabs | 6 tabs (+ Interactions) |

## 2. Architecture Before

```
Chat Request → ChatService.answer() → log_request() + log_response()
                                      ↓
                                  interaction_logs table (no migration)
                                      ↓
                                  Admin API → Frontend (no consumer)
                                  
No RAGAS library. Custom keyword-overlap "faithfulness" (evaluation/metrics.py).
update_ragas_scores() = dead code (0 callers).
No evaluation in live chat pipeline.
Admin page: 5 tabs (no Interactions).
```

## 3. Root Causes (from ragas_trace_report.md)

1. No Alembic migration for `interaction_logs`
2. `update_ragas_scores()` dead code
3. No evaluator in chat pipeline
4. Frontend had no Interactions tab

## 4. Changes Implemented

### 4.1 Database
- **Migration 7** (`database/migrations/versions/7_add_ragas_evaluation.py`):
  - `evaluation_status` (String(16), default NOT_EVALUATED)
  - `evaluation_error` (Text)
  - `evaluation_model` (String(128))
  - `evaluated_at` (DateTime)
  - `retrieved_contexts` (JSON)
  - `human_review` (String(32))
  - `human_review_note` (Text)
  - `human_reviewed_at` (DateTime)
  - Index on `evaluation_status`
  - `evidence_records` table
- **Model** (`database/models.py:304-380`): All new columns added to InteractionLog

### 4.2 RAGAS Evaluator
- **New file** (`evaluation/ragas_evaluator.py`):
  - Uses `ragas` library v0.4.3
  - Metrics: faithfulness, answer_relevancy, context_precision, context_recall
  - LLM backend: Fireworks/DeepSeek via LangChain wrapper
  - Async with timeout (30s default)
  - Graceful degradation: NOT_EVALUATED when no context, FAILED when LLM unavailable
  - Versioned evaluation model string

### 4.3 Interaction Logger
- **Rewritten** (`app/services/interaction_logger.py`):
  - `log_request()`: Creates interaction entry
  - `log_response()`: Updates with response + context snapshot + evaluation_status
  - `update_ragas_scores()`: Writes RAGAS metrics (no longer dead code)
  - `set_evaluation_status()`: PENDING/RUNNING/COMPLETED/FAILED
  - `set_human_review()`: accepted/needs_review/incorrect/hallucination/insufficient_evidence
  - `get_interactions()`: Paginated list with filters (status, intent, search, sort)
  - `get_interaction()`: Full detail with contexts + scores
  - `get_summary()`: Aggregate stats for dashboard

### 4.4 Chat Pipeline Integration
- **ChatService** (`app/services/chat_service.py`):
  - `_log_interaction_async()`: Dedicated session for logging (avoids autoflush conflicts)
  - `_background_ragas_eval()`: Async evaluation with fresh session
  - `log_request` + `log_response` called via dedicated session
  - Context snapshot (`docs`) passed to `log_response`
  - Background RAGAS triggered via `asyncio.create_task()`
  - Test mode (APP_ENV=test) skips all interaction logging

### 4.5 Admin API
- **Enhanced** (`app/api/admin.py`):
  - `GET /interactions`: Pagination, filter by status/intent/search, sort
  - `GET /interactions/{id}`: Full detail with contexts + scores
  - `POST /interactions/{id}/evaluate`: Trigger/retry RAGAS evaluation
  - `POST /interactions/{id}/review`: Set human review status
  - `GET /ragas/summary`: Aggregate stats

### 4.6 Admin Frontend
- **New component** (`frontend/app/(app)/admin/interactions-panel.tsx`):
  - Summary dashboard (total, evaluated, pending, failed, avg scores)
  - Interaction list with search, filter by status/intent, pagination
  - Detail view: question, response, context, RAGAS metrics, human review
  - Score cards with interpretation (high/warning/low)
  - Retry evaluation on FAILED
  - Human review buttons
- **Admin page** updated with "Interactions" tab

### 4.7 Tests
- **New** (`tests/unit/test_ragas_evaluation.py`): 22 tests
  - Database model schema (7 tests)
  - Interaction logging (6 tests)
  - RAGAS evaluator (3 tests)
  - Security/credential leak (3 tests)
  - Migration validation (3 tests)

## 5. RAGAS Results

The RAGAS evaluator is functional but produces null scores in development because:
- Fireworks API key is not set in the test/dev environment
- The evaluator correctly returns FAILED status with error message when LLM is unavailable
- In production with a valid API key, metrics will be computed

## 6. Security Verification

- No Authorization/Bearer/JWT/password/API key in interaction logs or API responses
- All admin endpoints require admin role
- Interaction logs do not store raw auth headers
- `evaluator.py` credential check: PASS

## 7. Remaining Limitations

1. **RAGAS scores are null in dev** — requires Fireworks API key
2. **No Alembic migration in production flow** — `create_all()` used for dev; production needs `alembic upgrade head`
3. **Frontend tests** — no test framework configured in frontend; manual E2E required
4. **Background evaluation** — uses `asyncio.create_task()` (single process); production with multiple workers needs queue-based evaluation
5. **No real-time updates** — frontend polls on manual refresh; WebSocket/SSE for live updates not implemented
