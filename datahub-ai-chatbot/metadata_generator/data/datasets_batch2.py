DATASETS_BATCH2 = [
  {
    "name": "sap_ekko",
    "description": "Purchasing Document Header - header data for all purchase orders",
    "domain": "supply_chain",
    "platform": "sap",
    "tags": [
      "SupplyChain",
      "SAP",
      "MasterData"
    ],
    "columns": [
      {
        "name": "ebeln",
        "description": "Purchasing document number",
        "datatype": "VARCHAR(10)",
        "nullable": False,
        "business_definition": "Unique identifier for a purchase order document in SAP. Links to all PO items and history records across the procurement lifecycle.",
        "sample_value": "PO-4500012345"
      },
      {
        "name": "bsart",
        "description": "Purchasing document type",
        "datatype": "VARCHAR(4)",
        "nullable": False,
        "business_definition": "Categorizes the PO type - standard order, framework agreement, scheduling agreement, or subcontracting order - governing approval and release workflows.",
        "sample_value": "NB"
      },
      {
        "name": "ekorg",
        "description": "Purchasing organization",
        "datatype": "VARCHAR(4)",
        "nullable": False,
        "business_definition": "Organizational unit responsible for procurement activities. VinFast uses org codes like VF01 for domestic and VF02 for international sourcing.",
        "sample_value": "VF01"
      },
      {
        "name": "lifnr",
        "description": "Vendor account number",
        "datatype": "VARCHAR(10)",
        "nullable": False,
        "business_definition": "SAP vendor master key identifying the supplier. Each VinFast parts supplier is assigned a unique vendor code in this field.",
        "sample_value": "V000003456"
      },
      {
        "name": "bedat",
        "description": "Purchase order date",
        "datatype": "DATE",
        "nullable": True,
        "business_definition": "Date on which the purchasing document was created in the system. Used for aging analysis and procurement cycle time tracking.",
        "sample_value": "2025-11-15"
      },
      {
        "name": "waers",
        "description": "Currency key",
        "datatype": "VARCHAR(5)",
        "nullable": False,
        "business_definition": "ISO currency code for the PO. VinFast transacts in VND for domestic suppliers and USD/EUR for overseas components.",
        "sample_value": "VND"
      },
      {
        "name": "netwr",
        "description": "Net order value",
        "datatype": "DECIMAL(18,2)",
        "nullable": True,
        "business_definition": "Total net value of the purchase order after discounts but before taxes and freight. Key metric in spend aggregation.",
        "sample_value": "1250000000.00"
      },
      {
        "name": "aedat",
        "description": "Date of last change",
        "datatype": "DATE",
        "nullable": True,
        "business_definition": "Timestamp of the most recent modification to the PO header, used for audit trails and change monitoring.",
        "sample_value": "2025-11-20"
      },
      {
        "name": "reswk",
        "description": "Supplying plant",
        "datatype": "VARCHAR(4)",
        "nullable": True,
        "business_definition": "Plant code from which materials are supplied. Maps to VinFast manufacturing facilities in Hai Phong, Da Nang, or Ha Tinh.",
        "sample_value": "HP01"
      },
      {
        "name": "frgke",
        "description": "Release indicator",
        "datatype": "VARCHAR(1)",
        "nullable": True,
        "business_definition": "Indicates the PO release approval status (1=created, 2=manager approved, 3=finance approved). Controls procurement workflow gates.",
        "sample_value": "2"
      },
      {
        "name": "kdat",
        "description": "Delivery date",
        "datatype": "DATE",
        "nullable": True,
        "business_definition": "Scheduled delivery date agreed with supplier. Compared against actual goods receipt for on-time delivery scoring.",
        "sample_value": "2025-12-20"
      }
    ]
  },
  {
    "name": "sap_ekpo",
    "description": "Purchasing Document Item - line-item details for purchase orders",
    "domain": "supply_chain",
    "platform": "sap",
    "tags": [
      "SupplyChain",
      "SAP",
      "Transactional"
    ],
    "columns": [
      {
        "name": "ebeln",
        "description": "Purchasing document number",
        "datatype": "VARCHAR(10)",
        "nullable": False,
        "business_definition": "Foreign key to EKKO identifying the parent purchase order. Used in join operations for order-level analysis.",
        "sample_value": "PO-4500012345"
      },
      {
        "name": "ebelp",
        "description": "Item number of purchasing document",
        "datatype": "INTEGER",
        "nullable": False,
        "business_definition": "Sequential line item number within a PO. Combined with ebeln forms the unique key for PO item identification.",
        "sample_value": 10
      },
      {
        "name": "matnr",
        "description": "Material number",
        "datatype": "VARCHAR(18)",
        "nullable": True,
        "business_definition": "SAP material master key for the procured part or raw material. VinFast uses 18-character codes encoding vehicle model and part category.",
        "sample_value": "VF8-BATT-MOD-001"
      },
      {
        "name": "menge",
        "description": "PO quantity",
        "datatype": "DECIMAL(13,3)",
        "nullable": True,
        "business_definition": "Ordered quantity in the base unit of measure. For VinFast this could be units (batteries, motors) or kilograms (steel, aluminum).",
        "sample_value": "500.000"
      },
      {
        "name": "meins",
        "description": "Base unit of measure",
        "datatype": "VARCHAR(3)",
        "nullable": False,
        "business_definition": "Unit of measure for the item quantity - PCE (pieces), KG (kilograms), M (meters). Drives UoM consistency in reporting.",
        "sample_value": "PCE"
      },
      {
        "name": "netpr",
        "description": "Net price",
        "datatype": "DECIMAL(18,2)",
        "nullable": True,
        "business_definition": "Unit price per item in the PO currency, used for line-level spend calculation and price variance analysis.",
        "sample_value": "2500000.00"
      },
      {
        "name": "peinh",
        "description": "Price unit",
        "datatype": "INTEGER",
        "nullable": True,
        "business_definition": "Number of units to which the net price applies. Defaults to 1; 10 means price is per 10 pieces.",
        "sample_value": 1
      },
      {
        "name": "werks",
        "description": "Plant",
        "datatype": "VARCHAR(4)",
        "nullable": True,
        "business_definition": "Plant receiving the material. Links to VinFast manufacturing plants and regional distribution centers.",
        "sample_value": "HP01"
      },
      {
        "name": "lgort",
        "description": "Storage location",
        "datatype": "VARCHAR(4)",
        "nullable": True,
        "business_definition": "Specific storage location within the plant where the material will be stocked after goods receipt.",
        "sample_value": "RAW"
      },
      {
        "name": "wempf",
        "description": "Goods recipient",
        "datatype": "VARCHAR(12)",
        "nullable": True,
        "business_definition": "Name or code of the person or department expecting delivery. Used by warehouse for put-away routing.",
        "sample_value": "ASSY-LINE-3"
      }
    ]
  },
  {
    "name": "sap_ekbe",
    "description": "Purchase Order History - goods receipt and invoice receipt records",
    "domain": "supply_chain",
    "platform": "sap",
    "tags": [
      "SupplyChain",
      "SAP",
      "Transactional"
    ],
    "columns": [
      {
        "name": "ebeln",
        "description": "Purchasing document number",
        "datatype": "VARCHAR(10)",
        "nullable": False,
        "business_definition": "PO number identifying the purchasing document to which this history record belongs. Links procurement execution back to the original order.",
        "sample_value": "PO-4500012345"
      },
      {
        "name": "ebelp",
        "description": "Item number of purchasing document",
        "datatype": "INTEGER",
        "nullable": False,
        "business_definition": "Line item within the PO. Combined with movement type and document year to form a unique history record key.",
        "sample_value": 10
      },
      {
        "name": "vgabe",
        "description": "Subsequent document category",
        "datatype": "VARCHAR(1)",
        "nullable": False,
        "business_definition": "Indicates what triggered the history record: 1=goods receipt, 2=invoice receipt, 3=return delivery. Critical for reconciling ordered vs received vs invoiced quantities.",
        "sample_value": "1"
      },
      {
        "name": "bwart",
        "description": "Movement type",
        "datatype": "VARCHAR(3)",
        "nullable": False,
        "business_definition": "SAP goods movement type code. 101=goods receipt for PO, 102=goods receipt reversal. Drives inventory valuation updates.",
        "sample_value": "101"
      },
      {
        "name": "menge",
        "description": "Quantity in unit of entry",
        "datatype": "DECIMAL(13,3)",
        "nullable": True,
        "business_definition": "Quantity of goods received or invoice verified for this transaction. Used to track delivery completeness against PO quantity.",
        "sample_value": "500.000"
      },
      {
        "name": "dmbtr",
        "description": "Amount in local currency",
        "datatype": "DECIMAL(18,2)",
        "nullable": True,
        "business_definition": "Transaction value in VND (company code currency). Used for accrual accounting and GR/IR clearing analysis.",
        "sample_value": "1250000000.00"
      },
      {
        "name": "budat",
        "description": "Posting date",
        "datatype": "DATE",
        "nullable": True,
        "business_definition": "Financial posting date of the goods receipt or invoice. Governs the period in which costs are recognized in financial statements.",
        "sample_value": "2025-12-22"
      },
      {
        "name": "cpudt",
        "description": "Date of entry",
        "datatype": "DATE",
        "nullable": True,
        "business_definition": "System date when the transaction record was created. Used for operational SLAs on goods receipt processing time.",
        "sample_value": "2025-12-22"
      },
      {
        "name": "lfbnr",
        "description": "Document number of goods receipt",
        "datatype": "VARCHAR(10)",
        "nullable": True,
        "business_definition": "Material document number generated by the goods receipt transaction. Enables cross-reference to inventory accounting entries.",
        "sample_value": "GR-50006789"
      },
      {
        "name": "shkzg",
        "description": "Debit/credit indicator",
        "datatype": "VARCHAR(1)",
        "nullable": True,
        "business_definition": "S=debit (increase inventory), H=credit (decrease inventory). Determines the direction of inventory quantity and value change.",
        "sample_value": "S"
      }
    ]
  },
  {
    "name": "sap_eord",
    "description": "Source List - approved procurement sources per material",
    "domain": "supply_chain",
    "platform": "sap",
    "tags": [
      "SupplyChain",
      "SAP",
      "MasterData"
    ],
    "columns": [
      {
        "name": "matnr",
        "description": "Material number",
        "datatype": "VARCHAR(18)",
        "nullable": False,
        "business_definition": "Material master key identifying the part or raw material for which sourcing is defined. Each material can have multiple source list entries with validity periods.",
        "sample_value": "VF8-BATT-MOD-001"
      },
      {
        "name": "werks",
        "description": "Plant",
        "datatype": "VARCHAR(4)",
        "nullable": False,
        "business_definition": "Plant for which the source is valid. VinFast configures source lists per plant to account for regional supplier variations.",
        "sample_value": "HP01"
      },
      {
        "name": "lifnr",
        "description": "Vendor account number",
        "datatype": "VARCHAR(10)",
        "nullable": False,
        "business_definition": "Approved supplier for this material-plant combination. Only suppliers on the source list are eligible for PO creation during procurement.",
        "sample_value": "V000003456"
      },
      {
        "name": "ekorg",
        "description": "Purchasing organization",
        "datatype": "VARCHAR(4)",
        "nullable": False,
        "business_definition": "Purchasing organization responsible for sourcing. Aligns with VinFast centralized vs decentralized procurement strategy.",
        "sample_value": "VF01"
      },
      {
        "name": "datbi",
        "description": "Validity end date",
        "datatype": "DATE",
        "nullable": True,
        "business_definition": "Last date on which the source is valid. After expiry, the supplier cannot be used for new POs without source list renewal.",
        "sample_value": "2026-12-31"
      },
      {
        "name": "datab",
        "description": "Validity start date",
        "datatype": "DATE",
        "nullable": True,
        "business_definition": "First date on which the source becomes active. Used for phase-in planning of new suppliers or renegotiated contracts.",
        "sample_value": "2025-01-01"
      },
      {
        "name": "flief",
        "description": "Fixed supplier indicator",
        "datatype": "BOOLEAN",
        "nullable": True,
        "business_definition": "When set, only this specific supplier can be used for the material-plant combination, overriding normal sourcing logic.",
        "sample_value": True
      },
      {
        "name": "loekz",
        "description": "Deletion indicator",
        "datatype": "VARCHAR(1)",
        "nullable": True,
        "business_definition": "Flag marking the source list entry as logically deleted but retained for audit history. X=deleted, blank=active.",
        "sample_value": ""
      },
      {
        "name": "ebelf",
        "description": "Purchase requisition quota",
        "datatype": "INTEGER",
        "nullable": True,
        "business_definition": "Percentage quota for automated sourcing distribution. Used when splitting procurement across multiple suppliers for the same material.",
        "sample_value": 60
      }
    ]
  },
  {
    "name": "sap_a018",
    "description": "Info Record - purchasing info record for material-supplier pricing",
    "domain": "supply_chain",
    "platform": "sap",
    "tags": [
      "SupplyChain",
      "SAP",
      "MasterData"
    ],
    "columns": [
      {
        "name": "matnr",
        "description": "Material number",
        "datatype": "VARCHAR(18)",
        "nullable": False,
        "business_definition": "Material master key for which pricing conditions are negotiated. The material-supplier combination drives unit cost in PO creation.",
        "sample_value": "VF8-BATT-MOD-001"
      },
      {
        "name": "lifnr",
        "description": "Vendor account number",
        "datatype": "VARCHAR(10)",
        "nullable": False,
        "business_definition": "Supplier to which the pricing condition applies. Multiple info records can exist per material-supplier pair with different validity periods.",
        "sample_value": "V000003456"
      },
      {
        "name": "ekorg",
        "description": "Purchasing organization",
        "datatype": "VARCHAR(4)",
        "nullable": False,
        "business_definition": "Purchasing organization level at which the condition is valid. Enables org-specific negotiated pricing.",
        "sample_value": "VF01"
      },
      {
        "name": "datbi",
        "description": "Validity end date",
        "datatype": "DATE",
        "nullable": True,
        "business_definition": "End date of price validity. Renewal negotiations must be completed before expiry to avoid procurement disruptions.",
        "sample_value": "2026-06-30"
      },
      {
        "name": "kbetr",
        "description": "Condition amount or percentage",
        "datatype": "DECIMAL(18,2)",
        "nullable": True,
        "business_definition": "Unit price or percentage for the condition type. For absolute pricing this is the per-unit cost in the condition currency.",
        "sample_value": "2500000.00"
      },
      {
        "name": "kpein",
        "description": "Condition pricing unit",
        "datatype": "INTEGER",
        "nullable": True,
        "business_definition": "Number of units the condition amount applies to. A value of 100 means the price is per 100 pieces.",
        "sample_value": 1
      },
      {
        "name": "konwa",
        "description": "Condition currency",
        "datatype": "VARCHAR(5)",
        "nullable": True,
        "business_definition": "Currency in which the condition amount is denominated. Critical for multi-currency sourcing from overseas suppliers.",
        "sample_value": "VND"
      },
      {
        "name": "verei",
        "description": "Indicator for condition release status",
        "datatype": "VARCHAR(1)",
        "nullable": True,
        "business_definition": "Release status of the info record: blank=unreleased, 1=released, 2=blocked. Controls whether the record can be used in PO creation.",
        "sample_value": "1"
      },
      {
        "name": "loekz",
        "description": "Deletion flag",
        "datatype": "VARCHAR(1)",
        "nullable": True,
        "business_definition": "Marked X when the info record is obsolete but retained for historical price traceability.",
        "sample_value": ""
      }
    ]
  },
  {
    "name": "stg_supplier_master",
    "description": "Supplier Master Staging - raw supplier onboarding and master data",
    "domain": "supply_chain",
    "platform": "staging",
    "tags": [
      "SupplyChain",
      "MasterData",
      "Batch",
      "Bronze"
    ],
    "columns": [
      {
        "name": "supplier_id",
        "description": "Unique supplier identifier",
        "datatype": "VARCHAR(10)",
        "nullable": False,
        "business_definition": "Primary key for the supplier master table. Maps to SAP LIFNR. Assigned during supplier onboarding and used across all procurement records.",
        "sample_value": "V000003456"
      },
      {
        "name": "supplier_name",
        "description": "Legal name of the supplier",
        "datatype": "VARCHAR(200)",
        "nullable": False,
        "business_definition": "Registered legal name of the vendor entity. Used for procurement contracts, payment processing, and regulatory reporting.",
        "sample_value": "Cong ty TNHH Linh kien o to Hai Phong"
      },
      {
        "name": "supplier_type",
        "description": "Type classification of supplier",
        "datatype": "VARCHAR(50)",
        "nullable": True,
        "business_definition": "Categorization of the supplier: domestic, international, OEM, Tier-1, raw material, or logistics provider. Drives procurement strategy.",
        "sample_value": "Tier-1"
      },
      {
        "name": "tax_id",
        "description": "Supplier tax identification number",
        "datatype": "VARCHAR(20)",
        "nullable": True,
        "business_definition": "Vietnamese tax code or foreign tax ID for the supplier. Required for invoice validation and tax reporting in VND transactions.",
        "sample_value": "0200956789"
      },
      {
        "name": "country",
        "description": "Country of the supplier",
        "datatype": "VARCHAR(3)",
        "nullable": False,
        "business_definition": "ISO Alpha-3 country code of the supplier registered address. Used for cross-border trade compliance and lead time estimation.",
        "sample_value": "VNM"
      },
      {
        "name": "payment_terms",
        "description": "Standard payment terms",
        "datatype": "VARCHAR(30)",
        "nullable": True,
        "business_definition": "Negotiated payment terms for the supplier, such as Net 30, Net 60, or advance payment. Critical for cash flow forecasting.",
        "sample_value": "Net 60"
      },
      {
        "name": "currency",
        "description": "Transaction currency",
        "datatype": "VARCHAR(3)",
        "nullable": True,
        "business_definition": "Default currency for transactions with this supplier. Impacts foreign exchange risk assessment in procurement spend analytics.",
        "sample_value": "VND"
      },
      {
        "name": "status",
        "description": "Supplier status",
        "datatype": "VARCHAR(20)",
        "nullable": False,
        "business_definition": "Current status: Active, Onboarding, Suspended, Blacklisted, or Inactive. Controls whether the supplier can receive purchase orders.",
        "sample_value": "Active"
      },
      {
        "name": "certification_level",
        "description": "Quality certification level",
        "datatype": "VARCHAR(30)",
        "nullable": True,
        "business_definition": "ISO or VinFast-specific quality certification: ISO 9001, IATF 16949, or VinFast Q-Star. Used in supplier qualification scoring.",
        "sample_value": "IATF 16949"
      },
      {
        "name": "created_date",
        "description": "Record creation timestamp",
        "datatype": "TIMESTAMP",
        "nullable": True,
        "business_definition": "System timestamp when the supplier record was first created in the staging layer. Used for onboarding cycle time analysis.",
        "sample_value": "2024-03-10 08:30:00"
      }
    ]
  },
  {
    "name": "stg_contract_terms",
    "description": "Contract Terms Staging - negotiated contract terms from procurement agreements",
    "domain": "supply_chain",
    "platform": "staging",
    "tags": [
      "SupplyChain",
      "Batch",
      "Silver"
    ],
    "columns": [
      {
        "name": "contract_id",
        "description": "Unique contract identifier",
        "datatype": "VARCHAR(20)",
        "nullable": False,
        "business_definition": "Primary key for the procurement contract. Links to SAP contract documents and external contract management systems.",
        "sample_value": "CTR-VF8-BATT-2025-001"
      },
      {
        "name": "supplier_id",
        "description": "Supplier identifier",
        "datatype": "VARCHAR(10)",
        "nullable": False,
        "business_definition": "Foreign key to the supplier master identifying the contracted party. Enables supplier-centric contract portfolio analysis.",
        "sample_value": "V000003456"
      },
      {
        "name": "effective_date",
        "description": "Contract effective start date",
        "datatype": "DATE",
        "nullable": False,
        "business_definition": "Date from which the contract terms are legally binding. Must be before or equal to the first PO referencing this contract.",
        "sample_value": "2025-01-01"
      },
      {
        "name": "expiration_date",
        "description": "Contract expiration date",
        "datatype": "DATE",
        "nullable": False,
        "business_definition": "Date on which the contract term ends. Used for contract renewal alerts and continuity planning for critical VinFast components.",
        "sample_value": "2026-12-31"
      },
      {
        "name": "contract_value",
        "description": "Total contracted value",
        "datatype": "DECIMAL(18,2)",
        "nullable": True,
        "business_definition": "Total monetary value of the contract in the agreed currency. Used for commitment tracking and financial planning.",
        "sample_value": "75000000000.00"
      },
      {
        "name": "currency",
        "description": "Contract currency",
        "datatype": "VARCHAR(3)",
        "nullable": False,
        "business_definition": "Currency in which contract values are denominated. Multi-currency contracts require FX rate tracking for accurate VND reporting.",
        "sample_value": "VND"
      },
      {
        "name": "price_escalation_clause",
        "description": "Price adjustment clause",
        "datatype": "TEXT",
        "nullable": True,
        "business_definition": "Description of conditions under which pricing can be renegotiated, including raw material index linking and inflation adjustments.",
        "sample_value": "Annual adjustment based on CPI index plus max 5% for raw material fluctuation."
      },
      {
        "name": "payment_terms",
        "description": "Contract payment terms",
        "datatype": "VARCHAR(100)",
        "nullable": True,
        "business_definition": "Detailed payment milestones and terms, including advance payment percentage, milestone triggers, and retention clauses.",
        "sample_value": "30% advance, 40% on delivery, 30% within 60 days after inspection"
      },
      {
        "name": "renewal_auto",
        "description": "Auto-renewal indicator",
        "datatype": "BOOLEAN",
        "nullable": True,
        "business_definition": "Flag indicating whether the contract automatically renews upon expiration unless notice is given by either party.",
        "sample_value": True
      },
      {
        "name": "contract_category",
        "description": "Category of contract",
        "datatype": "VARCHAR(50)",
        "nullable": True,
        "business_definition": "Classification: Framework Agreement, One-Time Purchase, Service Contract, Lease, or Licensing. Drives different procurement processes.",
        "sample_value": "Framework Agreement"
      }
    ]
  },
  {
    "name": "stg_po_acknowledgment",
    "description": "PO Acknowledgment Staging - supplier confirmations and acknowledgments",
    "domain": "supply_chain",
    "platform": "staging",
    "tags": [
      "SupplyChain",
      "Batch",
      "Bronze"
    ],
    "columns": [
      {
        "name": "po_number",
        "description": "Purchase order number",
        "datatype": "VARCHAR(10)",
        "nullable": False,
        "business_definition": "PO number being acknowledged by the supplier. Links the acknowledgment back to the original purchasing document.",
        "sample_value": "PO-4500012345"
      },
      {
        "name": "supplier_id",
        "description": "Supplier identifier",
        "datatype": "VARCHAR(10)",
        "nullable": False,
        "business_definition": "Supplier providing the acknowledgment. Used to verify that the acknowledging party matches the PO vendor.",
        "sample_value": "V000003456"
      },
      {
        "name": "acknowledgment_date",
        "description": "Date of acknowledgment",
        "datatype": "DATE",
        "nullable": True,
        "business_definition": "Date when the supplier confirmed receipt and acceptance of the PO. A key metric in the procure-to-pay cycle time.",
        "sample_value": "2025-11-16"
      },
      {
        "name": "acknowledgment_status",
        "description": "Status of acknowledgment",
        "datatype": "VARCHAR(30)",
        "nullable": False,
        "business_definition": "Acknowledgment outcome: Accepted, Accepted with Changes, Rejected, or No Response. Drives follow-up actions by procurement team.",
        "sample_value": "Accepted"
      },
      {
        "name": "confirmed_delivery_date",
        "description": "Supplier-confirmed delivery date",
        "datatype": "DATE",
        "nullable": True,
        "business_definition": "Date the supplier commits to deliver. May differ from the requested date in the PO. Used for production scheduling adjustments.",
        "sample_value": "2025-12-22"
      },
      {
        "name": "confirmed_quantity",
        "description": "Supplier-confirmed quantity",
        "datatype": "DECIMAL(13,3)",
        "nullable": True,
        "business_definition": "Quantity the supplier confirms they can deliver. Partial confirmations trigger procurement team to source remaining quantities.",
        "sample_value": "500.000"
      },
      {
        "name": "rejection_reason",
        "description": "Reason for rejection if applicable",
        "datatype": "TEXT",
        "nullable": True,
        "business_definition": "Free-text reason if the supplier rejects the PO. Common reasons: capacity constraints, material shortages, or pricing disputes.",
        "sample_value": ""
      },
      {
        "name": "acknowledgment_channel",
        "description": "Channel used for acknowledgment",
        "datatype": "VARCHAR(20)",
        "nullable": True,
        "business_definition": "Method by which the acknowledgment was received: SAP Ariba Network, EDI, Email, Portal Upload. Tracks digital adoption.",
        "sample_value": "EDI"
      }
    ]
  },
  {
    "name": "fact_procurement_spend",
    "description": "Procurement Spend Fact - detailed procurement expenditure records",
    "domain": "supply_chain",
    "platform": "fact",
    "tags": [
      "SupplyChain",
      "Analytics",
      "Gold"
    ],
    "columns": [
      {
        "name": "spend_id",
        "description": "Unique spend record identifier",
        "datatype": "VARCHAR(30)",
        "nullable": False,
        "business_definition": "Surrogate key uniquely identifying each spend transaction line. Generated from SAP document number, item, and fiscal year combination.",
        "sample_value": "SPEND-2025-4500012345-10"
      },
      {
        "name": "po_number",
        "description": "Purchase order number",
        "datatype": "VARCHAR(10)",
        "nullable": False,
        "business_definition": "PO reference for the spend transaction. Enables drill-down from aggregated spend to transactional source documents.",
        "sample_value": "PO-4500012345"
      },
      {
        "name": "supplier_key",
        "description": "Supplier dimension foreign key",
        "datatype": "VARCHAR(10)",
        "nullable": False,
        "business_definition": "Foreign key to dim_supplier. Enables supplier-centric spend analysis across procurement categories and time periods.",
        "sample_value": "V000003456"
      },
      {
        "name": "purchasing_group_key",
        "description": "Purchasing group dimension key",
        "datatype": "VARCHAR(3)",
        "nullable": True,
        "business_definition": "Foreign key to dim_purchasing_group identifying the buyer group responsible for the transaction.",
        "sample_value": "P01"
      },
      {
        "name": "category_key",
        "description": "Procurement category dimension key",
        "datatype": "VARCHAR(10)",
        "nullable": True,
        "business_definition": "Foreign key to dim_procurement_category for hierarchical spend categorization and budget tracking.",
        "sample_value": "CAT-BATT-001"
      },
      {
        "name": "spend_amount_vnd",
        "description": "Spend amount in VND",
        "datatype": "DECIMAL(18,2)",
        "nullable": False,
        "business_definition": "Net spend amount converted to Vietnamese Dong using the transaction date exchange rate. Single-currency metric for consolidated reporting.",
        "sample_value": "1250000000.00"
      },
      {
        "name": "quantity",
        "description": "Procured quantity",
        "datatype": "DECIMAL(13,3)",
        "nullable": True,
        "business_definition": "Quantity of materials or services procured in this transaction. Used with spend amount to calculate unit cost.",
        "sample_value": "500.000"
      },
      {
        "name": "unit_price_vnd",
        "description": "Unit price in VND",
        "datatype": "DECIMAL(18,2)",
        "nullable": True,
        "business_definition": "Calculated per-unit cost in VND. Monitored for price variance against info record and contract prices.",
        "sample_value": "2500000.00"
      },
      {
        "name": "posting_date",
        "description": "Financial posting date",
        "datatype": "DATE",
        "nullable": False,
        "business_definition": "Date the transaction was posted to the general ledger. Governs the fiscal period for spend accrual and reporting.",
        "sample_value": "2025-12-22"
      },
      {
        "name": "fiscal_year",
        "description": "Fiscal year of transaction",
        "datatype": "INTEGER",
        "nullable": False,
        "business_definition": "Fiscal year extracted from posting date for partitioning and year-over-year spend comparison.",
        "sample_value": 2025
      },
      {
        "name": "plant",
        "description": "Receiving plant code",
        "datatype": "VARCHAR(4)",
        "nullable": True,
        "business_definition": "Plant where the procured materials were delivered. Enables plant-level spend allocation and budget variance analysis.",
        "sample_value": "HP01"
      },
      {
        "name": "is_capitalized",
        "description": "Capital vs expense indicator",
        "datatype": "BOOLEAN",
        "nullable": True,
        "business_definition": "Flag distinguishing capital expenditure (Capex) from operational expenditure (Opex). Drives different accounting treatment and reporting.",
        "sample_value": False
      }
    ]
  },
  {
    "name": "fact_supplier_performance",
    "description": "Supplier Performance Fact - quantitative supplier evaluation metrics",
    "domain": "supply_chain",
    "platform": "fact",
    "tags": [
      "SupplyChain",
      "Analytics",
      "Gold"
    ],
    "columns": [
      {
        "name": "performance_id",
        "description": "Unique performance record identifier",
        "datatype": "VARCHAR(30)",
        "nullable": False,
        "business_definition": "Surrogate key for each supplier evaluation period. Combines supplier key, evaluation period, and metric type.",
        "sample_value": "PERF-V000003456-2025M11"
      },
      {
        "name": "supplier_key",
        "description": "Supplier dimension foreign key",
        "datatype": "VARCHAR(10)",
        "nullable": False,
        "business_definition": "Foreign key to dim_supplier. Central identifier for aggregating performance scores across all evaluation dimensions.",
        "sample_value": "V000003456"
      },
      {
        "name": "evaluation_period",
        "description": "Evaluation period (monthly)",
        "datatype": "VARCHAR(7)",
        "nullable": False,
        "business_definition": "Calendar period in YYYY-MM format for which the performance is measured. Supports time-series trend analysis.",
        "sample_value": "2025-11"
      },
      {
        "name": "ontime_delivery_rate",
        "description": "Percentage of on-time deliveries",
        "datatype": "DECIMAL(5,2)",
        "nullable": True,
        "business_definition": "Percentage of line items delivered on or before the confirmed delivery date. VinFast target is 98% or higher for Tier-1 suppliers.",
        "sample_value": "97.50"
      },
      {
        "name": "quality_defect_ppm",
        "description": "Defect rate in parts per million",
        "datatype": "INTEGER",
        "nullable": True,
        "business_definition": "Number of defective parts per million received. Target below 1000 PPM for production-critical components like battery modules.",
        "sample_value": 850
      },
      {
        "name": "reject_rate",
        "description": "Percentage of rejected deliveries",
        "datatype": "DECIMAL(5,2)",
        "nullable": True,
        "business_definition": "Percentage of total deliveries that were rejected during incoming quality inspection. Drives supplier corrective action requests.",
        "sample_value": "0.85"
      },
      {
        "name": "lead_time_days",
        "description": "Average lead time in days",
        "datatype": "DECIMAL(6,2)",
        "nullable": True,
        "business_definition": "Average number of days from PO creation to goods receipt for this supplier. Used for inventory safety stock calculations.",
        "sample_value": "14.50"
      },
      {
        "name": "price_competitiveness_score",
        "description": "Price competitiveness rating",
        "datatype": "INTEGER",
        "nullable": True,
        "business_definition": "Score 1-5 comparing supplier pricing against market benchmarks and other suppliers for similar materials.",
        "sample_value": 4
      },
      {
        "name": "overall_score",
        "description": "Composite supplier score",
        "datatype": "DECIMAL(5,2)",
        "nullable": True,
        "business_definition": "Weighted composite score combining quality (40%), delivery (30%), cost (20%), and compliance (10%). Used for supplier tiering decisions.",
        "sample_value": "86.50"
      }
    ]
  },
  {
    "name": "fact_po_fulfillment",
    "description": "PO Fulfillment Fact - purchase order completion and fulfillment tracking",
    "domain": "supply_chain",
    "platform": "fact",
    "tags": [
      "SupplyChain",
      "Analytics",
      "Gold"
    ],
    "columns": [
      {
        "name": "fulfillment_id",
        "description": "Unique fulfillment record identifier",
        "datatype": "VARCHAR(30)",
        "nullable": False,
        "business_definition": "Surrogate key for each PO line item fulfillment record. Links procurement targets to actual execution outcomes.",
        "sample_value": "FULFILL-PO-4500012345-10"
      },
      {
        "name": "po_number",
        "description": "Purchase order number",
        "datatype": "VARCHAR(10)",
        "nullable": False,
        "business_definition": "PO number for the fulfillment record. Used to join back to PO header and item master data for contextual analysis.",
        "sample_value": "PO-4500012345"
      },
      {
        "name": "po_item",
        "description": "PO line item number",
        "datatype": "INTEGER",
        "nullable": False,
        "business_definition": "Line item within the PO. Combined with po_number identifies the specific material or service in the fulfillment evaluation.",
        "sample_value": 10
      },
      {
        "name": "ordered_quantity",
        "description": "Quantity ordered",
        "datatype": "DECIMAL(13,3)",
        "nullable": False,
        "business_definition": "Original quantity ordered on the PO line item. Baseline against which received and invoiced quantities are compared.",
        "sample_value": "500.000"
      },
      {
        "name": "received_quantity",
        "description": "Total quantity received",
        "datatype": "DECIMAL(13,3)",
        "nullable": True,
        "business_definition": "Cumulative quantity received against this PO line through all goods receipt transactions. Used for over/under-delivery analysis.",
        "sample_value": "500.000"
      },
      {
        "name": "invoiced_quantity",
        "description": "Total quantity invoiced",
        "datatype": "DECIMAL(13,3)",
        "nullable": True,
        "business_definition": "Cumulative quantity for which invoices have been received. Compared against received quantity to detect billing discrepancies.",
        "sample_value": "500.000"
      },
      {
        "name": "fulfillment_percentage",
        "description": "Percentage of PO fulfilled",
        "datatype": "DECIMAL(5,2)",
        "nullable": True,
        "business_definition": "Received quantity divided by ordered quantity expressed as a percentage. Values over 100% indicate over-delivery.",
        "sample_value": "100.00"
      },
      {
        "name": "first_goods_receipt_date",
        "description": "Date of first goods receipt",
        "datatype": "DATE",
        "nullable": True,
        "business_definition": "Date on which the first partial delivery was received. Used to calculate initial response time from the supplier.",
        "sample_value": "2025-12-22"
      },
      {
        "name": "last_goods_receipt_date",
        "description": "Date of final goods receipt",
        "datatype": "DATE",
        "nullable": True,
        "business_definition": "Date when the last delivery completing the PO was received. Used for PO closure cycle time measurement.",
        "sample_value": "2025-12-28"
      },
      {
        "name": "fulfillment_status",
        "description": "Current fulfillment status",
        "datatype": "VARCHAR(20)",
        "nullable": True,
        "business_definition": "Overall PO fulfillment status: Open, Partially Received, Fully Received, Over-Delivered, or Closed.",
        "sample_value": "Fully Received"
      },
      {
        "name": "days_late",
        "description": "Days late vs confirmed delivery",
        "datatype": "INTEGER",
        "nullable": True,
        "business_definition": "Number of days the final delivery was received after the confirmed delivery date. Negative values indicate early delivery.",
        "sample_value": 0
      }
    ]
  },
  {
    "name": "dim_scm_supplier",
    "description": "Supplier Dimension - supplier master attributes and classification",
    "domain": "supply_chain",
    "platform": "dimension",
    "tags": [
      "SupplyChain",
      "MasterData",
      "Gold"
    ],
    "columns": [
      {
        "name": "supplier_key",
        "description": "Supplier surrogate key",
        "datatype": "VARCHAR(10)",
        "nullable": False,
        "business_definition": "Surrogate primary key for the supplier dimension. Maps 1:1 to SAP LIFNR values used across the data warehouse.",
        "sample_value": "V000003456"
      },
      {
        "name": "supplier_name",
        "description": "Full supplier legal name",
        "datatype": "VARCHAR(200)",
        "nullable": False,
        "business_definition": "Registered legal entity name of the supplier as per business registration. Used in contracts and official procurement documents.",
        "sample_value": "Cong ty TNHH Linh kien o to Hai Phong"
      },
      {
        "name": "supplier_short_name",
        "description": "Short name for reporting",
        "datatype": "VARCHAR(50)",
        "nullable": True,
        "business_definition": "Abbreviated supplier name used in dashboards and operational reports where space is limited.",
        "sample_value": "Hai Phong Auto Parts"
      },
      {
        "name": "supplier_tier",
        "description": "Supplier tier classification",
        "datatype": "VARCHAR(20)",
        "nullable": True,
        "business_definition": "Tier classification: Tier-1 (direct parts), Tier-2 (subcomponents), Tier-3 (raw materials). Defines supply chain complexity.",
        "sample_value": "Tier-1"
      },
      {
        "name": "supplier_region",
        "description": "Geographic region",
        "datatype": "VARCHAR(50)",
        "nullable": True,
        "business_definition": "Broad geographic region: Northern Vietnam, Southern Vietnam, ASEAN, Northeast Asia, Europe, or North America.",
        "sample_value": "Northern Vietnam"
      },
      {
        "name": "is_critical",
        "description": "Critical supplier flag",
        "datatype": "BOOLEAN",
        "nullable": False,
        "business_definition": "Flags suppliers providing sole-source, single-source, or long-lead-time components. Critical suppliers receive enhanced monitoring.",
        "sample_value": True
      },
      {
        "name": "supplier_status",
        "description": "Current supplier status",
        "datatype": "VARCHAR(20)",
        "nullable": False,
        "business_definition": "Lifecycle status: Active, On Hold, Under Review, Inactive, or Blacklisted. Controls transaction permissions.",
        "sample_value": "Active"
      },
      {
        "name": "qualification_date",
        "description": "Date of qualification",
        "datatype": "DATE",
        "nullable": True,
        "business_definition": "Date the supplier completed the VinFast supplier qualification process. Used for tenure analysis.",
        "sample_value": "2023-06-15"
      },
      {
        "name": "diversity_classification",
        "description": "Supplier diversity category",
        "datatype": "VARCHAR(50)",
        "nullable": True,
        "business_definition": "Diversity classification: Small Business, Women-Owned, Local Enterprise. Used for ESG and sustainability reporting.",
        "sample_value": "Local Enterprise"
      }
    ]
  },
  {
    "name": "dim_purchasing_group",
    "description": "Purchasing Group Dimension - buyer group organizational data",
    "domain": "supply_chain",
    "platform": "dimension",
    "tags": [
      "SupplyChain",
      "MasterData",
      "Gold"
    ],
    "columns": [
      {
        "name": "purchasing_group_key",
        "description": "Purchasing group code",
        "datatype": "VARCHAR(3)",
        "nullable": False,
        "business_definition": "SAP purchasing group code representing a buyer or buying team responsible for procurement activities.",
        "sample_value": "P01"
      },
      {
        "name": "group_name",
        "description": "Descriptive group name",
        "datatype": "VARCHAR(100)",
        "nullable": False,
        "business_definition": "Name of the purchasing group indicating its area of responsibility, such as Powertrain, Body & Chassis, or Electronics.",
        "sample_value": "Battery & Powertrain"
      },
      {
        "name": "group_leader",
        "description": "Name of group leader",
        "datatype": "VARCHAR(100)",
        "nullable": True,
        "business_definition": "Full name of the purchasing group manager. Used for organizational reporting and escalation workflows.",
        "sample_value": "Nguyen Van An"
      },
      {
        "name": "category_responsibility",
        "description": "Procurement categories managed",
        "datatype": "VARCHAR(200)",
        "nullable": True,
        "business_definition": "Comma-separated list of procurement categories this group is responsible for. Drives workload allocation and expertise alignment.",
        "sample_value": "Battery Cells, Battery Modules, Electric Motors, Power Electronics"
      },
      {
        "name": "plant_responsibility",
        "description": "Plants supported by this group",
        "datatype": "VARCHAR(100)",
        "nullable": True,
        "business_definition": "List of VinFast plants this purchasing group serves. Enables plant-level procurement responsibility assignment.",
        "sample_value": "HP01, HP02"
      },
      {
        "name": "is_active",
        "description": "Group active status",
        "datatype": "BOOLEAN",
        "nullable": False,
        "business_definition": "Indicates whether the purchasing group is currently active and can create purchase orders.",
        "sample_value": True
      }
    ]
  },
  {
    "name": "dim_procurement_category",
    "description": "Procurement Category Dimension - hierarchical spend classification",
    "domain": "supply_chain",
    "platform": "dimension",
    "tags": [
      "SupplyChain",
      "MasterData",
      "Gold"
    ],
    "columns": [
      {
        "name": "category_key",
        "description": "Category unique key",
        "datatype": "VARCHAR(10)",
        "nullable": False,
        "business_definition": "Surrogate key for the procurement category. Used as foreign key in fact tables for dimensional spend analysis.",
        "sample_value": "CAT-BATT-001"
      },
      {
        "name": "category_name",
        "description": "Category display name",
        "datatype": "VARCHAR(100)",
        "nullable": False,
        "business_definition": "Human-readable name of the procurement category. Examples: Battery Cells, Steel Body Panels, Interior Trim, Logistics Services.",
        "sample_value": "Lithium-ion Battery Cells"
      },
      {
        "name": "category_level",
        "description": "Level in hierarchy",
        "datatype": "INTEGER",
        "nullable": False,
        "business_definition": "Depth level in the category tree: L1 (Direct Material), L2 (Powertrain), L3 (Battery), L4 (Cells). Enables roll-up aggregation.",
        "sample_value": 3
      },
      {
        "name": "parent_category_key",
        "description": "Parent category key",
        "datatype": "VARCHAR(10)",
        "nullable": True,
        "business_definition": "Foreign key to the parent category in the hierarchy. Enables hierarchical drill-down and roll-up in reporting.",
        "sample_value": "CAT-POW-001"
      },
      {
        "name": "is_direct_material",
        "description": "Direct vs indirect material flag",
        "datatype": "BOOLEAN",
        "nullable": False,
        "business_definition": "True for materials that go into the final vehicle (BOM components), False for MRO and indirect procurement.",
        "sample_value": True
      },
      {
        "name": "budget_owner",
        "description": "Budget owner department",
        "datatype": "VARCHAR(100)",
        "nullable": True,
        "business_definition": "Department or cost center responsible for the category budget. Used for spend accountability and approval routing.",
        "sample_value": "Engineering - Powertrain"
      },
      {
        "name": "strategic_importance",
        "description": "Strategic importance rating",
        "datatype": "VARCHAR(20)",
        "nullable": True,
        "business_definition": "Kraljic matrix classification: Strategic, Leverage, Bottleneck, or Routine. Drives procurement strategy for the category.",
        "sample_value": "Strategic"
      }
    ]
  },
  {
    "name": "agg_supplier_scorecard_monthly",
    "description": "Supplier Scorecard Monthly - aggregated monthly supplier scorecards",
    "domain": "supply_chain",
    "platform": "aggregate",
    "tags": [
      "SupplyChain",
      "Analytics",
      "Gold",
      "PowerBI"
    ],
    "columns": [
      {
        "name": "supplier_key",
        "description": "Supplier dimension key",
        "datatype": "VARCHAR(10)",
        "nullable": False,
        "business_definition": "Foreign key to dim_supplier identifying the scored supplier. Composite key with scorecard_month for unique identification.",
        "sample_value": "V000003456"
      },
      {
        "name": "scorecard_month",
        "description": "Scorecard period (month)",
        "datatype": "VARCHAR(7)",
        "nullable": False,
        "business_definition": "Calendar month in YYYY-MM format representing the evaluated period. Enables monthly performance trend analysis.",
        "sample_value": "2025-11"
      },
      {
        "name": "total_po_count",
        "description": "Number of POs placed",
        "datatype": "INTEGER",
        "nullable": True,
        "business_definition": "Total number of purchase orders placed with the supplier during the month. Indicates transaction volume and relationship intensity.",
        "sample_value": 24
      },
      {
        "name": "total_spend_vnd",
        "description": "Total spend amount in VND",
        "datatype": "DECIMAL(18,2)",
        "nullable": True,
        "business_definition": "Aggregated total spend with the supplier in VND for the month. Used for spend concentration analysis.",
        "sample_value": "28750000000.00"
      },
      {
        "name": "ontime_delivery_rate",
        "description": "On-time delivery percentage",
        "datatype": "DECIMAL(5,2)",
        "nullable": True,
        "business_definition": "Monthly aggregate of on-time delivery performance. Compared against the 98% target for supplier scorecard grading.",
        "sample_value": "97.50"
      },
      {
        "name": "quality_score",
        "description": "Quality performance score",
        "datatype": "DECIMAL(5,2)",
        "nullable": True,
        "business_definition": "Quality score calculated from defect PPM and reject rate. Scored 0-100 with deductions for quality incidents and SCARs issued.",
        "sample_value": "92.00"
      },
      {
        "name": "compliance_score",
        "description": "Compliance and documentation score",
        "datatype": "DECIMAL(5,2)",
        "nullable": True,
        "business_definition": "Score measuring adherence to contractual terms including document submission, certification validity, and regulatory compliance.",
        "sample_value": "95.00"
      },
      {
        "name": "overall_score",
        "description": "Weighted overall score",
        "datatype": "DECIMAL(5,2)",
        "nullable": True,
        "business_definition": "Composite score across quality, delivery, cost, and compliance weighted by category-specific importance factors.",
        "sample_value": "86.50"
      },
      {
        "name": "scorecard_rating",
        "description": "Rating classification",
        "datatype": "VARCHAR(20)",
        "nullable": True,
        "business_definition": "Rating derived from overall_score: Platinum (95+), Gold (85+), Silver (70+), Bronze (50+), or Under Review (<50).",
        "sample_value": "Gold"
      },
      {
        "name": "improvement_plan_active",
        "description": "Active improvement plan flag",
        "datatype": "BOOLEAN",
        "nullable": True,
        "business_definition": "Indicates whether a supplier corrective action plan is currently active due to below-threshold performance.",
        "sample_value": False
      }
    ]
  },
  {
    "name": "agg_spend_by_category",
    "description": "Spend by Category - aggregated procurement spend by category hierarchy",
    "domain": "supply_chain",
    "platform": "aggregate",
    "tags": [
      "SupplyChain",
      "Analytics",
      "Gold",
      "PowerBI"
    ],
    "columns": [
      {
        "name": "category_key",
        "description": "Procurement category key",
        "datatype": "VARCHAR(10)",
        "nullable": False,
        "business_definition": "Foreign key to dim_procurement_category. Enables hierarchical category spend analysis at any level of the category tree.",
        "sample_value": "CAT-BATT-001"
      },
      {
        "name": "fiscal_year",
        "description": "Fiscal year",
        "datatype": "INTEGER",
        "nullable": False,
        "business_definition": "Fiscal year of the aggregated spend. Aligns with VinFast fiscal calendar for annual budget comparison.",
        "sample_value": 2025
      },
      {
        "name": "fiscal_period",
        "description": "Fiscal period (month)",
        "datatype": "INTEGER",
        "nullable": False,
        "business_definition": "Fiscal period number (1-12) within the fiscal year. Used with fiscal_year for period-over-period spend analysis.",
        "sample_value": 11
      },
      {
        "name": "total_spend_vnd",
        "description": "Total spend in VND",
        "datatype": "DECIMAL(18,2)",
        "nullable": False,
        "business_definition": "Sum of all procurement spend in the category for the period, converted to VND. Primary metric for budget tracking.",
        "sample_value": "525000000000.00"
      },
      {
        "name": "budget_vnd",
        "description": "Allocated budget in VND",
        "datatype": "DECIMAL(18,2)",
        "nullable": True,
        "business_definition": "Approved procurement budget for the category and period. Used to calculate spend vs budget variance.",
        "sample_value": "550000000000.00"
      },
      {
        "name": "budget_utilization_pct",
        "description": "Budget utilization percentage",
        "datatype": "DECIMAL(5,2)",
        "nullable": True,
        "business_definition": "Percentage of budget consumed: total_spend / budget * 100. Flags categories approaching or exceeding budget limits.",
        "sample_value": "95.45"
      },
      {
        "name": "supplier_count",
        "description": "Number of active suppliers",
        "datatype": "INTEGER",
        "nullable": True,
        "business_definition": "Count of distinct suppliers with spend in this category during the period. Used for supply base consolidation analysis.",
        "sample_value": 8
      },
      {
        "name": "avg_unit_price_vnd",
        "description": "Average unit price in VND",
        "datatype": "DECIMAL(18,2)",
        "nullable": True,
        "business_definition": "Quantity-weighted average unit price across all items in the category. Monitored for inflation and cost reduction initiatives.",
        "sample_value": "2450000.00"
      },
      {
        "name": "spend_change_vs_prior_pct",
        "description": "Spend change vs prior period",
        "datatype": "DECIMAL(5,2)",
        "nullable": True,
        "business_definition": "Percentage change in spend compared to the same period in the prior year. Positive values indicate spend growth.",
        "sample_value": "12.30"
      }
    ]
  },
  {
    "name": "agg_contract_coverage",
    "description": "Contract Coverage - procurement spend covered by active contracts",
    "domain": "supply_chain",
    "platform": "aggregate",
    "tags": [
      "SupplyChain",
      "Analytics",
      "Gold",
      "PowerBI"
    ],
    "columns": [
      {
        "name": "category_key",
        "description": "Procurement category key",
        "datatype": "VARCHAR(10)",
        "nullable": False,
        "business_definition": "Foreign key to dim_procurement_category for contract coverage analysis by category hierarchy.",
        "sample_value": "CAT-BATT-001"
      },
      {
        "name": "fiscal_year",
        "description": "Fiscal year",
        "datatype": "INTEGER",
        "nullable": False,
        "business_definition": "Fiscal year for which contract coverage is measured. Enables year-over-year coverage improvement tracking.",
        "sample_value": 2025
      },
      {
        "name": "total_spend_vnd",
        "description": "Total category spend in VND",
        "datatype": "DECIMAL(18,2)",
        "nullable": False,
        "business_definition": "Total procurement spend in the category for the period. Denominator for coverage percentage calculation.",
        "sample_value": "525000000000.00"
      },
      {
        "name": "contracted_spend_vnd",
        "description": "Spend under active contracts",
        "datatype": "DECIMAL(18,2)",
        "nullable": False,
        "business_definition": "Portion of total spend that is covered by active, valid contracts with suppliers. Numerator for coverage rate.",
        "sample_value": "420000000000.00"
      },
      {
        "name": "non_contracted_spend_vnd",
        "description": "Spend without active contracts",
        "datatype": "DECIMAL(18,2)",
        "nullable": True,
        "business_definition": "Portion of spend not covered by active contracts. Represents maverick spend or gap in contract management.",
        "sample_value": "105000000000.00"
      },
      {
        "name": "coverage_percentage",
        "description": "Contract coverage percentage",
        "datatype": "DECIMAL(5,2)",
        "nullable": False,
        "business_definition": "Percentage of category spend under active contracts. VinFast target is 85%+ coverage for direct material categories.",
        "sample_value": "80.00"
      },
      {
        "name": "active_contract_count",
        "description": "Number of active contracts",
        "datatype": "INTEGER",
        "nullable": True,
        "business_definition": "Count of distinct active contracts covering the category. Indicates contract fragmentation or consolidation.",
        "sample_value": 12
      },
      {
        "name": "contract_expiring_next_quarter",
        "description": "Contracts expiring within 90 days",
        "datatype": "INTEGER",
        "nullable": True,
        "business_definition": "Number of contracts in the category set to expire within the next quarter. Triggers renewal planning workflow.",
        "sample_value": 2
      },
      {
        "name": "avg_contract_discount",
        "description": "Average discount vs list price",
        "datatype": "DECIMAL(5,2)",
        "nullable": True,
        "business_definition": "Average negotiated discount percentage achieved through contracts compared to standard list prices.",
        "sample_value": "8.50"
      }
    ]
  },
  {
    "name": "sap_ekkn",
    "description": "Purchasing Document Accounting - account assignment data for PO items",
    "domain": "supply_chain",
    "platform": "sap",
    "tags": [
      "SupplyChain",
      "SAP",
      "Transactional"
    ],
    "columns": [
      {
        "name": "ebeln",
        "description": "Purchasing document number",
        "datatype": "VARCHAR(10)",
        "nullable": False,
        "business_definition": "PO number for which accounting assignment is defined. Links procurement transactions to financial controlling objects.",
        "sample_value": "PO-4500012345"
      },
      {
        "name": "ebelp",
        "description": "Item number of purchasing document",
        "datatype": "INTEGER",
        "nullable": False,
        "business_definition": "Line item within the PO that carries the account assignment. One PO item can have multiple account assignments for partial charging.",
        "sample_value": 10
      },
      {
        "name": "zekkn",
        "description": "Sequential account assignment number",
        "datatype": "INTEGER",
        "nullable": False,
        "business_definition": "Sequential number for multiple account assignment records within a single PO item. Enables split costing to multiple cost centers.",
        "sample_value": 1
      },
      {
        "name": "kostl",
        "description": "Cost center",
        "datatype": "VARCHAR(10)",
        "nullable": True,
        "business_definition": "Cost center code receiving the cost. VinFast uses cost centers like ASSY-L3 for assembly line 3 or ENG-PT for powertrain engineering.",
        "sample_value": "ASSY-L3"
      },
      {
        "name": "sakto",
        "description": "G/L account number",
        "datatype": "VARCHAR(10)",
        "nullable": True,
        "business_definition": "General ledger account for posting the procurement cost. Determines balance sheet or P&L treatment of the expenditure.",
        "sample_value": "40000001"
      },
      {
        "name": "menge",
        "description": "Quantity assigned",
        "datatype": "DECIMAL(13,3)",
        "nullable": True,
        "business_definition": "Quantity of the PO item allocated to this account assignment. Sum across zekkn values equals the total item quantity.",
        "sample_value": "500.000"
      },
      {
        "name": "prctr",
        "description": "Profit center",
        "datatype": "VARCHAR(10)",
        "nullable": True,
        "business_definition": "Profit center responsible for the procurement cost. Aligns with VinFast vehicle model profit center structure.",
        "sample_value": "P-VF8"
      },
      {
        "name": "aufnr",
        "description": "Order number",
        "datatype": "VARCHAR(12)",
        "nullable": True,
        "business_definition": "Production order or internal order number for which materials are being procured. Links procurement to manufacturing orders.",
        "sample_value": "MFG-VF8-11234"
      }
    ]
  },
  {
    "name": "sap_t024",
    "description": "Purchasing Group - SAP purchasing group master data",
    "domain": "supply_chain",
    "platform": "sap",
    "tags": [
      "SupplyChain",
      "SAP",
      "MasterData"
    ],
    "columns": [
      {
        "name": "ekgrp",
        "description": "Purchasing group code",
        "datatype": "VARCHAR(3)",
        "nullable": False,
        "business_definition": "Alpha-numeric code identifying the purchasing group or individual buyer in SAP. Primary key for the purchasing group master.",
        "sample_value": "P01"
      },
      {
        "name": "eknam",
        "description": "Purchasing group name",
        "datatype": "VARCHAR(18)",
        "nullable": True,
        "business_definition": "Short name or description of the purchasing group indicating its area of procurement responsibility.",
        "sample_value": "BATT-POW"
      },
      {
        "name": "tel_number",
        "description": "Telephone number",
        "datatype": "VARCHAR(30)",
        "nullable": True,
        "business_definition": "Contact telephone number for the purchasing group or buyer. Used for supplier communication and escalation contact.",
        "sample_value": "+84-225-1234567"
      },
      {
        "name": "smtp_addr",
        "description": "Email address",
        "datatype": "VARCHAR(241)",
        "nullable": True,
        "business_definition": "Email address of the purchasing group mailbox or buyer. SAP workflow notifications are routed to this address for approvals.",
        "sample_value": "battery.procurement@vinfast.vn"
      },
      {
        "name": "ekorg",
        "description": "Purchasing organization",
        "datatype": "VARCHAR(4)",
        "nullable": True,
        "business_definition": "Purchasing organization associated with the group. Defines the organizational scope within which the group operates.",
        "sample_value": "VF01"
      },
      {
        "name": "adrnr",
        "description": "Address number",
        "datatype": "VARCHAR(10)",
        "nullable": True,
        "business_definition": "SAP address number for the purchasing group physical or postal address. Used for correspondence routing.",
        "sample_value": "ADDR-65432"
      }
    ]
  },
  {
    "name": "fact_invoice_receipt",
    "description": "Invoice Receipt Fact - supplier invoice verification records",
    "domain": "supply_chain",
    "platform": "fact",
    "tags": [
      "SupplyChain",
      "Analytics",
      "Gold"
    ],
    "columns": [
      {
        "name": "invoice_id",
        "description": "Unique invoice identifier",
        "datatype": "VARCHAR(20)",
        "nullable": False,
        "business_definition": "Surrogate key for the invoice receipt record. Generated from SAP invoice document number and fiscal year.",
        "sample_value": "INV-5100007890"
      },
      {
        "name": "po_number",
        "description": "Purchase order number",
        "datatype": "VARCHAR(10)",
        "nullable": False,
        "business_definition": "PO number referenced by the invoice. Used for three-way matching between PO, goods receipt, and invoice.",
        "sample_value": "PO-4500012345"
      },
      {
        "name": "supplier_key",
        "description": "Supplier dimension key",
        "datatype": "VARCHAR(10)",
        "nullable": False,
        "business_definition": "Foreign key to dim_supplier. Identifies the supplier that issued the invoice.",
        "sample_value": "V000003456"
      },
      {
        "name": "invoice_amount_vnd",
        "description": "Invoice amount in VND",
        "datatype": "DECIMAL(18,2)",
        "nullable": False,
        "business_definition": "Total invoice amount in Vietnamese Dong including tax. Compared against PO value to detect pricing discrepancies.",
        "sample_value": "1375000000.00"
      },
      {
        "name": "tax_amount_vnd",
        "description": "Tax amount in VND",
        "datatype": "DECIMAL(18,2)",
        "nullable": True,
        "business_definition": "VAT or other tax amount applied to the invoice. Vietnamese VAT for automotive components is typically 10%.",
        "sample_value": "125000000.00"
      },
      {
        "name": "invoice_date",
        "description": "Invoice issuance date",
        "datatype": "DATE",
        "nullable": False,
        "business_definition": "Date on which the supplier issued the invoice. Used for invoice aging analysis and payment term compliance tracking.",
        "sample_value": "2025-12-28"
      },
      {
        "name": "posting_date",
        "description": "Invoice posting date",
        "datatype": "DATE",
        "nullable": True,
        "business_definition": "Date the invoice was posted in SAP for accounting. The gap from invoice_date indicates processing cycle time.",
        "sample_value": "2025-12-30"
      },
      {
        "name": "due_date",
        "description": "Payment due date",
        "datatype": "DATE",
        "nullable": True,
        "business_definition": "Date by which payment must be made based on payment terms. Used for cash flow forecasting and late payment penalty avoidance.",
        "sample_value": "2026-02-28"
      },
      {
        "name": "matching_status",
        "description": "Three-way matching status",
        "datatype": "VARCHAR(20)",
        "nullable": True,
        "business_definition": "Status of the three-way match: Matched, Quantity Discrepancy, Price Discrepancy, or Blocked. Drives invoice release workflow.",
        "sample_value": "Matched"
      },
      {
        "name": "payment_status",
        "description": "Invoice payment status",
        "datatype": "VARCHAR(20)",
        "nullable": True,
        "business_definition": "Current payment status: Unpaid, Paid, Partially Paid, Overdue, or Cancelled. Used for accounts payable aging.",
        "sample_value": "Unpaid"
      }
    ]
  },
  {
    "name": "sap_vbak",
    "description": "Sales Document Header - header data for all sales orders",
    "domain": "sales",
    "platform": "sap",
    "tags": [
      "Sales",
      "SAP",
      "MasterData"
    ],
    "columns": [
      {
        "name": "vbeln",
        "description": "Sales document number",
        "datatype": "VARCHAR(10)",
        "nullable": False,
        "business_definition": "Unique SAP document number for the sales order. Primary key for the sales document header. All order items and partners reference this key.",
        "sample_value": "SO-9000012345"
      },
      {
        "name": "auart",
        "description": "Sales document type",
        "datatype": "VARCHAR(4)",
        "nullable": False,
        "business_definition": "SAP order type: OR=Standard Order, TA=Telephone Order, WE=Web Order, EV=Electric Vehicle Order. Determines pricing procedure and fulfillment flow.",
        "sample_value": "EV"
      },
      {
        "name": "vkorg",
        "description": "Sales organization",
        "datatype": "VARCHAR(4)",
        "nullable": False,
        "business_definition": "Sales organization code. VinFast uses VFVM for domestic Vietnam market, VFNA for North America, VFEU for Europe, and VFAS for ASEAN.",
        "sample_value": "VFVM"
      },
      {
        "name": "vtweg",
        "description": "Distribution channel",
        "datatype": "VARCHAR(2)",
        "nullable": False,
        "business_definition": "Distribution channel: 10=Showroom Direct, 20=Online Direct, 30=Dealer Network, 40=Fleet/Corporate Sales.",
        "sample_value": "10"
      },
      {
        "name": "kunnr",
        "description": "Sold-to customer number",
        "datatype": "VARCHAR(10)",
        "nullable": False,
        "business_definition": "Customer master key for the sold-to party. Links the sales order to the customer who is purchasing the vehicle.",
        "sample_value": "C000012345"
      },
      {
        "name": "erdat",
        "description": "Order creation date",
        "datatype": "DATE",
        "nullable": False,
        "business_definition": "Date when the sales order was created in SAP. Used for order-to-delivery cycle time analysis and order booking reporting.",
        "sample_value": "2025-11-20"
      },
      {
        "name": "netwr",
        "description": "Net value of the order",
        "datatype": "DECIMAL(18,2)",
        "nullable": True,
        "business_definition": "Total net value of the sales order after discounts but before taxes. Primary revenue metric at the order header level.",
        "sample_value": "1250000000.00"
      },
      {
        "name": "waerk",
        "description": "Order currency",
        "datatype": "VARCHAR(5)",
        "nullable": True,
        "business_definition": "Currency of the sales order. VND for domestic sales, USD for export markets. Impacts FX reporting for multinational sales.",
        "sample_value": "VND"
      },
      {
        "name": "bstnk",
        "description": "Customer purchase order number",
        "datatype": "VARCHAR(35)",
        "nullable": True,
        "business_definition": "Reference number from the customer own purchase order system. Used for cross-reference during customer inquiries.",
        "sample_value": "PO-CUST-2025-12345"
      },
      {
        "name": "lifsk",
        "description": "Delivery block reason",
        "datatype": "VARCHAR(2)",
        "nullable": True,
        "business_definition": "Code indicating why delivery is blocked: 01=Credit Hold, 02=Payment Pending, 03=Customs Clearance. Blank means no block.",
        "sample_value": ""
      },
      {
        "name": "vkbur",
        "description": "Sales office",
        "datatype": "VARCHAR(4)",
        "nullable": True,
        "business_definition": "Sales office responsible for the order. Maps to VinFast showrooms and regional sales offices across Vietnam.",
        "sample_value": "HN01"
      }
    ]
  },
  {
    "name": "sap_vbap",
    "description": "Sales Document Item - line-item details for sales orders",
    "domain": "sales",
    "platform": "sap",
    "tags": [
      "Sales",
      "SAP",
      "Transactional"
    ],
    "columns": [
      {
        "name": "vbeln",
        "description": "Sales document number",
        "datatype": "VARCHAR(10)",
        "nullable": False,
        "business_definition": "Parent sales document number. Foreign key to VBAK for the order header context.",
        "sample_value": "SO-9000012345"
      },
      {
        "name": "posnr",
        "description": "Item number",
        "datatype": "INTEGER",
        "nullable": False,
        "business_definition": "Sequential line item number within the sales order. Combined with vbeln forms the unique item identifier.",
        "sample_value": 10
      },
      {
        "name": "matnr",
        "description": "Material number",
        "datatype": "VARCHAR(18)",
        "nullable": True,
        "business_definition": "Material master key for the vehicle model or option being sold. Identifies the specific VinFast model and configuration variant.",
        "sample_value": "VF8-LUX-AWD-2025"
      },
      {
        "name": "kmenge",
        "description": "Cumulative order quantity",
        "datatype": "DECIMAL(15,3)",
        "nullable": True,
        "business_definition": "Total quantity ordered for this line item. For vehicle sales this is typically 1, but can be higher for fleet orders.",
        "sample_value": "1.000"
      },
      {
        "name": "netpr",
        "description": "Net price per unit",
        "datatype": "DECIMAL(18,2)",
        "nullable": True,
        "business_definition": "Unit price for the item in the order currency after discounts. Used to calculate revenue contribution per vehicle or option.",
        "sample_value": "1250000000.00"
      },
      {
        "name": "werks",
        "description": "Plant delivering the material",
        "datatype": "VARCHAR(4)",
        "nullable": True,
        "business_definition": "Plant from which the vehicle will be delivered or picked up. Assigns fulfillment responsibility to specific VinFast facilities.",
        "sample_value": "HP01"
      },
      {
        "name": "abgru",
        "description": "Reason for rejection",
        "datatype": "VARCHAR(2)",
        "nullable": True,
        "business_definition": "Code explaining why a line item was rejected or cancelled: 01=Customer Cancellation, 02=Production Discontinued, 03=Credit Rejected.",
        "sample_value": ""
      },
      {
        "name": "pstyv",
        "description": "Item category",
        "datatype": "VARCHAR(4)",
        "nullable": True,
        "business_definition": "SAP item category: TAN=Standard Vehicle, TAK=Accessory, TAD=Service, TAL=Lease Vehicle. Controls billing and delivery processes.",
        "sample_value": "TAN"
      },
      {
        "name": "uepos",
        "description": "Higher-level item number",
        "datatype": "INTEGER",
        "nullable": True,
        "business_definition": "Item number of the parent item in a bill-of-material or configuration structure. Used for option bundles and vehicle configurations.",
        "sample_value": 0
      },
      {
        "name": "prat9",
        "description": "Delivery date confirmed by plant",
        "datatype": "DATE",
        "nullable": True,
        "business_definition": "Confirmed delivery or production date from the supplying plant. Drives customer promise date and delivery scheduling.",
        "sample_value": "2025-12-20"
      }
    ]
  },
  {
    "name": "sap_kna1",
    "description": "Customer Master - general customer account data",
    "domain": "sales",
    "platform": "sap",
    "tags": [
      "Sales",
      "SAP",
      "MasterData"
    ],
    "columns": [
      {
        "name": "kunnr",
        "description": "Customer number",
        "datatype": "VARCHAR(10)",
        "nullable": False,
        "business_definition": "Unique SAP customer account number. Primary identifier for all customer-related transactions across sales, delivery, and billing.",
        "sample_value": "C000012345"
      },
      {
        "name": "name1",
        "description": "Customer name",
        "datatype": "VARCHAR(35)",
        "nullable": False,
        "business_definition": "Primary name of the customer. For individuals it is the full name; for corporate customers it is the company legal name.",
        "sample_value": "Nguyen Thi Minh Anh"
      },
      {
        "name": "ort01",
        "description": "City",
        "datatype": "VARCHAR(35)",
        "nullable": True,
        "business_definition": "City of the customer registered address. Used for regional sales analysis and delivery zone assignment.",
        "sample_value": "Ha Noi"
      },
      {
        "name": "regio",
        "description": "Region or province",
        "datatype": "VARCHAR(3)",
        "nullable": True,
        "business_definition": "State or province code using ISO 3166-2. For Vietnam: HN=Ha Noi, HCM=Ho Chi Minh City, HP=Hai Phong. For US: CA, TX, etc.",
        "sample_value": "HN"
      },
      {
        "name": "land1",
        "description": "Country key",
        "datatype": "VARCHAR(3)",
        "nullable": False,
        "business_definition": "ISO Alpha-3 country code of the customer. VNM for domestic, USA for US market, DEU for Germany. Drives tax and export compliance.",
        "sample_value": "VNM"
      },
      {
        "name": "kukla",
        "description": "Customer classification",
        "datatype": "VARCHAR(2)",
        "nullable": True,
        "business_definition": "Customer type: RP=Retail Private, RC=Retail Corporate, FL=Fleet, DL=Dealer, GV=Government. Determines pricing tier and service model.",
        "sample_value": "RP"
      },
      {
        "name": "loevm",
        "description": "Deletion flag",
        "datatype": "VARCHAR(1)",
        "nullable": True,
        "business_definition": "Market for deletion flag. X=record marked for deletion, blank=active. Used for data lifecycle management.",
        "sample_value": ""
      },
      {
        "name": "stcd1",
        "description": "Tax identification number",
        "datatype": "VARCHAR(20)",
        "nullable": True,
        "business_definition": "Vietnamese tax ID (Ma so thue) or foreign tax ID. Required for invoice issuance and tax authority reporting.",
        "sample_value": "0123456789"
      },
      {
        "name": "telf1",
        "description": "Primary telephone number",
        "datatype": "VARCHAR(16)",
        "nullable": True,
        "business_definition": "Primary contact phone number for the customer. Used by sales advisors for order status updates and delivery coordination.",
        "sample_value": "+84-90-123-4567"
      },
      {
        "name": "smtp_addr",
        "description": "Email address",
        "datatype": "VARCHAR(241)",
        "nullable": True,
        "business_definition": "Primary email address for digital communications including order confirmations, delivery notifications, and service reminders.",
        "sample_value": "minhanh.nguyen@email.com"
      },
      {
        "name": "erdat",
        "description": "Customer master creation date",
        "datatype": "DATE",
        "nullable": True,
        "business_definition": "Date when the customer master record was created in SAP. Used for customer tenure and loyalty analysis.",
        "sample_value": "2025-06-15"
      }
    ]
  },
  {
    "name": "sap_vbkd",
    "description": "Sales Document Business Data - business data for sales documents",
    "domain": "sales",
    "platform": "sap",
    "tags": [
      "Sales",
      "SAP",
      "Transactional"
    ],
    "columns": [
      {
        "name": "vbeln",
        "description": "Sales document number",
        "datatype": "VARCHAR(10)",
        "nullable": False,
        "business_definition": "Foreign key to VBAK identifying the sales document. Business data extends the header with additional functional context.",
        "sample_value": "SO-9000012345"
      },
      {
        "name": "posnr",
        "description": "Item number",
        "datatype": "INTEGER",
        "nullable": False,
        "business_definition": "Line item number for item-level business data. 0 indicates header-level business data.",
        "sample_value": 0
      },
      {
        "name": "zterm",
        "description": "Payment terms",
        "datatype": "VARCHAR(4)",
        "nullable": True,
        "business_definition": "SAP payment terms key defining due dates and discount conditions. 0001=Payment due immediately, 0002=Net 30, 0003=Installment plan.",
        "sample_value": "0002"
      },
      {
        "name": "incov",
        "description": "Incoterms",
        "datatype": "VARCHAR(3)",
        "nullable": True,
        "business_definition": "International commercial terms code: CIF=Cost Insurance Freight, FOB=Free on Board, EXW=Ex Works. Critical for export sales liability.",
        "sample_value": "CIF"
      },
      {
        "name": "kdkg1",
        "description": "Rebate basis indicator",
        "datatype": "VARCHAR(1)",
        "nullable": True,
        "business_definition": "Indicates whether the order is eligible for rebate programs. Drives accrual calculation for dealer and fleet incentive programs.",
        "sample_value": "1"
      },
      {
        "name": "prsdt",
        "description": "Pricing date",
        "datatype": "DATE",
        "nullable": True,
        "business_definition": "Date used for determining valid pricing conditions. Typically equals the order date but can be overridden for price guarantees.",
        "sample_value": "2025-11-20"
      },
      {
        "name": "vkond",
        "description": "Promotion code",
        "datatype": "VARCHAR(10)",
        "nullable": True,
        "business_definition": "Code identifying the applied promotion or campaign. Links sales orders to marketing initiatives for ROI analysis.",
        "sample_value": "VINFAST-TET-2025"
      },
      {
        "name": "kalsm",
        "description": "Pricing procedure",
        "datatype": "VARCHAR(6)",
        "nullable": True,
        "business_definition": "SAP pricing procedure determining the sequence of condition types used to calculate the final price.",
        "sample_value": "VFSTAND"
      }
    ]
  },
  {
    "name": "sap_vbpa",
    "description": "Sales Partner - partner functions assigned to sales documents",
    "domain": "sales",
    "platform": "sap",
    "tags": [
      "Sales",
      "SAP",
      "Transactional"
    ],
    "columns": [
      {
        "name": "vbeln",
        "description": "Sales document number",
        "datatype": "VARCHAR(10)",
        "nullable": False,
        "business_definition": "Sales document number for which partner functions are defined. Partners include customer, payer, shipto, and sales employee.",
        "sample_value": "SO-9000012345"
      },
      {
        "name": "parvw",
        "description": "Partner function",
        "datatype": "VARCHAR(2)",
        "nullable": False,
        "business_definition": "SAP partner function code: AG=Sold-to, WE=Shipto, RG=Payer, RE=Bill-to, VE=Sales Employee. Each order requires at minimum AG and RG.",
        "sample_value": "AG"
      },
      {
        "name": "kunnr",
        "description": "Customer number for the partner",
        "datatype": "VARCHAR(10)",
        "nullable": False,
        "business_definition": "Customer master key for the partner fulfilling the specified partner function. Different partners may have different customer numbers.",
        "sample_value": "C000012345"
      },
      {
        "name": "lifnr",
        "description": "Vendor number (for consignment)",
        "datatype": "VARCHAR(10)",
        "nullable": True,
        "business_definition": "Vendor number used when the partner is a consignment or third-party supplier. Not typically used in standard vehicle sales.",
        "sample_value": ""
      },
      {
        "name": "adrnr",
        "description": "Address number",
        "datatype": "VARCHAR(10)",
        "nullable": True,
        "business_definition": "SAP address number linking to the specific address record for this partner function. Enables different addresses for sold-to vs ship-to.",
        "sample_value": "ADDR-98765"
      },
      {
        "name": "parza",
        "description": "Partner counter",
        "datatype": "INTEGER",
        "nullable": True,
        "business_definition": "Sequential counter for multiple partners with the same function. For example, multiple ship-to addresses for fleet orders.",
        "sample_value": 1
      },
      {
        "name": "knref",
        "description": "Customer reference number",
        "datatype": "VARCHAR(12)",
        "nullable": True,
        "business_definition": "External reference number from the partner system. Used for EDI and system-to-system partner identification.",
        "sample_value": "EXT-REF-12345"
      }
    ]
  },
  {
    "name": "stg_customer_order",
    "description": "Customer Order Staging - raw sales order data from multiple channels",
    "domain": "sales",
    "platform": "staging",
    "tags": [
      "Sales",
      "Batch",
      "Bronze"
    ],
    "columns": [
      {
        "name": "order_id",
        "description": "Unique order identifier",
        "datatype": "VARCHAR(20)",
        "nullable": False,
        "business_definition": "Primary key for the staged order record. Generated from source system order number and channel prefix for uniqueness.",
        "sample_value": "ONLINE-VF8-20251120-001"
      },
      {
        "name": "order_channel",
        "description": "Source sales channel",
        "datatype": "VARCHAR(20)",
        "nullable": False,
        "business_definition": "Originating channel for the order: Online, Showroom, Dealer, Phone, or Event. Drives channel performance and commission reporting.",
        "sample_value": "Online"
      },
      {
        "name": "customer_id",
        "description": "Customer identifier",
        "datatype": "VARCHAR(10)",
        "nullable": False,
        "business_definition": "Customer ID from the source system awaiting validation against SAP customer master. Subject to deduplication during ETL.",
        "sample_value": "C000012345"
      },
      {
        "name": "vehicle_model",
        "description": "Vehicle model code",
        "datatype": "VARCHAR(20)",
        "nullable": False,
        "business_definition": "VinFast model code ordered: VF3, VF5, VF6, VF7, VF8, VF9, or VFe34. Direct mapping to the material master.",
        "sample_value": "VF8"
      },
      {
        "name": "order_date",
        "description": "Order placement date",
        "datatype": "DATE",
        "nullable": False,
        "business_definition": "Date the customer placed the order. Used for order intake reporting and production slot allocation.",
        "sample_value": "2025-11-20"
      },
      {
        "name": "order_value_vnd",
        "description": "Total order value in VND",
        "datatype": "DECIMAL(18,2)",
        "nullable": True,
        "business_definition": "Total customer-facing order value including all options, accessories, and applicable taxes. Used for revenue forecasting.",
        "sample_value": "1250000000.00"
      },
      {
        "name": "order_status",
        "description": "Current order status",
        "datatype": "VARCHAR(30)",
        "nullable": False,
        "business_definition": "Order status: Pending, Confirmed, In Production, Ready for Delivery, Delivered, or Cancelled. Tracks order lifecycle progress.",
        "sample_value": "Confirmed"
      },
      {
        "name": "preferred_delivery_date",
        "description": "Customer preferred delivery date",
        "datatype": "DATE",
        "nullable": True,
        "business_definition": "Date the customer prefers to receive the vehicle. Production scheduling attempts to align with this preference.",
        "sample_value": "2025-12-25"
      },
      {
        "name": "payment_method",
        "description": "Payment method selected",
        "datatype": "VARCHAR(30)",
        "nullable": True,
        "business_definition": "Customer selected payment method: Full Payment, Bank Loan, VinFast Financial Lease, or Trade-in Program.",
        "sample_value": "Bank Loan"
      },
      {
        "name": "deposit_amount_vnd",
        "description": "Deposit amount paid",
        "datatype": "DECIMAL(18,2)",
        "nullable": True,
        "business_definition": "Amount paid as deposit or booking fee. Typically 10-20% of the total order value for order confirmation.",
        "sample_value": "125000000.00"
      },
      {
        "name": "sales_advisor_id",
        "description": "Sales advisor identifier",
        "datatype": "VARCHAR(10)",
        "nullable": True,
        "business_definition": "ID of the sales advisor associated with the order. For online orders, this is the virtual assistant ID; for showrooms, the assigned advisor.",
        "sample_value": "SA-HN-0042"
      }
    ]
  },
  {
    "name": "stg_vehicle_allocation",
    "description": "Vehicle Allocation Staging - production slot and VIN assignment data",
    "domain": "sales",
    "platform": "staging",
    "tags": [
      "Sales",
      "Batch",
      "Bronze"
    ],
    "columns": [
      {
        "name": "allocation_id",
        "description": "Unique allocation record identifier",
        "datatype": "VARCHAR(30)",
        "nullable": False,
        "business_definition": "Surrogate key for the vehicle allocation record. Links order demand to specific production slots and VIN numbers.",
        "sample_value": "ALLOC-VF8-2025M12-001"
      },
      {
        "name": "order_id",
        "description": "Customer order identifier",
        "datatype": "VARCHAR(20)",
        "nullable": False,
        "business_definition": "Foreign key to the customer order that triggered the allocation. One order generates one allocation for vehicle production.",
        "sample_value": "ONLINE-VF8-20251120-001"
      },
      {
        "name": "vin_number",
        "description": "Vehicle identification number",
        "datatype": "VARCHAR(17)",
        "nullable": True,
        "business_definition": "17-character VIN assigned to the vehicle after production scheduling. Unique global identifier for the manufactured vehicle.",
        "sample_value": "RLXEVF8P5RZ123456"
      },
      {
        "name": "model_code",
        "description": "Vehicle model configuration code",
        "datatype": "VARCHAR(20)",
        "nullable": False,
        "business_definition": "Detailed configuration code specifying model variant, drivetrain, battery type, and region specification.",
        "sample_value": "VF8-LUX-AWD-2025"
      },
      {
        "name": "exterior_color",
        "description": "Exterior paint color code",
        "datatype": "VARCHAR(20)",
        "nullable": True,
        "business_definition": "VinFast color code for the vehicle exterior: VF-BLK=Jet Black, VF-WHT=Pearl White, VF-RED=Sunset Red, VF-BLU=Ocean Blue.",
        "sample_value": "VF-BLK"
      },
      {
        "name": "interior_color",
        "description": "Interior trim color code",
        "datatype": "VARCHAR(20)",
        "nullable": True,
        "business_definition": "Interior color and material code: BK-LTH=Black Leather, TN-LTH=Tan Leather, GR-FAB=Gray Fabric.",
        "sample_value": "BK-LTH"
      },
      {
        "name": "battery_type",
        "description": "Battery configuration type",
        "datatype": "VARCHAR(30)",
        "nullable": True,
        "business_definition": "Battery pack type: Standard Range, Long Range, or Performance. Determines range and pricing for the configured vehicle.",
        "sample_value": "Long Range"
      },
      {
        "name": "production_week",
        "description": "Scheduled production week",
        "datatype": "VARCHAR(7)",
        "nullable": True,
        "business_definition": "ISO week number (YYYY-WW) when the vehicle is scheduled for production. Used for production capacity planning.",
        "sample_value": "2025-W51"
      },
      {
        "name": "allocation_status",
        "description": "Allocation status",
        "datatype": "VARCHAR(30)",
        "nullable": False,
        "business_definition": "Status: Slot Requested, Slot Confirmed, In Production, Pending VIN, VIN Assigned, or Ready for Delivery.",
        "sample_value": "Slot Confirmed"
      },
      {
        "name": "plant_code",
        "description": "Manufacturing plant",
        "datatype": "VARCHAR(4)",
        "nullable": True,
        "business_definition": "Plant code of the facility where the vehicle will be manufactured. Assigned based on model and regional demand.",
        "sample_value": "HP01"
      }
    ]
  },
  {
    "name": "stg_lead",
    "description": "Sales Lead Staging - customer leads and prospect data",
    "domain": "sales",
    "platform": "staging",
    "tags": [
      "Sales",
      "Batch",
      "Bronze"
    ],
    "columns": [
      {
        "name": "lead_id",
        "description": "Unique lead identifier",
        "datatype": "VARCHAR(20)",
        "nullable": False,
        "business_definition": "Primary key for the lead record. Generated from the CRM source system and campaign prefix.",
        "sample_value": "LEAD-WEB-202511-00042"
      },
      {
        "name": "lead_source",
        "description": "Lead acquisition channel",
        "datatype": "VARCHAR(50)",
        "nullable": False,
        "business_definition": "Originating source of the lead: Website, Facebook, TikTok, Zalo, Showroom Visit, Test Drive Event, Referral, or Dealership.",
        "sample_value": "Website"
      },
      {
        "name": "customer_name",
        "description": "Prospect full name",
        "datatype": "VARCHAR(100)",
        "nullable": False,
        "business_definition": "Full name of the prospective customer as provided during lead capture. Used for personalized follow-up communications.",
        "sample_value": "Tran Van Binh"
      },
      {
        "name": "phone_number",
        "description": "Contact phone number",
        "datatype": "VARCHAR(20)",
        "nullable": True,
        "business_definition": "Primary contact number for lead follow-up. Must be validated during conversion to prevent fake leads in the pipeline.",
        "sample_value": "+84-98-765-4321"
      },
      {
        "name": "email",
        "description": "Email address",
        "datatype": "VARCHAR(150)",
        "nullable": True,
        "business_definition": "Email address for digital marketing follow-up and lead nurturing campaigns. Used for automated drip email sequences.",
        "sample_value": "binh.tran@email.com"
      },
      {
        "name": "interested_model",
        "description": "Vehicle model of interest",
        "datatype": "VARCHAR(20)",
        "nullable": True,
        "business_definition": "VinFast model the prospect expressed interest in: VF3, VF5, VF6, VF7, VF8, VF9. Drives targeted marketing content.",
        "sample_value": "VF8"
      },
      {
        "name": "lead_status",
        "description": "Current lead status",
        "datatype": "VARCHAR(30)",
        "nullable": False,
        "business_definition": "Lead qualification stage: New, Contacted, Qualified, Test Drive Scheduled, Offer Made, Converted, or Lost.",
        "sample_value": "Qualified"
      },
      {
        "name": "lead_score",
        "description": "Lead qualification score",
        "datatype": "INTEGER",
        "nullable": True,
        "business_definition": "AI-driven lead score 1-100 based on engagement level, demographic fit, and behavioral signals. Scores above 70 trigger urgent follow-up.",
        "sample_value": 82
      },
      {
        "name": "assigned_sales_advisor",
        "description": "Assigned sales advisor",
        "datatype": "VARCHAR(50)",
        "nullable": True,
        "business_definition": "Sales advisor assigned to follow up on the lead. Auto-assigned based on geographic proximity and workload balance.",
        "sample_value": "Le Thi Huong"
      },
      {
        "name": "created_date",
        "description": "Lead capture timestamp",
        "datatype": "TIMESTAMP",
        "nullable": True,
        "business_definition": "Timestamp when the lead was first captured. Used for lead response time SLA measurement (target under 5 minutes for web leads).",
        "sample_value": "2025-11-20 14:32:15"
      }
    ]
  },
  {
    "name": "fact_vehicle_sales",
    "description": "Vehicle Sales Fact - finalized vehicle sales transactions",
    "domain": "sales",
    "platform": "fact",
    "tags": [
      "Sales",
      "Analytics",
      "Gold",
      "Confidential"
    ],
    "columns": [
      {
        "name": "sales_id",
        "description": "Unique sales transaction identifier",
        "datatype": "VARCHAR(30)",
        "nullable": False,
        "business_definition": "Surrogate key uniquely identifying each vehicle sale transaction. Generated from billing document and fiscal period.",
        "sample_value": "SALE-VF8-202512-001"
      },
      {
        "name": "order_id",
        "description": "Source order identifier",
        "datatype": "VARCHAR(20)",
        "nullable": False,
        "business_definition": "Reference to the original customer order. Enables traceability from lead generation through order booking to final sale.",
        "sample_value": "ONLINE-VF8-20251120-001"
      },
      {
        "name": "customer_key",
        "description": "Customer dimension key",
        "datatype": "VARCHAR(10)",
        "nullable": False,
        "business_definition": "Foreign key to dim_customer identifying the purchaser. Enables customer demographic and behavioral analysis on sales performance.",
        "sample_value": "C000012345"
      },
      {
        "name": "dealer_key",
        "description": "Dealer dimension key",
        "datatype": "VARCHAR(10)",
        "nullable": True,
        "business_definition": "Foreign key to dim_dealer for the selling dealership or showroom. Used for dealer performance scoring and commission calculation.",
        "sample_value": "D-HN-001"
      },
      {
        "name": "model_key",
        "description": "Vehicle model dimension key",
        "datatype": "VARCHAR(20)",
        "nullable": False,
        "business_definition": "Foreign key to dim_model identifying the specific vehicle model and configuration sold. Drives model-level sales analysis.",
        "sample_value": "VF8-LUX-AWD-2025"
      },
      {
        "name": "promotion_key",
        "description": "Promotion dimension key",
        "datatype": "VARCHAR(10)",
        "nullable": True,
        "business_definition": "Foreign key to dim_promotion if the sale was associated with a promotional campaign. Null for non-promotional sales.",
        "sample_value": "PROMO-TET-2025"
      },
      {
        "name": "sale_date",
        "description": "Date of sale",
        "datatype": "DATE",
        "nullable": False,
        "business_definition": "Date on which the sale was finalized and revenue recognized. Governs fiscal period reporting for sales targets.",
        "sample_value": "2025-12-15"
      },
      {
        "name": "sale_amount_vnd",
        "description": "Sale amount in VND",
        "datatype": "DECIMAL(18,2)",
        "nullable": False,
        "business_definition": "Total transaction value in VND including vehicle price, options, accessories, and applicable fees. Core revenue metric.",
        "sample_value": "1250000000.00"
      },
      {
        "name": "discount_amount_vnd",
        "description": "Discount applied in VND",
        "datatype": "DECIMAL(18,2)",
        "nullable": True,
        "business_definition": "Total discount amount applied to the sale including promotional discounts, loyalty discounts, and negotiation adjustments.",
        "sample_value": "50000000.00"
      },
      {
        "name": "net_revenue_vnd",
        "description": "Net revenue after discounts",
        "datatype": "DECIMAL(18,2)",
        "nullable": False,
        "business_definition": "Sale amount minus discounts. Represents the actual revenue recognized by VinFast for the transaction.",
        "sample_value": "1200000000.00"
      },
      {
        "name": "payment_type",
        "description": "Payment method used",
        "datatype": "VARCHAR(30)",
        "nullable": True,
        "business_definition": "Final payment method: Cash, Bank Transfer, Bank Loan, VinFast Financial Lease, or Trade-in with balance payment.",
        "sample_value": "Bank Loan"
      },
      {
        "name": "vin_number",
        "description": "Vehicle VIN number",
        "datatype": "VARCHAR(17)",
        "nullable": True,
        "business_definition": "VIN of the sold vehicle. Links sales records to vehicle production data and after-sales service history.",
        "sample_value": "RLXEVF8P5RZ123456"
      }
    ]
  },
  {
    "name": "fact_order_fulfillment",
    "description": "Order Fulfillment Fact - end-to-end order fulfillment tracking",
    "domain": "sales",
    "platform": "fact",
    "tags": [
      "Sales",
      "Analytics",
      "Gold"
    ],
    "columns": [
      {
        "name": "fulfillment_id",
        "description": "Unique fulfillment tracking identifier",
        "datatype": "VARCHAR(30)",
        "nullable": False,
        "business_definition": "Surrogate key for the order fulfillment record. Tracks a single order through the complete fulfillment lifecycle.",
        "sample_value": "FULFILL-SO-9000012345"
      },
      {
        "name": "order_id",
        "description": "Sales order identifier",
        "datatype": "VARCHAR(20)",
        "nullable": False,
        "business_definition": "Reference to the sales order being fulfilled. Enables end-to-end cycle time analysis from order to delivery.",
        "sample_value": "ONLINE-VF8-20251120-001"
      },
      {
        "name": "order_date",
        "description": "Original order date",
        "datatype": "DATE",
        "nullable": False,
        "business_definition": "Date the customer placed the order. Starting point for the order-to-delivery cycle time calculation.",
        "sample_value": "2025-11-20"
      },
      {
        "name": "production_start_date",
        "description": "Production start date",
        "datatype": "DATE",
        "nullable": True,
        "business_definition": "Date when vehicle production started on the assembly line. Used to measure order-to-production lead time.",
        "sample_value": "2025-12-08"
      },
      {
        "name": "production_completion_date",
        "description": "Production completion date",
        "datatype": "DATE",
        "nullable": True,
        "business_definition": "Date when vehicle completed final assembly and passed quality inspection. Measures production cycle time.",
        "sample_value": "2025-12-12"
      },
      {
        "name": "delivery_date",
        "description": "Actual delivery date",
        "datatype": "DATE",
        "nullable": True,
        "business_definition": "Date the vehicle was delivered to the customer. End point for the order-to-delivery cycle time measurement.",
        "sample_value": "2025-12-20"
      },
      {
        "name": "delivery_method",
        "description": "Delivery method",
        "datatype": "VARCHAR(30)",
        "nullable": True,
        "business_definition": "How the vehicle was delivered: Showroom Pickup, Home Delivery, or Dealership Transfer.",
        "sample_value": "Home Delivery"
      },
      {
        "name": "order_to_delivery_days",
        "description": "Days from order to delivery",
        "datatype": "INTEGER",
        "nullable": True,
        "business_definition": "Total calendar days from order placement to customer delivery. Key customer experience KPI with target under 30 days for standard models.",
        "sample_value": 30
      },
      {
        "name": "fulfillment_status",
        "description": "Current fulfillment status",
        "datatype": "VARCHAR(30)",
        "nullable": False,
        "business_definition": "Status: Order Placed, Scheduled for Production, In Production, Quality Check, Ready for Delivery, Delivered, or Cancelled.",
        "sample_value": "Delivered"
      },
      {
        "name": "delivery_notes",
        "description": "Delivery comments and notes",
        "datatype": "TEXT",
        "nullable": True,
        "business_definition": "Free-text notes about the delivery process including special requests, issues encountered, or customer feedback on delivery experience.",
        "sample_value": "Customer requested Saturday delivery. Vehicle presentation and handover completed successfully."
      }
    ]
  },
  {
    "name": "fact_dealer_performance",
    "description": "Dealer Performance Fact - dealer sales and operational performance metrics",
    "domain": "sales",
    "platform": "fact",
    "tags": [
      "Sales",
      "Analytics",
      "Gold",
      "Confidential"
    ],
    "columns": [
      {
        "name": "performance_id",
        "description": "Unique dealer performance identifier",
        "datatype": "VARCHAR(30)",
        "nullable": False,
        "business_definition": "Surrogate key for monthly dealer performance record. Composite of dealer key and evaluation period.",
        "sample_value": "DPERF-D-HN-001-202511"
      },
      {
        "name": "dealer_key",
        "description": "Dealer dimension key",
        "datatype": "VARCHAR(10)",
        "nullable": False,
        "business_definition": "Foreign key to dim_dealer identifying the dealership. Central identifier for dealer-level performance aggregation.",
        "sample_value": "D-HN-001"
      },
      {
        "name": "evaluation_month",
        "description": "Performance evaluation month",
        "datatype": "VARCHAR(7)",
        "nullable": False,
        "business_definition": "Calendar month in YYYY-MM format for which performance is measured. Enables sequential month-over-month comparison.",
        "sample_value": "2025-11"
      },
      {
        "name": "total_units_sold",
        "description": "Total vehicles sold",
        "datatype": "INTEGER",
        "nullable": False,
        "business_definition": "Number of new vehicles sold by the dealer in the month. Core volume KPI against monthly sales target.",
        "sample_value": 45
      },
      {
        "name": "total_revenue_vnd",
        "description": "Total sales revenue in VND",
        "datatype": "DECIMAL(18,2)",
        "nullable": False,
        "business_definition": "Aggregated gross revenue generated by the dealer in the month. Includes vehicle sales and accessories.",
        "sample_value": "54000000000.00"
      },
      {
        "name": "target_achievement_pct",
        "description": "Percentage of target achieved",
        "datatype": "DECIMAL(5,2)",
        "nullable": True,
        "business_definition": "Units sold divided by monthly target multiplied by 100. Performance above 100% qualifies for volume bonus incentives.",
        "sample_value": "112.50"
      },
      {
        "name": "customer_satisfaction_score",
        "description": "Average customer satisfaction",
        "datatype": "DECIMAL(4,2)",
        "nullable": True,
        "business_definition": "Average customer satisfaction score (1.0-5.0) from post-purchase surveys. VinFast minimum threshold is 4.0.",
        "sample_value": "4.50"
      },
      {
        "name": "test_drives_conducted",
        "description": "Test drives conducted",
        "datatype": "INTEGER",
        "nullable": True,
        "business_definition": "Number of test drives conducted at the dealership during the month. Leading indicator for future sales conversion.",
        "sample_value": 120
      },
      {
        "name": "lead_conversion_rate",
        "description": "Lead-to-sale conversion rate",
        "datatype": "DECIMAL(4,2)",
        "nullable": True,
        "business_definition": "Percentage of qualified leads that resulted in a sale within the month. Industry benchmark for automotive is 15-25%.",
        "sample_value": "22.50"
      },
      {
        "name": "aftersales_revenue_vnd",
        "description": "After-sales service revenue",
        "datatype": "DECIMAL(18,2)",
        "nullable": True,
        "business_definition": "Revenue generated from service visits, parts sales, and warranty work at the dealer service center.",
        "sample_value": "8500000000.00"
      }
    ]
  },
  {
    "name": "dim_customer",
    "description": "Customer Dimension - customer demographic and behavioral attributes",
    "domain": "sales",
    "platform": "dimension",
    "tags": [
      "Sales",
      "MasterData",
      "Gold",
      "Confidential",
      "PII"
    ],
    "columns": [
      {
        "name": "customer_key",
        "description": "Customer surrogate key",
        "datatype": "VARCHAR(10)",
        "nullable": False,
        "business_definition": "Surrogate primary key for the customer dimension. Maps 1:1 to SAP KUNNR and serves as the customer identifier across all fact tables.",
        "sample_value": "C000012345"
      },
      {
        "name": "full_name",
        "description": "Customer full name",
        "datatype": "VARCHAR(100)",
        "nullable": False,
        "business_definition": "Full name of the customer as registered in the customer master. Handling of Vietnamese name order (family + middle + given) is required.",
        "sample_value": "Nguyen Thi Minh Anh"
      },
      {
        "name": "gender",
        "description": "Customer gender",
        "datatype": "VARCHAR(10)",
        "nullable": True,
        "business_definition": "Customer gender for demographic analysis. Sourced from CRM profile data. Used in aggregate for market segmentation.",
        "sample_value": "Female"
      },
      {
        "name": "age_group",
        "description": "Age bracket",
        "datatype": "VARCHAR(10)",
        "nullable": True,
        "business_definition": "Age group category: 18-25, 26-35, 36-45, 46-55, 56+. Used for target market analysis and product positioning.",
        "sample_value": "26-35"
      },
      {
        "name": "city",
        "description": "City of residence",
        "datatype": "VARCHAR(50)",
        "nullable": True,
        "business_definition": "Primary city of residence. Used for regional sales analysis and targeted marketing campaigns.",
        "sample_value": "Ha Noi"
      },
      {
        "name": "province",
        "description": "Province of residence",
        "datatype": "VARCHAR(50)",
        "nullable": True,
        "business_definition": "Province-level geographic classification for regional market analysis and delivery logistics planning.",
        "sample_value": "Ha Noi"
      },
      {
        "name": "customer_segment",
        "description": "Customer segmentation category",
        "datatype": "VARCHAR(30)",
        "nullable": True,
        "business_definition": "Marketing segment: Premium, Mass Market, First-Time Buyer, Fleet, or Corporate. Drives differentiated service and communication strategies.",
        "sample_value": "Premium"
      },
      {
        "name": "acquisition_channel",
        "description": "Customer acquisition channel",
        "datatype": "VARCHAR(30)",
        "nullable": True,
        "business_definition": "How the customer was first acquired: Showroom Visit, Online, Referral, Event, or Third-Party Platform.",
        "sample_value": "Online"
      },
      {
        "name": "is_vip",
        "description": "VIP customer flag",
        "datatype": "BOOLEAN",
        "nullable": False,
        "business_definition": "Flags customers designated as VIP based on purchase history, loyalty, or high net worth status. VIP customers receive priority service.",
        "sample_value": False
      },
      {
        "name": "customer_since_date",
        "description": "Date of first purchase",
        "datatype": "DATE",
        "nullable": True,
        "business_definition": "Date of the customer first vehicle purchase from VinFast. Used for customer loyalty tenure calculation.",
        "sample_value": "2025-12-15"
      }
    ]
  },
  {
    "name": "dim_dealer",
    "description": "Dealer Dimension - dealership and showroom attributes",
    "domain": "sales",
    "platform": "dimension",
    "tags": [
      "Sales",
      "MasterData",
      "Gold"
    ],
    "columns": [
      {
        "name": "dealer_key",
        "description": "Dealer surrogate key",
        "datatype": "VARCHAR(10)",
        "nullable": False,
        "business_definition": "Surrogate primary key for the dealer dimension. Assigned by VinFast to each authorized dealership and company-owned showroom.",
        "sample_value": "D-HN-001"
      },
      {
        "name": "dealer_name",
        "description": "Dealership legal name",
        "datatype": "VARCHAR(200)",
        "nullable": False,
        "business_definition": "Registered business name of the dealership as per the dealer agreement with VinFast.",
        "sample_value": "VinFast Ha Noi - Showroom Nguyen Trai"
      },
      {
        "name": "dealer_type",
        "description": "Dealer type classification",
        "datatype": "VARCHAR(30)",
        "nullable": True,
        "business_definition": "Type: Company-Owned Showroom, Authorized Dealer, Service Center Only, or Mobile Service Partner.",
        "sample_value": "Authorized Dealer"
      },
      {
        "name": "dealer_tier",
        "description": "Dealer performance tier",
        "datatype": "VARCHAR(20)",
        "nullable": True,
        "business_definition": "Dealer tier based on sales volume and customer satisfaction: Platinum, Gold, Silver, or Standard. Determines incentive rates.",
        "sample_value": "Gold"
      },
      {
        "name": "city",
        "description": "City of dealer location",
        "datatype": "VARCHAR(50)",
        "nullable": True,
        "business_definition": "City where the dealership is physically located. Used for territory mapping and regional sales analysis.",
        "sample_value": "Ha Noi"
      },
      {
        "name": "region",
        "description": "Sales region",
        "datatype": "VARCHAR(30)",
        "nullable": True,
        "business_definition": "Sales region classification: Northern, Central, Southern, or International. Aligns with VinFast regional sales management structure.",
        "sample_value": "Northern"
      },
      {
        "name": "opening_date",
        "description": "Dealer opening date",
        "datatype": "DATE",
        "nullable": True,
        "business_definition": "Date the dealership commenced operations under the VinFast brand. Used for dealer maturity analysis.",
        "sample_value": "2022-03-20"
      },
      {
        "name": "is_active",
        "description": "Dealer active status",
        "datatype": "BOOLEAN",
        "nullable": False,
        "business_definition": "Indicates whether the dealer is currently active and authorized to sell VinFast vehicles and provide services.",
        "sample_value": True
      }
    ]
  },
  {
    "name": "dim_model",
    "description": "Vehicle Model Dimension - product and vehicle model attributes",
    "domain": "sales",
    "platform": "dimension",
    "tags": [
      "Sales",
      "MasterData",
      "Gold"
    ],
    "columns": [
      {
        "name": "model_key",
        "description": "Model configuration key",
        "datatype": "VARCHAR(20)",
        "nullable": False,
        "business_definition": "Surrogate primary key for the vehicle model and configuration variant. Maps to SAP material master for the configurable vehicle.",
        "sample_value": "VF8-LUX-AWD-2025"
      },
      {
        "name": "model_name",
        "description": "Commercial model name",
        "datatype": "VARCHAR(50)",
        "nullable": False,
        "business_definition": "Consumer-facing model name: VF 3, VF 5, VF 6, VF 7, VF 8, VF 9, or VFe34. Used in marketing and sales materials.",
        "sample_value": "VF 8"
      },
      {
        "name": "model_family",
        "description": "Model family name",
        "datatype": "VARCHAR(30)",
        "nullable": True,
        "business_definition": "Broader model family classification: Mini SUV (VF3), Compact SUV (VF5/6), Mid-size SUV (VF7/8), Full-size SUV (VF9).",
        "sample_value": "Mid-size SUV"
      },
      {
        "name": "drivetrain",
        "description": "Drivetrain type",
        "datatype": "VARCHAR(20)",
        "nullable": True,
        "business_definition": "Drivetrain configuration: FWD (Front Wheel Drive), RWD (Rear Wheel Drive), or AWD (All Wheel Drive).",
        "sample_value": "AWD"
      },
      {
        "name": "battery_capacity_kwh",
        "description": "Battery capacity in kWh",
        "datatype": "DECIMAL(5,1)",
        "nullable": True,
        "business_definition": "Lithium-ion battery pack capacity in kilowatt-hours. Ranges from 42 kWh (VF3) to 123 kWh (VF9). Key product specification.",
        "sample_value": "94.0"
      },
      {
        "name": "range_km",
        "description": "Estimated driving range in km",
        "datatype": "INTEGER",
        "nullable": True,
        "business_definition": "Estimated WLTP driving range in kilometers on a full charge. Critical factor in customer purchasing decisions.",
        "sample_value": 510
      },
      {
        "name": "base_price_vnd",
        "description": "Manufacturer suggested retail price",
        "datatype": "DECIMAL(18,2)",
        "nullable": True,
        "business_definition": "VinFast MSRP for the base model configuration before options and incentives. Used for pricing analysis and discount calculations.",
        "sample_value": "1150000000.00"
      },
      {
        "name": "model_year",
        "description": "Model year designation",
        "datatype": "INTEGER",
        "nullable": True,
        "business_definition": "Manufacturing model year for the vehicle variant. Used for year-over-year model comparison and depreciation analysis.",
        "sample_value": 2025
      },
      {
        "name": "production_status",
        "description": "Current production status",
        "datatype": "VARCHAR(20)",
        "nullable": True,
        "business_definition": "Production lifecycle status: Active, Discontinued, Coming Soon, or Limited Edition. Controls availability for ordering.",
        "sample_value": "Active"
      },
      {
        "name": "segment",
        "description": "Vehicle market segment",
        "datatype": "VARCHAR(30)",
        "nullable": True,
        "business_definition": "Market segment: A-SUV, B-SUV, C-SUV, D-SUV, or Mini EV. Aligns with global automotive classification standards.",
        "sample_value": "D-SUV"
      }
    ]
  },
  {
    "name": "dim_promotion",
    "description": "Promotion Dimension - sales promotion and campaign attributes",
    "domain": "sales",
    "platform": "dimension",
    "tags": [
      "Sales",
      "MasterData",
      "Gold"
    ],
    "columns": [
      {
        "name": "promotion_key",
        "description": "Promotion surrogate key",
        "datatype": "VARCHAR(10)",
        "nullable": False,
        "business_definition": "Surrogate primary key for the promotion. Assigned by the marketing department for each campaign initiative.",
        "sample_value": "PROMO-TET-2025"
      },
      {
        "name": "promotion_name",
        "description": "Promotion display name",
        "datatype": "VARCHAR(200)",
        "nullable": False,
        "business_definition": "Consumer-facing name of the promotion campaign. Used in marketing communications and sales materials.",
        "sample_value": "Tet 2025 - Year of the Snake Special"
      },
      {
        "name": "promotion_type",
        "description": "Type of promotion",
        "datatype": "VARCHAR(30)",
        "nullable": True,
        "business_definition": "Category: Cash Discount, Free Accessories, Trade-in Bonus, Loyalty Discount, Financing Subsidy, or Test Drive Event.",
        "sample_value": "Cash Discount"
      },
      {
        "name": "discount_percentage",
        "description": "Discount percentage offered",
        "datatype": "DECIMAL(5,2)",
        "nullable": True,
        "business_definition": "Percentage discount off the MSRP offered under the promotion. Typically ranges from 3% to 15% for seasonal campaigns.",
        "sample_value": "10.00"
      },
      {
        "name": "valid_from",
        "description": "Promotion start date",
        "datatype": "DATE",
        "nullable": False,
        "business_definition": "First date on which the promotion is available to customers. Orders placed before this date are not eligible.",
        "sample_value": "2025-12-01"
      },
      {
        "name": "valid_to",
        "description": "Promotion end date",
        "datatype": "DATE",
        "nullable": False,
        "business_definition": "Last date on which the promotion is available. Promotions can have limited inventory or limited time validity.",
        "sample_value": "2026-01-31"
      },
      {
        "name": "applicable_models",
        "description": "Vehicle models included",
        "datatype": "VARCHAR(200)",
        "nullable": True,
        "business_definition": "List of vehicle model codes eligible for the promotion. Some promotions target specific models to manage inventory.",
        "sample_value": "VF8, VF9"
      },
      {
        "name": "budget_vnd",
        "description": "Promotion budget in VND",
        "datatype": "DECIMAL(18,2)",
        "nullable": True,
        "business_definition": "Total allocated budget for the promotion campaign. Used for ROI analysis against incremental sales generated.",
        "sample_value": "50000000000.00"
      },
      {
        "name": "redemption_count",
        "description": "Times promotion has been redeemed",
        "datatype": "INTEGER",
        "nullable": True,
        "business_definition": "Number of sales transactions where the promotion was applied. Tracked against budget to manage remaining capacity.",
        "sample_value": 234
      }
    ]
  },
  {
    "name": "agg_daily_sales_by_model",
    "description": "Daily Sales by Model - aggregated daily sales volume per vehicle model",
    "domain": "sales",
    "platform": "aggregate",
    "tags": [
      "Sales",
      "Analytics",
      "Gold",
      "PowerBI",
      "RealTime"
    ],
    "columns": [
      {
        "name": "sale_date",
        "description": "Calendar date",
        "datatype": "DATE",
        "nullable": False,
        "business_definition": "Date of the aggregated sales transactions. Enables daily trend analysis and short-term sales forecasting.",
        "sample_value": "2025-12-15"
      },
      {
        "name": "model_key",
        "description": "Vehicle model key",
        "datatype": "VARCHAR(20)",
        "nullable": False,
        "business_definition": "Foreign key to dim_model identifying the vehicle model. Composite key with sale_date for unique daily model sales tracking.",
        "sample_value": "VF8-LUX-AWD-2025"
      },
      {
        "name": "units_sold",
        "description": "Number of units sold",
        "datatype": "INTEGER",
        "nullable": False,
        "business_definition": "Total number of vehicles of this model sold on the given date. Core daily sales velocity metric.",
        "sample_value": 12
      },
      {
        "name": "gross_revenue_vnd",
        "description": "Gross revenue in VND",
        "datatype": "DECIMAL(18,2)",
        "nullable": False,
        "business_definition": "Sum of gross transaction values before discounts for the model on the date. Used for daily revenue tracking.",
        "sample_value": "15000000000.00"
      },
      {
        "name": "avg_discount_pct",
        "description": "Average discount percentage",
        "datatype": "DECIMAL(5,2)",
        "nullable": True,
        "business_definition": "Average discount percentage applied to sales of this model on the date. Monitors discount depth and margin impact.",
        "sample_value": "8.50"
      },
      {
        "name": "channel_breakdown_json",
        "description": "Sales by channel (JSON)",
        "datatype": "TEXT",
        "nullable": True,
        "business_definition": "JSON structure containing sales breakdown by channel (showroom, online, dealer) for the model and date. Parsed in reporting layer.",
        "sample_value": "{\"showroom\": 5, \"online\": 4, \"dealer\": 3}"
      },
      {
        "name": "running_7day_avg",
        "description": "7-day rolling average",
        "datatype": "DECIMAL(6,2)",
        "nullable": True,
        "business_definition": "Rolling 7-day average of units sold for the model. Smooths daily fluctuations for trend analysis.",
        "sample_value": "8.57"
      }
    ]
  },
  {
    "name": "agg_monthly_dealer_target",
    "description": "Monthly Dealer Target - monthly sales targets assigned to each dealer",
    "domain": "sales",
    "platform": "aggregate",
    "tags": [
      "Sales",
      "Analytics",
      "Gold",
      "Confidential"
    ],
    "columns": [
      {
        "name": "target_id",
        "description": "Unique target record identifier",
        "datatype": "VARCHAR(30)",
        "nullable": False,
        "business_definition": "Surrogate key for the monthly dealer target. Composite of dealer key, fiscal year, and period.",
        "sample_value": "TGT-D-HN-001-2025-11"
      },
      {
        "name": "dealer_key",
        "description": "Dealer dimension key",
        "datatype": "VARCHAR(10)",
        "nullable": False,
        "business_definition": "Foreign key to dim_dealer identifying the dealership being assigned a sales target.",
        "sample_value": "D-HN-001"
      },
      {
        "name": "fiscal_year",
        "description": "Target fiscal year",
        "datatype": "INTEGER",
        "nullable": False,
        "business_definition": "Fiscal year to which the target belongs. Aligns with VinFast fiscal calendar for annual performance evaluation.",
        "sample_value": 2025
      },
      {
        "name": "fiscal_month",
        "description": "Target fiscal month (1-12)",
        "datatype": "INTEGER",
        "nullable": False,
        "business_definition": "Fiscal period number 1-12 within the fiscal year. Enables monthly target tracking and attainment analysis.",
        "sample_value": 11
      },
      {
        "name": "target_units",
        "description": "Target number of units",
        "datatype": "INTEGER",
        "nullable": False,
        "business_definition": "Number of vehicle units the dealer is expected to sell in the month. Negotiated between VinFast regional sales manager and dealer.",
        "sample_value": 40
      },
      {
        "name": "target_revenue_vnd",
        "description": "Target revenue in VND",
        "datatype": "DECIMAL(18,2)",
        "nullable": True,
        "business_definition": "Revenue target derived from unit targets multiplied by expected average selling price per model.",
        "sample_value": "50000000000.00"
      },
      {
        "name": "target_aftersales_revenue_vnd",
        "description": "Target after-sales revenue",
        "datatype": "DECIMAL(18,2)",
        "nullable": True,
        "business_definition": "Revenue target for the dealer service and parts operations. Part of the dealer balanced scorecard.",
        "sample_value": "7500000000.00"
      },
      {
        "name": "customer_satisfaction_target",
        "description": "Target CSAT score",
        "datatype": "DECIMAL(4,2)",
        "nullable": True,
        "business_definition": "Minimum average customer satisfaction score target. Dealers falling below 4.0 may face corrective actions.",
        "sample_value": "4.20"
      },
      {
        "name": "bonus_per_unit_vnd",
        "description": "Bonus incentive per unit",
        "datatype": "DECIMAL(18,2)",
        "nullable": True,
        "business_definition": "Volume bonus amount paid per unit sold above the target threshold. Incentivizes over-performance against target.",
        "sample_value": "5000000.00"
      },
      {
        "name": "target_status",
        "description": "Target approval status",
        "datatype": "VARCHAR(20)",
        "nullable": False,
        "business_definition": "Status: Draft, Proposed, Agreed, or Finalized. Targets must reach Finalized before they are used for performance evaluation.",
        "sample_value": "Finalized"
      }
    ]
  },
  {
    "name": "agg_sales_pipeline",
    "description": "Sales Pipeline - aggregated sales opportunity pipeline by stage",
    "domain": "sales",
    "platform": "aggregate",
    "tags": [
      "Sales",
      "Analytics",
      "Gold",
      "PowerBI"
    ],
    "columns": [
      {
        "name": "pipeline_date",
        "description": "Pipeline snapshot date",
        "datatype": "DATE",
        "nullable": False,
        "business_definition": "Date of the pipeline snapshot. Pipeline is typically captured daily or weekly for trend analysis and forecasting.",
        "sample_value": "2025-11-20"
      },
      {
        "name": "pipeline_stage",
        "description": "Pipeline stage name",
        "datatype": "VARCHAR(30)",
        "nullable": False,
        "business_definition": "Stage in the sales pipeline: Lead, Qualified, Test Drive, Negotiation, Offer Sent, Order Booked. Maps to CRM opportunity stages.",
        "sample_value": "Test Drive"
      },
      {
        "name": "opportunity_count",
        "description": "Number of opportunities",
        "datatype": "INTEGER",
        "nullable": False,
        "business_definition": "Count of sales opportunities currently in this pipeline stage. Used for funnel volume analysis.",
        "sample_value": 45
      },
      {
        "name": "total_pipeline_value_vnd",
        "description": "Total pipeline value in VND",
        "datatype": "DECIMAL(18,2)",
        "nullable": True,
        "business_definition": "Sum of estimated deal values for all opportunities in the stage. Weighted by stage probability for revenue forecasting.",
        "sample_value": "56250000000.00"
      },
      {
        "name": "weighted_value_vnd",
        "description": "Probability-weighted pipeline value",
        "datatype": "DECIMAL(18,2)",
        "nullable": True,
        "business_definition": "Total pipeline value multiplied by the stage conversion probability. Used for expected revenue forecasting.",
        "sample_value": "28125000000.00"
      },
      {
        "name": "avg_deal_size_vnd",
        "description": "Average deal size in VND",
        "datatype": "DECIMAL(18,2)",
        "nullable": True,
        "business_definition": "Average estimated deal value for opportunities in the stage. Used for sales coaching and deal qualification assessment.",
        "sample_value": "1250000000.00"
      },
      {
        "name": "stage_conversion_rate",
        "description": "Historical stage conversion rate",
        "datatype": "DECIMAL(5,2)",
        "nullable": True,
        "business_definition": "Historical percentage of opportunities that move from this stage to the next. Used for pipeline health evaluation.",
        "sample_value": "60.00"
      }
    ]
  },
  {
    "name": "sap_tvak",
    "description": "Sales Document Types - SAP sales document type configuration",
    "domain": "sales",
    "platform": "sap",
    "tags": [
      "Sales",
      "SAP",
      "MasterData"
    ],
    "columns": [
      {
        "name": "auart",
        "description": "Sales document type",
        "datatype": "VARCHAR(4)",
        "nullable": False,
        "business_definition": "SAP sales document type code. Primary key for the sales document type configuration table.",
        "sample_value": "EV"
      },
      {
        "name": "bezei",
        "description": "Description of sales document type",
        "datatype": "VARCHAR(20)",
        "nullable": True,
        "business_definition": "Short text description of the document type: EV=Electric Vehicle Order, OR=Standard Order, TA=Telephone Order.",
        "sample_value": "EV Order"
      },
      {
        "name": "vorga",
        "description": "Sales transaction group",
        "datatype": "VARCHAR(1)",
        "nullable": True,
        "business_definition": "High-level transaction group: A=Individual customer order, B=Project, C=Stock transport. Governs high-level processing logic.",
        "sample_value": "A"
      },
      {
        "name": "statx",
        "description": "Status profile",
        "datatype": "VARCHAR(8)",
        "nullable": True,
        "business_definition": "SAP status profile determining the allowed lifecycle statuses and transitions for the document type.",
        "sample_value": "EVSTAT"
      },
      {
        "name": "numerk",
        "description": "Number range key",
        "datatype": "VARCHAR(2)",
        "nullable": True,
        "business_definition": "Number range interval key for automatic document numbering. Ensures unique numbering per document type.",
        "sample_value": "01"
      }
    ]
  },
  {
    "name": "dim_region",
    "description": "Region Dimension - geographic sales region hierarchy",
    "domain": "sales",
    "platform": "dimension",
    "tags": [
      "Sales",
      "MasterData",
      "Gold"
    ],
    "columns": [
      {
        "name": "region_key",
        "description": "Region code",
        "datatype": "VARCHAR(10)",
        "nullable": False,
        "business_definition": "Surrogate primary key for the geographic sales region. Used as a foreign key in dealer and customer dimensions.",
        "sample_value": "REG-NORTH"
      },
      {
        "name": "region_name",
        "description": "Region display name",
        "datatype": "VARCHAR(100)",
        "nullable": False,
        "business_definition": "Human-readable name of the region: Northern Vietnam, Central Vietnam, Southern Vietnam, or International.",
        "sample_value": "Northern Vietnam"
      },
      {
        "name": "region_manager",
        "description": "Regional sales manager",
        "datatype": "VARCHAR(100)",
        "nullable": True,
        "business_definition": "Full name of the regional sales manager responsible for the region performance and dealer network management.",
        "sample_value": "Pham Van Cuong"
      },
      {
        "name": "country",
        "description": "Country code",
        "datatype": "VARCHAR(3)",
        "nullable": False,
        "business_definition": "ISO Alpha-3 country code for the region. VNM for domestic regions, country-specific codes for international markets.",
        "sample_value": "VNM"
      },
      {
        "name": "is_domestic",
        "description": "Domestic region flag",
        "datatype": "BOOLEAN",
        "nullable": False,
        "business_definition": "True for regions within Vietnam. False for international markets. Used for domestic vs export sales segmentation.",
        "sample_value": True
      },
      {
        "name": "target_quarterly_units",
        "description": "Quarterly sales target for region",
        "datatype": "INTEGER",
        "nullable": True,
        "business_definition": "Aggregated quarterly sales target for all dealers in the region. Used for regional performance tracking.",
        "sample_value": 1500
      }
    ]
  },
  {
    "name": "sap_qmel",
    "description": "Notification Header - quality and service notification header data",
    "domain": "after_sales",
    "platform": "sap",
    "tags": [
      "AfterSales",
      "SAP",
      "MasterData"
    ],
    "columns": [
      {
        "name": "qmnum",
        "description": "Notification number",
        "datatype": "VARCHAR(12)",
        "nullable": False,
        "business_definition": "Unique SAP notification number. Primary key for quality and service notifications across after-sales operations.",
        "sample_value": "NOTIF-1000012345"
      },
      {
        "name": "qmart",
        "description": "Notification type",
        "datatype": "VARCHAR(2)",
        "nullable": False,
        "business_definition": "SAP notification category: Q1=Quality Problem, Q2=Customer Complaint, S1=Service Request, S2=Warranty Claim, W1=Vehicle Handover.",
        "sample_value": "Q2"
      },
      {
        "name": "kunnr",
        "description": "Customer number",
        "datatype": "VARCHAR(10)",
        "nullable": True,
        "business_definition": "Customer who reported the issue or is associated with the service request. Links to SAP customer master.",
        "sample_value": "C000012345"
      },
      {
        "name": "arbpl",
        "description": "Work center",
        "datatype": "VARCHAR(8)",
        "nullable": True,
        "business_definition": "SAP work center code for the service center or repair shop handling the notification. Maps to VinFast service facility codes.",
        "sample_value": "SC-HN-01"
      },
      {
        "name": "ernam",
        "description": "Created by user",
        "datatype": "VARCHAR(12)",
        "nullable": True,
        "business_definition": "SAP user ID of the person or system that created the notification. Tracks accountability for service entry.",
        "sample_value": "SERVICE_DESK"
      },
      {
        "name": "erdat",
        "description": "Creation date",
        "datatype": "DATE",
        "nullable": True,
        "business_definition": "Date the notification was created in SAP. Used for service response time and SLA compliance measurement.",
        "sample_value": "2025-11-25"
      },
      {
        "name": "auswk",
        "description": "Object damage assessment",
        "datatype": "VARCHAR(50)",
        "nullable": True,
        "business_definition": "Preliminary assessment of the vehicle issue severity: Minor, Moderate, Major, or Critical. Drives prioritization and resource allocation.",
        "sample_value": "Moderate"
      },
      {
        "name": "ilart",
        "description": "Maintenance activity type",
        "datatype": "VARCHAR(3)",
        "nullable": True,
        "business_definition": "Type of activity: PM=Preventive Maintenance, RE=Repair, IN=Inspection, CO=Campaign. Determines the service workflow applied.",
        "sample_value": "RE"
      },
      {
        "name": "strmn",
        "description": "Expected start date",
        "datatype": "DATE",
        "nullable": True,
        "business_definition": "Planned start date for the service activity. Used for service bay scheduling and appointment management.",
        "sample_value": "2025-11-26"
      },
      {
        "name": "ltrmn",
        "description": "Expected finish date",
        "datatype": "DATE",
        "nullable": True,
        "business_definition": "Target completion date for the service activity. Compared against actual completion for cycle time analysis.",
        "sample_value": "2025-11-27"
      },
      {
        "name": "priok",
        "description": "Notification priority",
        "datatype": "VARCHAR(1)",
        "nullable": True,
        "business_definition": "Priority level: 1=Very Urgent, 2=Urgent, 3=Normal, 4=Low. Determines escalation and scheduling order in the service center.",
        "sample_value": "2"
      }
    ]
  },
  {
    "name": "sap_qmsm",
    "description": "Notification Task - individual tasks and activities within notifications",
    "domain": "after_sales",
    "platform": "sap",
    "tags": [
      "AfterSales",
      "SAP",
      "Transactional"
    ],
    "columns": [
      {
        "name": "qmnum",
        "description": "Notification number",
        "datatype": "VARCHAR(12)",
        "nullable": False,
        "business_definition": "Parent notification number. Foreign key to QMEL for the notification header context.",
        "sample_value": "NOTIF-1000012345"
      },
      {
        "name": "manum",
        "description": "Task number",
        "datatype": "INTEGER",
        "nullable": False,
        "business_definition": "Sequential task number within the notification. Combined with qmnum forms the unique task identifier.",
        "sample_value": 10
      },
      {
        "name": "matxt",
        "description": "Task description",
        "datatype": "VARCHAR(40)",
        "nullable": True,
        "business_definition": "Short description of the task to be performed. Examples: Diagnostic Scan, Battery Replacement, Software Update.",
        "sample_value": "HV Battery Diagnostic Scan"
      },
      {
        "name": "qmtxt",
        "description": "Task text",
        "datatype": "TEXT",
        "nullable": True,
        "business_definition": "Detailed free-text instructions or notes for the technician performing the task. Includes diagnostic codes and repair procedures.",
        "sample_value": "Run full HV battery diagnostic using VDS tool. Check cell voltage deviation across all 108 cells."
      },
      {
        "name": "arbpl",
        "description": "Work center assigned",
        "datatype": "VARCHAR(8)",
        "nullable": True,
        "business_definition": "Work center or service bay assigned to perform this specific task. Enables workload balancing across service center resources.",
        "sample_value": "BAY-HV-02"
      },
      {
        "name": "priok",
        "description": "Task priority",
        "datatype": "VARCHAR(1)",
        "nullable": True,
        "business_definition": "Priority of the individual task within the notification context: 1=Critical path, 2=Standard, 3=Optional.",
        "sample_value": "1"
      },
      {
        "name": "stemq",
        "description": "Task status",
        "datatype": "VARCHAR(2)",
        "nullable": True,
        "business_definition": "SAP task status code: CR=Created, IP=In Progress, CO=Completed, DL=Deleted. Tracks task lifecycle.",
        "sample_value": "IP"
      },
      {
        "name": "isr_date",
        "description": "Task start date",
        "datatype": "DATE",
        "nullable": True,
        "business_definition": "Actual date work on the task commenced. Used for tracking technician productivity and task duration.",
        "sample_value": "2025-11-26"
      },
      {
        "name": "ier_date",
        "description": "Task end date",
        "datatype": "DATE",
        "nullable": True,
        "business_definition": "Actual date the task was completed. Used to calculate actual repair time vs estimated time for variance analysis.",
        "sample_value": "2025-11-26"
      },
      {
        "name": "gstrp",
        "description": "Warranty code",
        "datatype": "VARCHAR(4)",
        "nullable": True,
        "business_definition": "Warranty classification code for the repair task: WTY=Warranty, CUS=Customer Pay, INS=Insurance, REC=Recall Campaign.",
        "sample_value": "WTY"
      }
    ]
  },
  {
    "name": "sap_viqmel",
    "description": "Notification List - comprehensive list view of all notifications",
    "domain": "after_sales",
    "platform": "sap",
    "tags": [
      "AfterSales",
      "SAP",
      "Transactional"
    ],
    "columns": [
      {
        "name": "qmnum",
        "description": "Notification number",
        "datatype": "VARCHAR(12)",
        "nullable": False,
        "business_definition": "Unique notification number. Primary key used across notification processing systems.",
        "sample_value": "NOTIF-1000012345"
      },
      {
        "name": "qmart",
        "description": "Notification type",
        "datatype": "VARCHAR(2)",
        "nullable": False,
        "business_definition": "Notification category code for filtering and reporting. Q1=Quality Problem, Q2=Customer Complaint, S1=Service Request.",
        "sample_value": "Q2"
      },
      {
        "name": "qmtxt",
        "description": "Notification description",
        "datatype": "VARCHAR(40)",
        "nullable": True,
        "business_definition": "Brief description of the notification issue or request. Appears in service advisor dashboards and customer communications.",
        "sample_value": "VF8 - Battery range degradation complaint"
      },
      {
        "name": "erdat",
        "description": "Creation date",
        "datatype": "DATE",
        "nullable": True,
        "business_definition": "Date the notification was entered into the system. Used for aging analysis and backlog management.",
        "sample_value": "2025-11-25"
      },
      {
        "name": "equnr",
        "description": "Equipment number (VIN)",
        "datatype": "VARCHAR(18)",
        "nullable": True,
        "business_definition": "Equipment master number, typically the VIN of the vehicle under service. Links the notification to the specific vehicle.",
        "sample_value": "RLXEVF8P5RZ123456"
      },
      {
        "name": "kunnr",
        "description": "Customer number",
        "datatype": "VARCHAR(10)",
        "nullable": True,
        "business_definition": "Customer number for the party reporting the issue. Used for customer communication and follow-up.",
        "sample_value": "C000012345"
      },
      {
        "name": "arbpl",
        "description": "Work center",
        "datatype": "VARCHAR(8)",
        "nullable": True,
        "business_definition": "Work center assigned to handle the notification. Enables load balancing across service centers.",
        "sample_value": "SC-HN-01"
      },
      {
        "name": "priok",
        "description": "Priority level",
        "datatype": "VARCHAR(1)",
        "nullable": True,
        "business_definition": "Overall notification priority. 1=Critical, 2=High, 3=Medium, 4=Low. Drives escalation and management attention.",
        "sample_value": "2"
      },
      {
        "name": "tplnr",
        "description": "Functional location",
        "datatype": "VARCHAR(30)",
        "nullable": True,
        "business_definition": "Functional location code identifying the vehicle system or component area affected: HV-BATT=High Voltage Battery, PWR-TRN=Powertrain.",
        "sample_value": "HV-BATT"
      },
      {
        "name": "strmn",
        "description": "Start date of maintenance",
        "datatype": "DATE",
        "nullable": True,
        "business_definition": "Planned maintenance start date. Used for service center capacity planning and customer appointment scheduling.",
        "sample_value": "2025-11-26"
      }
    ]
  },
  {
    "name": "sap_t357m",
    "description": "Service Master - maintenance and service master data",
    "domain": "after_sales",
    "platform": "sap",
    "tags": [
      "AfterSales",
      "SAP",
      "MasterData"
    ],
    "columns": [
      {
        "name": "ilart",
        "description": "Maintenance activity type",
        "datatype": "VARCHAR(3)",
        "nullable": False,
        "business_definition": "Primary key for the maintenance activity type. Defines categories like PM=Preventive Maintenance, RE=Repair, IN=Inspection.",
        "sample_value": "RE"
      },
      {
        "name": "ktext",
        "description": "Description of activity type",
        "datatype": "VARCHAR(40)",
        "nullable": True,
        "business_definition": "Descriptive text for the maintenance activity type. Provides human-readable context for the service category.",
        "sample_value": "General Repair - Mechanical"
      },
      {
        "name": "tplkz",
        "description": "Indicator for task list usage",
        "datatype": "VARCHAR(1)",
        "nullable": True,
        "business_definition": "Flag indicating whether standard task lists exist for this activity type. Guides technician to predefined service procedures.",
        "sample_value": "X"
      },
      {
        "name": "matyp",
        "description": "Sold-to party required flag",
        "datatype": "VARCHAR(1)",
        "nullable": True,
        "business_definition": "Indicates whether a customer assignment is mandatory for this activity type. Critical for customer-facing service activities.",
        "sample_value": "1"
      },
      {
        "name": "wty_enabled",
        "description": "Warranty claim eligibility",
        "datatype": "BOOLEAN",
        "nullable": True,
        "business_definition": "Determines whether activities of this type can be billed under warranty. True for covered repairs, False for customer-pay services.",
        "sample_value": True
      },
      {
        "name": "standard_hours",
        "description": "Standard labor hours",
        "datatype": "DECIMAL(5,2)",
        "nullable": True,
        "business_definition": "Expected standard labor hours for this activity type. Used for technician productivity measurement and customer billing estimates.",
        "sample_value": "1.50"
      }
    ]
  },
  {
    "name": "stg_warranty_claim",
    "description": "Warranty Claim Staging - raw warranty claim submissions",
    "domain": "after_sales",
    "platform": "staging",
    "tags": [
      "AfterSales",
      "Batch",
      "Bronze"
    ],
    "columns": [
      {
        "name": "claim_id",
        "description": "Unique warranty claim identifier",
        "datatype": "VARCHAR(20)",
        "nullable": False,
        "business_definition": "Primary key for the warranty claim record. Generated from the dealer warranty system with regional prefix.",
        "sample_value": "WTY-HN-202511-00123"
      },
      {
        "name": "notification_number",
        "description": "SAP notification reference",
        "datatype": "VARCHAR(12)",
        "nullable": False,
        "business_definition": "Reference to the SAP notification number associated with the warranty claim. Cross-references service visit with warranty processing.",
        "sample_value": "NOTIF-1000012345"
      },
      {
        "name": "vin_number",
        "description": "Vehicle VIN",
        "datatype": "VARCHAR(17)",
        "nullable": False,
        "business_definition": "VIN of the vehicle for which warranty work is claimed. Validates vehicle eligibility and remaining warranty coverage.",
        "sample_value": "RLXEVF8P5RZ123456"
      },
      {
        "name": "claim_type",
        "description": "Type of warranty claim",
        "datatype": "VARCHAR(30)",
        "nullable": False,
        "business_definition": "Warranty claim category: Parts Failure, Labor Only, Goodwill, Campaign/Recall, or Battery Degradation.",
        "sample_value": "Parts Failure"
      },
      {
        "name": "claim_date",
        "description": "Date claim was submitted",
        "datatype": "DATE",
        "nullable": False,
        "business_definition": "Date the dealer submitted the warranty claim to VinFast. Used for claim processing SLA tracking.",
        "sample_value": "2025-11-28"
      },
      {
        "name": "claim_amount_vnd",
        "description": "Total claim amount in VND",
        "datatype": "DECIMAL(18,2)",
        "nullable": True,
        "business_definition": "Total amount claimed including parts and labor. Validated against VinFast warranty policy coverage limits.",
        "sample_value": "8500000.00"
      },
      {
        "name": "parts_cost_vnd",
        "description": "Cost of replaced parts",
        "datatype": "DECIMAL(18,2)",
        "nullable": True,
        "business_definition": "Cost of parts replaced under warranty. Must match the parts catalog prices for reimbursement eligibility.",
        "sample_value": "5500000.00"
      },
      {
        "name": "labor_hours",
        "description": "Labor hours claimed",
        "datatype": "DECIMAL(5,2)",
        "nullable": True,
        "business_definition": "Number of labor hours claimed. Validated against standard repair times for the specific repair operation.",
        "sample_value": "2.50"
      },
      {
        "name": "claim_status",
        "description": "Current claim processing status",
        "datatype": "VARCHAR(30)",
        "nullable": False,
        "business_definition": "Claim status: Submitted, Under Review, Approved, Partially Approved, Rejected, or Paid.",
        "sample_value": "Under Review"
      },
      {
        "name": "dealer_code",
        "description": "Dealer submitting the claim",
        "datatype": "VARCHAR(10)",
        "nullable": True,
        "business_definition": "Code of the dealer or service center submitting the claim. Used for dealer warranty performance analysis.",
        "sample_value": "D-HN-001"
      },
      {
        "name": "failure_code",
        "description": "Root cause failure code",
        "datatype": "VARCHAR(10)",
        "nullable": True,
        "business_definition": "Standardized failure code classifying the root cause: BATT-CELL-DEG=Battery Cell Degradation, MOTR-BRG=Motor Bearing Failure.",
        "sample_value": "BATT-CELL-DEG"
      }
    ]
  },
  {
    "name": "stg_service_appointment",
    "description": "Service Appointment Staging - customer service appointment bookings",
    "domain": "after_sales",
    "platform": "staging",
    "tags": [
      "AfterSales",
      "Batch",
      "Bronze"
    ],
    "columns": [
      {
        "name": "appointment_id",
        "description": "Unique appointment identifier",
        "datatype": "VARCHAR(20)",
        "nullable": False,
        "business_definition": "Primary key for the service appointment. Generated from the service center booking system.",
        "sample_value": "APP-HN-20251125-001"
      },
      {
        "name": "vin_number",
        "description": "Vehicle VIN",
        "datatype": "VARCHAR(17)",
        "nullable": False,
        "business_definition": "VIN of the vehicle scheduled for service. Links the appointment to vehicle master data and service history.",
        "sample_value": "RLXEVF8P5RZ123456"
      },
      {
        "name": "customer_id",
        "description": "Customer identifier",
        "datatype": "VARCHAR(10)",
        "nullable": False,
        "business_definition": "Customer ID for the appointment. Used for customer communication and service history tracking.",
        "sample_value": "C000012345"
      },
      {
        "name": "service_center_code",
        "description": "Service center code",
        "datatype": "VARCHAR(10)",
        "nullable": False,
        "business_definition": "Code of the service center where the appointment is booked. Maps to the service center dimension.",
        "sample_value": "SC-HN-01"
      },
      {
        "name": "appointment_date",
        "description": "Scheduled appointment date",
        "datatype": "DATE",
        "nullable": False,
        "business_definition": "Date the customer has booked for service. Used for capacity planning and bay scheduling.",
        "sample_value": "2025-11-26"
      },
      {
        "name": "appointment_time",
        "description": "Scheduled time slot",
        "datatype": "VARCHAR(10)",
        "nullable": True,
        "business_definition": "Time slot for the appointment: Morning (08:00-12:00), Afternoon (13:00-17:00), or Full Day.",
        "sample_value": "Morning"
      },
      {
        "name": "service_type",
        "description": "Type of service requested",
        "datatype": "VARCHAR(50)",
        "nullable": False,
        "business_definition": "Service category: Scheduled Maintenance, Repair, Warranty Work, Recall Campaign, or Tire/AC Check.",
        "sample_value": "Scheduled Maintenance"
      },
      {
        "name": "estimated_duration_hours",
        "description": "Estimated service duration",
        "datatype": "DECIMAL(4,1)",
        "nullable": True,
        "business_definition": "Estimated hours for the service. Used for bay allocation and customer wait time communication.",
        "sample_value": "3.0"
      },
      {
        "name": "appointment_status",
        "description": "Current appointment status",
        "datatype": "VARCHAR(20)",
        "nullable": False,
        "business_definition": "Appointment status: Booked, Confirmed, In Service, Completed, No-Show, or Cancelled.",
        "sample_value": "Confirmed"
      },
      {
        "name": "special_requests",
        "description": "Customer special requests",
        "datatype": "TEXT",
        "nullable": True,
        "business_definition": "Free-text notes from the customer about specific issues or requests for the service visit.",
        "sample_value": "Please also check the AC - not cooling properly."
      },
      {
        "name": "booking_channel",
        "description": "Channel used for booking",
        "datatype": "VARCHAR(20)",
        "nullable": True,
        "business_definition": "Channel through which the appointment was booked: App, Website, Phone, Zalo, or In-Person.",
        "sample_value": "App"
      }
    ]
  },
  {
    "name": "stg_parts_order",
    "description": "Parts Order Staging - service parts order data from service centers",
    "domain": "after_sales",
    "platform": "staging",
    "tags": [
      "AfterSales",
      "Batch",
      "Bronze"
    ],
    "columns": [
      {
        "name": "parts_order_id",
        "description": "Unique parts order identifier",
        "datatype": "VARCHAR(20)",
        "nullable": False,
        "business_definition": "Primary key for the parts order record. Generated from the service center parts ordering system.",
        "sample_value": "PO-SC-HN-202511-0050"
      },
      {
        "name": "service_center_code",
        "description": "Service center placing order",
        "datatype": "VARCHAR(10)",
        "nullable": False,
        "business_definition": "Service center code for the facility ordering parts. Used for parts demand forecasting by location.",
        "sample_value": "SC-HN-01"
      },
      {
        "name": "part_number",
        "description": "Parts catalog number",
        "datatype": "VARCHAR(20)",
        "nullable": False,
        "business_definition": "Standardized parts number from the VinFast parts catalog. Maps to dim_parts_catalog for part attributes.",
        "sample_value": "BATT-MOD-VF8-001"
      },
      {
        "name": "order_quantity",
        "description": "Quantity ordered",
        "datatype": "INTEGER",
        "nullable": False,
        "business_definition": "Number of units of the part ordered. Used for inventory demand planning and stock level monitoring.",
        "sample_value": 2
      },
      {
        "name": "order_date",
        "description": "Date of parts order",
        "datatype": "DATE",
        "nullable": False,
        "business_definition": "Date the parts order was placed. Used for order-to-delivery cycle time analysis for parts replenishment.",
        "sample_value": "2025-11-24"
      },
      {
        "name": "requested_delivery_date",
        "description": "Requested delivery date",
        "datatype": "DATE",
        "nullable": True,
        "business_definition": "Date by which the service center needs the parts. Urgent orders may require expedited shipping.",
        "sample_value": "2025-11-26"
      },
      {
        "name": "order_type",
        "description": "Type of parts order",
        "datatype": "VARCHAR(20)",
        "nullable": False,
        "business_definition": "Order type: Stock Replenishment, Emergency, Customer Special Order, or Warranty Replacement.",
        "sample_value": "Emergency"
      },
      {
        "name": "total_amount_vnd",
        "description": "Total parts order amount",
        "datatype": "DECIMAL(18,2)",
        "nullable": True,
        "business_definition": "Total cost of the parts order in VND. Used for parts inventory valuation and service center billing.",
        "sample_value": "17500000.00"
      },
      {
        "name": "order_status",
        "description": "Current parts order status",
        "datatype": "VARCHAR(20)",
        "nullable": False,
        "business_definition": "Order status: Submitted, Processing, Shipped, Partially Delivered, Delivered, or Cancelled.",
        "sample_value": "Shipped"
      },
      {
        "name": "warehouse_code",
        "description": "Source warehouse code",
        "datatype": "VARCHAR(10)",
        "nullable": True,
        "business_definition": "Code of the central or regional warehouse fulfilling the order. Used for logistics analysis.",
        "sample_value": "WH-HN-01"
      }
    ]
  },
  {
    "name": "fact_service_visit",
    "description": "Service Visit Fact - completed service visit records",
    "domain": "after_sales",
    "platform": "fact",
    "tags": [
      "AfterSales",
      "Analytics",
      "Gold"
    ],
    "columns": [
      {
        "name": "visit_id",
        "description": "Unique service visit identifier",
        "datatype": "VARCHAR(20)",
        "nullable": False,
        "business_definition": "Surrogate key for the service visit record. Captures the complete service event from check-in to check-out.",
        "sample_value": "VISIT-SC-HN-20251126-001"
      },
      {
        "name": "appointment_id",
        "description": "Source appointment identifier",
        "datatype": "VARCHAR(20)",
        "nullable": True,
        "business_definition": "Reference to the appointment that generated this service visit. Null for walk-in visits without prior booking.",
        "sample_value": "APP-HN-20251125-001"
      },
      {
        "name": "notification_number",
        "description": "SAP notification number",
        "datatype": "VARCHAR(12)",
        "nullable": False,
        "business_definition": "SAP notification number generated for the service visit. Links to notification tasks and warranty processing.",
        "sample_value": "NOTIF-1000012345"
      },
      {
        "name": "customer_key",
        "description": "Customer dimension key",
        "datatype": "VARCHAR(10)",
        "nullable": False,
        "business_definition": "Foreign key to dim_customer identifying the vehicle owner. Enables customer-centric service analysis.",
        "sample_value": "C000012345"
      },
      {
        "name": "service_center_key",
        "description": "Service center dimension key",
        "datatype": "VARCHAR(10)",
        "nullable": False,
        "business_definition": "Foreign key to dim_service_center identifying the facility that performed the service.",
        "sample_value": "SC-HN-01"
      },
      {
        "name": "technician_key",
        "description": "Technician dimension key",
        "datatype": "VARCHAR(10)",
        "nullable": True,
        "business_definition": "Foreign key to dim_technician identifying the primary technician assigned. Enables technician productivity analysis.",
        "sample_value": "TECH-HN-0042"
      },
      {
        "name": "vehicle_vin",
        "description": "Vehicle VIN",
        "datatype": "VARCHAR(17)",
        "nullable": True,
        "business_definition": "VIN of the vehicle serviced. Links service visit to vehicle production and sales history.",
        "sample_value": "RLXEVF8P5RZ123456"
      },
      {
        "name": "check_in_datetime",
        "description": "Check-in timestamp",
        "datatype": "TIMESTAMP",
        "nullable": False,
        "business_definition": "Timestamp when the vehicle was checked in at the service center. Used for wait time measurement.",
        "sample_value": "2025-11-26 08:15:00"
      },
      {
        "name": "check_out_datetime",
        "description": "Check-out timestamp",
        "datatype": "TIMESTAMP",
        "nullable": True,
        "business_definition": "Timestamp when the vehicle was ready for customer pickup. Used for total service cycle time calculation.",
        "sample_value": "2025-11-26 11:30:00"
      },
      {
        "name": "total_labor_cost_vnd",
        "description": "Total labor cost in VND",
        "datatype": "DECIMAL(18,2)",
        "nullable": True,
        "business_definition": "Total labor charges for the visit. Differentiates warranty vs customer-pay portions.",
        "sample_value": "1500000.00"
      },
      {
        "name": "total_parts_cost_vnd",
        "description": "Total parts cost in VND",
        "datatype": "DECIMAL(18,2)",
        "nullable": True,
        "business_definition": "Total cost of parts used during the service. Links to parts catalog for margin analysis.",
        "sample_value": "5500000.00"
      },
      {
        "name": "total_bill_vnd",
        "description": "Total customer bill in VND",
        "datatype": "DECIMAL(18,2)",
        "nullable": True,
        "business_definition": "Total amount billed to the customer or warranty. Sum of labor, parts, and applicable taxes.",
        "sample_value": "7000000.00"
      },
      {
        "name": "visit_purpose",
        "description": "Purpose of the service visit",
        "datatype": "VARCHAR(50)",
        "nullable": True,
        "business_definition": "Primary purpose: Scheduled Maintenance, Repair, Warranty Claim, Recall, or Accessory Installation.",
        "sample_value": "Scheduled Maintenance"
      },
      {
        "name": "odometer_km",
        "description": "Vehicle mileage at service",
        "datatype": "INTEGER",
        "nullable": True,
        "business_definition": "Odometer reading at the time of service in kilometers. Used for maintenance schedule compliance.",
        "sample_value": "15250"
      }
    ]
  },
  {
    "name": "fact_warranty_claim",
    "description": "Warranty Claim Fact - approved and paid warranty claims",
    "domain": "after_sales",
    "platform": "fact",
    "tags": [
      "AfterSales",
      "Analytics",
      "Gold",
      "Confidential"
    ],
    "columns": [
      {
        "name": "claim_fact_id",
        "description": "Unique warranty claim fact identifier",
        "datatype": "VARCHAR(20)",
        "nullable": False,
        "business_definition": "Surrogate key for the approved warranty claim. Generated after claim approval and before payment processing.",
        "sample_value": "WCLM-2025-00123"
      },
      {
        "name": "claim_id",
        "description": "Source claim identifier",
        "datatype": "VARCHAR(20)",
        "nullable": False,
        "business_definition": "Reference to the original warranty claim submission from the staging layer.",
        "sample_value": "WTY-HN-202511-00123"
      },
      {
        "name": "visit_key",
        "description": "Service visit fact key",
        "datatype": "VARCHAR(20)",
        "nullable": True,
        "business_definition": "Foreign key to fact_service_visit linking the warranty claim to the original service event.",
        "sample_value": "VISIT-SC-HN-20251126-001"
      },
      {
        "name": "customer_key",
        "description": "Customer dimension key",
        "datatype": "VARCHAR(10)",
        "nullable": False,
        "business_definition": "Foreign key to dim_customer identifying the vehicle owner filing the warranty claim.",
        "sample_value": "C000012345"
      },
      {
        "name": "service_center_key",
        "description": "Service center dimension key",
        "datatype": "VARCHAR(10)",
        "nullable": False,
        "business_definition": "Foreign key to dim_service_center identifying the facility that performed the warranty work.",
        "sample_value": "SC-HN-01"
      },
      {
        "name": "parts_catalog_key",
        "description": "Parts catalog dimension key",
        "datatype": "VARCHAR(20)",
        "nullable": True,
        "business_definition": "Foreign key to dim_parts_catalog for the primary part replaced under warranty.",
        "sample_value": "BATT-MOD-VF8-001"
      },
      {
        "name": "claim_date",
        "description": "Date claim was submitted",
        "datatype": "DATE",
        "nullable": False,
        "business_definition": "Date the original warranty claim was submitted by the dealer. Used for claim aging analysis.",
        "sample_value": "2025-11-28"
      },
      {
        "name": "approval_date",
        "description": "Date claim was approved",
        "datatype": "DATE",
        "nullable": True,
        "business_definition": "Date the warranty claim was approved by VinFast warranty team. Used to measure claim processing cycle time.",
        "sample_value": "2025-12-02"
      },
      {
        "name": "approved_amount_vnd",
        "description": "Approved claim amount in VND",
        "datatype": "DECIMAL(18,2)",
        "nullable": False,
        "business_definition": "Final approved amount after validation against warranty policy. May differ from claimed amount.",
        "sample_value": "8500000.00"
      },
      {
        "name": "warranty_type",
        "description": "Type of warranty applied",
        "datatype": "VARCHAR(30)",
        "nullable": False,
        "business_definition": "Warranty type: New Vehicle Limited Warranty, Battery Warranty, Powertrain Warranty, or Extended Service Contract.",
        "sample_value": "New Vehicle Limited Warranty"
      },
      {
        "name": "vehicle_age_days",
        "description": "Vehicle age at claim in days",
        "datatype": "INTEGER",
        "nullable": True,
        "business_definition": "Number of days between vehicle delivery date and claim date. Used for warranty incidence rate analysis by vehicle age.",
        "sample_value": 180
      },
      {
        "name": "rejection_reason",
        "description": "Rejection reason if applicable",
        "datatype": "VARCHAR(200)",
        "nullable": True,
        "business_definition": "Reason for partial or full rejection. Common reasons: expired warranty, unauthorized modification, lack of service history.",
        "sample_value": ""
      }
    ]
  },
  {
    "name": "fact_parts_inventory",
    "description": "Parts Inventory Fact - daily parts inventory levels and movements",
    "domain": "after_sales",
    "platform": "fact",
    "tags": [
      "AfterSales",
      "Analytics",
      "Gold"
    ],
    "columns": [
      {
        "name": "inventory_id",
        "description": "Unique inventory record identifier",
        "datatype": "VARCHAR(30)",
        "nullable": False,
        "business_definition": "Surrogate key for the daily parts inventory snapshot. Composite of part, warehouse, and date.",
        "sample_value": "INV-BATT-MOD-VF8-001-WH-HN-20251126"
      },
      {
        "name": "parts_catalog_key",
        "description": "Parts catalog dimension key",
        "datatype": "VARCHAR(20)",
        "nullable": False,
        "business_definition": "Foreign key to dim_parts_catalog identifying the part. Enables part-level inventory analysis.",
        "sample_value": "BATT-MOD-VF8-001"
      },
      {
        "name": "warehouse_code",
        "description": "Warehouse code",
        "datatype": "VARCHAR(10)",
        "nullable": False,
        "business_definition": "Code of the warehouse or service center where inventory is held. Used for location-level stock analysis.",
        "sample_value": "WH-HN-01"
      },
      {
        "name": "snapshot_date",
        "description": "Inventory snapshot date",
        "datatype": "DATE",
        "nullable": False,
        "business_definition": "Date of the inventory snapshot. Enables daily stock level trending and replenishment trigger calculation.",
        "sample_value": "2025-11-26"
      },
      {
        "name": "opening_balance",
        "description": "Opening stock quantity",
        "datatype": "INTEGER",
        "nullable": False,
        "business_definition": "Quantity of the part in stock at the start of the day. Baseline for daily movement tracking.",
        "sample_value": 15
      },
      {
        "name": "quantity_received",
        "description": "Quantity received during day",
        "datatype": "INTEGER",
        "nullable": True,
        "business_definition": "Quantity of parts received from suppliers or central warehouse during the day.",
        "sample_value": 5
      },
      {
        "name": "quantity_issued",
        "description": "Quantity issued or consumed",
        "datatype": "INTEGER",
        "nullable": True,
        "business_definition": "Quantity of parts issued to service bays or sold over the counter during the day.",
        "sample_value": 3
      },
      {
        "name": "closing_balance",
        "description": "Closing stock quantity",
        "datatype": "INTEGER",
        "nullable": False,
        "business_definition": "Quantity remaining in stock at end of day. Calculated as opening + received - issued.",
        "sample_value": 17
      },
      {
        "name": "reorder_point",
        "description": "Minimum stock threshold",
        "datatype": "INTEGER",
        "nullable": True,
        "business_definition": "Minimum quantity before a replenishment order is triggered. Based on historical consumption and lead time.",
        "sample_value": 10
      },
      {
        "name": "stock_status",
        "description": "Stock status",
        "datatype": "VARCHAR(20)",
        "nullable": True,
        "business_definition": "Stock status indicator: In Stock, Low Stock, Out of Stock, or Overstocked. Derived from comparing closing balance with reorder point.",
        "sample_value": "In Stock"
      }
    ]
  },
  {
    "name": "dim_service_center",
    "description": "Service Center Dimension - service facility attributes",
    "domain": "after_sales",
    "platform": "dimension",
    "tags": [
      "AfterSales",
      "MasterData",
      "Gold"
    ],
    "columns": [
      {
        "name": "service_center_key",
        "description": "Service center code",
        "datatype": "VARCHAR(10)",
        "nullable": False,
        "business_definition": "Surrogate primary key for the service center dimension. Assigned by VinFast after-sales operations for each authorized facility.",
        "sample_value": "SC-HN-01"
      },
      {
        "name": "center_name",
        "description": "Service center legal name",
        "datatype": "VARCHAR(200)",
        "nullable": False,
        "business_definition": "Registered business name of the service center as per the service agreement with VinFast.",
        "sample_value": "VinFast Service Ha Noi - Cau Giay"
      },
      {
        "name": "center_type",
        "description": "Type of service center",
        "datatype": "VARCHAR(30)",
        "nullable": True,
        "business_definition": "Classification: Authorized Dealer Service Center, Company-Owned Service Center, Mobile Service Unit, or Independent Garage.",
        "sample_value": "Authorized Dealer Service Center"
      },
      {
        "name": "city",
        "description": "City of service center",
        "datatype": "VARCHAR(50)",
        "nullable": True,
        "business_definition": "City where the service center is located. Used for geographic service coverage analysis.",
        "sample_value": "Ha Noi"
      },
      {
        "name": "region",
        "description": "Service region",
        "datatype": "VARCHAR(30)",
        "nullable": True,
        "business_definition": "Region: Northern, Central, Southern. Aligns with VinFast after-sales regional management structure.",
        "sample_value": "Northern"
      },
      {
        "name": "number_of_bays",
        "description": "Number of service bays",
        "datatype": "INTEGER",
        "nullable": True,
        "business_definition": "Total number of vehicle service bays available. Used for capacity planning and throughput analysis.",
        "sample_value": 8
      },
      {
        "name": "has_hv_certification",
        "description": "High voltage certified",
        "datatype": "BOOLEAN",
        "nullable": True,
        "business_definition": "Indicates whether the center is certified to service high-voltage electric vehicle components. Critical for EV service capability.",
        "sample_value": True
      },
      {
        "name": "opening_date",
        "description": "Service center opening date",
        "datatype": "DATE",
        "nullable": True,
        "business_definition": "Date the service center commenced operations under the VinFast network. Used for tenure analysis.",
        "sample_value": "2021-09-01"
      },
      {
        "name": "is_active",
        "description": "Active status",
        "datatype": "BOOLEAN",
        "nullable": False,
        "business_definition": "Indicates whether the service center is currently operational and authorized to perform VinFast vehicle service.",
        "sample_value": True
      },
      {
        "name": "customer_rating_avg",
        "description": "Average customer rating",
        "datatype": "DECIMAL(3,2)",
        "nullable": True,
        "business_definition": "Average customer satisfaction rating for the service center on a 1.0-5.0 scale. Used for service quality benchmarking.",
        "sample_value": "4.35"
      }
    ]
  },
  {
    "name": "dim_technician",
    "description": "Technician Dimension - service technician attributes",
    "domain": "after_sales",
    "platform": "dimension",
    "tags": [
      "AfterSales",
      "MasterData",
      "Gold"
    ],
    "columns": [
      {
        "name": "technician_key",
        "description": "Technician code",
        "datatype": "VARCHAR(10)",
        "nullable": False,
        "business_definition": "Surrogate primary key for the technician dimension. Assigned by VinFast HR for each certified service technician.",
        "sample_value": "TECH-HN-0042"
      },
      {
        "name": "technician_name",
        "description": "Technician full name",
        "datatype": "VARCHAR(100)",
        "nullable": False,
        "business_definition": "Full name of the service technician as per HR records. Used for technician assignment and performance tracking.",
        "sample_value": "Hoang Minh Tuan"
      },
      {
        "name": "certification_level",
        "description": "Technician certification grade",
        "datatype": "VARCHAR(30)",
        "nullable": True,
        "business_definition": "Certification level: Level 1 (Basic), Level 2 (Intermediate), Level 3 (Advanced), or Master Technician. Determines work authorization scope.",
        "sample_value": "Level 3"
      },
      {
        "name": "hv_certified",
        "description": "High voltage certified",
        "datatype": "BOOLEAN",
        "nullable": True,
        "business_definition": "Indicates whether the technician is certified to work on high-voltage EV systems. Required for battery and powertrain repairs.",
        "sample_value": True
      },
      {
        "name": "specialization",
        "description": "Primary specialization area",
        "datatype": "VARCHAR(50)",
        "nullable": True,
        "business_definition": "Technical specialization: HV Battery, Powertrain, Body & Paint, Electronics, AC & Thermal, or General.",
        "sample_value": "HV Battery"
      },
      {
        "name": "years_of_experience",
        "description": "Years of experience",
        "datatype": "INTEGER",
        "nullable": True,
        "business_definition": "Total years of automotive service experience. Used for workforce skill matrix analysis.",
        "sample_value": 8
      },
      {
        "name": "service_center_key",
        "description": "Assigned service center",
        "datatype": "VARCHAR(10)",
        "nullable": True,
        "business_definition": "Foreign key to dim_service_center indicating the primary service center where the technician is based.",
        "sample_value": "SC-HN-01"
      },
      {
        "name": "certification_expiry",
        "description": "Certification expiry date",
        "datatype": "DATE",
        "nullable": True,
        "business_definition": "Date when the current technician certification expires. Must be renewed before expiry to maintain work authorization.",
        "sample_value": "2026-12-31"
      }
    ]
  },
  {
    "name": "dim_parts_catalog",
    "description": "Parts Catalog Dimension - official VinFast parts catalog",
    "domain": "after_sales",
    "platform": "dimension",
    "tags": [
      "AfterSales",
      "MasterData",
      "Gold"
    ],
    "columns": [
      {
        "name": "part_number",
        "description": "Parts catalog number",
        "datatype": "VARCHAR(20)",
        "nullable": False,
        "business_definition": "Primary key for the parts catalog dimension. Standardized part number used across ordering, inventory, and billing systems.",
        "sample_value": "BATT-MOD-VF8-001"
      },
      {
        "name": "part_name",
        "description": "Part description",
        "datatype": "VARCHAR(200)",
        "nullable": False,
        "business_definition": "Descriptive name of the part in both English and Vietnamese. Used in service invoices and customer communications.",
        "sample_value": "HV Battery Module - VF8 (Moule de batterie HV)"
      },
      {
        "name": "part_category",
        "description": "Part category",
        "datatype": "VARCHAR(30)",
        "nullable": True,
        "business_definition": "Category: Battery, Motor, Electronics, Body, Interior, Suspension, Brake, or HVAC.",
        "sample_value": "Battery"
      },
      {
        "name": "unit_price_vnd",
        "description": "Standard unit price in VND",
        "datatype": "DECIMAL(18,2)",
        "nullable": True,
        "business_definition": "Standard retail price for the part in Vietnamese Dong. Used for customer billing and warranty claim valuation.",
        "sample_value": "8750000.00"
      },
      {
        "name": "warranty_coverage_months",
        "description": "Warranty period in months",
        "datatype": "INTEGER",
        "nullable": True,
        "business_definition": "Number of months the part is covered under the VinFast parts warranty. Used for warranty claim eligibility check.",
        "sample_value": 24
      },
      {
        "name": "is_critical",
        "description": "Critical part flag",
        "datatype": "BOOLEAN",
        "nullable": True,
        "business_definition": "Indicates whether the part is critical for vehicle operation and requires elevated stock levels to avoid vehicle downtime.",
        "sample_value": True
      },
      {
        "name": "supplier_part_number",
        "description": "Supplier original part number",
        "datatype": "VARCHAR(30)",
        "nullable": True,
        "business_definition": "Original manufacturer part number for cross-reference. Used for supplier quality tracking and alternative sourcing.",
        "sample_value": "SAM-850-12345-VF8"
      },
      {
        "name": "weight_kg",
        "description": "Part weight in kilograms",
        "datatype": "DECIMAL(8,2)",
        "nullable": True,
        "business_definition": "Weight of the part in kilograms. Used for shipping cost calculation and service bay lifting equipment planning.",
        "sample_value": "12.50"
      }
    ]
  },
  {
    "name": "agg_service_csat_monthly",
    "description": "Service CSAT Monthly - aggregated monthly customer satisfaction scores",
    "domain": "after_sales",
    "platform": "aggregate",
    "tags": [
      "AfterSales",
      "Analytics",
      "Gold",
      "PowerBI"
    ],
    "columns": [
      {
        "name": "service_center_key",
        "description": "Service center dimension key",
        "datatype": "VARCHAR(10)",
        "nullable": False,
        "business_definition": "Foreign key to dim_service_center. Enables service center-level CSAT analysis for network performance benchmarking.",
        "sample_value": "SC-HN-01"
      },
      {
        "name": "survey_month",
        "description": "Survey period in YYYY-MM",
        "datatype": "VARCHAR(7)",
        "nullable": False,
        "business_definition": "Calendar month for which CSAT scores are aggregated. Enables month-over-month CSAT trend analysis.",
        "sample_value": "2025-11"
      },
      {
        "name": "responses_count",
        "description": "Number of survey responses",
        "datatype": "INTEGER",
        "nullable": True,
        "business_definition": "Total number of completed customer satisfaction surveys received for the month. Used for statistical confidence assessment.",
        "sample_value": 85
      },
      {
        "name": "overall_csat_score",
        "description": "Overall CSAT score 1.0-5.0",
        "datatype": "DECIMAL(3,2)",
        "nullable": True,
        "business_definition": "Average overall satisfaction score for the service center and month. Composite across all survey dimensions.",
        "sample_value": "4.35"
      },
      {
        "name": "service_quality_score",
        "description": "Service quality dimension score",
        "datatype": "DECIMAL(3,2)",
        "nullable": True,
        "business_definition": "Average score for the service quality dimension: quality of repair, completeness of service.",
        "sample_value": "4.40"
      },
      {
        "name": "timeliness_score",
        "description": "Timeliness dimension score",
        "datatype": "DECIMAL(3,2)",
        "nullable": True,
        "business_definition": "Average score for on-time completion and adherence to promised delivery time.",
        "sample_value": "4.10"
      },
      {
        "name": "communication_score",
        "description": "Communication dimension score",
        "datatype": "DECIMAL(3,2)",
        "nullable": True,
        "business_definition": "Average score for customer communication quality, including status updates and explanations.",
        "sample_value": "4.50"
      },
      {
        "name": "facility_score",
        "description": "Facility cleanliness score",
        "datatype": "DECIMAL(3,2)",
        "nullable": True,
        "business_definition": "Average score for service center cleanliness, comfort, and amenities.",
        "sample_value": "4.30"
      },
      {
        "name": "promoter_count",
        "description": "Number of promoters (9-10)",
        "datatype": "INTEGER",
        "nullable": True,
        "business_definition": "Count of responses with score 9-10 on likelihood to recommend. Used for NPS calculation.",
        "sample_value": 52
      },
      {
        "name": "detractor_count",
        "description": "Number of detractors (0-6)",
        "datatype": "INTEGER",
        "nullable": True,
        "business_definition": "Count of responses with score 0-6 on likelihood to recommend. Used for NPS calculation.",
        "sample_value": 8
      },
      {
        "name": "net_promoter_score",
        "description": "Calculated NPS",
        "datatype": "INTEGER",
        "nullable": True,
        "business_definition": "Net Promoter Score calculated as (% Promoters - % Detractors) * 100. Range: -100 to +100.",
        "sample_value": 52
      }
    ]
  },
  {
    "name": "agg_part_availability_daily",
    "description": "Part Availability Daily - daily parts stock availability summary",
    "domain": "after_sales",
    "platform": "aggregate",
    "tags": [
      "AfterSales",
      "Analytics",
      "Gold",
      "PowerBI"
    ],
    "columns": [
      {
        "name": "warehouse_code",
        "description": "Warehouse code",
        "datatype": "VARCHAR(10)",
        "nullable": False,
        "business_definition": "Code of the warehouse or service center. Composite key with snapshot_date for daily availability tracking.",
        "sample_value": "WH-HN-01"
      },
      {
        "name": "snapshot_date",
        "description": "Inventory snapshot date",
        "datatype": "DATE",
        "nullable": False,
        "business_definition": "Date of the availability snapshot. Enables daily trend analysis of stock-out risks.",
        "sample_value": "2025-11-26"
      },
      {
        "name": "total_part_skus",
        "description": "Total unique part SKUs",
        "datatype": "INTEGER",
        "nullable": False,
        "business_definition": "Total number of distinct parts carried in the warehouse. Used for inventory breadth measurement.",
        "sample_value": 1200
      },
      {
        "name": "skus_in_stock",
        "description": "SKUs with positive stock",
        "datatype": "INTEGER",
        "nullable": False,
        "business_definition": "Number of SKUs with at least one unit in stock. Used for stock availability rate calculation.",
        "sample_value": 1150
      },
      {
        "name": "skus_out_of_stock",
        "description": "SKUs with zero stock",
        "datatype": "INTEGER",
        "nullable": True,
        "business_definition": "Number of SKUs that are completely out of stock. Target is zero for critical parts.",
        "sample_value": 15
      },
      {
        "name": "availability_percentage",
        "description": "Stock availability rate",
        "datatype": "DECIMAL(5,2)",
        "nullable": False,
        "business_definition": "Percentage of SKUs in stock: skus_in_stock / total_part_skus * 100. Target is 98%+.",
        "sample_value": "95.83"
      },
      {
        "name": "critical_parts_available",
        "description": "Critical parts in stock",
        "datatype": "INTEGER",
        "nullable": True,
        "business_definition": "Number of critical-part SKUs with positive stock. Critical parts availability is a key service KPI.",
        "sample_value": 85
      },
      {
        "name": "critical_parts_total",
        "description": "Total critical part SKUs",
        "datatype": "INTEGER",
        "nullable": True,
        "business_definition": "Total number of critical-part SKUs carried. Used to calculate critical parts availability rate.",
        "sample_value": 88
      },
      {
        "name": "critical_availability_pct",
        "description": "Critical parts availability rate",
        "datatype": "DECIMAL(5,2)",
        "nullable": True,
        "business_definition": "Percentage of critical parts in stock. Target is 100% for vehicle-down situations.",
        "sample_value": "96.59"
      }
    ]
  },
  {
    "name": "agg_technician_productivity",
    "description": "Technician Productivity Monthly - aggregated technician productivity metrics",
    "domain": "after_sales",
    "platform": "aggregate",
    "tags": [
      "AfterSales",
      "Analytics",
      "Gold",
      "PowerBI"
    ],
    "columns": [
      {
        "name": "technician_key",
        "description": "Technician dimension key",
        "datatype": "VARCHAR(10)",
        "nullable": False,
        "business_definition": "Foreign key to dim_technician enabling technician-level productivity analysis.",
        "sample_value": "TECH-HN-0042"
      },
      {
        "name": "evaluation_month",
        "description": "Evaluation period in YYYY-MM",
        "datatype": "VARCHAR(7)",
        "nullable": False,
        "business_definition": "Month for which productivity is measured. Enables month-over-month productivity trend analysis.",
        "sample_value": "2025-11"
      },
      {
        "name": "total_hours_logged",
        "description": "Total hours logged",
        "datatype": "DECIMAL(6,2)",
        "nullable": False,
        "business_definition": "Total hours the technician was clocked in and available for work at the service center.",
        "sample_value": "176.00"
      },
      {
        "name": "billable_hours",
        "description": "Billable labor hours",
        "datatype": "DECIMAL(6,2)",
        "nullable": True,
        "business_definition": "Hours spent on revenue-generating service work (customer-pay and warranty). Core productivity metric.",
        "sample_value": "140.80"
      },
      {
        "name": "non_billable_hours",
        "description": "Non-billable hours",
        "datatype": "DECIMAL(6,2)",
        "nullable": True,
        "business_definition": "Hours spent on training, meetings, tool maintenance, and idle time. Used for utilization analysis.",
        "sample_value": "35.20"
      },
      {
        "name": "utilization_rate",
        "description": "Billable hours utilization %",
        "datatype": "DECIMAL(5,2)",
        "nullable": True,
        "business_definition": "Percentage of total logged hours that were billable: billable_hours / total_hours_logged * 100.",
        "sample_value": "80.00"
      },
      {
        "name": "jobs_completed",
        "description": "Number of jobs completed",
        "datatype": "INTEGER",
        "nullable": True,
        "business_definition": "Total number of service jobs completed by the technician in the month. Volume productivity metric.",
        "sample_value": 45
      },
      {
        "name": "avg_job_duration_hours",
        "description": "Average hours per job",
        "datatype": "DECIMAL(5,2)",
        "nullable": True,
        "business_definition": "Average duration of completed jobs. Used for efficiency analysis and standard repair time validation.",
        "sample_value": "3.13"
      },
      {
        "name": "first_time_fix_rate",
        "description": "First-time fix rate %",
        "datatype": "DECIMAL(5,2)",
        "nullable": True,
        "business_definition": "Percentage of jobs completed correctly on the first attempt without requiring a return visit. Target is 95%+.",
        "sample_value": "93.50"
      },
      {
        "name": "customer_satisfaction_avg",
        "description": "Average customer rating received",
        "datatype": "DECIMAL(3,2)",
        "nullable": True,
        "business_definition": "Average customer satisfaction rating for work performed by this technician during the month.",
        "sample_value": "4.60"
      }
    ]
  },

  {
    "name": "sap_tq80",
    "description": "Notification Type - SAP notification type configuration",
    "domain": "after_sales",
    "platform": "sap",
    "tags": [
      "AfterSales",
      "SAP",
      "MasterData"
    ],
    "columns": [
      {
        "name": "qmart",
        "description": "Notification type",
        "datatype": "VARCHAR(2)",
        "nullable": False,
        "business_definition": "SAP notification type code. Primary key defining the category of quality or service notification.",
        "sample_value": "Q2"
      },
      {
        "name": "kurztext",
        "description": "Short description",
        "datatype": "VARCHAR(30)",
        "nullable": True,
        "business_definition": "Short text description of the notification type: Q2=Customer Complaint, S1=Service Request, W1=Vehicle Handover Inspection.",
        "sample_value": "Customer Complaint"
      },
      {
        "name": "herkunft",
        "description": "Notification origin indicator",
        "datatype": "VARCHAR(1)",
        "nullable": True,
        "business_definition": "Origin of the notification: 1=Customer, 2=Internal, 3=Supplier, 4=Production. Drives notification routing rules.",
        "sample_value": "1"
      },
      {
        "name": "numkr",
        "description": "Number range key",
        "datatype": "VARCHAR(2)",
        "nullable": True,
        "business_definition": "Number range interval key for automatic notification numbering. Ensures unique IDs per notification type.",
        "sample_value": "02"
      },
      {
        "name": "wty_rel",
        "description": "Warranty relevance flag",
        "datatype": "BOOLEAN",
        "nullable": True,
        "business_definition": "Indicates whether notifications of this type are eligible for warranty claim processing.",
        "sample_value": True
      }
    ]
  },
  {
    "name": "stg_customer_feedback",
    "description": "Customer Feedback Staging - raw post-service customer feedback",
    "domain": "after_sales",
    "platform": "staging",
    "tags": [
      "AfterSales",
      "Batch",
      "Bronze"
    ],
    "columns": [
      {
        "name": "feedback_id",
        "description": "Unique feedback identifier",
        "datatype": "VARCHAR(20)",
        "nullable": False,
        "business_definition": "Primary key for the customer feedback record. Generated from the survey platform.",
        "sample_value": "FB-HN-20251126-001"
      },
      {
        "name": "visit_key",
        "description": "Service visit reference",
        "datatype": "VARCHAR(20)",
        "nullable": True,
        "business_definition": "Reference to the service visit that triggered the feedback survey.",
        "sample_value": "VISIT-SC-HN-20251126-001"
      },
      {
        "name": "customer_key",
        "description": "Customer dimension key",
        "datatype": "VARCHAR(10)",
        "nullable": False,
        "business_definition": "Foreign key to dim_customer identifying the feedback provider.",
        "sample_value": "C000012345"
      },
      {
        "name": "service_center_key",
        "description": "Service center code",
        "datatype": "VARCHAR(10)",
        "nullable": False,
        "business_definition": "Service center where the service was performed. Used for center-level CSAT analysis.",
        "sample_value": "SC-HN-01"
      },
      {
        "name": "survey_date",
        "description": "Date survey completed",
        "datatype": "DATE",
        "nullable": True,
        "business_definition": "Date the customer completed the feedback survey. Used for response rate timing analysis.",
        "sample_value": "2025-11-27"
      },
      {
        "name": "overall_rating",
        "description": "Overall satisfaction 1-5",
        "datatype": "INTEGER",
        "nullable": False,
        "business_definition": "Overall satisfaction rating on a scale of 1 (Very Dissatisfied) to 5 (Very Satisfied).",
        "sample_value": 4
      },
      {
        "name": "service_quality_rating",
        "description": "Service quality rating 1-5",
        "datatype": "INTEGER",
        "nullable": True,
        "business_definition": "Rating for the quality of repair work. Used for technician performance evaluation.",
        "sample_value": 5
      },
      {
        "name": "timeliness_rating",
        "description": "Timeliness rating 1-5",
        "datatype": "INTEGER",
        "nullable": True,
        "business_definition": "Rating for whether the service was completed on time. Identifies scheduling and workflow issues.",
        "sample_value": 3
      },
      {
        "name": "likelihood_to_recommend",
        "description": "NPS score 0-10",
        "datatype": "INTEGER",
        "nullable": True,
        "business_definition": "Likelihood to recommend VinFast service to others on a 0-10 scale. Used for Net Promoter Score calculation.",
        "sample_value": 9
      },
      {
        "name": "comments",
        "description": "Free-text comments",
        "datatype": "TEXT",
        "nullable": True,
        "business_definition": "Customer comments about their service experience. Analyzed for sentiment and recurring themes.",
        "sample_value": "Excellent service, but wait time was longer than expected."
      },
      {
        "name": "feedback_channel",
        "description": "Channel of feedback submission",
        "datatype": "VARCHAR(20)",
        "nullable": True,
        "business_definition": "Channel used: SMS, Email, App, Zalo, or Phone Survey. Used for response rate optimization.",
        "sample_value": "Email"
      }
    ]
  },
  {
    "name": "fact_as_quality_inspection",
    "description": "Quality Inspection Fact - incoming and outgoing quality inspection records",
    "domain": "after_sales",
    "platform": "fact",
    "tags": [
      "AfterSales",
      "Analytics",
      "Gold"
    ],
    "columns": [
      {
        "name": "inspection_id",
        "description": "Unique inspection record identifier",
        "datatype": "VARCHAR(30)",
        "nullable": False,
        "business_definition": "Surrogate key for the quality inspection record. Links to SAP quality management module.",
        "sample_value": "INSP-20251126-001"
      },
      {
        "name": "notification_number",
        "description": "SAP notification reference",
        "datatype": "VARCHAR(12)",
        "nullable": True,
        "business_definition": "Reference to the SAP quality notification if the inspection was triggered by a customer complaint.",
        "sample_value": "NOTIF-1000012345"
      },
      {
        "name": "vin_number",
        "description": "Vehicle VIN inspected",
        "datatype": "VARCHAR(17)",
        "nullable": True,
        "business_definition": "VIN of the vehicle undergoing quality inspection. Links to vehicle production and service history.",
        "sample_value": "RLXEVF8P5RZ123456"
      },
      {
        "name": "inspection_type",
        "description": "Type of inspection",
        "datatype": "VARCHAR(30)",
        "nullable": False,
        "business_definition": "Inspection category: Pre-Delivery Inspection (PDI), Incoming Quality, Outgoing Quality, or Root Cause Analysis.",
        "sample_value": "PDI"
      },
      {
        "name": "service_center_key",
        "description": "Service center code",
        "datatype": "VARCHAR(10)",
        "nullable": True,
        "business_definition": "Service center where the inspection was performed. For PDI, this is the delivering dealer.",
        "sample_value": "SC-HN-01"
      },
      {
        "name": "inspection_date",
        "description": "Inspection date",
        "datatype": "DATE",
        "nullable": False,
        "business_definition": "Date the inspection was performed. Used for inspection cycle time analysis.",
        "sample_value": "2025-12-14"
      },
      {
        "name": "inspector_id",
        "description": "Inspector employee ID",
        "datatype": "VARCHAR(10)",
        "nullable": True,
        "business_definition": "ID of the quality inspector who performed the inspection. Tracks accountability and inspector performance.",
        "sample_value": "QC-HN-008"
      },
      {
        "name": "defects_found",
        "description": "Number of defects found",
        "datatype": "INTEGER",
        "nullable": True,
        "business_definition": "Total number of defects or non-conformities found during inspection. Key quality metric.",
        "sample_value": 1
      },
      {
        "name": "defect_codes",
        "description": "Defect code list",
        "datatype": "TEXT",
        "nullable": True,
        "business_definition": "Comma-separated list of standardized defect codes identified during inspection. Used for Pareto analysis of quality issues.",
        "sample_value": "PAINT-SCR-001, TRIM-GAP-002"
      },
      {
        "name": "inspection_result",
        "description": "Overall inspection result",
        "datatype": "VARCHAR(20)",
        "nullable": False,
        "business_definition": "Result: Pass, Pass with Observations, Fail, or Rework Required. Drives vehicle release or hold decision.",
        "sample_value": "Pass with Observations"
      },
      {
        "name": "rework_required",
        "description": "Rework needed flag",
        "datatype": "BOOLEAN",
        "nullable": True,
        "business_definition": "Indicates whether rework was required before the vehicle could be released to the customer.",
        "sample_value": True
      },
      {
        "name": "inspection_notes",
        "description": "Inspector notes",
        "datatype": "TEXT",
        "nullable": True,
        "business_definition": "Free-text observations from the inspector about quality issues found. Used for root cause analysis.",
        "sample_value": "Minor scratch on rear bumper. Buffing required before delivery."
      }
    ]
  },
  {
    "name": "agg_warranty_cost_monthly",
    "description": "Warranty Cost Monthly - aggregated monthly warranty cost and incidence",
    "domain": "after_sales",
    "platform": "aggregate",
    "tags": [
      "AfterSales",
      "Analytics",
      "Gold",
      "PowerBI"
    ],
    "columns": [
      {
        "name": "fiscal_year",
        "description": "Fiscal year",
        "datatype": "INTEGER",
        "nullable": False,
        "business_definition": "Fiscal year of the aggregated warranty data. Aligns with VinFast fiscal calendar for warranty reserve analysis.",
        "sample_value": 2025
      },
      {
        "name": "fiscal_month",
        "description": "Fiscal month (1-12)",
        "datatype": "INTEGER",
        "nullable": False,
        "business_definition": "Fiscal period number within the fiscal year. Used for month-over-month warranty cost trending.",
        "sample_value": 11
      },
      {
        "name": "total_claims_count",
        "description": "Total warranty claims filed",
        "datatype": "INTEGER",
        "nullable": False,
        "business_definition": "Total number of warranty claims filed during the period. Volume metric for warranty incidence tracking.",
        "sample_value": 156
      },
      {
        "name": "approved_claims_count",
        "description": "Approved claims count",
        "datatype": "INTEGER",
        "nullable": True,
        "business_definition": "Number of claims approved for payment. Used for approval rate analysis.",
        "sample_value": 142
      },
      {
        "name": "rejected_claims_count",
        "description": "Rejected claims count",
        "datatype": "INTEGER",
        "nullable": True,
        "business_definition": "Number of claims rejected. High rejection rate indicates dealer training needs.",
        "sample_value": 14
      },
      {
        "name": "total_claimed_amount_vnd",
        "description": "Total amount claimed",
        "datatype": "DECIMAL(18,2)",
        "nullable": False,
        "business_definition": "Sum of all warranty claims submitted in VND. Gross warranty exposure metric.",
        "sample_value": "1326000000.00"
      },
      {
        "name": "total_approved_amount_vnd",
        "description": "Total approved amount",
        "datatype": "DECIMAL(18,2)",
        "nullable": True,
        "business_definition": "Sum of all approved claim amounts after validation. Used for warranty reserve liability calculation.",
        "sample_value": "1193400000.00"
      },
      {
        "name": "avg_cost_per_claim_vnd",
        "description": "Average cost per approved claim",
        "datatype": "DECIMAL(18,2)",
        "nullable": True,
        "business_definition": "Average cost of approved warranty claims. Used for warranty cost forecasting.",
        "sample_value": "8404225.35"
      },
      {
        "name": "cost_per_vehicle_vnd",
        "description": "Warranty cost per vehicle sold",
        "datatype": "DECIMAL(18,2)",
        "nullable": True,
        "business_definition": "Total approved warranty cost divided by number of vehicles sold in the period. Key quality cost KPI.",
        "sample_value": "2983500.00"
      },
      {
        "name": "incidence_rate_pct",
        "description": "Warranty incidence rate %",
        "datatype": "DECIMAL(5,2)",
        "nullable": True,
        "business_definition": "Percentage of vehicles in the field that generated a warranty claim in the period. Target is below 3%.",
        "sample_value": "2.80"
      }
    ]
  }
]