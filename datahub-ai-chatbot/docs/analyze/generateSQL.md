# Generate SQL — Phân tích cơ chế

Phân tích toàn bộ feature **Generate SQL** trong codebase (app/services/action_service.py, app/services/chat/flows.py, app/services/sql_llm.py, retrieval/intent.py, app/api/actions.py).

## 1. Kích hoạt (Trigger / Intent)

- Intent `SQL_GENERATION` (`retrieval/intent.py:42`, rules `:246-254`): bắt các câu dạng
  - *"viết câu lệnh SQL…"*, *"câu lệnh truy vấn…"*, *"trả về một câu sql"*, *"select …"*, *"from …"*
  - *"lấy các bản ghi có warehouse_id = 123"*, *"cho tôi bản ghi customer_id 5"* (tự nhiên ngôn ngữ, không cần từ "sql").
- Có thể gọi trực tiếp qua API `POST /api/v1/actions/sql` (`app/api/actions.py:44`) với `{dataset, columns}`.
- Routing: `app/services/chat_service.py:1348` — `chosen_tool == "sql_generator"` hoặc `intent == SQL_GENERATION` → `flows.py sql_generation_flow`.

## 2. Flow chọn bảng — 4 mức ưu tiên (`flows.py:57 sql_generation_flow`)

1. **Dataset được nêu tường minh**: `entity_hint` hoặc token dạng `table.column`/`snake_case` trùng dataset trong câu hỏi → resolve dataset đó, gọi `generate_sql` với các filter field tìm được.
2. **Field-aware discovery** (`action_service.py:395 discover_sql_candidates`):
   - Quét schema của tối đa 2000 dataset (lọc theo ACL của user qua `filter_accessible_urns`).
   - Trích filter fields bằng `extract_filter_fields` (`action_service.py:111`) — token dạng cột từ câu hỏi.
   - Điểm: **+2.0/field khớp schema** + **0.6/từ** metadata (name/description/glossary/domain) khớp câu hỏi.
   - Không fallback name-substring: chỉ là candidate khi schema thực sự chứa field hoặc metadata khớp mạnh.
3. **Chọn người thắng rõ ràng** (`flows.py:154-175`):
   - 1 candidate duy nhất, hoặc `best.score - candidates[1].score >= 1.5`, hoặc best có matched_fields mà candidates[1] không có.
   - Không rõ ràng nhưng best có field → **ưu tiên bảng `dim_*`** (bảng dimension là nguồn chuẩn định nghĩa field).
   - Vẫn không clear → **clarification** (`flows.py:189-199`): "Có nhiều dataset đều chứa trường X: … bạn muốn dataset nào?".
4. **Không có candidate** (`flows.py:138-151`): trả lời grounded *"Không tìm thấy dataset nào trong metadata DataHub có schema chứa trường lọc…"* — `insufficient_context=True`.

## 3. Sinh SQL deterministic, grounded (`action_service.py:456 generate_sql`)

- **Resolve dataset** → không có → `valid=False`.
- **Schema**: `_schema_columns(payload)`; không có cột nào → `valid=False` ("chưa có schema ghi nhận").
- **Validate cột được yêu cầu**: cột không tồn tại trong schema → liệt kê `unavailable_columns`, `valid=False` (không sinh SQL cho cột không có trong metadata).
- **Phân loại cột**: `numeric` (int/decimal/numeric/float/double/money) và `dateless` (date/timestamp/datetime) → dùng cho khối analytics.
- **JOIN grounded trên lineage** (`action_service.py:510-529`): lấy upstream qua `_lineage_urns`, so **cột trùng tên** giữa cột SELECT và schema bảng upstream → `JOIN {up} AS u1 ON t.shared = u1.shared` kèm lý do (mô tả bảng nguồn).
- **WHERE** (`action_service.py:542-550`): `extract_filter_values` (`:83`) trích `col = 'value'` từ câu hỏi bằng regex khớp **chỉ cột có trong schema**, escape `'` → `''`.
- **SQL output**: `SELECT t.col1, t.col2… FROM <table> AS t [JOIN…] [WHERE…]`.
- **Analytics bonus** (`:568-582`): nếu có cột numeric + date → thêm khối `GROUP BY date / COUNT(*) / SUM(numeric)`.
- **Explanation**: mô tả bảng, lý do từng JOIN, các filter trích từ câu hỏi — minh bạch mọi quyết định.

## 4. LLM enhance có ràng buộc (optional) — `flows.py:26 enhance_sql` → `sql_llm.py:61 GroundedSqlGenerator`

- LLM đọc câu hỏi + SQL grounded + **danh sách cột cho phép**, rewrite để sát ý người dùng (thêm WHERE/GROUP BY/ORDER BY).
- **Validation nghiêm ngặt** `_validate_grounded_sql` (`sql_llm.py:42`):
  - Phải bắt đầu `SELECT` (read-only).
  - Chặn DDL/DML: `_DANGEROUS` regex (create/alter/drop/truncate/delete/insert/update/grant/revoke/…).
  - Phải có `FROM`; không cho phép `;` nội bộ (chống multi-statement).
  - Mọi tham chiếu cột qua alias `t.` (`_COLUMN_REF_RE`) **phải thuộc allowed_columns**.
- Output không hợp lệ hoặc LLM không khả dụng → **fallback về SQL deterministic không đổi** — không bao giờ hallucinate cột/bảng.
- System prompt (`sql_llm.py:24`): "only SELECT, never invent columns/tables/schemas/aliases, no DDL/DML".

## 5. Nguyên tắc cốt lõi (đảm bảo an toàn & grounded)

1. **Không sinh SQL cho cột không có trong schema** — unavailable cột bị chặn từ đầu.
2. **Không bịa bảng/alias** — JOIN chỉ từ lineage thật, chỉ khi cột chung tồn tại.
3. **Luôn read-only** — enforced ở cả deterministic lẫn LLM boundary.
4. **LLM chỉ "đẹp hóa" trong không gian cột đã kiểm tra** — validate cột trên alias `t` trước khi dùng.
5. **Không fallback name-substring** khi discovery — thiếu thông tin thì hỏi lại hoặc trả lời grounded.

## 6. Giới hạn / phụ thuộc hiện tại

- Cần **lineage upstream** để sinh JOIN (trong DB thật lineage phần lớn trống → thường không có JOIN).
- Cần **schema đầy đủ** cho dataset; dataset thiếu schema → `valid=False`.
- LLM enhance phụ thuộc `GroundedSqlGenerator.available()` (LLM provider có sẵn) — không có thì dùng deterministic.

## 7. File tham chiếu

- `app/services/action_service.py` — `generate_sql` (456), `discover_sql_candidates` (395), `extract_filter_fields` (111), `extract_filter_values` (83), `_query_tokens` (132)
- `app/services/chat/flows.py` — `sql_generation_flow` (57), `enhance_sql` (26)
- `app/services/sql_llm.py` — `GroundedSqlGenerator` (61), `_validate_grounded_sql` (42), system prompt (24)
- `retrieval/intent.py` — intent `SQL_GENERATION` (42), rules (246-254)
- `app/services/chat_service.py` — routing (1348)
- `app/api/actions.py` — API `POST /actions/sql` (44)
- `tests/integration/test_sql_generation.py` — integration tests cho feature