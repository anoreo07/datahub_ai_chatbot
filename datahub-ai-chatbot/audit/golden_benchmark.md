# DataAtlas Golden Benchmark

- Schema version: 1.0.0
- Generated: 2026-08-17
- Total tests: 48

| Category | Test ID | Difficulty | Domain | Query |
|---|---|---|---|---|
| A | A-001 | easy | CUNG ỨNG (NĐH) | Tìm dataset có tên chính xác "List of Vendor Master Data" |
| A | A-002 | easy | SẢN XUẤT | Tìm dataset có tên chính xác "Display Plant Stock Availability" |
| A | A-003 | easy | - | Tìm dataset có tên chính xác "Fact_Mrp_Demand" |
| B | B-001 | easy | - | có báo cáo nào về chi phí bảo hành do lỗi nhà cung cấp xảy ra ngoài thị trường không? |
| B | B-002 | easy | - | dataset nào phục vụ kiểm tra WIP giữa MES và SAP? |
| B | B-003 | easy | - | bảng tính dự báo cung cấp hàng tuần theo từng part là dataset nào? |
| C | C-001 | hard | - | có bao nhiêu dataset tên "stas"? |
| C | C-002 | hard | - | có bao nhiêu dataset tên "stko"? |
| C | C-003 | hard | - | có bao nhiêu dataset tên "DIM_PACKED"? |
| CASE1 | CASE1-001 | hard | SẢN XUẤT | Demand là gì? |
| CASE1 | CASE1-002 | hard | SẢN XUẤT | Demand trong domain SẢN XUẤT là gì? |
| CASE1 | CASE1-003 | hard | - | so sánh Demand giữa SẢN XUẤT và KINH DOANH |
| CASE2 | CASE2-001 | medium | LOGISTIC | có báo cáo nào về capacity của nhà cung cấp (vendor) không? |
| CASE2 | CASE2-002 | medium | - | báo cáo capacity cung ứng tuần nào liên quan đến bảng survey capacity từng part? |
| CASE3 | CASE3-001 | hard | - | công thức Coverage Date trong Fact_Inventory_Coverage là gì? |
| CASE4 | CASE4-001 | hard | LOGISTIC | Report_Supply_Capacity lấy dữ liệu từ đâu? Liệt kê theo lineage từ report → dataset → nguồn thô. |
| CASE5 | CASE5-001 | hard | LOGISTIC | từ report capacity → định nghĩa capacity → cột liên quan → công thức → nguồn dữ liệu thô |
| CASE6 | CASE6-001 | hard | LOGISTIC | trong domain LOGISTIC, tìm report về capacity, term liên quan, dataset nguồn và lineage |
| D | D-001 | easy | SẢN XUẤT | "Nhu cầu linh kiện" là gì? |
| D | D-002 | easy | SẢN XUẤT | "Số lượng linh kiện hết hạn" là gì? |
| E | E-001 | hard | - | "Coverage Date" là gì? |
| F | F-001 | medium | - | dataset "VF_VN_DEX_PLANNING.v_ec1v_2025" gắn với glossary term nào? |
| F | F-002 | medium | - | dataset "VF_VN_DEX_PLANNING.mrp_stock_req" gắn với glossary term nào? |
| F | F-003 | medium | - | dataset "dms.stg.stg_contact" gắn với glossary term nào? |
| G | G-001 | medium | - | trong dataset "dim_businessunit" có trường "bu_short_name" nghĩa là gì? |
| G | G-002 | medium | - | trong dataset "fact_sale_orders" có trường "sod_total_amount" nghĩa là gì? |
| G | G-003 | medium | - | trong dataset "dim_plant" có trường "is_manufacturing" nghĩa là gì? |
| H | H-001 | easy | LOGISTIC | có dashboard/report nào tên "Report_Supply_Capacity"? |
| H | H-002 | easy | LOGISTIC | có dashboard/report nào tên "PFEP Report - Hai Phong Factory"? |
| H | H-003 | easy | SẢN XUẤT | có dashboard/report nào tên "VINFAST_Report12 PFEP"? |
| I | I-001 | medium | - | mô tả chi tiết của dashboard "R_Báo cáo đối soát hoá đơn DMS - SAP"? |
| J | J-001 | hard | LOGISTIC | dashboard "Report_Supply_Capacity" dùng những dataset nào làm nguồn? |
| K | K-001 | medium | SẢN XUẤT | "Tính toán “Demand of all build phases per variant”" tính như thế nào? |
| L | L-001 | hard | - | công thức của Coverage Date như trong dữ liệu là gì? |
| M | M-001 | hard | LOGISTIC | trace lineage của dashboard "PFEP Report - Hai Phong Factory" từ nguồn gốc? |
| N | N-001 | hard | SẢN XUẤT | upstream/downstream của dataset "fact_mcn_pfep" là gì? |
| O | O-001 | medium | - | dataset thô (staging) nào chứa dữ liệu đơn hàng bán? |
| O | O-002 | medium | - | dataset staging vật tư (material) trong DMS ở đâu? |
| P | P-001 | medium | - | nó có trường nào? |
| Q | Q-001 | hard | - | còn dashboard nào về PFEP cho nhà máy khác không? |
| R | R-001 | hard | - | so sánh số trường giữa Fact_Mrp_Demand và dim_vehicle_model |
| S | S-001 | hard | - | PFEP là gì và dashboard PFEP nào thuộc domain LOGISTIC? |
| T | T-001 | hard | SẢN XUẤT | tìm dataset tính nhu cầu linh kiện, cho biết trường chính và term định nghĩa liên quan |
| U | U-001 | hard | - | dataset chứa thông tin khách hàng (PII) nào có gắn term về bảo mật? |
| V | V-001 | hard | - | ai là owner của dataset fact_mcr? |
| W | W-001 | medium | TÀI CHÍNH | chỉ nêu báo cáo thuộc domain TÀI CHÍNH về giá thành hoặc ngân sách |
| X | X-001 | medium | - | dataset nào chứa trường 'plant_id'? |
| Y | Y-001 | medium | SẢN XUẤT | "MRP (Material Requirements Planning)" được định nghĩa ở đâu? |
