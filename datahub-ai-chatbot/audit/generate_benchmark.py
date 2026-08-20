#!/usr/bin/env python3
"""Generate the DataAtlas Golden Benchmark from real DataHub ground truth.

Reads the audit artifacts (data_ground_truth.json, domain_semantic_map.json,
asset_relationship_map.json, retrieval_risk_map.json) and emits a strictly
grounded, stratified benchmark covering categories A-Y and CASE TYPES 1-6.

Every expected_entity / expected_asset / expected_evidence references a real
URN that exists in data_ground_truth.json. When the ground truth has no data
for a relationship (e.g. lineage), the expectation is encoded as UNKNOWN and
the abstention_condition tells the judge how to grade it.

Outputs (in audit/):
  golden_benchmark.jsonl      one JSON object per line
  golden_benchmark.md         human readable catalog
  benchmark_statistics.md     category/difficulty/domain distribution

Run:  python generate_benchmark.py [--force]
"""

from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))

GT_JSON = os.path.join(HERE, "data_ground_truth.json")
DOMAIN_JSON = os.path.join(HERE, "domain_semantic_map.json")
REL_JSON = os.path.join(HERE, "asset_relationship_map.json")
RISK_JSON = os.path.join(HERE, "retrieval_risk_map.json")

OUT_JSONL = os.path.join(HERE, "golden_benchmark.jsonl")
OUT_MD = os.path.join(HERE, "golden_benchmark.md")
OUT_STATS = os.path.join(HERE, "benchmark_statistics.md")

SCHEMA_VERSION = "1.0.0"
GEN_DATE = date.today().isoformat()


def short_name(urn: str) -> str:
    m = re.search(r"dataPlatform:\w+,(.+?),PROD", urn or "")
    return m.group(1) if m else (urn or "")


def load() -> dict:
    gt = json.load(open(GT_JSON, encoding="utf-8"))
    domain = json.load(open(DOMAIN_JSON, encoding="utf-8"))
    rel = json.load(open(REL_JSON, encoding="utf-8"))
    risk = json.load(open(RISK_JSON, encoding="utf-8"))
    return {"gt": gt, "domain": domain, "rel": rel, "risk": risk}


class BenchmarkBuilder:
    def __init__(self, data: dict):
        self.gt = data["gt"]
        self.domain = data["domain"]
        self.rel = data["rel"]
        self.risk = data["risk"]
        self.datasets = self.gt["datasets"]
        self.dashboards = self.gt["dashboards"]
        self.terms = self.gt["glossary_terms"]
        self.nodes = self.gt.get("glossary_nodes", [])
        self.ds_by_urn = {d["urn"]: d for d in self.datasets}
        self.dash_by_urn = {d["urn"]: d for d in self.dashboards}
        self.term_by_urn = {t["urn"]: t for t in self.terms}
        self.tests = []
        self._used_ids = set()

    # -- helpers ------------------------------------------------------------
    def _new_id(self, cat: str, n: int) -> str:
        tid = f"{cat}-{n:03d}"
        while tid in self._used_ids:
            n += 1
            tid = f"{cat}-{n:03d}"
        self._used_ids.add(tid)
        return tid

    def add(self, **kw):
        tid = kw["test_id"]
        base = {
            "schema_version": SCHEMA_VERSION,
            "generated_on": GEN_DATE,
            "category": kw["category"],
            "case_type": kw.get("case_type"),
            "test_id": tid,
            "difficulty": kw["difficulty"],
            "domain": kw.get("domain"),
            "user_query": kw["user_query"],
            "conversation_history": kw.get("conversation_history", []),
            "expected_intent": kw["expected_intent"],
            "expected_entities": kw.get("expected_entities", []),
            "expected_domain": kw.get("expected_domain"),
            "expected_assets": kw.get("expected_assets", []),
            "expected_evidence": kw.get("expected_evidence", []),
            "expected_tool": kw.get("expected_tool", []),
            "expected_retrieval": kw.get("expected_retrieval", []),
            "forbidden_entities": kw.get("forbidden_entities", []),
            "expected_answer_facts": kw.get("expected_answer_facts", []),
            "acceptable_answer_variants": kw.get("acceptable_answer_variants", []),
            "abstention_condition": kw.get("abstention_condition"),
            "source_metadata": kw.get("source_metadata", {}),
            "ground_truth_provenance": kw.get("ground_truth_provenance", {}),
        }
        self.tests.append(base)
        return tid

    def build_all(self):
        self.build_a()
        self.build_b()
        self.build_c()
        self.build_d()
        self.build_e()
        self.build_f()
        self.build_g()
        self.build_h()
        self.build_i()
        self.build_j()
        self.build_k()
        self.build_l()
        self.build_m()
        self.build_n()
        self.build_o()
        self.build_p()
        self.build_q()
        self.build_r()
        self.build_s()
        self.build_t()
        self.build_u()
        self.build_v()
        self.build_w()
        self.build_x()
        self.build_y()
        self.build_case1()
        self.build_case2()
        self.build_case3()
        self.build_case4()
        self.build_case5()
        self.build_case6()

    # =====================================================================
    # CATEGORY A — Exact entity lookup (exact dataset name)
    # =====================================================================
    def build_a(self):
        anchors = [
            {
                "name": "List of Vendor Master Data",
                "urn": "urn:li:dataset:(urn:li:dataPlatform:SAP,Kế toán.List of Vendor Master Data ,PROD)",
                "platform": "SAP", "domain": "CUNG ỨNG (NĐH)",
                "fact": "báo cáo danh sách dữ liệu vendor master trên SAP thuộc domain CUNG ỨNG (NĐH)",
            },
            {
                "name": "Display Plant Stock Availability",
                "urn": "urn:li:dataset:(urn:li:dataPlatform:SAP,Global MFG LOG.Display Plant Stock Availability,PROD)",
                "platform": "SAP", "domain": "SẢN XUẤT",
                "fact": "report SAP hiển thị tình trạng tồn kho theo nhà máy, domain SẢN XUẤT",
            },
            {
                "name": "Fact_Mrp_Demand",
                "urn": "urn:li:dataset:(urn:li:dataPlatform:powerbi,PFEP_Report_-_Hai_Phong_Factory.Fact_Mrp_Demand,PROD)",
                "platform": "powerbi", "domain": None,
                "fact": "dataset Fact_Mrp_Demand có các trường material_id, plant_id, Demand Q'ty",
            },
        ]
        for i, a in enumerate(anchors, 1):
            self.add(
                category="A", test_id=self._new_id("A", i), difficulty="easy",
                domain=a["domain"],
                user_query=f'Tìm dataset có tên chính xác "{a["name"]}"',
                expected_intent="exact_dataset_lookup",
                expected_entities=[a["urn"]],
                expected_domain=a["domain"],
                expected_assets=[a["urn"]],
                expected_evidence=[{"field": "name", "value": a["name"]}],
                expected_tool=["retrieve:entity_summary"],
                expected_retrieval=["keyword_entity_summary"],
                forbidden_entities=[],
                expected_answer_facts=[a["fact"]],
                acceptable_answer_variants=[f"dataset {a['name']} trên {a['platform']}"],
                source_metadata={"entity_type": "dataset", "urn": a["urn"], "platform": a["platform"]},
                ground_truth_provenance={"file": "data_ground_truth.json", "key": "datasets"},
            )

    # =====================================================================
    # CATEGORY B — Natural-language dataset discovery
    # =====================================================================
    def build_b(self):
        # lookup real GSM urn from ground truth (name contains long description)
        gsm_urn = next(
            (d["urn"] for d in self.datasets if "Warranty Cost Recovery" in d["name"]),
            "urn:li:dataset:(urn:li:dataPlatform:GSM,Chất lượng.Supplier Warranty Cost Recovery ,PROD)",
        )
        anchors = [
            {
                "q": "có báo cáo nào về chi phí bảo hành do lỗi nhà cung cấp xảy ra ngoài thị trường không?",
                "urn": gsm_urn,
                "name": "Supplier Warranty Cost Recovery",
                "facts": ["GSM", "thu hồi chi phí bảo hành do lỗi nhà cung cấp ngoài thị trường"],
            },
            {
                "q": "dataset nào phục vụ kiểm tra WIP giữa MES và SAP?",
                "urn": "urn:li:dashboard:(powerbi,reports.082bd437-991d-4469-8efc-ee953b27362e)",
                "name": "Báo cáo check WIP MES_SAP",
                "facts": ["dashboard Báo cáo check WIP MES_SAP", "domain SẢN XUẤT"],
            },
            {
                "q": "bảng tính dự báo cung cấp hàng tuần theo từng part là dataset nào?",
                "urn": "urn:li:dataset:(urn:li:dataPlatform:redshift,sap.dwh.rpt_survey_weekly_supply_capacity,PROD)",
                "name": "rpt_survey_weekly_supply_capacity",
                "facts": ["rpt_survey_weekly_supply_capacity", "redshift"],
            },
        ]
        for i, a in enumerate(anchors, 1):
            self.add(
                category="B", test_id=self._new_id("B", i), difficulty="easy",
                domain=None,
                user_query=a["q"],
                expected_intent="discover_dataset_by_description",
                expected_entities=[a["urn"]],
                expected_domain=None,
                expected_assets=[a["urn"]],
                expected_evidence=[{"field": "description", "value": "keyword-match"}],
                expected_tool=["retrieve:entity_summary", "retrieve:schema_fields"],
                expected_retrieval=["semantic_entity_summary", "keyword_entity_summary"],
                forbidden_entities=[],
                expected_answer_facts=a["facts"],
                acceptable_answer_variants=[f"không chắc chắn 100%, đề xuất {a['name']}"],
                source_metadata={"entity_type": "dataset", "urn": a["urn"]},
                ground_truth_provenance={"file": "data_ground_truth.json", "key": "datasets"},
            )

    # =====================================================================
    # CATEGORY C — Similar-name disambiguation (hard negatives)
    # =====================================================================
    def build_c(self):
        groups = [
            {
                "name": "stas",
                "urns": [
                    "urn:li:dataset:(urn:li:dataPlatform:glue,sap_external.stas,PROD)",
                    "urn:li:dataset:(urn:li:dataPlatform:redshift,sap.external.stas,PROD)",
                ],
                "platforms": ["glue", "redshift"],
            },
            {
                "name": "stko",
                "urns": [
                    "urn:li:dataset:(urn:li:dataPlatform:glue,sap_external.stko,PROD)",
                    "urn:li:dataset:(urn:li:dataPlatform:redshift,sap.external.stko,PROD)",
                ],
                "platforms": ["glue", "redshift"],
            },
            {"name": "DIM_PACKED", "count": 21},
        ]
        for i, g in enumerate(groups, 1):
            if "count" in g:
                n_platform = f"tồn tại {g['count']} dataset trùng tên {g['name']} trên các platform khác nhau"
            else:
                n_platform = f"2 dataset (glue {g['name']} và redshift {g['name']})"
            self.add(
                category="C", test_id=self._new_id("C", i), difficulty="hard",
                domain=None,
                user_query=f'có bao nhiêu dataset tên "{g["name"]}"?',
                expected_intent="disambiguate_same_name",
                expected_entities=g.get("urns", []),
                expected_domain=None,
                expected_assets=[],
                expected_evidence=[{"field": "name", "value": g["name"], "note": "multiple urns"}],
                expected_tool=["retrieve:entity_summary"],
                expected_retrieval=["keyword_entity_summary"],
                forbidden_entities=[],
                expected_answer_facts=[n_platform, "phải nêu rõ platform để phân biệt"],
                acceptable_answer_variants=["nêu số lượng dataset trùng tên và từng platform/URN"],
                abstention_condition="không được khẳng định chỉ có một dataset tên đó; phải liệt kê tất cả các bản trùng tên tìm thấy",
                source_metadata={"entity_type": "dataset", "name": g["name"]},
                ground_truth_provenance={"file": "retrieval_risk_map.json", "key": "same_name_datasets"},
            )

    # =====================================================================
    # CATEGORY D — Domain-scoped glossary (clear single definition)
    # =====================================================================
    def build_d(self):
        terms = [
            {
                "name": "Nhu cầu linh kiện",
                "urn": "urn:li:glossaryTerm:72c69954-8944-4e58-9af2-328502dc9390",
                "domain": "SẢN XUẤT",
                "facts": ["Số lượng linh kiện/NVL cần để đáp ứng kế hoạch sản xuất", "MRP tính toán", "dựa trên MPS, BOM, tồn kho, thời gian cung ứng"],
            },
            {
                "name": "Số lượng linh kiện hết hạn",
                "urn": "urn:li:glossaryTerm:e5148b86-d3fb-4af8-860e-cd075c0a1527",
                "domain": "SẢN XUẤT",
                "facts": ["linh kiện hết hạn", "gắn với v_fact_monthly_inventory_hsd_summarize"],
            },
        ]
        for i, t in enumerate(terms, 1):
            self.add(
                category="D", test_id=self._new_id("D", i), difficulty="easy",
                domain=t["domain"],
                user_query=f'"{t["name"]}" là gì?',
                expected_intent="glossary_definition",
                expected_entities=[t["urn"]],
                expected_domain=t["domain"],
                expected_assets=[t["urn"]],
                expected_evidence=[{"field": "description", "urn": t["urn"]}],
                expected_tool=["retrieve:term_definition"],
                expected_retrieval=["keyword_term_definition", "semantic_term_definition"],
                forbidden_entities=[],
                expected_answer_facts=t["facts"],
                acceptable_answer_variants=[f"định nghĩa của {t['name']} theo DataHub"],
                source_metadata={"entity_type": "glossary_term", "urn": t["urn"]},
                ground_truth_provenance={"file": "data_ground_truth.json", "key": "glossary_terms"},
            )

    # =====================================================================
    # CATEGORY E — Same term / different definition (ambiguity)
    # =====================================================================
    def build_e(self):
        cov = {
            "urn1": "urn:li:glossaryTerm:7081e281-2d7b-4f66-9b1b-c31cdb66cc1b",
            "urn2": "urn:li:glossaryTerm:e26f9aeb-b1f9-4553-9eac-f9137f915e4a",
        }
        self.add(
            category="E", test_id=self._new_id("E", 1), difficulty="hard",
            domain=None,
            user_query='"Coverage Date" là gì?',
            expected_intent="glossary_definition",
            expected_entities=[cov["urn1"], cov["urn2"]],
            expected_domain=None,
            expected_assets=[cov["urn1"], cov["urn2"]],
            expected_evidence=[{"field": "name", "value": "Coverage Date", "note": "2 URN, 2 định nghĩa khác nhau"}],
            expected_tool=["retrieve:term_definition"],
            expected_retrieval=["keyword_term_definition"],
            forbidden_entities=[],
            expected_answer_facts=[
                "có 2 định nghĩa Coverage Date khác nhau trong DataHub",
                "định nghĩa 1: số ngày tồn kho hiện tại đáp ứng nhu cầu sản xuất",
                "định nghĩa 2: số ngày làm việc mà tồn kho + Git vẫn đủ nhu cầu sản xuất",
            ],
            acceptable_answer_variants=["liệt kê cả 2 định nghĩa kèm URN, yêu cầu làm rõ ngữ cảnh"],
            abstention_condition="không được trả lời một định nghĩa duy nhất; phải nêu cả 2 URN",
            source_metadata={"entity_type": "glossary_term", "name": "Coverage Date", "urns": [cov["urn1"], cov["urn2"]]},
            ground_truth_provenance={"file": "retrieval_risk_map.json", "key": "duplicate_term_names"},
        )

    # =====================================================================
    # CATEGORY F — Dataset <-> glossary linkage
    # =====================================================================
    def build_f(self):
        edges = [
            {
                "term": "BOM (Bill of Materials)",
                "term_urn": "urn:li:glossaryTerm:7137e03e-59d5-485c-b0ba-82957e0b6b23",
                "ds_name": "VF_VN_DEX_PLANNING.v_ec1v_2025",
                "ds_urn": "urn:li:dataset:(urn:li:dataPlatform:powerbi,VF_VN_DEX_PLANNING.v_ec1v_2025,PROD)",
            },
            {
                "term": "Nhu cầu linh kiện",
                "term_urn": "urn:li:glossaryTerm:72c69954-8944-4e58-9af2-328502dc9390",
                "ds_name": "VF_VN_DEX_PLANNING.mrp_stock_req",
                "ds_urn": "urn:li:dataset:(urn:li:dataPlatform:powerbi,VF_VN_DEX_PLANNING.mrp_stock_req,PROD)",
            },
            {
                "term": "PII",
                "term_urn": "urn:li:glossaryTerm:PII",
                "ds_name": "dms.stg.stg_contact",
                "ds_urn": "urn:li:dataset:(urn:li:dataPlatform:redshift,dms.stg.stg_contact,PROD)",
            },
        ]
        for i, e in enumerate(edges, 1):
            self.add(
                category="F", test_id=self._new_id("F", i), difficulty="medium",
                domain=None,
                user_query=f'dataset "{e["ds_name"]}" gắn với glossary term nào?',
                expected_intent="dataset_glossary_linkage",
                expected_entities=[e["ds_urn"], e["term_urn"]],
                expected_domain=None,
                expected_assets=[e["ds_urn"], e["term_urn"]],
                expected_evidence=[{"field": "glossary_term_urns", "urn": e["ds_urn"], "value": [e["term_urn"]]}],
                expected_tool=["retrieve:entity_summary"],
                expected_retrieval=["keyword_entity_summary"],
                forbidden_entities=[],
                expected_answer_facts=[f"dataset {e['ds_name']} gắn với term {e['term']}"],
                acceptable_answer_variants=[f"term {e['term']}"],
                source_metadata={"entity_type": "dataset", "urn": e["ds_urn"]},
                ground_truth_provenance={"file": "asset_relationship_map.json", "key": "dataset_to_glossary_term"},
            )

    # =====================================================================
    # CATEGORY G — Column / field definition
    # =====================================================================
    def build_g(self):
        cols = [
            {
                "ds_name": "dim_businessunit",
                "ds_urn": "urn:li:dataset:(urn:li:dataPlatform:powerbi,1._Awareness.dim_businessunit,PROD)",
                "field": "bu_short_name",
                "facts": ["trường bu_short_name tồn tại trong dim_businessunit", "tên viết tắt của đơn vị kinh doanh"],
            },
            {
                "ds_name": "fact_sale_orders",
                "ds_urn": "urn:li:dataset:(urn:li:dataPlatform:powerbi,1._Awareness.fact_sale_orders,PROD)",
                "field": "sod_total_amount",
                "facts": ["trường sod_total_amount tồn tại trong fact_sale_orders", "tổng giá trị đơn bán"],
            },
            {
                "ds_name": "dim_plant",
                "ds_urn": "urn:li:dataset:(urn:li:dataPlatform:powerbi,Báo_cáo_KQKD_Hậu_mãi.dim_plant,PROD)",
                "field": "is_manufacturing",
                "facts": ["trường is_manufacturing tồn tại trong dim_plant", "đánh dấu nhà máy sản xuất"],
            },
        ]
        for i, c in enumerate(cols, 1):
            self.add(
                category="G", test_id=self._new_id("G", i), difficulty="medium",
                domain=None,
                user_query=f'trong dataset "{c["ds_name"]}" có trường "{c["field"]}" nghĩa là gì?',
                expected_intent="column_definition",
                expected_entities=[c["ds_urn"]],
                expected_domain=None,
                expected_assets=[c["ds_urn"]],
                expected_evidence=[{"field": "schema_fields", "urn": c["ds_urn"], "value": c["field"]}],
                expected_tool=["retrieve:schema_fields"],
                expected_retrieval=["keyword_schema_fields"],
                forbidden_entities=[],
                expected_answer_facts=c["facts"],
                acceptable_answer_variants=["xác nhận trường tồn tại và mô tả ý nghĩa theo tên trường"],
                abstention_condition="nếu không có mô tả trường, phải nêu UNKNOWN thay vì bịa ý nghĩa",
                source_metadata={"entity_type": "dataset", "urn": c["ds_urn"], "field": c["field"]},
                ground_truth_provenance={"file": "data_ground_truth.json", "key": "datasets.payload.schema_fields"},
            )

    # =====================================================================
    # CATEGORY H — Report / dashboard discovery
    # =====================================================================
    def build_h(self):
        reports = [
            {
                "name": "Report_Supply_Capacity",
                "urn": "urn:li:dashboard:(powerbi,reports.08875c53-cbd5-4435-aafd-b31e4e6940a8)",
                "domain": "LOGISTIC",
                "facts": ["dashboard Report_Supply_Capacity", "domain LOGISTIC"],
            },
            {
                "name": "PFEP Report - Hai Phong Factory",
                "urn": "urn:li:dashboard:(powerbi,reports.1e74bc9a-cf99-49cf-9e44-6f25f4b4ee6a)",
                "domain": "LOGISTIC",
                "facts": ["dashboard PFEP Report - Hai Phong Factory", "domain LOGISTIC"],
            },
            {
                "name": "VINFAST_Report12 PFEP",
                "urn": "urn:li:dashboard:(powerbi,reports.5346a967-c65e-4c9c-b470-3921f3f735db)",
                "domain": "SẢN XUẤT",
                "facts": ["dashboard VINFAST_Report12 PFEP", "domain SẢN XUẤT"],
            },
        ]
        for i, r in enumerate(reports, 1):
            self.add(
                category="H", test_id=self._new_id("H", i), difficulty="easy",
                domain=r["domain"],
                user_query=f'có dashboard/report nào tên "{r["name"]}"?',
                expected_intent="dashboard_lookup",
                expected_entities=[r["urn"]],
                expected_domain=r["domain"],
                expected_assets=[r["urn"]],
                expected_evidence=[{"field": "name", "value": r["name"]}],
                expected_tool=["retrieve:dashboard_summary"],
                expected_retrieval=["keyword_dashboard_summary"],
                forbidden_entities=[],
                expected_answer_facts=r["facts"],
                acceptable_answer_variants=[f"dashboard {r['name']} thuộc domain {r['domain']}"],
                source_metadata={"entity_type": "dashboard", "urn": r["urn"]},
                ground_truth_provenance={"file": "data_ground_truth.json", "key": "dashboards"},
            )

    # =====================================================================
    # CATEGORY I — Report description / documentation evidence
    # =====================================================================
    def build_i(self):
        dash = {"name": "R_Báo cáo đối soát hoá đơn DMS - SAP", "urn": None}
        for d in self.dashboards:
            if d["name"].strip() == dash["name"]:
                dash["urn"] = d["urn"]
                break
        self.add(
            category="I", test_id=self._new_id("I", 1), difficulty="medium",
            domain=None,
            user_query=f'mô tả chi tiết của dashboard "{dash["name"]}"?',
            expected_intent="dashboard_description",
            expected_entities=[dash["urn"]] if dash["urn"] else [],
            expected_domain=None,
            expected_assets=[dash["urn"]] if dash["urn"] else [],
            expected_evidence=[{"field": "description", "urn": dash["urn"]}] if dash["urn"] else [],
            expected_tool=["retrieve:dashboard_summary"],
            expected_retrieval=["keyword_dashboard_summary"],
            forbidden_entities=[],
            expected_answer_facts=["dashboard chỉ có tên trùng nội dung mô tả, không có mô tả riêng biệt"],
            acceptable_answer_variants=["nêu rõ dashboard không có mô tả chi tiết ngoài tên"],
            abstention_condition="không bịa nội dung báo cáo khi không có description",
            source_metadata={"entity_type": "dashboard", "name": dash["name"]},
            ground_truth_provenance={"file": "data_ground_truth.json", "key": "dashboards.description"},
        )

    # =====================================================================
    # CATEGORY J — Report <-> dataset inputs (lineage UNKNOWN)
    # =====================================================================
    def build_j(self):
        dash = {
            "name": "Report_Supply_Capacity",
            "urn": "urn:li:dashboard:(powerbi,reports.08875c53-cbd5-4435-aafd-b31e4e6940a8)",
        }
        self.add(
            category="J", test_id=self._new_id("J", 1), difficulty="hard",
            domain="LOGISTIC",
            user_query=f'dashboard "{dash["name"]}" dùng những dataset nào làm nguồn?',
            expected_intent="report_dataset_lineage",
            expected_entities=[dash["urn"]],
            expected_domain="LOGISTIC",
            expected_assets=[],
            expected_evidence=[{"field": "upstream_urns", "urn": dash["urn"], "value": []}],
            expected_tool=["retrieve:dashboard_summary", "retrieve:entity_summary"],
            expected_retrieval=["keyword_dashboard_summary"],
            forbidden_entities=[],
            expected_answer_facts=["không có dữ liệu lineage dashboard→dataset trong DataHub"],
            acceptable_answer_variants=["trả lời UNKNOWN, đề xuất dataset liên quan nhưng phải gắn nhãn suy đoán"],
            abstention_condition="không khẳng định dataset nguồn khi upstream=0; chỉ đề xuất kèm mức độ chắc chắn thấp",
            source_metadata={"entity_type": "dashboard", "urn": dash["urn"]},
            ground_truth_provenance={"file": "asset_relationship_map.json", "key": "dashboard_to_dataset_input"},
        )

    # =====================================================================
    # CATEGORY K — Metric / formula explanation
    # =====================================================================
    def build_k(self):
        term = {
            "name": "Tính toán “Demand of all build phases per variant”",
            "urn": "urn:li:glossaryTerm:42dae407-ae65-4d6b-a9c9-6e4925d0c70c",
            "formula": "Demand (per Variant) = Sum(BOM Qty × Order Qty) WHERE Order Status = OPEN/IN PROGRESS FOR ALL Build Phases",
            "facts": ["công thức: Demand (per Variant) = Sum(BOM Qty × Order Qty)", "chỉ tính đơn hàng OPEN/IN PROGRESS"],
        }
        self.add(
            category="K", test_id=self._new_id("K", 1), difficulty="medium",
            domain="SẢN XUẤT",
            user_query=f'"{term["name"]}" tính như thế nào?',
            expected_intent="formula_explanation",
            expected_entities=[term["urn"]],
            expected_domain="SẢN XUẤT",
            expected_assets=[term["urn"]],
            expected_evidence=[{"field": "description", "urn": term["urn"], "value": term["formula"]}],
            expected_tool=["retrieve:term_definition"],
            expected_retrieval=["keyword_term_definition"],
            forbidden_entities=[],
            expected_answer_facts=term["facts"],
            acceptable_answer_variants=["trình bày công thức + điều kiện WHERE"],
            source_metadata={"entity_type": "glossary_term", "urn": term["urn"]},
            ground_truth_provenance={"file": "data_ground_truth.json", "key": "glossary_terms.description"},
        )

    # =====================================================================
    # CATEGORY L — Metric -> formula (Coverage Date dual definition)
    # =====================================================================
    def build_l(self):
        cov = {
            "urn1": "urn:li:glossaryTerm:7081e281-2d7b-4f66-9b1b-c31cdb66cc1b",
            "urn2": "urn:li:glossaryTerm:e26f9aeb-b1f9-4553-9eac-f9137f915e4a",
        }
        self.add(
            category="L", test_id=self._new_id("L", 1), difficulty="hard",
            domain=None,
            user_query="công thức của Coverage Date như trong dữ liệu là gì?",
            expected_intent="metric_formula",
            expected_entities=[cov["urn1"], cov["urn2"]],
            expected_domain=None,
            expected_assets=[cov["urn1"], cov["urn2"]],
            expected_evidence=[
                {"field": "description", "urn": cov["urn1"], "note": "định nghĩa 1"},
                {"field": "description", "urn": cov["urn2"], "note": "định nghĩa 2"},
            ],
            expected_tool=["retrieve:term_definition"],
            expected_retrieval=["keyword_term_definition"],
            forbidden_entities=[],
            expected_answer_facts=["có 2 định nghĩa Coverage Date; định nghĩa 2 nêu rõ cơ chế tính (tồn kho + Git, LOB ≥ 0)"],
            acceptable_answer_variants=["nêu cả 2 định nghĩa và chỉ ra định nghĩa nào có công thức rõ"],
            abstention_condition="không bịa công thức số học không có trong mô tả",
            source_metadata={"entity_type": "glossary_term", "urns": [cov["urn1"], cov["urn2"]]},
            ground_truth_provenance={"file": "data_ground_truth.json", "key": "glossary_terms.description"},
        )

    # =====================================================================
    # CATEGORY M — Report lineage trace (UNKNOWN)
    # =====================================================================
    def build_m(self):
        dash = {
            "name": "PFEP Report - Hai Phong Factory",
            "urn": "urn:li:dashboard:(powerbi,reports.1e74bc9a-cf99-49cf-9e44-6f25f4b4ee6a)",
        }
        self.add(
            category="M", test_id=self._new_id("M", 1), difficulty="hard",
            domain="LOGISTIC",
            user_query=f'trace lineage của dashboard "{dash["name"]}" từ nguồn gốc?',
            expected_intent="report_lineage_trace",
            expected_entities=[dash["urn"]],
            expected_domain="LOGISTIC",
            expected_assets=[],
            expected_evidence=[{"field": "upstream_urns", "urn": dash["urn"], "value": []}],
            expected_tool=["retrieve:dashboard_summary", "retrieve:entity_summary", "retrieve:lineage"],
            expected_retrieval=["keyword_dashboard_summary"],
            forbidden_entities=[],
            expected_answer_facts=["không có lineage trong DataHub; chỉ có thể trả lời UNKNOWN hoặc đề xuất tên dataset cùng tên báo cáo (Fact_Mrp_Demand) kèm nhãn suy đoán"],
            acceptable_answer_variants=["UNKNOWN + liệt kê dataset có tên chứa 'PFEP Report - Hai Phong' nếu có"],
            abstention_condition="không được dựng chuỗi lineage giả khi upstream=0",
            source_metadata={"entity_type": "dashboard", "urn": dash["urn"]},
            ground_truth_provenance={"file": "asset_relationship_map.json", "key": "dashboard_to_dataset_input"},
        )

    # =====================================================================
    # CATEGORY N — Dataset lineage (UNKNOWN)
    # =====================================================================
    def build_n(self):
        ds = {
            "name": "fact_mcn_pfep",
            "urn": "urn:li:dataset:(urn:li:dataPlatform:redshift,dataanalyticsprd.dwh.fact_mcn_pfep,PROD)",
        }
        self.add(
            category="N", test_id=self._new_id("N", 1), difficulty="hard",
            domain="SẢN XUẤT",
            user_query=f'upstream/downstream của dataset "{ds["name"]}" là gì?',
            expected_intent="dataset_lineage",
            expected_entities=[ds["urn"]],
            expected_domain="SẢN XUẤT",
            expected_assets=[],
            expected_evidence=[
                {"field": "upstream_urns", "urn": ds["urn"], "value": []},
                {"field": "downstream_urns", "urn": ds["urn"], "value": []},
            ],
            expected_tool=["retrieve:entity_summary", "retrieve:lineage"],
            expected_retrieval=["keyword_entity_summary"],
            forbidden_entities=[],
            expected_answer_facts=["không có lineage dataset trong DataHub"],
            acceptable_answer_variants=["trả lời UNKNOWN"],
            abstention_condition="không bịa upstream/downstream",
            source_metadata={"entity_type": "dataset", "urn": ds["urn"]},
            ground_truth_provenance={"file": "asset_relationship_map.json", "key": "dataset_to_dataset_upstream/downstream"},
        )

    # =====================================================================
    # CATEGORY O — Raw / source data discovery
    # =====================================================================
    def build_o(self):
        anchors = [
            {
                "q": "dataset thô (staging) nào chứa dữ liệu đơn hàng bán?",
                "name": "stg_lead",
                "urn": "urn:li:dataset:(urn:li:dataPlatform:redshift,dms.stg.stg_lead,PROD)",
                "platform": "redshift",
                "facts": ["stg_lead", "redshift dms.stg", "45 trường: leadid, leadsourcecode, firstname, fullname..."],
            },
            {
                "q": "dataset staging vật tư (material) trong DMS ở đâu?",
                "name": "stg_material",
                "urn": "urn:li:dataset:(urn:li:dataPlatform:redshift,dms.stg.stg_material,PROD)",
                "platform": "redshift",
                "facts": ["stg_material", "redshift dms.stg"],
            },
        ]
        for i, a in enumerate(anchors, 1):
            self.add(
                category="O", test_id=self._new_id("O", i), difficulty="medium",
                domain=None,
                user_query=a["q"],
                expected_intent="raw_source_discovery",
                expected_entities=[a["urn"]],
                expected_domain=None,
                expected_assets=[a["urn"]],
                expected_evidence=[{"field": "name", "value": a["name"], "note": "prefix stg_ = staging"}],
                expected_tool=["retrieve:entity_summary", "retrieve:schema_fields"],
                expected_retrieval=["keyword_entity_summary"],
                forbidden_entities=[],
                expected_answer_facts=a["facts"],
                acceptable_answer_variants=[f"đề xuất {a['name']} trên {a['platform']}"],
                source_metadata={"entity_type": "dataset", "urn": a["urn"]},
                ground_truth_provenance={"file": "data_ground_truth.json", "key": "datasets"},
            )

    # =====================================================================
    # CATEGORY P — Multi-turn context
    # =====================================================================
    def build_p(self):
        self.add(
            category="P", test_id=self._new_id("P", 1), difficulty="medium",
            domain=None,
            user_query="nó có trường nào?",
            conversation_history=[
                {"role": "user", "content": "tìm dataset Fact_Mrp_Demand"},
                {"role": "assistant", "content": "Fact_Mrp_Demand (powerbi, PFEP_Report_-_Hai_Phong_Factory)"},
            ],
            expected_intent="column_listing_in_context",
            expected_entities=["urn:li:dataset:(urn:li:dataPlatform:powerbi,PFEP_Report_-_Hai_Phong_Factory.Fact_Mrp_Demand,PROD)"],
            expected_domain=None,
            expected_assets=["urn:li:dataset:(urn:li:dataPlatform:powerbi,PFEP_Report_-_Hai_Phong_Factory.Fact_Mrp_Demand,PROD)"],
            expected_evidence=[{"field": "schema_fields", "note": "material_id, plant_id, Year, Mat-Plant, Refresh_Date, Material, Month, Demand Q'ty"}],
            expected_tool=["retrieve:schema_fields"],
            expected_retrieval=["keyword_schema_fields"],
            forbidden_entities=[],
            expected_answer_facts=["Fact_Mrp_Demand có 8 trường: material_id, plant_id, Year, Mat-Plant, Refresh_Date, Material, Month, Demand Q'ty"],
            acceptable_answer_variants=["liệt kê các trường của Fact_Mrp_Demand"],
            source_metadata={"entity_type": "dataset", "urn": "urn:li:dataset:(urn:li:dataPlatform:powerbi,PFEP_Report_-_Hai_Phong_Factory.Fact_Mrp_Demand,PROD)"},
            ground_truth_provenance={"file": "data_ground_truth.json", "key": "datasets.payload.schema_fields"},
        )

    # =====================================================================
    # CATEGORY Q — Entity switching (same term, different referent)
    # =====================================================================
    def build_q(self):
        self.add(
            category="Q", test_id=self._new_id("Q", 1), difficulty="hard",
            domain=None,
            user_query="còn dashboard nào về PFEP cho nhà máy khác không?",
            conversation_history=[
                {"role": "user", "content": "PFEP là gì?"},
                {"role": "assistant", "content": "PFEP (Plan for Every Part)..."},
            ],
            expected_intent="entity_switch_glossary_to_dashboard",
            expected_entities=[
                "urn:li:dashboard:(powerbi,reports.1e74bc9a-cf99-49cf-9e44-6f25f4b4ee6a)",
                "urn:li:dashboard:(powerbi,reports.08875c53-cbd5-4435-aafd-b31e4e6940a8)",
            ],
            expected_domain=None,
            expected_assets=[
                "urn:li:dashboard:(powerbi,reports.1e74bc9a-cf99-49cf-9e44-6f25f4b4ee6a)",
                "urn:li:dashboard:(powerbi,reports.08875c53-cbd5-4435-aafd-b31e4e6940a8)",
            ],
            expected_evidence=[{"field": "name", "note": "PFEP Report - Hai Phong Factory, Report_Supply_Capacity, VINFAST_Report12 PFEP, PFEP, PFEP_INDO..."}],
            expected_tool=["retrieve:dashboard_summary"],
            expected_retrieval=["keyword_dashboard_summary"],
            forbidden_entities=[],
            expected_answer_facts=["các dashboard PFEP khác: PFEP Report - Hai Phong Factory, Report_Supply_Capacity, VINFAST_Report12 PFEP, PFEP, PFEP_INDO, PFEP_INDIA"],
            acceptable_answer_variants=["liệt kê ít nhất 2 dashboard PFEP khác với ngữ cảnh trước"],
            source_metadata={"entity_type": "dashboard", "note": "switch từ glossary_term sang dashboard"},
            ground_truth_provenance={"file": "data_ground_truth.json", "key": "dashboards.name"},
        )

    # =====================================================================
    # CATEGORY R — Multi-entity comparison
    # =====================================================================
    def build_r(self):
        self.add(
            category="R", test_id=self._new_id("R", 1), difficulty="hard",
            domain=None,
            user_query="so sánh số trường giữa Fact_Mrp_Demand và dim_vehicle_model",
            expected_intent="multi_entity_comparison",
            expected_entities=[
                "urn:li:dataset:(urn:li:dataPlatform:powerbi,PFEP_Report_-_Hai_Phong_Factory.Fact_Mrp_Demand,PROD)",
                "urn:li:dataset:(urn:li:dataPlatform:powerbi,7_Báo_cáo_kho_vận.dim_vehicle_model,PROD)",
            ],
            expected_domain=None,
            expected_assets=[
                "urn:li:dataset:(urn:li:dataPlatform:powerbi,PFEP_Report_-_Hai_Phong_Factory.Fact_Mrp_Demand,PROD)",
                "urn:li:dataset:(urn:li:dataPlatform:powerbi,7_Báo_cáo_kho_vận.dim_vehicle_model,PROD)",
            ],
            expected_evidence=[
                {"field": "schema_field_count", "value": "8 (Fact_Mrp_Demand)"},
                {"field": "schema_field_count", "value": "7 (dim_vehicle_model)"},
            ],
            expected_tool=["retrieve:schema_fields"],
            expected_retrieval=["keyword_schema_fields"],
            forbidden_entities=[],
            expected_answer_facts=["Fact_Mrp_Demand có 8 trường, dim_vehicle_model có 7 trường"],
            acceptable_answer_variants=["so sánh số lượng trường và mô tả ngắn từng dataset"],
            source_metadata={"entity_type": "dataset", "urns": [
                "urn:li:dataset:(urn:li:dataPlatform:powerbi,PFEP_Report_-_Hai_Phong_Factory.Fact_Mrp_Demand,PROD)",
                "urn:li:dataset:(urn:li:dataPlatform:powerbi,7_Báo_cáo_kho_vận.dim_vehicle_model,PROD)",
            ]},
            ground_truth_provenance={"file": "data_ground_truth.json", "key": "datasets.schema_field_count"},
        )

    # =====================================================================
    # CATEGORY S — Multi-question decomposition
    # =====================================================================
    def build_s(self):
        self.add(
            category="S", test_id=self._new_id("S", 1), difficulty="hard",
            domain=None,
            user_query="PFEP là gì và dashboard PFEP nào thuộc domain LOGISTIC?",
            expected_intent="multi_question_decomposition",
            expected_entities=[
                "urn:li:glossaryTerm:7f04e765-927e-4272-a16c-843a06110280",
                "urn:li:dashboard:(powerbi,reports.1e74bc9a-cf99-49cf-9e44-6f25f4b4ee6a)",
                "urn:li:dashboard:(powerbi,reports.08875c53-cbd5-4435-aafd-b31e4e6940a8)",
            ],
            expected_domain=None,
            expected_assets=[
                "urn:li:glossaryTerm:7f04e765-927e-4272-a16c-843a06110280",
                "urn:li:dashboard:(powerbi,reports.1e74bc9a-cf99-49cf-9e44-6f25f4b4ee6a)",
                "urn:li:dashboard:(powerbi,reports.08875c53-cbd5-4435-aafd-b31e4e6940a8)",
            ],
            expected_evidence=[
                {"field": "description", "note": "định nghĩa PFEP"},
                {"field": "domain", "value": "LOGISTIC", "note": "dashboard"},
            ],
            expected_tool=["retrieve:term_definition", "retrieve:dashboard_summary"],
            expected_retrieval=["keyword_term_definition", "keyword_dashboard_summary"],
            forbidden_entities=[],
            expected_answer_facts=["PFEP = Plan for Every Part; dashboard LOGISTIC: PFEP Report - Hai Phong Factory, PFEP Report - Indonesia Factory, PFEP Report - India Factory, Report_Supply_Capacity, PFEP"],
            acceptable_answer_variants=["trả lời cả 2 phần: định nghĩa + danh sách dashboard"],
            source_metadata={"entity_type": "mixed"},
            ground_truth_provenance={"file": "data_ground_truth.json", "key": "glossary_terms + dashboards"},
        )

    # =====================================================================
    # CATEGORY T — Complex end-to-end task
    # =====================================================================
    def build_t(self):
        self.add(
            category="T", test_id=self._new_id("T", 1), difficulty="hard",
            domain="SẢN XUẤT",
            user_query="tìm dataset tính nhu cầu linh kiện, cho biết trường chính và term định nghĩa liên quan",
            expected_intent="end_to_end_dataset_term_field",
            expected_entities=[
                "urn:li:dataset:(urn:li:dataPlatform:powerbi,VF_VN_DEX_PLANNING.mrp_stock_req,PROD)",
                "urn:li:glossaryTerm:72c69954-8944-4e58-9af2-328502dc9390",
            ],
            expected_domain="SẢN XUẤT",
            expected_assets=[
                "urn:li:dataset:(urn:li:dataPlatform:powerbi,VF_VN_DEX_PLANNING.mrp_stock_req,PROD)",
                "urn:li:glossaryTerm:72c69954-8944-4e58-9af2-328502dc9390",
            ],
            expected_evidence=[
                {"field": "glossary_term_urns", "value": ["urn:li:glossaryTerm:72c69954-8944-4e58-9af2-328502dc9390"]},
                {"field": "description", "note": "Nhu cầu linh kiện do MRP tính"},
            ],
            expected_tool=["retrieve:entity_summary", "retrieve:schema_fields", "retrieve:term_definition"],
            expected_retrieval=["keyword_entity_summary", "semantic_term_definition"],
            forbidden_entities=[],
            expected_answer_facts=["dataset mrp_stock_req gắn term 'Nhu cầu linh kiện' và MRP (Material Requirements Planning)"],
            acceptable_answer_variants=["nêu dataset + term + trường tiêu biểu"],
            source_metadata={"entity_type": "mixed"},
            ground_truth_provenance={"file": "asset_relationship_map.json", "key": "dataset_to_glossary_term"},
        )

    # =====================================================================
    # CATEGORY U — Evidence direct / indirect / UNKNOWN
    # =====================================================================
    def build_u(self):
        self.add(
            category="U", test_id=self._new_id("U", 1), difficulty="hard",
            domain=None,
            user_query="dataset chứa thông tin khách hàng (PII) nào có gắn term về bảo mật?",
            expected_intent="evidence_direct_indirect",
            expected_entities=[
                "urn:li:dataset:(urn:li:dataPlatform:redshift,dms.stg.stg_contact,PROD)",
                "urn:li:glossaryTerm:PII",
            ],
            expected_domain=None,
            expected_assets=[
                "urn:li:dataset:(urn:li:dataPlatform:redshift,dms.stg.stg_contact,PROD)",
                "urn:li:glossaryTerm:PII",
            ],
            expected_evidence=[
                {"field": "glossary_term_urns", "note": "stg_contact gắn PII và AES-256 (direct)"},
            ],
            expected_tool=["retrieve:entity_summary"],
            expected_retrieval=["keyword_entity_summary"],
            forbidden_entities=[],
            expected_answer_facts=["stg_contact (dms.stg) có term PII và AES-256 - bằng chứng trực tiếp"],
            acceptable_answer_variants=["nêu rõ mức bằng chứng: direct (term gắn trực tiếp)"],
            abstention_condition="không suy đoán dataset khác chứa PII nếu không có term gắn",
            source_metadata={"entity_type": "dataset", "urn": "urn:li:dataset:(urn:li:dataPlatform:redshift,dms.stg.stg_contact,PROD)"},
            ground_truth_provenance={"file": "asset_relationship_map.json", "key": "dataset_to_glossary_term"},
        )

    # =====================================================================
    # CATEGORY V — Negative / abstention
    # =====================================================================
    def build_v(self):
        self.add(
            category="V", test_id=self._new_id("V", 1), difficulty="hard",
            domain=None,
            user_query="ai là owner của dataset fact_mcr?",
            expected_intent="owner_query",
            expected_entities=["urn:li:dataset:(urn:li:dataPlatform:redshift,dataanalyticsprd.dwh.fact_mcr,PROD)"],
            expected_domain=None,
            expected_assets=[],
            expected_evidence=[{"field": "owners", "value": []}],
            expected_tool=["retrieve:entity_summary"],
            expected_retrieval=["keyword_entity_summary"],
            forbidden_entities=[],
            expected_answer_facts=["không có thông tin owner trong DataHub (owners=0)"],
            acceptable_answer_variants=["trả lời UNKNOWN / không có dữ liệu owner"],
            abstention_condition="không bịa tên owner; nêu UNKNOWN và gợi ý kiểm tra DataHub UI",
            source_metadata={"entity_type": "dataset", "urn": "urn:li:dataset:(urn:li:dataPlatform:redshift,dataanalyticsprd.dwh.fact_mcr,PROD)"},
            ground_truth_provenance={"file": "data_ground_truth.json", "key": "datasets.owners"},
        )

    # =====================================================================
    # CATEGORY W — Constraint-following (domain scoping)
    # =====================================================================
    def build_w(self):
        self.add(
            category="W", test_id=self._new_id("W", 1), difficulty="medium",
            domain="TÀI CHÍNH",
            user_query="chỉ nêu báo cáo thuộc domain TÀI CHÍNH về giá thành hoặc ngân sách",
            expected_intent="domain_constrained_discovery",
            expected_entities=[
                "urn:li:dataset:(urn:li:dataPlatform:SAP,Kế toán.Báo cáo giá thành,PROD)",
                "urn:li:dataset:(urn:li:dataPlatform:SAP,Tối ưu Sản xuất và Cung ứng.Báo cáo sử dụng ngân sách Opex và phân tích CPU/CPH,PROD)",
            ],
            expected_domain="TÀI CHÍNH",
            expected_assets=[
                "urn:li:dataset:(urn:li:dataPlatform:SAP,Kế toán.Báo cáo giá thành,PROD)",
                "urn:li:dataset:(urn:li:dataPlatform:SAP,Tối ưu Sản xuất và Cung ứng.Báo cáo sử dụng ngân sách Opex và phân tích CPU/CPH,PROD)",
            ],
            expected_evidence=[{"field": "domain", "value": "TÀI CHÍNH"}],
            expected_tool=["retrieve:entity_summary"],
            expected_retrieval=["keyword_entity_summary", "filter:domain"],
            forbidden_entities=["urn:li:dataset:(urn:li:dataPlatform:SAP,Sản xuất.Báo cáo tình trạng kiểm soát dữ liệu rác và kỷ luật dữ liệu,PROD)"],
            expected_answer_facts=["chỉ liệt kê dataset domain TÀI CHÍNH: Báo cáo giá thành, Báo cáo sử dụng ngân sách Opex..."],
            acceptable_answer_variants=["không nêu dataset ngoài domain TÀI CHÍNH"],
            abstention_condition="phải lọc theo domain TÀI CHÍNH; dataset SẢN XUẤT là forbidden",
            source_metadata={"entity_type": "dataset", "domain": "TÀI CHÍNH"},
            ground_truth_provenance={"file": "data_ground_truth.json", "key": "datasets.domain"},
        )

    # =====================================================================
    # CATEGORY X — Retrieval-only vs reasoning-only
    # =====================================================================
    def build_x(self):
        self.add(
            category="X", test_id=self._new_id("X", 1), difficulty="medium",
            domain=None,
            user_query="dataset nào chứa trường 'plant_id'?",
            expected_intent="retrieval_only_field_query",
            expected_entities=["urn:li:dataset:(urn:li:dataPlatform:powerbi,PFEP_Report_-_Hai_Phong_Factory.Fact_Mrp_Demand,PROD)"],
            expected_domain=None,
            expected_assets=[],
            expected_evidence=[{"field": "schema_fields", "note": "plant_id xuất hiện trong nhiều dataset (892 lần)"}],
            expected_tool=["retrieve:schema_fields"],
            expected_retrieval=["keyword_schema_fields"],
            forbidden_entities=[],
            expected_answer_facts=["plant_id là field phổ biến (892 dataset); phải nêu danh sách mẫu và cảnh báo nhiều kết quả"],
            acceptable_answer_variants=["liệt kê dataset mẫu + cảnh báo trùng field"],
            abstention_condition="không khẳng định chỉ một dataset duy nhất chứa plant_id",
            source_metadata={"entity_type": "field", "field": "plant_id"},
            ground_truth_provenance={"file": "retrieval_risk_map.json", "key": "top_shared_fields"},
        )

    # =====================================================================
    # CATEGORY Y — Citation / provenance
    # =====================================================================
    def build_y(self):
        term = {"name": "MRP (Material Requirements Planning)", "urn": "urn:li:glossaryTerm:90343e1f-15de-4625-adc8-a247318d7cbc"}
        self.add(
            category="Y", test_id=self._new_id("Y", 1), difficulty="medium",
            domain="SẢN XUẤT",
            user_query=f'"{term["name"]}" được định nghĩa ở đâu?',
            expected_intent="citation_provenance",
            expected_entities=[term["urn"]],
            expected_domain=None,
            expected_assets=[term["urn"]],
            expected_evidence=[{"field": "description", "urn": term["urn"]}],
            expected_tool=["retrieve:term_definition"],
            expected_retrieval=["keyword_term_definition"],
            forbidden_entities=[],
            expected_answer_facts=[f"định nghĩa nằm trong glossary term {term['name']} ({term['urn']})"],
            acceptable_answer_variants=["trả lời kèm URN/đường dẫn nguồn"],
            abstention_condition="câu trả lời phải gắn nguồn (term URN)",  # noqa: E501
            source_metadata={"entity_type": "glossary_term", "urn": term["urn"]},
            ground_truth_provenance={"file": "data_ground_truth.json", "key": "glossary_terms"},
        )

    # =====================================================================
    # CASE TYPE 1 — Domain-scoped term
    # =====================================================================
    def build_case1(self):
        cases = [
            {
                "q": "Demand là gì?",
                "urn": "urn:li:glossaryTerm:72c69954-8944-4e58-9af2-328502dc9390",
                "facts": ["có nhiều term 'Demand' liên quan (Nhu cầu linh kiện, Demand of all build phases per variant, Required Demand)", "phải hỏi lại domain hoặc nêu đầy đủ các định nghĩa"],
            },
            {
                "q": "Demand trong domain SẢN XUẤT là gì?",
                "urn": "urn:li:glossaryTerm:72c69954-8944-4e58-9af2-328502dc9390",
                "facts": ["trong SẢN XUẤT, Demand = Nhu cầu linh kiện (Component/Part Demand) do MRP tính", "liên quan dataset mrp_stock_req"],
            },
            {
                "q": "so sánh Demand giữa SẢN XUẤT và KINH DOANH",
                "urn": "urn:li:glossaryTerm:72c69954-8944-4e58-9af2-328502dc9390",
                "facts": ["SẢN XUẤT: nhu cầu linh kiện/NVL theo MPS/BOM", "KINH DOANH: không có term Demand rõ ràng trong DataHub → UNKNOWN"],
            },
        ]
        for i, c in enumerate(cases, 1):
            self.add(
                category="CASE1", case_type=1, test_id=self._new_id("CASE1", i), difficulty="hard",
                domain="SẢN XUẤT" if i != 3 else None,
                user_query=c["q"],
                expected_intent="domain_scoped_glossary",
                expected_entities=[c["urn"]],
                expected_domain="SẢN XUẤT" if i != 3 else None,
                expected_assets=[c["urn"]],
                expected_evidence=[{"field": "description", "urn": c["urn"]}],
                expected_tool=["retrieve:term_definition"],
                expected_retrieval=["keyword_term_definition", "filter:domain"],
                forbidden_entities=[],
                expected_answer_facts=c["facts"],
                acceptable_answer_variants=["hỏi lại domain khi không rõ; hoặc liệt kê mọi định nghĩa Demand"],
                abstention_condition="khi query không có domain rõ, không được chọn 1 định nghĩa duy nhất",
                source_metadata={"entity_type": "glossary_term", "urns": ["urn:li:glossaryTerm:72c69954-8944-4e58-9af2-328502dc9390", "urn:li:glossaryTerm:42dae407-ae65-4d6b-a9c9-6e4925d0c70c"]},
                ground_truth_provenance={"file": "domain_semantic_map.json", "key": "_domain_scoped_glossary_heuristic"},
            )

    # =====================================================================
    # CASE TYPE 2 — Report discovery (capacity of vendor)
    # =====================================================================
    def build_case2(self):
        cases = [
            {
                "q": "có báo cáo nào về capacity của nhà cung cấp (vendor) không?",
                "facts": ["dashboard: Report_Supply_Capacity, VFVN2_DG_R Supplier Capacity", "dataset: fact_supplier_capacity, rpt_survey_weekly_supply_capacity"],
                "entities": [
                    "urn:li:dashboard:(powerbi,reports.08875c53-cbd5-4435-aafd-b31e4e6940a8)",
                    "urn:li:dashboard:(powerbi,reports.809b7230-223f-43ac-9b4d-a1f59b4f17c8)",
                    "urn:li:dataset:(urn:li:dataPlatform:powerbi,HP_side_-_Control_Max_stock_+_Inbound.fact_supplier_capacity,PROD)",
                    "urn:li:dataset:(urn:li:dataPlatform:redshift,sap.dwh.rpt_survey_weekly_supply_capacity,PROD)",
                ],
            },
            {
                "q": "báo cáo capacity cung ứng tuần nào liên quan đến bảng survey capacity từng part?",
                "facts": ["rpt_survey_weekly_supply_capacity (redshift sap.dwh) có 20 trường"],
                "entities": ["urn:li:dataset:(urn:li:dataPlatform:redshift,sap.dwh.rpt_survey_weekly_supply_capacity,PROD)"],
            },
        ]
        for i, c in enumerate(cases, 1):
            self.add(
                category="CASE2", case_type=2, test_id=self._new_id("CASE2", i), difficulty="medium",
                domain="LOGISTIC" if i == 1 else None,
                user_query=c["q"],
                expected_intent="report_discovery_capacity",
                expected_entities=c["entities"],
                expected_domain="LOGISTIC" if i == 1 else None,
                expected_assets=c["entities"],
                expected_evidence=[{"field": "name", "note": "capacity/supplier/survey keywords"}],
                expected_tool=["retrieve:dashboard_summary", "retrieve:entity_summary"],
                expected_retrieval=["keyword_dashboard_summary", "keyword_entity_summary"],
                forbidden_entities=[],
                expected_answer_facts=c["facts"],
                acceptable_answer_variants=["liệt kê dashboard + dataset liên quan capacity"],
                source_metadata={"entity_type": "mixed"},
                ground_truth_provenance={"file": "data_ground_truth.json", "key": "dashboards.name + datasets.name"},
            )

    # =====================================================================
    # CASE TYPE 3 — Metric / column formula
    # =====================================================================
    def build_case3(self):
        cov1 = "urn:li:glossaryTerm:7081e281-2d7b-4f66-9b1b-c31cdb66cc1b"
        cov2 = "urn:li:glossaryTerm:e26f9aeb-b1f9-4553-9eac-f9137f915e4a"
        self.add(
            category="CASE3", case_type=3, test_id=self._new_id("CASE3", 1), difficulty="hard",
            domain=None,
            user_query="công thức Coverage Date trong Fact_Inventory_Coverage là gì?",
            expected_intent="metric_formula_in_dataset",
            expected_entities=[cov1, cov2, "urn:li:dataset:(urn:li:dataPlatform:powerbi,20260509_Pilot_part_Final.Fact_Inventory_Coverage,PROD)"],
            expected_domain=None,
            expected_assets=[cov1, cov2],
            expected_evidence=[
                {"field": "description", "urn": cov2, "note": "Coverage Date định nghĩa 2: số ngày làm việc tồn kho + Git đủ nhu cầu, LOB ≥ 0"},
            ],
            expected_tool=["retrieve:term_definition"],
            expected_retrieval=["keyword_term_definition"],
            forbidden_entities=[],
            expected_answer_facts=["không có công thức số học khép kín trong mô tả; chỉ có cơ chế: tồn kho + Git đủ nhu cầu cho tới khi LOB < 0"],
            acceptable_answer_variants=["giải thích cơ chế + gắn URN term, không bịa con số"],
            abstention_condition="không bịa công thức; chỉ trích dẫn cơ chế trong description",
            source_metadata={"entity_type": "glossary_term", "urns": [cov1, cov2]},
            ground_truth_provenance={"file": "data_ground_truth.json", "key": "glossary_terms.description"},
        )

    # =====================================================================
    # CASE TYPE 4 — Report lineage
    # =====================================================================
    def build_case4(self):
        dash = "urn:li:dashboard:(powerbi,reports.08875c53-cbd5-4435-aafd-b31e4e6940a8)"
        self.add(
            category="CASE4", case_type=4, test_id=self._new_id("CASE4", 1), difficulty="hard",
            domain="LOGISTIC",
            user_query="Report_Supply_Capacity lấy dữ liệu từ đâu? Liệt kê theo lineage từ report → dataset → nguồn thô.",
            expected_intent="report_lineage_chain",
            expected_entities=[dash],
            expected_domain="LOGISTIC",
            expected_assets=[],
            expected_evidence=[{"field": "upstream_urns", "urn": dash, "value": []}],
            expected_tool=["retrieve:dashboard_summary", "retrieve:entity_summary", "retrieve:lineage"],
            expected_retrieval=["keyword_dashboard_summary"],
            forbidden_entities=[],
            expected_answer_facts=["không có lineage report→dataset trong DataHub → phải trả lời UNKNOWN ở bước lineage, chỉ có thể đề xuất dataset tên khớp"],
            acceptable_answer_variants=["UNKNOWN + đề xuất tên dataset khớp (fact_supplier_capacity) kèm nhãn suy đoán"],
            abstention_condition="không dựng chuỗi lineage khi không có dữ liệu",
            source_metadata={"entity_type": "dashboard", "urn": dash},
            ground_truth_provenance={"file": "asset_relationship_map.json", "key": "dashboard_to_dataset_input"},
        )

    # =====================================================================
    # CASE TYPE 5 — Multi-hop 5 bước
    # =====================================================================
    def build_case5(self):
        self.add(
            category="CASE5", case_type=5, test_id=self._new_id("CASE5", 1), difficulty="hard",
            domain="LOGISTIC",
            user_query="từ report capacity → định nghĩa capacity → cột liên quan → công thức → nguồn dữ liệu thô",
            expected_intent="multi_hop_chain",
            expected_entities=[
                "urn:li:dashboard:(powerbi,reports.08875c53-cbd5-4435-aafd-b31e4e6940a8)",
                "urn:li:dataset:(urn:li:dataPlatform:redshift,sap.dwh.rpt_survey_weekly_supply_capacity,PROD)",
            ],
            expected_domain="LOGISTIC",
            expected_assets=["urn:li:dashboard:(powerbi,reports.08875c53-cbd5-4435-aafd-b31e4e6940a8)"],
            expected_evidence=[
                {"field": "name", "note": "hop1 report"},
                {"field": "description", "note": "hop2 định nghĩa capacity: không có term capacity chuyên biệt → UNKNOWN"},
                {"field": "schema_fields", "note": "hop3 cột liên quan của rpt_survey_weekly_supply_capacity"},
                {"field": "formula", "note": "hop4 công thức: UNKNOWN (không có trong dữ liệu)"},
                {"field": "lineage", "note": "hop5 nguồn thô: UNKNOWN (không có lineage)"},
            ],
            expected_tool=["retrieve:dashboard_summary", "retrieve:entity_summary", "retrieve:schema_fields", "retrieve:term_definition", "retrieve:lineage"],
            expected_retrieval=["keyword_entity_summary"],
            forbidden_entities=[],
            expected_answer_facts=["hop1: Report_Supply_Capacity; hop2: không có term 'capacity' → UNKNOWN; hop3: liệt kê cột của rpt_survey_weekly_supply_capacity; hop4: UNKNOWN; hop5: UNKNOWN"],
            acceptable_answer_variants=["đi từng hop, ghi rõ hop nào UNKNOWN"],
            abstention_condition="hop không có dữ liệu phải đánh dấu UNKNOWN",
            source_metadata={"entity_type": "mixed"},
            ground_truth_provenance={"file": "data_ground_truth.json", "key": "mixed"},
        )

    # =====================================================================
    # CASE TYPE 6 — Domain + report + lineage chain
    # =====================================================================
    def build_case6(self):
        self.add(
            category="CASE6", case_type=6, test_id=self._new_id("CASE6", 1), difficulty="hard",
            domain="LOGISTIC",
            user_query="trong domain LOGISTIC, tìm report về capacity, term liên quan, dataset nguồn và lineage",
            expected_intent="domain_report_term_lineage_chain",
            expected_entities=[
                "urn:li:dashboard:(powerbi,reports.08875c53-cbd5-4435-aafd-b31e4e6940a8)",
                "urn:li:dataset:(urn:li:dataPlatform:redshift,sap.dwh.rpt_survey_weekly_supply_capacity,PROD)",
            ],
            expected_domain="LOGISTIC",
            expected_assets=["urn:li:dashboard:(powerbi,reports.08875c53-cbd5-4435-aafd-b31e4e6940a8)"],
            expected_evidence=[
                {"field": "domain", "value": "LOGISTIC"},
                {"field": "name", "note": "report capacity"},
                {"field": "term", "note": "không có term capacity chuyên biệt → UNKNOWN"},
                {"field": "lineage", "note": "UNKNOWN"},
            ],
            expected_tool=["retrieve:dashboard_summary", "retrieve:entity_summary", "retrieve:term_definition", "retrieve:lineage"],
            expected_retrieval=["keyword_dashboard_summary", "filter:domain"],
            forbidden_entities=[],
            expected_answer_facts=["domain LOGISTIC có report capacity; term capacity UNKNOWN; dataset gợi ý rpt_survey_weekly_supply_capacity; lineage UNKNOWN"],
            acceptable_answer_variants=["đi từng bước, ghi rõ UNKNOWN khi thiếu"],
            abstention_condition="không bịa term hay lineage khi thiếu dữ liệu",
            source_metadata={"entity_type": "mixed"},
            ground_truth_provenance={"file": "data_ground_truth.json", "key": "mixed"},
        )

    # =====================================================================
    # Emit
    # =====================================================================
    def emit(self, force=False):
        for p in (OUT_JSONL, OUT_MD, OUT_STATS):
            if os.path.exists(p) and not force:
                raise SystemExit(f"{os.path.basename(p)} đã tồn tại. Chạy lại với --force để ghi đè.")
        # sort by category then test_id
        def skey(t):
            cat, num = t["test_id"].split("-")
            return (cat, int(num))
        self.tests.sort(key=skey)

        with open(OUT_JSONL, "w", encoding="utf-8") as f:
            for t in self.tests:
                f.write(json.dumps(t, ensure_ascii=False) + "\n")

        self._write_md()
        self._write_stats()
        print(f"Wrote {len(self.tests)} tests")
        print(f"  {OUT_JSONL}")
        print(f"  {OUT_MD}")
        print(f"  {OUT_STATS}")

    def _write_md(self):
        with open(OUT_MD, "w", encoding="utf-8") as f:
            f.write("# DataAtlas Golden Benchmark\n\n")
            f.write(f"- Schema version: {SCHEMA_VERSION}\n")
            f.write(f"- Generated: {GEN_DATE}\n")
            f.write(f"- Total tests: {len(self.tests)}\n\n")
            f.write("| Category | Test ID | Difficulty | Domain | Query |\n")
            f.write("|---|---|---|---|---|\n")
            for t in self.tests:
                dom = t.get("domain") or "-"
                q = t["user_query"].replace("|", "/").replace("\n", " ")
                f.write(f"| {t['category']} | {t['test_id']} | {t['difficulty']} | {dom} | {q} |\n")

    def _write_stats(self):
        cats = Counter(t["category"] for t in self.tests)
        diffs = Counter(t["difficulty"] for t in self.tests)
        doms = Counter((t.get("domain") or "(none)") for t in self.tests)
        case_types = Counter(t.get("case_type") for t in self.tests if t.get("case_type"))
        with open(OUT_STATS, "w", encoding="utf-8") as f:
            f.write("# Benchmark Statistics\n\n")
            f.write(f"- Total tests: {len(self.tests)}\n")
            f.write(f"- Generated: {GEN_DATE}\n\n")
            f.write("## By category\n\n| Category | Count |\n|---|---|\n")
            for k in sorted(cats):
                f.write(f"| {k} | {cats[k]} |\n")
            f.write("\n## By difficulty\n\n| Difficulty | Count |\n|---|---|\n")
            for k in sorted(diffs):
                f.write(f"| {k} | {diffs[k]} |\n")
            f.write("\n## By domain\n\n| Domain | Count |\n|---|---|\n")
            for k in sorted(doms):
                f.write(f"| {k} | {doms[k]} |\n")
            f.write("\n## By case type\n\n| Case type | Count |\n|---|---|\n")
            for k in sorted(case_types, key=lambda x: (x is None, x)):
                f.write(f"| {k} | {case_types[k]} |\n")


def main():
    ap = argparse.ArgumentParser(description="Generate DataAtlas Golden Benchmark")
    ap.add_argument("--force", action="store_true", help="overwrite existing outputs")
    args = ap.parse_args()
    data = load()
    b = BenchmarkBuilder(data)
    b.build_all()
    b.emit(force=args.force)


if __name__ == "__main__":
    main()
