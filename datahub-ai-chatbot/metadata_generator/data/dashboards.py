DASHBOARDS = [
    # =========================================================================
    # MANUFACTURING (10 dashboards) - Owner: truong.nguyen@vinfast.vn
    # =========================================================================
    {
        "name": "manufacturing_production_overview",
        "displayName": "Sản Xuất - Tổng Quan Sản Xuất",
        "description": "Real-time production monitoring dashboard showing OEE, throughput, and quality metrics across all assembly lines.",
        "domain": "manufacturing",
        "owner": "truong.nguyen@vinfast.vn",
        "update_frequency": "Real-time (5 min refresh)",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/mfg_production_overview",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/mfg_dashboard.md",
        "tags": ["Manufacturing", "PowerBI", "RealTime", "Critical"],
        "charts": [
            {"name": "production_oee_gauge", "displayName": "OEE Tổng Thể", "chart_type": "LINE", "description": "Current overall equipment effectiveness across all lines"},
            {"name": "throughput_trend", "displayName": "Xu Hướng Thông Qua", "chart_type": "LINE", "description": "Daily throughput trend for past 30 days"},
            {"name": "line_speed_card", "displayName": "Tốc Độ Dây Chuyền", "chart_type": "TEXT", "description": "Real-time line speed in vehicles per hour"},
            {"name": "defect_rate_pie", "displayName": "Tỷ Lệ Lỗi Theo Nhà Máy", "chart_type": "PIE", "description": "Defect rate distribution across plants"}
        ]
    },
    {
        "name": "manufacturing_line_utilization",
        "displayName": "Sản Xuất - Tỷ Lệ Sử Dụng Dây Chuyền",
        "description": "Line utilization rates by shift and product model to identify bottlenecks and underutilized capacity.",
        "domain": "manufacturing",
        "owner": "truong.nguyen@vinfast.vn",
        "update_frequency": "Real-time (5 min refresh)",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/mfg_line_utilization",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/mfg_line_util.md",
        "tags": ["Manufacturing", "PowerBI", "RealTime", "Analytics"],
        "charts": [
            {"name": "utilization_bar", "displayName": "Tỷ Lệ Sử Dụng Theo Dây Chuyền", "chart_type": "BAR", "description": "Utilization percentage by assembly line"},
            {"name": "bottleneck_heatmap", "displayName": "Bản Đồ Nhiệt Nút Cổ Chai", "chart_type": "TABLE", "description": "Heatmap of bottleneck stations by shift"},
            {"name": "idle_time_area", "displayName": "Thời Gian Chờ Theo Ca", "chart_type": "AREA", "description": "Idle time breakdown by shift and reason"},
            {"name": "line_util_gauge", "displayName": "Sử Dụng Mục Tiêu", "chart_type": "LINE", "description": "Line utilization vs target"}
        ]
    },
    {
        "name": "manufacturing_oee_tracking",
        "displayName": "Sản Xuất - Theo Dõi OEE",
        "description": "Detailed OEE tracking with availability, performance, and quality breakdowns by line and shift.",
        "domain": "manufacturing",
        "owner": "truong.nguyen@vinfast.vn",
        "update_frequency": "Daily",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/mfg_oee_tracking",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/mfg_oee.md",
        "tags": ["Manufacturing", "PowerBI", "Critical", "Analytics"],
        "charts": [
            {"name": "oee_trend_line", "displayName": "Xu Hướng OEE", "chart_type": "LINE", "description": "Daily OEE trend for current month"},
            {"name": "availability_pie", "displayName": "Tỷ Lệ Sẵn Sàng", "chart_type": "PIE", "description": "Availability breakdown by downtime category"},
            {"name": "performance_bar", "displayName": "Hiệu Suất Theo Dây Chuyền", "chart_type": "BAR", "description": "Performance rate by line"},
            {"name": "oee_table", "displayName": "Chi Tiết OEE", "chart_type": "TABLE", "description": "Detailed OEE metrics by line and shift"}
        ]
    },
    {
        "name": "manufacturing_quality_defects",
        "displayName": "Sản Xuất - Chất Lượng & Lỗi",
        "description": "Quality defect tracking with Pareto analysis, defect categorization, and trend monitoring.",
        "domain": "manufacturing",
        "owner": "truong.nguyen@vinfast.vn",
        "update_frequency": "Real-time (5 min refresh)",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/mfg_quality_defects",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/mfg_quality.md",
        "tags": ["Manufacturing", "PowerBI", "RealTime", "Critical"],
        "charts": [
            {"name": "defect_pareto", "displayName": "Pareto Lỗi", "chart_type": "BAR", "description": "Pareto chart of defect types"},
            {"name": "defect_trend", "displayName": "Xu Hướng Lỗi", "chart_type": "LINE", "description": "Defect rate trend over time"},
            {"name": "defect_location", "displayName": "Lỗi Theo Vị Trí", "chart_type": "PIE", "description": "Defect distribution by station"},
            {"name": "quality_score_card", "displayName": "Điểm Chất Lượng", "chart_type": "TEXT", "description": "Current quality score"}
        ]
    },
    {
        "name": "manufacturing_scrap_analysis",
        "displayName": "Sản Xuất - Phân Tích Phế Liệu",
        "description": "Scrap material analysis with cost impact, trend analysis, and root cause breakdown.",
        "domain": "manufacturing",
        "owner": "truong.nguyen@vinfast.vn",
        "update_frequency": "Daily",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/mfg_scrap_analysis",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/mfg_scrap.md",
        "tags": ["Manufacturing", "PowerBI", "Analytics", "Transactional"],
        "charts": [
            {"name": "scrap_cost_bar", "displayName": "Chi Phí Phế Liệu Theo Tháng", "chart_type": "BAR", "description": "Monthly scrap cost by material type"},
            {"name": "scrap_rate_trend", "displayName": "Xu Hướng Tỷ Lệ Phế Liệu", "chart_type": "LINE", "description": "Scrap rate trend over 12 months"},
            {"name": "scrap_reason_pie", "displayName": "Nguyên Nhân Phế Liệu", "chart_type": "PIE", "description": "Scrap breakdown by root cause"},
            {"name": "scrap_summary_card", "displayName": "Tổng Quan Phế Liệu", "chart_type": "TEXT", "description": "Total scrap cost and rate summary"},
            {"name": "scrap_detail_table", "displayName": "Chi Tiết Phế Liệu", "chart_type": "TABLE", "description": "Detailed scrap transactions"}
        ]
    },
    {
        "name": "manufacturing_production_plan_vs_actual",
        "displayName": "Sản Xuất - Kế Hoạch vs Thực Tế",
        "description": "Production plan vs actual output comparison with variance analysis and forecast tracking.",
        "domain": "manufacturing",
        "owner": "truong.nguyen@vinfast.vn",
        "update_frequency": "Daily",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/mfg_plan_vs_actual",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/mfg_plan_actual.md",
        "tags": ["Manufacturing", "PowerBI", "Batch", "Analytics"],
        "charts": [
            {"name": "plan_actual_bar", "displayName": "Kế Hoạch vs Thực Tế", "chart_type": "BAR", "description": "Plan vs actual by model and week"},
            {"name": "variance_area", "displayName": "Chênh Lệch Tích Lũy", "chart_type": "AREA", "description": "Cumulative variance over month"},
            {"name": "achievement_gauge", "displayName": "Tỷ Lệ Hoàn Thành", "chart_type": "LINE", "description": "Production achievement percentage"},
            {"name": "forecast_actual_scatter", "displayName": "Dự Báo vs Thực Tế", "chart_type": "SCATTER", "description": "Forecast accuracy scatter plot"}
        ]
    },
    {
        "name": "manufacturing_shift_performance",
        "displayName": "Sản Xuất - Hiệu Suất Ca Làm Việc",
        "description": "Shift-level performance comparison showing output, quality, and efficiency by shift team.",
        "domain": "manufacturing",
        "owner": "truong.nguyen@vinfast.vn",
        "update_frequency": "Daily",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/mfg_shift_performance",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/mfg_shift.md",
        "tags": ["Manufacturing", "PowerBI", "Analytics", "Transactional"],
        "charts": [
            {"name": "shift_output_bar", "displayName": "Sản Lượng Theo Ca", "chart_type": "BAR", "description": "Output comparison by shift"},
            {"name": "shift_quality_line", "displayName": "Chất Lượng Theo Ca", "chart_type": "LINE", "description": "Defect rate by shift over time"},
            {"name": "shift_efficiency_table", "displayName": "Hiệu Suất Ca", "chart_type": "TABLE", "description": "Efficiency metrics by shift team"},
            {"name": "top_performer_card", "displayName": "Ca Xuất Sắc Nhất", "chart_type": "TEXT", "description": "Current top-performing shift"}
        ]
    },
    {
        "name": "manufacturing_work_center_efficiency",
        "displayName": "Sản Xuất - Hiệu Quả Trung Tâm Làm Việc",
        "description": "Efficiency analysis by work center with cycle time, setup time, and throughput metrics.",
        "domain": "manufacturing",
        "owner": "truong.nguyen@vinfast.vn",
        "update_frequency": "Daily",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/mfg_work_center_eff",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/mfg_wc_eff.md",
        "tags": ["Manufacturing", "PowerBI", "Analytics", "Certified"],
        "charts": [
            {"name": "cycle_time_bar", "displayName": "Thời Gian Chu Kỳ Theo Trung Tâm", "chart_type": "BAR", "description": "Average cycle time by work center"},
            {"name": "setup_time_trend", "displayName": "Xu Hướng Thời Gian Thiết Lập", "chart_type": "LINE", "description": "Setup time trend over weeks"},
            {"name": "throughput_scatter", "displayName": "Thông Qua vs Hiệu Suất", "chart_type": "SCATTER", "description": "Throughput vs efficiency scatter plot"},
            {"name": "wc_summary_gauge", "displayName": "Tổng Quan Trung Tâm", "chart_type": "LINE", "description": "Work center composite score"}
        ]
    },
    {
        "name": "manufacturing_maintenance_calendar",
        "displayName": "Sản Xuất - Lịch Bảo Trì",
        "description": "Planned and unplanned maintenance calendar with downtime impact and work order tracking.",
        "domain": "manufacturing",
        "owner": "truong.nguyen@vinfast.vn",
        "update_frequency": "Real-time (15 min refresh)",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/mfg_maintenance_cal",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/mfg_maintenance.md",
        "tags": ["Manufacturing", "PowerBI", "RealTime", "Batch"],
        "charts": [
            {"name": "maintenance_timeline", "displayName": "Dòng Thời Gian Bảo Trì", "chart_type": "TABLE", "description": "Scheduled maintenance events timeline"},
            {"name": "downtime_impact_bar", "displayName": "Tác Động Dừng Máy", "chart_type": "BAR", "description": "Downtime hours by equipment"},
            {"name": "work_order_status_pie", "displayName": "Trạng Thái Lệnh Bảo Trì", "chart_type": "PIE", "description": "Work order status distribution"},
            {"name": "mtbf_card", "displayName": "MTBF Trung Bình", "chart_type": "TEXT", "description": "Mean time between failures"},
            {"name": "maintenance_cost_area", "displayName": "Chi Phí Bảo Trì", "chart_type": "AREA", "description": "Maintenance cost trend"}
        ]
    },
    {
        "name": "manufacturing_capacity_utilization",
        "displayName": "Sản Xuất - Sử Dụng Công Suất",
        "description": "Capacity utilization analysis across plants and lines with bottleneck identification and what-if scenarios.",
        "domain": "manufacturing",
        "owner": "truong.nguyen@vinfast.vn",
        "update_frequency": "Daily",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/mfg_capacity_util",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/mfg_capacity.md",
        "tags": ["Manufacturing", "PowerBI", "Analytics", "Gold"],
        "charts": [
            {"name": "capacity_bar", "displayName": "Công Suất Theo Nhà Máy", "chart_type": "BAR", "description": "Capacity utilization by plant"},
            {"name": "bottleneck_funnel", "displayName": "Phân Tích Nút Cổ Chai", "chart_type": "BAR", "description": "Bottleneck identification funnel"},
            {"name": "capacity_forecast_line", "displayName": "Dự Báo Công Suất", "chart_type": "LINE", "description": "Capacity forecast vs demand"},
            {"name": "utilization_map", "displayName": "Bản Đồ Sử Dụng", "chart_type": "SCATTER", "description": "Geographic capacity utilization map"}
        ]
    },

    # =========================================================================
    # LOGISTICS (10 dashboards) - Owner: anh.tran@vinfast.vn
    # =========================================================================
    {
        "name": "logistics_inventory_overview",
        "displayName": "Logistics - Tổng Quan Hàng Tồn Kho",
        "description": "Real-time inventory snapshot with stock levels, value, and movement across all warehouses.",
        "domain": "logistics",
        "owner": "anh.tran@vinfast.vn",
        "update_frequency": "Real-time (5 min refresh)",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/log_inventory_overview",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/log_inventory.md",
        "tags": ["SupplyChain", "PowerBI", "RealTime", "Critical"],
        "charts": [
            {"name": "inventory_value_card", "displayName": "Giá Trị Tồn Kho", "chart_type": "TEXT", "description": "Total inventory value in VND"},
            {"name": "stock_level_bar", "displayName": "Mức Tồn Theo Kho", "chart_type": "BAR", "description": "Stock levels by warehouse"},
            {"name": "inventory_mix_pie", "displayName": "Cơ Cấu Hàng Tồn", "chart_type": "PIE", "description": "Inventory mix by category"},
            {"name": "stock_trend_area", "displayName": "Xu Hướng Tồn Kho", "chart_type": "AREA", "description": "Inventory trend over 90 days"}
        ]
    },
    {
        "name": "logistics_warehouse_utilization",
        "displayName": "Logistics - Sử Dụng Kho",
        "description": "Warehouse space utilization, slot occupancy, and storage efficiency by facility.",
        "domain": "logistics",
        "owner": "anh.tran@vinfast.vn",
        "update_frequency": "Daily",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/log_warehouse_util",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/log_warehouse.md",
        "tags": ["SupplyChain", "PowerBI", "Analytics", "Transactional"],
        "charts": [
            {"name": "space_util_gauge", "displayName": "Sử Dụng Không Gian Kho", "chart_type": "LINE", "description": "Warehouse space utilization rate"},
            {"name": "slot_occ_bar", "displayName": "Tỷ Lệ Lấp Đầy Kệ", "chart_type": "BAR", "description": "Slot occupancy by warehouse zone"},
            {"name": "warehouse_map", "displayName": "Bản Đồ Kho", "chart_type": "SCATTER", "description": "Geographic warehouse locations and utilization"},
            {"name": "storage_eff_table", "displayName": "Hiệu Suất Lưu Trữ", "chart_type": "TABLE", "description": "Storage efficiency metrics by facility"}
        ]
    },
    {
        "name": "logistics_stock_movement",
        "displayName": "Logistics - Biến Động Hàng Tồn",
        "description": "Stock movement tracking with receipts, issues, transfers, and adjustments across all locations.",
        "domain": "logistics",
        "owner": "anh.tran@vinfast.vn",
        "update_frequency": "Real-time (15 min refresh)",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/log_stock_movement",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/log_stock_mvmt.md",
        "tags": ["SupplyChain", "PowerBI", "RealTime", "Transactional"],
        "charts": [
            {"name": "movement_sankey", "displayName": "Luồng Biến Động", "chart_type": "AREA", "description": "Stock movement flow between locations"},
            {"name": "receipts_issues_bar", "displayName": "Nhập Xuất Theo Ngày", "chart_type": "BAR", "description": "Daily receipts vs issues"},
            {"name": "adjustments_line", "displayName": "Điều Chỉnh Tồn Kho", "chart_type": "LINE", "description": "Inventory adjustments trend"},
            {"name": "movement_summary_card", "displayName": "Tổng Quan Biến Động", "chart_type": "TEXT", "description": "Total movements today"}
        ]
    },
    {
        "name": "logistics_inbound_delivery_tracking",
        "displayName": "Logistics - Theo Dõi Giao Hàng Đến",
        "description": "Inbound delivery tracking with ETA monitoring, dock scheduling, and receiving performance.",
        "domain": "logistics",
        "owner": "anh.tran@vinfast.vn",
        "update_frequency": "Real-time (5 min refresh)",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/log_inbound_tracking",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/log_inbound.md",
        "tags": ["SupplyChain", "PowerBI", "RealTime", "Critical"],
        "charts": [
            {"name": "inbound_eta_table", "displayName": "Lịch Giao Hàng Đến", "chart_type": "TABLE", "description": "Inbound deliveries with ETA"},
            {"name": "on_time_rate_gauge", "displayName": "Tỷ Lệ Đúng Giờ", "chart_type": "LINE", "description": "Inbound on-time delivery rate"},
            {"name": "dock_util_bar", "displayName": "Sử Dụng Bến Đỗ", "chart_type": "BAR", "description": "Dock utilization by time slot"},
            {"name": "receiving_time_line", "displayName": "Thời Gian Nhận Hàng", "chart_type": "LINE", "description": "Average receiving time trend"},
            {"name": "inbound_volume_area", "displayName": "Khối Lượng Hàng Đến", "chart_type": "AREA", "description": "Inbound volume by week"}
        ]
    },
    {
        "name": "logistics_outbound_dashboard",
        "displayName": "Logistics - Giao Hàng Đi",
        "description": "Outbound shipment tracking with loading performance, dispatch accuracy, and delivery confirmation.",
        "domain": "logistics",
        "owner": "anh.tran@vinfast.vn",
        "update_frequency": "Real-time (5 min refresh)",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/log_outbound",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/log_outbound.md",
        "tags": ["SupplyChain", "PowerBI", "RealTime", "Transactional"],
        "charts": [
            {"name": "outbound_volume_bar", "displayName": "Khối Lượng Giao Hàng", "chart_type": "BAR", "description": "Outbound shipments by day"},
            {"name": "dispatch_accuracy_pie", "displayName": "Độ Chính Xác Giao Hàng", "chart_type": "PIE", "description": "Dispatch accuracy breakdown"},
            {"name": "loading_time_trend", "displayName": "Thời Gian Xếp Hàng", "chart_type": "LINE", "description": "Loading time trend"},
            {"name": "delivery_status_card", "displayName": "Trạng Thái Giao Hàng", "chart_type": "TEXT", "description": "Current delivery status summary"}
        ]
    },
    {
        "name": "logistics_inventory_turnover",
        "displayName": "Logistics - Vòng Quay Hàng Tồn Kho",
        "description": "Inventory turnover analysis by category and warehouse with slow-moving and dead stock identification.",
        "domain": "logistics",
        "owner": "anh.tran@vinfast.vn",
        "update_frequency": "Weekly",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/log_inv_turnover",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/log_turnover.md",
        "tags": ["SupplyChain", "PowerBI", "Analytics", "Gold"],
        "charts": [
            {"name": "turnover_ratio_bar", "displayName": "Tỷ Lệ Vòng Quay Theo Danh Mục", "chart_type": "BAR", "description": "Turnover ratio by category"},
            {"name": "slow_mover_pie", "displayName": "Hàng Di Chuyển Chậm", "chart_type": "PIE", "description": "Slow-moving stock composition"},
            {"name": "dead_stock_card", "displayName": "Giá Trị Hàng Chết", "chart_type": "TEXT", "description": "Dead stock value"},
            {"name": "turnover_trend_line", "displayName": "Xu Hướng Vòng Quay", "chart_type": "LINE", "description": "Turnover ratio trend"}
        ]
    },
    {
        "name": "logistics_aging_analysis",
        "displayName": "Logistics - Phân Tích Tuổi Hàng Tồn",
        "description": "Inventory aging analysis with aging buckets, potential obsolescence, and write-off risk assessment.",
        "domain": "logistics",
        "owner": "anh.tran@vinfast.vn",
        "update_frequency": "Weekly",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/log_aging_analysis",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/log_aging.md",
        "tags": ["SupplyChain", "PowerBI", "Analytics", "Critical"],
        "charts": [
            {"name": "aging_buckets_bar", "displayName": "Phân Bố Tuổi Hàng Tồn", "chart_type": "BAR", "description": "Inventory aging bucket distribution"},
            {"name": "obsolescence_risk_funnel", "displayName": "Rủi Ro Lỗi Thời", "chart_type": "BAR", "description": "Obsolescence risk funnel"},
            {"name": "aging_detail_table", "displayName": "Chi Tiết Tuổi Hàng", "chart_type": "TABLE", "description": "Aging detail by SKU"},
            {"name": "writeoff_estimate_card", "displayName": "Dự Phòng Xóa Sổ", "chart_type": "TEXT", "description": "Estimated write-off value"}
        ]
    },
    {
        "name": "logistics_supplier_delivery_performance",
        "displayName": "Logistics - Hiệu Suất Giao Hàng Nhà Cung Cấp",
        "description": "Supplier delivery performance tracking with OTIF metrics, lead time analysis, and compliance scoring.",
        "domain": "logistics",
        "owner": "anh.tran@vinfast.vn",
        "update_frequency": "Weekly",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/log_supplier_perf",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/log_supplier_perf.md",
        "tags": ["SupplyChain", "PowerBI", "Analytics", "SAP"],
        "charts": [
            {"name": "otif_gauge", "displayName": "OTIF Tổng Thể", "chart_type": "LINE", "description": "On-time in-full rate"},
            {"name": "supplier_score_bar", "displayName": "Điểm Nhà Cung Cấp", "chart_type": "BAR", "description": "Supplier performance scores"},
            {"name": "lead_time_trend", "displayName": "Xu Hướng Thời Gian Giao Hàng", "chart_type": "LINE", "description": "Average lead time by supplier"},
            {"name": "compliance_table", "displayName": "Tuân Thủ Giao Hàng", "chart_type": "TABLE", "description": "Supplier compliance details"}
        ]
    },
    {
        "name": "logistics_cross_dock_operations",
        "displayName": "Logistics - Vận Hành Cross-Dock",
        "description": "Cross-dock operations monitoring with throughput, dock-to-stock time, and staging efficiency.",
        "domain": "logistics",
        "owner": "anh.tran@vinfast.vn",
        "update_frequency": "Real-time (15 min refresh)",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/log_crossdock",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/log_crossdock.md",
        "tags": ["SupplyChain", "PowerBI", "RealTime", "Transactional"],
        "charts": [
            {"name": "crossdock_throughput_bar", "displayName": "Thông Qua Cross-Dock", "chart_type": "BAR", "description": "Hourly cross-dock throughput"},
            {"name": "dock_to_stock_line", "displayName": "Thời Gian Dock-to-Stock", "chart_type": "LINE", "description": "Dock-to-stock time trend"},
            {"name": "staging_util_pie", "displayName": "Sử Dụng Khu Vực Xếp Hàng", "chart_type": "PIE", "description": "Staging area utilization"},
            {"name": "crossdock_summary_card", "displayName": "Tổng Quan Cross-Dock", "chart_type": "TEXT", "description": "Today's cross-dock volume"}
        ]
    },
    {
        "name": "logistics_material_flow_analysis",
        "displayName": "Logistics - Phân Tích Luồng Vật Tư",
        "description": "End-to-end material flow analysis from supplier receipt to production consumption with cycle time mapping.",
        "domain": "logistics",
        "owner": "anh.tran@vinfast.vn",
        "update_frequency": "Daily",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/log_material_flow",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/log_material_flow.md",
        "tags": ["SupplyChain", "PowerBI", "Analytics", "Silver"],
        "charts": [
            {"name": "flow_cycle_bar", "displayName": "Thời Gian Chu Kỳ Luồng", "chart_type": "BAR", "description": "Cycle time by material flow stage"},
            {"name": "material_scatter", "displayName": "Phân Tán Vật Tư", "chart_type": "SCATTER", "description": "Material flow volume vs velocity"},
            {"name": "flow_diagram_table", "displayName": "Sơ Đồ Luồng", "chart_type": "TABLE", "description": "Material flow mapping table"},
            {"name": "bottleneck_gauge", "displayName": "Nút Cổ Chai Luồng", "chart_type": "LINE", "description": "Flow bottleneck indicator"},
            {"name": "flow_trend_area", "displayName": "Xu Hướng Luồng Vật Tư", "chart_type": "AREA", "description": "Material flow volume trend"}
        ]
    },

    # =========================================================================
    # FINANCE (10 dashboards) - Owner: thuy.nguyen@vinfast.vn
    # =========================================================================
    {
        "name": "finance_pnl_overview",
        "displayName": "Tài Chính - Tổng Quan P&L",
        "description": "Profit and loss summary with revenue, COGS, gross margin, and operating expense tracking.",
        "domain": "finance",
        "owner": "thuy.nguyen@vinfast.vn",
        "update_frequency": "Daily",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/fin_pnl_overview",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/fin_pnl.md",
        "tags": ["Finance", "PowerBI", "Critical", "Analytics"],
        "charts": [
            {"name": "revenue_trend_line", "displayName": "Xu Hướng Doanh Thu", "chart_type": "LINE", "description": "Daily revenue trend"},
            {"name": "gross_margin_gauge", "displayName": "Biên Lợi Nhuận Gộp", "chart_type": "LINE", "description": "Current gross margin percentage"},
            {"name": "expense_breakdown_pie", "displayName": "Cơ Cấu Chi Phí", "chart_type": "PIE", "description": "Operating expense breakdown"},
            {"name": "pnl_summary_card", "displayName": "Tóm Tắt P&L", "chart_type": "TEXT", "description": "Net profit summary"},
            {"name": "revenue_vs_budget_bar", "displayName": "Doanh Thu vs Ngân Sách", "chart_type": "BAR", "description": "Revenue comparison vs budget"}
        ]
    },
    {
        "name": "finance_cash_flow_dashboard",
        "displayName": "Tài Chính - Dòng Tiền",
        "description": "Cash flow monitoring with operating, investing, and financing cash flows and forecast.",
        "domain": "finance",
        "owner": "thuy.nguyen@vinfast.vn",
        "update_frequency": "Daily",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/fin_cashflow",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/fin_cashflow.md",
        "tags": ["Finance", "PowerBI", "Critical", "RealTime"],
        "charts": [
            {"name": "cash_balance_card", "displayName": "Số Dư Tiền Mặt", "chart_type": "TEXT", "description": "Current cash balance"},
            {"name": "cash_flow_area", "displayName": "Dòng Tiền Thuần", "chart_type": "AREA", "description": "Net cash flow over time"},
            {"name": "cash_components_bar", "displayName": "Cấu Phần Dòng Tiền", "chart_type": "BAR", "description": "Operating vs investing vs financing"},
            {"name": "cash_forecast_line", "displayName": "Dự Báo Dòng Tiền", "chart_type": "LINE", "description": "Cash flow forecast 13 weeks"}
        ]
    },
    {
        "name": "finance_budget_variance",
        "displayName": "Tài Chính - Chênh Lệch Ngân Sách",
        "description": "Budget vs actual variance analysis by cost center and account with drill-down capability.",
        "domain": "finance",
        "owner": "thuy.nguyen@vinfast.vn",
        "update_frequency": "Monthly",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/fin_budget_variance",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/fin_budget.md",
        "tags": ["Finance", "PowerBI", "Analytics", "SAP"],
        "charts": [
            {"name": "variance_bar", "displayName": "Chênh Lệch Theo Bộ Phận", "chart_type": "BAR", "description": "Budget variance by department"},
            {"name": "variance_percent_gauge", "displayName": "Tỷ Lệ Chênh Lệch", "chart_type": "LINE", "description": "Overall variance percentage"},
            {"name": "budget_detail_table", "displayName": "Chi Tiết Ngân Sách", "chart_type": "TABLE", "description": "Budget vs actual line items"},
            {"name": "spending_trend_line", "displayName": "Xu Hướng Chi Tiêu", "chart_type": "LINE", "description": "Monthly spending trend vs budget"}
        ]
    },
    {
        "name": "finance_cost_center_analysis",
        "displayName": "Tài Chính - Phân Tích Trung Tâm Chi Phí",
        "description": "Cost center performance analysis with cost allocation, benchmark comparison, and efficiency metrics.",
        "domain": "finance",
        "owner": "thuy.nguyen@vinfast.vn",
        "update_frequency": "Monthly",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/fin_cost_center",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/fin_cost_ctr.md",
        "tags": ["Finance", "PowerBI", "Analytics", "Certified"],
        "charts": [
            {"name": "cost_allocation_pie", "displayName": "Phân Bổ Chi Phí", "chart_type": "PIE", "description": "Cost allocation by department"},
            {"name": "cost_per_unit_bar", "displayName": "Chi Phí Trên Đơn Vị", "chart_type": "BAR", "description": "Cost per unit by cost center"},
            {"name": "benchmark_scatter", "displayName": "So Sánh Chuẩn", "chart_type": "SCATTER", "description": "Cost center benchmark scatter"},
            {"name": "efficiency_score_card", "displayName": "Điểm Hiệu Quả", "chart_type": "TEXT", "description": "Cost efficiency score"}
        ]
    },
    {
        "name": "finance_accounts_payable_aging",
        "displayName": "Tài Chính - Tuổi Nợ Phải Trả",
        "description": "AP aging analysis with payment terms compliance, due date tracking, and cash discount opportunities.",
        "domain": "finance",
        "owner": "thuy.nguyen@vinfast.vn",
        "update_frequency": "Daily",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/fin_ap_aging",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/fin_ap.md",
        "tags": ["Finance", "PowerBI", "Critical", "SAP"],
        "charts": [
            {"name": "ap_aging_buckets", "displayName": "Phân Bố Tuổi Nợ AP", "chart_type": "BAR", "description": "AP aging bucket distribution"},
            {"name": "overdue_pie", "displayName": "Nợ Quá Hạn", "chart_type": "PIE", "description": "Overdue AP by vendor"},
            {"name": "payment_due_table", "displayName": "Hóa Đơn Đến Hạn", "chart_type": "TABLE", "description": "Upcoming payment due list"},
            {"name": "discount_opportunity_card", "displayName": "Cơ Hội Chiết Khấu", "chart_type": "TEXT", "description": "Available cash discount amount"}
        ]
    },
    {
        "name": "finance_accounts_receivable_tracking",
        "displayName": "Tài Chính - Theo Dõi Khoản Phải Thu",
        "description": "AR tracking dashboard with collection efficiency, DSO monitoring, and aging analysis.",
        "domain": "finance",
        "owner": "thuy.nguyen@vinfast.vn",
        "update_frequency": "Daily",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/fin_ar_tracking",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/fin_ar.md",
        "tags": ["Finance", "PowerBI", "Critical", "RealTime"],
        "charts": [
            {"name": "dso_gauge", "displayName": "DSO Hiện Tại", "chart_type": "LINE", "description": "Days sales outstanding"},
            {"name": "ar_aging_bar", "displayName": "Tuổi Khoản Phải Thu", "chart_type": "BAR", "description": "AR aging buckets"},
            {"name": "collection_eff_line", "displayName": "Hiệu Suất Thu Hồi", "chart_type": "LINE", "description": "Collection efficiency trend"},
            {"name": "ar_summary_card", "displayName": "Tổng AR", "chart_type": "TEXT", "description": "Total accounts receivable"}
        ]
    },
    {
        "name": "finance_working_capital",
        "displayName": "Tài Chính - Vốn Lưu Động",
        "description": "Working capital analysis with current ratio, quick ratio, and cash conversion cycle monitoring.",
        "domain": "finance",
        "owner": "thuy.nguyen@vinfast.vn",
        "update_frequency": "Weekly",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/fin_working_capital",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/fin_wc.md",
        "tags": ["Finance", "PowerBI", "Analytics", "Gold"],
        "charts": [
            {"name": "current_ratio_gauge", "displayName": "Tỷ Số Thanh Toán Hiện Hành", "chart_type": "LINE", "description": "Current ratio"},
            {"name": "ccc_trend_line", "displayName": "Chu Kỳ Chuyển Đổi Tiền Mặt", "chart_type": "LINE", "description": "Cash conversion cycle trend"},
            {"name": "wc_components_area", "displayName": "Cấu Phần Vốn Lưu Động", "chart_type": "AREA", "description": "AR, AP, Inventory components"},
            {"name": "wc_summary_table", "displayName": "Tổng Quan Vốn Lưu Động", "chart_type": "TABLE", "description": "Working capital KPIs"}
        ]
    },
    {
        "name": "finance_capital_expenditure",
        "displayName": "Tài Chính - Chi Tiêu Vốn",
        "description": "CapEx tracking with budget consumption, project spending, and ROI analysis.",
        "domain": "finance",
        "owner": "thuy.nguyen@vinfast.vn",
        "update_frequency": "Monthly",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/fin_capex",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/fin_capex.md",
        "tags": ["Finance", "PowerBI", "Analytics", "Confidential"],
        "charts": [
            {"name": "capex_budget_bar", "displayName": "Ngân Sách CAPEX Theo Dự Án", "chart_type": "BAR", "description": "CapEx budget vs spend by project"},
            {"name": "roi_scatter", "displayName": "ROI Dự Án", "chart_type": "SCATTER", "description": "Project ROI analysis"},
            {"name": "capex_forecast_line", "displayName": "Dự Báo CAPEX", "chart_type": "LINE", "description": "CapEx forecast remainder"},
            {"name": "project_status_pie", "displayName": "Trạng Thái Dự Án", "chart_type": "PIE", "description": "Capital project status distribution"}
        ]
    },
    {
        "name": "finance_tax_provision",
        "displayName": "Tài Chính - Dự Phòng Thuế",
        "description": "Tax provision tracking with deferred tax, current tax liability, and compliance calendar.",
        "domain": "finance",
        "owner": "thuy.nguyen@vinfast.vn",
        "update_frequency": "Quarterly",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/fin_tax_provision",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/fin_tax.md",
        "tags": ["Finance", "PowerBI", "Regulatory", "Confidential"],
        "charts": [
            {"name": "tax_liability_card", "displayName": "Nợ Thuế Hiện Tại", "chart_type": "TEXT", "description": "Current tax liability"},
            {"name": "deferred_tax_area", "displayName": "Thuế Hoãn Lại", "chart_type": "AREA", "description": "Deferred tax trend"},
            {"name": "tax_breakdown_pie", "displayName": "Cơ Cấu Thuế", "chart_type": "PIE", "description": "Tax breakdown by type"},
            {"name": "compliance_calendar_table", "displayName": "Lịch Tuân Thủ Thuế", "chart_type": "TABLE", "description": "Tax filing and payment calendar"},
            {"name": "effective_rate_line", "displayName": "Thuế Suất Hiệu Dụng", "chart_type": "LINE", "description": "Effective tax rate trend"}
        ]
    },
    {
        "name": "finance_financial_ratios",
        "displayName": "Tài Chính - Chỉ Số Tài Chính",
        "description": "Comprehensive financial ratios dashboard covering liquidity, solvency, profitability, and efficiency metrics.",
        "domain": "finance",
        "owner": "thuy.nguyen@vinfast.vn",
        "update_frequency": "Monthly",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/fin_ratios",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/fin_ratios.md",
        "tags": ["Finance", "PowerBI", "Analytics", "Gold"],
        "charts": [
            {"name": "profitability_gauges", "displayName": "Chỉ Số Lợi Nhuận", "chart_type": "LINE", "description": "ROE, ROA, ROS gauges"},
            {"name": "liquidity_line", "displayName": "Chỉ Số Thanh Khoản", "chart_type": "LINE", "description": "Current and quick ratio trend"},
            {"name": "solvency_bar", "displayName": "Chỉ Số Khả Năng Thanh Toán", "chart_type": "BAR", "description": "Debt-to-equity and interest coverage"},
            {"name": "ratio_table", "displayName": "Bảng Chỉ Số", "chart_type": "TABLE", "description": "All financial ratios summary"}
        ]
    },

    # =========================================================================
    # SUPPLY CHAIN (10 dashboards) - Owner: cuong.vo@vinfast.vn
    # =========================================================================
    {
        "name": "supply_chain_procurement_spend",
        "displayName": "Chuỗi Cung Ứng - Chi Tiêu Mua Hàng",
        "description": "Procurement spend analysis by category, supplier, and business unit with savings tracking.",
        "domain": "supply_chain",
        "owner": "cuong.vo@vinfast.vn",
        "update_frequency": "Weekly",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/sc_procurement_spend",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/sc_spend.md",
        "tags": ["SupplyChain", "PowerBI", "Analytics", "SAP"],
        "charts": [
            {"name": "spend_by_category_bar", "displayName": "Chi Tiêu Theo Danh Mục", "chart_type": "BAR", "description": "Spend breakdown by category"},
            {"name": "top_suppliers_pie", "displayName": "Top Nhà Cung Cấp", "chart_type": "PIE", "description": "Spend distribution by supplier"},
            {"name": "savings_card", "displayName": "Tiết Kiệm Chi Phí", "chart_type": "TEXT", "description": "Total procurement savings YTD"},
            {"name": "spend_trend_line", "displayName": "Xu Hướng Chi Tiêu", "chart_type": "LINE", "description": "Monthly spend trend"},
            {"name": "spend_detail_table", "displayName": "Chi Tiết Chi Tiêu", "chart_type": "TABLE", "description": "Detailed procurement transactions"}
        ]
    },
    {
        "name": "supply_chain_supplier_scorecard",
        "displayName": "Chuỗi Cung Ứng - Thẻ Điểm Nhà Cung Cấp",
        "description": "Supplier scorecard with quality, delivery, cost, and sustainability dimensions.",
        "domain": "supply_chain",
        "owner": "cuong.vo@vinfast.vn",
        "update_frequency": "Monthly",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/sc_supplier_scorecard",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/sc_scorecard.md",
        "tags": ["SupplyChain", "PowerBI", "Analytics", "Certified"],
        "charts": [
            {"name": "scorecard_radar", "displayName": "Điểm Tổng Thể Nhà Cung Cấp", "chart_type": "TABLE", "description": "Supplier scorecard dimensions"},
            {"name": "quality_score_bar", "displayName": "Điểm Chất Lượng", "chart_type": "BAR", "description": "Quality scores by supplier"},
            {"name": "delivery_rate_gauge", "displayName": "Tỷ Lệ Giao Hàng Đúng Hẹn", "chart_type": "LINE", "description": "On-time delivery rate"},
            {"name": "score_trend_line", "displayName": "Xu Hướng Điểm", "chart_type": "LINE", "description": "Supplier score trend over time"}
        ]
    },
    {
        "name": "supply_chain_contract_coverage",
        "displayName": "Chuỗi Cung Ứng - Bảo Phủ Hợp Đồng",
        "description": "Contract coverage analysis with spend under management, contract compliance, and renewal tracking.",
        "domain": "supply_chain",
        "owner": "cuong.vo@vinfast.vn",
        "update_frequency": "Monthly",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/sc_contract_coverage",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/sc_contract.md",
        "tags": ["SupplyChain", "PowerBI", "Analytics", "Confidential"],
        "charts": [
            {"name": "coverage_pie", "displayName": "Tỷ Lệ Bảo Phủ Hợp Đồng", "chart_type": "PIE", "description": "Spend under contract vs non-contract"},
            {"name": "compliance_gauge", "displayName": "Tuân Thủ Hợp Đồng", "chart_type": "LINE", "description": "Contract compliance rate"},
            {"name": "renewal_calendar_table", "displayName": "Lịch Gia Hạn", "chart_type": "TABLE", "description": "Upcoming contract renewals"},
            {"name": "savings_opp_bar", "displayName": "Cơ Hội Tiết Kiệm", "chart_type": "BAR", "description": "Savings opportunities by category"}
        ]
    },
    {
        "name": "supply_chain_sourcing_pipeline",
        "displayName": "Chuỗi Cung Ứng - Kênh Tìm Nguồn Cung",
        "description": "Strategic sourcing pipeline tracking from RFP to contract award with milestone monitoring.",
        "domain": "supply_chain",
        "owner": "cuong.vo@vinfast.vn",
        "update_frequency": "Weekly",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/sc_sourcing_pipeline",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/sc_sourcing.md",
        "tags": ["SupplyChain", "PowerBI", "Transactional", "Internal"],
        "charts": [
            {"name": "pipeline_funnel", "displayName": "Kênh Tìm Nguồn Cung", "chart_type": "BAR", "description": "Sourcing pipeline stages funnel"},
            {"name": "rfp_timeline_bar", "displayName": "Dòng Thời Gian RFP", "chart_type": "BAR", "description": "RFP stages duration"},
            {"name": "pipeline_value_card", "displayName": "Giá Trị Kênh", "chart_type": "TEXT", "description": "Total pipeline value"},
            {"name": "sourcing_detail_table", "displayName": "Chi Tiết Tìm Nguồn Cung", "chart_type": "TABLE", "description": "Active sourcing events"}
        ]
    },
    {
        "name": "supply_chain_commodity_price_tracker",
        "displayName": "Chuỗi Cung Ứng - Theo Dõi Giá Hàng Hóa",
        "description": "Real-time commodity price tracking for steel, copper, rubber, and other key raw materials.",
        "domain": "supply_chain",
        "owner": "cuong.vo@vinfast.vn",
        "update_frequency": "Real-time (1 hour refresh)",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/sc_commodity_prices",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/sc_commodity.md",
        "tags": ["SupplyChain", "PowerBI", "RealTime", "Critical"],
        "charts": [
            {"name": "price_index_line", "displayName": "Chỉ Số Giá Hàng Hóa", "chart_type": "LINE", "description": "Commodity price index trend"},
            {"name": "steel_price_card", "displayName": "Giá Thép", "chart_type": "TEXT", "description": "Current steel price"},
            {"name": "rubber_trend_area", "displayName": "Xu Hướng Giá Cao Su", "chart_type": "AREA", "description": "Rubber price trend"},
            {"name": "price_comparison_bar", "displayName": "So Sánh Giá", "chart_type": "BAR", "description": "Monthly price comparison by commodity"},
            {"name": "impact_analysis_table", "displayName": "Phân Tích Tác Động", "chart_type": "TABLE", "description": "Price impact on procurement budget"}
        ]
    },
    {
        "name": "supply_chain_risk_monitoring",
        "displayName": "Chuỗi Cung Ứng - Giám Sát Rủi Ro",
        "description": "Supply chain risk monitoring with geo-political, financial, and operational risk indicators.",
        "domain": "supply_chain",
        "owner": "cuong.vo@vinfast.vn",
        "update_frequency": "Daily",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/sc_risk_monitor",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/sc_risk.md",
        "tags": ["SupplyChain", "PowerBI", "Critical", "Confidential"],
        "charts": [
            {"name": "risk_heatmap", "displayName": "Bản Đồ Nhiệt Rủi Ro", "chart_type": "SCATTER", "description": "Geographic risk heatmap"},
            {"name": "supplier_financial_bar", "displayName": "Rủi Ro Tài Chính Nhà Cung Cấp", "chart_type": "BAR", "description": "Supplier financial risk scores"},
            {"name": "risk_breakdown_pie", "displayName": "Phân Loại Rủi Ro", "chart_type": "PIE", "description": "Risk breakdown by category"},
            {"name": "high_risk_table", "displayName": "Rủi Ro Cao", "chart_type": "TABLE", "description": "High-risk supplier list"}
        ]
    },
    {
        "name": "supply_chain_sustainability_dashboard",
        "displayName": "Chuỗi Cung Ứng - Bền Vững",
        "description": "Supply chain sustainability metrics including carbon emissions, ethical sourcing, and supplier diversity.",
        "domain": "supply_chain",
        "owner": "cuong.vo@vinfast.vn",
        "update_frequency": "Monthly",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/sc_sustainability",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/sc_sustainability.md",
        "tags": ["SupplyChain", "PowerBI", "Analytics", "Regulatory"],
        "charts": [
            {"name": "carbon_emissions_area", "displayName": "Lượng Phát Thải Carbon", "chart_type": "AREA", "description": "Scope 1, 2, 3 emissions trend"},
            {"name": "ethical_sourcing_gauge", "displayName": "Tìm Nguồn Cung Có Đạo Đức", "chart_type": "LINE", "description": "Ethical sourcing compliance rate"},
            {"name": "supplier_diversity_pie", "displayName": "Đa Dạng Nhà Cung Cấp", "chart_type": "PIE", "description": "Supplier diversity breakdown"},
            {"name": "sustainability_score_card", "displayName": "Điểm Bền Vững", "chart_type": "TEXT", "description": "Overall sustainability score"}
        ]
    },
    {
        "name": "supply_chain_po_fulfillment",
        "displayName": "Chuỗi Cung Ứng - Thực Hiện Đơn Mua",
        "description": "Purchase order fulfillment tracking with confirmation rates, delivery status, and exception management.",
        "domain": "supply_chain",
        "owner": "cuong.vo@vinfast.vn",
        "update_frequency": "Real-time (15 min refresh)",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/sc_po_fulfillment",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/sc_po.md",
        "tags": ["SupplyChain", "PowerBI", "RealTime", "SAP"],
        "charts": [
            {"name": "po_status_pie", "displayName": "Trạng Thái Đơn Mua", "chart_type": "PIE", "description": "PO status distribution"},
            {"name": "confirmation_rate_gauge", "displayName": "Tỷ Lệ Xác Nhận", "chart_type": "LINE", "description": "PO confirmation rate"},
            {"name": "fulfillment_trend_line", "displayName": "Xu Hướng Thực Hiện", "chart_type": "LINE", "description": "PO fulfillment trend"},
            {"name": "exception_list_table", "displayName": "Danh Sách Ngoại Lệ", "chart_type": "TABLE", "description": "PO exceptions and issues"},
            {"name": "po_aging_bar", "displayName": "Tuổi Đơn Mua", "chart_type": "BAR", "description": "PO aging buckets"}
        ]
    },
    {
        "name": "supply_chain_strategic_sourcing",
        "displayName": "Chuỗi Cung Ứng - Tìm Nguồn Cung Chiến Lược",
        "description": "Strategic sourcing initiatives tracking with savings, supplier consolidation, and category strategies.",
        "domain": "supply_chain",
        "owner": "cuong.vo@vinfast.vn",
        "update_frequency": "Monthly",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/sc_strategic_sourcing",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/sc_strategic.md",
        "tags": ["SupplyChain", "PowerBI", "Analytics", "Gold"],
        "charts": [
            {"name": "savings_pipeline_funnel", "displayName": "Kênh Tiết Kiệm", "chart_type": "BAR", "description": "Savings pipeline by initiative"},
            {"name": "supplier_consolidation_bar", "displayName": "Hợp Nhất Nhà Cung Cấp", "chart_type": "BAR", "description": "Supplier consolidation progress"},
            {"name": "category_spend_pie", "displayName": "Chi Tiêu Theo Danh Mục", "chart_type": "PIE", "description": "Category spend distribution"},
            {"name": "initiative_table", "displayName": "Sáng Kiến Chiến Lược", "chart_type": "TABLE", "description": "Strategic sourcing initiatives"}
        ]
    },
    {
        "name": "supply_chain_logistics_cost_analysis",
        "displayName": "Chuỗi Cung Ứng - Phân Tích Chi Phí Logistics",
        "description": "Logistics cost analysis across transportation, warehousing, and inventory carrying costs.",
        "domain": "supply_chain",
        "owner": "cuong.vo@vinfast.vn",
        "update_frequency": "Monthly",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/sc_logistics_cost",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/sc_log_cost.md",
        "tags": ["SupplyChain", "PowerBI", "Analytics", "Transactional"],
        "charts": [
            {"name": "cost_breakdown_pie", "displayName": "Cơ Cấu Chi Phí Logistics", "chart_type": "PIE", "description": "Logistics cost breakdown"},
            {"name": "transport_cost_bar", "displayName": "Chi Phí Vận Chuyển", "chart_type": "BAR", "description": "Transport cost by mode"},
            {"name": "cost_per_unit_line", "displayName": "Chi Phí Trên Đơn Vị", "chart_type": "LINE", "description": "Logistics cost per unit trend"},
            {"name": "warehouse_cost_card", "displayName": "Chi Phí Kho Bãi", "chart_type": "TEXT", "description": "Total warehouse cost"},
            {"name": "cost_comparison_table", "displayName": "So Sánh Chi Phí", "chart_type": "TABLE", "description": "Cost comparison across facilities"}
        ]
    },

    # =========================================================================
    # SALES (10 dashboards) - Owner: ha.le@vinfast.vn
    # =========================================================================
    {
        "name": "sales_daily_sales_by_model",
        "displayName": "Bán Hàng - Doanh Số Theo Mẫu Xe",
        "description": "Daily sales tracking by vehicle model with mix analysis and growth trends.",
        "domain": "sales",
        "owner": "ha.le@vinfast.vn",
        "update_frequency": "Daily",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/sales_daily_by_model",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/sales_model.md",
        "tags": ["PowerBI", "RealTime", "Transactional", "Salesforce"],
        "charts": [
            {"name": "sales_by_model_bar", "displayName": "Doanh Số Theo Mẫu Xe", "chart_type": "BAR", "description": "Daily sales volume by model"},
            {"name": "model_mix_pie", "displayName": "Cơ Cấu Mẫu Xe", "chart_type": "PIE", "description": "Sales mix by model"},
            {"name": "sales_trend_line", "displayName": "Xu Hướng Doanh Số", "chart_type": "LINE", "description": "30-day sales trend"},
            {"name": "top_model_card", "displayName": "Mẫu Xe Bán Chạy Nhất", "chart_type": "TEXT", "description": "Best-selling model today"}
        ]
    },
    {
        "name": "sales_dealer_performance",
        "displayName": "Bán Hàng - Hiệu Suất Đại Lý",
        "description": "Dealer performance scorecard with sales targets, conversion rates, and customer satisfaction.",
        "domain": "sales",
        "owner": "ha.le@vinfast.vn",
        "update_frequency": "Weekly",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/sales_dealer_perf",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/sales_dealer.md",
        "tags": ["PowerBI", "Analytics", "Salesforce", "Gold"],
        "charts": [
            {"name": "dealer_sales_bar", "displayName": "Doanh Số Theo Đại Lý", "chart_type": "BAR", "description": "Sales by dealer"},
            {"name": "target_vs_actual_gauge", "displayName": "Mục Tiêu vs Thực Tế", "chart_type": "LINE", "description": "Target achievement rate"},
            {"name": "conversion_funnel", "displayName": "Kênh Chuyển Đổi", "chart_type": "BAR", "description": "Lead to sale conversion funnel"},
            {"name": "dealer_scorecard_table", "displayName": "Thẻ Điểm Đại Lý", "chart_type": "TABLE", "description": "Dealer performance metrics"},
            {"name": "dealer_map", "displayName": "Bản Đồ Đại Lý", "chart_type": "SCATTER", "description": "Geographic dealer performance map"}
        ]
    },
    {
        "name": "sales_sales_pipeline",
        "displayName": "Bán Hàng - Kênh Bán Hàng",
        "description": "Sales pipeline tracking from lead generation to deal closure with stage analysis.",
        "domain": "sales",
        "owner": "ha.le@vinfast.vn",
        "update_frequency": "Real-time (5 min refresh)",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/sales_pipeline",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/sales_pipeline.md",
        "tags": ["PowerBI", "RealTime", "Salesforce", "Critical"],
        "charts": [
            {"name": "pipeline_funnel", "displayName": "Kênh Bán Hàng", "chart_type": "BAR", "description": "Pipeline stages funnel"},
            {"name": "pipeline_value_card", "displayName": "Giá Trị Kênh", "chart_type": "TEXT", "description": "Total pipeline value"},
            {"name": "win_rate_line", "displayName": "Tỷ Lệ Thắng", "chart_type": "LINE", "description": "Win rate trend by quarter"},
            {"name": "deal_size_bar", "displayName": "Quy Mô Giao Dịch", "chart_type": "BAR", "description": "Deal size distribution"},
            {"name": "pipeline_by_stage_pie", "displayName": "Kênh Theo Giai Đoạn", "chart_type": "PIE", "description": "Pipeline value by stage"}
        ]
    },
    {
        "name": "sales_market_share_analysis",
        "displayName": "Bán Hàng - Phân Tích Thị Phần",
        "description": "Market share analysis by segment, region, and competitor with trend tracking.",
        "domain": "sales",
        "owner": "ha.le@vinfast.vn",
        "update_frequency": "Monthly",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/sales_market_share",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/sales_market_share.md",
        "tags": ["PowerBI", "Analytics", "Gold", "Confidential"],
        "charts": [
            {"name": "market_share_pie", "displayName": "Thị Phần Theo Phân Khúc", "chart_type": "PIE", "description": "Market share by segment"},
            {"name": "competitor_bar", "displayName": "So Sánh Đối Thủ", "chart_type": "BAR", "description": "Market share vs competitors"},
            {"name": "share_trend_line", "displayName": "Xu Hướng Thị Phần", "chart_type": "LINE", "description": "Market share trend over 12 months"},
            {"name": "regional_map", "displayName": "Thị Phần Theo Khu Vực", "chart_type": "SCATTER", "description": "Regional market share map"}
        ]
    },
    {
        "name": "sales_campaign_roi",
        "displayName": "Bán Hàng - ROI Chiến Dịch",
        "description": "Marketing campaign ROI analysis with cost, revenue, leads generated, and conversion metrics.",
        "domain": "sales",
        "owner": "ha.le@vinfast.vn",
        "update_frequency": "Weekly",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/sales_campaign_roi",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/sales_campaign.md",
        "tags": ["PowerBI", "Analytics", "Salesforce", "Batch"],
        "charts": [
            {"name": "campaign_cost_bar", "displayName": "Chi Phí Chiến Dịch", "chart_type": "BAR", "description": "Campaign costs by channel"},
            {"name": "roi_gauge", "displayName": "ROI Chiến Dịch", "chart_type": "LINE", "description": "Campaign ROI percentage"},
            {"name": "lead_generation_line", "displayName": "Khách Hàng Tiềm Năng", "chart_type": "LINE", "description": "Leads generated over time"},
            {"name": "campaign_comparison_table", "displayName": "So Sánh Chiến Dịch", "chart_type": "TABLE", "description": "Campaign performance comparison"}
        ]
    },
    {
        "name": "sales_customer_segmentation",
        "displayName": "Bán Hàng - Phân Khúc Khách Hàng",
        "description": "Customer segmentation analysis with demographic, behavioral, and value-based segments.",
        "domain": "sales",
        "owner": "ha.le@vinfast.vn",
        "update_frequency": "Monthly",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/sales_customer_seg",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/sales_segment.md",
        "tags": ["PowerBI", "Analytics", "PII", "MasterData"],
        "charts": [
            {"name": "segment_size_pie", "displayName": "Quy Mô Phân Khúc", "chart_type": "PIE", "description": "Customer segment distribution"},
            {"name": "segment_value_bar", "displayName": "Giá Trị Theo Phân Khúc", "chart_type": "BAR", "description": "Revenue by customer segment"},
            {"name": "demographic_scatter", "displayName": "Nhân Khẩu Học", "chart_type": "SCATTER", "description": "Age vs income by segment"},
            {"name": "segment_trend_area", "displayName": "Xu Hướng Phân Khúc", "chart_type": "AREA", "description": "Segment growth over time"}
        ]
    },
    {
        "name": "sales_pricing_analysis",
        "displayName": "Bán Hàng - Phân Tích Giá",
        "description": "Pricing analysis with price elasticity, discount impact, and competitive price positioning.",
        "domain": "sales",
        "owner": "ha.le@vinfast.vn",
        "update_frequency": "Weekly",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/sales_pricing",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/sales_pricing.md",
        "tags": ["PowerBI", "Analytics", "Confidential", "Certified"],
        "charts": [
            {"name": "price_vs_volume_scatter", "displayName": "Giá vs Sản Lượng", "chart_type": "SCATTER", "description": "Price elasticity scatter"},
            {"name": "discount_impact_bar", "displayName": "Tác Động Chiết Khấu", "chart_type": "BAR", "description": "Discount impact on margin"},
            {"name": "competitive_price_line", "displayName": "Giá Cạnh Tranh", "chart_type": "LINE", "description": "Competitive price positioning"},
            {"name": "price_table", "displayName": "Bảng Giá", "chart_type": "TABLE", "description": "Price list by model and variant"}
        ]
    },
    {
        "name": "sales_order_backlog",
        "displayName": "Bán Hàng - Đơn Hàng Tồn Đọng",
        "description": "Order backlog tracking with aging, fulfillment status, and delivery commitment monitoring.",
        "domain": "sales",
        "owner": "ha.le@vinfast.vn",
        "update_frequency": "Daily",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/sales_order_backlog",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/sales_backlog.md",
        "tags": ["PowerBI", "Critical", "RealTime", "Transactional"],
        "charts": [
            {"name": "backlog_value_card", "displayName": "Giá Trị Tồn Đọng", "chart_type": "TEXT", "description": "Total backlog value"},
            {"name": "backlog_aging_bar", "displayName": "Tuổi Đơn Tồn Đọng", "chart_type": "BAR", "description": "Backlog aging buckets"},
            {"name": "fulfillment_trend_line", "displayName": "Xu Hướng Thực Hiện", "chart_type": "LINE", "description": "Order fulfillment rate trend"},
            {"name": "backlog_by_model_pie", "displayName": "Tồn Đọng Theo Mẫu Xe", "chart_type": "PIE", "description": "Backlog distribution by model"},
            {"name": "backlog_detail_table", "displayName": "Chi Tiết Tồn Đọng", "chart_type": "TABLE", "description": "Detailed backlog orders"}
        ]
    },
    {
        "name": "sales_regional_demand",
        "displayName": "Bán Hàng - Nhu Cầu Theo Khu Vực",
        "description": "Regional demand analysis with sales density maps, regional trends, and inventory allocation.",
        "domain": "sales",
        "owner": "ha.le@vinfast.vn",
        "update_frequency": "Weekly",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/sales_regional_demand",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/sales_regional.md",
        "tags": ["PowerBI", "Analytics", "MasterData", "Internal"],
        "charts": [
            {"name": "demand_map", "displayName": "Bản Đồ Nhu Cầu", "chart_type": "SCATTER", "description": "Regional demand heatmap"},
            {"name": "regional_sales_bar", "displayName": "Doanh Số Theo Khu Vực", "chart_type": "BAR", "description": "Sales volume by region"},
            {"name": "demand_trend_line", "displayName": "Xu Hướng Nhu Cầu", "chart_type": "LINE", "description": "Regional demand trend"},
            {"name": "allocation_gauge", "displayName": "Phân Bổ Hàng Tồn", "chart_type": "LINE", "description": "Inventory allocation adequacy"}
        ]
    },
    {
        "name": "sales_online_showroom_traffic",
        "displayName": "Bán Hàng - Lượng Truy Cập Showroom Online",
        "description": "Online showroom traffic analytics with page views, configurator usage, and lead generation.",
        "domain": "sales",
        "owner": "ha.le@vinfast.vn",
        "update_frequency": "Real-time (5 min refresh)",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/sales_online_traffic",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/sales_online.md",
        "tags": ["PowerBI", "RealTime", "Analytics", "Salesforce"],
        "charts": [
            {"name": "page_views_line", "displayName": "Lượt Xem Trang", "chart_type": "LINE", "description": "Daily page view trend"},
            {"name": "configurator_usage_bar", "displayName": "Sử Dụng Công Cụ Cấu Hình", "chart_type": "BAR", "description": "Configurator usage by model"},
            {"name": "traffic_source_pie", "displayName": "Nguồn Truy Cập", "chart_type": "PIE", "description": "Traffic source breakdown"},
            {"name": "lead_conversion_card", "displayName": "Chuyển Đổi Khách Hàng", "chart_type": "TEXT", "description": "Online lead conversion rate"},
            {"name": "popular_models_table", "displayName": "Mẫu Xe Được Xem Nhiều", "chart_type": "TABLE", "description": "Most viewed vehicle models"}
        ]
    },

    # =========================================================================
    # AFTER SALES (10 dashboards) - Owner: hieu.nguyen@vinfast.vn
    # =========================================================================
    {
        "name": "after_sales_service_desk_overview",
        "displayName": "Hậu Mãi - Tổng Quan Bàn Dịch Vụ",
        "description": "Service desk overview with ticket volume, resolution times, and customer satisfaction metrics.",
        "domain": "after_sales",
        "owner": "hieu.nguyen@vinfast.vn",
        "update_frequency": "Real-time (5 min refresh)",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/as_service_desk",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/as_service_desk.md",
        "tags": ["PowerBI", "RealTime", "Transactional", "Salesforce"],
        "charts": [
            {"name": "ticket_volume_line", "displayName": "Khối Lượng Yêu Cầu", "chart_type": "LINE", "description": "Daily ticket volume trend"},
            {"name": "resolution_time_gauge", "displayName": "Thời Gian Giải Quyết", "chart_type": "LINE", "description": "Average resolution time"},
            {"name": "ticket_status_pie", "displayName": "Trạng Thái Yêu Cầu", "chart_type": "PIE", "description": "Ticket status distribution"},
            {"name": "satisfaction_card", "displayName": "Điểm Hài Lòng", "chart_type": "TEXT", "description": "Customer satisfaction score"}
        ]
    },
    {
        "name": "after_sales_warranty_claim_analysis",
        "displayName": "Hậu Mãi - Phân Tích Yêu Cầu Bảo Hành",
        "description": "Warranty claim analysis with cost trends, defect patterns, and approval cycle times.",
        "domain": "after_sales",
        "owner": "hieu.nguyen@vinfast.vn",
        "update_frequency": "Weekly",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/as_warranty_claims",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/as_warranty.md",
        "tags": ["PowerBI", "Analytics", "Transactional", "SAP"],
        "charts": [
            {"name": "claim_cost_bar", "displayName": "Chi Phí Bảo Hành Theo Tháng", "chart_type": "BAR", "description": "Monthly warranty cost"},
            {"name": "defect_category_pie", "displayName": "Phân Loại Lỗi Bảo Hành", "chart_type": "PIE", "description": "Defect categories in claims"},
            {"name": "approval_cycle_line", "displayName": "Thời Gian Phê Duyệt", "chart_type": "LINE", "description": "Claim approval cycle trend"},
            {"name": "claim_frequency_table", "displayName": "Tần Suất Yêu Cầu", "chart_type": "TABLE", "description": "Claims by model and component"}
        ]
    },
    {
        "name": "after_sales_parts_availability",
        "displayName": "Hậu Mãi - Tồn Kho Phụ Tùng",
        "description": "Parts availability dashboard with stock levels, fill rates, and order fulfillment for service parts.",
        "domain": "after_sales",
        "owner": "hieu.nguyen@vinfast.vn",
        "update_frequency": "Real-time (15 min refresh)",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/as_parts_availability",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/as_parts.md",
        "tags": ["PowerBI", "RealTime", "Critical", "SupplyChain"],
        "charts": [
            {"name": "fill_rate_gauge", "displayName": "Tỷ Lệ Đáp Ứng", "chart_type": "LINE", "description": "Parts fill rate"},
            {"name": "stock_level_bar", "displayName": "Mức Tồn Phụ Tùng", "chart_type": "BAR", "description": "Stock levels by part category"},
            {"name": "stockout_pie", "displayName": "Hàng Hết Tồn", "chart_type": "PIE", "description": "Stockout breakdown by part"},
            {"name": "order_backlog_card", "displayName": "Đơn Hàng Tồn Đọng", "chart_type": "TEXT", "description": "Pending parts orders"},
            {"name": "parts_trend_area", "displayName": "Xu Hướng Phụ Tùng", "chart_type": "AREA", "description": "Parts demand trend"}
        ]
    },
    {
        "name": "after_sales_technician_performance",
        "displayName": "Hậu Mãi - Hiệu Suất Kỹ Thuật Viên",
        "description": "Technician performance tracking with repair times, first-time fix rates, and certification status.",
        "domain": "after_sales",
        "owner": "hieu.nguyen@vinfast.vn",
        "update_frequency": "Weekly",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/as_technician_perf",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/as_technician.md",
        "tags": ["PowerBI", "Analytics", "Internal", "MasterData"],
        "charts": [
            {"name": "repair_time_bar", "displayName": "Thời Gian Sửa Chữa", "chart_type": "BAR", "description": "Average repair time by technician"},
            {"name": "first_time_fix_gauge", "displayName": "Tỷ Lệ Sửa Lần Đầu", "chart_type": "LINE", "description": "First-time fix rate"},
            {"name": "tech_workload_pie", "displayName": "Khối Lượng Công Việc", "chart_type": "PIE", "description": "Workload distribution"},
            {"name": "certification_table", "displayName": "Chứng Chỉ Kỹ Thuật Viên", "chart_type": "TABLE", "description": "Technician certification status"}
        ]
    },
    {
        "name": "after_sales_csat_tracking",
        "displayName": "Hậu Mãi - Theo Dõi Hài Lòng Khách Hàng",
        "description": "Customer satisfaction tracking with NPS, CSAT scores, survey response analysis, and trend monitoring.",
        "domain": "after_sales",
        "owner": "hieu.nguyen@vinfast.vn",
        "update_frequency": "Daily",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/as_csat",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/as_csat.md",
        "tags": ["PowerBI", "Analytics", "Critical", "Salesforce"],
        "charts": [
            {"name": "nps_gauge", "displayName": "Chỉ Số NPS", "chart_type": "LINE", "description": "Net promoter score"},
            {"name": "csat_trend_line", "displayName": "Xu Hướng CSAT", "chart_type": "LINE", "description": "CSAT score trend"},
            {"name": "feedback_categories_pie", "displayName": "Danh Mục Phản Hồi", "chart_type": "PIE", "description": "Feedback category breakdown"},
            {"name": "survey_response_card", "displayName": "Tỷ Lệ Phản Hồi", "chart_type": "TEXT", "description": "Survey response rate"},
            {"name": "satisfaction_table", "displayName": "Chi Tiết Hài Lòng", "chart_type": "TABLE", "description": "Satisfaction by dealer"}
        ]
    },
    {
        "name": "after_sales_service_revenue",
        "displayName": "Hậu Mãi - Doanh Thu Dịch Vụ",
        "description": "Service revenue tracking with labor vs parts mix, warranty vs customer pay analysis.",
        "domain": "after_sales",
        "owner": "hieu.nguyen@vinfast.vn",
        "update_frequency": "Daily",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/as_service_revenue",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/as_revenue.md",
        "tags": ["PowerBI", "Analytics", "Finance", "Transactional"],
        "charts": [
            {"name": "revenue_trend_area", "displayName": "Xu Hướng Doanh Thu Dịch Vụ", "chart_type": "AREA", "description": "Service revenue trend"},
            {"name": "labor_vs_parts_pie", "displayName": "Nhân Công vs Phụ Tùng", "chart_type": "PIE", "description": "Revenue split labor vs parts"},
            {"name": "warranty_vs_cp_bar", "displayName": "Bảo Hành vs Khách Trả", "chart_type": "BAR", "description": "Warranty vs customer pay revenue"},
            {"name": "revenue_card", "displayName": "Doanh Thu Hôm Nay", "chart_type": "TEXT", "description": "Today service revenue"}
        ]
    },
    {
        "name": "after_sales_recall_management",
        "displayName": "Hậu Mãi - Quản Lý Thu Hồi",
        "description": "Recall management dashboard with affected vehicle tracking, completion rates, and campaign status.",
        "domain": "after_sales",
        "owner": "hieu.nguyen@vinfast.vn",
        "update_frequency": "Weekly",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/as_recall",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/as_recall.md",
        "tags": ["PowerBI", "Critical", "Regulatory", "Analytics"],
        "charts": [
            {"name": "recall_completion_gauge", "displayName": "Tỷ Lệ Hoàn Thành Thu Hồi", "chart_type": "LINE", "description": "Recall completion rate"},
            {"name": "affected_vehicles_bar", "displayName": "Số Lượng Xe Ảnh Hưởng", "chart_type": "BAR", "description": "Affected vehicles by campaign"},
            {"name": "campaign_status_pie", "displayName": "Trạng Thái Chiến Dịch", "chart_type": "PIE", "description": "Recall campaign status"},
            {"name": "recall_timeline_table", "displayName": "Dòng Thời Gian Thu Hồi", "chart_type": "TABLE", "description": "Recall campaign timeline"},
            {"name": "regional_impact_map", "displayName": "Tác Động Theo Khu Vực", "chart_type": "SCATTER", "description": "Geographic recall impact"}
        ]
    },
    {
        "name": "after_sales_fleet_service_dashboard",
        "displayName": "Hậu Mãi - Dịch Vụ Đội Xe",
        "description": "Fleet service management dashboard with maintenance schedules, service history, and cost tracking.",
        "domain": "after_sales",
        "owner": "hieu.nguyen@vinfast.vn",
        "update_frequency": "Daily",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/as_fleet_service",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/as_fleet.md",
        "tags": ["PowerBI", "Analytics", "MasterData", "Batch"],
        "charts": [
            {"name": "fleet_health_gauge", "displayName": "Sức Khỏe Đội Xe", "chart_type": "LINE", "description": "Overall fleet health score"},
            {"name": "maintenance_schedule_bar", "displayName": "Lịch Bảo Dưỡng", "chart_type": "BAR", "description": "Upcoming maintenance by fleet"},
            {"name": "fleet_cost_area", "displayName": "Chi Phí Đội Xe", "chart_type": "AREA", "description": "Fleet maintenance cost trend"},
            {"name": "fleet_summary_table", "displayName": "Tổng Quan Đội Xe", "chart_type": "TABLE", "description": "Fleet service summary"}
        ]
    },
    {
        "name": "after_sales_appointment_fill_rate",
        "displayName": "Hậu Mãi - Tỷ Lệ Lấp Đầy Lịch Hẹn",
        "description": "Service appointment fill rate analysis with booking trends, no-show tracking, and capacity optimization.",
        "domain": "after_sales",
        "owner": "hieu.nguyen@vinfast.vn",
        "update_frequency": "Daily",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/as_appointment_fill",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/as_appointment.md",
        "tags": ["PowerBI", "Analytics", "Transactional", "Internal"],
        "charts": [
            {"name": "fill_rate_gauge", "displayName": "Tỷ Lệ Lấp Đầy", "chart_type": "LINE", "description": "Appointment fill rate"},
            {"name": "booking_trend_line", "displayName": "Xu Hướng Đặt Lịch", "chart_type": "LINE", "description": "Daily booking trend"},
            {"name": "no_show_pie", "displayName": "Không Đến", "chart_type": "PIE", "description": "No-show breakdown by day"},
            {"name": "capacity_util_card", "displayName": "Sử Dụng Công Suất", "chart_type": "TEXT", "description": "Service bay utilization"},
            {"name": "appointment_table", "displayName": "Lịch Hẹn Chi Tiết", "chart_type": "TABLE", "description": "Appointment schedule details"}
        ]
    },
    {
        "name": "after_sales_complaint_analysis",
        "displayName": "Hậu Mãi - Phân Tích Khiếu Nại",
        "description": "Customer complaint analysis with categorization, resolution tracking, and root cause identification.",
        "domain": "after_sales",
        "owner": "hieu.nguyen@vinfast.vn",
        "update_frequency": "Weekly",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/as_complaint",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/as_complaint.md",
        "tags": ["PowerBI", "Analytics", "Critical", "Salesforce"],
        "charts": [
            {"name": "complaint_category_bar", "displayName": "Phân Loại Khiếu Nại", "chart_type": "BAR", "description": "Complaints by category"},
            {"name": "resolution_time_line", "displayName": "Thời Gian Giải Quyết", "chart_type": "LINE", "description": "Average resolution time trend"},
            {"name": "complaint_trend_area", "displayName": "Xu Hướng Khiếu Nại", "chart_type": "AREA", "description": "Complaint volume trend"},
            {"name": "root_cause_pie", "displayName": "Nguyên Nhân Gốc", "chart_type": "PIE", "description": "Root cause distribution"},
            {"name": "escalation_table", "displayName": "Khiếu Nại Leo Thang", "chart_type": "TABLE", "description": "Escalated complaints"}
        ]
    },

    # =========================================================================
    # VEHICLE DEVELOPMENT (10 dashboards) - Owner: tuan.le@vinfast.vn
    # =========================================================================
    {
        "name": "vehicle_development_program_gate_tracker",
        "displayName": "Phát Triển Xe - Theo Dõi Cổng Chương Trình",
        "description": "Product development program gate tracker with milestone status, deliverables, and stage-gate progress.",
        "domain": "vehicle_development",
        "owner": "tuan.le@vinfast.vn",
        "update_frequency": "Weekly",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/vd_gate_tracker",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/vd_gates.md",
        "tags": ["PowerBI", "Analytics", "Critical", "Certified"],
        "charts": [
            {"name": "gate_status_funnel", "displayName": "Trạng Thái Cổng", "chart_type": "BAR", "description": "Stage-gate progress funnel"},
            {"name": "milestone_timeline_bar", "displayName": "Dòng Thời Gian Mốc", "chart_type": "BAR", "description": "Milestone completion timeline"},
            {"name": "deliverable_status_pie", "displayName": "Trạng Thái Bàn Giao", "chart_type": "PIE", "description": "Deliverable status distribution"},
            {"name": "gate_score_card", "displayName": "Điểm Cổng", "chart_type": "TEXT", "description": "Overall gate readiness score"},
            {"name": "program_summary_table", "displayName": "Tổng Quan Chương Trình", "chart_type": "TABLE", "description": "Program milestone summary"}
        ]
    },
    {
        "name": "vehicle_development_dv_pv_progress",
        "displayName": "Phát Triển Xe - Tiến Độ DV/PV",
        "description": "Design Validation and Product Validation progress tracking with test completion and issue resolution.",
        "domain": "vehicle_development",
        "owner": "tuan.le@vinfast.vn",
        "update_frequency": "Weekly",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/vd_dv_pv_progress",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/vd_dv_pv.md",
        "tags": ["PowerBI", "Analytics", "Critical", "Transactional"],
        "charts": [
            {"name": "test_completion_gauge", "displayName": "Hoàn Thành Thử Nghiệm", "chart_type": "LINE", "description": "DV/PV test completion rate"},
            {"name": "test_status_bar", "displayName": "Trạng Thái Thử Nghiệm", "chart_type": "BAR", "description": "Test status by category"},
            {"name": "issue_backlog_line", "displayName": "Tồn Đọng Vấn Đề", "chart_type": "LINE", "description": "Open issues trend"},
            {"name": "test_coverage_pie", "displayName": "Bảo Phủ Thử Nghiệm", "chart_type": "PIE", "description": "Test coverage by requirement"}
        ]
    },
    {
        "name": "vehicle_development_change_request_dashboard",
        "displayName": "Phát Triển Xe - Yêu Cầu Thay Đổi",
        "description": "Engineering change request tracking with approval status, impact analysis, and implementation progress.",
        "domain": "vehicle_development",
        "owner": "tuan.le@vinfast.vn",
        "update_frequency": "Daily",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/vd_change_request",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/vd_ecr.md",
        "tags": ["PowerBI", "RealTime", "Analytics", "Transactional"],
        "charts": [
            {"name": "ecr_status_pie", "displayName": "Trạng Thái ECR", "chart_type": "PIE", "description": "ECR status distribution"},
            {"name": "ecr_approval_funnel", "displayName": "Phê Duyệt ECR", "chart_type": "BAR", "description": "ECR approval process funnel"},
            {"name": "ecr_trend_bar", "displayName": "Xu Hướng ECR", "chart_type": "BAR", "description": "Monthly ECR submission trend"},
            {"name": "impact_analysis_table", "displayName": "Phân Tích Tác Động", "chart_type": "TABLE", "description": "ECR impact assessment"}
        ]
    },
    {
        "name": "vehicle_development_cost_engineering",
        "displayName": "Phát Triển Xe - Kỹ Thuật Chi Phí",
        "description": "Cost engineering dashboard tracking target cost achievement, cost drivers, and value engineering savings.",
        "domain": "vehicle_development",
        "owner": "tuan.le@vinfast.vn",
        "update_frequency": "Monthly",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/vd_cost_engineering",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/vd_cost_eng.md",
        "tags": ["PowerBI", "Analytics", "Finance", "Confidential"],
        "charts": [
            {"name": "target_cost_gauge", "displayName": "Chi Phí Mục Tiêu", "chart_type": "LINE", "description": "Target cost achievement"},
            {"name": "cost_drivers_bar", "displayName": "Yếu Tố Chi Phí", "chart_type": "BAR", "description": "Cost drivers breakdown"},
            {"name": "ve_savings_area", "displayName": "Tiết Kiệm Kỹ Thuật", "chart_type": "AREA", "description": "Value engineering savings"},
            {"name": "cost_comparison_table", "displayName": "So Sánh Chi Phí", "chart_type": "TABLE", "description": "Cost comparison vs benchmark"}
        ]
    },
    {
        "name": "vehicle_development_weight_management",
        "displayName": "Phát Triển Xe - Quản Lý Trọng Lượng",
        "description": "Vehicle weight management dashboard tracking weight targets, savings initiatives, and compliance.",
        "domain": "vehicle_development",
        "owner": "tuan.le@vinfast.vn",
        "update_frequency": "Monthly",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/vd_weight_mgmt",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/vd_weight.md",
        "tags": ["PowerBI", "Analytics", "Critical", "Regulatory"],
        "charts": [
            {"name": "weight_gauge", "displayName": "Trọng Lượng Mục Tiêu", "chart_type": "LINE", "description": "Weight vs target"},
            {"name": "weight_breakdown_pie", "displayName": "Phân Bổ Trọng Lượng", "chart_type": "PIE", "description": "Weight by system category"},
            {"name": "savings_bar", "displayName": "Tiết Kiệm Trọng Lượng", "chart_type": "BAR", "description": "Weight savings by initiative"},
            {"name": "weight_trend_line", "displayName": "Xu Hướng Trọng Lượng", "chart_type": "LINE", "description": "Weight trend over program phases"}
        ]
    },
    {
        "name": "vehicle_development_prototype_build_status",
        "displayName": "Phát Triển Xe - Trạng Thái Chế Tạo Mẫu",
        "description": "Prototype build status tracking with build phases, parts availability, and build issue management.",
        "domain": "vehicle_development",
        "owner": "tuan.le@vinfast.vn",
        "update_frequency": "Daily",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/vd_prototype_build",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/vd_proto.md",
        "tags": ["PowerBI", "RealTime", "Critical", "Manufacturing"],
        "charts": [
            {"name": "build_progress_funnel", "displayName": "Tiến Độ Chế Tạo", "chart_type": "BAR", "description": "Prototype build progress stages"},
            {"name": "parts_readiness_card", "displayName": "Sẵn Sàng Phụ Tùng", "chart_type": "TEXT", "description": "Prototype parts readiness"},
            {"name": "build_issues_bar", "displayName": "Vấn Đề Chế Tạo", "chart_type": "BAR", "description": "Build issues by severity"},
            {"name": "build_calendar_table", "displayName": "Lịch Chế Tạo", "chart_type": "TABLE", "description": "Prototype build plan calendar"}
        ]
    },
    {
        "name": "vehicle_development_test_result_analysis",
        "displayName": "Phát Triển Xe - Phân Tích Kết Quả Thử Nghiệm",
        "description": "Test result analysis dashboard with pass/fail rates, test coverage, and certification readiness.",
        "domain": "vehicle_development",
        "owner": "tuan.le@vinfast.vn",
        "update_frequency": "Weekly",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/vd_test_results",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/vd_test.md",
        "tags": ["PowerBI", "Analytics", "Regulatory", "Certified"],
        "charts": [
            {"name": "pass_fail_gauge", "displayName": "Tỷ Lệ Đạt/Không Đạt", "chart_type": "LINE", "description": "Test pass rate"},
            {"name": "test_results_pie", "displayName": "Kết Quả Thử Nghiệm", "chart_type": "PIE", "description": "Pass, fail, retest distribution"},
            {"name": "failure_analysis_bar", "displayName": "Phân Tích Lỗi", "chart_type": "BAR", "description": "Failure modes by frequency"},
            {"name": "certification_readiness_table", "displayName": "Sẵn Sàng Chứng Nhận", "chart_type": "TABLE", "description": "Certification test status"},
            {"name": "test_coverage_area", "displayName": "Bảo Phủ Thử Nghiệm", "chart_type": "AREA", "description": "Test coverage trend"}
        ]
    },
    {
        "name": "vehicle_development_homologation_tracker",
        "displayName": "Phát Triển Xe - Theo Dõi Chứng Nhận",
        "description": "Vehicle homologation tracking across markets with certification status, document management, and timeline.",
        "domain": "vehicle_development",
        "owner": "tuan.le@vinfast.vn",
        "update_frequency": "Weekly",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/vd_homologation",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/vd_homologation.md",
        "tags": ["PowerBI", "Critical", "Regulatory", "Analytics"],
        "charts": [
            {"name": "cert_status_map", "displayName": "Trạng Thái Chứng Nhận Theo Thị Trường", "chart_type": "SCATTER", "description": "Homologation status by country"},
            {"name": "timeline_gauge", "displayName": "Tiến Độ Chứng Nhận", "chart_type": "LINE", "description": "Overall homologation progress"},
            {"name": "doc_completion_pie", "displayName": "Hoàn Thành Tài Liệu", "chart_type": "PIE", "description": "Document submission status"},
            {"name": "cert_detail_table", "displayName": "Chi Tiết Chứng Nhận", "chart_type": "TABLE", "description": "Certificate details by market"}
        ]
    },
    {
        "name": "vehicle_development_software_release",
        "displayName": "Phát Triển Xe - Phát Hành Phần Mềm",
        "description": "Software release management dashboard tracking release versions, validation status, and deployment progress.",
        "domain": "vehicle_development",
        "owner": "tuan.le@vinfast.vn",
        "update_frequency": "Real-time (15 min refresh)",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/vd_software_release",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/vd_software.md",
        "tags": ["PowerBI", "RealTime", "Critical", "Analytics"],
        "charts": [
            {"name": "release_version_bar", "displayName": "Phiên Bản Phát Hành", "chart_type": "BAR", "description": "Release versions over time"},
            {"name": "validation_status_pie", "displayName": "Trạng Thái Xác Nhận", "chart_type": "PIE", "description": "Software validation status"},
            {"name": "deployment_trend_line", "displayName": "Xu Hướng Triển Khai", "chart_type": "LINE", "description": "Deployment success rate trend"},
            {"name": "open_defects_card", "displayName": "Lỗi Đang Mở", "chart_type": "TEXT", "description": "Open software defects"},
            {"name": "release_notes_table", "displayName": "Ghi Chú Phát Hành", "chart_type": "TABLE", "description": "Release notes summary"}
        ]
    },
    {
        "name": "vehicle_development_adas_calibration",
        "displayName": "Phát Triển Xe - Hiệu Chuẩn ADAS",
        "description": "ADAS calibration tracking with sensor validation, calibration status, and performance verification.",
        "domain": "vehicle_development",
        "owner": "tuan.le@vinfast.vn",
        "update_frequency": "Weekly",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/vd_adas_calibration",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/vd_adas.md",
        "tags": ["PowerBI", "Analytics", "Critical", "Regulatory"],
        "charts": [
            {"name": "calibration_progress_gauge", "displayName": "Tiến Độ Hiệu Chuẩn", "chart_type": "LINE", "description": "ADAS calibration completion"},
            {"name": "sensor_status_bar", "displayName": "Trạng Thái Cảm Biến", "chart_type": "BAR", "description": "Sensor calibration by type"},
            {"name": "perf_verification_scatter", "displayName": "Xác Nhận Hiệu Suất", "chart_type": "SCATTER", "description": "ADAS performance verification"},
            {"name": "calibration_table", "displayName": "Chi Tiết Hiệu Chuẩn", "chart_type": "TABLE", "description": "Calibration records detail"}
        ]
    },

    # =========================================================================
    # VGREEN (10 dashboards) - Owner: mai.nguyen@vinfast.vn
    # =========================================================================
    {
        "name": "vgreen_battery_production_dashboard",
        "displayName": "VGreen - Sản Xuất Pin",
        "description": "Battery production monitoring with cell output, yield rates, and quality metrics.",
        "domain": "vgreen",
        "owner": "mai.nguyen@vinfast.vn",
        "update_frequency": "Real-time (5 min refresh)",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/vg_battery_production",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/vg_battery_prod.md",
        "tags": ["Manufacturing", "PowerBI", "RealTime", "Critical"],
        "charts": [
            {"name": "cell_output_bar", "displayName": "Sản Lượng Cell", "chart_type": "BAR", "description": "Daily battery cell output"},
            {"name": "yield_rate_gauge", "displayName": "Tỷ Lệ Đạt", "chart_type": "LINE", "description": "Production yield rate"},
            {"name": "defect_category_pie", "displayName": "Phân Loại Lỗi Pin", "chart_type": "PIE", "description": "Battery defect categories"},
            {"name": "production_trend_line", "displayName": "Xu Hướng Sản Xuất", "chart_type": "LINE", "description": "Battery production trend"}
        ]
    },
    {
        "name": "vgreen_charging_network_map",
        "displayName": "VGreen - Bản Đồ Mạng Lưới Sạc",
        "description": "Charging station network map with station status, utilization rates, and coverage analysis.",
        "domain": "vgreen",
        "owner": "mai.nguyen@vinfast.vn",
        "update_frequency": "Real-time (5 min refresh)",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/vg_charging_network",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/vg_charging.md",
        "tags": ["PowerBI", "RealTime", "Critical", "Analytics"],
        "charts": [
            {"name": "station_map", "displayName": "Bản Đồ Trạm Sạc", "chart_type": "SCATTER", "description": "Charging station locations"},
            {"name": "station_status_pie", "displayName": "Trạng Thái Trạm", "chart_type": "PIE", "description": "Station online vs offline"},
            {"name": "utilization_bar", "displayName": "Tỷ Lệ Sử Dụng", "chart_type": "BAR", "description": "Station utilization by location"},
            {"name": "charging_sessions_line", "displayName": "Phiên Sạc", "chart_type": "LINE", "description": "Daily charging sessions"},
            {"name": "coverage_card", "displayName": "Bảo Phủ Mạng Lưới", "chart_type": "TEXT", "description": "Network coverage percentage"}
        ]
    },
    {
        "name": "vgreen_energy_consumption",
        "displayName": "VGreen - Tiêu Thụ Năng Lượng",
        "description": "Energy consumption monitoring across facilities with cost tracking and efficiency analysis.",
        "domain": "vgreen",
        "owner": "mai.nguyen@vinfast.vn",
        "update_frequency": "Daily",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/vg_energy_consumption",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/vg_energy.md",
        "tags": ["PowerBI", "Analytics", "Manufacturing", "Batch"],
        "charts": [
            {"name": "energy_usage_area", "displayName": "Sử Dụng Năng Lượng", "chart_type": "AREA", "description": "Energy consumption by facility"},
            {"name": "cost_trend_line", "displayName": "Xu Hướng Chi Phí", "chart_type": "LINE", "description": "Energy cost trend"},
            {"name": "energy_mix_pie", "displayName": "Cơ Cấu Năng Lượng", "chart_type": "PIE", "description": "Energy source mix"},
            {"name": "efficiency_card", "displayName": "Hiệu Suất Năng Lượng", "chart_type": "TEXT", "description": "Energy efficiency index"}
        ]
    },
    {
        "name": "vgreen_battery_testing",
        "displayName": "VGreen - Thử Nghiệm Pin",
        "description": "Battery testing dashboard with cycle life, capacity retention, and safety test results.",
        "domain": "vgreen",
        "owner": "mai.nguyen@vinfast.vn",
        "update_frequency": "Daily",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/vg_battery_testing",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/vg_battery_test.md",
        "tags": ["PowerBI", "Analytics", "Critical", "Certified"],
        "charts": [
            {"name": "cycle_life_line", "displayName": "Vòng Đời Chu Kỳ", "chart_type": "LINE", "description": "Battery cycle life test results"},
            {"name": "capacity_retention_gauge", "displayName": "Duy Trì Dung Lượng", "chart_type": "LINE", "description": "Capacity retention rate"},
            {"name": "safety_test_pie", "displayName": "Thử Nghiệm An Toàn", "chart_type": "PIE", "description": "Safety test pass/fail"},
            {"name": "test_summary_table", "displayName": "Tổng Quan Thử Nghiệm", "chart_type": "TABLE", "description": "Battery test summary"}
        ]
    },
    {
        "name": "vgreen_ev_range_analysis",
        "displayName": "VGreen - Phân Tích Phạm Vi EV",
        "description": "EV range analysis with real-world vs WLTP range, battery degradation impact, and driving pattern effects.",
        "domain": "vgreen",
        "owner": "mai.nguyen@vinfast.vn",
        "update_frequency": "Weekly",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/vg_ev_range",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/vg_range.md",
        "tags": ["PowerBI", "Analytics", "Transactional", "Analytics"],
        "charts": [
            {"name": "range_comparison_bar", "displayName": "So Sánh Phạm Vi", "chart_type": "BAR", "description": "WLTP vs real-world range by model"},
            {"name": "degradation_trend_line", "displayName": "Xu Hướng Suy Giảm", "chart_type": "LINE", "description": "Battery degradation over time"},
            {"name": "driving_pattern_scatter", "displayName": "Mẫu Lái Xe", "chart_type": "SCATTER", "description": "Range vs driving speed scatter"},
            {"name": "range_card", "displayName": "Phạm Vi Trung Bình", "chart_type": "TEXT", "description": "Average real-world range"}
        ]
    },
    {
        "name": "vgreen_sustainability_reporting",
        "displayName": "VGreen - Báo Cáo Bền Vững",
        "description": "Sustainability reporting dashboard with ESG metrics, emission reduction targets, and green initiatives tracking.",
        "domain": "vgreen",
        "owner": "mai.nguyen@vinfast.vn",
        "update_frequency": "Monthly",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/vg_sustainability",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/vg_sustainability.md",
        "tags": ["PowerBI", "Analytics", "Regulatory", "Gold"],
        "charts": [
            {"name": "esg_score_card", "displayName": "Điểm ESG", "chart_type": "TEXT", "description": "Overall ESG score"},
            {"name": "emission_trend_area", "displayName": "Xu Hướng Phát Thải", "chart_type": "AREA", "description": "CO2 emission reduction trend"},
            {"name": "green_initiatives_bar", "displayName": "Sáng Kiến Xanh", "chart_type": "BAR", "description": "Green initiative progress"},
            {"name": "esg_dimensions_pie", "displayName": "Các Khía Cạnh ESG", "chart_type": "PIE", "description": "Environmental, Social, Governance breakdown"},
            {"name": "target_vs_actual_gauge", "displayName": "Mục Tiêu vs Thực Tế", "chart_type": "LINE", "description": "Emission target achievement"}
        ]
    },
    {
        "name": "vgreen_carbon_footprint",
        "displayName": "VGreen - Dấu Chân Carbon",
        "description": "Carbon footprint tracking across scope 1, 2, and 3 emissions with reduction initiatives and offset tracking.",
        "domain": "vgreen",
        "owner": "mai.nguyen@vinfast.vn",
        "update_frequency": "Monthly",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/vg_carbon_footprint",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/vg_carbon.md",
        "tags": ["PowerBI", "Analytics", "Regulatory", "Confidential"],
        "charts": [
            {"name": "scope_breakdown_bar", "displayName": "Phân Tích Phạm Vi", "chart_type": "BAR", "description": "Scope 1, 2, 3 emissions"},
            {"name": "carbon_trend_line", "displayName": "Xu Hướng Carbon", "chart_type": "LINE", "description": "Carbon footprint trend"},
            {"name": "reduction_pie", "displayName": "Giảm Phát Thải", "chart_type": "PIE", "description": "Reduction by initiative"},
            {"name": "offset_card", "displayName": "Bù Đắp Carbon", "chart_type": "TEXT", "description": "Carbon offset credits"},
            {"name": "intensity_table", "displayName": "Cường Độ Carbon", "chart_type": "TABLE", "description": "Carbon intensity by product"}
        ]
    },
    {
        "name": "vgreen_battery_lifecycle",
        "displayName": "VGreen - Vòng Đời Pin",
        "description": "Battery lifecycle management from production to recycling with second-life usage tracking.",
        "domain": "vgreen",
        "owner": "mai.nguyen@vinfast.vn",
        "update_frequency": "Weekly",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/vg_battery_lifecycle",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/vg_battery_lc.md",
        "tags": ["PowerBI", "Analytics", "MasterData", "Regulatory"],
        "charts": [
            {"name": "lifecycle_funnel", "displayName": "Vòng Đời Pin", "chart_type": "BAR", "description": "Battery lifecycle stages"},
            {"name": "second_life_bar", "displayName": "Sử Dụng Lần Hai", "chart_type": "BAR", "description": "Second-life applications"},
            {"name": "recycling_rate_gauge", "displayName": "Tỷ Lệ Tái Chế", "chart_type": "LINE", "description": "Battery recycling rate"},
            {"name": "lifecycle_table", "displayName": "Chi Tiết Vòng Đời", "chart_type": "TABLE", "description": "Battery lifecycle records"}
        ]
    },
    {
        "name": "vgreen_charging_revenue",
        "displayName": "VGreen - Doanh Thu Sạc",
        "description": "Charging revenue monitoring with transaction analysis, pricing optimization, and usage patterns.",
        "domain": "vgreen",
        "owner": "mai.nguyen@vinfast.vn",
        "update_frequency": "Daily",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/vg_charging_revenue",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/vg_charge_rev.md",
        "tags": ["PowerBI", "Analytics", "Finance", "Transactional"],
        "charts": [
            {"name": "revenue_trend_area", "displayName": "Xu Hướng Doanh Thu", "chart_type": "AREA", "description": "Charging revenue trend"},
            {"name": "transaction_volume_bar", "displayName": "Khối Lượng Giao Dịch", "chart_type": "BAR", "description": "Daily transaction count"},
            {"name": "pricing_pie", "displayName": "Phân Tích Giá", "chart_type": "PIE", "description": "Revenue by pricing tier"},
            {"name": "arpu_card", "displayName": "Doanh Thu Trên Người Dùng", "chart_type": "TEXT", "description": "Average revenue per user"},
            {"name": "usage_pattern_table", "displayName": "Mẫu Sử Dụng", "chart_type": "TABLE", "description": "Charging usage patterns"}
        ]
    },
    {
        "name": "vgreen_renewable_energy_mix",
        "displayName": "VGreen - Cơ Cấu Năng Lượng Tái Tạo",
        "description": "Renewable energy mix tracking with solar, wind, hydro contributions and grid independence progress.",
        "domain": "vgreen",
        "owner": "mai.nguyen@vinfast.vn",
        "update_frequency": "Monthly",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/vg_renewable_mix",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/vg_renewable.md",
        "tags": ["PowerBI", "Analytics", "Regulatory", "Gold"],
        "charts": [
            {"name": "renewable_mix_pie", "displayName": "Cơ Cấu Năng Lượng Tái Tạo", "chart_type": "PIE", "description": "Solar, wind, hydro breakdown"},
            {"name": "renewable_share_gauge", "displayName": "Tỷ Lệ Năng Lượng Tái Tạo", "chart_type": "LINE", "description": "Renewable energy share"},
            {"name": "generation_trend_line", "displayName": "Xu Hướng Sản Xuất", "chart_type": "LINE", "description": "Renewable generation trend"},
            {"name": "grid_independence_card", "displayName": "Độc Lập Lưới Điện", "chart_type": "TEXT", "description": "Grid independence percentage"},
            {"name": "investment_bar", "displayName": "Đầu Tư Tái Tạo", "chart_type": "BAR", "description": "Renewable investment by type"}
        ]
    },

    # =========================================================================
    # DATA GOVERNANCE (10 dashboards) - Owner: thao.le@vinfast.vn
    # =========================================================================
    {
        "name": "data_governance_data_quality_scorecard",
        "displayName": "Quản Trị Dữ Liệu - Thẻ Điểm Chất Lượng",
        "description": "Data quality scorecard with completeness, accuracy, consistency, and timeliness metrics across domains.",
        "domain": "data_governance",
        "owner": "thao.le@vinfast.vn",
        "update_frequency": "Daily",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/dg_quality_scorecard",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/dg_quality.md",
        "tags": ["PowerBI", "Analytics", "Critical", "MasterData"],
        "charts": [
            {"name": "overall_dq_gauge", "displayName": "Chất Lượng Tổng Thể", "chart_type": "LINE", "description": "Overall data quality score"},
            {"name": "dq_dimensions_bar", "displayName": "Các Khía Cạnh Chất Lượng", "chart_type": "BAR", "description": "Completeness, accuracy, consistency, timeliness"},
            {"name": "dq_by_domain_pie", "displayName": "Chất Lượng Theo Miền", "chart_type": "PIE", "description": "Data quality by domain"},
            {"name": "dq_trend_line", "displayName": "Xu Hướng Chất Lượng", "chart_type": "LINE", "description": "Data quality trend over time"},
            {"name": "issue_detail_table", "displayName": "Chi Tiết Vấn Đề", "chart_type": "TABLE", "description": "Data quality issues detail"}
        ]
    },
    {
        "name": "data_governance_data_catalog_growth",
        "displayName": "Quản Trị Dữ Liệu - Tăng Trưởng Danh Mục",
        "description": "Data catalog growth tracking with asset counts, coverage by domain, and adoption metrics.",
        "domain": "data_governance",
        "owner": "thao.le@vinfast.vn",
        "update_frequency": "Weekly",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/dg_catalog_growth",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/dg_catalog.md",
        "tags": ["PowerBI", "Analytics", "MasterData", "Internal"],
        "charts": [
            {"name": "catalog_assets_bar", "displayName": "Tài Sản Danh Mục", "chart_type": "BAR", "description": "Catalog assets by type"},
            {"name": "growth_trend_line", "displayName": "Xu Hướng Tăng Trưởng", "chart_type": "LINE", "description": "Catalog growth trend"},
            {"name": "coverage_by_domain_pie", "displayName": "Bảo Phủ Theo Miền", "chart_type": "PIE", "description": "Catalog coverage by domain"},
            {"name": "adoption_card", "displayName": "Tỷ Lệ Áp Dụng", "chart_type": "TEXT", "description": "Catalog adoption rate"}
        ]
    },
    {
        "name": "data_governance_data_lineage_viewer",
        "displayName": "Quản Trị Dữ Liệu - Sơ Đồ Dòng Dữ Liệu",
        "description": "Interactive data lineage viewer showing upstream and downstream dependencies for critical datasets.",
        "domain": "data_governance",
        "owner": "thao.le@vinfast.vn",
        "update_frequency": "Real-time (on demand)",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/dg_lineage_viewer",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/dg_lineage.md",
        "tags": ["PowerBI", "RealTime", "MasterData", "Certified"],
        "charts": [
            {"name": "lineage_graph", "displayName": "Đồ Thị Dòng Dữ Liệu", "chart_type": "TABLE", "description": "Interactive lineage graph view"},
            {"name": "upstream_count_card", "displayName": "Nguồn Thượng Nguồn", "chart_type": "TEXT", "description": "Upstream source count"},
            {"name": "downstream_impact_bar", "displayName": "Tác Động Hạ Nguồn", "chart_type": "BAR", "description": "Downstream impact analysis"},
            {"name": "critical_path_pie", "displayName": "Đường Dẫn Quan Trọng", "chart_type": "PIE", "description": "Critical data paths"}
        ]
    },
    {
        "name": "data_governance_data_sla_compliance",
        "displayName": "Quản Trị Dữ Liệu - Tuân Thủ SLA",
        "description": "Data SLA compliance monitoring with freshness, availability, and latency tracking by dataset.",
        "domain": "data_governance",
        "owner": "thao.le@vinfast.vn",
        "update_frequency": "Daily",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/dg_sla_compliance",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/dg_sla.md",
        "tags": ["PowerBI", "Analytics", "Critical", "Batch"],
        "charts": [
            {"name": "sla_breach_gauge", "displayName": "Vi Phạm SLA", "chart_type": "LINE", "description": "SLA breach rate"},
            {"name": "freshness_bar", "displayName": "Độ Mới Dữ Liệu", "chart_type": "BAR", "description": "Data freshness by dataset"},
            {"name": "availability_line", "displayName": "Khả Dụng Hệ Thống", "chart_type": "LINE", "description": "System availability trend"},
            {"name": "sla_detail_table", "displayName": "Chi Tiết SLA", "chart_type": "TABLE", "description": "SLA compliance details"}
        ]
    },
    {
        "name": "data_governance_data_breach_monitor",
        "displayName": "Quản Trị Dữ Liệu - Giám Sát Xâm Phạm",
        "description": "Data breach monitoring dashboard with incident tracking, severity scoring, and response time metrics.",
        "domain": "data_governance",
        "owner": "thao.le@vinfast.vn",
        "update_frequency": "Real-time (5 min refresh)",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/dg_breach_monitor",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/dg_breach.md",
        "tags": ["PowerBI", "RealTime", "Confidential", "Regulatory"],
        "charts": [
            {"name": "incident_severity_pie", "displayName": "Mức Độ Sự Cố", "chart_type": "PIE", "description": "Incident severity distribution"},
            {"name": "response_time_gauge", "displayName": "Thời Gian Phản Ứng", "chart_type": "LINE", "description": "Average incident response time"},
            {"name": "breach_trend_line", "displayName": "Xu Hướng Xâm Phạm", "chart_type": "LINE", "description": "Breach incident trend"},
            {"name": "open_cases_card", "displayName": "Vụ Đang Mở", "chart_type": "TEXT", "description": "Open breach cases"}
        ]
    },
    {
        "name": "data_governance_access_audit_log",
        "displayName": "Quản Trị Dữ Liệu - Nhật Ký Truy Cập",
        "description": "Access audit log dashboard with user activity monitoring, anomaly detection, and compliance reporting.",
        "domain": "data_governance",
        "owner": "thao.le@vinfast.vn",
        "update_frequency": "Real-time (15 min refresh)",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/dg_access_audit",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/dg_audit.md",
        "tags": ["PowerBI", "RealTime", "Confidential", "Regulatory"],
        "charts": [
            {"name": "access_volume_area", "displayName": "Khối Lượng Truy Cập", "chart_type": "AREA", "description": "Daily access volume trend"},
            {"name": "user_activity_bar", "displayName": "Hoạt Động Người Dùng", "chart_type": "BAR", "description": "Top users by activity"},
            {"name": "anomaly_detection_table", "displayName": "Phát Hiện Bất Thường", "chart_type": "TABLE", "description": "Anomalous access patterns"},
            {"name": "compliance_status_card", "displayName": "Trạng Thái Tuân Thủ", "chart_type": "TEXT", "description": "Audit compliance status"}
        ]
    },
    {
        "name": "data_governance_data_retention_tracker",
        "displayName": "Quản Trị Dữ Liệu - Theo Dõi Lưu Trữ",
        "description": "Data retention policy compliance tracking with purge schedules, archive status, and storage optimization.",
        "domain": "data_governance",
        "owner": "thao.le@vinfast.vn",
        "update_frequency": "Weekly",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/dg_retention_tracker",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/dg_retention.md",
        "tags": ["PowerBI", "Analytics", "Regulatory", "Batch"],
        "charts": [
            {"name": "retention_compliance_gauge", "displayName": "Tuân Thủ Lưu Trữ", "chart_type": "LINE", "description": "Retention policy compliance rate"},
            {"name": "purge_backlog_bar", "displayName": "Tồn Đọng Xóa Dữ Liệu", "chart_type": "BAR", "description": "Purge backlog by dataset"},
            {"name": "storage_usage_area", "displayName": "Sử Dụng Lưu Trữ", "chart_type": "AREA", "description": "Storage usage over time"},
            {"name": "archive_status_pie", "displayName": "Trạng Thái Lưu Trữ", "chart_type": "PIE", "description": "Archive status distribution"}
        ]
    },
    {
        "name": "data_governance_master_data_quality",
        "displayName": "Quản Trị Dữ Liệu - Chất Lượng Dữ Liệu Master",
        "description": "Master data quality monitoring for customer, product, vendor, and material master records.",
        "domain": "data_governance",
        "owner": "thao.le@vinfast.vn",
        "update_frequency": "Daily",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/dg_master_data_quality",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/dg_mdq.md",
        "tags": ["PowerBI", "Analytics", "MasterData", "Critical"],
        "charts": [
            {"name": "mdm_quality_gauge", "displayName": "Chất Lượng MDM", "chart_type": "LINE", "description": "Overall master data quality score"},
            {"name": "entity_quality_bar", "displayName": "Chất Lượng Theo Thực Thể", "chart_type": "BAR", "description": "Quality by master data entity"},
            {"name": "duplicate_records_pie", "displayName": "Bản Ghi Trùng Lặp", "chart_type": "PIE", "description": "Duplicate record distribution"},
            {"name": "completeness_table", "displayName": "Tỷ Lệ Đầy Đủ", "chart_type": "TABLE", "description": "Field completeness by entity"}
        ]
    },
    {
        "name": "data_governance_data_sharing_overview",
        "displayName": "Quản Trị Dữ Liệu - Tổng Quan Chia Sẻ Dữ Liệu",
        "description": "Data sharing agreements overview with active shares, consumption metrics, and access governance.",
        "domain": "data_governance",
        "owner": "thao.le@vinfast.vn",
        "update_frequency": "Weekly",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/dg_sharing_overview",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/dg_sharing.md",
        "tags": ["PowerBI", "Analytics", "Confidential", "Internal"],
        "charts": [
            {"name": "active_shares_card", "displayName": "Chia Sẻ Đang Hoạt Động", "chart_type": "TEXT", "description": "Active data shares"},
            {"name": "consumption_bar", "displayName": "Tiêu Thụ Dữ Liệu", "chart_type": "BAR", "description": "Data consumption by consumer"},
            {"name": "agreement_status_pie", "displayName": "Trạng Thái Thỏa Thuận", "chart_type": "PIE", "description": "Sharing agreement status"},
            {"name": "governance_table", "displayName": "Quản Trị Chia Sẻ", "chart_type": "TABLE", "description": "Data sharing governance details"}
        ]
    },
    {
        "name": "data_governance_data_stewardship",
        "displayName": "Quản Trị Dữ Liệu - Quản Trị Dữ Liệu",
        "description": "Data stewardship dashboard with steward assignments, stewardship activities, and domain coverage.",
        "domain": "data_governance",
        "owner": "thao.le@vinfast.vn",
        "update_frequency": "Monthly",
        "powerbi_url": "https://app.powerbi.com/groups/me/dashboards/dg_stewardship",
        "documentation": "https://vinfast.sharepoint.com/sites/datahub/wiki/dg_stewardship.md",
        "tags": ["PowerBI", "Analytics", "MasterData", "Internal"],
        "charts": [
            {"name": "steward_coverage_bar", "displayName": "Bảo Phủ Quản Trị Viên", "chart_type": "BAR", "description": "Steward assignments by domain"},
            {"name": "activity_trend_line", "displayName": "Xu Hướng Hoạt Động", "chart_type": "LINE", "description": "Stewardship activities trend"},
            {"name": "domain_coverage_pie", "displayName": "Bảo Phủ Miền", "chart_type": "PIE", "description": "Domain coverage by steward"},
            {"name": "stewardship_score_card", "displayName": "Điểm Quản Trị", "chart_type": "TEXT", "description": "Overall stewardship score"}
        ]
    },
]
