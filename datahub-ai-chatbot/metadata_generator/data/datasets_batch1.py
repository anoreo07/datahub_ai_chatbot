DATASETS_BATCH1 = [
    {
        "name": 'sap_crhd',
        "description": 'Work Center Header - master data for production work centers',
        "domain": 'manufacturing',
        "platform": 'sap',
        "tags": ['Manufacturing', 'MasterData', 'SAP', 'Certified', 'Gold'],
        "columns": [
        {
            "name": 'objid',
            "description": 'Work center object ID',
            "datatype": 'VARCHAR(50)',
            "nullable": False,
            "business_definition": 'Unique identifier for a work center within the production system.',
            "sample_value": 'WC-100'
        },
        {
            "name": 'werks',
            "description": 'Plant',
            "datatype": 'VARCHAR(10)',
            "nullable": False,
            "business_definition": 'Plant code identifying the manufacturing facility.',
            "sample_value": 'VF01'
        },
        {
            "name": 'arbpl',
            "description": 'Work center description / location',
            "datatype": 'VARCHAR(80)',
            "nullable": True,
            "business_definition": 'Descriptive name or location identifier for the work center on the shop floor.',
            "sample_value": 'Assembly Line 1 - Hai Phong'
        },
        {
            "name": 'ktext',
            "description": 'Work center name',
            "datatype": 'VARCHAR(80)',
            "nullable": True,
            "business_definition": 'Full name of the work center used in production reporting.',
            "sample_value": 'VF8 Final Assembly Line'
        },
        {
            "name": 'verwe',
            "description": 'Work center category',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Categorization of the work center type such as machine or assembly line.',
            "sample_value": '0001'
        },
        {
            "name": 'kapar',
            "description": 'Capacity planner group',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Group code for the capacity planner responsible for scheduling.',
            "sample_value": 'CPG-01'
        },
        {
            "name": 'created_at',
            "description": 'Record creation timestamp',
            "datatype": 'TIMESTAMP',
            "nullable": True,
            "business_definition": 'Date and time when the work center master record was created.',
            "sample_value": '2023-06-15 08:30:00'
        }
        ]
    },
    {
        "name": 'sap_plpo',
        "description": 'Routing - task list operations and sequences for production',
        "domain": 'manufacturing',
        "platform": 'sap',
        "tags": ['Manufacturing', 'MasterData', 'SAP', 'Gold'],
        "columns": [
        {
            "name": 'plnnr',
            "description": 'Routing number',
            "datatype": 'VARCHAR(30)',
            "nullable": False,
            "business_definition": 'Unique routing number identifying the sequence of operations to produce a material.',
            "sample_value": 'R-VF8-001'
        },
        {
            "name": 'plnal',
            "description": 'Group counter',
            "datatype": 'VARCHAR(10)',
            "nullable": False,
            "business_definition": 'Counter within a routing group to differentiate alternative versions.',
            "sample_value": '01'
        },
        {
            "name": 'vornr',
            "description": 'Operation number',
            "datatype": 'VARCHAR(10)',
            "nullable": False,
            "business_definition": 'Sequential number identifying the position of an operation within the routing.',
            "sample_value": '0020'
        },
        {
            "name": 'arbpl',
            "description": 'Work center',
            "datatype": 'VARCHAR(50)',
            "nullable": True,
            "business_definition": 'Work center assigned to execute this operation in the routing.',
            "sample_value": 'WC-100'
        },
        {
            "name": 'steus',
            "description": 'Control key',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Control key that determines scheduling, costing, or confirmation functions.',
            "sample_value": 'PP01'
        },
        {
            "name": 'ltxa1',
            "description": 'Operation short text',
            "datatype": 'VARCHAR(80)',
            "nullable": True,
            "business_definition": 'Brief description of the operation activity performed during production.',
            "sample_value": 'Chassis welding - VF8'
        },
        {
            "name": 'meinh',
            "description": 'Base unit of measure',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Unit of measure for operation duration or output quantity.',
            "sample_value": 'MIN'
        },
        {
            "name": 'vge01',
            "description": 'Standard value 1 (setup time)',
            "datatype": 'DECIMAL(10,2)',
            "nullable": True,
            "business_definition": 'Planned setup time in minutes to prepare the work center.',
            "sample_value": '15.00'
        },
        {
            "name": 'vge02',
            "description": 'Standard value 2 (machine time)',
            "datatype": 'DECIMAL(10,2)',
            "nullable": True,
            "business_definition": 'Planned machine processing time in minutes for the operation.',
            "sample_value": '45.00'
        }
        ]
    },
    {
        "name": 'sap_afko',
        "description": 'Production Order Header - master production order data',
        "domain": 'manufacturing',
        "platform": 'sap',
        "tags": ['Manufacturing', 'Transactional', 'SAP', 'Critical', 'Certified', 'Gold'],
        "columns": [
        {
            "name": 'aufnr',
            "description": 'Production order number',
            "datatype": 'VARCHAR(30)',
            "nullable": False,
            "business_definition": 'Unique production order number for planning and executing manufacturing runs.',
            "sample_value": 'PO-2024-10045'
        },
        {
            "name": 'werks',
            "description": 'Plant',
            "datatype": 'VARCHAR(10)',
            "nullable": False,
            "business_definition": 'Plant where the production order is executed.',
            "sample_value": 'VF01'
        },
        {
            "name": 'matnr',
            "description": 'Material number',
            "datatype": 'VARCHAR(40)',
            "nullable": False,
            "business_definition": 'Material number of the product being produced by this order.',
            "sample_value": 'M-VF8-001'
        },
        {
            "name": 'gstrp',
            "description": 'Basic start date',
            "datatype": 'DATE',
            "nullable": True,
            "business_definition": 'Scheduled start date for the production order.',
            "sample_value": '2024-06-01'
        },
        {
            "name": 'gltrp',
            "description": 'Basic finish date',
            "datatype": 'DATE',
            "nullable": True,
            "business_definition": 'Scheduled completion date for the production order.',
            "sample_value": '2024-06-05'
        },
        {
            "name": 'pwmng',
            "description": 'Total order quantity',
            "datatype": 'DECIMAL(15,2)',
            "nullable": True,
            "business_definition": 'Planned total quantity of units to be produced under this order.',
            "sample_value": '500.00'
        },
        {
            "name": 'meins',
            "description": 'Unit of measure',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Unit of measure for the production order quantity.',
            "sample_value": 'EA'
        },
        {
            "name": 'phast',
            "description": 'Production order status',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'System status indicating the lifecycle phase such as created or released.',
            "sample_value": 'REL'
        }
        ]
    },
    {
        "name": 'sap_afvc',
        "description": 'Production Order Operation - individual operations within a production order',
        "domain": 'manufacturing',
        "platform": 'sap',
        "tags": ['Manufacturing', 'Transactional', 'SAP', 'Gold'],
        "columns": [
        {
            "name": 'aufpl',
            "description": 'Order internal ID',
            "datatype": 'VARCHAR(30)',
            "nullable": False,
            "business_definition": 'Internal SAP identifier linking the operation to its parent production order.',
            "sample_value": '10045'
        },
        {
            "name": 'aplzl',
            "description": 'Internal operation counter',
            "datatype": 'VARCHAR(10)',
            "nullable": False,
            "business_definition": 'Internal counter uniquely identifying the operation within the order.',
            "sample_value": '01'
        },
        {
            "name": 'vornr',
            "description": 'Operation number',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Operation number from the routing copied into the production order.',
            "sample_value": '0010'
        },
        {
            "name": 'arbpl',
            "description": 'Work center',
            "datatype": 'VARCHAR(50)',
            "nullable": True,
            "business_definition": 'Work center assigned to execute this order operation.',
            "sample_value": 'WC-105'
        },
        {
            "name": 'ltxa1',
            "description": 'Operation description',
            "datatype": 'VARCHAR(80)',
            "nullable": True,
            "business_definition": 'Description of the operation activity for shop floor execution.',
            "sample_value": 'Motor assembly - VF8'
        },
        {
            "name": 'ism01',
            "description": 'Actual setup time',
            "datatype": 'DECIMAL(10,2)',
            "nullable": True,
            "business_definition": 'Actual setup time recorded via confirmation for this operation.',
            "sample_value": '12.50'
        },
        {
            "name": 'ism02',
            "description": 'Actual machine time',
            "datatype": 'DECIMAL(10,2)',
            "nullable": True,
            "business_definition": 'Actual machine processing time recorded for this operation.',
            "sample_value": '42.30'
        },
        {
            "name": 'xmnge',
            "description": 'Confirmed yield quantity',
            "datatype": 'DECIMAL(15,2)',
            "nullable": True,
            "business_definition": 'Quantity of good units confirmed as completed for this operation.',
            "sample_value": '485.00'
        }
        ]
    },
    {
        "name": 'sap_stko',
        "description": 'BOM Header - bill of materials header records',
        "domain": 'manufacturing',
        "platform": 'sap',
        "tags": ['Manufacturing', 'MasterData', 'SAP', 'Certified', 'Gold'],
        "columns": [
        {
            "name": 'stlnr',
            "description": 'BOM number',
            "datatype": 'VARCHAR(30)',
            "nullable": False,
            "business_definition": 'Unique bill of materials number defining the structural parent for a product.',
            "sample_value": 'BOM-VF8-001'
        },
        {
            "name": 'werks',
            "description": 'Plant',
            "datatype": 'VARCHAR(10)',
            "nullable": False,
            "business_definition": 'Plant where the BOM is valid for production.',
            "sample_value": 'VF01'
        },
        {
            "name": 'matnr',
            "description": 'Material number of BOM header',
            "datatype": 'VARCHAR(40)',
            "nullable": False,
            "business_definition": 'Material number representing the parent assembly or finished good.',
            "sample_value": 'M-VF8-001'
        },
        {
            "name": 'stlan',
            "description": 'BOM usage',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Indicates the BOM purpose such as production, engineering, or cost estimation.',
            "sample_value": '1'
        },
        {
            "name": 'loekz',
            "description": 'Deletion flag',
            "datatype": 'VARCHAR(1)',
            "nullable": True,
            "business_definition": 'Flag indicating whether the BOM has been marked for deletion.',
            "sample_value": 'N'
        },
        {
            "name": 'stlal',
            "description": 'Alternative BOM',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Alternative BOM counter when multiple BOM versions exist for the same material.',
            "sample_value": '01'
        },
        {
            "name": 'datuv',
            "description": 'Valid-from date',
            "datatype": 'DATE',
            "nullable": True,
            "business_definition": 'Start date from which the BOM is effective for production use.',
            "sample_value": '2024-01-01'
        }
        ]
    },
    {
        "name": 'sap_stpo',
        "description": 'BOM Item - individual components within a bill of materials',
        "domain": 'manufacturing',
        "platform": 'sap',
        "tags": ['Manufacturing', 'MasterData', 'SAP', 'Gold'],
        "columns": [
        {
            "name": 'stlkn',
            "description": 'BOM item node number',
            "datatype": 'VARCHAR(10)',
            "nullable": False,
            "business_definition": 'Internal node number uniquely identifying the item position within the BOM.',
            "sample_value": '0010'
        },
        {
            "name": 'stlnr',
            "description": 'BOM number',
            "datatype": 'VARCHAR(30)',
            "nullable": False,
            "business_definition": 'BOM number linking the item back to the header record.',
            "sample_value": 'BOM-VF8-001'
        },
        {
            "name": 'idnrk',
            "description": 'Component material number',
            "datatype": 'VARCHAR(40)',
            "nullable": False,
            "business_definition": 'Material number of the component that goes into the parent product.',
            "sample_value": 'M-BAT-789'
        },
        {
            "name": 'menge',
            "description": 'Component quantity',
            "datatype": 'DECIMAL(15,3)',
            "nullable": True,
            "business_definition": 'Quantity of the component required to produce one unit of the parent assembly.',
            "sample_value": '2.000'
        },
        {
            "name": 'meins',
            "description": 'Unit of measure',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Unit of measure for the component quantity.',
            "sample_value": 'EA'
        },
        {
            "name": 'postp',
            "description": 'Item category',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Category of the BOM item such as stock item, non-stock item, or document.',
            "sample_value": 'L'
        },
        {
            "name": 'sankz',
            "description": 'Scrap percentage',
            "datatype": 'DECIMAL(5,2)',
            "nullable": True,
            "business_definition": 'Expected scrap percentage for this component during manufacturing.',
            "sample_value": '1.50'
        },
        {
            "name": 'sortf',
            "description": 'Sort string',
            "datatype": 'VARCHAR(20)',
            "nullable": True,
            "business_definition": 'Alphanumeric field for sorting BOM items in a preferred sequence.',
            "sample_value": 'A001'
        }
        ]
    },
    {
        "name": 'sap_marc',
        "description": 'Plant Material - material-level plant data',
        "domain": 'manufacturing',
        "platform": 'sap',
        "tags": ['Manufacturing', 'MasterData', 'SAP', 'Certified', 'Gold'],
        "columns": [
        {
            "name": 'matnr',
            "description": 'Material number',
            "datatype": 'VARCHAR(40)',
            "nullable": False,
            "business_definition": 'Material number uniquely identifying a material across all plants.',
            "sample_value": 'M-VF8-001'
        },
        {
            "name": 'werks',
            "description": 'Plant',
            "datatype": 'VARCHAR(10)',
            "nullable": False,
            "business_definition": 'Plant code for which the material plant data is maintained.',
            "sample_value": 'VF01'
        },
        {
            "name": 'dispo',
            "description": 'MRP controller',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'MRP controller code responsible for material planning and procurement.',
            "sample_value": 'MRP-01'
        },
        {
            "name": 'dispr',
            "description": 'MRP type',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'MRP planning type defining consumption-based or MRP-based planning.',
            "sample_value": 'PD'
        },
        {
            "name": 'ekgrp',
            "description": 'Purchasing group',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Purchasing group code responsible for procurement of this material.',
            "sample_value": 'PUR-01'
        },
        {
            "name": 'einsme',
            "description": 'Unit of measure',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Base unit of measure for inventory and production planning.',
            "sample_value": 'EA'
        },
        {
            "name": 'lgort',
            "description": 'Default storage location',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Default storage location for goods receipt of this material at the plant.',
            "sample_value": 'FG01'
        },
        {
            "name": 'mtart',
            "description": 'Material type',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Classification such as raw material, finished good, or semi-finished.',
            "sample_value": 'FERT'
        }
        ]
    },
    {
        "name": 'sap_mkal',
        "description": 'Production Version - production version for a material',
        "domain": 'manufacturing',
        "platform": 'sap',
        "tags": ['Manufacturing', 'MasterData', 'SAP', 'Gold'],
        "columns": [
        {
            "name": 'matnr',
            "description": 'Material number',
            "datatype": 'VARCHAR(40)',
            "nullable": False,
            "business_definition": 'Material number for which the production version is defined.',
            "sample_value": 'M-VF8-001'
        },
        {
            "name": 'werks',
            "description": 'Plant',
            "datatype": 'VARCHAR(10)',
            "nullable": False,
            "business_definition": 'Plant where the production version is valid.',
            "sample_value": 'VF01'
        },
        {
            "name": 'verid',
            "description": 'Production version ID',
            "datatype": 'VARCHAR(10)',
            "nullable": False,
            "business_definition": 'Unique identifier specifying the BOM and routing combination.',
            "sample_value": 'PV-01'
        },
        {
            "name": 'stlnr',
            "description": 'BOM number',
            "datatype": 'VARCHAR(30)',
            "nullable": True,
            "business_definition": 'BOM number linked to this production version for material explosion.',
            "sample_value": 'BOM-VF8-001'
        },
        {
            "name": 'plnnr',
            "description": 'Routing number',
            "datatype": 'VARCHAR(30)',
            "nullable": True,
            "business_definition": 'Routing number linked to this production version for operation sequencing.',
            "sample_value": 'R-VF8-001'
        },
        {
            "name": 'datuv',
            "description": 'Valid-from date',
            "datatype": 'DATE',
            "nullable": True,
            "business_definition": 'Start date from which the production version is valid for planning.',
            "sample_value": '2024-01-01'
        },
        {
            "name": 'verid_text',
            "description": 'Production version description',
            "datatype": 'VARCHAR(80)',
            "nullable": True,
            "business_definition": 'Text description of the production version for identification.',
            "sample_value": 'VF8 Standard Assembly PV'
        }
        ]
    },
    {
        "name": 'sap_mseg',
        "description": 'Goods Movement - material document line items for inventory movements',
        "domain": 'manufacturing',
        "platform": 'sap',
        "tags": ['Manufacturing', 'Transactional', 'SAP', 'Critical', 'Gold'],
        "columns": [
        {
            "name": 'mblnr',
            "description": 'Material document number',
            "datatype": 'VARCHAR(30)',
            "nullable": False,
            "business_definition": 'Document number representing the header of a goods movement transaction.',
            "sample_value": 'GD-2024-56789'
        },
        {
            "name": 'zeile',
            "description": 'Line item number',
            "datatype": 'VARCHAR(10)',
            "nullable": False,
            "business_definition": 'Sequential line number within the goods movement document.',
            "sample_value": '001'
        },
        {
            "name": 'matnr',
            "description": 'Material number',
            "datatype": 'VARCHAR(40)',
            "nullable": False,
            "business_definition": 'Material number of the goods being moved.',
            "sample_value": 'M-VF8-001'
        },
        {
            "name": 'werks',
            "description": 'Plant',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Plant where the goods movement is posted.',
            "sample_value": 'VF01'
        },
        {
            "name": 'lgort',
            "description": 'Storage location',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Storage location from or to which goods are moved.',
            "sample_value": 'FG01'
        },
        {
            "name": 'menge',
            "description": 'Movement quantity',
            "datatype": 'DECIMAL(15,3)',
            "nullable": True,
            "business_definition": 'Quantity of goods moved in this line item.',
            "sample_value": '100.000'
        },
        {
            "name": 'meins',
            "description": 'Unit of measure',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Unit of measure for the movement quantity.',
            "sample_value": 'EA'
        },
        {
            "name": 'bwart',
            "description": 'Movement type',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'SAP movement type code such as 101 for goods receipt or 201 for goods issue.',
            "sample_value": '101'
        },
        {
            "name": 'cpudt',
            "description": 'Posting date',
            "datatype": 'DATE',
            "nullable": True,
            "business_definition": 'Date on which the goods movement was posted in the system.',
            "sample_value": '2024-06-10'
        }
        ]
    },
    {
        "name": 'sap_kalkt02',
        "description": 'Cost Estimate - cost estimate for materials',
        "domain": 'manufacturing',
        "platform": 'sap',
        "tags": ['Manufacturing', 'MasterData', 'SAP', 'Finance', 'Gold'],
        "columns": [
        {
            "name": 'kalnr',
            "description": 'Cost estimate number',
            "datatype": 'VARCHAR(20)',
            "nullable": False,
            "business_definition": 'Unique internal number identifying a cost estimate run for a material.',
            "sample_value": 'CE-2024-100'
        },
        {
            "name": 'matnr',
            "description": 'Material number',
            "datatype": 'VARCHAR(40)',
            "nullable": False,
            "business_definition": 'Material number for which the cost estimate is created.',
            "sample_value": 'M-VF8-001'
        },
        {
            "name": 'werks',
            "description": 'Plant',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Plant for which the standard cost is estimated.',
            "sample_value": 'VF01'
        },
        {
            "name": 'bwtar',
            "description": 'Valuation type',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Valuation type for the material such as different procurement categories.',
            "sample_value": 'STD'
        },
        {
            "name": 'stprs',
            "description": 'Standard price',
            "datatype": 'DECIMAL(15,2)',
            "nullable": True,
            "business_definition": 'Calculated standard price for the material based on cost components in VND.',
            "sample_value": '1250000.00'
        },
        {
            "name": 'peinh',
            "description": 'Price unit',
            "datatype": 'INTEGER',
            "nullable": True,
            "business_definition": 'Price unit quantity to which the standard price applies.',
            "sample_value": '1'
        },
        {
            "name": 'lkdat',
            "description": 'Costing date',
            "datatype": 'DATE',
            "nullable": True,
            "business_definition": 'Date on which the cost estimate was last calculated or released.',
            "sample_value": '2024-05-01'
        },
        {
            "name": 'verid',
            "description": 'Production version',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Production version used in the cost estimate for routing and BOM selection.',
            "sample_value": 'PV-01'
        }
        ]
    },
    {
        "name": 'stg_production',
        "description": 'Staging table for raw production data ingested from SAP and IoT sensors',
        "domain": 'manufacturing',
        "platform": 'sap',
        "tags": ['Manufacturing', 'Analytics', 'Bronze', 'RealTime'],
        "columns": [
        {
            "name": 'source_system',
            "description": 'Source system identifier',
            "datatype": 'VARCHAR(50)',
            "nullable": False,
            "business_definition": 'Identifies the originating system of the production record such as SAP ECC or MES.',
            "sample_value": 'SAP_ECC'
        },
        {
            "name": 'record_id',
            "description": 'Staging record UUID',
            "datatype": 'VARCHAR(100)',
            "nullable": False,
            "business_definition": 'Universally unique identifier for the staging record to ensure idempotent processing.',
            "sample_value": '550e8400-e29b-41d4-a716-446655440000'
        },
        {
            "name": 'payload',
            "description": 'Raw JSON payload',
            "datatype": 'TEXT',
            "nullable": True,
            "business_definition": 'Raw JSON payload containing production event data extracted from the source system.',
            "sample_value": '{"order":"PO-2024-10045","operation":"0010","qty":500}'
        },
        {
            "name": 'ingestion_ts',
            "description": 'Ingestion timestamp',
            "datatype": 'TIMESTAMP',
            "nullable": False,
            "business_definition": 'Timestamp when the record was ingested into the staging layer.',
            "sample_value": '2024-06-10 14:30:00'
        },
        {
            "name": 'batch_id',
            "description": 'Batch run identifier',
            "datatype": 'VARCHAR(50)',
            "nullable": True,
            "business_definition": 'Identifier for the batch ingestion job that loaded this record.',
            "sample_value": 'BATCH-2024-06-10-001'
        },
        {
            "name": 'status',
            "description": 'Processing status',
            "datatype": 'VARCHAR(20)',
            "nullable": True,
            "business_definition": 'Current processing status such as raw, validated, or error.',
            "sample_value": 'raw'
        },
        {
            "name": 'error_message',
            "description": 'Error description',
            "datatype": 'TEXT',
            "nullable": True,
            "business_definition": 'Error message populated when validation or transformation fails.',
            "sample_value": 'None'
        }
        ]
    },
    {
        "name": 'stg_quality_inspection',
        "description": 'Staging table for quality inspection raw data from SAP QM and devices',
        "domain": 'manufacturing',
        "platform": 'sap',
        "tags": ['Manufacturing', 'Analytics', 'Bronze', 'Critical'],
        "columns": [
        {
            "name": 'inspection_id',
            "description": 'Inspection lot UUID',
            "datatype": 'VARCHAR(100)',
            "nullable": False,
            "business_definition": 'Unique identifier for the quality inspection lot from SAP QM or MES.',
            "sample_value": 'IQC-2024-88231'
        },
        {
            "name": 'material',
            "description": 'Inspected material',
            "datatype": 'VARCHAR(40)',
            "nullable": False,
            "business_definition": 'Material number of the product or component being inspected.',
            "sample_value": 'M-VF8-001'
        },
        {
            "name": 'inspector_id',
            "description": 'Inspector operator code',
            "datatype": 'VARCHAR(50)',
            "nullable": True,
            "business_definition": 'Employee code of the quality inspector who performed the check.',
            "sample_value": 'EMP-4521'
        },
        {
            "name": 'result',
            "description": 'Inspection result',
            "datatype": 'VARCHAR(20)',
            "nullable": True,
            "business_definition": 'Overall inspection result: accepted, rejected, or rework.',
            "sample_value": 'accepted'
        },
        {
            "name": 'defect_count',
            "description": 'Number of defects found',
            "datatype": 'INTEGER',
            "nullable": True,
            "business_definition": 'Total count of defects identified during the inspection.',
            "sample_value": '0'
        },
        {
            "name": 'inspection_ts',
            "description": 'Inspection timestamp',
            "datatype": 'TIMESTAMP',
            "nullable": True,
            "business_definition": 'Date and time when the inspection was performed.',
            "sample_value": '2024-06-10 10:15:00'
        },
        {
            "name": 'source_system',
            "description": 'Originating system identifier',
            "datatype": 'VARCHAR(50)',
            "nullable": True,
            "business_definition": 'Source system from which the inspection data was extracted.',
            "sample_value": 'SAP_QM'
        }
        ]
    },
    {
        "name": 'fact_shop_floor_production',
        "description": 'Shop floor production fact table recording every production confirmation event',
        "domain": 'manufacturing',
        "platform": 'sap',
        "tags": ['Manufacturing', 'Analytics', 'Critical', 'Certified', 'Gold', 'RealTime'],
        "columns": [
        {
            "name": 'confirmation_id',
            "description": 'Production confirmation unique ID',
            "datatype": 'VARCHAR(100)',
            "nullable": False,
            "business_definition": 'Unique identifier for each production confirmation event.',
            "sample_value": 'CONF-2024-0012345'
        },
        {
            "name": 'order_id',
            "description": 'Production order ID',
            "datatype": 'VARCHAR(30)',
            "nullable": True,
            "business_definition": 'Production order number associated with the confirmation.',
            "sample_value": 'PO-2024-10045'
        },
        {
            "name": 'material_id',
            "description": 'Material produced',
            "datatype": 'VARCHAR(40)',
            "nullable": True,
            "business_definition": 'Material number of the product confirmed as produced.',
            "sample_value": 'M-VF8-001'
        },
        {
            "name": 'work_center_id',
            "description": 'Work center performing the operation',
            "datatype": 'VARCHAR(50)',
            "nullable": True,
            "business_definition": 'Work center where the production confirmation was recorded.',
            "sample_value": 'WC-100'
        },
        {
            "name": 'confirmed_qty',
            "description": 'Confirmed good quantity',
            "datatype": 'DECIMAL(15,2)',
            "nullable": True,
            "business_definition": 'Quantity of units confirmed as good output.',
            "sample_value": '485.00'
        },
        {
            "name": 'scrap_qty',
            "description": 'Scrap quantity',
            "datatype": 'DECIMAL(15,2)',
            "nullable": True,
            "business_definition": 'Quantity scrapped during the operation due to quality defects.',
            "sample_value": '15.00'
        },
        {
            "name": 'setup_time',
            "description": 'Actual setup time (minutes)',
            "datatype": 'DECIMAL(10,2)',
            "nullable": True,
            "business_definition": 'Actual setup duration recorded for the operation in minutes.',
            "sample_value": '12.50'
        },
        {
            "name": 'run_time',
            "description": 'Actual run time (minutes)',
            "datatype": 'DECIMAL(10,2)',
            "nullable": True,
            "business_definition": 'Actual processing time recorded for the operation in minutes.',
            "sample_value": '42.30'
        },
        {
            "name": 'confirmation_date',
            "description": 'Confirmation posting date',
            "datatype": 'DATE',
            "nullable": True,
            "business_definition": 'Date on which the production confirmation was posted.',
            "sample_value": '2024-06-10'
        },
        {
            "name": 'shift',
            "description": 'Production shift code',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Shift during which production was completed such as morning or night.',
            "sample_value": 'CA'
        }
        ]
    },
    {
        "name": 'fact_mfg_quality_inspection',
        "description": 'Quality inspection fact table recording inspection results at lot and characteristic level',
        "domain": 'manufacturing',
        "platform": 'sap',
        "tags": ['Manufacturing', 'Analytics', 'Critical', 'Certified', 'Gold'],
        "columns": [
        {
            "name": 'inspection_lot_id',
            "description": 'Inspection lot identifier',
            "datatype": 'VARCHAR(50)',
            "nullable": False,
            "business_definition": 'SAP inspection lot number grouping all quality checks for a batch or production run.',
            "sample_value": 'IQC-2024-88231'
        },
        {
            "name": 'material_id',
            "description": 'Inspected material',
            "datatype": 'VARCHAR(40)',
            "nullable": True,
            "business_definition": 'Material number of the product or component under inspection.',
            "sample_value": 'M-VF8-001'
        },
        {
            "name": 'characteristic',
            "description": 'Inspection characteristic code',
            "datatype": 'VARCHAR(50)',
            "nullable": True,
            "business_definition": 'Code of the quality characteristic being inspected such as dimension or weight.',
            "sample_value": 'DIM-001'
        },
        {
            "name": 'measured_value',
            "description": 'Measured value',
            "datatype": 'DECIMAL(15,4)',
            "nullable": True,
            "business_definition": 'Actual measurement reading for the characteristic being inspected.',
            "sample_value": '4520.5000'
        },
        {
            "name": 'upper_limit',
            "description": 'Upper specification limit',
            "datatype": 'DECIMAL(15,4)',
            "nullable": True,
            "business_definition": 'Upper tolerance limit for the characteristic defined by quality engineering.',
            "sample_value": '4530.0000'
        },
        {
            "name": 'lower_limit',
            "description": 'Lower specification limit',
            "datatype": 'DECIMAL(15,4)',
            "nullable": True,
            "business_definition": 'Lower tolerance limit for the characteristic defined by quality engineering.',
            "sample_value": '4510.0000'
        },
        {
            "name": 'result_code',
            "description": 'Inspection result code',
            "datatype": 'VARCHAR(20)',
            "nullable": True,
            "business_definition": 'Code indicating pass or fail for the characteristic inspection.',
            "sample_value": 'PASS'
        },
        {
            "name": 'inspected_by',
            "description": 'Inspector ID',
            "datatype": 'VARCHAR(50)',
            "nullable": True,
            "business_definition": 'Employee ID of the quality inspector who performed the measurement.',
            "sample_value": 'EMP-4521'
        },
        {
            "name": 'inspection_date',
            "description": 'Inspection date',
            "datatype": 'DATE',
            "nullable": True,
            "business_definition": 'Date on which the inspection was performed.',
            "sample_value": '2024-06-10'
        }
        ]
    },
    {
        "name": 'fact_oee_daily',
        "description": 'Overall Equipment Effectiveness daily fact table aggregated from shift-level production data',
        "domain": 'manufacturing',
        "platform": 'sap',
        "tags": ['Manufacturing', 'Analytics', 'Certified', 'Gold', 'PowerBI'],
        "columns": [
        {
            "name": 'oee_date',
            "description": 'Calendar date',
            "datatype": 'DATE',
            "nullable": False,
            "business_definition": 'Date for which the OEE metrics are calculated and reported.',
            "sample_value": '2024-06-10'
        },
        {
            "name": 'work_center_id',
            "description": 'Work center identifier',
            "datatype": 'VARCHAR(50)',
            "nullable": False,
            "business_definition": 'Work center for which the OEE is computed.',
            "sample_value": 'WC-100'
        },
        {
            "name": 'availability_pct',
            "description": 'Availability percentage',
            "datatype": 'DECIMAL(5,2)',
            "nullable": True,
            "business_definition": 'Ratio of actual operating time to planned production time.',
            "sample_value": '95.80'
        },
        {
            "name": 'performance_pct',
            "description": 'Performance percentage',
            "datatype": 'DECIMAL(5,2)',
            "nullable": True,
            "business_definition": 'Ratio of actual production speed to ideal speed.',
            "sample_value": '92.40'
        },
        {
            "name": 'quality_pct',
            "description": 'Quality percentage',
            "datatype": 'DECIMAL(5,2)',
            "nullable": True,
            "business_definition": 'Ratio of good units produced to total units produced.',
            "sample_value": '98.60'
        },
        {
            "name": 'oee_pct',
            "description": 'Overall OEE percentage',
            "datatype": 'DECIMAL(5,2)',
            "nullable": True,
            "business_definition": 'OEE calculated as availability times performance times quality.',
            "sample_value": '87.30'
        },
        {
            "name": 'planned_downtime_mins',
            "description": 'Planned downtime in minutes',
            "datatype": 'DECIMAL(10,2)',
            "nullable": True,
            "business_definition": 'Total planned downtime including breaks and maintenance.',
            "sample_value": '60.00'
        },
        {
            "name": 'unplanned_downtime_mins',
            "description": 'Unplanned downtime in minutes',
            "datatype": 'DECIMAL(10,2)',
            "nullable": True,
            "business_definition": 'Total unplanned downtime due to breakdowns or disruptions.',
            "sample_value": '15.00'
        },
        {
            "name": 'total_output_qty',
            "description": 'Total units produced',
            "datatype": 'INTEGER',
            "nullable": True,
            "business_definition": 'Total number of units produced at the work center during the day.',
            "sample_value": '500'
        },
        {
            "name": 'good_output_qty',
            "description": 'Good units produced',
            "datatype": 'INTEGER',
            "nullable": True,
            "business_definition": 'Number of defect-free units produced during the day.',
            "sample_value": '485'
        }
        ]
    },
    {
        "name": 'dim_material',
        "description": 'Material master dimension table providing comprehensive material attributes',
        "domain": 'manufacturing',
        "platform": 'sap',
        "tags": ['Manufacturing', 'MasterData', 'SAP', 'Certified', 'Gold', 'PowerBI'],
        "columns": [
        {
            "name": 'material_sk',
            "description": 'Material surrogate key',
            "datatype": 'VARCHAR(100)',
            "nullable": False,
            "business_definition": 'Data warehouse surrogate key uniquely identifying each material record.',
            "sample_value": 'SK-MAT-VF8-001'
        },
        {
            "name": 'material_id',
            "description": 'SAP material number',
            "datatype": 'VARCHAR(40)',
            "nullable": False,
            "business_definition": 'SAP material master number from the MARA table.',
            "sample_value": 'M-VF8-001'
        },
        {
            "name": 'material_name',
            "description": 'Material description',
            "datatype": 'VARCHAR(200)',
            "nullable": True,
            "business_definition": 'English description of the material from the material master text.',
            "sample_value": 'VinFast VF8 Electric SUV - Complete Vehicle'
        },
        {
            "name": 'material_type',
            "description": 'Material type',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'SAP material type classification such as FERT, HALB, or ROH.',
            "sample_value": 'FERT'
        },
        {
            "name": 'base_uom',
            "description": 'Base unit of measure',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Base unit of measure for inventory and production purposes.',
            "sample_value": 'EA'
        },
        {
            "name": 'material_group',
            "description": 'Material group code',
            "datatype": 'VARCHAR(20)',
            "nullable": True,
            "business_definition": 'Group code categorizing the material for reporting and analysis.',
            "sample_value": 'VEHICLE'
        },
        {
            "name": 'product_hierarchy',
            "description": 'Product hierarchy code',
            "datatype": 'VARCHAR(30)',
            "nullable": True,
            "business_definition": 'Product hierarchy used for sales and operations planning roll-ups.',
            "sample_value": 'VF8-SUV-2024'
        },
        {
            "name": 'is_active',
            "description": 'Active material flag',
            "datatype": 'BOOLEAN',
            "nullable": True,
            "business_definition": 'Flag indicating whether the material is currently active in the system.',
            "sample_value": 'True'
        }
        ]
    },
    {
        "name": 'dim_product',
        "description": 'Product dimension table for VinFast vehicle models and variants',
        "domain": 'manufacturing',
        "platform": 'sap',
        "tags": ['Manufacturing', 'MasterData', 'SAP', 'Certified', 'Gold', 'PowerBI'],
        "columns": [
        {
            "name": 'product_sk',
            "description": 'Product surrogate key',
            "datatype": 'VARCHAR(100)',
            "nullable": False,
            "business_definition": 'Data warehouse surrogate key for the product dimension.',
            "sample_value": 'SK-PROD-VF8'
        },
        {
            "name": 'model_code',
            "description": 'Vehicle model code',
            "datatype": 'VARCHAR(20)',
            "nullable": False,
            "business_definition": 'Short code identifying the vehicle model such as VF8 or VF9.',
            "sample_value": 'VF8'
        },
        {
            "name": 'model_name',
            "description": 'Vehicle model name',
            "datatype": 'VARCHAR(100)',
            "nullable": True,
            "business_definition": 'Full marketing name of the vehicle model.',
            "sample_value": 'VinFast VF8 Eco'
        },
        {
            "name": 'variant',
            "description": 'Variant specification',
            "datatype": 'VARCHAR(50)',
            "nullable": True,
            "business_definition": 'Variant identifier for specific configurations such as battery type or trim.',
            "sample_value": 'Eco-Plus'
        },
        {
            "name": 'drive_type',
            "description": 'Drive type',
            "datatype": 'VARCHAR(30)',
            "nullable": True,
            "business_definition": 'Vehicle drivetrain type such as AWD, RWD, or FWD.',
            "sample_value": 'AWD'
        },
        {
            "name": 'battery_capacity_kwh',
            "description": 'Battery capacity in kWh',
            "datatype": 'DECIMAL(5,2)',
            "nullable": True,
            "business_definition": 'Nominal battery pack capacity in kilowatt-hours for the EV model.',
            "sample_value": '94.00'
        },
        {
            "name": 'range_km',
            "description": 'Estimated driving range in km',
            "datatype": 'INTEGER',
            "nullable": True,
            "business_definition": 'Estimated driving range per full charge in kilometers.',
            "sample_value": '500'
        },
        {
            "name": 'launch_date',
            "description": 'Model launch date',
            "datatype": 'DATE',
            "nullable": True,
            "business_definition": 'Official market launch date for the vehicle model.',
            "sample_value": '2024-03-01'
        },
        {
            "name": 'is_current_model',
            "description": 'Currently in production flag',
            "datatype": 'BOOLEAN',
            "nullable": True,
            "business_definition": 'Indicates whether the model is in active production at VinFast factories.',
            "sample_value": 'True'
        }
        ]
    },
    {
        "name": 'dim_work_center',
        "description": 'Work center dimension table with capacity and location attributes',
        "domain": 'manufacturing',
        "platform": 'sap',
        "tags": ['Manufacturing', 'MasterData', 'SAP', 'Certified', 'Gold', 'PowerBI'],
        "columns": [
        {
            "name": 'work_center_sk',
            "description": 'Work center surrogate key',
            "datatype": 'VARCHAR(100)',
            "nullable": False,
            "business_definition": 'Data warehouse surrogate key for the work center dimension.',
            "sample_value": 'SK-WC-100'
        },
        {
            "name": 'work_center_id',
            "description": 'SAP work center ID',
            "datatype": 'VARCHAR(50)',
            "nullable": False,
            "business_definition": 'SAP object ID for the work center from CRHD table.',
            "sample_value": 'WC-100'
        },
        {
            "name": 'work_center_name',
            "description": 'Work center descriptive name',
            "datatype": 'VARCHAR(200)',
            "nullable": True,
            "business_definition": 'Full descriptive name of the work center used in production reporting.',
            "sample_value": 'VF8 Final Assembly Line 1'
        },
        {
            "name": 'plant',
            "description": 'Plant code',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Plant where the work center is physically located.',
            "sample_value": 'VF01'
        },
        {
            "name": 'location',
            "description": 'Physical location',
            "datatype": 'VARCHAR(200)',
            "nullable": True,
            "business_definition": 'Physical location within the plant such as building and bay.',
            "sample_value": 'Hai Phong Plant - Building A - Bay 3'
        },
        {
            "name": 'capacity_category',
            "description": 'Capacity planning category',
            "datatype": 'VARCHAR(20)',
            "nullable": True,
            "business_definition": 'Category of the work center for capacity planning such as machine or labor.',
            "sample_value": 'Machine'
        },
        {
            "name": 'capacity_per_shift',
            "description": 'Maximum capacity per shift',
            "datatype": 'INTEGER',
            "nullable": True,
            "business_definition": 'Maximum units the work center can process in a standard shift.',
            "sample_value": '60'
        },
        {
            "name": 'is_active',
            "description": 'Active work center flag',
            "datatype": 'BOOLEAN',
            "nullable": True,
            "business_definition": 'Flag indicating whether the work center is currently operational.',
            "sample_value": 'True'
        }
        ]
    },
    {
        "name": 'agg_daily_production_output',
        "description": 'Daily production output aggregate per model and work center',
        "domain": 'manufacturing',
        "platform": 'sap',
        "tags": ['Manufacturing', 'Analytics', 'Certified', 'Silver', 'PowerBI'],
        "columns": [
        {
            "name": 'production_date',
            "description": 'Production date',
            "datatype": 'DATE',
            "nullable": False,
            "business_definition": 'Calendar date for the aggregated production output.',
            "sample_value": '2024-06-10'
        },
        {
            "name": 'model_code',
            "description": 'Vehicle model code',
            "datatype": 'VARCHAR(20)',
            "nullable": True,
            "business_definition": 'Vehicle model code for the output aggregation.',
            "sample_value": 'VF8'
        },
        {
            "name": 'work_center_id',
            "description": 'Work center ID',
            "datatype": 'VARCHAR(50)',
            "nullable": True,
            "business_definition": 'Work center for which the daily output is aggregated.',
            "sample_value": 'WC-100'
        },
        {
            "name": 'total_planned_qty',
            "description": 'Total planned quantity',
            "datatype": 'INTEGER',
            "nullable": True,
            "business_definition": 'Total units planned for production on this day.',
            "sample_value": '550'
        },
        {
            "name": 'total_produced_qty',
            "description": 'Total produced quantity',
            "datatype": 'INTEGER',
            "nullable": True,
            "business_definition": 'Total units actually produced on this day.',
            "sample_value": '530'
        },
        {
            "name": 'total_scrap_qty',
            "description": 'Total scrapped quantity',
            "datatype": 'INTEGER',
            "nullable": True,
            "business_definition": 'Total units scrapped during production on this day.',
            "sample_value": '12'
        },
        {
            "name": 'yield_pct',
            "description": 'Production yield percentage',
            "datatype": 'DECIMAL(5,2)',
            "nullable": True,
            "business_definition": 'Percentage of produced units that pass quality inspection.',
            "sample_value": '97.74'
        },
        {
            "name": 'plan_achievement_pct',
            "description": 'Plan achievement percentage',
            "datatype": 'DECIMAL(5,2)',
            "nullable": True,
            "business_definition": 'Percentage of planned production that was actually completed.',
            "sample_value": '96.36'
        }
        ]
    },
    {
        "name": 'agg_line_utilization_monthly',
        "description": 'Monthly production line utilization aggregate across work centers',
        "domain": 'manufacturing',
        "platform": 'sap',
        "tags": ['Manufacturing', 'Analytics', 'Silver', 'PowerBI'],
        "columns": [
        {
            "name": 'year_month',
            "description": 'Year-month period',
            "datatype": 'VARCHAR(10)',
            "nullable": False,
            "business_definition": 'Reporting period in YYYY-MM format for the monthly utilization.',
            "sample_value": '2024-06'
        },
        {
            "name": 'work_center_id',
            "description": 'Work center ID',
            "datatype": 'VARCHAR(50)',
            "nullable": True,
            "business_definition": 'Work center for which the monthly utilization is calculated.',
            "sample_value": 'WC-100'
        },
        {
            "name": 'plant',
            "description": 'Plant code',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Plant grouping for the utilization report.',
            "sample_value": 'VF01'
        },
        {
            "name": 'available_hours',
            "description": 'Total available hours',
            "datatype": 'DECIMAL(10,2)',
            "nullable": True,
            "business_definition": 'Total hours the work center was available for production in the month.',
            "sample_value": '720.00'
        },
        {
            "name": 'utilized_hours',
            "description": 'Total utilized hours',
            "datatype": 'DECIMAL(10,2)',
            "nullable": True,
            "business_definition": 'Total hours the work center was actively utilized for production.',
            "sample_value": '648.00'
        },
        {
            "name": 'downtime_hours',
            "description": 'Total downtime hours',
            "datatype": 'DECIMAL(10,2)',
            "nullable": True,
            "business_definition": 'Total hours of downtime including planned and unplanned events.',
            "sample_value": '72.00'
        },
        {
            "name": 'utilization_pct',
            "description": 'Utilization percentage',
            "datatype": 'DECIMAL(5,2)',
            "nullable": True,
            "business_definition": 'Percentage of available hours that were utilized for production.',
            "sample_value": '90.00'
        },
        {
            "name": 'total_output_qty',
            "description": 'Monthly total output units',
            "datatype": 'INTEGER',
            "nullable": True,
            "business_definition": 'Total units produced at the work center during the month.',
            "sample_value": '11000'
        },
        {
            "name": 'output_per_hour',
            "description": 'Average output per hour',
            "datatype": 'DECIMAL(10,2)',
            "nullable": True,
            "business_definition": 'Average production throughput per utilized hour.',
            "sample_value": '16.98'
        }
        ]
    },
    {
        "name": 'sap_mard',
        "description": 'Storage Location Stock - plant-level storage location stock data',
        "domain": 'logistics',
        "platform": 'sap',
        "tags": ['Logistics', 'MasterData', 'SAP', 'Certified', 'Gold'],
        "columns": [
        {
            "name": 'matnr',
            "description": 'Material number',
            "datatype": 'VARCHAR(40)',
            "nullable": False,
            "business_definition": 'Material number of the stock item in the storage location.',
            "sample_value": 'M-VF8-001'
        },
        {
            "name": 'werks',
            "description": 'Plant',
            "datatype": 'VARCHAR(10)',
            "nullable": False,
            "business_definition": 'Plant code for the storage location stock.',
            "sample_value": 'VF01'
        },
        {
            "name": 'lgort',
            "description": 'Storage location',
            "datatype": 'VARCHAR(10)',
            "nullable": False,
            "business_definition": 'Storage location code within the plant where the stock is held.',
            "sample_value": 'FG01'
        },
        {
            "name": 'labst',
            "description": 'Unrestricted stock quantity',
            "datatype": 'DECIMAL(15,3)',
            "nullable": True,
            "business_definition": 'Quantity of unrestricted-use stock available in the storage location.',
            "sample_value": '1250.000'
        },
        {
            "name": 'insme',
            "description": 'Quality inspection stock quantity',
            "datatype": 'DECIMAL(15,3)',
            "nullable": True,
            "business_definition": 'Quantity of stock placed under quality inspection.',
            "sample_value": '50.000'
        },
        {
            "name": 'einme',
            "description": 'Blocked stock quantity',
            "datatype": 'DECIMAL(15,3)',
            "nullable": True,
            "business_definition": 'Quantity of blocked stock not available for use or sale.',
            "sample_value": '0.000'
        },
        {
            "name": 'speme',
            "description": 'Stock in transfer quantity',
            "datatype": 'DECIMAL(15,3)',
            "nullable": True,
            "business_definition": 'Quantity of stock in transit between storage locations or plants.',
            "sample_value": '200.000'
        },
        {
            "name": 'meins',
            "description": 'Base unit of measure',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Base unit of measure for the stock quantities.',
            "sample_value": 'EA'
        },
        {
            "name": 'ersda',
            "description": 'Creation date',
            "datatype": 'DATE',
            "nullable": True,
            "business_definition": 'Date when the storage location stock record was created.',
            "sample_value": '2024-01-15'
        }
        ]
    },
    {
        "name": 'sap_mchb',
        "description": 'Batch Stock - stock per batch per storage location',
        "domain": 'logistics',
        "platform": 'sap',
        "tags": ['Logistics', 'MasterData', 'SAP', 'Batch', 'Gold'],
        "columns": [
        {
            "name": 'matnr',
            "description": 'Material number',
            "datatype": 'VARCHAR(40)',
            "nullable": False,
            "business_definition": 'Material number for which the batch stock is maintained.',
            "sample_value": 'M-BAT-789'
        },
        {
            "name": 'werks',
            "description": 'Plant',
            "datatype": 'VARCHAR(10)',
            "nullable": False,
            "business_definition": 'Plant where the batch stock is located.',
            "sample_value": 'VF01'
        },
        {
            "name": 'lgort',
            "description": 'Storage location',
            "datatype": 'VARCHAR(10)',
            "nullable": False,
            "business_definition": 'Storage location where the batch stock resides.',
            "sample_value": 'RM01'
        },
        {
            "name": 'charg',
            "description": 'Batch number',
            "datatype": 'VARCHAR(20)',
            "nullable": False,
            "business_definition": 'Batch number assigned to the material for traceability.',
            "sample_value": 'BAT-2024-0610'
        },
        {
            "name": 'clabs',
            "description": 'Unrestricted batch stock quantity',
            "datatype": 'DECIMAL(15,3)',
            "nullable": True,
            "business_definition": 'Unrestricted-use stock quantity for the specific batch.',
            "sample_value": '500.000'
        },
        {
            "name": 'cinsm',
            "description": 'Inspection batch stock quantity',
            "datatype": 'DECIMAL(15,3)',
            "nullable": True,
            "business_definition": 'Stock quantity for this batch under quality inspection.',
            "sample_value": '0.000'
        },
        {
            "name": 'cspem',
            "description": 'Blocked batch stock quantity',
            "datatype": 'DECIMAL(15,3)',
            "nullable": True,
            "business_definition": 'Blocked stock quantity for this batch.',
            "sample_value": '10.000'
        },
        {
            "name": 'lfdat',
            "description": 'Shelf-life expiration date',
            "datatype": 'DATE',
            "nullable": True,
            "business_definition": 'Expiration date for the batch used for FIFO stock rotation.',
            "sample_value": '2025-06-10'
        }
        ]
    },
    {
        "name": 'sap_mch1',
        "description": 'Batch - batch master data',
        "domain": 'logistics',
        "platform": 'sap',
        "tags": ['Logistics', 'MasterData', 'SAP', 'Batch', 'Gold'],
        "columns": [
        {
            "name": 'matnr',
            "description": 'Material number',
            "datatype": 'VARCHAR(40)',
            "nullable": False,
            "business_definition": 'Material number for which the batch is defined.',
            "sample_value": 'M-BAT-789'
        },
        {
            "name": 'werks',
            "description": 'Plant',
            "datatype": 'VARCHAR(10)',
            "nullable": False,
            "business_definition": 'Plant where the batch was created.',
            "sample_value": 'VF01'
        },
        {
            "name": 'charg',
            "description": 'Batch number',
            "datatype": 'VARCHAR(20)',
            "nullable": False,
            "business_definition": 'Unique batch number assigned to a specific production or procurement lot.',
            "sample_value": 'BAT-2024-0610'
        },
        {
            "name": 'lvorm',
            "description": 'Deletion indicator',
            "datatype": 'VARCHAR(1)',
            "nullable": True,
            "business_definition": 'Flag indicating whether the batch is marked for deletion.',
            "sample_value": 'N'
        },
        {
            "name": 'ersda',
            "description": 'Creation date',
            "datatype": 'DATE',
            "nullable": True,
            "business_definition": 'Date when the batch master record was created.',
            "sample_value": '2024-06-10'
        },
        {
            "name": 'cruser',
            "description": 'Created by user',
            "datatype": 'VARCHAR(20)',
            "nullable": True,
            "business_definition": 'SAP user ID who created the batch record.',
            "sample_value": 'PROD_USER'
        },
        {
            "name": 'batch_status',
            "description": 'Batch status code',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Current status of the batch such as active, locked, or expired.',
            "sample_value": 'ACTIVE'
        }
        ]
    },
    {
        "name": 'sap_lqua',
        "description": 'Warehouse Stock - stock per storage bin in warehouse management',
        "domain": 'logistics',
        "platform": 'sap',
        "tags": ['Logistics', 'MasterData', 'SAP', 'Gold'],
        "columns": [
        {
            "name": 'lgnum',
            "description": 'Warehouse number',
            "datatype": 'VARCHAR(10)',
            "nullable": False,
            "business_definition": 'Warehouse number identifying the warehouse management system environment.',
            "sample_value": 'WH01'
        },
        {
            "name": 'matnr',
            "description": 'Material number',
            "datatype": 'VARCHAR(40)',
            "nullable": False,
            "business_definition": 'Material number of the stock in the warehouse bin.',
            "sample_value": 'M-VF8-001'
        },
        {
            "name": 'lgtyp',
            "description": 'Storage type',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Storage type code defining the warehouse area such as high-rack or bulk.',
            "sample_value": 'HIGH'
        },
        {
            "name": 'lgpla',
            "description": 'Storage bin',
            "datatype": 'VARCHAR(30)',
            "nullable": True,
            "business_definition": 'Physical storage bin identifier within the warehouse.',
            "sample_value": 'A-01-02-03'
        },
        {
            "name": 'bestq',
            "description": 'Stock category',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Category of stock such as unrestricted, quality inspection, or blocked.',
            "sample_value": 'unrestricted'
        },
        {
            "name": 'gesme',
            "description": 'Total stock quantity',
            "datatype": 'DECIMAL(15,3)',
            "nullable": True,
            "business_definition": 'Total quantity of the material stored in the storage bin.',
            "sample_value": '240.000'
        },
        {
            "name": 'meins',
            "description": 'Base unit of measure',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Base unit of measure for the stock quantity.',
            "sample_value": 'EA'
        },
        {
            "name": 'charg',
            "description": 'Batch number',
            "datatype": 'VARCHAR(20)',
            "nullable": True,
            "business_definition": 'Batch number of the stock in the storage bin.',
            "sample_value": 'BAT-2024-0610'
        }
        ]
    },
    {
        "name": 'sap_lagp',
        "description": 'Storage Bin - warehouse storage bin master data',
        "domain": 'logistics',
        "platform": 'sap',
        "tags": ['Logistics', 'MasterData', 'SAP', 'Gold'],
        "columns": [
        {
            "name": 'lgnum',
            "description": 'Warehouse number',
            "datatype": 'VARCHAR(10)',
            "nullable": False,
            "business_definition": 'Warehouse number to which the storage bin belongs.',
            "sample_value": 'WH01'
        },
        {
            "name": 'lgtyp',
            "description": 'Storage type',
            "datatype": 'VARCHAR(10)',
            "nullable": False,
            "business_definition": 'Storage type code defining the warehouse zone of the bin.',
            "sample_value": 'HIGH'
        },
        {
            "name": 'lgpla',
            "description": 'Storage bin identifier',
            "datatype": 'VARCHAR(30)',
            "nullable": False,
            "business_definition": 'Unique identifier for the physical storage bin location.',
            "sample_value": 'A-01-02-03'
        },
        {
            "name": 'maxle',
            "description": 'Maximum weight capacity (kg)',
            "datatype": 'DECIMAL(10,2)',
            "nullable": True,
            "business_definition": 'Maximum weight capacity of the storage bin in kilograms.',
            "sample_value": '1000.00'
        },
        {
            "name": 'kzlef',
            "description": 'Bin capacity utilization flag',
            "datatype": 'VARCHAR(1)',
            "nullable": True,
            "business_definition": 'Flag indicating whether the bin is at capacity.',
            "sample_value": 'N'
        },
        {
            "name": 'lgber',
            "description": 'Storage section',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Storage section within the storage type for finer location granularity.',
            "sample_value": 'SEC-01'
        },
        {
            "name": 'bwlvs',
            "description": 'Movement type indicator',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Indicator for allowed movement types into or out of the bin.',
            "sample_value": 'ALL'
        },
        {
            "name": 'status',
            "description": 'Bin status',
            "datatype": 'VARCHAR(20)',
            "nullable": True,
            "business_definition": 'Operational status such as active, blocked, or maintenance.',
            "sample_value": 'active'
        }
        ]
    },
    {
        "name": 'sap_t001l',
        "description": 'Storage Locations - storage location master data per plant',
        "domain": 'logistics',
        "platform": 'sap',
        "tags": ['Logistics', 'MasterData', 'SAP', 'Gold'],
        "columns": [
        {
            "name": 'werks',
            "description": 'Plant',
            "datatype": 'VARCHAR(10)',
            "nullable": False,
            "business_definition": 'Plant code where the storage location is defined.',
            "sample_value": 'VF01'
        },
        {
            "name": 'lgort',
            "description": 'Storage location code',
            "datatype": 'VARCHAR(10)',
            "nullable": False,
            "business_definition": 'Unique code for the storage location within the plant.',
            "sample_value": 'FG01'
        },
        {
            "name": 'lgobe',
            "description": 'Storage location description',
            "datatype": 'VARCHAR(80)',
            "nullable": True,
            "business_definition": 'Descriptive name of the storage location for operational reference.',
            "sample_value": 'Finished Goods - Hai Phong'
        },
        {
            "name": 'dislo',
            "description": 'MRP indicator for location',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'MRP relevance indicator for the storage location.',
            "sample_value": 'D'
        },
        {
            "name": 'delet',
            "description": 'Deletion flag',
            "datatype": 'VARCHAR(1)',
            "nullable": True,
            "business_definition": 'Flag indicating whether the storage location is marked for deletion.',
            "sample_value": 'N'
        },
        {
            "name": 'address_id',
            "description": 'Address ID',
            "datatype": 'VARCHAR(20)',
            "nullable": True,
            "business_definition": 'Reference to the address master record for the storage location.',
            "sample_value": 'ADDR-001'
        }
        ]
    },
    {
        "name": 'sap_lips',
        "description": 'Delivery Item - delivery document line items for outbound and inbound deliveries',
        "domain": 'logistics',
        "platform": 'sap',
        "tags": ['Logistics', 'Transactional', 'SAP', 'Silver'],
        "columns": [
        {
            "name": 'vbeln',
            "description": 'Delivery document number',
            "datatype": 'VARCHAR(30)',
            "nullable": False,
            "business_definition": 'SAP delivery document number grouping all line items for a shipment.',
            "sample_value": 'DEL-2024-50001'
        },
        {
            "name": 'posnr',
            "description": 'Delivery item number',
            "datatype": 'VARCHAR(10)',
            "nullable": False,
            "business_definition": 'Line item number within the delivery document.',
            "sample_value": '0010'
        },
        {
            "name": 'matnr',
            "description": 'Material number',
            "datatype": 'VARCHAR(40)',
            "nullable": False,
            "business_definition": 'Material number of the item being delivered.',
            "sample_value": 'M-VF8-001'
        },
        {
            "name": 'lfimg',
            "description": 'Actual delivered quantity',
            "datatype": 'DECIMAL(15,3)',
            "nullable": True,
            "business_definition": 'Quantity of the material actually delivered.',
            "sample_value": '50.000'
        },
        {
            "name": 'meins',
            "description": 'Unit of measure',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Unit of measure for the delivery quantity.',
            "sample_value": 'EA'
        },
        {
            "name": 'charg',
            "description": 'Batch number',
            "datatype": 'VARCHAR(20)',
            "nullable": True,
            "business_definition": 'Batch number delivered for traceability.',
            "sample_value": 'BAT-2024-0610'
        },
        {
            "name": 'werks',
            "description": 'Plant',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Plant from which the material is delivered.',
            "sample_value": 'VF01'
        },
        {
            "name": 'lgort',
            "description": 'Storage location',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Storage location from which the material is picked.',
            "sample_value": 'FG01'
        }
        ]
    },
    {
        "name": 'stg_inbound_delivery',
        "description": 'Staging table for inbound delivery data from supplier shipments',
        "domain": 'logistics',
        "platform": 'sap',
        "tags": ['Logistics', 'Analytics', 'Bronze', 'Critical'],
        "columns": [
        {
            "name": 'inbound_delivery_id',
            "description": 'Inbound delivery document number',
            "datatype": 'VARCHAR(30)',
            "nullable": False,
            "business_definition": 'SAP inbound delivery number for supplier shipment tracking.',
            "sample_value": 'IN-DEL-2024-77123'
        },
        {
            "name": 'supplier_id',
            "description": 'Supplier code',
            "datatype": 'VARCHAR(20)',
            "nullable": True,
            "business_definition": 'Supplier code from which the inbound delivery is received.',
            "sample_value": 'SUP-1001'
        },
        {
            "name": 'material_id',
            "description": 'Material number',
            "datatype": 'VARCHAR(40)',
            "nullable": True,
            "business_definition": 'Material number of the goods being received.',
            "sample_value": 'M-BAT-789'
        },
        {
            "name": 'expected_qty',
            "description": 'Expected delivery quantity',
            "datatype": 'DECIMAL(15,3)',
            "nullable": True,
            "business_definition": 'Expected quantity of goods as per the purchase order.',
            "sample_value": '1000.000'
        },
        {
            "name": 'received_qty',
            "description": 'Received quantity',
            "datatype": 'DECIMAL(15,3)',
            "nullable": True,
            "business_definition": 'Actual quantity of goods received at the warehouse.',
            "sample_value": '985.000'
        },
        {
            "name": 'delivery_date',
            "description": 'Delivery date',
            "datatype": 'DATE',
            "nullable": True,
            "business_definition": 'Date when the inbound delivery is scheduled or received.',
            "sample_value": '2024-06-15'
        },
        {
            "name": 'status',
            "description": 'Delivery status',
            "datatype": 'VARCHAR(30)',
            "nullable": True,
            "business_definition": 'Current status such as in-transit, received, or booked.',
            "sample_value": 'received'
        },
        {
            "name": 'source_system',
            "description": 'Source system code',
            "datatype": 'VARCHAR(50)',
            "nullable": True,
            "business_definition": 'Originating system from which the delivery data is extracted.',
            "sample_value": 'SAP_ECC'
        },
        {
            "name": 'ingestion_ts',
            "description": 'Ingestion timestamp',
            "datatype": 'TIMESTAMP',
            "nullable": True,
            "business_definition": 'Timestamp when the record was ingested into the staging layer.',
            "sample_value": '2024-06-15 06:30:00'
        }
        ]
    },
    {
        "name": 'stg_outbound_delivery',
        "description": 'Staging table for outbound delivery data to customers and dealers',
        "domain": 'logistics',
        "platform": 'sap',
        "tags": ['Logistics', 'Analytics', 'Bronze', 'Critical'],
        "columns": [
        {
            "name": 'outbound_delivery_id',
            "description": 'Outbound delivery document number',
            "datatype": 'VARCHAR(30)',
            "nullable": False,
            "business_definition": 'SAP outbound delivery number for shipments to customers or dealers.',
            "sample_value": 'OUT-DEL-2024-33210'
        },
        {
            "name": 'customer_id',
            "description": 'Customer code',
            "datatype": 'VARCHAR(20)',
            "nullable": True,
            "business_definition": 'Customer or dealer code receiving the outbound delivery.',
            "sample_value": 'DLR-001'
        },
        {
            "name": 'material_id',
            "description": 'Material number',
            "datatype": 'VARCHAR(40)',
            "nullable": True,
            "business_definition": 'Material number of the goods being shipped.',
            "sample_value": 'M-VF8-001'
        },
        {
            "name": 'delivered_qty',
            "description": 'Delivered quantity',
            "datatype": 'DECIMAL(15,3)',
            "nullable": True,
            "business_definition": 'Quantity of goods actually shipped in the outbound delivery.',
            "sample_value": '25.000'
        },
        {
            "name": 'shipment_date',
            "description": 'Shipment date',
            "datatype": 'DATE',
            "nullable": True,
            "business_definition": 'Date when the goods are shipped from the warehouse.',
            "sample_value": '2024-06-16'
        },
        {
            "name": 'vehicle_vin',
            "description": 'Vehicle VIN number',
            "datatype": 'VARCHAR(50)',
            "nullable": True,
            "business_definition": 'Vehicle identification number for traceability.',
            "sample_value": 'RLXEVF8S0R1002345'
        },
        {
            "name": 'destination',
            "description": 'Destination address',
            "datatype": 'VARCHAR(200)',
            "nullable": True,
            "business_definition": 'Destination address or dealer location code.',
            "sample_value": 'VinFast Hanoi Showroom'
        },
        {
            "name": 'status',
            "description": 'Delivery status',
            "datatype": 'VARCHAR(30)',
            "nullable": True,
            "business_definition": 'Current status such as picked, packed, loaded, or shipped.',
            "sample_value": 'shipped'
        },
        {
            "name": 'ingestion_ts',
            "description": 'Ingestion timestamp',
            "datatype": 'TIMESTAMP',
            "nullable": True,
            "business_definition": 'Timestamp when the record was ingested into staging.',
            "sample_value": '2024-06-16 14:00:00'
        }
        ]
    },
    {
        "name": 'stg_inventory_snapshot',
        "description": 'Staging table for daily inventory snapshots from SAP and WMS',
        "domain": 'logistics',
        "platform": 'sap',
        "tags": ['Logistics', 'Analytics', 'Bronze', 'RealTime'],
        "columns": [
        {
            "name": 'snapshot_id',
            "description": 'Snapshot unique identifier',
            "datatype": 'VARCHAR(100)',
            "nullable": False,
            "business_definition": 'Unique identifier for the inventory snapshot record.',
            "sample_value": 'SNAP-2024-06-10-001'
        },
        {
            "name": 'material_id',
            "description": 'Material number',
            "datatype": 'VARCHAR(40)',
            "nullable": False,
            "business_definition": 'Material number captured in the inventory snapshot.',
            "sample_value": 'M-VF8-001'
        },
        {
            "name": 'plant',
            "description": 'Plant code',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Plant code for the inventory snapshot.',
            "sample_value": 'VF01'
        },
        {
            "name": 'storage_location',
            "description": 'Storage location code',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Storage location for the inventory level.',
            "sample_value": 'FG01'
        },
        {
            "name": 'batch',
            "description": 'Batch number',
            "datatype": 'VARCHAR(20)',
            "nullable": True,
            "business_definition": 'Batch number included in the snapshot if applicable.',
            "sample_value": 'BAT-2024-0610'
        },
        {
            "name": 'unrestricted_qty',
            "description": 'Unrestricted stock quantity',
            "datatype": 'DECIMAL(15,3)',
            "nullable": True,
            "business_definition": 'Unrestricted-use stock at the time of the snapshot.',
            "sample_value": '1200.000'
        },
        {
            "name": 'inqty',
            "description": 'Inspection stock quantity',
            "datatype": 'DECIMAL(15,3)',
            "nullable": True,
            "business_definition": 'Quantity under quality inspection at snapshot time.',
            "sample_value": '50.000'
        },
        {
            "name": 'snapshot_date',
            "description": 'Snapshot date',
            "datatype": 'DATE',
            "nullable": False,
            "business_definition": 'Date on which the inventory snapshot was taken.',
            "sample_value": '2024-06-10'
        },
        {
            "name": 'snapshot_ts',
            "description": 'Snapshot timestamp',
            "datatype": 'TIMESTAMP',
            "nullable": True,
            "business_definition": 'Exact timestamp when the inventory snapshot was captured.',
            "sample_value": '2024-06-10 23:59:59'
        },
        {
            "name": 'source_system',
            "description": 'Source system code',
            "datatype": 'VARCHAR(50)',
            "nullable": True,
            "business_definition": 'System that provided the inventory data.',
            "sample_value": 'SAP_ECC'
        }
        ]
    },
    {
        "name": 'fact_inventory_balance',
        "description": 'Daily inventory balance fact table at storage-location and batch grain',
        "domain": 'logistics',
        "platform": 'sap',
        "tags": ['Logistics', 'Analytics', 'Critical', 'Certified', 'Gold', 'PowerBI'],
        "columns": [
        {
            "name": 'balance_date',
            "description": 'Balance date',
            "datatype": 'DATE',
            "nullable": False,
            "business_definition": 'Date for which the inventory balance is recorded.',
            "sample_value": '2024-06-10'
        },
        {
            "name": 'material_id',
            "description": 'Material number',
            "datatype": 'VARCHAR(40)',
            "nullable": False,
            "business_definition": 'Material number of the inventory item.',
            "sample_value": 'M-VF8-001'
        },
        {
            "name": 'plant',
            "description": 'Plant code',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Plant where the inventory is held.',
            "sample_value": 'VF01'
        },
        {
            "name": 'storage_location',
            "description": 'Storage location code',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Storage location where the inventory is held.',
            "sample_value": 'FG01'
        },
        {
            "name": 'batch',
            "description": 'Batch number',
            "datatype": 'VARCHAR(20)',
            "nullable": True,
            "business_definition": 'Batch number for the inventory balance.',
            "sample_value": 'BAT-2024-0610'
        },
        {
            "name": 'unrestricted_qty',
            "description": 'Unrestricted stock quantity',
            "datatype": 'DECIMAL(15,3)',
            "nullable": True,
            "business_definition": 'End-of-day unrestricted-use stock balance.',
            "sample_value": '1150.000'
        },
        {
            "name": 'inspection_qty',
            "description": 'Inspection stock quantity',
            "datatype": 'DECIMAL(15,3)',
            "nullable": True,
            "business_definition": 'End-of-day stock quantity under quality inspection.',
            "sample_value": '30.000'
        },
        {
            "name": 'blocked_qty',
            "description": 'Blocked stock quantity',
            "datatype": 'DECIMAL(15,3)',
            "nullable": True,
            "business_definition": 'End-of-day blocked stock quantity.',
            "sample_value": '5.000'
        },
        {
            "name": 'total_stock_value_vnd',
            "description": 'Total stock value in VND',
            "datatype": 'DECIMAL(18,2)',
            "nullable": True,
            "business_definition": 'Total valuation of the inventory balance in Vietnamese Dong.',
            "sample_value": '1437500000.00'
        }
        ]
    },
    {
        "name": 'fact_goods_movement',
        "description": 'Goods movement fact table recording every inventory transaction',
        "domain": 'logistics',
        "platform": 'sap',
        "tags": ['Logistics', 'Analytics', 'Critical', 'Gold'],
        "columns": [
        {
            "name": 'movement_id',
            "description": 'Goods movement unique ID',
            "datatype": 'VARCHAR(100)',
            "nullable": False,
            "business_definition": 'Unique identifier for each goods movement transaction.',
            "sample_value": 'GM-2024-56789-001'
        },
        {
            "name": 'material_id',
            "description": 'Material number',
            "datatype": 'VARCHAR(40)',
            "nullable": False,
            "business_definition": 'Material number of the goods being moved.',
            "sample_value": 'M-VF8-001'
        },
        {
            "name": 'plant',
            "description": 'Plant code',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Plant where the goods movement occurred.',
            "sample_value": 'VF01'
        },
        {
            "name": 'movement_type',
            "description": 'SAP movement type',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'SAP movement type code such as 101 for goods receipt.',
            "sample_value": '101'
        },
        {
            "name": 'movement_qty',
            "description": 'Movement quantity',
            "datatype": 'DECIMAL(15,3)',
            "nullable": True,
            "business_definition": 'Quantity of goods moved in the transaction.',
            "sample_value": '100.000'
        },
        {
            "name": 'uom',
            "description": 'Unit of measure',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Unit of measure for the movement quantity.',
            "sample_value": 'EA'
        },
        {
            "name": 'from_storage_loc',
            "description": 'Source storage location',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Storage location from which goods are moved.',
            "sample_value": 'RM01'
        },
        {
            "name": 'to_storage_loc',
            "description": 'Target storage location',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Storage location to which goods are moved.',
            "sample_value": 'WC01'
        },
        {
            "name": 'posting_date',
            "description": 'Posting date',
            "datatype": 'DATE',
            "nullable": True,
            "business_definition": 'Date when the goods movement was posted in SAP.',
            "sample_value": '2024-06-10'
        },
        {
            "name": 'reference_doc',
            "description": 'Reference document number',
            "datatype": 'VARCHAR(30)',
            "nullable": True,
            "business_definition": 'Document such as production order or purchase order triggering the movement.',
            "sample_value": 'PO-2024-10045'
        }
        ]
    },
    {
        "name": 'fact_shipment_tracking',
        "description": 'Shipment tracking fact table for logistics shipment monitoring',
        "domain": 'logistics',
        "platform": 'sap',
        "tags": ['Logistics', 'Analytics', 'Critical', 'Gold', 'RealTime'],
        "columns": [
        {
            "name": 'tracking_id',
            "description": 'Shipment tracking event ID',
            "datatype": 'VARCHAR(100)',
            "nullable": False,
            "business_definition": 'Unique identifier for each shipment tracking event.',
            "sample_value": 'TRK-2024-33210-01'
        },
        {
            "name": 'delivery_id',
            "description": 'Delivery document number',
            "datatype": 'VARCHAR(30)',
            "nullable": True,
            "business_definition": 'SAP delivery document number associated with the shipment.',
            "sample_value": 'OUT-DEL-2024-33210'
        },
        {
            "name": 'vehicle_vin',
            "description": 'Vehicle VIN',
            "datatype": 'VARCHAR(50)',
            "nullable": True,
            "business_definition": 'Vehicle identification number for the shipped unit.',
            "sample_value": 'RLXEVF8S0R1002345'
        },
        {
            "name": 'carrier',
            "description": 'Carrier name',
            "datatype": 'VARCHAR(100)',
            "nullable": True,
            "business_definition": 'Logistics carrier or shipping company handling the delivery.',
            "sample_value": 'VinFast Logistics'
        },
        {
            "name": 'origin',
            "description": 'Origin location',
            "datatype": 'VARCHAR(200)',
            "nullable": True,
            "business_definition": 'Location from which the shipment originates.',
            "sample_value": 'Hai Phong Plant, Vietnam'
        },
        {
            "name": 'destination',
            "description": 'Destination location',
            "datatype": 'VARCHAR(200)',
            "nullable": True,
            "business_definition": 'Destination location for the shipment.',
            "sample_value": 'Dealer Hanoi - Showroom 01'
        },
        {
            "name": 'event_type',
            "description": 'Tracking event type',
            "datatype": 'VARCHAR(50)',
            "nullable": True,
            "business_definition": 'Type of tracking event such as loaded or in-transit.',
            "sample_value": 'in-transit'
        },
        {
            "name": 'event_ts',
            "description": 'Event timestamp',
            "datatype": 'TIMESTAMP',
            "nullable": True,
            "business_definition": 'Timestamp when the tracking event was recorded.',
            "sample_value": '2024-06-16 15:30:00'
        },
        {
            "name": 'eta_date',
            "description": 'Estimated arrival date',
            "datatype": 'DATE',
            "nullable": True,
            "business_definition": 'Estimated date of arrival at the destination.',
            "sample_value": '2024-06-18'
        }
        ]
    },
    {
        "name": 'dim_warehouse',
        "description": 'Warehouse dimension table with location and capacity attributes',
        "domain": 'logistics',
        "platform": 'sap',
        "tags": ['Logistics', 'MasterData', 'SAP', 'Certified', 'Gold', 'PowerBI'],
        "columns": [
        {
            "name": 'warehouse_sk',
            "description": 'Warehouse surrogate key',
            "datatype": 'VARCHAR(100)',
            "nullable": False,
            "business_definition": 'Data warehouse surrogate key for the warehouse dimension.',
            "sample_value": 'SK-WH-01'
        },
        {
            "name": 'warehouse_id',
            "description": 'SAP warehouse number',
            "datatype": 'VARCHAR(10)',
            "nullable": False,
            "business_definition": 'SAP warehouse number from the warehouse management module.',
            "sample_value": 'WH01'
        },
        {
            "name": 'warehouse_name',
            "description": 'Warehouse descriptive name',
            "datatype": 'VARCHAR(200)',
            "nullable": True,
            "business_definition": 'Full descriptive name of the warehouse facility.',
            "sample_value": 'Hai Phong Central Warehouse'
        },
        {
            "name": 'plant',
            "description": 'Plant code',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Plant to which the warehouse belongs.',
            "sample_value": 'VF01'
        },
        {
            "name": 'location',
            "description": 'Geographic location',
            "datatype": 'VARCHAR(200)',
            "nullable": True,
            "business_definition": 'Physical address or geographic area of the warehouse.',
            "sample_value": 'Hai Phong City, Vietnam'
        },
        {
            "name": 'warehouse_type',
            "description": 'Warehouse type',
            "datatype": 'VARCHAR(30)',
            "nullable": True,
            "business_definition": 'Classification such as central, regional, or cross-dock.',
            "sample_value": 'central'
        },
        {
            "name": 'total_capacity_m3',
            "description": 'Total storage capacity in cubic meters',
            "datatype": 'DECIMAL(12,2)',
            "nullable": True,
            "business_definition": 'Total volumetric storage capacity of the warehouse.',
            "sample_value": '50000.00'
        },
        {
            "name": 'is_active',
            "description": 'Active warehouse flag',
            "datatype": 'BOOLEAN',
            "nullable": True,
            "business_definition": 'Indicates whether the warehouse is currently operational.',
            "sample_value": 'True'
        }
        ]
    },
    {
        "name": 'dim_storage_location',
        "description": 'Storage location dimension table for plant-level storage areas',
        "domain": 'logistics',
        "platform": 'sap',
        "tags": ['Logistics', 'MasterData', 'SAP', 'Gold', 'PowerBI'],
        "columns": [
        {
            "name": 'storage_loc_sk',
            "description": 'Storage location surrogate key',
            "datatype": 'VARCHAR(100)',
            "nullable": False,
            "business_definition": 'Data warehouse surrogate key for the storage location dimension.',
            "sample_value": 'SK-SLOC-FG01'
        },
        {
            "name": 'storage_loc_id',
            "description": 'SAP storage location code',
            "datatype": 'VARCHAR(10)',
            "nullable": False,
            "business_definition": 'SAP storage location code assigned within the plant.',
            "sample_value": 'FG01'
        },
        {
            "name": 'plant',
            "description": 'Plant code',
            "datatype": 'VARCHAR(10)',
            "nullable": False,
            "business_definition": 'Plant code where the storage location is defined.',
            "sample_value": 'VF01'
        },
        {
            "name": 'description',
            "description": 'Storage location description',
            "datatype": 'VARCHAR(200)',
            "nullable": True,
            "business_definition": 'Descriptive name of the storage location for operational use.',
            "sample_value": 'Finished Goods Storage'
        },
        {
            "name": 'location_type',
            "description": 'Type of storage location',
            "datatype": 'VARCHAR(30)',
            "nullable": True,
            "business_definition": 'Categorization such as raw materials or finished goods.',
            "sample_value": 'finished_goods'
        },
        {
            "name": 'is_mrp_relevant',
            "description": 'MRP relevance flag',
            "datatype": 'BOOLEAN',
            "nullable": True,
            "business_definition": 'Indicates whether the location is relevant for MRP planning.',
            "sample_value": 'True'
        },
        {
            "name": 'is_active',
            "description": 'Active location flag',
            "datatype": 'BOOLEAN',
            "nullable": True,
            "business_definition": 'Indicates whether the storage location is currently active.',
            "sample_value": 'True'
        }
        ]
    },
    {
        "name": 'dim_logistics_supplier',
        "description": 'Supplier dimension table with procurement and vendor attributes',
        "domain": 'logistics',
        "platform": 'sap',
        "tags": ['Logistics', 'MasterData', 'SAP', 'Certified', 'Gold', 'PowerBI'],
        "columns": [
        {
            "name": 'supplier_sk',
            "description": 'Supplier surrogate key',
            "datatype": 'VARCHAR(100)',
            "nullable": False,
            "business_definition": 'Data warehouse surrogate key for the supplier dimension.',
            "sample_value": 'SK-SUP-1001'
        },
        {
            "name": 'supplier_id',
            "description": 'SAP vendor code',
            "datatype": 'VARCHAR(20)',
            "nullable": False,
            "business_definition": 'SAP vendor account number from the LFA1 table.',
            "sample_value": 'SUP-1001'
        },
        {
            "name": 'supplier_name',
            "description": 'Supplier company name',
            "datatype": 'VARCHAR(200)',
            "nullable": True,
            "business_definition": 'Registered company name of the supplier.',
            "sample_value": 'VinEnergy Battery Co., Ltd'
        },
        {
            "name": 'supplier_category',
            "description": 'Supplier category code',
            "datatype": 'VARCHAR(30)',
            "nullable": True,
            "business_definition": 'Category of supplier such as raw material or parts.',
            "sample_value": 'Tier 1'
        },
        {
            "name": 'country',
            "description": 'Supplier country',
            "datatype": 'VARCHAR(50)',
            "nullable": True,
            "business_definition": 'Country where the supplier is registered or operates.',
            "sample_value": 'Vietnam'
        },
        {
            "name": 'payment_terms',
            "description": 'Payment terms code',
            "datatype": 'VARCHAR(20)',
            "nullable": True,
            "business_definition": 'SAP payment terms code defining the payment schedule.',
            "sample_value": 'NET30'
        },
        {
            "name": 'is_active',
            "description": 'Active supplier flag',
            "datatype": 'BOOLEAN',
            "nullable": True,
            "business_definition": 'Indicates whether the supplier is currently approved for procurement.',
            "sample_value": 'True'
        },
        {
            "name": 'quality_rating',
            "description": 'Quality rating',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Quality performance rating assigned to the supplier.',
            "sample_value": 'A'
        }
        ]
    },
    {
        "name": 'agg_daily_inventory_level',
        "description": 'Daily inventory level aggregate at plant and material group grain',
        "domain": 'logistics',
        "platform": 'sap',
        "tags": ['Logistics', 'Analytics', 'Silver', 'PowerBI'],
        "columns": [
        {
            "name": 'inventory_date',
            "description": 'Inventory date',
            "datatype": 'DATE',
            "nullable": False,
            "business_definition": 'Calendar date for the daily inventory aggregate.',
            "sample_value": '2024-06-10'
        },
        {
            "name": 'plant',
            "description": 'Plant code',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Plant for which the inventory level is aggregated.',
            "sample_value": 'VF01'
        },
        {
            "name": 'material_group',
            "description": 'Material group code',
            "datatype": 'VARCHAR(20)',
            "nullable": True,
            "business_definition": 'Material group for inventory aggregation.',
            "sample_value": 'BATTERY'
        },
        {
            "name": 'total_unrestricted_qty',
            "description": 'Total unrestricted stock quantity',
            "datatype": 'DECIMAL(15,3)',
            "nullable": True,
            "business_definition": 'Aggregated unrestricted stock quantity across all locations.',
            "sample_value": '8500.000'
        },
        {
            "name": 'total_stock_value_vnd',
            "description": 'Total stock value in VND',
            "datatype": 'DECIMAL(18,2)',
            "nullable": True,
            "business_definition": 'Aggregated inventory valuation in Vietnamese Dong.',
            "sample_value": '10625000000.00'
        },
        {
            "name": 'days_of_cover',
            "description": 'Days of inventory cover',
            "datatype": 'DECIMAL(10,2)',
            "nullable": True,
            "business_definition": 'Number of days inventory can sustain average daily consumption.',
            "sample_value": '18.50'
        },
        {
            "name": 'stockout_flag',
            "description": 'Stock-out indicator',
            "datatype": 'BOOLEAN',
            "nullable": True,
            "business_definition": 'Flag indicating whether any material in the group is at zero stock.',
            "sample_value": 'False'
        }
        ]
    },
    {
        "name": 'agg_monthly_turnover',
        "description": 'Monthly inventory turnover aggregate by material group and plant',
        "domain": 'logistics',
        "platform": 'sap',
        "tags": ['Logistics', 'Analytics', 'Silver', 'PowerBI'],
        "columns": [
        {
            "name": 'year_month',
            "description": 'Year-month period',
            "datatype": 'VARCHAR(10)',
            "nullable": False,
            "business_definition": 'Reporting period in YYYY-MM format for monthly turnover.',
            "sample_value": '2024-06'
        },
        {
            "name": 'plant',
            "description": 'Plant code',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Plant for which the turnover is calculated.',
            "sample_value": 'VF01'
        },
        {
            "name": 'material_group',
            "description": 'Material group code',
            "datatype": 'VARCHAR(20)',
            "nullable": True,
            "business_definition": 'Material group for turnover aggregation.',
            "sample_value": 'BATTERY'
        },
        {
            "name": 'begin_inventory_value_vnd',
            "description": 'Beginning inventory value',
            "datatype": 'DECIMAL(18,2)',
            "nullable": True,
            "business_definition": 'Inventory valuation at month start in VND.',
            "sample_value": '9500000000.00'
        },
        {
            "name": 'end_inventory_value_vnd',
            "description": 'Ending inventory value',
            "datatype": 'DECIMAL(18,2)',
            "nullable": True,
            "business_definition": 'Inventory valuation at month end in VND.',
            "sample_value": '10625000000.00'
        },
        {
            "name": 'total_consumption_value_vnd',
            "description": 'Total consumption value',
            "datatype": 'DECIMAL(18,2)',
            "nullable": True,
            "business_definition": 'Value of inventory consumed during the month in VND.',
            "sample_value": '5230000000.00'
        },
        {
            "name": 'turnover_ratio',
            "description": 'Inventory turnover ratio',
            "datatype": 'DECIMAL(10,2)',
            "nullable": True,
            "business_definition": 'Ratio of consumption to average inventory.',
            "sample_value": '1.04'
        }
        ]
    },
    {
        "name": 'agg_warehouse_utilization',
        "description": 'Warehouse utilization aggregate tracking capacity usage across storage types',
        "domain": 'logistics',
        "platform": 'sap',
        "tags": ['Logistics', 'Analytics', 'Silver', 'PowerBI'],
        "columns": [
        {
            "name": 'year_month',
            "description": 'Year-month period',
            "datatype": 'VARCHAR(10)',
            "nullable": False,
            "business_definition": 'Reporting period in YYYY-MM format for utilization.',
            "sample_value": '2024-06'
        },
        {
            "name": 'warehouse_id',
            "description": 'Warehouse number',
            "datatype": 'VARCHAR(10)',
            "nullable": False,
            "business_definition": 'Warehouse number for the utilization report.',
            "sample_value": 'WH01'
        },
        {
            "name": 'storage_type',
            "description": 'Storage type code',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Storage type within the warehouse such as high-rack or bulk.',
            "sample_value": 'HIGH'
        },
        {
            "name": 'total_capacity_qty',
            "description": 'Total bin capacity',
            "datatype": 'INTEGER',
            "nullable": True,
            "business_definition": 'Total number of storage bins available.',
            "sample_value": '500'
        },
        {
            "name": 'occupied_bins',
            "description": 'Number of occupied bins',
            "datatype": 'INTEGER',
            "nullable": True,
            "business_definition": 'Number of storage bins currently occupied with stock.',
            "sample_value": '423'
        },
        {
            "name": 'empty_bins',
            "description": 'Number of empty bins',
            "datatype": 'INTEGER',
            "nullable": True,
            "business_definition": 'Number of storage bins that are empty and available.',
            "sample_value": '77'
        },
        {
            "name": 'utilization_pct',
            "description": 'Utilization percentage',
            "datatype": 'DECIMAL(5,2)',
            "nullable": True,
            "business_definition": 'Percentage of total storage bins that are occupied.',
            "sample_value": '84.60'
        },
        {
            "name": 'blocked_bins',
            "description": 'Blocked bins count',
            "datatype": 'INTEGER',
            "nullable": True,
            "business_definition": 'Number of bins that are blocked and unavailable.',
            "sample_value": '0'
        }
        ]
    },
    {
        "name": 'agg_monthly_logistics_cost',
        "description": 'Monthly logistics cost aggregate by cost category and plant',
        "domain": 'logistics',
        "platform": 'sap',
        "tags": ['Logistics', 'Analytics', 'Finance', 'Silver', 'PowerBI'],
        "columns": [
        {
            "name": 'year_month',
            "description": 'Year-month period',
            "datatype": 'VARCHAR(10)',
            "nullable": False,
            "business_definition": 'Reporting period in YYYY-MM format for cost aggregation.',
            "sample_value": '2024-06'
        },
        {
            "name": 'plant',
            "description": 'Plant code',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Plant for which logistics cost is aggregated.',
            "sample_value": 'VF01'
        },
        {
            "name": 'cost_category',
            "description": 'Logistics cost category',
            "datatype": 'VARCHAR(50)',
            "nullable": True,
            "business_definition": 'Category such as transportation, warehousing, or handling.',
            "sample_value": 'Transportation'
        },
        {
            "name": 'total_cost_vnd',
            "description": 'Total cost in VND',
            "datatype": 'DECIMAL(18,2)',
            "nullable": True,
            "business_definition": 'Aggregated logistics cost for the month in VND.',
            "sample_value": '2450000000.00'
        },
        {
            "name": 'budget_vnd',
            "description": 'Monthly budget in VND',
            "datatype": 'DECIMAL(18,2)',
            "nullable": True,
            "business_definition": 'Budgeted logistics cost for the month in VND.',
            "sample_value": '2500000000.00'
        },
        {
            "name": 'variance_pct',
            "description": 'Budget variance percentage',
            "datatype": 'DECIMAL(5,2)',
            "nullable": True,
            "business_definition": 'Percentage variance between actual cost and budget.',
            "sample_value": '-2.00'
        }
        ]
    },
    {
        "name": 'sap_bkpf',
        "description": 'Accounting Document Header - header data for financial accounting documents',
        "domain": 'finance',
        "platform": 'sap',
        "tags": ['Finance', 'Transactional', 'SAP', 'Critical', 'Certified', 'Gold'],
        "columns": [
        {
            "name": 'belnr',
            "description": 'Accounting document number',
            "datatype": 'VARCHAR(30)',
            "nullable": False,
            "business_definition": 'SAP accounting document number uniquely identifying a posted financial document.',
            "sample_value": 'DOC-2024-1000001'
        },
        {
            "name": 'bukrs',
            "description": 'Company code',
            "datatype": 'VARCHAR(10)',
            "nullable": False,
            "business_definition": 'Company code for which the financial document is posted.',
            "sample_value": 'VF00'
        },
        {
            "name": 'bldat',
            "description": 'Document date',
            "datatype": 'DATE',
            "nullable": True,
            "business_definition": 'Date on which the document was created in the business context.',
            "sample_value": '2024-06-10'
        },
        {
            "name": 'budat',
            "description": 'Posting date',
            "datatype": 'DATE',
            "nullable": True,
            "business_definition": 'Date on which the document is posted for financial accounting.',
            "sample_value": '2024-06-10'
        },
        {
            "name": 'blart',
            "description": 'Document type',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'SAP document type such as SA for G/L posting or KR for vendor invoice.',
            "sample_value": 'SA'
        },
        {
            "name": 'waers',
            "description": 'Currency code',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Transaction currency code used in the document.',
            "sample_value": 'VND'
        },
        {
            "name": 'cpudt',
            "description": 'Entry date',
            "datatype": 'DATE',
            "nullable": True,
            "business_definition": 'Date when the document was entered into the SAP system.',
            "sample_value": '2024-06-10'
        },
        {
            "name": 'xblnr',
            "description": 'External document reference',
            "datatype": 'VARCHAR(50)',
            "nullable": True,
            "business_definition": 'External reference number from the source document.',
            "sample_value": 'INV-2024-8823'
        },
        {
            "name": 'bktxt',
            "description": 'Document header text',
            "datatype": 'VARCHAR(80)',
            "nullable": True,
            "business_definition": 'Brief header text describing the purpose of the accounting document.',
            "sample_value": 'Monthly G/L posting June 2024'
        }
        ]
    },
    {
        "name": 'sap_bseg',
        "description": 'Accounting Document Segment - line items for accounting documents',
        "domain": 'finance',
        "platform": 'sap',
        "tags": ['Finance', 'Transactional', 'SAP', 'Critical', 'Certified', 'Gold'],
        "columns": [
        {
            "name": 'belnr',
            "description": 'Accounting document number',
            "datatype": 'VARCHAR(30)',
            "nullable": False,
            "business_definition": 'Document number linking the line item to the accounting document header.',
            "sample_value": 'DOC-2024-1000001'
        },
        {
            "name": 'buzei',
            "description": 'Line item number',
            "datatype": 'VARCHAR(10)',
            "nullable": False,
            "business_definition": 'Sequential number identifying the line item within the document.',
            "sample_value": '001'
        },
        {
            "name": 'bukrs',
            "description": 'Company code',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Company code for the line item posting.',
            "sample_value": 'VF00'
        },
        {
            "name": 'saknr',
            "description": 'G/L account number',
            "datatype": 'VARCHAR(20)',
            "nullable": True,
            "business_definition": 'General ledger account number being debited or credited.',
            "sample_value": 'GL-500100'
        },
        {
            "name": 'hkont',
            "description": 'Account number',
            "datatype": 'VARCHAR(20)',
            "nullable": True,
            "business_definition": 'Customer, vendor, or G/L account depending on document type.',
            "sample_value": 'GL-500100'
        },
        {
            "name": 'wrbtr',
            "description": 'Amount in document currency',
            "datatype": 'DECIMAL(18,2)',
            "nullable": True,
            "business_definition": 'Transaction amount in the document currency with sign.',
            "sample_value": '150000000.00'
        },
        {
            "name": 'dmbtr',
            "description": 'Amount in local currency (VND)',
            "datatype": 'DECIMAL(18,2)',
            "nullable": True,
            "business_definition": 'Amount in company code currency after translation.',
            "sample_value": '150000000.00'
        },
        {
            "name": 'shkzg',
            "description": 'Debit/credit indicator',
            "datatype": 'VARCHAR(1)',
            "nullable": True,
            "business_definition": 'Indicator S for debit or H for credit posting.',
            "sample_value": 'S'
        },
        {
            "name": 'kostl',
            "description": 'Cost center',
            "datatype": 'VARCHAR(20)',
            "nullable": True,
            "business_definition": 'Cost center code for cost allocation of the line item.',
            "sample_value": 'CC-1001'
        },
        {
            "name": 'zuonr',
            "description": 'Assignment number',
            "datatype": 'VARCHAR(30)',
            "nullable": True,
            "business_definition": 'Additional assignment field for internal reporting.',
            "sample_value": 'ASG-2024-001'
        }
        ]
    },
    {
        "name": 'sap_ska1',
        "description": 'GL Account Master - general ledger account master data',
        "domain": 'finance',
        "platform": 'sap',
        "tags": ['Finance', 'MasterData', 'SAP', 'Certified', 'Gold'],
        "columns": [
        {
            "name": 'saknr',
            "description": 'G/L account number',
            "datatype": 'VARCHAR(20)',
            "nullable": False,
            "business_definition": 'SAP G/L account number from the chart of accounts.',
            "sample_value": 'GL-500100'
        },
        {
            "name": 'ktopl',
            "description": 'Chart of accounts',
            "datatype": 'VARCHAR(10)',
            "nullable": False,
            "business_definition": 'Chart of accounts code to which the G/L account belongs.',
            "sample_value": 'COAVF'
        },
        {
            "name": 'txt20',
            "description": 'Short account description',
            "datatype": 'VARCHAR(40)',
            "nullable": True,
            "business_definition": 'Short text describing the G/L account purpose.',
            "sample_value": 'Raw Material Cost'
        },
        {
            "name": 'txt50',
            "description": 'Long account description',
            "datatype": 'VARCHAR(100)',
            "nullable": True,
            "business_definition": 'Long description providing detailed account purpose.',
            "sample_value": 'Raw Material Procurement Cost - Automotive Parts'
        },
        {
            "name": 'bilkt',
            "description": 'Group account number',
            "datatype": 'VARCHAR(20)',
            "nullable": True,
            "business_definition": 'Group account number used for consolidation reporting.',
            "sample_value": 'GRP-5001'
        },
        {
            "name": 'stype',
            "description": 'Account type',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Classification such as P&L, balance sheet, or off-balance sheet.',
            "sample_value": 'P&L'
        },
        {
            "name": 'xbilk',
            "description": 'Balance sheet account indicator',
            "datatype": 'BOOLEAN',
            "nullable": True,
            "business_definition": 'Flag indicating whether the account is a balance sheet account.',
            "sample_value": 'False'
        },
        {
            "name": 'aktiv',
            "description": 'Account status',
            "datatype": 'VARCHAR(1)',
            "nullable": True,
            "business_definition": 'Status of the G/L account such as active or blocked.',
            "sample_value": 'X'
        }
        ]
    },
    {
        "name": 'sap_knb1',
        "description": 'Customer Master (Company Code) - customer master data at company code level',
        "domain": 'finance',
        "platform": 'sap',
        "tags": ['Finance', 'MasterData', 'SAP', 'Gold', 'PII'],
        "columns": [
        {
            "name": 'kunnr',
            "description": 'Customer number',
            "datatype": 'VARCHAR(20)',
            "nullable": False,
            "business_definition": 'SAP customer account number assigned to the business partner.',
            "sample_value": 'CUST-10001'
        },
        {
            "name": 'bukrs',
            "description": 'Company code',
            "datatype": 'VARCHAR(10)',
            "nullable": False,
            "business_definition": 'Company code for which the customer master data is maintained.',
            "sample_value": 'VF00'
        },
        {
            "name": 'erdat',
            "description": 'Creation date',
            "datatype": 'DATE',
            "nullable": True,
            "business_definition": 'Date when the customer master was created in the company code.',
            "sample_value": '2022-05-15'
        },
        {
            "name": 'zuawa',
            "description": 'Key for sorting and listing',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Sort key used for account listing and reporting.',
            "sample_value": '002'
        },
        {
            "name": 'waers',
            "description": 'Currency code',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Currency used for transactions with the customer.',
            "sample_value": 'VND'
        },
        {
            "name": 'akont',
            "description": 'Reconciliation account',
            "datatype": 'VARCHAR(20)',
            "nullable": True,
            "business_definition": 'G/L reconciliation account for automatic posting of customer transactions.',
            "sample_value": 'GL-100100'
        },
        {
            "name": 'kredit',
            "description": 'Credit limit',
            "datatype": 'DECIMAL(18,2)',
            "nullable": True,
            "business_definition": 'Credit limit assigned to the customer in company code currency.',
            "sample_value": '5000000000.00'
        },
        {
            "name": 'loevm',
            "description": 'Deletion flag',
            "datatype": 'VARCHAR(1)',
            "nullable": True,
            "business_definition": 'Flag indicating whether the customer record is marked for deletion.',
            "sample_value": 'N'
        }
        ]
    },
    {
        "name": 'sap_lfb1',
        "description": 'Vendor Master (Company Code) - vendor master data at company code level',
        "domain": 'finance',
        "platform": 'sap',
        "tags": ['Finance', 'MasterData', 'SAP', 'Gold'],
        "columns": [
        {
            "name": 'lifnr',
            "description": 'Vendor number',
            "datatype": 'VARCHAR(20)',
            "nullable": False,
            "business_definition": 'SAP vendor account number assigned to the supplier business partner.',
            "sample_value": 'VEN-50001'
        },
        {
            "name": 'bukrs',
            "description": 'Company code',
            "datatype": 'VARCHAR(10)',
            "nullable": False,
            "business_definition": 'Company code for which the vendor master data is maintained.',
            "sample_value": 'VF00'
        },
        {
            "name": 'erdat',
            "description": 'Creation date',
            "datatype": 'DATE',
            "nullable": True,
            "business_definition": 'Date when the vendor master was created in the company code.',
            "sample_value": '2021-11-20'
        },
        {
            "name": 'akont',
            "description": 'Reconciliation account',
            "datatype": 'VARCHAR(20)',
            "nullable": True,
            "business_definition": 'G/L reconciliation account for automatic posting of vendor transactions.',
            "sample_value": 'GL-200100'
        },
        {
            "name": 'zuawa',
            "description": 'Sort key',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Sort key for vendor account listing and reporting.',
            "sample_value": '001'
        },
        {
            "name": 'waers',
            "description": 'Currency code',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Transaction currency code for the vendor.',
            "sample_value": 'VND'
        },
        {
            "name": 'sperr',
            "description": 'Posting block indicator',
            "datatype": 'VARCHAR(1)',
            "nullable": True,
            "business_definition": 'Flag indicating whether posting to this vendor account is blocked.',
            "sample_value": 'N'
        },
        {
            "name": 'loevm',
            "description": 'Deletion flag',
            "datatype": 'VARCHAR(1)',
            "nullable": True,
            "business_definition": 'Flag indicating whether the vendor record is marked for deletion.',
            "sample_value": 'N'
        }
        ]
    },
    {
        "name": 'sap_coep',
        "description": 'CO Line Items - controlling line items for cost accounting postings',
        "domain": 'finance',
        "platform": 'sap',
        "tags": ['Finance', 'Transactional', 'SAP', 'Gold', 'Internal'],
        "columns": [
        {
            "name": 'belnr',
            "description": 'CO document number',
            "datatype": 'VARCHAR(30)',
            "nullable": False,
            "business_definition": 'SAP controlling document number for cost accounting postings.',
            "sample_value": 'CO-DOC-2024-50001'
        },
        {
            "name": 'buzei',
            "description": 'Line item number',
            "datatype": 'VARCHAR(10)',
            "nullable": False,
            "business_definition": 'Sequential line item number within the controlling document.',
            "sample_value": '001'
        },
        {
            "name": 'objnr',
            "description": 'Object number',
            "datatype": 'VARCHAR(30)',
            "nullable": True,
            "business_definition": 'Internal object number for the cost object such as cost center.',
            "sample_value": 'OBJ-CC-1001'
        },
        {
            "name": 'kostl',
            "description": 'Cost center',
            "datatype": 'VARCHAR(20)',
            "nullable": True,
            "business_definition": 'Cost center receiving the cost posting.',
            "sample_value": 'CC-1001'
        },
        {
            "name": 'wkgbtr',
            "description": 'Amount in cost object currency',
            "datatype": 'DECIMAL(18,2)',
            "nullable": True,
            "business_definition": 'Cost amount posted in the controlling area currency.',
            "sample_value": '25000000.00'
        },
        {
            "name": 'meinb',
            "description": 'Unit of measure for quantity',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Unit of measure for the quantity posted.',
            "sample_value": 'EA'
        },
        {
            "name": 'menge',
            "description": 'Quantity',
            "datatype": 'DECIMAL(15,3)',
            "nullable": True,
            "business_definition": 'Quantity posted in the cost accounting line item.',
            "sample_value": '10.000'
        },
        {
            "name": 'bldat',
            "description": 'Document date',
            "datatype": 'DATE',
            "nullable": True,
            "business_definition": 'Date of the original accounting document generating the CO posting.',
            "sample_value": '2024-06-10'
        },
        {
            "name": 'usnam',
            "description": 'User name',
            "datatype": 'VARCHAR(20)',
            "nullable": True,
            "business_definition": 'SAP user ID that created the cost accounting posting.',
            "sample_value": 'FIN_USER'
        }
        ]
    },
    {
        "name": 'sap_anep',
        "description": 'Asset Line Items - asset accounting line items for fixed assets',
        "domain": 'finance',
        "platform": 'sap',
        "tags": ['Finance', 'Transactional', 'SAP', 'Gold'],
        "columns": [
        {
            "name": 'belnr',
            "description": 'Asset document number',
            "datatype": 'VARCHAR(30)',
            "nullable": False,
            "business_definition": 'SAP asset accounting document number for fixed asset postings.',
            "sample_value": 'AS-DOC-2024-10001'
        },
        {
            "name": 'buzei',
            "description": 'Line item number',
            "datatype": 'VARCHAR(10)',
            "nullable": False,
            "business_definition": 'Sequential line item number within the asset document.',
            "sample_value": '001'
        },
        {
            "name": 'anln1',
            "description": 'Main asset number',
            "datatype": 'VARCHAR(20)',
            "nullable": False,
            "business_definition": 'Main fixed asset number from the asset master record.',
            "sample_value": 'AS-10001'
        },
        {
            "name": 'anln2',
            "description": 'Asset sub-number',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Asset sub-number for component-level asset tracking.',
            "sample_value": '0001'
        },
        {
            "name": 'kostl',
            "description": 'Cost center',
            "datatype": 'VARCHAR(20)',
            "nullable": True,
            "business_definition": 'Cost center responsible for the asset.',
            "sample_value": 'CC-1001'
        },
        {
            "name": 'menge',
            "description": 'Quantity',
            "datatype": 'DECIMAL(15,3)',
            "nullable": True,
            "business_definition": 'Quantity posted in the asset line item.',
            "sample_value": '1.000'
        },
        {
            "name": 'wrbtr',
            "description": 'Amount in document currency',
            "datatype": 'DECIMAL(18,2)',
            "nullable": True,
            "business_definition": 'Transaction amount for the asset posting.',
            "sample_value": '5000000000.00'
        },
        {
            "name": 'bldat',
            "description": 'Document date',
            "datatype": 'DATE',
            "nullable": True,
            "business_definition": 'Date of the asset accounting document.',
            "sample_value": '2024-06-10'
        }
        ]
    },
    {
        "name": 'sap_faglflext',
        "description": 'General Ledger Balances - G/L account balance data',
        "domain": 'finance',
        "platform": 'sap',
        "tags": ['Finance', 'Transactional', 'SAP', 'Gold'],
        "columns": [
        {
            "name": 'ryear',
            "description": 'Fiscal year',
            "datatype": 'INTEGER',
            "nullable": False,
            "business_definition": 'Fiscal year of the G/L balance.',
            "sample_value": '2024'
        },
        {
            "name": 'racct',
            "description": 'G/L account number',
            "datatype": 'VARCHAR(20)',
            "nullable": False,
            "business_definition": 'G/L account number for the balance.',
            "sample_value": 'GL-500100'
        },
        {
            "name": 'rbukrs',
            "description": 'Company code',
            "datatype": 'VARCHAR(10)',
            "nullable": False,
            "business_definition": 'Company code for the balance.',
            "sample_value": 'VF00'
        },
        {
            "name": 'rldnr',
            "description": 'Ledger',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Ledger code for parallel accounting.',
            "sample_value": '0L'
        },
        {
            "name": 'hslvt',
            "description": 'Balance in company code currency',
            "datatype": 'DECIMAL(18,2)',
            "nullable": True,
            "business_definition": 'Opening balance in company code currency VND.',
            "sample_value": '5000000000.00'
        },
        {
            "name": 'hsl01',
            "description": 'Period 1 balance',
            "datatype": 'DECIMAL(18,2)',
            "nullable": True,
            "business_definition": 'Balance for posting period 1 in company code currency.',
            "sample_value": '5200000000.00'
        },
        {
            "name": 'hsl02',
            "description": 'Period 2 balance',
            "datatype": 'DECIMAL(18,2)',
            "nullable": True,
            "business_definition": 'Balance for posting period 2 in company code currency.',
            "sample_value": '5100000000.00'
        },
        {
            "name": 'hsl03',
            "description": 'Period 3 balance',
            "datatype": 'DECIMAL(18,2)',
            "nullable": True,
            "business_definition": 'Balance for posting period 3 in company code currency.',
            "sample_value": '5300000000.00'
        }
        ]
    },
    {
        "name": 'stg_gl_transactions',
        "description": 'Staging table for general ledger transaction data from SAP FI',
        "domain": 'finance',
        "platform": 'sap',
        "tags": ['Finance', 'Analytics', 'Bronze', 'Critical'],
        "columns": [
        {
            "name": 'record_id',
            "description": 'Staging record UUID',
            "datatype": 'VARCHAR(100)',
            "nullable": False,
            "business_definition": 'Universally unique identifier for the staging record.',
            "sample_value": '660e8400-e29b-41d4-a716-446655440001'
        },
        {
            "name": 'document_number',
            "description": 'SAP accounting document number',
            "datatype": 'VARCHAR(30)',
            "nullable": True,
            "business_definition": 'SAP accounting document number from BKPF table.',
            "sample_value": 'DOC-2024-1000001'
        },
        {
            "name": 'company_code',
            "description": 'Company code',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Company code of the financial transaction.',
            "sample_value": 'VF00'
        },
        {
            "name": 'gl_account',
            "description": 'G/L account number',
            "datatype": 'VARCHAR(20)',
            "nullable": True,
            "business_definition": 'G/L account posted in the transaction line item.',
            "sample_value": 'GL-500100'
        },
        {
            "name": 'amount_vnd',
            "description": 'Transaction amount in VND',
            "datatype": 'DECIMAL(18,2)',
            "nullable": True,
            "business_definition": 'Transaction amount in Vietnamese Dong with sign.',
            "sample_value": '150000000.00'
        },
        {
            "name": 'posting_date',
            "description": 'Posting date',
            "datatype": 'DATE',
            "nullable": True,
            "business_definition": 'Date when the transaction was posted.',
            "sample_value": '2024-06-10'
        },
        {
            "name": 'document_type',
            "description": 'SAP document type',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Type of accounting document such as SA, KR, or DR.',
            "sample_value": 'SA'
        },
        {
            "name": 'source_system',
            "description": 'Source system code',
            "datatype": 'VARCHAR(50)',
            "nullable": True,
            "business_definition": 'System from which the GL data was extracted.',
            "sample_value": 'SAP_ECC'
        },
        {
            "name": 'ingestion_ts',
            "description": 'Ingestion timestamp',
            "datatype": 'TIMESTAMP',
            "nullable": False,
            "business_definition": 'Timestamp when the record was ingested into staging.',
            "sample_value": '2024-06-10 22:00:00'
        }
        ]
    },
    {
        "name": 'stg_ap_invoices',
        "description": 'Staging table for accounts payable invoice data',
        "domain": 'finance',
        "platform": 'sap',
        "tags": ['Finance', 'Analytics', 'Bronze', 'Critical'],
        "columns": [
        {
            "name": 'ap_record_id',
            "description": 'AP staging record UUID',
            "datatype": 'VARCHAR(100)',
            "nullable": False,
            "business_definition": 'Unique identifier for the AP invoice staging record.',
            "sample_value": '770e8400-e29b-41d4-a716-446655440002'
        },
        {
            "name": 'invoice_number',
            "description": 'Vendor invoice number',
            "datatype": 'VARCHAR(50)',
            "nullable": False,
            "business_definition": 'Invoice number provided by the vendor or supplier.',
            "sample_value": 'INV-8823'
        },
        {
            "name": 'vendor_id',
            "description": 'SAP vendor code',
            "datatype": 'VARCHAR(20)',
            "nullable": True,
            "business_definition": 'SAP vendor account number for the invoice issuer.',
            "sample_value": 'VEN-50001'
        },
        {
            "name": 'invoice_amount_vnd',
            "description": 'Invoice amount in VND',
            "datatype": 'DECIMAL(18,2)',
            "nullable": True,
            "business_definition": 'Total invoice amount including tax in VND.',
            "sample_value": '750000000.00'
        },
        {
            "name": 'tax_amount_vnd',
            "description": 'Tax amount in VND',
            "datatype": 'DECIMAL(18,2)',
            "nullable": True,
            "business_definition": 'VAT or other tax amount included in the invoice.',
            "sample_value": '75000000.00'
        },
        {
            "name": 'invoice_date',
            "description": 'Invoice issue date',
            "datatype": 'DATE',
            "nullable": True,
            "business_definition": 'Date when the vendor issued the invoice.',
            "sample_value": '2024-06-05'
        },
        {
            "name": 'due_date',
            "description": 'Payment due date',
            "datatype": 'DATE',
            "nullable": True,
            "business_definition": 'Due date for payment based on vendor payment terms.',
            "sample_value": '2024-07-05'
        },
        {
            "name": 'status',
            "description": 'Invoice processing status',
            "datatype": 'VARCHAR(30)',
            "nullable": True,
            "business_definition": 'Status such as received, validated, or posted.',
            "sample_value": 'posted'
        },
        {
            "name": 'ingestion_ts',
            "description": 'Ingestion timestamp',
            "datatype": 'TIMESTAMP',
            "nullable": False,
            "business_definition": 'Timestamp when the invoice was ingested into staging.',
            "sample_value": '2024-06-10 23:00:00'
        }
        ]
    },
    {
        "name": 'stg_ar_receipts',
        "description": 'Staging table for accounts receivable receipt data from customer payments',
        "domain": 'finance',
        "platform": 'sap',
        "tags": ['Finance', 'Analytics', 'Bronze', 'Critical'],
        "columns": [
        {
            "name": 'ar_record_id',
            "description": 'AR staging record UUID',
            "datatype": 'VARCHAR(100)',
            "nullable": False,
            "business_definition": 'Unique identifier for the AR receipt staging record.',
            "sample_value": '880e8400-e29b-41d4-a716-446655440003'
        },
        {
            "name": 'receipt_number',
            "description": 'Customer receipt number',
            "datatype": 'VARCHAR(50)',
            "nullable": False,
            "business_definition": 'Receipt or payment reference number from the customer.',
            "sample_value": 'RCT-2024-12345'
        },
        {
            "name": 'customer_id',
            "description": 'Customer code',
            "datatype": 'VARCHAR(20)',
            "nullable": True,
            "business_definition": 'SAP customer account number making the payment.',
            "sample_value": 'CUST-10001'
        },
        {
            "name": 'receipt_amount_vnd',
            "description": 'Receipt amount in VND',
            "datatype": 'DECIMAL(18,2)',
            "nullable": True,
            "business_definition": 'Payment amount received from the customer in VND.',
            "sample_value": '2000000000.00'
        },
        {
            "name": 'receipt_date',
            "description": 'Receipt date',
            "datatype": 'DATE',
            "nullable": True,
            "business_definition": 'Date when the customer payment was received.',
            "sample_value": '2024-06-12'
        },
        {
            "name": 'payment_method',
            "description": 'Payment method code',
            "datatype": 'VARCHAR(30)',
            "nullable": True,
            "business_definition": 'Method of payment such as bank transfer or credit card.',
            "sample_value": 'bank_transfer'
        },
        {
            "name": 'bank_account',
            "description": 'Bank account reference',
            "datatype": 'VARCHAR(50)',
            "nullable": True,
            "business_definition": 'Bank account number from which the payment was made.',
            "sample_value": 'VN1234567890'
        },
        {
            "name": 'status',
            "description": 'Receipt processing status',
            "datatype": 'VARCHAR(30)',
            "nullable": True,
            "business_definition": 'Status such as matched, uncleared, or posted.',
            "sample_value": 'matched'
        },
        {
            "name": 'ingestion_ts',
            "description": 'Ingestion timestamp',
            "datatype": 'TIMESTAMP',
            "nullable": False,
            "business_definition": 'Timestamp when the receipt was ingested into staging.',
            "sample_value": '2024-06-12 20:00:00'
        }
        ]
    },
    {
        "name": 'fact_general_ledger',
        "description": 'General ledger fact table at the line-item grain for financial reporting',
        "domain": 'finance',
        "platform": 'sap',
        "tags": ['Finance', 'Analytics', 'Critical', 'Certified', 'Gold', 'PowerBI'],
        "columns": [
        {
            "name": 'gl_line_id',
            "description": 'General ledger line unique ID',
            "datatype": 'VARCHAR(100)',
            "nullable": False,
            "business_definition": 'Unique identifier for each G/L line item in the warehouse.',
            "sample_value": 'GL-LINE-2024-1000001-001'
        },
        {
            "name": 'document_number',
            "description": 'Accounting document number',
            "datatype": 'VARCHAR(30)',
            "nullable": True,
            "business_definition": 'SAP accounting document number from BKPF.',
            "sample_value": 'DOC-2024-1000001'
        },
        {
            "name": 'company_code',
            "description": 'Company code',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Company code for the G/L posting.',
            "sample_value": 'VF00'
        },
        {
            "name": 'gl_account',
            "description": 'G/L account number',
            "datatype": 'VARCHAR(20)',
            "nullable": True,
            "business_definition": 'General ledger account number posted.',
            "sample_value": 'GL-500100'
        },
        {
            "name": 'cost_center',
            "description": 'Cost center code',
            "datatype": 'VARCHAR(20)',
            "nullable": True,
            "business_definition": 'Cost center assigned for cost allocation.',
            "sample_value": 'CC-1001'
        },
        {
            "name": 'profit_center',
            "description": 'Profit center code',
            "datatype": 'VARCHAR(20)',
            "nullable": True,
            "business_definition": 'Profit center assigned for profitability analysis.',
            "sample_value": 'PC-2001'
        },
        {
            "name": 'amount_vnd',
            "description": 'Line amount in VND',
            "datatype": 'DECIMAL(18,2)',
            "nullable": True,
            "business_definition": 'Line item amount in VND positive for debit, negative for credit.',
            "sample_value": '150000000.00'
        },
        {
            "name": 'debit_credit',
            "description": 'Debit or credit indicator',
            "datatype": 'VARCHAR(1)',
            "nullable": True,
            "business_definition": 'Indicator S for debit or H for credit entry.',
            "sample_value": 'S'
        },
        {
            "name": 'posting_date',
            "description": 'Posting date',
            "datatype": 'DATE',
            "nullable": True,
            "business_definition": 'Date when the G/L posting was recorded.',
            "sample_value": '2024-06-10'
        },
        {
            "name": 'fiscal_year',
            "description": 'Fiscal year',
            "datatype": 'INTEGER',
            "nullable": True,
            "business_definition": 'Fiscal year of the posting for period-end reporting.',
            "sample_value": '2024'
        }
        ]
    },
    {
        "name": 'fact_accounts_payable',
        "description": 'Accounts payable fact table at the invoice and payment grain',
        "domain": 'finance',
        "platform": 'sap',
        "tags": ['Finance', 'Analytics', 'Critical', 'Certified', 'Gold', 'PowerBI'],
        "columns": [
        {
            "name": 'ap_line_id',
            "description": 'AP line unique ID',
            "datatype": 'VARCHAR(100)',
            "nullable": False,
            "business_definition": 'Unique identifier for each AP line item in the warehouse.',
            "sample_value": 'AP-LINE-2024-50001-001'
        },
        {
            "name": 'invoice_number',
            "description": 'Vendor invoice number',
            "datatype": 'VARCHAR(50)',
            "nullable": True,
            "business_definition": 'Invoice number issued by the vendor.',
            "sample_value": 'INV-8823'
        },
        {
            "name": 'vendor_id',
            "description": 'Vendor code',
            "datatype": 'VARCHAR(20)',
            "nullable": True,
            "business_definition": 'SAP vendor account number.',
            "sample_value": 'VEN-50001'
        },
        {
            "name": 'invoice_amount_vnd',
            "description": 'Invoice amount in VND',
            "datatype": 'DECIMAL(18,2)',
            "nullable": True,
            "business_definition": 'Total invoice amount in Vietnamese Dong.',
            "sample_value": '750000000.00'
        },
        {
            "name": 'paid_amount_vnd',
            "description": 'Paid amount in VND',
            "datatype": 'DECIMAL(18,2)',
            "nullable": True,
            "business_definition": 'Total amount paid to the vendor against this invoice.',
            "sample_value": '750000000.00'
        },
        {
            "name": 'open_amount_vnd',
            "description": 'Open balance in VND',
            "datatype": 'DECIMAL(18,2)',
            "nullable": True,
            "business_definition": 'Outstanding amount yet to be paid on the invoice.',
            "sample_value": '0.00'
        },
        {
            "name": 'invoice_date',
            "description": 'Invoice date',
            "datatype": 'DATE',
            "nullable": True,
            "business_definition": 'Date when the vendor issued the invoice.',
            "sample_value": '2024-06-05'
        },
        {
            "name": 'due_date',
            "description": 'Payment due date',
            "datatype": 'DATE',
            "nullable": True,
            "business_definition": 'Due date for payment as per vendor terms.',
            "sample_value": '2024-07-05'
        },
        {
            "name": 'payment_date',
            "description": 'Payment date',
            "datatype": 'DATE',
            "nullable": True,
            "business_definition": 'Date when the payment was executed.',
            "sample_value": '2024-06-25'
        },
        {
            "name": 'days_overdue',
            "description": 'Days overdue',
            "datatype": 'INTEGER',
            "nullable": True,
            "business_definition": 'Number of days past due, zero if paid on time.',
            "sample_value": '0'
        }
        ]
    },
    {
        "name": 'fact_accounts_receivable',
        "description": 'Accounts receivable fact table at the receipt and invoice grain',
        "domain": 'finance',
        "platform": 'sap',
        "tags": ['Finance', 'Analytics', 'Critical', 'Certified', 'Gold', 'PowerBI'],
        "columns": [
        {
            "name": 'ar_line_id',
            "description": 'AR line unique ID',
            "datatype": 'VARCHAR(100)',
            "nullable": False,
            "business_definition": 'Unique identifier for each AR line item in the warehouse.',
            "sample_value": 'AR-LINE-2024-10001-001'
        },
        {
            "name": 'customer_id',
            "description": 'Customer code',
            "datatype": 'VARCHAR(20)',
            "nullable": True,
            "business_definition": 'SAP customer account number.',
            "sample_value": 'CUST-10001'
        },
        {
            "name": 'invoice_number',
            "description": 'Sales invoice number',
            "datatype": 'VARCHAR(50)',
            "nullable": True,
            "business_definition": 'Invoice number issued to the customer.',
            "sample_value": 'INV-VF8-001'
        },
        {
            "name": 'invoice_amount_vnd',
            "description": 'Invoice amount in VND',
            "datatype": 'DECIMAL(18,2)',
            "nullable": True,
            "business_definition": 'Total invoice amount in Vietnamese Dong.',
            "sample_value": '3200000000.00'
        },
        {
            "name": 'received_amount_vnd',
            "description": 'Received payment in VND',
            "datatype": 'DECIMAL(18,2)',
            "nullable": True,
            "business_definition": 'Amount received from the customer in VND.',
            "sample_value": '3200000000.00'
        },
        {
            "name": 'open_amount_vnd',
            "description": 'Open balance in VND',
            "datatype": 'DECIMAL(18,2)',
            "nullable": True,
            "business_definition": 'Outstanding amount yet to be collected in VND.',
            "sample_value": '0.00'
        },
        {
            "name": 'invoice_date',
            "description": 'Invoice date',
            "datatype": 'DATE',
            "nullable": True,
            "business_definition": 'Date of the sales invoice issued to the customer.',
            "sample_value": '2024-06-01'
        },
        {
            "name": 'due_date',
            "description": 'Payment due date',
            "datatype": 'DATE',
            "nullable": True,
            "business_definition": 'Due date for customer payment.',
            "sample_value": '2024-07-01'
        },
        {
            "name": 'receipt_date',
            "description": 'Receipt date',
            "datatype": 'DATE',
            "nullable": True,
            "business_definition": 'Date when the payment was actually received.',
            "sample_value": '2024-06-15'
        },
        {
            "name": 'days_outstanding',
            "description": 'Days outstanding',
            "datatype": 'INTEGER',
            "nullable": True,
            "business_definition": 'Number of days the invoice has been outstanding.',
            "sample_value": '14'
        }
        ]
    },
    {
        "name": 'dim_cost_center',
        "description": 'Cost center dimension table for controlling and cost allocation',
        "domain": 'finance',
        "platform": 'sap',
        "tags": ['Finance', 'MasterData', 'SAP', 'Certified', 'Gold', 'PowerBI'],
        "columns": [
        {
            "name": 'cost_center_sk',
            "description": 'Cost center surrogate key',
            "datatype": 'VARCHAR(100)',
            "nullable": False,
            "business_definition": 'Data warehouse surrogate key for the cost center dimension.',
            "sample_value": 'SK-CC-1001'
        },
        {
            "name": 'cost_center_id',
            "description": 'SAP cost center code',
            "datatype": 'VARCHAR(20)',
            "nullable": False,
            "business_definition": 'SAP cost center code from the controlling module.',
            "sample_value": 'CC-1001'
        },
        {
            "name": 'cost_center_name',
            "description": 'Cost center description',
            "datatype": 'VARCHAR(200)',
            "nullable": True,
            "business_definition": 'Descriptive name of the cost center for reporting.',
            "sample_value": 'Assembly Line 1 Operations'
        },
        {
            "name": 'controlling_area',
            "description": 'Controlling area code',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'SAP controlling area to which the cost center belongs.',
            "sample_value": 'VF00'
        },
        {
            "name": 'cost_center_category',
            "description": 'Category code',
            "datatype": 'VARCHAR(20)',
            "nullable": True,
            "business_definition": 'Categorization such as production, administration, or sales.',
            "sample_value": 'Production'
        },
        {
            "name": 'responsible_person',
            "description": 'Cost center manager email',
            "datatype": 'VARCHAR(100)',
            "nullable": True,
            "business_definition": 'Email of the cost center manager responsible for budget.',
            "sample_value": 'manager@vinfast.vn'
        },
        {
            "name": 'is_active',
            "description": 'Active cost center flag',
            "datatype": 'BOOLEAN',
            "nullable": True,
            "business_definition": 'Indicates whether the cost center is active for posting.',
            "sample_value": 'True'
        }
        ]
    },
    {
        "name": 'dim_profit_center',
        "description": 'Profit center dimension table for profitability reporting',
        "domain": 'finance',
        "platform": 'sap',
        "tags": ['Finance', 'MasterData', 'SAP', 'Certified', 'Gold', 'PowerBI'],
        "columns": [
        {
            "name": 'profit_center_sk',
            "description": 'Profit center surrogate key',
            "datatype": 'VARCHAR(100)',
            "nullable": False,
            "business_definition": 'Data warehouse surrogate key for profit center dimension.',
            "sample_value": 'SK-PC-2001'
        },
        {
            "name": 'profit_center_id',
            "description": 'SAP profit center code',
            "datatype": 'VARCHAR(20)',
            "nullable": False,
            "business_definition": 'SAP profit center code used for segment reporting.',
            "sample_value": 'PC-2001'
        },
        {
            "name": 'profit_center_name',
            "description": 'Profit center description',
            "datatype": 'VARCHAR(200)',
            "nullable": True,
            "business_definition": 'Descriptive name of the profit center for financial analysis.',
            "sample_value": 'VF8 - Electric SUV Line'
        },
        {
            "name": 'controlling_area',
            "description": 'Controlling area code',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'SAP controlling area to which the profit center belongs.',
            "sample_value": 'VF00'
        },
        {
            "name": 'segment',
            "description": 'Business segment code',
            "datatype": 'VARCHAR(30)',
            "nullable": True,
            "business_definition": 'Business segment code for external IFRS reporting.',
            "sample_value": 'SEG-EV'
        },
        {
            "name": 'department',
            "description": 'Department name',
            "datatype": 'VARCHAR(100)',
            "nullable": True,
            "business_definition": 'Department responsible for the profit center.',
            "sample_value": 'Electric Vehicle Division'
        },
        {
            "name": 'is_active',
            "description": 'Active profit center flag',
            "datatype": 'BOOLEAN',
            "nullable": True,
            "business_definition": 'Indicates whether the profit center is currently active.',
            "sample_value": 'True'
        }
        ]
    },
    {
        "name": 'dim_gl_account',
        "description": 'GL Account dimension table for chart of accounts attributes',
        "domain": 'finance',
        "platform": 'sap',
        "tags": ['Finance', 'MasterData', 'SAP', 'Certified', 'Gold', 'PowerBI'],
        "columns": [
        {
            "name": 'gl_account_sk',
            "description": 'GL account surrogate key',
            "datatype": 'VARCHAR(100)',
            "nullable": False,
            "business_definition": 'Data warehouse surrogate key for the GL account dimension.',
            "sample_value": 'SK-GL-500100'
        },
        {
            "name": 'gl_account_id',
            "description": 'SAP G/L account number',
            "datatype": 'VARCHAR(20)',
            "nullable": False,
            "business_definition": 'SAP G/L account number from SKA1.',
            "sample_value": 'GL-500100'
        },
        {
            "name": 'gl_account_name',
            "description": 'GL account description',
            "datatype": 'VARCHAR(200)',
            "nullable": True,
            "business_definition": 'Full description of the G/L account.',
            "sample_value": 'Raw Material Cost - Automotive'
        },
        {
            "name": 'chart_of_accounts',
            "description": 'Chart of accounts',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Chart of accounts code.',
            "sample_value": 'COAVF'
        },
        {
            "name": 'account_type',
            "description": 'Account type',
            "datatype": 'VARCHAR(20)',
            "nullable": True,
            "business_definition": 'Classification such as expense, revenue, asset, or liability.',
            "sample_value": 'Expense'
        },
        {
            "name": 'is_balance_sheet',
            "description": 'Balance sheet account flag',
            "datatype": 'BOOLEAN',
            "nullable": True,
            "business_definition": 'Indicates whether the account is a balance sheet account.',
            "sample_value": 'False'
        },
        {
            "name": 'is_active',
            "description": 'Active account flag',
            "datatype": 'BOOLEAN',
            "nullable": True,
            "business_definition": 'Indicates whether the account is active for posting.',
            "sample_value": 'True'
        }
        ]
    },
    {
        "name": 'agg_monthly_pnl',
        "description": 'Monthly P&L aggregate by profit center and cost element',
        "domain": 'finance',
        "platform": 'sap',
        "tags": ['Finance', 'Analytics', 'Certified', 'Silver', 'PowerBI'],
        "columns": [
        {
            "name": 'year_month',
            "description": 'Year-month period',
            "datatype": 'VARCHAR(10)',
            "nullable": False,
            "business_definition": 'Reporting period in YYYY-MM format for P&L aggregation.',
            "sample_value": '2024-06'
        },
        {
            "name": 'profit_center_id',
            "description": 'Profit center code',
            "datatype": 'VARCHAR(20)',
            "nullable": True,
            "business_definition": 'Profit center for the P&L aggregation.',
            "sample_value": 'PC-2001'
        },
        {
            "name": 'total_revenue_vnd',
            "description": 'Total revenue in VND',
            "datatype": 'DECIMAL(18,2)',
            "nullable": True,
            "business_definition": 'Total revenue recognized in Vietnamese Dong.',
            "sample_value": '125000000000.00'
        },
        {
            "name": 'total_cogs_vnd',
            "description": 'Total cost of goods sold in VND',
            "datatype": 'DECIMAL(18,2)',
            "nullable": True,
            "business_definition": 'Total cost of goods sold in Vietnamese Dong.',
            "sample_value": '87500000000.00'
        },
        {
            "name": 'gross_profit_vnd',
            "description": 'Gross profit in VND',
            "datatype": 'DECIMAL(18,2)',
            "nullable": True,
            "business_definition": 'Gross profit calculated as revenue minus COGS in VND.',
            "sample_value": '37500000000.00'
        },
        {
            "name": 'operating_expense_vnd',
            "description": 'Operating expenses in VND',
            "datatype": 'DECIMAL(18,2)',
            "nullable": True,
            "business_definition": 'Total operating expenses in Vietnamese Dong.',
            "sample_value": '15000000000.00'
        },
        {
            "name": 'net_profit_vnd',
            "description": 'Net profit in VND',
            "datatype": 'DECIMAL(18,2)',
            "nullable": True,
            "business_definition": 'Net profit after all expenses in Vietnamese Dong.',
            "sample_value": '22500000000.00'
        },
        {
            "name": 'gross_margin_pct',
            "description": 'Gross margin percentage',
            "datatype": 'DECIMAL(5,2)',
            "nullable": True,
            "business_definition": 'Gross margin as a percentage of revenue.',
            "sample_value": '30.00'
        },
        {
            "name": 'net_margin_pct',
            "description": 'Net margin percentage',
            "datatype": 'DECIMAL(5,2)',
            "nullable": True,
            "business_definition": 'Net profit margin as a percentage of revenue.',
            "sample_value": '18.00'
        }
        ]
    },
    {
        "name": 'agg_daily_cash_position',
        "description": 'Daily cash position aggregate by bank account and currency',
        "domain": 'finance',
        "platform": 'sap',
        "tags": ['Finance', 'Analytics', 'Certified', 'Silver', 'PowerBI'],
        "columns": [
        {
            "name": 'cash_date',
            "description": 'Cash position date',
            "datatype": 'DATE',
            "nullable": False,
            "business_definition": 'Calendar date for the daily cash position.',
            "sample_value": '2024-06-10'
        },
        {
            "name": 'bank_account_id',
            "description": 'Bank account code',
            "datatype": 'VARCHAR(30)',
            "nullable": True,
            "business_definition": 'Bank account identifier from the treasury module.',
            "sample_value": 'BA-VF-001'
        },
        {
            "name": 'currency',
            "description": 'Currency code',
            "datatype": 'VARCHAR(10)',
            "nullable": True,
            "business_definition": 'Currency of the bank account.',
            "sample_value": 'VND'
        },
        {
            "name": 'opening_balance_vnd',
            "description": 'Opening balance in VND',
            "datatype": 'DECIMAL(18,2)',
            "nullable": True,
            "business_definition": 'Cash balance at the start of the day in VND.',
            "sample_value": '50000000000.00'
        },
        {
            "name": 'total_inflows_vnd',
            "description": 'Total inflows in VND',
            "datatype": 'DECIMAL(18,2)',
            "nullable": True,
            "business_definition": 'Total cash inflows received during the day in VND.',
            "sample_value": '3200000000.00'
        },
        {
            "name": 'total_outflows_vnd',
            "description": 'Total outflows in VND',
            "datatype": 'DECIMAL(18,2)',
            "nullable": True,
            "business_definition": 'Total cash outflows during the day in VND.',
            "sample_value": '750000000.00'
        },
        {
            "name": 'closing_balance_vnd',
            "description": 'Closing balance in VND',
            "datatype": 'DECIMAL(18,2)',
            "nullable": True,
            "business_definition": 'Cash balance at the end of the day in VND.',
            "sample_value": '52450000000.00'
        },
        {
            "name": 'is_forecast',
            "description": 'Forecast indicator',
            "datatype": 'BOOLEAN',
            "nullable": True,
            "business_definition": 'Indicates whether the position is actual or forecast.',
            "sample_value": 'False'
        }
        ]
    },
    {
        "name": 'agg_budget_variance',
        "description": 'Budget variance aggregate comparing actuals against budget by cost center',
        "domain": 'finance',
        "platform": 'sap',
        "tags": ['Finance', 'Analytics', 'Certified', 'Silver', 'PowerBI'],
        "columns": [
        {
            "name": 'year_month',
            "description": 'Year-month period',
            "datatype": 'VARCHAR(10)',
            "nullable": False,
            "business_definition": 'Reporting period in YYYY-MM format for budget variance.',
            "sample_value": '2024-06'
        },
        {
            "name": 'cost_center_id',
            "description": 'Cost center code',
            "datatype": 'VARCHAR(20)',
            "nullable": True,
            "business_definition": 'Cost center for budget variance analysis.',
            "sample_value": 'CC-1001'
        },
        {
            "name": 'budget_amount_vnd',
            "description": 'Budgeted amount in VND',
            "datatype": 'DECIMAL(18,2)',
            "nullable": True,
            "business_definition": 'Budgeted expense amount for the period in VND.',
            "sample_value": '500000000.00'
        },
        {
            "name": 'actual_amount_vnd',
            "description": 'Actual amount in VND',
            "datatype": 'DECIMAL(18,2)',
            "nullable": True,
            "business_definition": 'Actual expense posted for the period in VND.',
            "sample_value": '485000000.00'
        },
        {
            "name": 'variance_vnd',
            "description": 'Variance amount in VND',
            "datatype": 'DECIMAL(18,2)',
            "nullable": True,
            "business_definition": 'Difference between budget and actual in VND.',
            "sample_value": '15000000.00'
        },
        {
            "name": 'variance_pct',
            "description": 'Variance percentage',
            "datatype": 'DECIMAL(5,2)',
            "nullable": True,
            "business_definition": 'Percentage variance between budget and actual.',
            "sample_value": '3.00'
        },
        {
            "name": 'variance_type',
            "description": 'Variance type',
            "datatype": 'VARCHAR(20)',
            "nullable": True,
            "business_definition": 'Classification such as favorable or unfavorable.',
            "sample_value": 'Favorable'
        }
        ]
    }
]
