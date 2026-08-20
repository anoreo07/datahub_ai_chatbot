# DataAtlas — Context Documentation Index

> Bộ tài liệu ngữ cảnh (context) của project DataAtlas — AI Chatbot cho DataHub.
> Mục đích: cung cấp bức tranh toàn cảnh chính xác, dựa trên **bằng chứng** (code, dữ liệu, test, log) để bất kỳ agent/mentor nào cũng có thể nắm được trạng thái hiện tại của hệ thống mà không cần đọc lại toàn bộ codebase.

## Quy ước ký hiệu bằng chứng

Mọi khẳng định trong bộ tài liệu được gán nhãn mức độ chắc chắn:

| Ký hiệu | Ý nghĩa |
|---|---|
| `[VERIFIED]` | Được xác minh trực tiếp từ code, dữ liệu, hoặc kết quả test. |
| `[OBSERVED]` | Quan sát được tại thời điểm ghi nhận (DB, log, runtime) — có thể thay đổi theo thời gian. |
| `[INFERRED]` | Suy luận hợp lý từ các bằng chứng gián tiếp — cần kiểm chứng thêm. |
| `[UNKNOWN]` | Chưa có đủ thông tin; ghi nhận là lỗ hổng tri thức cần bổ sung. |

## Danh sách tài liệu

| File | Nội dung | Trạng thái |
|---|---|---|
| `00_context_index.md` | File này — index + phần Validation | ✅ Hoàn chỉnh |
| `01_project_overview.md` | Tổng quan project, lịch sử, mục tiêu, stack | ✅ Hoàn chỉnh |
| `02_current_architecture.md` | Kiến trúc hiện tại: modules, data flow, auth/RBAC | ✅ Hoàn chỉnh |
| `03_data_knowledge_model.md` | Mô hình tri thức dữ liệu: entities, chunks, ACL, các nguồn dữ liệu | ✅ Hoàn chỉnh |
| `04_current_failures_and_tests.md` | Phân loại failures hiện tại + hệ thống test/benchmark | ✅ Hoàn chỉnh |
| `05_mentor_requirements.md` | 7 yêu cầu cốt lõi của mentor (từ các báo cáo đánh giá) | ✅ Hoàn chỉnh |
| `06_data_quality_gaps.md` | Các khoảng trống chất lượng dữ liệu | ✅ Hoàn chỉnh |
| `07_target_use_cases.md` | Các use-case mục tiêu + trạng thái hỗ trợ hiện tại | ✅ Hoàn chỉnh |
| `08_constraints_and_goals.md` | Ràng buộc và mục tiêu phát triển | ✅ Hoàn chỉnh |

## Bản đồ luồng đọc (recommended reading order)

1. **Bắt đầu**: `01_project_overview.md` → hiểu project là gì.
2. **Kiến trúc**: `02_current_architecture.md` → hiểu hệ thống vận hành thế nào.
3. **Dữ liệu**: `03_data_knowledge_model.md` → hiểu dữ liệu hệ thống đang có.
4. **Vấn đề**: `04_current_failures_and_tests.md` → hiểu hệ thống đang hỏng chỗ nào.
5. **Tiêu chuẩn**: `05_mentor_requirements.md` → hiểu đích đến phải đạt.
6. **Khoảng trống**: `06_data_quality_gaps.md` → hiểu rào cản về dữ liệu.
7. **Mục tiêu**: `07_target_use_cases.md` + `08_constraints_and_goals.md` → hiểu cần xây gì, với ràng buộc gì.

## Nguồn dữ liệu chính được tham chiếu

- **Code**: `app/`, `retrieval/`, `ingestion/`, `indexing/`, `llm/`, `guardrails/`, `database/`, `config/`, `sync/`, `workers/`, `frontend/`.
- **Dữ liệu**: PostgreSQL `chatbot` (localhost:5433), OpenSearch index `datahub-rag-chunks-v1` (localhost:9201), Redis (localhost:6380).
- **Dữ liệu pull từ DataHub thật**: `datahub_pull/*.txt` (snapshot corpus).
- **Test/benchmark**: `audit/` (baseline_benchmark_report.md, final_benchmark_report.md, final_metrics.json, rolling_fix_report.md, mentor_acceptance_report.md, data_landscape_audit.md, golden_benchmark.jsonl, test_cases_26.jsonl), `tests/`, `docs/SYSTEM_CONTEXT.md`, `docs/regression_report.md`, `docs/semantic_context_precision_report.md`, `docs/for_gpt.txt`, `context_data.txt`.

---

## Validation (xác minh bộ tài liệu)

### Files đã tạo
- ✅ 9 files đúng tên quy định trong `docs/context/` (`00` → `08`).

### Source code đã đọc (đại diện)
- ✅ `app/main.py` — router registration, lifespan, startup sync config.
- ✅ `app/api/chat.py` — endpoints `/api/v1/chat`, dependency injection `get_current_user`, auth wiring.
- ✅ `app/services/chat_service.py` — `ChatService.answer()` (line 535), user context default, domain filter.
- ✅ `app/auth/authorization.py` — `AuthorizationService`, `build_database_acl_filter`, `build_opensearch_acl_filter`, `filter_accessible_urns`, audit.
- ✅ `app/auth/models.py`, `app/auth/rbac.py` — `UserContext`, `EntityAcl`, `RbacService`.
- ✅ `database/models.py` — toàn bộ ORM models (Entity, EntityChunk, EntityAclDB, Rbac*, AuditLog, IndexJob, ...).
- ✅ `config/settings.py` — toàn bộ settings (APP_ENV, DATABASE_URL, EMBEDDING, LLM, JWT, ...).
- ✅ `retrieval/intent.py`, `retrieval/intent_resolver.py`, `retrieval/query_understanding.py` — intent taxonomy, router, QU layer.
- ✅ `retrieval/hybrid_search.py`, `retrieval/reranker.py`, `retrieval/evidence.py`, `retrieval/citation.py`, `retrieval/context_builder.py`, `retrieval/entity_resolver.py`, `retrieval/fuzzy.py`.
- ✅ `llm/generator.py`, `llm/client.py`, `llm/fireworks.py` — AnswerGenerator, provider resolution, fallback path.
- ✅ `guardrails/validation.py`, `guardrails/sanitizer.py` — output validation, secret masking.
- ✅ `indexing/` — chunker, embedder, pipeline, vector_store.
- ✅ `ingestion/` — mock_source, graphql_source, mappers, sync.py, document_parsers.
- ✅ `sync/` — incremental_sync, event_handler, dlq, retry, locks, consumer.
- ✅ `workers/` — sync_worker, indexing_worker, document_worker, embedding_worker, scheduler.
- ✅ `compose.yaml`, `Dockerfile`, `pyproject.toml`, `.env`, `.env.example`.

### Dữ liệu đã kiểm tra (read-only queries)
- ✅ PostgreSQL `chatbot`: bảng tồn tại = `entities, entity_chunks, entity_acls, sync_checkpoints, rbac_roles, rbac_role_domains, rbac_users, rbac_user_roles, audit_logs, conversation_history, index_jobs, image_records, vision_cache_records, alembic_version`.
- ✅ `entities` (9,067): dataset=8,542, dashboard=327, glossary_term=177, glossary_node=21. PROD=8,864, NULL env=203.
- ✅ `entity_chunks` = 21,194 (PostgreSQL) == OpenSearch `datahub-rag-chunks-v1` count 21,194.
- ✅ `entity_acls` = 884 (tất cả `internal`, `is_public=false`, 884 distinct URNs).
- ✅ `rbac_roles` = 5 (Tài chính, Logistics, Sản Xuất, VGreen, Sales); `rbac_users` = 0; `rbac_user_roles` = 0.
- ✅ `audit_logs` = 0 rows; `conversation_history` = 1,168; `index_jobs` = 1,203 (1,202 completed, 1 processing); `image_records` = 1.
- ✅ 9 domains phân bố: SẢN XUẤT=519, TÀI CHÍNH=209, KINH DOANH=93, CUNG ỨNG (TT)=67, LOGISTIC=67, HẬU MÃI=43, CUNG ỨNG (NĐH)=21, PHÁT TRIỂN XE=14, VGreen=1.
- ✅ OpenSearch: index `datahub-rag-chunks-v1` = 21,194 docs (441.4MB), health green.

### Test / benchmark / log đã đọc
- ✅ `audit/baseline_benchmark_report.md` — baseline 7/48 PASS (14.6%).
- ✅ `audit/final_benchmark_report.md` — pipeline 15/48 (31.3%); rich semantic 24/48 (50%).
- ✅ `audit/final_metrics.json` — 31/48 (64.58%) với lenient scoring.
- ✅ `audit/final_metrics_subset.json` — subset 12 tests, 6/12.
- ✅ `audit/rolling_fix_report.md` — progression baseline → 34 → 35 → 26/26 (r26) → golden 36/48*.
- ✅ `audit/root_cause_map.md` — root causes RC1a/RC1b/RC2...
- ✅ `audit/mentor_acceptance_report.md` — CASE1 domain-scoped PARTIAL, CASE2 vendor capacity FAIL, CASE3 pass.
- ✅ `audit/data_landscape_audit.md` — data landscape, dirty platform names.
- ✅ `audit/golden_benchmark.jsonl` (48), `audit/test_cases_26.jsonl` (26), `audit/baseline_raw.jsonl`, `audit/final_raw.jsonl`, `audit/baseline_verdicts.jsonl`, `audit/final_verdicts.jsonl`, `audit/test_harness/raw_26.jsonl`.
- ✅ `docs/SYSTEM_CONTEXT.md` — 85 cases, 38 PASS / 47 FAIL (~44.7%).
- ✅ `docs/regression_report.md` — 85 cases HTTP-level PASS, 120 turns.
- ✅ `docs/semantic_context_precision_report.md` — 85 cases, 25 critical / 15 high / 7 medium FAIL.
- ✅ `docs/for_gpt.txt`, `context_data.txt`, `datahub_pull/*.txt` samples.

### Điểm chưa xác minh (cần bổ sung)
- `[UNKNOWN]` Chi tiết từng dòng logic của `app/services/chat_service.py` (2,869 dòng) — chưa đọc hết từng nhánh.
- `[UNKNOWN]` `frontend/` — mới đọc cấu trúc, chưa đọc chi tiết từng component.
- `[UNKNOWN]` Cơ chế khởi tạo ACL ban đầu (884 ACL được seed từ nguồn nào) — chưa trace được migration/seed script.
- `[UNKNOWN]` Trạng thái runtime của `app/api/actions.py`, `app/api/storage.py`, `app/api/datasource.py` — chưa đọc.
- `[UNKNOWN]` LLM provider đang dùng thực tế (fireworks key) — chưa verify key hợp lệ tại runtime.

### Cảnh báo độ trễ (staleness)
- Bộ tài liệu được tạo từ snapshot **2026-08-20**. Repo có **56 files modified chưa commit** so với HEAD `8a87be5c` (`git status`).
- Các số liệu `[OBSERVED]` (counts, metrics) có thể thay đổi sau mỗi sync/index/re-run benchmark.