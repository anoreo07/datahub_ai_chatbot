# RAGAS Implementation Trace Report

## Current Architecture

```
User Question
  -> ChatService.answer()
    -> Retrieval (hybrid_search) -> list[SearchResult]
    -> build_context(results) -> list[ContextDocument]
    -> LLM generates answer
    -> log_request() -- saves question + intent
    -> log_response(retrieved_contexts=_ctx_snap) -- saves answer + context
    -> _background_ragas_eval(question, answer, _ctx_snap)
      -> convert ContextDocument -> str(ctx)  <-- BUG: produces garbage
      -> evaluate_interaction(retrieved_contexts=ctx_strings)
        -> RAGAS Faithfulness (always)
        -> RAGAS ContextPrecision (only if reference)
        -> RAGAS ContextRecall (only if reference)
      -> update_ragas_scores()
    -> return ChatResponse
```

## Root Causes

### BUG 1 (CRITICAL): ContextDocument to string conversion is wrong
**File:** app/services/chat_service.py:537-546

The code checks for `ctx.text` and `ctx.chunk_text`, but ContextDocument (retrieval/context_builder.py:10-21) has `content`, not `text` or `chunk_text`.

Falls to `str(ctx)` which produces `<ContextDocument object at 0x...>`.

RAGAS receives garbage strings as context. Faithfulness=0.0 is correct given garbage input.

**Fix:** Check for `ctx.content` instead.

### BUG 2 (MEDIUM): retrieved_contexts stored as ContextDocument objects
**File:** app/services/interaction_logger.py:109

`entry.retrieved_contexts = {"contexts": retrieved_contexts[:10]}`

Receives list[ContextDocument] but typed as list[str]. JSON serialization produces garbage in DB.

**Fix:** Convert to strings before storing.

### BUG 3 (MEDIUM): AnswerRelevancy needs embeddings
ragas.metrics.AnswerRelevancy requires `embeddings` parameter. Current code skips it entirely.

Ollama nomic-embed-text is available locally. Can use it via langchain_ollama.

### BUG 4 (LOW): ContextPrecision/ContextRecall need reference
These metrics require a `reference` column in the dataset. Without reference, they are NOT_EVALUATED.

**Fix:** Generate reference from retrieved context + question when no ground truth available.

### BUG 5 (LOW): evaluator.py line 175 compares answer to itself
Local faithfulness metric passes response.answer as both answer AND context_text.

## Current Metrics

| Metric | Status | Issue |
|--------|--------|-------|
| Faithfulness | RUNNING | Input is garbage strings -> always 0.0 |
| Answer Relevancy | SKIPPED | Needs embeddings |
| Context Precision | SKIPPED | Needs reference |
| Context Recall | SKIPPED | Needs reference |

## Gemini Configuration

- GEMINI_MODEL_1: gemini-3.1-flash-lite
- GEMINI_MODEL_2: gemini-3.5-flash-lite
- Endpoint: https://generativelanguage.googleapis.com/v1beta/openai/
- Failover: round-robin with 10s cooldown

## Proposed Implementation

1. Fix ContextDocument.content extraction
2. Fix retrieved_contexts persistence
3. Add AnswerRelevancy with Ollama embeddings
4. Implement reference generation for ContextPrecision/ContextRecall
5. Add explanation layer for metrics
6. Fix overall score calculation
7. Update Admin UI
8. Create benchmark dataset
9. Run real E2E test
