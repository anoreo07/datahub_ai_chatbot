# RAGAS Implementation Report

## 1. Architecture Before

```
User Question
  -> ChatService.answer()
    -> build_context(results) -> list[ContextDocument]
    -> LLM generates answer
    -> _background_ragas_eval(question, answer, _ctx_snap)
      -> convert ContextDocument -> str(ctx)  # BUG: ctx.text/ctx.chunk_text don't exist
      -> evaluate_interaction(retrieved_contexts=garbage_strings)
      -> RAGAS sees no context -> faithfulness = 0.0
```

## 2. Root Causes Found

### BUG 1 (CRITICAL): ContextDocument.content extraction
**File:** app/services/chat_service.py:537-546

Code checked `ctx.text` and `ctx.chunk_text`, but `ContextDocument` (retrieval/context_builder.py:18) has `content`.

Falls to `str(ctx)` which produces `<ContextDocument object at 0x...>`.

RAGAS received garbage strings as context. Faithfulness=0.0 was correct given garbage input.

### BUG 2: retrieved_contexts persistence
**File:** app/services/interaction_logger.py:109

`entry.retrieved_contexts = {"contexts": retrieved_contexts[:10]}` stored ContextDocument objects instead of strings.

### BUG 3: answer_relevancy score not extracted
**File:** evaluation/ragas_evaluator.py:327-328

Hardcoded `answer_relevancy=None` instead of reading from `scores`.

### BUG 4: AnswerRelevancy missing embeddings
ragas.metrics.AnswerRelevancy requires `embeddings` parameter. Code skipped it entirely.

## 3. Architecture After

```
User Question
  -> ChatService.answer()
    -> build_context(results) -> list[ContextDocument]
    -> LLM generates answer
    -> _background_ragas_eval(question, answer, _ctx_snap)
      -> convert ContextDocument.content -> str  # FIXED
      -> evaluate_interaction(retrieved_contexts=real_context_strings)
      -> RAGAS metrics:
        - Faithfulness (always)
        - AnswerRelevancy (always, with Ollama embeddings)
        - ContextPrecision (only if reference)
        - ContextRecall (only if reference)
      -> update_ragas_scores()
```

## 4. Metrics Implemented

| Metric | Status | Input | Meaning |
|--------|--------|-------|---------|
| Faithfulness | COMPLETED | question, answer, contexts | Answer supported by context |
| Answer Relevancy | COMPLETED | question, answer, contexts | Answer addresses question |
| Context Precision | NOT_EVALUATED | needs reference | Context relevant to reference |
| Context Recall | NOT_EVALUATED | needs reference | Context covers reference |

## 5. Gemini Integration

- **Model 1:** gemini-3.1-flash-lite (primary)
- **Model 2:** gemini-3.5-flash-lite (failover)
- **Endpoint:** OpenAI-compatible via Google AI
- **Failover:** round-robin with 10s cooldown
- **Timeout:** 45s per model, 120s total

## 6. Embedding Integration

- **Provider:** Ollama (nomic-embed-text)
- **Endpoint:** OpenAI-compatible via localhost:11434
- **Used by:** AnswerRelevancy metric
- **Wrapper:** `_OllamaEmbeddingsWrapper` for ragas compatibility

## 7. Persistence

- `interaction_logs` table with RAGAS columns
- `retrieved_contexts` stored as JSON string
- `evaluation_model`, `evaluation_status`, `evaluation_error`
- Scores: faithfulness, answer_relevancy, context_precision, context_recall

## 8. API

- `GET /admin/interactions` — list with filter/sort/pagination
- `GET /admin/interactions/{id}` — full detail
- `POST /admin/interactions/{id}/evaluate` — trigger/retry
- `POST /admin/interactions/{id}/review` — human review
- `GET /admin/ragas/summary` — aggregate stats

## 9. Test Results

| Metric | Before | After |
|--------|--------|-------|
| Tests | 716 passed, 1 failed | 716 passed, 1 failed |
| Faithfulness | 0.0 (garbage context) | 1.0 (real context) |
| Answer Relevancy | N/A | 0.80 |
| Context Precision | N/A | needs reference |
| Context Recall | N/A | needs reference |

## 10. Known Limitations

1. **ContextPrecision/ContextRecall need reference** — no ground truth dataset yet
2. **Faithfulness edge cases** — negative claims (e.g., "no domain") score 0.0 even when correct
3. **No explanation layer** — metrics don't provide explanations
4. **No overall score** — need to compute from available metrics
5. **Admin UI not updated** — need to show all 4 metrics properly

## 11. Files Changed

- `evaluation/ragas_evaluator.py` — Complete rewrite with Gemini + embeddings
- `app/services/chat_service.py` — Fixed ContextDocument.content extraction
- `app/services/interaction_logger.py` — Fixed context persistence + evaluation_model
- `config/settings.py` — Added GEMINI_API_KEY, GEMINI_MODEL_1/2
- `.env` — Added Gemini configuration
- `pyproject.toml` — Added ragas, langchain-google-genai, langchain-ollama
- `tests/unit/test_ragas_evaluation.py` — Fixed test_no_llm_returns_failed
