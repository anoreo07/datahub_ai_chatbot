# Impact Analysis — Phân tích cơ chế

Phân tích feature **Impact Analysis** (đánh giá ảnh hưởng hạ nguồn khi xóa/thay đổi dataset) — `app/services/action_service.py` + `retrieval/intent.py` + `app/api/actions.py`.

## 1. Kích hoạt (Trigger / Intent)

- Intent `IMPACT_ANALYSIS` (`retrieval/intent.py:124-144`) — nhiều dạng câu hỏi:
  - *"nếu xóa/thay đổi X ..."*, *"delete dataset X what happens"*
  - *"ai bị ảnh hưởng"*, *"impact"*, *"blast radius"*, *"bị ảnh hưởng"*
  - Verb-first: *"Xóa dim_X thì những bảng nào bị ảnh hưởng?"* (`:131`)
  - Implicit: *"Xóa dataset X thì sao?"*, *"thay đổi X ra sao"* (`:136`)
  - Reverse: *"ảnh hưởng của việc xóa dataset X?"* (`:142`)
- `RECURSIVE_IMPACT` (`:120`) cho yêu cầu xuyên sâu/tất cả hậu duệ — được ưu tiên trước `IMPACT_ANALYSIS` thường.
- `retrieval/classifier.py:239` — direction mặc định `downstream` cho impact.
- **API**: `POST /api/v1/actions/impact` (`app/api/actions.py:56`) — `valid=False` → HTTP 404 với message.

## 2. Pipeline (`action_service.py:593 impact_analysis`)

1. **Resolve dataset** (`resolve_dataset`) → không tìm thấy → `valid=False` "Không tìm thấy dataset trong metadata DataHub."
2. **Lineage hạ nguồn** (`_lineage_urns`, `:290`): gọi live GraphQL `get_lineage(urn, direction="downstream")` → danh sách downstream URNs. Lỗi → `log.exception("action_lineage_failed")`, trả rỗng.
3. **Phân loại nạn nhân** (`:610-622`): resolve URNs → `_urn_kind(d_urn)` → 4 nhóm:
   - `dashboard`, `pipeline`, `job`, còn lại → `datasets`.
4. **Bổ sung dashboard** (`:624-631`): quét dashboard (≤1000) có payload `upstreams` chứa entity này (chỉ khi admin hoặc không có auth) → thêm vào `affected_dashboards` (không trùng).
5. **Mức rủi ro** (`:633-638`): `total ≥ 6` → `high`; `≥ 3` → `medium`; còn lại `low`.
6. **Business impact text** (`:640-658`): mỗi nhóm khác rỗng → câu liệt kê 5 tên đầu (+ "..." nếu nhiều hơn); không có gì → "Không tìm thấy phụ thuộc hạ nguồn nào từ lineage DataHub."

## 3. Response (`ImpactResponse`)

- `dataset`, `urn`, `valid`
- `affected_datasets` / `affected_dashboards` / `affected_pipelines` / `affected_jobs` — mỗi `ImpactItem` = `{urn, name, url, kind}`
- `business_impact`: danh sách câu tiếng Việt giải thích
- `risk_level`: low/medium/high

## 4. Nguyên tắc cốt lõi

1. **Deterministic, grounded**: chỉ dùng lineage thật từ DataHub — không bịa nạn nhân.
2. **Chỉ hạ nguồn (downstream)**: impact = ai tiêu thụ dataset này; upstream không thuộc phạm vi.
3. **Trung thực**: không có lineage → nói rõ "không tìm thấy phụ thuộc" thay vì phỏng đoán.
4. **Bảo mật**: resolve có ACL (nếu có user); dashboard augmentation bị giới hạn admin.
5. **Rủi ro định lượng đơn giản**: theo tổng số nạn nhân, không cần LLM.

## 5. File tham chiếu

- `app/services/action_service.py` — `impact_analysis` (593), `_lineage_urns` (290), `resolve_dataset`
- `retrieval/intent.py` — rules `IMPACT_ANALYSIS` (124-144), `RECURSIVE_IMPACT` (120)
- `retrieval/classifier.py` — direction downstream (239)
- `app/api/actions.py` — `POST /actions/impact` (56)
- `app/schemas/actions.py` — `ImpactResponse`, `ImpactItem`
- `tests/integration/test_impact.py` — tests cho impact