LINEAGE = [
    {
        "upstream_urns": [
            "urn:li:dataset:(urn:li:dataPlatform:sap,afko,PROD)",
            "urn:li:dataset:(urn:li:dataPlatform:sap,afvc,PROD)",
            "urn:li:dataset:(urn:li:dataPlatform:sap,mseg,PROD)",
        ],
        "downstream_urns": [
            "urn:li:dataset:(urn:li:dataPlatform:sap,stg_shop_floor_production,PROD)",
            "urn:li:dataset:(urn:li:dataPlatform:sap,fact_shop_floor_production,PROD)",
            "urn:li:dataset:(urn:li:dataPlatform:powerbi,pbi_mfg_production,PROD)",
        ],
    },
    {
        "upstream_urns": [
            "urn:li:dataset:(urn:li:dataPlatform:sap,crhd,PROD)",
        ],
        "downstream_urns": [
            "urn:li:dataset:(urn:li:dataPlatform:sap,stg_work_center,PROD)",
            "urn:li:dataset:(urn:li:dataPlatform:sap,dim_work_center,PROD)",
            "urn:li:dataset:(urn:li:dataPlatform:powerbi,pbi_mfg_line_util,PROD)",
        ],
    },
    {
        "upstream_urns": [
            "urn:li:dataset:(urn:li:dataPlatform:sap,stko,PROD)",
            "urn:li:dataset:(urn:li:dataPlatform:sap,stpo,PROD)",
        ],
        "downstream_urns": [
            "urn:li:dataset:(urn:li:dataPlatform:sap,stg_bom,PROD)",
            "urn:li:dataset:(urn:li:dataPlatform:sap,dim_material,PROD)",
            "urn:li:dataset:(urn:li:dataPlatform:powerbi,pbi_mfg_oee,PROD)",
        ],
    },
    {
        "upstream_urns": [
            "urn:li:dataset:(urn:li:dataPlatform:sap,mard,PROD)",
            "urn:li:dataset:(urn:li:dataPlatform:sap,mchb,PROD)",
        ],
        "downstream_urns": [
            "urn:li:dataset:(urn:li:dataPlatform:sap,stg_inventory_snapshot,PROD)",
            "urn:li:dataset:(urn:li:dataPlatform:sap,fact_inventory_balance,PROD)",
            "urn:li:dataset:(urn:li:dataPlatform:powerbi,pbi_log_inventory,PROD)",
        ],
    },
    {
        "upstream_urns": [
            "urn:li:dataset:(urn:li:dataPlatform:sap,ekko,PROD)",
            "urn:li:dataset:(urn:li:dataPlatform:sap,ekpo,PROD)",
        ],
        "downstream_urns": [
            "urn:li:dataset:(urn:li:dataPlatform:sap,stg_inbound_delivery,PROD)",
            "urn:li:dataset:(urn:li:dataPlatform:sap,fact_goods_movement,PROD)",
            "urn:li:dataset:(urn:li:dataPlatform:powerbi,pbi_log_stock_movement,PROD)",
        ],
    },
    {
        "upstream_urns": [
            "urn:li:dataset:(urn:li:dataPlatform:sap,stg_outbound_delivery,PROD)",
        ],
        "downstream_urns": [
            "urn:li:dataset:(urn:li:dataPlatform:sap,fact_shipment_tracking,PROD)",
            "urn:li:dataset:(urn:li:dataPlatform:powerbi,pbi_log_shipment,PROD)",
        ],
    },
    {
        "upstream_urns": [
            "urn:li:dataset:(urn:li:dataPlatform:sap,bkpf,PROD)",
            "urn:li:dataset:(urn:li:dataPlatform:sap,bseg,PROD)",
            "urn:li:dataset:(urn:li:dataPlatform:sap,ska1,PROD)",
        ],
        "downstream_urns": [
            "urn:li:dataset:(urn:li:dataPlatform:sap,stg_gl_transactions,PROD)",
            "urn:li:dataset:(urn:li:dataPlatform:sap,fact_general_ledger,PROD)",
            "urn:li:dataset:(urn:li:dataPlatform:powerbi,pbi_fin_pnl,PROD)",
        ],
    },
    {
        "upstream_urns": [
            "urn:li:dataset:(urn:li:dataPlatform:sap,lfb1,PROD)",
        ],
        "downstream_urns": [
            "urn:li:dataset:(urn:li:dataPlatform:sap,stg_ap_invoices,PROD)",
            "urn:li:dataset:(urn:li:dataPlatform:sap,fact_accounts_payable,PROD)",
            "urn:li:dataset:(urn:li:dataPlatform:powerbi,pbi_fin_ap,PROD)",
        ],
    },
    {
        "upstream_urns": [
            "urn:li:dataset:(urn:li:dataPlatform:sap,knb1,PROD)",
        ],
        "downstream_urns": [
            "urn:li:dataset:(urn:li:dataPlatform:sap,stg_ar_receipts,PROD)",
            "urn:li:dataset:(urn:li:dataPlatform:sap,fact_accounts_receivable,PROD)",
            "urn:li:dataset:(urn:li:dataPlatform:powerbi,pbi_fin_ar,PROD)",
        ],
    },
    {
        "upstream_urns": [
            "urn:li:dataset:(urn:li:dataPlatform:sap,ekko,PROD)",
            "urn:li:dataset:(urn:li:dataPlatform:sap,ekpo,PROD)",
            "urn:li:dataset:(urn:li:dataPlatform:sap,ekbe,PROD)",
        ],
        "downstream_urns": [
            "urn:li:dataset:(urn:li:dataPlatform:sap,stg_po_acknowledgment,PROD)",
            "urn:li:dataset:(urn:li:dataPlatform:sap,fact_procurement_spend,PROD)",
            "urn:li:dataset:(urn:li:dataPlatform:powerbi,pbi_sc_spend,PROD)",
        ],
    },
    {
        "upstream_urns": [
            "urn:li:dataset:(urn:li:dataPlatform:sap,lfa1,PROD)",
        ],
        "downstream_urns": [
            "urn:li:dataset:(urn:li:dataPlatform:sap,stg_supplier_master,PROD)",
            "urn:li:dataset:(urn:li:dataPlatform:sap,fact_supplier_performance,PROD)",
            "urn:li:dataset:(urn:li:dataPlatform:powerbi,pbi_sc_supplier,PROD)",
        ],
    },
    {
        "upstream_urns": [
            "urn:li:dataset:(urn:li:dataPlatform:sap,stg_contract_terms,PROD)",
        ],
        "downstream_urns": [
            "urn:li:dataset:(urn:li:dataPlatform:sap,fact_po_fulfillment,PROD)",
            "urn:li:dataset:(urn:li:dataPlatform:powerbi,pbi_sc_contract,PROD)",
        ],
    },
    {
        "upstream_urns": [
            "urn:li:dataset:(urn:li:dataPlatform:sap,vbak,PROD)",
            "urn:li:dataset:(urn:li:dataPlatform:sap,vbap,PROD)",
            "urn:li:dataset:(urn:li:dataPlatform:sap,kna1,PROD)",
        ],
        "downstream_urns": [
            "urn:li:dataset:(urn:li:dataPlatform:sap,stg_customer_order,PROD)",
            "urn:li:dataset:(urn:li:dataPlatform:sap,fact_vehicle_sales,PROD)",
            "urn:li:dataset:(urn:li:dataPlatform:powerbi,pbi_sales_daily,PROD)",
        ],
    },
    {
        "upstream_urns": [
            "urn:li:dataset:(urn:li:dataPlatform:sap,stg_lead,PROD)",
        ],
        "downstream_urns": [
            "urn:li:dataset:(urn:li:dataPlatform:sap,fact_dealer_performance,PROD)",
            "urn:li:dataset:(urn:li:dataPlatform:powerbi,pbi_sales_dealer,PROD)",
        ],
    },
    {
        "upstream_urns": [
            "urn:li:dataset:(urn:li:dataPlatform:sap,stg_vehicle_allocation,PROD)",
            "urn:li:dataset:(urn:li:dataPlatform:sap,dim_model,PROD)",
        ],
        "downstream_urns": [
            "urn:li:dataset:(urn:li:dataPlatform:sap,fact_order_fulfillment,PROD)",
            "urn:li:dataset:(urn:li:dataPlatform:powerbi,pbi_sales_pipeline,PROD)",
        ],
    },
    {
        "upstream_urns": [
            "urn:li:dataset:(urn:li:dataPlatform:sap,qmel,PROD)",
            "urn:li:dataset:(urn:li:dataPlatform:sap,qmsm,PROD)",
        ],
        "downstream_urns": [
            "urn:li:dataset:(urn:li:dataPlatform:sap,stg_warranty_claim,PROD)",
            "urn:li:dataset:(urn:li:dataPlatform:sap,fact_warranty_claim,PROD)",
            "urn:li:dataset:(urn:li:dataPlatform:powerbi,pbi_as_warranty,PROD)",
        ],
    },
    {
        "upstream_urns": [
            "urn:li:dataset:(urn:li:dataPlatform:sap,stg_service_appointment,PROD)",
        ],
        "downstream_urns": [
            "urn:li:dataset:(urn:li:dataPlatform:sap,fact_service_visit,PROD)",
            "urn:li:dataset:(urn:li:dataPlatform:powerbi,pbi_as_service,PROD)",
        ],
    },
    {
        "upstream_urns": [
            "urn:li:dataset:(urn:li:dataPlatform:sap,stg_parts_order,PROD)",
        ],
        "downstream_urns": [
            "urn:li:dataset:(urn:li:dataPlatform:sap,fact_parts_inventory,PROD)",
            "urn:li:dataset:(urn:li:dataPlatform:powerbi,pbi_as_parts,PROD)",
        ],
    },
    {
        "upstream_urns": [
            "urn:li:dataset:(urn:li:dataPlatform:sap,plm_doc,PROD)",
            "urn:li:dataset:(urn:li:dataPlatform:sap,draw,PROD)",
        ],
        "downstream_urns": [
            "urn:li:dataset:(urn:li:dataPlatform:sap,stg_design_release,PROD)",
            "urn:li:dataset:(urn:li:dataPlatform:sap,fact_dv_pv_test_result,PROD)",
            "urn:li:dataset:(urn:li:dataPlatform:powerbi,pbi_vd_test,PROD)",
        ],
    },
    {
        "upstream_urns": [
            "urn:li:dataset:(urn:li:dataPlatform:sap,cvers,PROD)",
            "urn:li:dataset:(urn:li:dataPlatform:sap,aenr,PROD)",
        ],
        "downstream_urns": [
            "urn:li:dataset:(urn:li:dataPlatform:sap,stg_engineering_change,PROD)",
            "urn:li:dataset:(urn:li:dataPlatform:sap,fact_change_implementation,PROD)",
            "urn:li:dataset:(urn:li:dataPlatform:powerbi,pbi_vd_change,PROD)",
        ],
    },
    {
        "upstream_urns": [
            "urn:li:dataset:(urn:li:dataPlatform:sap,stg_prototype_build,PROD)",
        ],
        "downstream_urns": [
            "urn:li:dataset:(urn:li:dataPlatform:sap,fact_program_milestone,PROD)",
            "urn:li:dataset:(urn:li:dataPlatform:powerbi,pbi_vd_program,PROD)",
        ],
    },
    {
        "upstream_urns": [
            "urn:li:dataset:(urn:li:dataPlatform:sap,stg_battery_production,PROD)",
        ],
        "downstream_urns": [
            "urn:li:dataset:(urn:li:dataPlatform:sap,fact_battery_cell_production,PROD)",
            "urn:li:dataset:(urn:li:dataPlatform:powerbi,pbi_vg_battery,PROD)",
        ],
    },
    {
        "upstream_urns": [
            "urn:li:dataset:(urn:li:dataPlatform:sap,stg_charging_sessions,PROD)",
        ],
        "downstream_urns": [
            "urn:li:dataset:(urn:li:dataPlatform:sap,fact_charging_network_usage,PROD)",
            "urn:li:dataset:(urn:li:dataPlatform:powerbi,pbi_vg_charging,PROD)",
        ],
    },
    {
        "upstream_urns": [
            "urn:li:dataset:(urn:li:dataPlatform:sap,stg_energy_consumption,PROD)",
        ],
        "downstream_urns": [
            "urn:li:dataset:(urn:li:dataPlatform:sap,fact_energy_management,PROD)",
            "urn:li:dataset:(urn:li:dataPlatform:powerbi,pbi_vg_energy,PROD)",
        ],
    },
    {
        "upstream_urns": [
            "urn:li:dataset:(urn:li:dataPlatform:great_expectations,data_quality_rules,PROD)",
            "urn:li:dataset:(urn:li:dataPlatform:great_expectations,data_quality_results,PROD)",
        ],
        "downstream_urns": [
            "urn:li:dataset:(urn:li:dataPlatform:great_expectations,data_quality_scorecard,PROD)",
            "urn:li:dataset:(urn:li:dataPlatform:powerbi,pbi_dg_quality,PROD)",
        ],
    },
    {
        "upstream_urns": [
            "urn:li:dataset:(urn:li:dataPlatform:audit,data_access_audit,PROD)",
            "urn:li:dataset:(urn:li:dataPlatform:audit,data_breach_log,PROD)",
        ],
        "downstream_urns": [
            "urn:li:dataset:(urn:li:dataPlatform:powerbi,pbi_dg_compliance,PROD)",
        ],
    },
]
