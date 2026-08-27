# Search Dataset — Phân tích cơ chế

Phân tích feature **Search Dataset** (tìm kiếm dataset/entity) — API `app/api/search.py` + `retrieval/hybrid_search.py` + routing chat.

## 1. Kích hoạt (Trigger / Intent)

- **API**: `GET /api/v1/search?q=...&entity_type=...&domain=...&platform=...&owner=...&tag=...&column=...&limit=N` (`app/api/search.py:92`). Cũng có `GET /api/v1/search/stats` (đếm entity theo type, `:75`).
- **Chat**: intent `FIND_ENTITY`/`GENERAL` (default, `retrieval/intent.py:282`) → `hybrid_search` tool (`intent_resolver.py:369`, `_INTENT_TOOL`). Discovery sentences ("dataset X ở đâu", "có báo cáo nào về ...") đi qua `HybridSearch.search`.

## 2. Pipeline tìm kiếm (`retrieval/hybrid_search.py:132 search`)

Đường đi lần lượt — đường nào có kết quả tin cậy thì dừng:

1. **Exact match** (`:135`): `EntityResolver.resolve` ra `exact_match` → trả về đúng 1 entity.
2. **Single resolved** (`:148`): resolver chốt 1 entity không ambiguity VÀ câu hỏi có dấu hiệu tên entity (`_names_entity`) hoặc score ≥ `ENTITY_RESOLVER_TRUST_THRESHOLD` → trả về entity đó. Chặn clarification rác cho những câu hỏi nêu đích danh entity.
3. **Candidates** (`:156`): resolver trả top candidates (≤5) — chỉ dùng khi câu hỏi có tên entity hoặc top candidate đủ mạnh (chống keyword spillover của discovery sentences).
4. **Hybrid vector search** (`:169`): embed query → `OpenSearchVectorStore.hybrid_search` (BM25 keyword + vector, `top_k`).
5. **TokenDiscovery merge** (`:175-214`): bổ sung candidate từ token discovery (domain-scoped semantic). Vì câu tiếng Việt không khớp token kỹ thuật trong entity content (vd *"WIP giữa MES và SAP"* → `Báo cáo check WIP MES_SAP`). Token được expand (`expand_query_tokens`), entity được chấm bằng `score_entity`, điểm merge = `0.9 + 0.1*hits/max_hits` (full-token-match có thể vượt vector hits).
6. **Mock fallback** (`:216-222`): chỉ khi không có kết quả VÀ `USE_FAKE_OPENSEARCH`/`USE_MOCK_DATAHUB` → scan source theo token.

## 3. Lọc & bảo mật

- **Domain RBAC** (`app/api/search.py:118`): user filter theo domain ngoài quyền → trả về 0 kết quả hoàn toàn (không lộ tên/số lượng).
- **ACL post-filter** (`:122`): `filter_accessible_urns` lọc mọi kết quả theo quyền user.
- **Filter bổ sung** (`:126`): `_matches_owner` / `_matches_tag` / `_matches_column` — so khớp chuẩn hóa (`_norm`: lowercase + bỏ dấu tiếng Việt) trên owners/tags/schema_fields.
- Snippet cắt `[:200]` ký tự; `datahub_url` đính kèm để mở nhanh trong DataHub UI.

## 4. Nguyên tắc cốt lõi

1. **Resolver-first**: entity được nêu đích danh thì không lan man sang fuzzy runner-up.
2. **Discovery chỉ khi có tín hiệu**: candidate fuzzy không tự surface cho câu discovery thiếu tên.
3. **Grounded kết hợp**: vector + token discovery bù nhau cho tiếng Việt/technical mix.
4. **RBAC/ACL chặt**: domain ngoài quyền = không lộ thông tin; mọi kết quả phải qua ACL.

## 5. File tham chiếu

- `app/api/search.py` — `GET /search` (92), `GET /search/stats` (75), `_matches_owner/tag/column` (45-72)
- `retrieval/hybrid_search.py` — `search` (132), `keyword_search` (225), `_search_mock_fallback` (111)
- `retrieval/discovery.py` — `TokenDiscovery`, `expand_query_tokens`, `score_entity`
- `retrieval/entity_resolver.py` — resolve + trust threshold
- `retrieval/intent.py` — `classify_intent` (266), default `GENERAL`
- `retrieval/intent_resolver.py` — tool mapping (369)
- `app/auth/authorization.py` — `filter_accessible_urns`, `can_access_domain`
- `tests/` — tests cho search + resolver