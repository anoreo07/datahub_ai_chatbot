# Data Lineage — Phân tích cơ chế

Phân tích feature **Data Lineage** (truy vết upstream/downstream của dataset) — `app/services/action_service.py` + `app/services/chat/lineage.py` + `retrieval/tools.py`.

## 1. Kích hoạt (Trigger / Intent)

- Intent `LINEAGE` (`retrieval/intent.py:177`): *"lấy dữ liệu từ đâu"*, *"upstream"*, *"downstream"*, *"lineage"*, *"nguồn"*, *"phụ thuộc"*, *"dòng dữ liệu"*, *"data flow"*.
- Phân nhánh `LINEAGE_UPSTREAM` / `LINEAGE_DOWNSTREAM` (`intent.py:13-14`) → normalize về `LINEAGE` (`LEGACY_FOR`, `:51-52`).
- `retrieval/classifier.py` — direction: `downstream`/`xuống` → downstream; `upstream`/"nguồn dữ liệu" → upstream; mặc định `both` (`:245`).
- **API**: `POST /api/v1/actions/lineage` (`app/api/actions.py:72`); chat đi qua tool `lineage` (`intent_resolver.py:125-134`, prompt "Data lineage của dataset ...").

## 2. Pipeline — hai đường thực thi

### a) API/action service (`action_service.py:305 build_lineage_data`) — **live GraphQL**
1. `_lineage_urns(urn)` (`:290`): gọi live `get_lineage` upstream + downstream → list URNs.
2. `_resolve_urns` (`:284`): nạp entity cho tất cả URNs từ DB.
3. `_nodes` (`:309`): mỗi URN (trừ chính nó) → `LineageNode(name, urn, url, entity_type)`; URN không resolve được → fallback hiển thị raw URN.
4. Không có lineage cả hai chiều → trả `None` (API: `LineageData` rỗng, `actions.py:86-87`).

### b) Chat (`app/services/chat/lineage.py`) — **payload-based**
- `build_lineage_data` (`:16`): dùng `payload["upstreams"]`/`payload["downstreams"]` của SearchResult (đã sync vào DB):
  - Dedupe bỏ URN trùng chính nó (`_dedupe`, `:20`).
  - **Rule up-only**: entity xuất hiện CẢ hai chiều → chỉ giữ upstream, loại khỏi downstream (`:33`) — tránh render 2 lần.
  - Mỗi node resolve tên/url qua `entity_repo.get_by_urn`.
- `build_lineage_answer` (`:58`): câu trả lời **deterministic** từ CHÍNH payload đó (không LLM):
  - Mỗi URN → citation `E1`, `E2`, ... (`Citation` source_type `datahub_entity`).
  - Output: *"Dataset X có lineage theo DataHub: N upstream: tên [E1], ...; M downstream: tên [E2], ..."*.
  - `mask_secrets` an toàn trước khi trả về.

### c) Tool lineage (`retrieval/tools.py:220`)
- `_live_lineage_urns` (`:159`): refresh lineage trực tiếp từ nguồn (payload chỉ có 1-hop cũ) → gộp `live_lineage`.
- Lọc theo direction (upstream/downstream/both, `:234-240`); `graph_expander` hỗ trợ depth cho indirect downstream (`:131`).

## 3. Entity type resolution (`structured_retrieval.py:469`)

- **Type-aware**: phát hiện loại entity câu hỏi nêu (`_detect_entity_type`):
  - *"dashboard X dùng những dataset nào làm nguồn?"* → resolve **dashboard** trước, fallback dataset.
  - Ưu tiên **identifier catalog verbatim** (`Report_Supply_Capacity`, `dms.stg.stg_contact`) qua `_extract_identifiers` — name-extractor hay canonicalise hỏng.
- Câu hỏi "lấy dữ liệu từ đâu / upstream / downstream" → `entity_name_for(question, [...])` để tìm entity gốc.

## 4. Nguyên tắc cốt lõi

1. **Grounding**: API dùng live GraphQL; chat dùng payload sync (đã qua ACL khi search).
2. **Deterministic answer**: lineage text sinh từ dữ liệu thật, kèm citation trỏ vào từng entity.
3. **Không bịa**: entity URN không resolve → hiện raw URN chứ không suy đoán tên.
4. **Dedupe chặt**: bỏ trùng + rule up-only để graph không render lặp.
5. **Hỗ trợ cả hai chiều**: upstream/downstream/both theo câu hỏi.

## 5. File tham chiếu

- `app/services/action_service.py` — `build_lineage_data` (305), `_lineage_urns` (290), `_resolve_urns` (284)
- `app/services/chat/lineage.py` — `build_lineage_data` (16), `build_lineage_answer` (58)
- `app/services/chat/structured_retrieval.py` — lineage resolution type-aware (469)
- `retrieval/tools.py` — tool `lineage` (220), `_live_lineage_urns` (159)
- `retrieval/graph_expander.py` — expand depth
- `retrieval/intent.py` — LINEAGE rules (177)
- `app/api/actions.py` — `POST /actions/lineage` (72)
- `app/schemas/chat.py` — `LineageData`, `LineageNode`