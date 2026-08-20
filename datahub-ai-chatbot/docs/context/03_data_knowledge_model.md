# DataAtlas — Mô hình tri thức dữ liệu (Data Knowledge Model)

## 1. Các tầng dữ liệu

Hệ thống có 4 tầng dữ liệu chính: `[VERIFIED]`

| Tầng | Nơi lưu | Mô tả |
|---|---|---|
| **Nguồn thô** | `datahub_pull/*.txt` (JSONL) | Snapshot raw từ DataHub corporate — nguồn ground truth |
| **Metadata DB** | PostgreSQL `chatbot` | Entities, chunks, ACL, RBAC, audit, history, jobs |
| **Vector store** | OpenSearch `datahub-rag-chunks-v1` | Chunks nhúng vector (768 dim), 21,194 docs |
| **Cache/queue** | Redis `:6380` | Cache, hàng đợi workers |

## 2. Snapshot dữ liệu (datahub_pull/)

`[VERIFIED]` — 12 file JSONL, tổng **11,259 records** (đã pull đủ 100%, state done):

| File | Records | Loại entity |
|---|---|---|
| `dataset.txt` | 8,542 | DATASET |
| `chart.txt` | 1,487 | CHART |
| `dashboard.txt` | 327 | DASHBOARD |
| `container.txt` | 347 | CONTAINER |
| `data_flow.txt` | 221 | DATA_FLOW |
| `data_platform.txt` | 86 | DATA_PLATFORM |
| `corp_user.txt` | 32 | CORP_USER |
| `glossary_term.txt` | 177 | GLOSSARY_TERM |
| `glossary_node.txt` | 21 | GLOSSARY_NODE |
| `domain.txt` | 9 | DOMAIN |
| `tag.txt` | 5 | TAG |
| `corp_group.txt` | 5 | CORP_GROUP |
| *(state: data_job)* | 0 | DATA_JOB (rỗng) |

> ⚠️ **Khoảng trống quan trọng**: DB `entities` chỉ chứa **4 loại** (dataset, dashboard, glossary_term, glossary_node). Các loại còn lại (chart 1,487, container 347, data_flow 221, tag 5, domain 9, data_platform 86, corp_user 32, corp_group 5) **đã pull về file nhưng chưa được load vào DB / index**. `[OBSERVED]` — khớp với `audit/data_landscape_audit.md`.

## 3. PostgreSQL `chatbot` — schema thực tế

`[VERIFIED]` — 14 bảng (read-only query `pg_tables`):

| Bảng | Số rows | Ghi chú |
|---|---|---|
| `entities` | **9,067** | dataset=8,542 · dashboard=327 · glossary_term=177 · glossary_node=21 |
| `entity_chunks` | **21,194** | chunk content + metadata + embedding_model |
| `entity_acls` | **884** | ACL theo entity URN |
| `sync_checkpoints` | 5 | trạng thái sync |
| `rbac_roles` | 5 | Tài chính, Logistics, Sản Xuất, VGreen, Sales |
| `rbac_role_domains` | 14 | role→domain mapping |
| `rbac_users` | **0** | chưa có user |
| `rbac_user_roles` | **0** | chưa có gán role |
| `audit_logs` | **0** | audit chưa được ghi |
| `conversation_history` | 1,168 | lịch sử hội thoại |
| `index_jobs` | 1,203 | 1,202 completed · 1 processing |
| `image_records` | 1 | vision images |
| `vision_cache_records` | n/a | vision cache |
| `alembic_version` | 1 | migration version |

### 3.1 Bảng `entities`

Cột: `id, urn, entity_type, name, display_name, description, platform, environment, domain, datahub_url, payload (json), content_hash, created_at, updated_at`. `[VERIFIED]`

- Environment: **PROD = 8,864**, **NULL = 203**. `[OBSERVED]`
- 9 domains phân bố: SẢN XUẤT=519, TÀI CHÍNH=209, KINH DOANH=93, CUNG ỨNG (TT)=67, LOGISTIC=67, HẬU MÃI=43, CUNG ỨNG (NĐH)=21, PHÁT TRIỂN XE=14, VGreen=1. `[OBSERVED]`
- Platform (từ `data_landscape_audit.md`): powerbi=3,396, redshift=3,089, glue=1,336, SAP=430, ... (xem `06_data_quality_gaps.md` cho dirty names).

### 3.2 Bảng `entity_chunks`

Cột: `id, entity_id, entity_urn, chunk_type, chunk_index, content, chunk_metadata (json), content_hash, embedding_model, indexed_at, created_at, updated_at`. `[VERIFIED]`

### 3.3 Bảng `entity_acls` (ACL persist)

Cột: `id, entity_urn, is_public, allowed_user_ids (ARRAY), allowed_groups (ARRAY), denied_user_ids (ARRAY), denied_groups (ARRAY), classification, tenant_id, created_at, updated_at`. `[VERIFIED]`

- 884 ACL, **tất cả** `is_public=false`, `classification='internal'`. `[OBSERVED]`
- Ví dụ ACL: URN DMS "Kế toán bán hàng.AR Receipts" → `allowed_groups=['finance-team','admin-group']`, internal. `[OBSERVED]`
- **Chỉ 884/9,067 entities có ACL** — 8,183 entities không có ACL (mặc định `can_view_entity` trả True). `[INFERRED]`
- **Cảnh báo**: `is_public=false` cho toàn bộ ACL nghĩa là non-admin chỉ được xem các URN trong allowed (theo `build_opensearch_acl_filter` → restrict về public entities khi không có rules). Hệ quả: người dùng anonymous (default) bị chặn toàn bộ nếu không có accessible rules? Cần verify runtime. `[INFERRED]`

## 4. OpenSearch `datahub-rag-chunks-v1`

`[OBSERVED]`:

- Health: **green**, 21,194 docs, 441.4MB primary store.
- Count khớp chính xác với `entity_chunks` (21,194). `[VERIFIED]`

## 5. Nguồn ground truth cho test (context files)

`[VERIFIED]`:

- **`context_data.txt`** (124KB, Aug 5): snapshot cũ — "135 datasets | 167 glossary terms", platform redshift.
- **`for_gpt.txt`** (318KB, Aug 18): snapshot mới hơn — "135 datasets | 167 glossary", có ambiguity group 23, phân bố domain 10+1, dùng cho sinh câu hỏi test.
- **`audit/golden_benchmark.jsonl`** (48 cases, 2026-08-17): golden dataset chuẩn.
- **`audit/test_cases_26.jsonl`** (26 cases): J1-J5 (JOIN_EVIDENCE/SCHEMA), M1 (MULTI_TURN), ... — dùng cho harness 26-case.

> ⚠️ Lưu ý: `context_data.txt`/`for_gpt.txt` nói "135 datasets" nhưng DB thật có **8,542 datasets** — các file ground truth này là **subset nhỏ** (có lẽ dataset redshift mẫu) dùng để sinh test, không phải toàn bộ corpus. `[INFERRED]` — cần đối chiếu chi tiết.

## 6. Mô hình tri thức chatbot hiểu gì

Dựa trên code `[VERIFIED]`:

- **Entity**: URN, type (dataset/dashboard/glossary_term/glossary_node), name, platform, domain, environment, description, payload.
- **Field (schema)**: qua schema lookup / structured retrieval — field name, data_type, description, nullable, is_primary_key.
- **Glossary term**: term ↔ datasets mapping, term definition.
- **Lineage**: upstream/downstream, impact analysis.
- **Owner**: entity owner lookup (deterministic từ stored enrichment — commit `8a87be5c`).
- **Domain**: entity domain lookup (deterministic).
- **Graph**: related datasets, join fields, multi-hop.

## 7. Khoảng trống tri thức (knowledge gaps)

`[VERIFIED]` / `[INFERRED]`:

1. **Chart/Container/DataFlow/Tag/Domain/CorpUser chưa vào DB** — câu hỏi về chart/tag/flow hiện không có dữ liệu index. `[VERIFIED]`
2. **ACL chỉ phủ 884/9,067 entities**. `[OBSERVED]`
3. **RBAC chưa có user thật** (0 rbac_users) — toàn bộ phiên runtime là anonymous hoặc admin. `[OBSERVED]`
4. **Audit log rỗng** — không thể dùng audit để trace access denial. `[OBSERVED]`
5. **Ground truth test files là subset** nhỏ (135 datasets) so với corpus 8,542 — benchmark sinh từ subset, có thể không đại diện toàn corpus. `[INFERRED]`
6. **Missing fields**: nhiều dataset không có description/owner/schema → retrieval thiếu evidence (xem `06_data_quality_gaps.md`).