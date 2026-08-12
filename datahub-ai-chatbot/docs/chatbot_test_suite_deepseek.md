# Chatbot Test Suite — Đánh giá chất lượng trả lời

> Dữ liệu thật từ DataHub (135 redshift datasets, không mock). Câu hỏi từ cơ bản đến phức tạp.

> Tiêu chí đánh giá: **Trả lời đúng trọng tâm**, **Guardrails**, **Trả lời + thực hiện đúng chức năng**.

## Tóm tắt nhanh

- **Fireworks - DeepSeek V4 Flash**: Đạt 25, Đạt một phần 0, Tổng 25 câu

---


## Fireworks - DeepSeek V4 Flash

### Q01 — Term definition
**Câu hỏi:** Term BOM (Bill of Materials) nghĩa là gì?
- **Intent:** `TERM_DEFINITION` | Confidence: `high` | Ambiguous: `False` | Insufficient: `False`
- **Entities:** BOM (Bill of Materials)
- **Citations:** 1 | Lineage down: 0 | up: 0
- **Trả lời:** BOM (Bill of Materials) là danh sách đầy đủ các linh kiện, vật tư cần thiết để sản xuất một sản phẩm [E1].

### Q02 — Term definition
**Câu hỏi:** Term COGS (Cost of Goods Sold) là gì?
- **Intent:** `TERM_DEFINITION` | Confidence: `high` | Ambiguous: `False` | Insufficient: `False`
- **Entities:** COGS (Cost of Goods Sold)
- **Citations:** 1 | Lineage down: 0 | up: 0
- **Trả lời:** COGS (Cost of Goods Sold) là Giá vốn hàng bán, bao gồm chi phí nguyên vật liệu, nhân công và sản xuất [E1].

### Q03 — Term definition
**Câu hỏi:** Term GRN (Goods Received Note) định nghĩa như thế nào?
- **Intent:** `TERM_DEFINITION` | Confidence: `high` | Ambiguous: `False` | Insufficient: `False`
- **Entities:** GRN (Goods Received Note)
- **Citations:** 1 | Lineage down: 0 | up: 0
- **Trả lời:** GRN (Goods Received Note) là biên bản nhận hàng ghi nhận số lượng và tình trạng hàng hóa khi nhập kho [E1].

### Q04 — Term definition
**Câu hỏi:** Term Aging Inventory có ý nghĩa gì trong quản lý kho?
- **Intent:** `GENERAL` | Confidence: `medium` | Ambiguous: `False` | Insufficient: `False`
- **Entities:** -
- **Citations:** 0 | Lineage down: 0 | up: 0
- **Trả lời:** {"type": "object"}

### Q05 — Dataset discovery
**Câu hỏi:** Dataset fact_revenue lưu trữ thông tin gì?
- **Intent:** `GENERAL` | Confidence: `high` | Ambiguous: `False` | Insufficient: `False`
- **Entities:** fact_sales_delivery, fact_test_drive, fact_sales_order, fact_recall, dim_customer, dim_technician, fact_production_order, dim_domestic_vendor
- **Citations:** 8 | Lineage down: 0 | up: 0
- **Trả lời:** I couldn't find this information in the available DataHub metadata.

### Q06 — Dataset discovery
**Câu hỏi:** Dataset dim_product có những trường (field) nào?
- **Intent:** `SCHEMA_LOOKUP` | Confidence: `high` | Ambiguous: `False` | Insufficient: `False`
- **Entities:** dim_product
- **Citations:** 1 | Lineage down: 0 | up: 0
- **Trả lời:** Dataset dim_product có các trường: product_id, model_name, variant, body_type, fuel_type, battery_capacity_kwh, engine_power_hp, seating_capacity, exterior_color, interior_material, standard_warranty_months, base_price, product_status, launch_date, created_at [E1].

### Q07 — Dataset discovery
**Câu hỏi:** Dataset fact_inventory thuộc domain nào và nội dung là gì?
- **Intent:** `ENTITY_DOMAIN` | Confidence: `high` | Ambiguous: `False` | Insufficient: `False`
- **Entities:** fact_inventory
- **Citations:** 1 | Lineage down: 0 | up: 0
- **Trả lời:** Dataset fact_inventory thuộc domain LOGISTIC [E1]. Nội dung là tồn kho hiện tại của từng vật tư tại từng kho [E1].

### Q08 — Owner / Domain
**Câu hỏi:** Ai là người sở hữu dataset dim_product?
- **Intent:** `OWNER_LOOKUP` | Confidence: `high` | Ambiguous: `False` | Insufficient: `False`
- **Entities:** dim_product
- **Citations:** 0 | Lineage down: 0 | up: 0
- **Trả lời:** Dataset dim_product hiện không có người sở hữu (owner).

### Q09 — Owner / Domain
**Câu hỏi:** Dataset fact_goods_issue thuộc domain nào?
- **Intent:** `ENTITY_DOMAIN` | Confidence: `high` | Ambiguous: `False` | Insufficient: `False`
- **Entities:** fact_goods_issue
- **Citations:** 1 | Lineage down: 0 | up: 0
- **Trả lời:** Dataset fact_goods_issue thuộc domain LOGISTIC [E1].

### Q10 — Lineage - simple
**Câu hỏi:** Dataset dim_product lấy dữ liệu từ đâu (upstream)?
- **Intent:** `LINEAGE` | Confidence: `high` | Ambiguous: `False` | Insufficient: `False`
- **Entities:** fact_revenue, fact_standard_cost, fact_production_routing, fact_production_order, fact_production_output, dim_product
- **Citations:** 5 | Lineage down: 5 | up: 0
- **Trả lời:** Dataset dim_product có lineage theo DataHub: 5 downstream: fact_revenue [E1], fact_standard_cost [E2], fact_production_routing [E3], fact_production_order [E4], fact_production_output [E5].

### Q11 — Lineage - simple
**Câu hỏi:** Dataset fact_general_ledger phụ thuộc vào những bảng upstream nào?
- **Intent:** `LINEAGE` | Confidence: `high` | Ambiguous: `False` | Insufficient: `False`
- **Entities:** dim_cost_center, dim_gl_account, dim_profit_center, fact_general_ledger
- **Citations:** 3 | Lineage down: 0 | up: 3
- **Trả lời:** Dataset fact_general_ledger có lineage theo DataHub: 3 upstream: dim_cost_center [E1], dim_gl_account [E2], dim_profit_center [E3].

### Q12 — Schema detail
**Câu hỏi:** Field gross_revenue trong fact_revenue có ý nghĩa gì?
- **Intent:** `SCHEMA_LOOKUP` | Confidence: `high` | Ambiguous: `False` | Insufficient: `False`
- **Entities:** fact_revenue
- **Citations:** 1 | Lineage down: 0 | up: 0
- **Trả lời:** Trường gross_revenue trong fact_revenue có ý nghĩa là Doanh thu gộp [E1].

### Q13 — Lineage - downstream
**Câu hỏi:** Nếu tôi xóa bảng dim_product thì những bảng nào bị ảnh hưởng trực tiếp?
- **Intent:** `GENERAL` | Confidence: `high` | Ambiguous: `False` | Insufficient: `False`
- **Entities:** DC Fast Charger, Balance Sheet, fact_fmea, fact_vendor_scorecard, Vendor Scorecard, Cross-docking, SOR (Statement of Requirements), Residual Value
- **Citations:** 8 | Lineage down: 0 | up: 0
- **Trả lời:** I couldn't find this information in the available DataHub metadata.

### Q14 — Lineage - downstream
**Câu hỏi:** dim_material được sử dụng (downstream) bởi những bảng nào?
- **Intent:** `LINEAGE` | Confidence: `high` | Ambiguous: `False` | Insufficient: `False`
- **Entities:** fact_standard_cost, fact_inventory_movement, fact_lead_time, dim_inventory_category, fact_reorder_alert, fact_inventory_forecast, fact_inventory, fact_physical_inventory, fact_goods_receipt, fact_stock_transfer, fact_material_consumption, fact_goods_issue, fact_purchase_order, dim_material
- **Citations:** 13 | Lineage down: 13 | up: 0
- **Trả lời:** Dataset dim_material có lineage theo DataHub: 13 downstream: fact_standard_cost [E1], fact_inventory_movement [E2], fact_lead_time [E3], dim_inventory_category [E4], fact_reorder_alert [E5], fact_inventory_forecast [E6], fact_inventory [E7], fact_physical_inventory [E8], fact_goods_receipt [E9], fact_stock_transfer [E10], fact_material_consumption [E11], fact_goods_issue [E12], fact_purchase_order [E13].

### Q15 — Lineage - downstream
**Câu hỏi:** Xóa bảng dim_supplier sẽ ảnh hưởng đến các bảng nào?
- **Intent:** `GENERAL` | Confidence: `high` | Ambiguous: `False` | Insufficient: `False`
- **Entities:** Vendor Scorecard, Residual Value, fact_fmea, fact_vendor_scorecard, Balance Sheet, SOR (Statement of Requirements), One Pedal Driving, FMEA (Failure Mode and Effects Analysis)
- **Citations:** 8 | Lineage down: 0 | up: 0
- **Trả lời:** I couldn't find this information in the available DataHub metadata.

### Q16 — Lineage - deep impact
**Câu hỏi:** Xóa dim_assembly_line thì những bảng nào bị ảnh hưởng (kể cả gián tiếp)?
- **Intent:** `GENERAL` | Confidence: `high` | Ambiguous: `False` | Insufficient: `False`
- **Entities:** fact_fmea, Safety Stock, Residual Value, FMEA (Failure Mode and Effects Analysis), DC Fast Charger, dim_engineering_change, fact_recall, MTTR (Mean Time To Repair)
- **Citations:** 8 | Lineage down: 0 | up: 0
- **Trả lời:** Trong metadata hiện có, không tìm thấy thông tin về dataset 'dim_assembly_line' hay bất kỳ lineage nào liên quan. Do đó, không thể xác định bảng nào bị ảnh hưởng khi xóa nó.

### Q17 — Lineage - deep impact
**Câu hỏi:** Xóa bảng dim_plant thì ảnh hưởng đến những bảng nào?
- **Intent:** `GENERAL` | Confidence: `high` | Ambiguous: `False` | Insufficient: `False`
- **Entities:** Residual Value, Balance Sheet, fact_fmea, fact_vendor_scorecard, Vendor Scorecard, SOR (Statement of Requirements), FMEA (Failure Mode and Effects Analysis), fact_recall
- **Citations:** 8 | Lineage down: 0 | up: 0
- **Trả lời:** I couldn't find this information in the available DataHub metadata.

### Q18 — Lineage - deep impact
**Câu hỏi:** Nếu xóa fact_production_order, các bảng nào bị ảnh hưởng?
- **Intent:** `GENERAL` | Confidence: `high` | Ambiguous: `False` | Insufficient: `False`
- **Entities:** fact_production_order
- **Citations:** 1 | Lineage down: 0 | up: 0
- **Trả lời:** I couldn't find this information in the available DataHub metadata. Context chỉ có thông tin về fact_production_order nhưng không có lineage (quan hệ upstream/downstream) để xác định bảng nào bị ảnh hưởng khi xóa.

### Q19 — Composite
**Câu hỏi:** Những dataset nào trong domain TÀI CHÍNH có lineage liên quan đến dim_cost_center?
- **Intent:** `LINEAGE` | Confidence: `high` | Ambiguous: `False` | Insufficient: `False`
- **Entities:** dim_plant, fact_fixed_asset, fact_budget, fact_general_ledger, fact_actual_cost, fact_budget_variance, fact_goods_issue, dim_cost_center
- **Citations:** 7 | Lineage down: 6 | up: 1
- **Trả lời:** Dataset dim_cost_center có lineage theo DataHub: 1 upstream: dim_plant [E1]; 6 downstream: fact_fixed_asset [E2], fact_budget [E3], fact_general_ledger [E4], fact_actual_cost [E5], fact_budget_variance [E6], fact_goods_issue [E7].

### Q20 — Composite
**Câu hỏi:** Bảng nào trong dây chuyền của dim_product thuộc domain LOGISTIC?
- **Intent:** `GENERAL` | Confidence: `high` | Ambiguous: `False` | Insufficient: `False`
- **Entities:** dim_assembly_line, Throughput, dim_warehouse, dim_station, fact_wip_tracking, dim_uom, fact_production_output, fact_inventory
- **Citations:** 8 | Lineage down: 0 | up: 0
- **Trả lời:** I couldn't find this information in the available DataHub metadata.

### Q21 — Advanced impact
**Câu hỏi:** Xóa dim_material thì danh sách đầy đủ các bảng bị ảnh hưởng gồm những bảng nào?
- **Intent:** `GENERAL` | Confidence: `high` | Ambiguous: `False` | Insufficient: `False`
- **Entities:** BOM (Bill of Materials), Vendor Scorecard, Balance Sheet, fact_fmea, fact_vendor_scorecard, Approved Supplier List, SOR (Statement of Requirements), Residual Value
- **Citations:** 8 | Lineage down: 0 | up: 0
- **Trả lời:** Tôi không tìm thấy thông tin về bảng dim_material hoặc lineage của nó trong metadata DataHub hiện có. Do đó, không thể xác định danh sách các bảng bị ảnh hưởng.

### Q22 — Advanced impact
**Câu hỏi:** Nếu xóa dim_warehouse, chuỗi ảnh hưởng dài nhất đến bảng nào và qua những bước nào?
- **Intent:** `GENERAL` | Confidence: `high` | Ambiguous: `False` | Insufficient: `False`
- **Entities:** fact_fmea, Residual Value, FMEA (Failure Mode and Effects Analysis), Routing, Supplier Tier Management, Supply Chain Risk, Drop Shipment, Reorder Point (ROP)
- **Citations:** 8 | Lineage down: 0 | up: 0
- **Trả lời:** I couldn't find this information in the available DataHub metadata. Không có entity nào tên dim_warehouse hoặc thông tin lineage trong ngữ cảnh được cung cấp.

### Q23 — Advanced impact
**Câu hỏi:** Bảng dim_cost_center ảnh hưởng upstream lẫn downstream như thế nào khi bị xóa?
- **Intent:** `LINEAGE` | Confidence: `high` | Ambiguous: `False` | Insufficient: `False`
- **Entities:** dim_plant, fact_fixed_asset, fact_budget, fact_general_ledger, fact_actual_cost, fact_budget_variance, fact_goods_issue, dim_cost_center
- **Citations:** 7 | Lineage down: 6 | up: 1
- **Trả lời:** Dataset dim_cost_center có lineage theo DataHub: 1 upstream: dim_plant [E1]; 6 downstream: fact_fixed_asset [E2], fact_budget [E3], fact_general_ledger [E4], fact_actual_cost [E5], fact_budget_variance [E6], fact_goods_issue [E7].

### Q24 — Synthesis
**Câu hỏi:** Term nào liên quan đến doanh thu và những dataset nào chứa nó?
- **Intent:** `TERM_TO_DATASETS` | Confidence: `high` | Ambiguous: `False` | Insufficient: `False`
- **Entities:** -
- **Citations:** 0 | Lineage down: 0 | up: 0
- **Trả lời:** Không tìm thấy dataset 'lien quan en doanh thu chua no' trong hệ thống DataHub.

### Q25 — Synthesis
**Câu hỏi:** Tổng hợp dữ liệu của bảng dim_supplier tham gia vào dây chuyền nào và ảnh hưởng các bảng nào?
- **Intent:** `GENERAL` | Confidence: `high` | Ambiguous: `False` | Insufficient: `False`
- **Entities:** fact_vendor_scorecard, SOR (Statement of Requirements), Vendor Scorecard, fact_market_share, fact_fmea, fact_telemetry, Residual Value, Balance Sheet
- **Citations:** 8 | Lineage down: 0 | up: 0
- **Trả lời:** I couldn't find this information in the available DataHub metadata.
