# TRACE REPORT — V-DataAtlas Chatbot Architecture & Pipelines
> Ngày phân tích: 2026-08-28 | Thực hiện theo BƯỚC 0

---

## 1. TỔNG QUAN FILE TRACE (THEO THỨ TỰ YÊU CẦU)

### Nhóm 1 — Chat Pipeline
1. `app/services/chat_service.py` — Orchestrator trung tâm điều phối toàn bộ luồng chat, từ routing intent, guardrails, image context, entity resolution, structured retrieval, generation đến postprocessing.
2. `app/api/chat.py` — Fast API HTTP/SSE streaming router exposing `/api/v1/chat` & `/api/v1/chat/stream`, inject authorization context và stream tokens.
3. `app/services/chat/entity_resolution.py` — Service phân giải thực thể (exact lookup, glossary alias, semantic expansion, suggestion fallback qua LLM/fuzzy).
4. `app/services/chat/question_analysis.py` — Tập hợp các regex patterns & helper functions phân tích câu hỏi (anaphora, field location, column meaning, datahub relevance, deterministic listing).
5. `retrieval/intent.py` — Định nghĩa enum `QueryIntent`, rule strings regex và hàm phân loại intent `classify_intent()`.
6. `retrieval/classifier.py` — LLM-based semantic intent classifier + fallback `regex_plan` tạo `QueryPlan`.
7. `retrieval/hybrid_search.py` — Pipeline tìm kiếm kết hợp (entity resolver exact match -> vector OpenSearch KNN -> token discovery).
8. `retrieval/context_builder.py` — Đóng gói danh sách SearchResult thành XML `<context>` và ContextDocument có ID E1, E2,...
9. `retrieval/reranker.py` — Reranker 4 trọng số (base score 0.5, semantic 0.2, graph 0.15, metadata 0.1, citation 0.05).
10. `retrieval/evidence.py` — Quản lý EvidenceRecord và phát hiện ràng buộc context-only / anaphora / field operations.
11. `retrieval/citation.py` — Xây dựng và validate citation URN mapping giữa model outputs và context documents.
12. `llm/generator.py` — AnswerGenerator RAG & streaming text generator, kết hợp multi-signal confidence và secret masking.

### Nhóm 2 — Foundation
13. `config/settings.py` — Quản lý cấu hình toàn hệ thống qua Pydantic BaseSettings (OpenSearch, LLM, Redis, Thresholds).
14. `config/constants.py` — Các hằng số cốt lõi (MVP_ENTITY_TYPES, chunk token targets, overlap, citation source labels).
15. `config/prompts.py` — Kho prompts hệ thống (SYSTEM_PROMPT, SEMANTIC_INTENT_PROMPT, QUERY_UNDERSTANDING_PROMPT, GUARDRAIL_RULES).
16. `guardrails/service.py` — GuardrailService điều phối kiểm tra scope, prompt injection, evidence validation, recommendation format.
17. `guardrails/scope.py` — ScopeClassifier bằng regex phát hiện câu hỏi out-of-scope (coding, math, infra, trivia).
18. `guardrails/sanitizer.py` — Hàm `mask_secrets()` che dấu token/key/connection string và `detect_prompt_injection()`.
19. `app/auth/authorization.py` — AuthorizationService kiểm tra quyền ACL người dùng trên Entity và OpenSearch/DB filters.
20. `app/auth/rbac.py` — RbacService đánh giá quyền truy cập domain theo RBAC data-driven snapshot.
21. `ingestion/normalizer.py` — Hàm `clean_name()` và `compute_content_hash()` chuẩn hoá dữ liệu catalog.

### Nhóm 3 — Tests
22. `tests/test_intent.py` — Unit tests cho intent classification.
23. `tests/test_entity_resolver.py` — Unit tests cho entity resolver scoring.
24. `tests/test_fuzzy.py` — Unit tests cho fuzzy matching và tiếng Việt phonetic folding.
25. `tests/test_guardrails.py` — Unit tests cho sanitization, scope, prompt injection.
26. `tests/retrieval/` — 16 files test chi tiết (classifier, coreference, graph, intent_resolver, query_understanding, reranker, validator,...).

---

## 2. BẢNG DANH SÁCH FUNCTIONS QUAN TRỌNG & TYPE SIGNATURES

| Module / Class | Function / Method | Input Types | Output Type |
|---|---|---|---|
| `ChatService` | `answer()` | `question: str, user: UserContext | None, conversation_id: str | None, suggested_name: str | None, model: str | None, selected_action: str | None, images: list[str] | None, ragas_enabled: bool, on_status, on_token` | `ChatResponse` |
| `EntityResolutionService` | `entity_name_for()` | `question: str, remove_words: list[str], prefer_type: str | None, trace_id: str | None` | `str` |
| `EntityResolutionService` | `suggest_entity()` | `original: str, entity_type: str | None, question: str, trace_id: str` | `Suggestion | None` |
| `EntityResolutionService` | `resolve_glossary_by_alias()` | `term_name: str, question: str | None, trace_id: str | None` | `list[SearchResult]` |
| `EntityResolutionService` | `resolve_with_expansion()` | `term_name: str, question: str, entity_type: str | None, scope: QueryScope | None, trace_id: str | None` | `ResolutionResult | None` |
| `retrieval.intent` | `classify_intent()` | `query: str` | `QueryIntent` |
| `retrieval.classifier` | `classify()` | `question: str, llm: BaseLLM` | `QueryPlan` |
| `retrieval.classifier` | `regex_plan()` | `question: str` | `QueryPlan` |
| `HybridSearch` | `search()` | `query: str, top_k: int = 10, **filters` | `list[SearchResult]` |
| `Reranker` | `rerank()` | `query: str, results: Sequence[SearchResult]` | `list[SearchResult]` |
| `context_builder` | `build_context()` | `results: Sequence[SearchResult], max_chunks: int = 8` | `tuple[list[ContextDocument], str]` |
| `AnswerGenerator` | `generate()` | `query: str, results: Sequence[SearchResult], intent: QueryIntent, history: list[tuple[str, str]] | None, recommendation: bool` | `tuple[str, list[Citation], list[ContextDocument], str, str]` |
| `AnswerGenerator` | `generate_stream()` | `query: str, results: Sequence[SearchResult], intent: QueryIntent, history: list[tuple[str, str]] | None, on_token: Callable, recommendation: bool` | `tuple[str, list[Citation], list[ContextDocument], str, str]` |
| `GuardrailService` | `enforce_scope()` | `query: str` | `str | None` |
| `GuardrailService` | `check_prompt_injection()` | `query: str` | `str | None` |
| `RbacService` | `can_access_domain()` | `user: UserContext, domain: str | None` | `bool` |
| `AuthorizationService` | `can_view_entity()` | `user: UserContext, entity_urn: str` | `bool` |

---

## 3. CÁC ĐIỂM DỄ VỠ (FRAGILE POINTS) ĐÃ PHÁT HIỆN

1. **`classify_intent()` bỏ quên `_GREETINGS` và `_CHITCHAT` check:**
   - Trong `retrieval/intent.py`, tập hợp `_GREETINGS` và `_CHITCHAT` đã được định nghĩa nhưng `classify_intent()` chỉ so khớp qua `_RULES` mà không kiểm tra tập `_GREETINGS` trước, dẫn đến `"hello"` bị trả về `QueryIntent.GENERAL` (làm rớt test `test_general_fallback`).
2. **Regex Anaphora / Entity Extraction bị nuốt ký tự đuôi:**
   - Trong `retrieval/coreference.py`, hàm bóc tách entity khi match cụm từ `"schema của dim_warehouse là gì?"` đang match regex greedy hoặc group thừa dẫn đến output `'dim_warehouse c'` hoặc `'dim_customer l'` thay vì `'dim_warehouse'`.
3. **Intent Resolver Action vs Message Conflict:**
   - Khi user chọn Action (ví dụ `Impact Analysis`) nhưng gõ câu hỏi tường minh về schema hoặc greeting (ví dụ `"sales_order có bao nhiêu cột?"` hoặc `"hello"`), `IntentResolver` trong `retrieval/intent_resolver.py` đang ưu tiên Action mà không `override`, gây lỗi test.
4. **ChatService kích thước quá lớn (>3000 lines):**
   - `app/services/chat_service.py` chứa quá nhiều luồng inline (SQL generation, lineage traversal, impact fallback, domain gating, vision orchestration) khiến việc chỉnh sửa dễ gây side-effect không mong muốn. Cần modularize sang `app/services/chat/`.
5. **Fuzzy Threshold cố định không linh hoạt:**
   - `fuzzy_score` hiện tại áp dụng ngưỡng cứng `0.85` (`ENTITY_RESOLVER_TRUST_THRESHOLD`). Tên dài như `dim_BaoCaoLayout` khi sai 1-2 ký tự (`dim_BaoCeoLayout`) bị rớt threshold nếu không tính theo độ dài chuỗi (Levenshtein distance adaptive).
6. **Thiếu module tạo thông báo gợi ý lỗi chính tả (Suggestion / Correction):**
   - Hiện tại hệ thống nếu không resolve được sẽ trả về không tìm thấy hoặc gọi LLM suggestion mà không append thông báo rõ ràng cho người dùng `EntityCorrection` (ví dụ: `⚠️ Lưu ý: Có phải ý bạn là dim_BaoCaoLayout?`).
7. **Thiếu Semantic Synonym Expansion trong BM25 Retrieval:**
   - Câu hỏi tự nhiên dùng từ ngữ đời thường (ví dụ: "lấy dữ liệu từ đâu", "bảng nào feed vào", "công thức tính Coverage date") chưa được expand từ đồng nghĩa trước khi query hybrid search, dẫn đến BM25 recall thấp nếu không match chính xác keyword metadata.
