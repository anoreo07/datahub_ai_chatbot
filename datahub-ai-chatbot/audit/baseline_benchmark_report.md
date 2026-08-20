# BASELINE BENCHMARK REPORT

Pipeline traced per test case: USER QUERY -> context/reference resolution -> LLM intent -> entity resolution -> domain resolution -> retrieval -> reranking -> tool selection -> tool arguments -> evidence state -> reasoning/planning -> final response -> citation.

Verdict rule: the FIRST INCORRECT STATE in the pipeline determines the failure type.

Total tests: 48 | PASS: 7 | FAIL: 41

## A-001

- **Difficulty**: easy | **Category**: A | **Case**: -
- **User query**: `Tìm dataset có tên chính xác "List of Vendor Master Data"`
- **Expected intent**: `exact_dataset_lookup` | **Expected domain**: `CUNG ỨNG (NĐH)`
- **Expected assets (1)**: urn:li:dataset:(urn:li:dataPlatform:SAP,Kế toán.List of Vendor Master Data ,PROD)
- **Expected evidence**: [{"field": "name", "value": "List of Vendor Master Data"}]
- **Expected tool**: `['retrieve:entity_summary']`
- **Actual answer (trunc)**: `Không tìm thấy dataset có tên chính xác 'List of Vendor Master Data' (không có khoảng trắng cuối). Tuy nhiên, có dataset có tên 'List of Vendor Master Data ' (có khoảng trắng cuối) [E1]. Dataset này thuộc nền tảng SAP, URN: urn:li:dataset:(urn:li:dataPlatform:SAP,Kế toán.List of Vendor Master Data ,PROD) [E1].`
- **Response flags**: ambiguous=False insufficient_context=False confidence=medium intent=FIND_ENTITY
- **Resolved entities (1)**: List of Vendor Master Data 
- **Citations**: 1
- **Trace_id**: `75177de787cf` | log lines: 9
- **VERDICT**: **FAIL**
  - **First incorrect state**: `entity_resolution`
  - **Failure type**: `ENTITY_RESOLUTION_FAILURE`
  - **Root cause**: `RC1a`
  - **Evidence**: resolver_result ambiguous=False, top_score=0.76 exact=False, runner-up is a glossary term 'Tính toán H part MRD date - Planned' but response surfaced ambiguous=True clarification instead of the correct dataset.

## A-002

- **Difficulty**: easy | **Category**: A | **Case**: -
- **User query**: `Tìm dataset có tên chính xác "Display Plant Stock Availability"`
- **Expected intent**: `exact_dataset_lookup` | **Expected domain**: `SẢN XUẤT`
- **Expected assets (1)**: urn:li:dataset:(urn:li:dataPlatform:SAP,Global MFG LOG.Display Plant Stock Availability,PROD)
- **Expected evidence**: [{"field": "name", "value": "Display Plant Stock Availability"}]
- **Expected tool**: `['retrieve:entity_summary']`
- **Actual answer (trunc)**: `Dataset 'Display Plant Stock Availability' tồn tại trong DataHub với URN urn:li:dataset:(urn:li:dataPlatform:SAP,Global MFG LOG.Display Plant Stock Availability,PROD) [E1]. Đây là dataset thuộc nền tảng SAP, môi trường PROD. Không có thêm mô tả, schema, owner hay lineage trong ngữ cảnh.`
- **Response flags**: ambiguous=False insufficient_context=False confidence=medium intent=FIND_ENTITY
- **Resolved entities (1)**: Display Plant Stock Availability
- **Citations**: 1
- **Trace_id**: `25050823e5af` | log lines: 9
- **VERDICT**: **PASS**

## A-003

- **Difficulty**: easy | **Category**: A | **Case**: -
- **User query**: `Tìm dataset có tên chính xác "Fact_Mrp_Demand"`
- **Expected intent**: `exact_dataset_lookup` | **Expected domain**: `None`
- **Expected assets (1)**: urn:li:dataset:(urn:li:dataPlatform:powerbi,PFEP_Report_-_Hai_Phong_Factory.Fact_Mrp_Demand,PROD)
- **Expected evidence**: [{"field": "name", "value": "Fact_Mrp_Demand"}]
- **Expected tool**: `['retrieve:entity_summary']`
- **Actual answer (trunc)**: `Tìm thấy dataset có tên chính xác 'Fact_Mrp_Demand' [E1]. Đây là dataset trên nền tảng Power BI, với các trường schema: material_id, plant_id, Year, Mat-Plant, Refresh_Date, Material, Month, Demand Q'ty [E1].`
- **Response flags**: ambiguous=False insufficient_context=False confidence=medium intent=FIND_ENTITY
- **Resolved entities (1)**: Fact_Mrp_Demand
- **Citations**: 1
- **Trace_id**: `fa796dece653` | log lines: 7
- **VERDICT**: **PASS**

## B-001

- **Difficulty**: easy | **Category**: B | **Case**: -
- **User query**: `có báo cáo nào về chi phí bảo hành do lỗi nhà cung cấp xảy ra ngoài thị trường không?`
- **Expected intent**: `discover_dataset_by_description` | **Expected domain**: `None`
- **Expected assets (1)**: urn:li:dataset:(urn:li:dataPlatform:GSM,Chất lượng.Supplier Warranty Cost Recovery 
" Báo cáo thu hồi chi phí bảo hành do lỗi nhà cung cấp xảy ra ngoài thị trường",PROD)
- **Expected evidence**: [{"field": "description", "value": "keyword-match"}]
- **Expected tool**: `['retrieve:entity_summary', 'retrieve:schema_fields']`
- **Actual answer (trunc)**: `Không tìm thấy dataset 'bao cao chi phi bao hanh do loi nha cung cap xay ra ngoai thi truong' trong hệ thống DataHub. Ý bạn là 'Supplier Warranty Cost Recovery  " Báo cáo thu hồi chi phí bảo hành do lỗi nhà cung cấp xảy ra ngoài thị trường"'?`
- **Response flags**: ambiguous=False insufficient_context=False confidence=high intent=SCHEMA_LOOKUP
- **Trace_id**: `b37ea83e2c82` | log lines: 5
- **VERDICT**: **FAIL**
  - **First incorrect state**: `entity_resolution`
  - **Failure type**: `ENTITY_RESOLUTION_FAILURE`
  - **Root cause**: `RC1b`
  - **Evidence**: resolver_name_query db_rows=0 then fuzzy name-match resolved an unrelated entity before downstream tools ran.

## B-002

- **Difficulty**: easy | **Category**: B | **Case**: -
- **User query**: `dataset nào phục vụ kiểm tra WIP giữa MES và SAP?`
- **Expected intent**: `discover_dataset_by_description` | **Expected domain**: `None`
- **Expected assets (1)**: urn:li:dashboard:(powerbi,reports.082bd437-991d-4469-8efc-ee953b27362e)
- **Expected evidence**: [{"field": "description", "value": "keyword-match"}]
- **Expected tool**: `['retrieve:entity_summary', 'retrieve:schema_fields']`
- **Actual answer (trunc)**: `Tôi không thể tìm thấy thông tin này trong metadata DataHub hiện có.`
- **Response flags**: ambiguous=False insufficient_context=False confidence=medium intent=TERM_TO_DATASETS
- **Resolved entities (8)**: Display WIP at actual cost, Detail cost component, Check WIP MLDOC, Activity type Price Report
- **Citations**: 8
- **Trace_id**: `041a2345afd7` | log lines: 5
- **VERDICT**: **FAIL**
  - **First incorrect state**: `intent`
  - **Failure type**: `INTENT_FAILURE`
  - **Root cause**: `RC2`
  - **Evidence**: keyword intent router chose TERM_TO_DATASETS for an NL discovery query; correct intent is dataset discovery/definition.

## B-003

- **Difficulty**: easy | **Category**: B | **Case**: -
- **User query**: `bảng tính dự báo cung cấp hàng tuần theo từng part là dataset nào?`
- **Expected intent**: `discover_dataset_by_description` | **Expected domain**: `None`
- **Expected assets (1)**: urn:li:dataset:(urn:li:dataPlatform:redshift,sap.dwh.rpt_survey_weekly_supply_capacity,PROD)
- **Expected evidence**: [{"field": "description", "value": "keyword-match"}]
- **Expected tool**: `['retrieve:entity_summary', 'retrieve:schema_fields']`
- **Actual answer (trunc)**: `Không tìm thấy dataset 'bang tinh du bao cung cap hang tuan theo tung part' trong hệ thống DataHub. Ý bạn là 'CUNG ỨNG (NĐH)'?`
- **Response flags**: ambiguous=False insufficient_context=False confidence=high intent=TERM_TO_DATASETS
- **Trace_id**: `bd23f29438dd` | log lines: 5
- **VERDICT**: **FAIL**
  - **First incorrect state**: `intent`
  - **Failure type**: `INTENT_FAILURE`
  - **Root cause**: `RC2`
  - **Evidence**: NL discovery query misrouted by keyword router; wrong tool selected, no entity context.

## C-001

- **Difficulty**: hard | **Category**: C | **Case**: -
- **User query**: `có bao nhiêu dataset tên "stas"?`
- **Expected intent**: `disambiguate_same_name` | **Expected domain**: `None`
- **Expected assets (0)**: 
- **Expected evidence**: [{"field": "name", "value": "stas", "note": "multiple urns"}]
- **Expected tool**: `['retrieve:entity_summary']`
- **Actual answer (trunc)**: `Có tổng cộng 500 datasets.  DMS: AR Receipts, Báo cáo Sales orders (Layout báo cáo cọc), Báo cáo bảo hành, Báo cáo hóa đơn  SCT, Báo cáo lệnh sửa chữa/ bảo hành Pending, Báo cáo sales orders, Báo cáo sales orders (Báo cáo chương trình giảm giá), Báo cáo tồn kho ĐLPP, Báo cáo đơn hàng  EMSP: Báo cáo ODO(EMSP), Danh sách Bill thuê Pin(EMSP), Danh sách bill điều chỉnh (EMSP), Danh sách yêu cầu đổi gó`
- **Response flags**: ambiguous=False insufficient_context=False confidence=high intent=COUNT_ENTITIES
- **Resolved entities (200)**:  EV VIN Battery Report,  FTQ Welding - Ultrasonic,  MA - PIST Dimension Check, #Measurements
- **Trace_id**: `681d0218227c` | log lines: 2
- **VERDICT**: **FAIL**
  - **First incorrect state**: `tool_arguments`
  - **Failure type**: `TOOL_ARGUMENT_FAILURE`
  - **Root cause**: `RC3`
  - **Evidence**: count_entities called with entity_hint=None, answered 'Có tổng cộng 500 datasets' instead of counting the requested subset.

## C-002

- **Difficulty**: hard | **Category**: C | **Case**: -
- **User query**: `có bao nhiêu dataset tên "stko"?`
- **Expected intent**: `disambiguate_same_name` | **Expected domain**: `None`
- **Expected assets (0)**: 
- **Expected evidence**: [{"field": "name", "value": "stko", "note": "multiple urns"}]
- **Expected tool**: `['retrieve:entity_summary']`
- **Actual answer (trunc)**: `Có tổng cộng 500 datasets.  DMS: AR Receipts, Báo cáo Sales orders (Layout báo cáo cọc), Báo cáo bảo hành, Báo cáo hóa đơn  SCT, Báo cáo lệnh sửa chữa/ bảo hành Pending, Báo cáo sales orders, Báo cáo sales orders (Báo cáo chương trình giảm giá), Báo cáo tồn kho ĐLPP, Báo cáo đơn hàng  EMSP: Báo cáo ODO(EMSP), Danh sách Bill thuê Pin(EMSP), Danh sách bill điều chỉnh (EMSP), Danh sách yêu cầu đổi gó`
- **Response flags**: ambiguous=False insufficient_context=False confidence=high intent=COUNT_ENTITIES
- **Resolved entities (200)**:  EV VIN Battery Report,  FTQ Welding - Ultrasonic,  MA - PIST Dimension Check, #Measurements
- **Trace_id**: `e032e32d0a76` | log lines: 2
- **VERDICT**: **FAIL**
  - **First incorrect state**: `tool_arguments`
  - **Failure type**: `TOOL_ARGUMENT_FAILURE`
  - **Root cause**: `RC3`
  - **Evidence**: count tool invoked without the entity/domain filter from the query; result is global count 500.

## C-003

- **Difficulty**: hard | **Category**: C | **Case**: -
- **User query**: `có bao nhiêu dataset tên "DIM_PACKED"?`
- **Expected intent**: `disambiguate_same_name` | **Expected domain**: `None`
- **Expected assets (0)**: 
- **Expected evidence**: [{"field": "name", "value": "DIM_PACKED", "note": "multiple urns"}]
- **Expected tool**: `['retrieve:entity_summary']`
- **Actual answer (trunc)**: `Có tổng cộng 500 datasets.  DMS: AR Receipts, Báo cáo Sales orders (Layout báo cáo cọc), Báo cáo bảo hành, Báo cáo hóa đơn  SCT, Báo cáo lệnh sửa chữa/ bảo hành Pending, Báo cáo sales orders, Báo cáo sales orders (Báo cáo chương trình giảm giá), Báo cáo tồn kho ĐLPP, Báo cáo đơn hàng  EMSP: Báo cáo ODO(EMSP), Danh sách Bill thuê Pin(EMSP), Danh sách bill điều chỉnh (EMSP), Danh sách yêu cầu đổi gó`
- **Response flags**: ambiguous=False insufficient_context=False confidence=high intent=COUNT_ENTITIES
- **Resolved entities (200)**:  EV VIN Battery Report,  FTQ Welding - Ultrasonic,  MA - PIST Dimension Check, #Measurements
- **Trace_id**: `e232c8ffa428` | log lines: 2
- **VERDICT**: **FAIL**
  - **First incorrect state**: `tool_arguments`
  - **Failure type**: `TOOL_ARGUMENT_FAILURE`
  - **Root cause**: `RC3`
  - **Evidence**: count_entities missing filter argument; returns total dataset count not the scoped count.

## CASE1-001

- **Difficulty**: hard | **Category**: CASE1 | **Case**: 1
- **User query**: `Demand là gì?`
- **Expected intent**: `domain_scoped_glossary` | **Expected domain**: `SẢN XUẤT`
- **Expected assets (1)**: urn:li:glossaryTerm:72c69954-8944-4e58-9af2-328502dc9390
- **Expected evidence**: [{"field": "description", "urn": "urn:li:glossaryTerm:72c69954-8944-4e58-9af2-328502dc9390"}]
- **Expected tool**: `['retrieve:term_definition']`
- **Actual answer (trunc)**: `Trong metadata hiện có, không có định nghĩa glossary cho thuật ngữ 'Demand'. Tuy nhiên, dataset 'Demand check' [E1] trên nền tảng PowerBI chứa các trường liên quan đến nhu cầu như req_M0 đến req_M12 (nhu cầu theo tháng), Stock, Stock_amount, cùng thông tin vật tư, nhà cung cấp và nhà máy.`
- **Response flags**: ambiguous=False insufficient_context=False confidence=medium intent=TERM_DEFINITION
- **Resolved entities (1)**: Demand check
- **Citations**: 1
- **Trace_id**: `738390c7201e` | log lines: 5
- **VERDICT**: **FAIL**
  - **First incorrect state**: `entity_resolution`
  - **Failure type**: `ENTITY_RESOLUTION_FAILURE`
  - **Root cause**: `RC4`
  - **Evidence**: glossary query 'Demand là gì?' resolved to dataset 'Demand check' instead of the Demand glossary terms; glossary resolution lacks term-vs-dataset scoping.

## CASE1-002

- **Difficulty**: hard | **Category**: CASE1 | **Case**: 1
- **User query**: `Demand trong domain SẢN XUẤT là gì?`
- **Expected intent**: `domain_scoped_glossary` | **Expected domain**: `SẢN XUẤT`
- **Expected assets (1)**: urn:li:glossaryTerm:72c69954-8944-4e58-9af2-328502dc9390
- **Expected evidence**: [{"field": "description", "urn": "urn:li:glossaryTerm:72c69954-8944-4e58-9af2-328502dc9390"}]
- **Expected tool**: `['retrieve:term_definition']`
- **Actual answer (trunc)**: `I couldn't find this information in the available DataHub metadata.`
- **Response flags**: ambiguous=False insufficient_context=True confidence=low intent=TERM_DEFINITION
- **Resolved entities (1)**: CP sản xuất bình quân/xe SOP
- **Citations**: 1
- **Trace_id**: `5cc096c4099f` | log lines: 5
- **VERDICT**: **FAIL**
  - **First incorrect state**: `domain_resolution`
  - **Failure type**: `DOMAIN_DISAMBIGUATION_FAILURE`
  - **Root cause**: `RC4`
  - **Evidence**: domain context SẢN XUẤT was dropped; ambiguous clarify on 'CP sản xuất bình quân/xe SOP' instead of applying domain scoping.

## CASE1-003

- **Difficulty**: hard | **Category**: CASE1 | **Case**: 1
- **User query**: `so sánh Demand giữa SẢN XUẤT và KINH DOANH`
- **Expected intent**: `domain_scoped_glossary` | **Expected domain**: `None`
- **Expected assets (1)**: urn:li:glossaryTerm:72c69954-8944-4e58-9af2-328502dc9390
- **Expected evidence**: [{"field": "description", "urn": "urn:li:glossaryTerm:72c69954-8944-4e58-9af2-328502dc9390"}]
- **Expected tool**: `['retrieve:term_definition']`
- **Actual answer (trunc)**: `### Kết luận Đã so sánh 6 dataset ứng viên: Báo cáo tiến độ xuất NVL cho sản xuất, Báo cáo số liệu tạm ứng và hoàn ứng, Báo cáo tình trạng nhập kho và Xuất hàng , MCO - Báo cáo tối ưu chi phí sản xuất, [KD]_Báo cáo đặt hàng sản xuất nhà máy, [LOG]_sản lượng  và chi phí cho hàng Premium. Khuyến nghị cụ thể nằm ở phần lý do.  ### Lý do chính - Resolve entities: Báo cáo tiến độ xuất NVL cho sản xuất,`
- **Response flags**: ambiguous=False insufficient_context=False confidence=high intent=THINKING_OVERVIEW
- **Trace_id**: `e5953c49719a` | log lines: 3
- **VERDICT**: **FAIL**
  - **First incorrect state**: `planner_decomposition`
  - **Failure type**: `PLANNER_DECOMPOSITION_FAILURE`
  - **Root cause**: `RC5`
  - **Evidence**: thinking mode tried to compare 6 datasets in one turn; composite comparison was not decomposed into per-entity sub-steps.

## CASE2-001

- **Difficulty**: medium | **Category**: CASE2 | **Case**: 2
- **User query**: `có báo cáo nào về capacity của nhà cung cấp (vendor) không?`
- **Expected intent**: `report_discovery_capacity` | **Expected domain**: `LOGISTIC`
- **Expected assets (4)**: urn:li:dashboard:(powerbi,reports.08875c53-cbd5-4435-aafd-b31e4e6940a8), urn:li:dashboard:(powerbi,reports.809b7230-223f-43ac-9b4d-a1f59b4f17c8), urn:li:dataset:(urn:li:dataPlatform:powerbi,HP_side_-_Control_Max_stock_+_Inbound.fact_supplier_capacity,PROD), urn:li:dataset:(urn:li:dataPlatform:redshift,sap.dwh.rpt_survey_weekly_supply_capacity,PROD)
- **Expected evidence**: [{"field": "name", "note": "capacity/supplier/survey keywords"}]
- **Expected tool**: `['retrieve:dashboard_summary', 'retrieve:entity_summary']`
- **Actual answer (trunc)**: `Có nhiều entity trùng khớp với yêu cầu của bạn: 'Quota giữa các nhà cung cấp' hoặc 'Báo cáo vận hành kho' hoặc '[LOG]_Sản lượng hàng nhập và chi phí thực tế'. Bạn muốn hỏi về entity nào?`
- **Response flags**: ambiguous=True insufficient_context=False confidence=low intent=GENERAL
- **Resolved entities (10)**: Quota giữa các nhà cung cấp, Báo cáo vận hành kho, [LOG]_Sản lượng hàng nhập và chi phí thự, [LOG]_Dữ liệu tracking của các lô hàng đ
- **Trace_id**: `ffa2474f562e` | log lines: 10
- **VERDICT**: **FAIL**
  - **First incorrect state**: `report_discovery`
  - **Failure type**: `REPORT_DISCOVERY_FAILURE`
  - **Root cause**: `RC6`
  - **Evidence**: correct dashboard/report existed among candidates but ambiguity gate blocked it; report-type resolution does not surface report/dashboard entities.

## CASE2-002

- **Difficulty**: medium | **Category**: CASE2 | **Case**: 2
- **User query**: `báo cáo capacity cung ứng tuần nào liên quan đến bảng survey capacity từng part?`
- **Expected intent**: `report_discovery_capacity` | **Expected domain**: `None`
- **Expected assets (1)**: urn:li:dataset:(urn:li:dataPlatform:redshift,sap.dwh.rpt_survey_weekly_supply_capacity,PROD)
- **Expected evidence**: [{"field": "name", "note": "capacity/supplier/survey keywords"}]
- **Expected tool**: `['retrieve:dashboard_summary', 'retrieve:entity_summary']`
- **Actual answer (trunc)**: `Có nhiều entity trùng khớp với yêu cầu của bạn: '[CSKH]_Weekly Report_Báo cáo khiếu nại liên quan tới RSA - MBS - MBC' hoặc 'Báo cáo kiểm tra chất lượng Sơn (QA)' hoặc 'Supplier Warranty Cost Recovery  " Báo cáo thu hồi chi phí bảo hành do lỗi nhà cung cấp xảy ra ngoài thị trường"'. Bạn muốn hỏi về entity nào?`
- **Response flags**: ambiguous=True insufficient_context=False confidence=low intent=GENERAL
- **Resolved entities (10)**: [CSKH]_Weekly Report_Báo cáo khiếu nại l, Báo cáo kiểm tra chất lượng Sơn (QA), Supplier Warranty Cost Recovery 
" Báo c, [QE-PPHP]-[QEHP] Battery Pack Shop Jira 
- **Trace_id**: `bb9ada3daf95` | log lines: 9
- **VERDICT**: **FAIL**
  - **First incorrect state**: `report_discovery`
  - **Failure type**: `REPORT_DISCOVERY_FAILURE`
  - **Root cause**: `RC6`
  - **Evidence**: rpt_survey_weekly_supply_capacity not discovered; report discovery missed the target report entity.

## CASE3-001

- **Difficulty**: hard | **Category**: CASE3 | **Case**: 3
- **User query**: `công thức Coverage Date trong Fact_Inventory_Coverage là gì?`
- **Expected intent**: `metric_formula_in_dataset` | **Expected domain**: `None`
- **Expected assets (2)**: urn:li:glossaryTerm:7081e281-2d7b-4f66-9b1b-c31cdb66cc1b, urn:li:glossaryTerm:e26f9aeb-b1f9-4553-9eac-f9137f915e4a
- **Expected evidence**: [{"field": "description", "urn": "urn:li:glossaryTerm:e26f9aeb-b1f9-4553-9eac-f9137f915e4a", "note": "Coverage Date định nghĩa 2: số ngày làm việc tồn kho + Git đủ nhu cầu, LOB ≥ 0"}]
- **Expected tool**: `['retrieve:term_definition']`
- **Actual answer (trunc)**: `Tôi không tìm thấy công thức Coverage Date trong Fact_Inventory_Coverage trong metadata DataHub hiện có. Ngữ cảnh chỉ cung cấp định nghĩa glossary term 'Inventory - Tồn kho xe' [E1], không bao gồm schema hay công thức của dataset Fact_Inventory_Coverage.`
- **Response flags**: ambiguous=False insufficient_context=True confidence=low intent=TERM_DEFINITION
- **Resolved entities (1)**: Inventory - Tồn kho xe
- **Citations**: 1
- **Trace_id**: `e8731c6028ed` | log lines: 5
- **VERDICT**: **FAIL**
  - **First incorrect state**: `entity_resolution`
  - **Failure type**: `ENTITY_RESOLUTION_FAILURE`
  - **Root cause**: `RC1b`
  - **Evidence**: fuzzy name-match resolved wrong entity (e.g. '[VN] Dealer OUT') instead of the intended one.

## CASE4-001

- **Difficulty**: hard | **Category**: CASE4 | **Case**: 4
- **User query**: `Report_Supply_Capacity lấy dữ liệu từ đâu? Liệt kê theo lineage từ report → dataset → nguồn thô.`
- **Expected intent**: `report_lineage_chain` | **Expected domain**: `LOGISTIC`
- **Expected assets (0)**: 
- **Expected evidence**: [{"field": "upstream_urns", "urn": "urn:li:dashboard:(powerbi,reports.08875c53-cbd5-4435-aafd-b31e4e6940a8)", "value": []}]
- **Expected tool**: `['retrieve:dashboard_summary', 'retrieve:entity_summary', 'retrieve:lineage']`
- **Actual answer (trunc)**: `Dataset [CSKH]_Daily Report_Báo cáo khiếu nại KH về chất lượng phục vụ tại các SR/XDV hiện không có lineage (upstream/downstream) được ghi nhận.`
- **Response flags**: ambiguous=False insufficient_context=False confidence=high intent=LINEAGE
- **Resolved entities (1)**: [CSKH]_Daily Report_Báo cáo khiếu nại KH
- **Trace_id**: `6d663325a80f` | log lines: 5
- **VERDICT**: **FAIL**
  - **First incorrect state**: `entity_resolution`
  - **Failure type**: `ENTITY_RESOLUTION_FAILURE`
  - **Root cause**: `RC7`
  - **Evidence**: lineage query resolved wrong dataset ('[CSKH]_Daily Report_Báo cáo khiếu nại KH...' instead of Report_Supply_Capacity dashboard) before lineage tool ran.

## CASE5-001

- **Difficulty**: hard | **Category**: CASE5 | **Case**: 5
- **User query**: `từ report capacity → định nghĩa capacity → cột liên quan → công thức → nguồn dữ liệu thô`
- **Expected intent**: `multi_hop_chain` | **Expected domain**: `LOGISTIC`
- **Expected assets (1)**: urn:li:dashboard:(powerbi,reports.08875c53-cbd5-4435-aafd-b31e4e6940a8)
- **Expected evidence**: [{"field": "name", "note": "hop1 report"}, {"field": "description", "note": "hop2 định nghĩa capacity: không có term capacity chuyên biệt → UNKNOWN"}, {"field": "schema_fields", "note": "hop3 cột liên quan của rpt_survey_weekly_supply_capacity"}, {"field": "formula", "note": "hop4 công thức: UNKNOWN
- **Expected tool**: `['retrieve:dashboard_summary', 'retrieve:entity_summary', 'retrieve:schema_fields', 'retrieve:term_definition', 'retrieve:lineage']`
- **Actual answer (trunc)**: `I couldn't find this information in the available DataHub metadata.`
- **Response flags**: ambiguous=False insufficient_context=True confidence=low intent=SCHEMA_LOOKUP
- **Resolved entities (1)**: [LOG-PPHP]-Báo cáo tồn kho EWM  hàng ngu
- **Citations**: 1
- **Trace_id**: `162aed9d22aa` | log lines: 5
- **VERDICT**: **FAIL**
  - **First incorrect state**: `planner_decomposition`
  - **Failure type**: `PLANNER_DECOMPOSITION_FAILURE`
  - **Root cause**: `RC5`
  - **Evidence**: multi-hop query collapsed into single SCHEMA_LOOKUP instead of decomposed lineage hops.

## CASE6-001

- **Difficulty**: hard | **Category**: CASE6 | **Case**: 6
- **User query**: `trong domain LOGISTIC, tìm report về capacity, term liên quan, dataset nguồn và lineage`
- **Expected intent**: `domain_report_term_lineage_chain` | **Expected domain**: `LOGISTIC`
- **Expected assets (1)**: urn:li:dashboard:(powerbi,reports.08875c53-cbd5-4435-aafd-b31e4e6940a8)
- **Expected evidence**: [{"field": "domain", "value": "LOGISTIC"}, {"field": "name", "note": "report capacity"}, {"field": "term", "note": "không có term capacity chuyên biệt → UNKNOWN"}, {"field": "lineage", "note": "UNKNOWN"}]
- **Expected tool**: `['retrieve:dashboard_summary', 'retrieve:entity_summary', 'retrieve:term_definition', 'retrieve:lineage']`
- **Actual answer (trunc)**: `Dataset Báo cáo tình trạng kiểm soát dữ liệu rác và kỷ luật dữ liệu hiện không có lineage (upstream/downstream) được ghi nhận.`
- **Response flags**: ambiguous=False insufficient_context=False confidence=high intent=LINEAGE
- **Resolved entities (1)**: Báo cáo tình trạng kiểm soát dữ liệu rác
- **Trace_id**: `fb2d4ee124b4` | log lines: 5
- **VERDICT**: **FAIL**
  - **First incorrect state**: `entity_resolution`
  - **Failure type**: `ENTITY_RESOLUTION_FAILURE`
  - **Root cause**: `RC7`
  - **Evidence**: lineage query resolved wrong entity before lineage tool; UNKNOWN returned on wrong entity.

## D-001

- **Difficulty**: easy | **Category**: D | **Case**: -
- **User query**: `"Nhu cầu linh kiện" là gì?`
- **Expected intent**: `glossary_definition` | **Expected domain**: `SẢN XUẤT`
- **Expected assets (1)**: urn:li:glossaryTerm:72c69954-8944-4e58-9af2-328502dc9390
- **Expected evidence**: [{"field": "description", "urn": "urn:li:glossaryTerm:72c69954-8944-4e58-9af2-328502dc9390"}]
- **Expected tool**: `['retrieve:term_definition']`
- **Actual answer (trunc)**: `Nhu cầu linh kiện (Component Demand / Part Demand) là số lượng linh kiện, nguyên vật liệu cần thiết để đáp ứng cho kế hoạch sản xuất thành phẩm xe tại một thời điểm xác định, được hệ thống MRP tính toán dựa trên kế hoạch sản xuất, cấu trúc BOM, tồn kho hiện tại, và thời gian cung ứng [E1]. Mục đích sử dụng bao gồm xác định số lượng chi tiết cần mua/sản xuất, hỗ trợ lập kế hoạch mua hàng và sản xuấ`
- **Response flags**: ambiguous=False insufficient_context=False confidence=medium intent=TERM_DEFINITION
- **Resolved entities (1)**: Nhu cầu linh kiện 
- **Citations**: 1
- **Trace_id**: `f5455953689e` | log lines: 5
- **VERDICT**: **PASS**

## D-002

- **Difficulty**: easy | **Category**: D | **Case**: -
- **User query**: `"Số lượng linh kiện hết hạn" là gì?`
- **Expected intent**: `glossary_definition` | **Expected domain**: `SẢN XUẤT`
- **Expected assets (1)**: urn:li:glossaryTerm:e5148b86-d3fb-4af8-860e-cd075c0a1527
- **Expected evidence**: [{"field": "description", "urn": "urn:li:glossaryTerm:e5148b86-d3fb-4af8-860e-cd075c0a1527"}]
- **Expected tool**: `['retrieve:term_definition']`
- **Actual answer (trunc)**: `Số lượng linh kiện hết hạn (Expired Components Count) là tổng số linh kiện trong kho có ngày hết hạn sớm hơn ngày hiện tại (SLED < Today), nghĩa là những linh kiện đó không còn đủ điều kiện để sử dụng hoặc đưa vào sản xuất do đã vượt quá thời hạn sử dụng quy định [E1]. Mục đích sử dụng bao gồm kiểm soát tồn kho, tránh sử dụng vật tư không đạt chuẩn, phục vụ báo cáo chất lượng (QA report), kiểm tra`
- **Response flags**: ambiguous=False insufficient_context=False confidence=medium intent=TERM_DEFINITION
- **Resolved entities (1)**: Số lượng linh kiện hết hạn 
- **Citations**: 1
- **Trace_id**: `845866133f77` | log lines: 5
- **VERDICT**: **PASS**

## E-001

- **Difficulty**: hard | **Category**: E | **Case**: -
- **User query**: `"Coverage Date" là gì?`
- **Expected intent**: `glossary_definition` | **Expected domain**: `None`
- **Expected assets (2)**: urn:li:glossaryTerm:7081e281-2d7b-4f66-9b1b-c31cdb66cc1b, urn:li:glossaryTerm:e26f9aeb-b1f9-4553-9eac-f9137f915e4a
- **Expected evidence**: [{"field": "name", "value": "Coverage Date", "note": "2 URN, 2 định nghĩa khác nhau"}]
- **Expected tool**: `['retrieve:term_definition']`
- **Actual answer (trunc)**: `Coverage Date (Coverage Days) là số ngày mà lượng tồn kho hiện tại có thể đáp ứng được nhu cầu sản xuất dự kiến, trước khi cần bổ sung thêm hàng [E1]. Mục đích sử dụng: đánh giá mức độ an toàn của tồn kho, cảnh báo sớm nguy cơ thiếu hụt vật tư, và hỗ trợ ra quyết định đặt hàng/bổ sung kịp thời [E1].`
- **Response flags**: ambiguous=False insufficient_context=False confidence=medium intent=TERM_DEFINITION
- **Resolved entities (1)**: Coverage Date
- **Citations**: 1
- **Trace_id**: `9b4b4b9075f5` | log lines: 6
- **VERDICT**: **FAIL**
  - **First incorrect state**: `entity_resolution`
  - **Failure type**: `ENTITY_RESOLUTION_FAILURE`
  - **Root cause**: `RC4`
  - **Evidence**: Coverage Date has 2 glossary URNs but only 1 surfaced; duplicate-term surface incomplete, no disambiguation.

## F-001

- **Difficulty**: medium | **Category**: F | **Case**: -
- **User query**: `dataset "VF_VN_DEX_PLANNING.v_ec1v_2025" gắn với glossary term nào?`
- **Expected intent**: `dataset_glossary_linkage` | **Expected domain**: `None`
- **Expected assets (2)**: urn:li:dataset:(urn:li:dataPlatform:powerbi,VF_VN_DEX_PLANNING.v_ec1v_2025,PROD), urn:li:glossaryTerm:7137e03e-59d5-485c-b0ba-82957e0b6b23
- **Expected evidence**: [{"field": "glossary_term_urns", "urn": "urn:li:dataset:(urn:li:dataPlatform:powerbi,VF_VN_DEX_PLANNING.v_ec1v_2025,PROD)", "value": ["urn:li:glossaryTerm:7137e03e-59d5-485c-b0ba-82957e0b6b23"]}]
- **Expected tool**: `['retrieve:entity_summary']`
- **Actual answer (trunc)**: `Không tìm thấy dataset 'vf vn dex planning v ec1v 2025" gan voi glossary' trong hệ thống DataHub.`
- **Response flags**: ambiguous=False insufficient_context=False confidence=high intent=TERM_TO_DATASETS
- **Trace_id**: `ca102002ade0` | log lines: 4
- **VERDICT**: **FAIL**
  - **First incorrect state**: `intent`
  - **Failure type**: `INTENT_FAILURE`
  - **Root cause**: `RC2`
  - **Evidence**: 'dataset X gắn với term nào' (term linkage) reversed direction; router picked wrong tool and resolved '[VN] Dealer OUT'.

## F-002

- **Difficulty**: medium | **Category**: F | **Case**: -
- **User query**: `dataset "VF_VN_DEX_PLANNING.mrp_stock_req" gắn với glossary term nào?`
- **Expected intent**: `dataset_glossary_linkage` | **Expected domain**: `None`
- **Expected assets (2)**: urn:li:dataset:(urn:li:dataPlatform:powerbi,VF_VN_DEX_PLANNING.mrp_stock_req,PROD), urn:li:glossaryTerm:72c69954-8944-4e58-9af2-328502dc9390
- **Expected evidence**: [{"field": "glossary_term_urns", "urn": "urn:li:dataset:(urn:li:dataPlatform:powerbi,VF_VN_DEX_PLANNING.mrp_stock_req,PROD)", "value": ["urn:li:glossaryTerm:72c69954-8944-4e58-9af2-328502dc9390"]}]
- **Expected tool**: `['retrieve:entity_summary']`
- **Actual answer (trunc)**: `I couldn't find this information in the available DataHub metadata.`
- **Response flags**: ambiguous=False insufficient_context=True confidence=low intent=TERM_TO_DATASETS
- **Resolved entities (8)**: Safety Stock, Logic SBOM , Tồn kho min max, Available_Stock
- **Citations**: 8
- **Trace_id**: `a4fa7e3cbc2d` | log lines: 5
- **VERDICT**: **FAIL**
  - **First incorrect state**: `intent`
  - **Failure type**: `INTENT_FAILURE`
  - **Root cause**: `RC2`
  - **Evidence**: dataset-to-term linkage query misrouted; linkage direction reversed.

## F-003

- **Difficulty**: medium | **Category**: F | **Case**: -
- **User query**: `dataset "dms.stg.stg_contact" gắn với glossary term nào?`
- **Expected intent**: `dataset_glossary_linkage` | **Expected domain**: `None`
- **Expected assets (2)**: urn:li:dataset:(urn:li:dataPlatform:redshift,dms.stg.stg_contact,PROD), urn:li:glossaryTerm:PII
- **Expected evidence**: [{"field": "glossary_term_urns", "urn": "urn:li:dataset:(urn:li:dataPlatform:redshift,dms.stg.stg_contact,PROD)", "value": ["urn:li:glossaryTerm:PII"]}]
- **Expected tool**: `['retrieve:entity_summary']`
- **Actual answer (trunc)**: `Không tìm thấy dataset 'dms stg stg contact" gan voi glossary' trong hệ thống DataHub.`
- **Response flags**: ambiguous=False insufficient_context=False confidence=high intent=TERM_TO_DATASETS
- **Trace_id**: `37572e2eb074` | log lines: 7
- **VERDICT**: **FAIL**
  - **First incorrect state**: `intent`
  - **Failure type**: `INTENT_FAILURE`
  - **Root cause**: `RC2`
  - **Evidence**: dataset-to-term linkage query misrouted; resolved unrelated entity.

## G-001

- **Difficulty**: medium | **Category**: G | **Case**: -
- **User query**: `trong dataset "dim_businessunit" có trường "bu_short_name" nghĩa là gì?`
- **Expected intent**: `column_definition` | **Expected domain**: `None`
- **Expected assets (1)**: urn:li:dataset:(urn:li:dataPlatform:powerbi,1._Awareness.dim_businessunit,PROD)
- **Expected evidence**: [{"field": "schema_fields", "urn": "urn:li:dataset:(urn:li:dataPlatform:powerbi,1._Awareness.dim_businessunit,PROD)", "value": "bu_short_name"}]
- **Expected tool**: `['retrieve:schema_fields']`
- **Actual answer (trunc)**: `Dataset **dim_businessunit** có các trường: business_unit_sid, business_unit_id, bu_short_name, bu_regular_name, bu_description, bu_type, bu_storetype, vf_showroom_yes, showroom_model, company_code, parent_bu_id, dms_business_unit_id, createdon, establishedin, area_sid, area_escooter_sid, car_service_area_sid, escooter_service_area_sid, province_sid, parent_bu_sid, type, open_time, bu_is_active, A`
- **Response flags**: ambiguous=False insufficient_context=False confidence=high intent=SCHEMA_LOOKUP
- **Resolved entities (1)**: dim_businessunit
- **Trace_id**: `b3a3e460fbfd` | log lines: 5
- **VERDICT**: **FAIL**
  - **First incorrect state**: `evidence_selection`
  - **Failure type**: `EVIDENCE_SELECTION_FAILURE`
  - **Root cause**: `RC8`
  - **Evidence**: field property query listed fields but did not explain the target field; evidence for field definition not injected into context.

## G-002

- **Difficulty**: medium | **Category**: G | **Case**: -
- **User query**: `trong dataset "fact_sale_orders" có trường "sod_total_amount" nghĩa là gì?`
- **Expected intent**: `column_definition` | **Expected domain**: `None`
- **Expected assets (1)**: urn:li:dataset:(urn:li:dataPlatform:powerbi,1._Awareness.fact_sale_orders,PROD)
- **Expected evidence**: [{"field": "schema_fields", "urn": "urn:li:dataset:(urn:li:dataPlatform:powerbi,1._Awareness.fact_sale_orders,PROD)", "value": "sod_total_amount"}]
- **Expected tool**: `['retrieve:schema_fields']`
- **Actual answer (trunc)**: `Dataset **fact_sale_orders** có các trường: dms_sod_id, sod_id, dms_so_id, so_id, bu_sid, customer_sid, product_sid, _xts_salesunitid_value, sod_total_amount, sod_total_amount_base, sod_status, sod_foc, sod_segment, created_date, updated_date, transaction_date, cancel_date, so_is_return, so_totalamountbeforediscount_base, so_status_code, so_status.`
- **Response flags**: ambiguous=False insufficient_context=False confidence=high intent=SCHEMA_LOOKUP
- **Resolved entities (1)**: fact_sale_orders
- **Trace_id**: `58ac58a9503c` | log lines: 5
- **VERDICT**: **FAIL**
  - **First incorrect state**: `entity_resolution`
  - **Failure type**: `ENTITY_RESOLUTION_FAILURE`
  - **Root cause**: `RC1b`
  - **Evidence**: fuzzy name-match resolved wrong entity for field-owner query.

## G-003

- **Difficulty**: medium | **Category**: G | **Case**: -
- **User query**: `trong dataset "dim_plant" có trường "is_manufacturing" nghĩa là gì?`
- **Expected intent**: `column_definition` | **Expected domain**: `None`
- **Expected assets (1)**: urn:li:dataset:(urn:li:dataPlatform:powerbi,Báo_cáo_KQKD_Hậu_mãi.dim_plant,PROD)
- **Expected evidence**: [{"field": "schema_fields", "urn": "urn:li:dataset:(urn:li:dataPlatform:powerbi,Báo_cáo_KQKD_Hậu_mãi.dim_plant,PROD)", "value": "is_manufacturing"}]
- **Expected tool**: `['retrieve:schema_fields']`
- **Actual answer (trunc)**: `Dataset **DIM_PLANT** có các trường: plant_sid, PLANT_ID, plant_name, region_id, country_id, address_id, is_manufacturing, is_scm_scope, country_name, plant_type.`
- **Response flags**: ambiguous=False insufficient_context=False confidence=high intent=SCHEMA_LOOKUP
- **Resolved entities (1)**: DIM_PLANT
- **Trace_id**: `11c5801150c8` | log lines: 5
- **VERDICT**: **FAIL**
  - **First incorrect state**: `evidence_selection`
  - **Failure type**: `EVIDENCE_SELECTION_FAILURE`
  - **Root cause**: `RC8`
  - **Evidence**: field property evidence not built into context; answer lacks field-level description.

## H-001

- **Difficulty**: easy | **Category**: H | **Case**: -
- **User query**: `có dashboard/report nào tên "Report_Supply_Capacity"?`
- **Expected intent**: `dashboard_lookup` | **Expected domain**: `LOGISTIC`
- **Expected assets (1)**: urn:li:dashboard:(powerbi,reports.08875c53-cbd5-4435-aafd-b31e4e6940a8)
- **Expected evidence**: [{"field": "name", "value": "Report_Supply_Capacity"}]
- **Expected tool**: `['retrieve:dashboard_summary']`
- **Actual answer (trunc)**: `Xin lỗi, đã xảy ra lỗi khi tạo câu trả lời.`
- **Response flags**: ambiguous=False insufficient_context=False confidence=medium intent=ENTITY_EXISTS
- **Resolved entities (1)**: Mapping Supplier & Buyer Report
- **Citations**: 1
- **Trace_id**: `2e88b34857ae` | log lines: 7
- **VERDICT**: **FAIL**
  - **First incorrect state**: `report_discovery`
  - **Failure type**: `REPORT_DISCOVERY_FAILURE`
  - **Root cause**: `RC6`
  - **Evidence**: resolved dataset 'Mapping Supplier & Buyer Report' instead of the report entity; report discovery wrong.

## H-002

- **Difficulty**: easy | **Category**: H | **Case**: -
- **User query**: `có dashboard/report nào tên "PFEP Report - Hai Phong Factory"?`
- **Expected intent**: `dashboard_lookup` | **Expected domain**: `LOGISTIC`
- **Expected assets (1)**: urn:li:dashboard:(powerbi,reports.1e74bc9a-cf99-49cf-9e44-6f25f4b4ee6a)
- **Expected evidence**: [{"field": "name", "value": "PFEP Report - Hai Phong Factory"}]
- **Expected tool**: `['retrieve:dashboard_summary']`
- **Actual answer (trunc)**: `Có. Dashboard 'PFEP Report - Hai Phong Factory' tồn tại trong DataHub [E1]. Đây là một dashboard Power BI với URN: urn:li:dashboard:(powerbi,reports.1e74bc9a-cf99-49cf-9e44-6f25f4b4ee6a) [E1].`
- **Response flags**: ambiguous=False insufficient_context=False confidence=medium intent=ENTITY_EXISTS
- **Resolved entities (1)**: PFEP Report - Hai Phong Factory
- **Citations**: 1
- **Trace_id**: `d68942147a4f` | log lines: 9
- **VERDICT**: **FAIL**
  - **First incorrect state**: `report_discovery`
  - **Failure type**: `REPORT_DISCOVERY_FAILURE`
  - **Root cause**: `RC6`
  - **Evidence**: correct dashboard among candidates but ambiguity gate blocked it; report-type entities not surfaced.

## H-003

- **Difficulty**: easy | **Category**: H | **Case**: -
- **User query**: `có dashboard/report nào tên "VINFAST_Report12 PFEP"?`
- **Expected intent**: `dashboard_lookup` | **Expected domain**: `SẢN XUẤT`
- **Expected assets (1)**: urn:li:dashboard:(powerbi,reports.5346a967-c65e-4c9c-b470-3921f3f735db)
- **Expected evidence**: [{"field": "name", "value": "VINFAST_Report12 PFEP"}]
- **Expected tool**: `['retrieve:dashboard_summary']`
- **Actual answer (trunc)**: `Có, tồn tại dashboard tên 'VINFAST_Report12 PFEP' [E1]. Đây là một dashboard PowerBI với URN `urn:li:dashboard:(powerbi,reports.5346a967-c65e-4c9c-b470-3921f3f735db)` [E1].`
- **Response flags**: ambiguous=False insufficient_context=False confidence=medium intent=ENTITY_EXISTS
- **Resolved entities (1)**: VINFAST_Report12 PFEP
- **Citations**: 1
- **Trace_id**: `d2b39f5a4fab` | log lines: 9
- **VERDICT**: **FAIL**
  - **First incorrect state**: `report_discovery`
  - **Failure type**: `REPORT_DISCOVERY_FAILURE`
  - **Root cause**: `RC6`
  - **Evidence**: dashboard discovery missed target; report/dashboard candidate not resolved.

## I-001

- **Difficulty**: medium | **Category**: I | **Case**: -
- **User query**: `mô tả chi tiết của dashboard "R_Báo cáo đối soát hoá đơn DMS - SAP"?`
- **Expected intent**: `dashboard_description` | **Expected domain**: `None`
- **Expected assets (1)**: urn:li:dashboard:(powerbi,reports.784b19a7-6d1a-4dad-ad9a-d2a3e7cbfff1)
- **Expected evidence**: [{"field": "description", "urn": "urn:li:dashboard:(powerbi,reports.784b19a7-6d1a-4dad-ad9a-d2a3e7cbfff1)"}]
- **Expected tool**: `['retrieve:dashboard_summary']`
- **Actual answer (trunc)**: `Dashboard 'R_Báo cáo đối soát hoá đơn DMS - SAP' hiện chỉ có tên và URL truy cập [E1]. Không có mô tả chi tiết, chủ sở hữu, schema hay lineage trong metadata hiện có.`
- **Response flags**: ambiguous=False insufficient_context=False confidence=medium intent=TERM_DEFINITION
- **Resolved entities (1)**: R_Báo cáo đối soát hoá đơn DMS - SAP
- **Citations**: 1
- **Trace_id**: `88f4f989ee59` | log lines: 9
- **VERDICT**: **PASS**

## J-001

- **Difficulty**: hard | **Category**: J | **Case**: -
- **User query**: `dashboard "Report_Supply_Capacity" dùng những dataset nào làm nguồn?`
- **Expected intent**: `report_dataset_lineage` | **Expected domain**: `LOGISTIC`
- **Expected assets (0)**: 
- **Expected evidence**: [{"field": "upstream_urns", "urn": "urn:li:dashboard:(powerbi,reports.08875c53-cbd5-4435-aafd-b31e4e6940a8)", "value": []}]
- **Expected tool**: `['retrieve:dashboard_summary', 'retrieve:entity_summary']`
- **Actual answer (trunc)**: `Dataset Báo cáo chi phí sử dụng năng lượng hàng tháng hiện không có lineage (upstream/downstream) được ghi nhận.`
- **Response flags**: ambiguous=False insufficient_context=False confidence=high intent=LINEAGE
- **Resolved entities (1)**: Báo cáo chi phí sử dụng năng lượng hàng 
- **Trace_id**: `b64401803d22` | log lines: 5
- **VERDICT**: **FAIL**
  - **First incorrect state**: `entity_resolution`
  - **Failure type**: `ENTITY_RESOLUTION_FAILURE`
  - **Root cause**: `RC7`
  - **Evidence**: lineage query resolved wrong entity before lineage tool; lineage UNKNOWN on wrong entity.

## K-001

- **Difficulty**: medium | **Category**: K | **Case**: -
- **User query**: `"Tính toán “Demand of all build phases per variant”" tính như thế nào?`
- **Expected intent**: `formula_explanation` | **Expected domain**: `SẢN XUẤT`
- **Expected assets (1)**: urn:li:glossaryTerm:42dae407-ae65-4d6b-a9c9-6e4925d0c70c
- **Expected evidence**: [{"field": "description", "urn": "urn:li:glossaryTerm:42dae407-ae65-4d6b-a9c9-6e4925d0c70c", "value": "Demand (per Variant) = Sum(BOM Qty × Order Qty) WHERE Order Status = OPEN/IN PROGRESS FOR ALL Build Phases"}]
- **Expected tool**: `['retrieve:term_definition']`
- **Actual answer (trunc)**: `Glossary term 'Tính toán “Demand of all build phases per variant”' tồn tại trong DataHub [E1], nhưng metadata chỉ có tên, không có công thức hoặc mô tả cách tính. Vì vậy tôi không thể mô tả cách tính.`
- **Response flags**: ambiguous=False insufficient_context=False confidence=medium intent=TERM_DEFINITION
- **Resolved entities (1)**: Tính toán “Demand of all build phases pe
- **Citations**: 1
- **Trace_id**: `a25b0cfd77eb` | log lines: 9
- **VERDICT**: **FAIL**
  - **First incorrect state**: `metric_formula_discovery`
  - **Failure type**: `METRIC_FORMULA_DISCOVERY_FAILURE`
  - **Root cause**: `RC8`
  - **Evidence**: formula exists in ground-truth description but not injected into context; answer said 'không có công thức' (no formula).

## L-001

- **Difficulty**: hard | **Category**: L | **Case**: -
- **User query**: `công thức của Coverage Date như trong dữ liệu là gì?`
- **Expected intent**: `metric_formula` | **Expected domain**: `None`
- **Expected assets (2)**: urn:li:glossaryTerm:7081e281-2d7b-4f66-9b1b-c31cdb66cc1b, urn:li:glossaryTerm:e26f9aeb-b1f9-4553-9eac-f9137f915e4a
- **Expected evidence**: [{"field": "description", "urn": "urn:li:glossaryTerm:7081e281-2d7b-4f66-9b1b-c31cdb66cc1b", "note": "định nghĩa 1"}, {"field": "description", "urn": "urn:li:glossaryTerm:e26f9aeb-b1f9-4553-9eac-f9137f915e4a", "note": "định nghĩa 2"}]
- **Expected tool**: `['retrieve:term_definition']`
- **Actual answer (trunc)**: `Metadata hiện có chỉ cung cấp định nghĩa Coverage Date (số ngày tồn kho đáp ứng nhu cầu sản xuất dự kiến) [E1], nhưng không chứa công thức tính toán cụ thể.`
- **Response flags**: ambiguous=False insufficient_context=False confidence=medium intent=TERM_DEFINITION
- **Resolved entities (1)**: Coverage Date
- **Citations**: 1
- **Trace_id**: `68b5372d581a` | log lines: 5
- **VERDICT**: **FAIL**
  - **First incorrect state**: `entity_resolution`
  - **Failure type**: `ENTITY_RESOLUTION_FAILURE`
  - **Root cause**: `RC4`
  - **Evidence**: Coverage Date 2 URNs, only 1 surfaced; duplicate-term surfacing incomplete.

## M-001

- **Difficulty**: hard | **Category**: M | **Case**: -
- **User query**: `trace lineage của dashboard "PFEP Report - Hai Phong Factory" từ nguồn gốc?`
- **Expected intent**: `report_lineage_trace` | **Expected domain**: `LOGISTIC`
- **Expected assets (0)**: 
- **Expected evidence**: [{"field": "upstream_urns", "urn": "urn:li:dashboard:(powerbi,reports.1e74bc9a-cf99-49cf-9e44-6f25f4b4ee6a)", "value": []}]
- **Expected tool**: `['retrieve:dashboard_summary', 'retrieve:entity_summary', 'retrieve:lineage']`
- **Actual answer (trunc)**: `Dataset [PEPP-PPHT]-Báo cáo tuần _Bulk material hiện không có lineage (upstream/downstream) được ghi nhận.`
- **Response flags**: ambiguous=False insufficient_context=False confidence=high intent=LINEAGE
- **Resolved entities (1)**: [PEPP-PPHT]-Báo cáo tuần _Bulk material
- **Trace_id**: `7d9d9256310d` | log lines: 5
- **VERDICT**: **FAIL**
  - **First incorrect state**: `entity_resolution`
  - **Failure type**: `ENTITY_RESOLUTION_FAILURE`
  - **Root cause**: `RC7`
  - **Evidence**: lineage query resolved wrong entity before lineage tool; lineage UNKNOWN on wrong entity.

## N-001

- **Difficulty**: hard | **Category**: N | **Case**: -
- **User query**: `upstream/downstream của dataset "fact_mcn_pfep" là gì?`
- **Expected intent**: `dataset_lineage` | **Expected domain**: `SẢN XUẤT`
- **Expected assets (0)**: 
- **Expected evidence**: [{"field": "upstream_urns", "urn": "urn:li:dataset:(urn:li:dataPlatform:redshift,dataanalyticsprd.dwh.fact_mcn_pfep,PROD)", "value": []}, {"field": "downstream_urns", "urn": "urn:li:dataset:(urn:li:dataPlatform:redshift,dataanalyticsprd.dwh.fact_mcn_pfep,PROD)", "value": []}]
- **Expected tool**: `['retrieve:entity_summary', 'retrieve:lineage']`
- **Actual answer (trunc)**: `Dataset fact_mcn_pfep hiện không có lineage (upstream/downstream) được ghi nhận.`
- **Response flags**: ambiguous=False insufficient_context=False confidence=high intent=LINEAGE
- **Resolved entities (1)**: fact_mcn_pfep
- **Trace_id**: `5ba4796e431c` | log lines: 5
- **VERDICT**: **FAIL**
  - **First incorrect state**: `entity_resolution`
  - **Failure type**: `ENTITY_RESOLUTION_FAILURE`
  - **Root cause**: `RC7`
  - **Evidence**: lineage query resolved wrong entity before lineage tool.

## O-001

- **Difficulty**: medium | **Category**: O | **Case**: -
- **User query**: `dataset thô (staging) nào chứa dữ liệu đơn hàng bán?`
- **Expected intent**: `raw_source_discovery` | **Expected domain**: `None`
- **Expected assets (1)**: urn:li:dataset:(urn:li:dataPlatform:redshift,dms.stg.stg_lead,PROD)
- **Expected evidence**: [{"field": "name", "value": "stg_lead", "note": "prefix stg_ = staging"}]
- **Expected tool**: `['retrieve:entity_summary', 'retrieve:schema_fields']`
- **Actual answer (trunc)**: `Có nhiều entity trùng khớp với yêu cầu của bạn: 'Báo cáo đơn hàng' hoặc 'Báo cáo hóa đơn  SCT' hoặc 'Dealer OUT - ĐL/NPP bán ra cho Khách hàng'. Bạn muốn hỏi về entity nào?`
- **Response flags**: ambiguous=True insufficient_context=False confidence=low intent=GENERAL
- **Resolved entities (10)**: Báo cáo đơn hàng, Báo cáo hóa đơn  SCT, Dealer OUT - ĐL/NPP bán ra cho Khách hàn, [VN] Đơn hàng GSM
- **Trace_id**: `adf6b083dec2` | log lines: 9
- **VERDICT**: **FAIL**
  - **First incorrect state**: `entity_resolution`
  - **Failure type**: `ENTITY_RESOLUTION_FAILURE`
  - **Root cause**: `RC1a`
  - **Evidence**: false-positive ambiguity gate: resolver ambiguous=False but response ambiguous=True clarify with runner-up of different type.

## O-002

- **Difficulty**: medium | **Category**: O | **Case**: -
- **User query**: `dataset staging vật tư (material) trong DMS ở đâu?`
- **Expected intent**: `raw_source_discovery` | **Expected domain**: `None`
- **Expected assets (1)**: urn:li:dataset:(urn:li:dataPlatform:redshift,dms.stg.stg_material,PROD)
- **Expected evidence**: [{"field": "name", "value": "stg_material", "note": "prefix stg_ = staging"}]
- **Expected tool**: `['retrieve:entity_summary', 'retrieve:schema_fields']`
- **Actual answer (trunc)**: `Có nhiều entity trùng khớp với yêu cầu của bạn: '[Production]CAR_VIN_DeclareStatus' hoặc 'MRQ (Material Readiness Quality)' hoặc 'Chi phí tồn kho vật tư trực tiếp'. Bạn muốn hỏi về entity nào?`
- **Response flags**: ambiguous=True insufficient_context=False confidence=low intent=GENERAL
- **Resolved entities (10)**: [Production]CAR_VIN_DeclareStatus, MRQ (Material Readiness Quality), Chi phí tồn kho vật tư trực tiếp, Good Issue
- **Trace_id**: `5271507d4eff` | log lines: 9
- **VERDICT**: **FAIL**
  - **First incorrect state**: `entity_resolution`
  - **Failure type**: `ENTITY_RESOLUTION_FAILURE`
  - **Root cause**: `RC1b`
  - **Evidence**: fuzzy name-match resolved wrong entity.

## P-001

- **Difficulty**: medium | **Category**: P | **Case**: -
- **User query**: `nó có trường nào?`
- **Conversation history**: 2 turn(s)
- **Expected intent**: `column_listing_in_context` | **Expected domain**: `None`
- **Expected assets (1)**: urn:li:dataset:(urn:li:dataPlatform:powerbi,PFEP_Report_-_Hai_Phong_Factory.Fact_Mrp_Demand,PROD)
- **Expected evidence**: [{"field": "schema_fields", "note": "material_id, plant_id, Year, Mat-Plant, Refresh_Date, Material, Month, Demand Q'ty"}]
- **Expected tool**: `['retrieve:schema_fields']`
- **Actual answer (trunc)**: `Dataset **Fact_Mrp_Demand** có các trường: material_id, plant_id, Year, Mat-Plant, Refresh_Date, Material, Month, Demand Q'ty.`
- **Response flags**: ambiguous=False insufficient_context=False confidence=high intent=SCHEMA_LOOKUP
- **Trace_id**: `d907992ae689` | log lines: 4
- **VERDICT**: **PASS**

## Q-001

- **Difficulty**: hard | **Category**: Q | **Case**: -
- **User query**: `còn dashboard nào về PFEP cho nhà máy khác không?`
- **Conversation history**: 2 turn(s)
- **Expected intent**: `entity_switch_glossary_to_dashboard` | **Expected domain**: `None`
- **Expected assets (2)**: urn:li:dashboard:(powerbi,reports.1e74bc9a-cf99-49cf-9e44-6f25f4b4ee6a), urn:li:dashboard:(powerbi,reports.08875c53-cbd5-4435-aafd-b31e4e6940a8)
- **Expected evidence**: [{"field": "name", "note": "PFEP Report - Hai Phong Factory, Report_Supply_Capacity, VINFAST_Report12 PFEP, PFEP, PFEP_INDO..."}]
- **Expected tool**: `['retrieve:dashboard_summary']`
- **Actual answer (trunc)**: `Trong metadata hiện có, tôi không tìm thấy dashboard nào về PFEP cho nhà máy khác. Chỉ có glossary term PFEP [E1] và dataset 'Báo cáo Kế hoạch tài chính opex & capex của các nhà máy' (không có owner) [E2], nhưng không có dashboard PFEP nào được liệt kê.`
- **Response flags**: ambiguous=False insufficient_context=True confidence=medium intent=FIND_ENTITY
- **Trace_id**: `b712bee02535` | log lines: 58
- **VERDICT**: **FAIL**
  - **First incorrect state**: `context_propagation`
  - **Failure type**: `CONTEXT_PROPAGATION_FAILURE`
  - **Root cause**: `RC9`
  - **Evidence**: multi-turn follow-up: whole follow-up query fuzzy-matched as entity name -> OWNER_LOOKUP wrong; anaphora/reference not propagated from prior turn.

## R-001

- **Difficulty**: hard | **Category**: R | **Case**: -
- **User query**: `so sánh số trường giữa Fact_Mrp_Demand và dim_vehicle_model`
- **Expected intent**: `multi_entity_comparison` | **Expected domain**: `None`
- **Expected assets (2)**: urn:li:dataset:(urn:li:dataPlatform:powerbi,PFEP_Report_-_Hai_Phong_Factory.Fact_Mrp_Demand,PROD), urn:li:dataset:(urn:li:dataPlatform:powerbi,7_Báo_cáo_kho_vận.dim_vehicle_model,PROD)
- **Expected evidence**: [{"field": "schema_field_count", "value": "8 (Fact_Mrp_Demand)"}, {"field": "schema_field_count", "value": "7 (dim_vehicle_model)"}]
- **Expected tool**: `['retrieve:schema_fields']`
- **Actual answer (trunc)**: `Dataset **Fact_Mrp_Demand** có các trường: material_id, plant_id, Year, Mat-Plant, Refresh_Date, Material, Month, Demand Q'ty.`
- **Response flags**: ambiguous=False insufficient_context=False confidence=high intent=SCHEMA_LOOKUP
- **Resolved entities (1)**: Fact_Mrp_Demand
- **Trace_id**: `b16b95b0fac7` | log lines: 5
- **VERDICT**: **FAIL**
  - **First incorrect state**: `planner_decomposition`
  - **Failure type**: `PLANNER_DECOMPOSITION_FAILURE`
  - **Root cause**: `RC5`
  - **Evidence**: query needs 2 datasets but only 1 resolved; multi-entity query not decomposed.

## S-001

- **Difficulty**: hard | **Category**: S | **Case**: -
- **User query**: `PFEP là gì và dashboard PFEP nào thuộc domain LOGISTIC?`
- **Expected intent**: `multi_question_decomposition` | **Expected domain**: `None`
- **Expected assets (3)**: urn:li:glossaryTerm:7f04e765-927e-4272-a16c-843a06110280, urn:li:dashboard:(powerbi,reports.1e74bc9a-cf99-49cf-9e44-6f25f4b4ee6a), urn:li:dashboard:(powerbi,reports.08875c53-cbd5-4435-aafd-b31e4e6940a8)
- **Expected evidence**: [{"field": "description", "note": "định nghĩa PFEP"}, {"field": "domain", "value": "LOGISTIC", "note": "dashboard"}]
- **Expected tool**: `['retrieve:term_definition', 'retrieve:dashboard_summary']`
- **Actual answer (trunc)**: `Tôi không tìm thấy định nghĩa (glossary term) cho PFEP trong metadata hiện có, nên không thể giải thích ý nghĩa của thuật ngữ này [E1]. Tuy nhiên, có một dashboard tên 'PFEP' thuộc domain LOGISTIC, nền tảng PowerBI, với URL: https://datahub.vinfastauto.com/dashboard/urn:li:dashboard:(powerbi,reports.675d1b63-79e2-4e43-b8e2-0b8e9897ca6c) [E1].`
- **Response flags**: ambiguous=False insufficient_context=False confidence=medium intent=TERM_DEFINITION
- **Resolved entities (1)**: PFEP
- **Citations**: 1
- **Trace_id**: `641fcdc51ce5` | log lines: 5
- **VERDICT**: **FAIL**
  - **First incorrect state**: `planner_decomposition`
  - **Failure type**: `PLANNER_DECOMPOSITION_FAILURE`
  - **Root cause**: `RC5`
  - **Evidence**: two-part question only answered 1/2 parts; composite query not decomposed.

## T-001

- **Difficulty**: hard | **Category**: T | **Case**: -
- **User query**: `tìm dataset tính nhu cầu linh kiện, cho biết trường chính và term định nghĩa liên quan`
- **Expected intent**: `end_to_end_dataset_term_field` | **Expected domain**: `SẢN XUẤT`
- **Expected assets (2)**: urn:li:dataset:(urn:li:dataPlatform:powerbi,VF_VN_DEX_PLANNING.mrp_stock_req,PROD), urn:li:glossaryTerm:72c69954-8944-4e58-9af2-328502dc9390
- **Expected evidence**: [{"field": "glossary_term_urns", "value": ["urn:li:glossaryTerm:72c69954-8944-4e58-9af2-328502dc9390"]}, {"field": "description", "note": "Nhu cầu linh kiện do MRP tính"}]
- **Expected tool**: `['retrieve:entity_summary', 'retrieve:schema_fields', 'retrieve:term_definition']`
- **Actual answer (trunc)**: `Tôi không tìm thấy dataset tính nhu cầu linh kiện trong metadata DataHub hiện có. Dataset duy nhất trong ngữ cảnh là '[LOG- PPHT]-Báo cáo hạn sử dụng còn lại của các mã NVL có quản lý HSD' (mã báo cáo ZMMQ003, nguồn SAP + Excel, tần suất hàng ngày, domain SẢN XUẤT) - báo cáo về tồn kho, thời gian GR, thời gian sản xuất và hết hạn của NVL có quản lý HSD [E1]. Không có thông tin về trường chính hay `
- **Response flags**: ambiguous=False insufficient_context=False confidence=medium intent=SCHEMA_LOOKUP
- **Resolved entities (1)**: '[LOG- PPHT]-Báo cáo hạn sử dụng còn lại
- **Citations**: 1
- **Trace_id**: `201e71db901a` | log lines: 5
- **VERDICT**: **FAIL**
  - **First incorrect state**: `entity_resolution`
  - **Failure type**: `ENTITY_RESOLUTION_FAILURE`
  - **Root cause**: `RC1b`
  - **Evidence**: fuzzy name-match resolved wrong entity.

## U-001

- **Difficulty**: hard | **Category**: U | **Case**: -
- **User query**: `dataset chứa thông tin khách hàng (PII) nào có gắn term về bảo mật?`
- **Expected intent**: `evidence_direct_indirect` | **Expected domain**: `None`
- **Expected assets (2)**: urn:li:dataset:(urn:li:dataPlatform:redshift,dms.stg.stg_contact,PROD), urn:li:glossaryTerm:PII
- **Expected evidence**: [{"field": "glossary_term_urns", "note": "stg_contact gắn PII và AES-256 (direct)"}]
- **Expected tool**: `['retrieve:entity_summary']`
- **Actual answer (trunc)**: `Term 'PII' hiện chưa được gắn cho dataset nào trong metadata DataHub.`
- **Response flags**: ambiguous=False insufficient_context=False confidence=high intent=TERM_TO_DATASETS
- **Resolved entities (1)**: PII
- **Trace_id**: `f70f2f8d0f29` | log lines: 5
- **VERDICT**: **FAIL**
  - **First incorrect state**: `retrieval`
  - **Failure type**: `RETRIEVAL_FAILURE`
  - **Root cause**: `RC10`
  - **Evidence**: term->datasets reverse-linkage returned empty though ground truth has 23 edges (stg_contact<->PII, stg_pbed<->PII); reverse edges not retrieved.

## V-001

- **Difficulty**: hard | **Category**: V | **Case**: -
- **User query**: `ai là owner của dataset fact_mcr?`
- **Expected intent**: `owner_query` | **Expected domain**: `None`
- **Expected assets (0)**: 
- **Expected evidence**: [{"field": "owners", "value": []}]
- **Expected tool**: `['retrieve:entity_summary']`
- **Actual answer (trunc)**: `Không tìm thấy dataset 'owner fact mcr' trong hệ thống DataHub. Ý bạn là 'Fact_Mrp_Demand'?`
- **Response flags**: ambiguous=False insufficient_context=False confidence=high intent=OWNER_LOOKUP
- **Trace_id**: `f97a9fb33167` | log lines: 5
- **VERDICT**: **FAIL**
  - **First incorrect state**: `entity_resolution`
  - **Failure type**: `ENTITY_RESOLUTION_FAILURE`
  - **Root cause**: `RC1b`
  - **Evidence**: fact_mcr not resolved -> chat_not_found; fuzzy name-match failed to resolve the entity.

## W-001

- **Difficulty**: medium | **Category**: W | **Case**: -
- **User query**: `chỉ nêu báo cáo thuộc domain TÀI CHÍNH về giá thành hoặc ngân sách`
- **Expected intent**: `domain_constrained_discovery` | **Expected domain**: `TÀI CHÍNH`
- **Expected assets (2)**: urn:li:dataset:(urn:li:dataPlatform:SAP,Kế toán.Báo cáo giá thành,PROD), urn:li:dataset:(urn:li:dataPlatform:SAP,Tối ưu Sản xuất và Cung ứng.Báo cáo sử dụng ngân sách Opex và phân tích CPU/CPH,PROD)
- **Expected evidence**: [{"field": "domain", "value": "TÀI CHÍNH"}]
- **Expected tool**: `['retrieve:entity_summary']`
- **Actual answer (trunc)**: `Có nhiều entity trùng khớp với yêu cầu của bạn: 'Báo cáo giá thành kế hoạch ngân sách' hoặc 'Báo cáo tiêu dùng ngân sách theo Bộ phận' hoặc 'Báo cáo Capex'. Bạn muốn hỏi về entity nào?`
- **Response flags**: ambiguous=True insufficient_context=False confidence=low intent=GENERAL
- **Resolved entities (10)**: Báo cáo giá thành kế hoạch ngân sách, Báo cáo tiêu dùng ngân sách theo Bộ phận, Báo cáo Capex, Báo cáo kế hoạch Ngân sách
- **Trace_id**: `ffcbaf43a23e` | log lines: 10
- **VERDICT**: **FAIL**
  - **First incorrect state**: `domain_resolution`
  - **Failure type**: `DOMAIN_DISAMBIGUATION_FAILURE`
  - **Root cause**: `RC11`
  - **Evidence**: domain constraint TÀI CHÍNH not applied as filter; resolver returned ambiguous clarify instead of scoping to domain.

## X-001

- **Difficulty**: medium | **Category**: X | **Case**: -
- **User query**: `dataset nào chứa trường 'plant_id'?`
- **Expected intent**: `retrieval_only_field_query` | **Expected domain**: `None`
- **Expected assets (0)**: 
- **Expected evidence**: [{"field": "schema_fields", "note": "plant_id xuất hiện trong nhiều dataset (892 lần)"}]
- **Expected tool**: `['retrieve:schema_fields']`
- **Actual answer (trunc)**: `Dataset **dim_bom_cost_non_plant_restore** có các trường: material_id, base_uom, curr_id, price_type, price_priority, price_priority_v2, net_price_base_uom, net_price_base_uom_per_unit.`
- **Response flags**: ambiguous=False insufficient_context=False confidence=high intent=SCHEMA_LOOKUP
- **Resolved entities (1)**: dim_bom_cost_non_plant_restore
- **Trace_id**: `9017985f082f` | log lines: 5
- **VERDICT**: **FAIL**
  - **First incorrect state**: `entity_resolution`
  - **Failure type**: `ENTITY_RESOLUTION_FAILURE`
  - **Root cause**: `RC1b`
  - **Evidence**: fuzzy name-match resolved wrong entity.

## Y-001

- **Difficulty**: medium | **Category**: Y | **Case**: -
- **User query**: `"MRP (Material Requirements Planning)" được định nghĩa ở đâu?`
- **Expected intent**: `citation_provenance` | **Expected domain**: `None`
- **Expected assets (1)**: urn:li:glossaryTerm:90343e1f-15de-4625-adc8-a247318d7cbc
- **Expected evidence**: [{"field": "description", "urn": "urn:li:glossaryTerm:90343e1f-15de-4625-adc8-a247318d7cbc"}]
- **Expected tool**: `['retrieve:term_definition']`
- **Actual answer (trunc)**: `MRP (Material Requirements Planning) được định nghĩa trong glossary term có URN urn:li:glossaryTerm:90343e1f-15de-4625-adc8-a247318d7cbc [E1]. Bạn có thể xem chi tiết tại URL: https://datahub.vinfastauto.com/glossary/urn:li:glossaryTerm:90343e1f-15de-4625-adc8-a247318d7cbc [E1].`
- **Response flags**: ambiguous=False insufficient_context=False confidence=medium intent=TERM_DEFINITION
- **Resolved entities (1)**: MRP (Material Requirements Planning)
- **Citations**: 1
- **Trace_id**: `0b23f85abce0` | log lines: 5
- **VERDICT**: **PASS**

## FAILURE SUMMARY (by failure type)

| Failure type | Count |
|---|---|
| ENTITY_RESOLUTION_FAILURE | 17 |
| INTENT_FAILURE | 5 |
| REPORT_DISCOVERY_FAILURE | 5 |
| PLANNER_DECOMPOSITION_FAILURE | 4 |
| TOOL_ARGUMENT_FAILURE | 3 |
| DOMAIN_DISAMBIGUATION_FAILURE | 2 |
| EVIDENCE_SELECTION_FAILURE | 2 |
| RETRIEVAL_FAILURE | 1 |
| CONTEXT_PROPAGATION_FAILURE | 1 |
| METRIC_FORMULA_DISCOVERY_FAILURE | 1 |

## FAILURE SUMMARY (by root cause)

| RC | Count | Tests |
|---|---|---|
| RC1b | 7 | B-001, G-002, O-002, T-001, V-001, X-001, CASE3-001 |
| RC2 | 5 | B-002, B-003, F-001, F-002, F-003 |
| RC6 | 5 | H-001, H-002, H-003, CASE2-001, CASE2-002 |
| RC7 | 5 | J-001, M-001, N-001, CASE4-001, CASE6-001 |
| RC4 | 4 | CASE1-001, CASE1-002, E-001, L-001 |
| RC5 | 4 | CASE1-003, CASE5-001, R-001, S-001 |
| RC3 | 3 | C-001, C-002, C-003 |
| RC8 | 3 | G-001, G-003, K-001 |
| RC1a | 2 | A-001, O-001 |
| RC10 | 1 | U-001 |
| RC11 | 1 | W-001 |
| RC9 | 1 | Q-001 |
