# Real DataHub Integration Gap Analysis

## Mục tiêu

Tài liệu này liệt kê tất cả những gì cần thay đổi để chuyển từ MockDataHubSource
sang GraphQLDataHubSource thật trong production. Mỗi mục đều có file/line,
mức độ ưu tiên, và hướng dẫn fix.

---

## 1. GraphQL Pagination không hoạt động

**File:** `ingestion/graphql/queries.py` — `SEARCH_WITH_CURSOR_QUERY`

**Vấn đề:** Query `search` không hỗ trợ cursor pagination. `SCROLL_ACROSS_ENTITIES_QUERY`
đã được thêm nhưng `_list_type` trong `graphql_source.py` vẫn gọi `get_entity()` cho
mỗi search result (N+1 — xem mục 2).

**Fix:** Đảm bảo scroll query trả về đủ field để map entity mà không cần gọi riêng lẻ.
Xem `ingestion/graphql_source.py:304-321`.

---

## 2. N+1 API Calls trong GraphQL Sync

**File:** `ingestion/graphql_source.py:304-321` (`_list_type`)

**Vấn đề:** `_list_type` gọi `list_entities()` (1 call) sau đó gọi `get_entity(urn)` (1 call mỗi entity).
Với 100 datasets → 101 GraphQL calls.

**Fix:** `_search_hit_to_canonical()` (`graphql_source.py:174`) cần map đủ field
từ search hit (name, description, platform, owners, domain, glossaryTerms, tags)
mà không cần gọi type-specific query. Chỉ gọi `_get_dataset`/`_get_dashboard` khi cần
lineage/schema.

---

## 3. URN Type Routing Thiếu

**File:** `ingestion/graphql_source.py:121-138` (`_URN_TYPE_ROUTING`)

**Vấn đề:** `_urn_to_type` đã map 11 type (dataset, dashboard, glossaryTerm, chart,
dataFlow, dataJob, container, tag, mlModel), nhưng `get_entity` (line 147-157)
chỉ xử lý dataset/glossary_term/dashboard/document; các type khác fallback về
`_search_fallback_entity`. Type `document` chưa có `_get_document` (line 156 gọi
method không tồn tại — gây RuntimeError).

**Fix:** Thêm `_get_document()` vào `GraphQLDataHubSource` hoặc sửa fallback.

---

## 4. ACL Filtering Không Hoạt Động

**File:** `app/auth/authorization.py`

**Vấn đề:**
- `build_database_acl_filter()` và `build_opensearch_acl_filter()` luôn return `None`
- ACL chỉ lưu in-memory, không persist, không sync từ DataHub
- Không có bảng `entity_acls` trong database

**Cần làm:**
- Tạo model `EntityAclDB` trong `database/models.py`
- Migration để tạo bảng `entity_acls`
- Implement filter cho SQLAlchemy (WHERE entity_urn NOT IN denied, ...)
- Implement filter cho OpenSearch (bool should: is_public OR entity_urn IN allowed)
- Wire vào ChatService

---

## 5. Auth Bypass trong ChatService

**File:** `app/services/chat_service.py:29`

**Vấn đề:** `answer()` hardcode `user_id="local-developer"`.

**Fix:**
- `app/api/chat.py` — Inject `get_current_user` dependency
- `app/services/chat_service.py` — Nhận `UserContext` thay vì `user_id: str`
- Dùng user context cho entity resolution filtering + audit log

---

## 6. `MockDataHubSource` vs `GraphQLDataHubSource` Interface Gaps

| Method | Mock | GraphQL | Ghi chú |
|--------|------|---------|---------|
| `list_domains()` | ✅ sync (return list) | ❌ not implemented | Source abstract có `list_domains` async |
| `get_schema()` | ✅ | ❌ not implemented | Cần GraphQL `schema` field |
| `get_owners()` | ✅ | ❌ not implemented | Cần GraphQL `ownership` field |
| `get_by_domain()` | ✅ | ❌ not implemented | Cần filter param |
| `get_by_platform()` | ✅ | ❌ not implemented | |
| `get_by_environment()` | ✅ | ❌ not implemented | |
| `resolve_by_name()` | ✅ | ❌ not implemented | |
| `get_lineage()` | ✅ (local edges) | ✅ (GraphQL lineage) | Khác format response |

---

## 7. Factory/DI Không Chuẩn

**File:** `ingestion/factory.py:20`

**Vấn đề:** `create_datahub_source()` trả về `MockDataHubSource` khi `USE_MOCK_DATAHUB=true`,
`GraphQLDataHubSource` khi false. Khi chuyển production, cần context manager lifecycle
(connect, healthcheck, close).

**Fix:** Thêm `AsyncContextManager` pattern:
```python
async def get_datahub_source() -> AsyncIterator[DataHubSource]:
    source = create_datahub_source()
    try:
        if not await source.healthcheck():
            raise DataHubConnectionError("DataHub unreachable")
        yield source
    finally:
        await source.close()
```

---

## 8. Feature Flags Chưa Đồng Bộ

**File:** `.env.mock.example`, `config/settings.py`

**Vấn đề:** Khi `USE_MOCK_DATAHUB=false`, cần set `DATAHUB_GMS_URL` và `DATAHUB_ACCESS_TOKEN`.
Settings validator ở `ingestion/__init__.py` kiểm tra nhưng chưa có validation cho các
flag khác (USE_MOCK_LLM=false cần API key, etc).

**Cần thêm validator:**
```python
@model_validator(mode="after")
def validate_production_config(self):
    if not self.USE_MOCK_DATAHUB and not self.DATAHUB_GMS_URL:
        raise ValueError("DATAHUB_GMS_URL required when USE_MOCK_DATAHUB=false")
    if not self.USE_MOCK_LLM and not self.FIREWORKS_API_KEY:
        raise ValueError("FIREWORKS_API_KEY required when USE_MOCK_LLM=false")
    return self
```

---

## 9. Document Parser Thiếu Dependency

**File:** `pyproject.toml` — thiếu `PyMuPDF`

**Vấn đề:** `ingestion/document_parsers/pdf_parser.py` dùng `fitz` (PyMuPDF) nhưng
không có trong dependencies. Silent fallback thành latin-1 decode → mất dữ liệu.

**Fix:** Thêm `PyMuPDF>=1.23.0` vào `pyproject.toml` dependencies.

---

## 10. Index Rebuild Type Error

**File:** `app/api/index.py:26-32`

**Vấn đề:** `list_by_type` trả về `Sequence[Entity]`, dòng 26 gán cho `all_entities`,
sau đó cast `list(all_entities)` ở dòng 27. Code lộn xộn.

**Fix:**
```python
all_entities = []
for etype in ["dataset", "dashboard", "glossary_term", "document"]:
    all_entities.extend(await entity_repo.list_by_type(etype))
```

---

## 11. Workers Rỗng

**Files:** `workers/document_worker.py`, `workers/embedding_worker.py`

**Vấn đề:** Cả 2 worker infinite loop không làm gì.

**Fix:**
- Xóa khỏi `compose.yaml` nếu chưa implement
- Hoặc implement logic tối thiểu: poll Redis queue, process job

---

## 12. Metrics/Healthcheck Không DataHub-Aware

**File:** `app/api/health.py`

**Vấn đề:** Health endpoint chỉ kiểm tra DB, Redis (nếu có), không kiểm tra
DataHub connectivity. Khi `USE_MOCK_DATAHUB=false`, production cần check
DataHub GMS health.

**Fix:** Thêm DataHub health check vào health endpoint khi không mock.

---

## 13. Hardcoded JWT Secret

**File:** `config/settings.py`

**Vấn đề:** `JWT_SECRET_KEY: str = "dev-secret"`.

**Fix:** Xóa default value. Raise `ValueError` nếu dùng JWT mode mà không set secret.

---

## 14. Docker Build Không Nhất Quán

**File:** `.github/workflows/ci.yml`

**Vấn đề:** CI workflow references `platform/docker/chatbot.Dockerfile` nhưng
root `Dockerfile` ở `datahub-ai-chatbot/Dockerfile`.

**Fix:** Đồng bộ Dockerfile paths — quyết định root Dockerfile hoặc deploy/docker/Dockerfile.

---

## 15. Migration từ Mock Sang Real: Step-by-Step

### Phase 1 — Experiment (1-2 days)
1. Set `USE_MOCK_DATAHUB=false`, cấu hình `DATAHUB_GMS_URL`
2. Sửa `_search_hit_to_canonical` — map đủ field từ scroll result
3. Test `list_datasets()` với real DataHub (GraphQL query)
4. Fix N+1 trong `_list_type`

### Phase 2 — Feature Parity (3-5 days)
5. Implement `list_domains()` trong GraphQL source
6. Implement `get_schema()`, `get_owners()`, `resolve_by_name()`
7. Thêm `_get_document()` — hiện tại missing
8. Fix ACL — create entity_acls table, implement filters

### Phase 3 — Auth & Security (2-3 days)
9. Fix JWT secret validation
10. Wire `UserContext` vào ChatService
11. Implement ACL filtering trong ChatService

### Phase 4 — Production Readiness (2-3 days)
12. Add PDF parser dependency (PyMuPDF)
13. Fix workers hoặc xóa khỏi compose
14. Fix index rebuild type error
15. Đồng bộ Dockerfile paths
16. Thêm DataHub health check
