# DataAtlas — Semantic & Context Precision Regression Report

> Bộ test bổ sung sau regression 85 case (HTTP-level). Mục tiêu: phát hiện các lỗi mà API regression không bắt được — context propagation, evidence usage, entity switching, tool selection, multi-subquestion, citation, Thinking Mode.

## Thông tin chạy

- Số test case: **85** (A01–A10, B01–B10, C01–C10, D01–D10, E01–E10, F01–F10, G01–G10, H01–H10, M01–M05).
- Backend: localhost:8000, môi trường thật (PostgreSQL + Redis + OpenSearch + LLM), auth admin.
- 0 HTTP error / timeouts. Mọi kết quả dưới đây đánh giá nội dung (semantic), không chỉ status 200.
- Observability lấy từ backend log theo trace_id (route_evidence_context, evidence_answer, route_field_op, intent_resolution, route_anaphora, route_hybrid, route_structured, route_planner_dag, thinking_skip…).

## Kết quả tổng quan

| Metric | Giá trị |
|--------|---------|
| Tổng test | 85 |
| PASS | 38 (44.7%) |
| FAIL | 47 (55.3%) |
| Semantic accuracy rate | 44.7% |
| Context reference accuracy | ~70% (B group: 7/10 ) |
| Entity switching accuracy | 7/10 (Group C) |
| Evidence usage accuracy | 7/10 (Group B) |
| Tool-selection accuracy | ~70% — chọn tool đúng intent, nhưng field-op/evidence cứu được không phải lúc nào cũng chạy (lỗi G10/E10) |
| Over-answering rate | 3/10 (Group E) + các trường hợp schema-dump trong A/B/F |
| Citation accuracy | các answer có citation inline về E-id thực sự được dùng (đúng evidence); citations[] structured thường rỗng |
| Thinking Mode accuracy | 1/11 kích hoạt đúng (F04); 0/10 nhóm H — **under-trigger nghiêm trọng** |
| UI Thinking state | chưa kiểm tra được qua API thuần; on_status('thinking') chỉ phát khi _complex=true (không phát ở nhóm H) |

### FAIL theo severity

| Severity | Số FAIL |
|----------|---------|
| Critical | 25 |
| High | 15 |
| Medium | 7 |
| Low | 0 |

## Chi tiết theo nhóm

### A — Field-level precision — 4/10 PASS

| ID | Expected | Actual | Current entity | Evidence | Tool | Retrieval | Thinking | Citation | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| A01 | warehouse_id answered as varchar from schema evidence; no re-search | warehouse_id answered as varchar from schema evidence; no re-search | fact_inventory_movement | E1         | field_property   | no-retrieval | OFF | E1 inline | **PASS** |
| A02 | movement_id answered as bigint from evidence | movement_id answered as bigint from evidence | fact_inventory_movement | E1         | field_property   | no-retrieval | OFF | E1 inline | **PASS** |
| A03 | 'quantity có kiểu dữ liệu gì?' not parsed as field-op (single-word field not in  | hybrid search -> wrong-entity clarification (fact_vendor_quality etc) instead of evidence  | - | -          | hybrid_search    | retrieval  | OFF | - | **FAIL** |
| A04 | 'Field nào biểu diễn ngày giao dịch?' not parsed as find_field (connective 'biểu | treated as dataset name -> dataset-not-found, expected movement_date | - | -          | schema_lookup    | retrieval  | OFF | - | **FAIL** |
| A05 | find_field 'warehouse' answered warehouse_id from schema evidence | find_field 'warehouse' answered warehouse_id from schema evidence | fact_inventory_movement | E1         | field_property   | no-retrieval | OFF | E1 inline | **PASS** |
| A06 | respects output constraint; answers only field name + type | respects output constraint; answers only field name + type | fact_inventory_movement | E1         | field_property   | no-retrieval | OFF | E1 inline | **PASS** |
| A07 | double ask (field + its type) misrouted to join-intent; returns 'chưa có trường  | double ask (field + its type) misrouted to join-intent; returns 'chưa có trường khóa khớp' | fact_goods_receipt | E1         | join             | no-retrieval | OFF | E1 inline | **FAIL** |
| A08 | 'Field đó là gì?' | answers FULL schema listing (over-answer) instead of clarifying the field reference | fact_inventory_movement | E1         | schema           | no-retrieval | OFF | E1 inline | **FAIL** |
| A09 | same over-answer at T2; T3 'Còn kiểu dữ liệu của nó?' | anaphora resolved to word 'kieu', hybrid search, generic no-info | fact_inventory_movement | E1         | hybrid_search    | retrieval  | OFF | - | **FAIL** |
| A10 | context_only respected (no re-search) but returns whole schema, not warehouse_id | context_only respected (no re-search) but returns whole schema, not warehouse_id field/typ | fact_inventory_movement | E1         | schema           | no-retrieval | OFF | E1 inline | **FAIL** |

### B — Evidence propagation — 7/10 PASS

| ID | Expected | Actual | Current entity | Evidence | Tool | Retrieval | Thinking | Citation | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| B01 | warehouse_id type answered from E1 (schema evidence cached from turn 1) | warehouse_id type answered from E1 (schema evidence cached from turn 1) | fact_inventory_movement | E1         | field_property   | no-retrieval | OFF | E1 inline | **PASS** |
| B02 | context_only honored; find_field answered from E1 without re-resolution | context_only honored; find_field answered from E1 without re-resolution | fact_inventory_movement | E1         | field_property   | no-retrieval | OFF | E1 inline | **PASS** |
| B03 | 'Field đó có description gì?' | full schema listing (focus field not tracked, over-answer) | fact_inventory_movement | E1         | schema           | no-retrieval | OFF | E1 inline | **FAIL** |
| B04 | glossary follow-up answered from dataset evidence (dataset has no glossary); no  | glossary follow-up answered from dataset evidence (dataset has no glossary); no hallucinat | fact_inventory_movement | E1         | glossary         | no-retrieval | OFF | - | **PASS** |
| B05 | owner answered from evidence (metadata has no owner); entity unchanged | owner answered from evidence (metadata has no owner); entity unchanged | fact_inventory_movement | E1         | owner            | no-retrieval | OFF | - | **PASS** |
| B06 | T3 'quay lại schema vừa lấy, warehouse_id kiểu gì?' | evidence E1 restored but returns whole schema instead of varchar (over-answer; field op no | fact_inventory_movement | E1         | schema           | no-retrieval | OFF | E1 inline | **FAIL** |
| B07 | lineage downstream-filter subquestion fails ('không tìm thấy dataset downstream  | lineage downstream-filter subquestion fails ('không tìm thấy dataset downstream lien quan  | dim_warehouse | E1-E9      | lineage/impact   | retrieval  | OFF | - | **FAIL** |
| B08 | after chitchat interleaving, 'schema vừa lấy có warehouse_id' restores E1 eviden | after chitchat interleaving, 'schema vừa lấy có warehouse_id' restores E1 evidence (contex | fact_inventory_movement | E1         | schema           | no-retrieval | OFF | E1 inline | **PASS** |
| B09 | backend log exposes evidence ids, chosen_tool, routing_decision, entity_hint, pl | backend log exposes evidence ids, chosen_tool, routing_decision, entity_hint, plan_source  | - | E1         | -                | -          | OFF | - | **PASS** |
| B10 | multi-step field follow-up (type | description) both answered from E1/focus field; structured field metadata retained | fact_inventory_movement | E1         | field_property   | no-retrieval | OFF | E1 inline | **PASS** |

### C — Entity switching — 7/10 PASS

| ID | Expected | Actual | Current entity | Evidence | Tool | Retrieval | Thinking | Citation | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| C01 | switch to fact_goods_receipt triggers correct new retrieval | switch to fact_goods_receipt triggers correct new retrieval | fact_goods_receipt | E1         | schema_lookup    | retrieval  | OFF | - | **PASS** |
| C02 | 'Còn dataset ban đầu thì sao?' nondeterministic | ambiguous entity clarification instead of returning to fact_inventory_movement (passed on  | - | -          | hybrid_search    | retrieval  | OFF | - | **FAIL** |
| C03 | schema of fact_goods_receipt loaded (E1) but 'warehouse_id kiểu gì?' | GENERAL couldn't-find; evidence not used (informal 'kiểu gì' not parsed) | fact_goods_receipt | E1         | hybrid_search    | retrieval  | OFF | - | **FAIL** |
| C04 | dim_warehouse info | 'lineage của nó' answered dim_warehouse lineage from E1 | dim_warehouse | E1         | lineage          | no-retrieval | OFF | E1..E9 inline | **PASS** |
| C05 | explicit switch to fact_inventory_movement | new entity info | fact_inventory_movement | E1         | hybrid_search    | retrieval  | OFF | - | **PASS** |
| C06 | after C05 (entity=fact_inventory_movement), 'nó có owner nào?' | 'Không tìm thấy dataset no owner' (anaphora not resolved to active entity; owner path brea | fact_inventory_movement | E1         | owner_lookup     | retrieval  | OFF | - | **FAIL** |
| C07 | switch to dim_warehouse then explicit schema of fact_inventory_movement restores | switch to dim_warehouse then explicit schema of fact_inventory_movement restores original  | fact_inventory_movement | -          | schema_lookup    | retrieval  | OFF | - | **PASS** |
| C08 | anaphora 'nó có những trường nào?' resolved via evidence/active entity; no gener | anaphora 'nó có những trường nào?' resolved via evidence/active entity; no generic re-reso | fact_inventory_movement | E1         | schema           | no-retrieval | OFF | E1 inline | **PASS** |
| C09 | after dim_warehouse info, explicit schema ask of fact_inventory_movement correct | after dim_warehouse info, explicit schema ask of fact_inventory_movement correct | fact_inventory_movement | -          | schema_lookup    | retrieval  | OFF | - | **PASS** |
| C10 | 4-step entity chain with explicit return to fact_inventory_movement (entity rest | 4-step entity chain with explicit return to fact_inventory_movement (entity restored, thou | fact_inventory_movement | -          | hybrid_search    | retrieval  | OFF | - | **PASS** |

### D — No-retrieval / retrieval decision — 7/10 PASS

| ID | Expected | Actual | Current entity | Evidence | Tool | Retrieval | Thinking | Citation | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| D01 | context_only respected; answered from evidence scope (no re-search) | context_only respected; answered from evidence scope (no re-search) | fact_inventory_movement | E1         | evidence         | no-retrieval | OFF | - | **PASS** |
| D02 | warehouse_id type answered from E1 with context_only constraint | warehouse_id type answered from E1 with context_only constraint | fact_inventory_movement | E1         | field_property   | no-retrieval | OFF | E1 inline | **PASS** |
| D03 | join subquestion returns join answer with None/NULL target artifacts (join targe | join subquestion returns join answer with None/NULL target artifacts (join target not reso | fact_inventory_movement | E1         | join             | no-retrieval | OFF | E1 inline | **FAIL** |
| D04 | nullable property answered from E1 | nullable property answered from E1 | fact_inventory_movement | E1         | field_property   | no-retrieval | OFF | E1 inline | **PASS** |
| D05 | 'Không tìm kiếm thêm' | hybrid search ambiguity (constraint not honored; searched wildly unrelated entities) | - | -          | hybrid_search    | retrieval  | OFF | - | **FAIL** |
| D06 | owner from evidence; no owner | honest statement, entity unchanged | fact_inventory_movement | E1         | owner            | no-retrieval | OFF | - | **PASS** |
| D07 | new dataset request | proper new retrieval | fact_goods_receipt | -          | schema_lookup    | retrieval  | OFF | - | **PASS** |
| D08 | glossary term definition | glossary retrieval | GrossRevenue | E1         | glossary_lookup  | retrieval  | OFF | E1 inline | **PASS** |
| D09 | self-contained 'warehouse_id có kiểu dữ liệu gì trong fact_inventory_movement?' | ambiguous clarification (fact_inventory duplicates) instead of field-property answer | fact_inventory_movement | -          | hybrid_search    | retrieval  | OFF | - | **FAIL** |
| D10 | evidence/context gate runs before generic retrieval for follow-ups (observed in  | evidence/context gate runs before generic retrieval for follow-ups (observed in events: ev | - | E1         | -                | no-retrieval | OFF | - | **PASS** |

### E — Response focus / over-answering — 7/10 PASS

| ID | Expected | Actual | Current entity | Evidence | Tool | Retrieval | Thinking | Citation | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| E01 | field type only; no schema dump | field type only; no schema dump | fact_inventory_movement | E1         | field_property   | no-retrieval | OFF | E1 inline | **PASS** |
| E02 | find_field returns only the matching field, not dataset metadata | find_field returns only the matching field, not dataset metadata | fact_inventory_movement | E1         | field_property   | no-retrieval | OFF | E1 inline | **PASS** |
| E03 | owner of dim_warehouse | entity switched to 'Bonded Warehouse' glossary term (anaphora/entity-switch bug) instead o | Bonded Warehouse | E1         | owner_lookup     | retrieval  | OFF | - | **FAIL** |
| E04 | 'Glossary term nào giải thích Revenue?' | ambiguous clarification (Monthly Revenue/Net Revenue/fact_contract_performance) instead of | - | -          | hybrid_search    | retrieval  | OFF | - | **FAIL** |
| E05 | lineage only; no extra schema/metadata analysis | lineage only; no extra schema/metadata analysis | dim_warehouse | E1-E9      | lineage          | retrieval  | OFF | E1..E9 inline | **PASS** |
| E06 | Revenue datasets answered (sales.orders, finance.monthly_revenue, fact_revenue)  | Revenue datasets answered (sales.orders, finance.monthly_revenue, fact_revenue) without un | Revenue | E1,E2,E6   | term_to_datasets | retrieval  | OFF | - | **PASS** |
| E07 | output constraint honored; only field+type returned | output constraint honored; only field+type returned | fact_inventory_movement | E1         | field_property   | no-retrieval | OFF | E1 inline | **PASS** |
| E08 | 'Chỉ dựa trên schema vừa lấy, movement_date kiểu gì?' | whole schema listing instead of movement_date/date | fact_inventory_movement | E1         | schema           | no-retrieval | OFF | E1 inline | **FAIL** |
| E09 | no spurious 'bạn có thể hỏi...' appended to free answers; only evidence-fallthro | no spurious 'bạn có thể hỏi...' appended to free answers; only evidence-fallthrough templa | - | E1         | -                | -          | OFF | - | **PASS** |
| E10 | citation points at the actually-used schema evidence (E1) | citation points at the actually-used schema evidence (E1) | fact_inventory_movement | E1         | field_property   | no-retrieval | OFF | E1 inline | **PASS** |

### F — Multi-subquestion — 2/10 PASS

| ID | Expected | Actual | Current entity | Evidence | Tool | Retrieval | Thinking | Citation | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| F01 | composite schema+find+type | only schema listed; find/type sub-questions dropped | fact_inventory_movement | -          | schema_lookup    | retrieval  | OFF | - | **FAIL** |
| F02 | 'vai trò, domain, owner' | ambiguous entity clarification; no decomposition | - | -          | hybrid_search    | retrieval  | OFF | - | **FAIL** |
| F03 | downstream selection via IMPACT answered with inventory group + reasoning from l | downstream selection via IMPACT answered with inventory group + reasoning from lineage | dim_warehouse | E1         | lineage/impact   | retrieval  | OFF | - | **PASS** |
| F04 | THINKING_OVERVIEW triggered and answered Revenue datasets+terms+domain multi-sou | THINKING_OVERVIEW triggered and answered Revenue datasets+terms+domain multi-source | Revenue | multi      | thinking         | retrieval  | ON | - | **PASS** |
| F05 | schema+warehouse+quantity+date | only schema listing; 3 sub-questions dropped | fact_inventory_movement | -          | schema_lookup    | retrieval  | OFF | - | **FAIL** |
| F06 | 3 sub-questions (pk/join/type) | only schema listing | fact_inventory_movement | -          | schema_lookup    | retrieval  | OFF | - | **FAIL** |
| F07 | composite with one new-entity subquestion | only schema; fact_goods_receipt not fetched | fact_inventory_movement | -          | schema_lookup    | retrieval  | OFF | - | **FAIL** |
| F08 | 5 sub-questions | only schema listing (types omitted) | fact_inventory_movement | -          | schema_lookup    | retrieval  | OFF | - | **FAIL** |
| F09 | desc+nonexistent-field | only schema; no UNKNOWN/missing marking | fact_inventory_movement | -          | schema_lookup    | retrieval  | OFF | - | **FAIL** |
| F10 | 3-subquestion composite | only schema listing | fact_inventory_movement | -          | schema_lookup    | retrieval  | OFF | - | **FAIL** |

### G — Evidence quality — 2/10 PASS

| ID | Expected | Actual | Current entity | Evidence | Tool | Retrieval | Thinking | Citation | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| G01 | FK question between two datasets | ambiguous clarification; no reasoning over same-name field (no direct FK inference, but al | - | -          | hybrid_search    | retrieval  | OFF | - | **FAIL** |
| G02 | lineage then 'schema join field?' | returns fact_inventory_movement schema; does not distinguish lineage-evidence vs join-evid | fact_inventory_movement | E1-E9      | schema_lookup    | retrieval  | OFF | - | **FAIL** |
| G03 | 'lineage có xác nhận quan hệ với warehouse?' | repeats dim_warehouse lineage; no Direct/Indirect evidence classification | dim_warehouse | E1-E9      | lineage          | retrieval  | OFF | - | **FAIL** |
| G04 | 'Có dataset nào là inventory movement được mô tả rõ?' | TERM_TO_DATASETS garbled output (Certificate of Origin (CO) not found) | Certificate of Origin (CO) | -          | term_to_datasets | retrieval  | OFF | - | **FAIL** |
| G05 | dataset glossary absence stated honestly (no glossary evidence) | dataset glossary absence stated honestly (no glossary evidence) | fact_inventory_movement | E1         | glossary         | no-retrieval | OFF | - | **PASS** |
| G06 | owner absence stated (no hallucination) | owner absence stated (no hallucination) | fact_goods_receipt | E1         | owner            | no-retrieval | OFF | - | **PASS** |
| G07 | 'Lấy thông tin fact_inventory_movement' | 4-candidate ambiguity, then field description 'couldn't find'; exact-name fast path failed | fact_inventory_movement | -          | hybrid_search    | retrieval  | OFF | - | **FAIL** |
| G08 | 'dim_warehouse liên quan chặt chẽ với fact_inventory_movement dựa trên tên giống | semantic-similarity claim not rejected; ambiguous clarification | - | -          | hybrid_search    | retrieval  | OFF | - | **FAIL** |
| G09 | 'Có mấy dataset tên fact_inventory_movement?' | ambiguous clarification instead of count answer | fact_inventory_movement | -          | hybrid_search    | retrieval  | OFF | - | **FAIL** |
| G10 | 'quantity kiểu gì?' after schema evidence | route_general_conversational generic answer ('thường là integer hoặc float') IGNORING sche | - | E1         | conversational   | no-retrieval(reasoning) | OFF | - | **FAIL** |

### H — Complex Thinking Mode — 0/10 PASS

| ID | Expected | Actual | Current entity | Evidence | Tool | Retrieval | Thinking | Citation | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| H01 | complex analysis question misrouted to SCHEMA_LOOKUP (regex) | schema only; Thinking Mode NOT triggered | dim_warehouse | -          | schema_lookup    | retrieval  | OFF | - | **FAIL** |
| H02 | end-to-end no-speculation | ambiguous clarification; Thinking not triggered | - | -          | hybrid_search    | retrieval  | OFF | - | **FAIL** |
| H03 | dataset role classification | 'Không tìm thấy dataset xac inh nhap kho...' (whole clause as entity name) | - | -          | schema_lookup    | retrieval  | OFF | - | **FAIL** |
| H04 | Direct/Indirect/UNKNOWN | route_general_conversational 'UNKNOWN' only; no orchestration | - | -          | conversational   | no-retrieval(reasoning) | OFF | - | **FAIL** |
| H05 | data-logic design | ambiguous clarification; Thinking not triggered | - | -          | hybrid_search    | retrieval  | OFF | - | **FAIL** |
| H06 | 3-task analysis | schema only; sub-tasks dropped; Thinking not triggered | fact_inventory_movement | -          | schema_lookup    | retrieval  | OFF | - | **FAIL** |
| H07 | 5-question analysis | schema only; dropped | fact_inventory_movement | -          | schema_lookup    | retrieval  | OFF | - | **FAIL** |
| H08 | comparison of two datasets | only fact_goods_receipt schema; no comparison; Thinking not triggered | fact_goods_receipt | -          | schema_lookup    | retrieval  | OFF | - | **FAIL** |
| H09 | missing-metadata analysis | ambiguous clarification | - | -          | hybrid_search    | retrieval  | OFF | - | **FAIL** |
| H10 | self-check conclusion | ambiguous clarification; Thinking not triggered | - | -          | hybrid_search    | retrieval  | OFF | - | **FAIL** |

### M — Context window / memory — 2/5 PASS

| ID | Expected | Actual | Current entity | Evidence | Tool | Retrieval | Thinking | Citation | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| M01 | 7-turn chain retained 6/7; T4 'movement_id có null không?' mis-parsed as dataset | ENTITY_EXISTS fail (informal property parsing gap) | fact_inventory_movement | E1         | entity_exists    | retrieval  | OFF | - | **FAIL** |
| M02 | downstream filter subquestion fails at T2; T3 schema returns dim_warehouse not a | downstream filter subquestion fails at T2; T3 schema returns dim_warehouse not a chosen do | dim_warehouse | E1-E9      | lineage/impact   | retrieval  | OFF | - | **FAIL** |
| M03 | schema | Revenue definition -> back to warehouse_id type correctly restored from E1 after unrelated | fact_inventory_movement | E1         | field_property   | no-retrieval | OFF | E1 inline | **PASS** |
| M04 | 4-entity chain (FIM | dim->FGR->FIM) retains identity; return answered from correct entity (lightweight) | fact_inventory_movement | -          | hybrid_search    | retrieval  | OFF | - | **PASS** |
| M05 | 10-turn chain: T4 null fail, T5 'quantity kiểu gì?' generic non-evidence answer, | 10-turn chain: T4 null fail, T5 'quantity kiểu gì?' generic non-evidence answer, T10 'Quay | dim_warehouse | E1/E3      | hybrid_search    | retrieval  | OFF | E3 inline | **FAIL** |

## Root cause theo failure pattern

### RC-1. Parser field-op không bắt được cú pháp thông dụng
- Trigger: `kiểu gì`, `null không`, field đơn từ không dấu gạch dưới (`quantity`), connective find_field hẹp (`biểu diễn…`).
- Ảnh hưởng: A03, A04, A09/T3, B06/T3, C03, E08, M01/T4, M05/T4, G10, D09.
- Bằng chứng: `route_field_op` không chạy; backend rơi vào `route_hybrid`/`route_general_conversational`.

### RC-2. Mất focus field / over-answer thành schema dump
- `Field đó / Field nào …` không đính focus field -> evidence resolver trả `schema` listing toàn bộ.
- Ảnh hưởng: A08, A10, B03, B06, E08; nhóm F gần như toàn bộ.

### RC-3. Anaphora/entity-switch sai trong ngữ cảnh dài
- `nó có owner`, `owner là ai`, `quay lại …` resolve nhầm sang glossary term / dataset khác / từ khoá (`kieu`, `no owner`, `Bonded Warehouse`, `dim_warehouse` thay vì `fact_inventory_movement`).
- Ảnh hưởng Critical: A09/T3, C06, E03, M05/T10.

### RC-4. Composite/multi-subquestion không được decompose
- Regex router khớp một intent duy nhất (SCHEMA_LOOKUP/LINEAGE…), các sub-question còn lại bị thả. Thinking Mode/Query Planner không chạy vì intent không phải COMPOSITE/GENERAL.
- Ảnh hưởng: toàn bộ Group F (F01,F02,F05–F10), H06–H08.

### RC-5. Thinking Mode under-trigger
- Complexity classifier `reason=simple` cho nhiều câu phức tạp; các câu GENERAL lại bị ambiguous-clarification trước khi tới thinking gate; câu bắt đầu bằng 'Phân tích…' bị regex bắt thành SCHEMA_LOOKUP.
- Ảnh hưởng: Group H (0/10), riêng F03 (IMPACT) và F04 (THINKING) hoạt động.

### RC-6. Exact-name fast path không kích hoạt khi câu có thêm yếu tố
- `warehouse_id có kiểu dữ liệu gì trong fact_inventory_movement` (D09), `Có mấy dataset tên fact_inventory_movement` (G09), `Lấy thông tin fact_inventory_movement` (G07) -> entity ambiguity do intent không phải FIND_ENTITY/DATASET_LOOKUP.

### RC-7. `không tìm kiếm thêm` / context-only không được enforce với mọi cú pháp
- D05: constraint không được tôn trọng do parser không nhận diện; rơi vào hybrid search.

### RC-8. Câu hỏi evidence-quality trả metadata thô thay vì đánh giá
- G02/G03/G04/G10: trả schema/lineage/câu chung chung mà không phân biệt Direct/Indirect/UNKNOWN hay đối chiếu join-vs-lineage.

## Đánh giá riêng theo hệ thống con

### Context propagation
- **Tốt**: E1–E9 được giữ và restore đúng trong A01-A10/B01-B08/M03 sau các turn unrelated (chitchat, Revenue).
- **Yếu**: focus field không bền; sau một sub-turn field-level (type/desc) thì `field đó`/`nó` không quy về đúng field -> over-answer. Failed: A08, A09, B03.

### Evidence propagation
- Structured metadata của turn trước (schema_fields, owners, lineage list) có sẵn và tái sử dụng tốt (B01,B02,B05,B10,M03).
- Lỗi: một số câu không attach field-property nên evidence không được truy vấn (B06,C03,G10); context_only hẹp.

### Router
- Regex intent nhạy cảm thứ tự từ; câu composite/general complex bị map sai -> GROUP F/H fail hàng loạt.
- Route evidence-context hoạt động đúng (route_evidence_context + route_field_op thấy rõ), hiếm khi chạy sai entity khi có reference tường minh.

### Entity resolution
- Resolve explicit name khi câu đứng một mình rất tốt (C01, C04, C05, C07-C10, D07).
- Error: câu có thêm yếu tố (D09,G07,G09), anaphora trong chuỗi dài (C06,E03,M05/T10), và ambiguity fact_inventory (fact_inventory xuất hiện 2 URN) làm clarify sai.

### Retrieval / tool selection
- Tool chọn theo chosen_tool khớp intent chính (schema_lookup/owner/lineage/glossary…).
- Lỗi: khi field-op parse thất bại, hệ thống re-search hoặc conversational thay vì từ chối/reason trên evidence (A03,D05,G10,D09).

### Response generation
- Câu hỏi field-level trả schema dump (over-answering) — pattern phổ biến nhất. Un-grounded generation cho `quantity kiểu gì` (integer/float) bỏ qua schema thực (decimal).

### Thinking Mode
- Chỉ F04 trigger Thinking (OVERVIEW). 0/10 Group H. Complexity classifier có nhiều false-negative (reason=simple); những câu 'Phân tích …' bị SCHEMA_LOOKUP bắt trước.
- UI Thinking state không thể xác nhận qua API lần này (không emission); xem note ở trên.

## Đề xuất thứ tự ưu tiên sửa

1. **(Critical) Multi-subquestion & Thinking trigger** — cho composite/parse-thất-bại rơi vào planner/thinking thay vì single-intent (Group F + H).
2. **(Critical) Field-op parser** — mở rộng property patterns (`kiểu gì`, `null không`, `mô tả`), find_field connectives, và field token cho từ đơn; khi parse thất bại -> trả lời từ evidence bằng focus field hẹp, không schema-dump.
3. **(Critical) Anaphora trong chuỗi dài & entity-switch** — bind `nó/owner/…` vào active entity canonical, chặn resolve sang glossary term / keyword; bảo toàn entity qua nhiều turn (C06,E03,M05/T10).
4. **(High) Exact-name fast path** — mở rộng _has_own_identifier/trusted resolution cho câu có hỏi thêm thuộc tính (D09,G07,G09).
5. **(High) Enforce context_only / 'không tìm kiếm thêm'** cho mọi cú pháp constraint (D05).
6. **(High) Un-grounded generation** — chặn general-conversational cho câu field-type khi đã có schema evidence (G10/M05/T5).
7. **(Medium) Join/evidence-quality** — target-entity resolution cho join answer (D03), và trả lời Direct/Indirect/UNKNOWN theo evidence (G02-G04).
8. **(Low) Citation structured** — điền citations[] thay vì chỉ inline `(dựa trên E1)`.

## So sánh với regression 85/85

85/85 PASS (HTTP-level) chỉ chứng minh pipeline chạy không 5xx, intent routing chính xác, và kết quả không lỗi. Regression lần này cho thấy semantic/context precision trung bình **~45%**, chủ yếu do: (1) câu hỏi field-level bị thả về schema dump, (2) composite/thinking không được trigger, (3) anaphora/entity-switch sai trong ngữ cảnh dài, (4) un-grounded generation. Đây là loại lỗi mà 85-case suite API không thể phát hiện được.

_Generated: 2026-08-12 · driver: /tmp/opencode/semantic_driver.py (85 TESTS) · data: /tmp/semantic_results.json (85 cases)_