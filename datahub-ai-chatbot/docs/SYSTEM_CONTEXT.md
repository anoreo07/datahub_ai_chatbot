# SYSTEM_CONTEXT — DataAtlas Chatbot (để vá lỗi semantic/context precision)

> File này cung cấp ngữ cảnh hệ thống cần thiết để một AI (hoặc kỹ sư) hiểu
> kiến trúc routing của chatbot DataAtlas và từ đó **vá đúng** các lỗi được ghi
> trong `docs/semantic_context_precision_report.md`.
>
> Mọi đường dẫn trong file này là **tương đối với `datahub-ai-chatbot/`** và,
> trừ khi ghi chú, đều trace về code thật đang chạy (môi trường local, backend
> `localhost:8000`, auth admin). Số dòng ghi theo trạng thái code hiện tại —
> nếu một hàm đã di chuyển, tìm theo tên hàm chứ không căn cứ số dòng.

---

## 1. Báo cáo và các lỗi cần vá

`docs/semantic_context_precision_report.md` = kết quả chạy **85 case**
(semantic + context precision) do `semantic_driver.py` sinh. Kết quả: **38 PASS /
47 FAIL (~44.7%)**. 0 lỗi HTTP; mọi FAIL là lỗi nội dung (semantic) mà một bộ
test HTTP-only không bắt được.

8 root-cause (RC) trong report, kèm **code location tương ứng** ở mục 4:

| RC | Pattern lỗi | FAIL tiêu biểu |
|----|-------------|----------------|
| RC-1 | Parser field-op không bắt cú pháp thông dụng (`kiểu gì`, `null không`, field đơn từ, connective `biểu diễn`) | A03 A04 B06 C03 D09 E08 M01 M05 G10 |
| RC-2 | Mất focus field / over-answer thành schema dump | A08 B03 E08 + toàn Group F |
| RC-3 | Anaphora/entity-switch sai trong ngữ cảnh dài (`nó có owner`, `quay lại …`) | C06 E03 M05/T10 |
| RC-4 | Composite/multi-subquestion không được decompose | Group F, H06–H08 |
| RC-5 | Thinking Mode under-trigger (0/10 Group H) | H01–H10 |
| RC-6 | Exact-name fast path không kích hoạt khi câu có thêm yếu tố | D09 G07 G09 |
| RC-7 | `không tìm kiếm thêm`/context-only không enforce với mọi cú pháp | D05 |
| RC-8 | Câu evidence-quality trả metadata thô thay vì đánh giá | G02 G03 G04 G10 |

---

## 2. Cấu trúc hệ thống

Backend: FastAPI. Pipeline mỗi `question` đi qua `ChatService.answer()` và một
chuỗi **gate/cổng** chạy tuần tự — thứ tự các gate quyết định hầu hết hành vi
semantic.

```
POST /api/v1/chat  (app/api/chat.py)
  → ChatService.answer()  (app/services/chat_service.py)
      ├─ vision gate        (ảnh)            ~L397-460
      ├─ EVIDENCE gate      (follow-up theo E1..En)  L472-490
      ├─ FIELD-PROPERTY gate(question tự mang entity+field)  L497-508
      ├─ THINKING gate      (GENERAL + complex) L524-570
      ├─ SQL gate                                 L576-582
      ├─ SYNC-relation gate                        L588-597
      ├─ quality gate                              L603-611
      ├─ conversational gate (GENERAL phi-DataHub) L616-632
      ├─ LISTING gate                               L634-679
      ├─ deterministic listing                      L681-690
      ├─ regex_plan / LLM plan                      L697-703
      ├─ Query Planner DAG (COMPOSITE/MULTI_ENTITY)L712-718
      └─ retrieval: anaphora / structured / hybrid  L727-917
          → rerank (L1060) → ambiguity clarify (L1074-1100)
          → generate (L1133-1187)
```

### 2.1 Các module then chốt

| Module | Vai trò |
|--------|---------|
| `app/services/chat_service.py` | Orchestrator + toàn bộ gate ở mục 4 |
| `app/services/chat/evidence.py` | Evidence store (E1..En) + trả lời từ evidence |
| `app/services/chat/field_ops.py` | Trả lời field-property (type/desc/glossary/nullable/...) |
| `retrieval/evidence.py` | `FieldOp`, regex property patterns, `parse_field_operation` |
| `retrieval/context_resolver.py` | `resolve_context` — câu tham chiếu evidence nào, focus field, op |
| `retrieval/context.py` | dependency `_ctx` (llm, hybrid_search, memory, evidence, planner...) |
| `retrieval/intent.py` | `QueryIntent` enum + regex router `_RULES` |
| `retrieval/intent_resolver.py` | Resolver intent → plan/tool, `regex_plan`, needs_semantic |
| `retrieval/thinking/complexity.py` | Complexity classifier (quyết định Thinking Mode) |
| `retrieval/thinking/planner.py` + `orchestrator.py` | DAG planning + synthesize |
| `retrieval/planner_executor.py` | Execute plan steps |
| `retrieval/entity_resolver.py` / `app/services/chat/entity_resolution.py` | Resolve tên entity, canonicalise, strict/trusted |
| `retrieval/reranker.py` | Rerank; ảnh hưởng ambiguity (score gap) |
| `retrieval/coreference.py` | Coreference/anaphora resolution |

---

## 3. Luồng dữ liệu + observability (đọc log để debug)

Mỗi request sau khi chạy sinh `trace_id`; các event route được ghi log qua
`log.info("<event>", trace_id=...)` và `semantic_driver.py` đọc chúng từ
`/tmp/datahub_backend.log` theo trace_id. Các event quan trọng cần grep:

- `intent_resolution` — intent/chosen_tool/routing_decision/entity_hint/plan_source
- `route_evidence_context` — evidence gate chạy (kèm `evidence=E1`)
- `route_field_property` — direct field-op gate chạy
- `route_field_op` / `evidence_answer` — field answer từ evidence (kèm op/property/field)
- `route_anaphora` — inferred_entity/inferred_type/has_anaphora
- `route_hybrid` / `route_structured` / `route_explicit_entity`
- `route_thinking_mode` / `thinking_complexity` / `thinking_skip`
- `chat_ambiguous_clarification` — clarification (guardrail #9)
- `chat_not_found` / `chat_term_not_found` / `chat_suggestion`
- `route_planner_dag` — DAG planner chạy

Khi một case FAIL, đọc events của trace_id đó trong log sẽ cho biết **gate nào
đã chạy / không chạy** — nguyên nhân root-cause gần như luôn nằm ở chỗ gate sai
bị tắt sớm hoặc parser không nhận diện.

> Lưu ý: log càng chạy nhiều test càng dài. `fetch_events` tìm theo `trace_id` trong
> toàn bộ file, nên cứ log accumulate.

---

## 4. Từng RC → code location để sửa

### RC-1. Parser field-op không bắt cú pháp thông dụng

Parser làm 2 việc: (a) detect property, (b) lấy field token.

- **Regex property**: `retrieval/evidence.py:159-182` (`_PROPERTY_PATTERNS`).
  - Thiếu `kiểu gì` → `data_type` KHÔNG match (chỉ có `kiểu dữ liệu|kieu du lieu|kiểu type|datatype|type`).
    → FAIL A03, C03, B06, M05/T4-T5, G10.
  - Thiếu `null không` / `có null` → `nullable` chỉ có `nullable|bắt buộc|…|cho phép null`.
    → FAIL M01/T4, M05/T4.
  - Thiếu `mô tả … là gì / mô tả gì` dạng rút gọn → một số mô tả không detect.
- **Field token**: `retrieval/evidence.py:208-218` (`_field_token`) dùng
  `extract_field_refs` + `looks_like_a_field`. Field **đơn từ không gạch dưới**
  (ví dụ `quantity`) không được nhận → `parse_field_operation` trả `None` →
  hỏi rơi xuống `route_hybrid` và trả clarification sai entity.
- **find_field connective**: `retrieval/evidence.py:184-191` (`_FIND_FIELD_RE`)
  chỉ hỗ trợ `liên quan|liên hệ|relate|chứa|gắn` — KHÔNG có `biểu diễn`.
  → FAIL A04 ("Field nào biểu diễn ngày giao dịch?").
- **Hàm nhận diện tổng**: `parse_field_operation` `retrieval/evidence.py:221-237`.

Khi property+field có đủ, trả lời từ `app/services/chat/field_ops.py:57-131`
(`answer_field_property`) — **đã** trả đúng type/desc/glossary/nullable. Vấn đề
chính là parser KHÔNG tạo được `FieldOp`, không phải phần trả lời.

**Hướng vá**: mở rộng regex 3 chỗ trên; đảm bảo field đơn từ (token không `_`
nhưng là từ khoá trong `schema_fields`) vẫn định nghĩa được bằng cách kiểm tra
nghịch đảo: nếu `schema_fields` hiện có chứa field trùng token thì tạo `FieldOp`.

---

### RC-2. Mất focus field / over-answer schema dump

- `resolve_context` `retrieval/context_resolver.py:195-228`: logic chọn
  `focus_field` (L286-307) lấy từ field-op → field_refs → `structured.focus_field`
  → `structured.join_field` → `_named_focus`. Khi câu `Field đó là gì?` không mang
  field mới, focus field của turn trước phải được giữ — hiện không bền.
- Câu hỏi field mà grammar không parse ra `FieldOp` sẽ lọt tới nhánh
  `hint == "schema"` trong `answer_from_evidence`
  `app/services/chat/evidence.py:338-345` → trả **toàn bộ schema** (over-answer).
- Thứ tự trong `answer_from_evidence` `app/services/chat/evidence.py:265-359`:
  field answer chạy trước (L269-273), nhưng chỉ khi `evidence_field_answer`
  (L362-430) tạo được `FieldOp`. Nếu không → đổ xuống schema listing.

**Hướng vá**: (1) persist focus field ở EvidenceRecord (`focus_field` đã có trong
field_ops flow nhưng chưa được lưu ổn định khi turn là schema-direct);
(2) khi `hint == schema` và có `focus_field`, ưu tiên trả property của focus đó;
(3) ngăn schema-listing cho câu dạng `Field đó …`/`… là gì` (thiếu op).

---

### RC-3. Anaphora / entity-switch sai trong ngữ cảnh dài

- `_is_contextual_followup` `app/services/chat/question_analysis.py:377-398` —
  bỏ qua nếu `_has_own_identifier` (L270). Đáng chú ý: `nó có owner nào?` khi
  `nó` = `fact_inventory_movement` lại bị resolve nhầm — xem nhánh
  `has_ctx` → `resolve_followup_entity` `app/services/chat/entity_resolution.py:238-292`.
  Log `route_anaphora` (chat_service L774-777) cho inferred_entity sai —
  CAD để debug.
- `_infer_entity_from_history` `app/services/chat/question_analysis.py:596` —
  heuristic token; có thể bắt nhầm "no owner" thành entity name (`'no owner'`),
  hay "Bonded Warehouse" (glossary term) thay vì `dim_warehouse`.
- M05/T10: "Quay lại warehouse_id của fact_inventory_movement" trả lời từ
  **dim_warehouse (E3)** — tức `_match_active_evidence` / `_last_schema`
  `retrieval/context_resolver.py:122-152` chọn evidence cuối (dim) thay vì câu
  `Quay lại …` phải bám vào entity tường minh. Kiểm tra
  `_evidence_for_field` (L163-174): nó ưu tiên evidence "chứa field" — nhưng nếu
  `warehouse_id` có ở cả E1 (FIM) lẫn E3 (dim), phải ưu tiên entity được nêu tên.

**Hướng vá**: khi câu mang entity tường minh (`Quay lại X …`, `X có owner`),
bind thẳng vào entity đó mà KHÔNG qua coreference history; canonicalise trước
khi so sánh với evidence.

---

### RC-4. Composite / multi-subquestion không decompose

- Regex router `retrieval/intent.py` chỉ map **một** intent/câu (SCHEMA_LOOKUP
  rule L140 bắt sớm: `(field|schema|trường|…)`).
- `regex_plan` / `intent_resolver` `retrieval/intent_resolver.py:367` +
  `chat_service.py:712-718` chỉ chạy DAG planner khi `plan.steps` hoặc intent
  `COMPOSITE_QUERY/MULTI_ENTITY_QUERY`. Câu F-style (schema + find + type) thường
  bị đánh `SCHEMA_LOOKUP` đơn → chỉ trả schema.
- `_extra_steps`/planner dò multi-source (`retrieval/thinking/planner.py:271+`)
  — nhưng chưa được gọi vì intent không phải GENERAL/COMPOSITE.

**Hướng vá**: thêm detector composite (nhiều mệnh đề với dấu phẩy/từ nối
`và/sau đó/cho biết … và …`) → ép sang `COMPOSITE_QUERY`/DAG planner (hoặc
Thinking) thay vì rơi vào SCHEMA_LOOKUP singleton.

---

### RC-5. Thinking Mode under-trigger (0/10 Group H)

- Complexity: `retrieval/thinking/complexity.py:122-183` — score ≥ 3 mới
  `complex`; nhiều câu H bị `reason=simple`.
- Gate `chat_service.py:524-570` chỉ chạy khi `intent == GENERAL` và **không**
  phải `_ctx_followup` (L521-523). Các câu bắt đầu `Phân tích …` bị regex
  `_RULES` bắt thành SCHEMA_LOOKUP/IMPACT trước khi tới thinking gate → không
  bao giờ vào `maybe_answer`.
- `maybe_answer` `retrieval/thinking/orchestrator.py:43` trả `None` với câu
  không đủ meta → gọi `is_complex` (L106) — chỉ để logging.

**Hướng vá**: cho câu general/complex rơi vào `is_complex` trước regex router;
khi có cụm planning/decomposition (`Phân tích … gồm … và`, `đánh giá`, `so sánh
… và …`) ép intent sang GENERAL để thinking gate bắt. Xem lại ngưỡng score cho
pattern "phân tích + liệt kê nội dung".

---

### RC-6. Exact-name fast path không kích hoạt

- Fast path `try_explicit_entity_lookup` chỉ chạy với
  `intent in (FIND_ENTITY, DATASET_LOOKUP)` — `chat_service.py:900-907`.
- `warehouse_id có kiểu dữ liệu gì trong fact_inventory_movement` → intent
  GENERAL (không có `field … của …`, vì `trong` hỗ trợ ở
  `_FIELD_OF_ENTITY` `retrieval/evidence.py:194-196` nhưng cấu trúc
  `X … trong Y` không khớp) → `route_hybrid` → clarification sai.

**Hướng vá**: mở rộng `_FIELD_OF_ENTITY` cho `trong`, và khi question mang đúng
tên dataset có trong catalog (`fact_inventory_movement`) — dù intent khác —
ưu tiên `try_explicit_entity_lookup` hoặc resolve chính xác trước hybrid.

---

### RC-7. context_only không enforce

- `has_context_only_constraint` `retrieval/evidence.py:317-325` dùng
  `_CONSTRAINT_PHRASES` (L92-107) — chỉ có `chỉ dựa trên …|chỉ dùng|chỉ sử dụng|only …`.
  D05 (`Không tìm kiếm thêm. warehouse_id nằm ở bảng nào?`) **không** match
  → `res.context_only=False` → rơi vào hybrid.
- Trong `resolve_context` `retrieval/context_resolver.py:211` context_only được
  đọc nhưng constraint `không tìm kiếm thêm|không search thêm` chưa có trong
  regex detect.

**Hướng vá**: thêm pattern `không tìm kiếm thêm / không search thêm` vào
context-only detector; đảm bảo evidence gate bắt khi có context_only + câu có
entity/field tham chiếu.

---

### RC-8. Evidence-quality trả metadata thô

- G02/G03/G04/G10: các intent (LINEAGE, TERM_TO_DATASETS, GENERAL) trả
  schema/lineage/danh sách thô vì `answer_from_evidence`
  (`app/services/chat/evidence.py`) không có nhánh "đánh giá evidence" —
  classification Direct/Indirect/UNKNOWN.
- G10: `quantity kiểu gì?` → `route_general_conversational`
  (`chat_service.py:616-632`) → LLM trả chung chung (integer/decimal) **bỏ qua**
  schema thật (decimal). Vì câu không match `_PROPERTY_PATTERNS`
  (`kiểu gì` thiếu) nên field-op không chạy.

**Hướng vá**: (1) bổ sung `kiểu gì`/cụm type vào RC-1 (về trước thứ tự ưu tiên);
(2) chặn `route_general_conversational` khi có evidence schema chứa field này
(không trả general answer khi field đã có metadata); (3) thêm nhánh
evidence-quality trong `answer_from_evidence` để trả Direct/Indirect/UNKNOWN.

---

## 5. Thứ tự ưu tiên vá (đề xuất từ report)

1. RC-4 + RC-5 (Critical): decompose + Thinking trigger — cứu Group F+H.
2. RC-1 (Critical): field-op parser — cứu A/B/C/D/E/G/M hàng loạt.
3. RC-3 (Critical): anaphora trong chuỗi dài + entity-switch — C06/E03/M05.
4. RC-6 (High): exact-name fast path — D09/G07/G09.
5. RC-7 (High): enforce context_only — D05.
6. RC-8 (High): un-grounded generation — G10/M05/T5.
7. RC-2 (Medium→High): focus field + chống over-answer.
8. RC-8 (tiếp): join/evidence-quality — D03, G02-G04.

---

## 6. Cách chạy lại / verify sau khi vá

Môi trường: backend local `localhost:8000`, PostgreSQL + Redis + OpenSearch +
LLM thật, auth admin (`/tmp/dhab_token`). Rate limit 60 req/60s → driver tự
pace 1.4s/call.

```bash
# 1) Compile + unit/retrieval tests trước
cd datahub-ai-chatbot
python -m py_compile app/services/chat_service.py retrieval/evidence.py
python -m pytest tests/unit tests/retrieval -q --timeout=120

# 2) Chạy lại semantic suite đầy đủ (77 case cũ + 8 case mới = 85)
python /tmp/opencode/semantic_driver.py                 # chạy cả 85
python /tmp/opencode/semantic_driver.py B09,C07,D10     # chạy subset, merge

# 3) Regenerate report
python /tmp/opencode/gen_report.py
# → /tmp/semantic_context_precision_report.md
# → copy vào docs/ nếu muốn:
cp /tmp/semantic_context_precision_report.md docs/semantic_context_precision_report.md
```

Duyệt nhanh từng RC bằng bộ case nhỏ:

```bash
python /tmp/opencode/semantic_driver.py A03,D05,D09,G10,H01,M05
python /tmp/opencode/gen_report.py
```

Nếu một case chuyển PASS→FAIL hoặc ngược lại, đọc events trong
`/tmp/datahub_backend.log` theo `trace_id` của case đó trước khi kết luận
(tránh trường hợp nondeterministic như C02 — chạy lại 2-3 lần).

---

## 7. Lưu ý kỹ thuật khi sửa

- **Không hardcode dataset/field/expected answer**. `field_ops.py` chỉ đọc
  `schema_fields` thật; giữ nguyên nguyên tắc này.
- **Nguyên tắc gating**: evidence > field-property > thinking > structured >
  hybrid. Một câu follow-up có context chỉ/evidence KHÔNG được tự ý `route_hybrid`.
- **Ambiguity guardrail #9**: `chat_service.py:1076-1100` — khi 2 entity cùng
  score (gap < 0.15, score > 0.5) sẽ clarification. Trước khi "sửa" một case về
  clarification sai, kiểm tra reranker trả đúng entity chưa.
- **Observability**: sau khi thêm gate xử lý mới, ghi `log.info("<event>",
  trace_id=...)` theo đúng convention để driver còn đọc được.
- Test suite HTTP (85 case) chạy `scripts/run_chat_test_suite.py` hoặc
  `tests/e2e/test_chat_e2e.py`; semantic suite nằm ở `/tmp/opencode/`.

---

## 8. Trạng thái dữ liệu môi trường (khi chạy suite)

- Catalog thật: ~500 entities (228 datasets, 91 dashboards, 181 glossary terms,
  9 domains) từ DataHub GMS.
- `fact_inventory_movement` xuất hiện 2 URN (fact_inventory + fact_inventory_forecast
  liên quan) → nguy cơ ambiguity clarification cao; `dim_warehouse` có 1 upstream
  (dim_plant) + 8 downstream (gồm fact_inventory_movement, fact_goods_receipt).
- Evidence E1..En snapshot theo từng turn; driver merge kết quả cũ + mới vào
  `/tmp/semantic_results.json` (85 case, không ghi đè).