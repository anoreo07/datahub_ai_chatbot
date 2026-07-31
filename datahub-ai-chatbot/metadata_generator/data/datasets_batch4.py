DATASETS_BATCH4 = []

from data.datasets_batch_generator import generate_fact_columns, generate_dim_columns, generate_agg_columns

_plant_codes = ["VF01", "VF02", "VF03", "VF04"]
_line_names = [
    "VF8 Final", "VF9 Final", "VF7 Final", "VF5 Final", "VF3 Final",
    "Engine", "Paint Shop", "Body Shop", "Battery Pack", "QC Line",
]
_plant_lines = [(p, l) for p in _plant_codes for l in _line_names]

# ──────────────────────────────────────────────
# SẢN XUẤT (manufacturing) — ~380 additional datasets
# Current: 20, Need: 465, Add: 445
# ──────────────────────────────────────────────
_mfg_dom = "manufacturing"
_mfg_idx = 0

# Fact tables — production events per plant/line/shift (60 tables)
PRODUCTION_LINES = [
    "VF8 Final Assembly", "VF9 Final Assembly", "VF7 Final Assembly",
    "VF5 Final Assembly", "VF3 Final Assembly", "Engine Assembly",
    "Paint Shop", "Body Shop", "Battery Pack Assembly", "QC Inspection",
]
SHIFT_NAMES = ["Morning", "Afternoon", "Night"]

for plant in ["VF01", "VF02", "VF03", "VF04"]:
    for line in PRODUCTION_LINES:
        _mfg_idx += 1
        safe_line = line.lower().replace(" ", "_")
        DATASETS_BATCH4.append({
            "name": f"fact_production_{safe_line}_{plant.lower()}",
            "description": f"Production fact table for {line} at plant {plant} — records each production event, cycle time, quality outcome per shift.",
            "domain": _mfg_dom,
            "platform": "sap",
            "tags": ["Manufacturing", "Fact", "Production", "SAP"],
            "columns": generate_fact_columns("production", [
                ("plant", "VARCHAR(10)", "Plant code", True),
                ("line_id", "VARCHAR(50)", "Production line identifier", True),
                ("shift", "VARCHAR(20)", "Shift name (Morning/Afternoon/Night)", True),
                ("production_date", "DATE", "Production date", True),
                ("order_number", "VARCHAR(30)", "Production order number", True),
                ("model_code", "VARCHAR(20)", "Vehicle model code being assembled", False),
                ("target_units", "INTEGER", "Target units for the shift", False),
                ("produced_units", "INTEGER", "Actual units produced", False),
                ("good_units", "INTEGER", "Units passing first-time quality", False),
                ("rework_units", "INTEGER", "Units requiring rework", False),
                ("scrap_units", "INTEGER", "Units scrapped", False),
                ("cycle_time_sec", "DECIMAL(10,2)", "Average cycle time in seconds", False),
                ("downtime_minutes", "DECIMAL(10,2)", "Total downtime in minutes", False),
                ("oee_pct", "DECIMAL(5,2)", "Overall Equipment Effectiveness percentage", False),
                ("availability_pct", "DECIMAL(5,2)", "Availability rate percentage", False),
                ("performance_pct", "DECIMAL(5,2)", "Performance rate percentage", False),
                ("quality_pct", "DECIMAL(5,2)", "Quality rate percentage", False),
                ("created_at", "TIMESTAMP", "Record creation timestamp", False),
            ]),
        })

# OEE daily aggregation (60 tables)
for plant in ["VF01", "VF02", "VF03", "VF04"]:
    for line in PRODUCTION_LINES[:15]:
        _mfg_idx += 1
        safe_line = line.lower().replace(" ", "_")
        DATASETS_BATCH4.append({
            "name": f"agg_oee_daily_{safe_line}_{plant.lower()}",
            "description": f"Daily OEE aggregation for {line} at plant {plant} — availability, performance, quality metrics aggregated from shift-level data.",
            "domain": _mfg_dom,
            "platform": "aggregate",
            "tags": ["Manufacturing", "Aggregate", "OEE", "Daily"],
            "columns": generate_agg_columns([
                ("plant", "VARCHAR(10)", "Plant code", True),
                ("line_id", "VARCHAR(50)", "Production line identifier", True),
                ("report_date", "DATE", "Report date", True),
                ("total_target_units", "INTEGER", "Total target units for the day", False),
                ("total_produced_units", "INTEGER", "Total units produced", False),
                ("avg_oee_pct", "DECIMAL(5,2)", "Average OEE percentage", False),
                ("avg_availability_pct", "DECIMAL(5,2)", "Average availability percentage", False),
                ("avg_performance_pct", "DECIMAL(5,2)", "Average performance percentage", False),
                ("avg_quality_pct", "DECIMAL(5,2)", "Average quality percentage", False),
                ("total_downtime_minutes", "DECIMAL(10,2)", "Total downtime in minutes", False),
                ("total_rework_units", "INTEGER", "Total rework units", False),
                ("total_scrap_units", "INTEGER", "Total scrap units", False),
                ("first_pass_yield_pct", "DECIMAL(5,2)", "First-pass yield percentage", False),
            ]),
        })

# Dimension tables — production reference data (30 tables)
PROD_DIM_TABLES = [
    ("dim_production_line", f"Production line master data — details of each assembly line across all plants."),
    ("dim_shift_calendar", f"Shift calendar master — defines shift patterns, holidays, and working days per plant."),
    ("dim_model", f"Vehicle model master — specifications and attributes of each vehicle model produced."),
    ("dim_workstation", f"Workstation master — individual workstations and stations within each production line."),
    ("dim_operation", f"Operation master — standard operations and routing steps for each model."),
    ("dim_defect_code", f"Defect code master — classification of quality defects found during production."),
    ("dim_quality_checkpoint", f"Quality checkpoint master — inspection points along the production line."),
    ("dim_tooling", f"Tooling master — tools, jigs, and fixtures used in production."),
    ("dim_material_bom", f"Bill of Materials master — component materials required for each model."),
    ("dim_production_order", f"Production order master — details of each production order released."),
    ("dim_machine", f"Machine master — machines and equipment used in production."),
    ("dim_maintenance_plan", f"Maintenance plan master — scheduled maintenance plans for equipment."),
    ("dim_station", f"Station master — stations along assembly lines with capabilities and tooling."),
    ("dim_shift_pattern", f"Shift pattern master — shift rotation patterns and crew assignments."),
    ("dim_product_family", f"Product family master — grouping of vehicle models into families."),
]
for tbl in PROD_DIM_TABLES:
    _mfg_idx += 1
    name, desc = tbl
    DATASETS_BATCH4.append({
        "name": name,
        "description": desc,
        "domain": _mfg_dom,
        "platform": "postgres",
        "tags": ["Manufacturing", "MasterData", "Dimension"],
        "columns": generate_dim_columns(name),
    })

# Quality inspection fact tables (30 tables)
for plant in ["VF01", "VF02", "VF03"]:
    for line in ["Body Shop", "Paint Shop", "QC Inspection", "Final Assembly", "Battery Pack"]:
        _mfg_idx += 1
        safe_line = line.lower().replace(" ", "_")
        DATASETS_BATCH4.append({
            "name": f"fact_quality_{safe_line}_{plant.lower()}",
            "description": f"Quality inspection fact table for {line} at plant {plant} — records each inspection event, defect findings, and resolution.",
            "domain": _mfg_dom,
            "platform": "sap",
            "tags": ["Manufacturing", "Fact", "Quality", "SAP"],
            "columns": generate_fact_columns("quality", [
                ("plant", "VARCHAR(10)", "Plant code", True),
                ("line_id", "VARCHAR(50)", "Production line identifier", True),
                ("inspection_date", "DATE", "Inspection date", True),
                ("inspection_type", "VARCHAR(30)", "Type of inspection (incoming/in-process/final)", True),
                ("unit_vin", "VARCHAR(30)", "Vehicle VIN or unit identifier", True),
                ("checkpoint_code", "VARCHAR(30)", "Quality checkpoint code", False),
                ("defect_code", "VARCHAR(30)", "Defect code if found", False),
                ("defect_severity", "VARCHAR(10)", "Defect severity (critical/major/minor)", False),
                ("defect_description", "TEXT", "Description of the defect found", False),
                ("inspector_id", "VARCHAR(30)", "Inspector user ID", False),
                ("inspection_result", "VARCHAR(10)", "Inspection result (pass/fail/conditional)", False),
                ("rework_order", "VARCHAR(30)", "Rework order number if applicable", False),
                ("rework_completed_date", "DATE", "Date rework was completed", False),
                ("rework_verified_by", "VARCHAR(30)", "User ID who verified rework", False),
                ("created_at", "TIMESTAMP", "Record creation timestamp", False),
            ]),
        })

# Maintenance fact tables (30 tables)
for plant in ["VF01", "VF02", "VF03"]:
    for line_type in ["assembly", "paint", "body", "engine", "battery"]:
        _mfg_idx += 1
        DATASETS_BATCH4.append({
            "name": f"fact_maintenance_{line_type}_{plant.lower()}",
            "description": f"Maintenance event fact table for {line_type} line at plant {plant} — tracks breakdowns, repairs, and preventive maintenance activities.",
            "domain": _mfg_dom,
            "platform": "sap",
            "tags": ["Manufacturing", "Fact", "Maintenance", "SAP"],
            "columns": generate_fact_columns("maintenance", [
                ("plant", "VARCHAR(10)", "Plant code", True),
                ("line_type", "VARCHAR(30)", "Type of production line", True),
                ("event_date", "DATE", "Maintenance event date", True),
                ("machine_code", "VARCHAR(30)", "Machine/equipment identifier", False),
                ("maintenance_type", "VARCHAR(20)", "Type (breakdown/preventive/predictive)", False),
                ("downtime_start", "TIMESTAMP", "Downtime start timestamp", False),
                ("downtime_end", "TIMESTAMP", "Downtime end timestamp", False),
                ("downtime_minutes", "DECIMAL(10,2)", "Total downtime in minutes", False),
                ("failure_code", "VARCHAR(30)", "Failure mode code", False),
                ("failure_description", "TEXT", "Description of failure", False),
                ("root_cause", "TEXT", "Root cause analysis findings", False),
                ("repair_action", "TEXT", "Repair action taken", False),
                ("technician_id", "VARCHAR(30)", "Technician user ID", False),
                ("parts_used", "TEXT", "Spare parts used in repair", False),
                ("cost_estimate", "DECIMAL(12,2)", "Estimated repair cost", False),
                ("next_maintenance_date", "DATE", "Next scheduled maintenance date", False),
            ]),
        })

# ──────────────────────────────────────────────
# TÀI CHÍNH (finance) — ~200 additional datasets
# Current: 20, Need: 227, Add: 207
# ──────────────────────────────────────────────
_fin_dom = "finance"

# Financial fact tables per cost center/entity (80 tables)
FIN_COST_CENTERS = [
    "VF01_Manufacturing", "VF01_Assembly", "VF02_Manufacturing", "VF02_Assembly",
    "VF03_Manufacturing", "VF03_Assembly", "HQ_Administration", "HQ_Executive",
    "Sales_North", "Sales_Central", "Sales_South", "R&D_Vehicle",
    "R&D_Battery", "R&D_Software", "SupplyChain_Procurement", "SupplyChain_Logistics",
    "AfterSales_Service", "AfterSales_Warranty", "AfterSales_Parts", "HR_Operations",
    "IT_Infrastructure", "IT_Applications", "Marketing_Brand", "Marketing_Digital",
]
for cc in FIN_COST_CENTERS:
    _mfg_idx += 1
    safe_cc = cc.lower()
    DATASETS_BATCH4.append({
        "name": f"fact_actuals_{safe_cc}",
        "description": f"Financial actuals for cost center {cc} — records actual costs and revenues posted monthly.",
        "domain": _fin_dom,
        "platform": "sap",
        "tags": ["Finance", "Fact", "Actuals", "SAP"],
        "columns": generate_fact_columns("finance", [
            ("cost_center", "VARCHAR(30)", "Cost center code", True),
            ("fiscal_year", "INTEGER", "Fiscal year", True),
            ("fiscal_period", "INTEGER", "Fiscal period (1-12)", True),
            ("gl_account", "VARCHAR(20)", "General ledger account code", False),
            ("gl_account_name", "VARCHAR(100)", "GL account description", False),
            ("amount_dr", "DECIMAL(16,2)", "Debit amount posted", False),
            ("amount_cr", "DECIMAL(16,2)", "Credit amount posted", False),
            ("amount_net", "DECIMAL(16,2)", "Net amount (dr - cr)", False),
            ("currency", "VARCHAR(3)", "Currency code (VND/USD)", False),
            ("document_number", "VARCHAR(30)", "Accounting document number", False),
            ("document_date", "DATE", "Document date", False),
            ("posting_date", "DATE", "Posting date", False),
            ("user_id", "VARCHAR(30)", "User who posted the entry", False),
            ("profit_center", "VARCHAR(30)", "Profit center assignment", False),
            ("internal_order", "VARCHAR(30)", "Internal order number", False),
            ("text", "TEXT", "Document header text", False),
        ]),
    })

# Budget tables per cost center (24 tables)
for cc in FIN_COST_CENTERS[:24]:
    safe_cc = cc.lower()
    DATASETS_BATCH4.append({
        "name": f"fact_budget_{safe_cc}",
        "description": f"Budget vs actual tracking for cost center {cc} — monthly budget targets and actual comparisons.",
        "domain": _fin_dom,
        "platform": "aggregate",
        "tags": ["Finance", "Fact", "Budget", "SAP"],
        "columns": generate_agg_columns([
            ("cost_center", "VARCHAR(30)", "Cost center code", True),
            ("fiscal_year", "INTEGER", "Fiscal year", True),
            ("fiscal_period", "INTEGER", "Fiscal period (1-12)", True),
            ("gl_account_group", "VARCHAR(50)", "GL account group", False),
            ("budget_amount", "DECIMAL(16,2)", "Budgeted amount", False),
            ("actual_amount", "DECIMAL(16,2)", "Actual posted amount", False),
            ("variance_amount", "DECIMAL(16,2)", "Budget vs actual variance", False),
            ("variance_pct", "DECIMAL(5,2)", "Variance percentage", False),
            ("budget_version", "VARCHAR(20)", "Budget version (original/revised)", False),
        ]),
    })

# Finance dimension tables (20 tables)
FIN_DIM_TABLES = [
    ("dim_cost_center", "Cost center master — organizational units for cost tracking and allocation."),
    ("dim_gl_account", "General ledger account master — chart of accounts for financial reporting."),
    ("dim_profit_center", "Profit center master — profit accountability units across the organization."),
    ("dim_fiscal_calendar", "Fiscal calendar master — defines fiscal periods and year-end dates."),
    ("dim_internal_order", "Internal order master — tracking for specific projects or cost initiatives."),
    ("dim_vendor", "Vendor master — supplier and vendor financial information."),
    ("dim_customer_finance", "Customer financial master — credit limits, payment terms, and banking details."),
    ("dim_tax_code", "Tax code master — VAT and tax rates for financial transactions."),
    ("dim_asset", "Fixed asset master — depreciation, acquisition, and retirement tracking."),
    ("dim_budget_version", "Budget version master — defines budget scenarios and versions."),
]
for name, desc in FIN_DIM_TABLES:
    DATASETS_BATCH4.append({
        "name": name, "description": desc, "domain": _fin_dom, "platform": "postgres",
        "tags": ["Finance", "MasterData", "Dimension"],
        "columns": generate_dim_columns(name),
    })

# Finance aggregation tables (25 tables)
FIN_PERIODS = ["Monthly", "Quarterly", "YearToDate"]
FIN_METRICS = ["Revenue", "COGS", "GrossMargin", "OpEx", "NetIncome", "EBITDA", "CAPEX", "WorkingCapital", "CashFlow"]
for period in FIN_PERIODS[:2]:
    for metric in FIN_METRICS[:6]:
        DATASETS_BATCH4.append({
            "name": f"agg_{metric.lower()}_{period.lower()}",
            "description": f"{period} aggregation of {metric} — summarized financial metric across all cost centers and profit centers.",
            "domain": _fin_dom,
            "platform": "aggregate",
            "tags": ["Finance", "Aggregate", metric],
            "columns": generate_agg_columns([
                ("report_period", "VARCHAR(20)", "Report period label", True),
                ("fiscal_year", "INTEGER", "Fiscal year", True),
                ("total_amount", "DECIMAL(16,2)", f"Total {metric} amount", False),
                ("budget_amount", "DECIMAL(16,2)", f"Budgeted {metric} amount", False),
                ("variance_pct", "DECIMAL(5,2)", "Variance from budget percentage", False),
                ("prior_period_amount", "DECIMAL(16,2)", f"Prior period {metric} amount", False),
                ("growth_pct", "DECIMAL(5,2)", "Period-over-period growth percentage", False),
            ]),
        })

# ──────────────────────────────────────────────
# LOGISTICS (logistics) — ~65 additional datasets
# Current: 20, Need: 85, Add: 65
# ──────────────────────────────────────────────
_log_dom = "logistics"

LOG_WAREHOUSES = ["WH_HaiPhong", "WH_DaNang", "WH_HCM", "WH_HaNoi", "WH_CanTho"]
for wh in LOG_WAREHOUSES:
    safe_wh = wh.lower()
    DATASETS_BATCH4.append({
        "name": f"fact_inventory_movement_{safe_wh}",
        "description": f"Inventory movement fact table for warehouse {wh} — tracks goods receipt, issue, transfer, and adjustment transactions.",
        "domain": _log_dom,
        "platform": "sap",
        "tags": ["Logistics", "Fact", "Inventory", "SAP"],
        "columns": generate_fact_columns("inventory", [
            ("warehouse", "VARCHAR(20)", "Warehouse code", True),
            ("movement_date", "DATE", "Movement transaction date", True),
            ("material_code", "VARCHAR(30)", "Material code", True),
            ("movement_type", "VARCHAR(10)", "Movement type (GR/GI/TR/ADJ)", False),
            ("quantity", "DECIMAL(12,2)", "Movement quantity", False),
            ("uom", "VARCHAR(5)", "Unit of measure", False),
            ("stock_type", "VARCHAR(10)", "Stock type (unrestricted/QC/blocked)", False),
            ("batch_number", "VARCHAR(20)", "Batch/lot number", False),
            ("storage_location", "VARCHAR(20)", "Storage location within warehouse", False),
            ("reference_document", "VARCHAR(30)", "Reference document (PO/DO/TO)", False),
            ("created_by", "VARCHAR(30)", "User who created the transaction", False),
            ("created_at", "TIMESTAMP", "Transaction creation timestamp", False),
        ]),
    })

for wh in ["WH_HaiPhong", "WH_HCM"]:
    DATASETS_BATCH4.append({
        "name": f"agg_inventory_daily_{wh.lower()}",
        "description": f"Daily inventory snapshot for warehouse {wh} — ending balance, stock aging, and slow-moving analysis.",
        "domain": _log_dom,
        "platform": "aggregate",
        "tags": ["Logistics", "Aggregate", "Inventory", "Daily"],
        "columns": generate_agg_columns([
            ("warehouse", "VARCHAR(20)", "Warehouse code", True),
            ("snapshot_date", "DATE", "Inventory snapshot date", True),
            ("material_count", "INTEGER", "Number of distinct materials", False),
            ("total_quantity", "DECIMAL(14,2)", "Total inventory quantity", False),
            ("total_value", "DECIMAL(16,2)", "Total inventory value", False),
            ("stock_days_avg", "DECIMAL(8,2)", "Average days of stock on hand", False),
            ("slow_moving_pct", "DECIMAL(5,2)", "Percentage of slow-moving items", False),
            ("stockout_count", "INTEGER", "Number of materials with stockout", False),
        ]),
    })

LOG_DIM_TABLES = [
    ("dim_storage_location", "Storage location master — defines bins, zones, and storage types within warehouses."),
    ("dim_batch", "Batch master — batch/lot attributes including production date, expiry, and quality status."),
    ("dim_packing_unit", "Packing unit master — defines packaging types and unit conversions."),
    ("dim_shipping_point", "Shipping point master — loading points and shipping docks."),
]
for name, desc in LOG_DIM_TABLES:
    DATASETS_BATCH4.append({
        "name": name, "description": desc, "domain": _log_dom, "platform": "postgres",
        "tags": ["Logistics", "MasterData", "Dimension"],
        "columns": generate_dim_columns(name),
    })

# ──────────────────────────────────────────────
# CUNG ỨNG (supply_chain) — ~58 additional datasets
# ──────────────────────────────────────────────
_sc_dom = "supply_chain"

SC_SUPPLIERS = ["SUP_VF01", "SUP_VF02", "SUP_VF03", "SUP_VF04", "SUP_VF05", "SUP_VF06"]
for sup in SC_SUPPLIERS:
    safe_sup = sup.lower()
    DATASETS_BATCH4.append({
        "name": f"fact_purchase_order_{safe_sup}",
        "description": f"Purchase order fact table for supplier group {sup} — tracks PO issuance, receipt, invoice matching.",
        "domain": _sc_dom,
        "platform": "sap",
        "tags": ["SupplyChain", "Fact", "Procurement", "SAP"],
        "columns": generate_fact_columns("procurement", [
            ("supplier_group", "VARCHAR(20)", "Supplier group code", True),
            ("po_number", "VARCHAR(30)", "Purchase order number", True),
            ("po_date", "DATE", "Purchase order date", True),
            ("material_code", "VARCHAR(30)", "Purchased material code", False),
            ("quantity_ordered", "DECIMAL(12,2)", "Ordered quantity", False),
            ("quantity_received", "DECIMAL(12,2)", "Received quantity", False),
            ("quantity_invoiced", "DECIMAL(12,2)", "Invoiced quantity", False),
            ("unit_price", "DECIMAL(14,2)", "Unit price in VND", False),
            ("total_amount", "DECIMAL(16,2)", "Total PO amount", False),
            ("currency", "VARCHAR(3)", "Currency code", False),
            ("payment_terms", "VARCHAR(30)", "Payment terms code", False),
            ("delivery_date", "DATE", "Expected delivery date", False),
            ("actual_delivery_date", "DATE", "Actual delivery date", False),
            ("receiving_plant", "VARCHAR(10)", "Receiving plant code", False),
            ("created_by", "VARCHAR(30)", "Purchaser user ID", False),
            ("status", "VARCHAR(20)", "PO status (open/partially_received/closed/cancelled)", False),
        ]),
    })

SC_DIM_TABLES = [
    ("dim_supplier_rating", "Supplier rating master — evaluation scores and performance categories for suppliers."),
    ("dim_procurement_category", "Procurement category master — indirect/direct material categories."),
    ("dim_contract", "Contract master — long-term agreements with suppliers."),
    ("dim_sourcing_project", "Sourcing project master — RFQ and negotiation tracking."),
]
for name, desc in SC_DIM_TABLES:
    DATASETS_BATCH4.append({
        "name": name, "description": desc, "domain": _sc_dom, "platform": "postgres",
        "tags": ["SupplyChain", "MasterData", "Dimension"],
        "columns": generate_dim_columns(name),
    })

# ──────────────────────────────────────────────
# KINH DOANH (sales) — ~42 additional datasets
# ──────────────────────────────────────────────
_sls_dom = "sales"

SALES_REGIONS = ["North", "Central", "South", "Highlands"]
for region in SALES_REGIONS:
    safe_r = region.lower()
    DATASETS_BATCH4.append({
        "name": f"fact_order_{safe_r}",
        "description": f"Sales order fact table for {region} region — customer orders, fulfillment, and delivery tracking.",
        "domain": _sls_dom,
        "platform": "sap",
        "tags": ["Sales", "Fact", "Order", "SAP"],
        "columns": generate_fact_columns("sales_order", [
            ("region", "VARCHAR(20)", "Sales region", True),
            ("order_date", "DATE", "Order date", True),
            ("order_number", "VARCHAR(30)", "Sales order number", True),
            ("customer_code", "VARCHAR(20)", "Customer/dealer code", False),
            ("model_code", "VARCHAR(20)", "Vehicle model code ordered", False),
            ("quantity", "INTEGER", "Order quantity", False),
            ("unit_price", "DECIMAL(14,2)", "Unit selling price", False),
            ("total_amount", "DECIMAL(16,2)", "Total order amount", False),
            ("discount_amount", "DECIMAL(14,2)", "Discount applied", False),
            ("net_amount", "DECIMAL(16,2)", "Net amount after discount", False),
            ("currency", "VARCHAR(3)", "Currency code", False),
            ("payment_method", "VARCHAR(20)", "Payment method", False),
            ("delivery_date", "DATE", "Requested delivery date", False),
            ("actual_delivery_date", "DATE", "Actual delivery date", False),
            ("order_status", "VARCHAR(20)", "Order status (open/delivered/cancelled)", False),
            ("salesperson_id", "VARCHAR(30)", "Salesperson user ID", False),
        ]),
    })

SALES_DIM_TABLES = [
    ("dim_customer_segment", "Customer segment master — B2B/B2C/government and segment attributes."),
    ("dim_price_list", "Price list master — vehicle model pricing by region and customer segment."),
    ("dim_sales_channel", "Sales channel master — dealership, online, fleet, export channels."),
    ("dim_promotion", "Promotion master — sales campaigns, incentives, and rebate programs."),
    ("dim_dealer_territory", "Dealer territory master — geographic territory assignments for dealers."),
]
for name, desc in SALES_DIM_TABLES:
    DATASETS_BATCH4.append({
        "name": name, "description": desc, "domain": _sls_dom, "platform": "postgres",
        "tags": ["Sales", "MasterData", "Dimension"],
        "columns": generate_dim_columns(name),
    })

# ──────────────────────────────────────────────
# HẬU MÃI (after_sales) — ~32 additional datasets
# ──────────────────────────────────────────────
_as_dom = "after_sales"

AS_SERVICE_CENTERS = ["SC_HaiPhong", "SC_HaNoi", "SC_DaNang", "SC_HCM", "SC_CanTho"]
for sc in AS_SERVICE_CENTERS:
    DATASETS_BATCH4.append({
        "name": f"fact_service_order_{sc.lower()}",
        "description": f"Service order fact table for service center {sc} — customer service appointments, labor, and parts used.",
        "domain": _as_dom,
        "platform": "sap",
        "tags": ["AfterSales", "Fact", "Service", "SAP"],
        "columns": generate_fact_columns("service", [
            ("service_center", "VARCHAR(20)", "Service center code", True),
            ("order_date", "DATE", "Service order date", True),
            ("order_number", "VARCHAR(30)", "Service order number", True),
            ("customer_code", "VARCHAR(20)", "Customer identifier", False),
            ("vehicle_vin", "VARCHAR(30)", "Vehicle VIN", False),
            ("service_type", "VARCHAR(30)", "Type of service (routine/repair/warranty/recall)", False),
            ("labor_hours", "DECIMAL(8,2)", "Hours of labor charged", False),
            ("labor_rate", "DECIMAL(12,2)", "Labor rate per hour", False),
            ("parts_cost", "DECIMAL(14,2)", "Total parts cost", False),
            ("total_charge", "DECIMAL(14,2)", "Total customer charge", False),
            ("warranty_claim_amount", "DECIMAL(14,2)", "Amount claimed under warranty", False),
            ("customer_pay_amount", "DECIMAL(14,2)", "Amount paid by customer", False),
            ("technician_id", "VARCHAR(30)", "Service technician ID", False),
            ("appointment_date", "DATE", "Scheduled appointment date", False),
            ("completion_date", "DATE", "Service completion date", False),
            ("customer_satisfaction_score", "INTEGER", "Customer satisfaction rating (1-5)", False),
            ("status", "VARCHAR(20)", "Service order status", False),
        ]),
    })

AS_DIM_TABLES = [
    ("dim_service_center", "Service center master — locations, capabilities, and operating hours of service centers."),
    ("dim_warranty_type", "Warranty type master — defines warranty coverage periods and terms by vehicle model."),
    ("dim_service_package", "Service package master — predefined service packages and pricing."),
    ("dim_technician_certification", "Technician certification master — skills and certifications required for service types."),
]
for name, desc in AS_DIM_TABLES:
    DATASETS_BATCH4.append({
        "name": name, "description": desc, "domain": _as_dom, "platform": "postgres",
        "tags": ["AfterSales", "MasterData", "Dimension"],
        "columns": generate_dim_columns(name),
    })

# ──────────────────────────────────────────────
# PHÁT TRIỂN XE (vehicle_development) — add 5 more
# ──────────────────────────────────────────────
DATASETS_BATCH4.append({
    "name": "fact_test_cycle_execution",
    "description": "Test cycle execution fact table — records each test run including results, pass/fail status, and test conditions for vehicle validation.",
    "domain": "vehicle_development", "platform": "sap",
    "tags": ["VehicleDevelopment", "Fact", "Testing", "SAP"],
    "columns": generate_fact_columns("testing", [
        ("test_cycle_id", "VARCHAR(30)", "Test cycle identifier", True),
        ("test_date", "DATE", "Test execution date", True),
        ("prototype_vin", "VARCHAR(30)", "Prototype vehicle VIN", True),
        ("test_case_code", "VARCHAR(30)", "Test case code", False),
        ("test_type", "VARCHAR(30)", "Test type (durability/safety/performance/emissions)", False),
        ("test_condition", "VARCHAR(100)", "Test conditions (temperature, humidity, speed)", False),
        ("result", "VARCHAR(10)", "Test result (pass/fail/blocked)", False),
        ("failure_mode", "VARCHAR(50)", "Failure mode if failed", False),
        ("measurement_value", "DECIMAL(12,4)", "Primary measurement value", False),
        ("measurement_uom", "VARCHAR(10)", "Unit of measurement", False),
        ("tester_id", "VARCHAR(30)", "Test engineer ID", False),
        ("notes", "TEXT", "Test notes and observations", False),
    ]),
})
DATASETS_BATCH4.append({
    "name": "agg_test_summary_weekly",
    "description": "Weekly test summary aggregation — pass rates, failure trends, and test coverage by vehicle model and test type.",
    "domain": "vehicle_development", "platform": "aggregate",
    "tags": ["VehicleDevelopment", "Aggregate", "Testing"],
    "columns": generate_agg_columns([
        ("report_week", "DATE", "Report week start date", True),
        ("model_code", "VARCHAR(20)", "Vehicle model code", True),
        ("total_tests", "INTEGER", "Total tests executed", False),
        ("pass_count", "INTEGER", "Number of passed tests", False),
        ("fail_count", "INTEGER", "Number of failed tests", False),
        ("pass_rate_pct", "DECIMAL(5,2)", "Pass rate percentage", False),
        ("blocked_count", "INTEGER", "Number of blocked tests", False),
        ("avg_measurement_deviation", "DECIMAL(10,4)", "Average deviation from specification", False),
    ]),
})

# ──────────────────────────────────────────────
# VGreen — add 5 more (current: 20 → need only 4, but keep reasonable)
# ──────────────────────────────────────────────
DATASETS_BATCH4.append({
    "name": "fact_charging_session",
    "description": "EV charging session fact table — records each charging event including energy delivered, duration, and station performance.",
    "domain": "vgreen", "platform": "sap",
    "tags": ["VGreen", "Fact", "Charging", "SAP"],
    "columns": generate_fact_columns("charging", [
        ("session_id", "VARCHAR(30)", "Charging session identifier", True),
        ("station_code", "VARCHAR(20)", "Charging station code", True),
        ("start_time", "TIMESTAMP", "Charging start timestamp", True),
        ("end_time", "TIMESTAMP", "Charging end timestamp", True),
        ("duration_minutes", "DECIMAL(8,2)", "Charging duration in minutes", False),
        ("energy_kwh", "DECIMAL(10,2)", "Energy delivered in kWh", False),
        ("vehicle_vin", "VARCHAR(30)", "Vehicle VIN being charged", False),
        ("battery_soc_start", "DECIMAL(5,2)", "State of charge at start (%)", False),
        ("battery_soc_end", "DECIMAL(5,2)", "State of charge at end (%)", False),
        ("max_power_kw", "DECIMAL(8,2)", "Maximum power drawn in kW", False),
        ("avg_power_kw", "DECIMAL(8,2)", "Average power in kW", False),
        ("connector_type", "VARCHAR(10)", "Connector type (CCS/CHAdeMO/Type2)", False),
        ("ambient_temperature", "DECIMAL(4,1)", "Ambient temperature in Celsius", False),
        ("error_code", "VARCHAR(20)", "Error code if session interrupted", False),
        ("customer_id", "VARCHAR(30)", "Customer identifier", False),
        ("tariff_per_kwh", "DECIMAL(8,2)", "Tariff rate per kWh applied", False),
        ("total_cost", "DECIMAL(12,2)", "Total charging cost", False),
    ]),
})
DATASETS_BATCH4.append({
    "name": "agg_charging_daily_by_station",
    "description": "Daily charging aggregation by station — total energy, sessions, utilization rate per charging station.",
    "domain": "vgreen", "platform": "aggregate",
    "tags": ["VGreen", "Aggregate", "Charging", "Daily"],
    "columns": generate_agg_columns([
        ("report_date", "DATE", "Report date", True),
        ("station_code", "VARCHAR(20)", "Charging station code", True),
        ("total_sessions", "INTEGER", "Total charging sessions", False),
        ("total_energy_kwh", "DECIMAL(12,2)", "Total energy delivered in kWh", False),
        ("avg_duration_minutes", "DECIMAL(8,2)", "Average charging duration", False),
        ("max_power_kw", "DECIMAL(8,2)", "Peak power observed in kW", False),
        ("utilization_pct", "DECIMAL(5,2)", "Station utilization rate (plugged time / available time)", False),
        ("revenue_vnd", "DECIMAL(14,2)", "Total revenue in VND", False),
        ("error_count", "INTEGER", "Number of sessions with errors", False),
    ]),
})
