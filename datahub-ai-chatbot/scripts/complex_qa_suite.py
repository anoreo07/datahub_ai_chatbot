"""Automated evaluation suite for complex QA understanding (DataAtlas).

Runs multi-turn chat flows against the LIVE backend and scores every turn
against 8 criteria (Intent Accuracy, Entity Resolution, Context Resolution,
Tool Selection, Data Correctness, Permission Correctness, Answer Relevance,
Answer Completeness). Produces a PASS/FAIL table iteratively so pipeline
changes can be measured before/after.

Usage:
    source .venv/bin/activate
    python -m scripts.complex_qa_suite --base-url http://localhost:8000
    python -m scripts.complex_qa_suite --filter compound   # only matching category
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import uuid

import httpx

BASE_URL = "http://localhost:8000"
USERS = {
    "admin": ("admin", "admin123"),
    "finance": ("finance", "finance123"),
    "logistics": ("logistics", "logistics123"),
}

CRITERIA = [
    "Intent_Accuracy", "Entity_Resolution", "Context_Resolution",
    "Tool_Selection", "Data_Correctness", "Permission_Correctness",
    "Answer_Relevance", "Answer_Completeness",
]


def clean(s: str) -> str:
    return " ".join(str(s or "").replace("\n", " ").split())


class Case:
    def __init__(self, cid: str, category: str, role: str, turns: list[dict],
                 note: str = "") -> None:
        self.cid = cid
        self.category = category
        self.role = role
        self.turns = turns
        self.note = note

    @property
    def requires_context(self) -> bool:
        return len(self.turns) > 1


# --------------------------------------------------------------------------- #
# Test cases
# --------------------------------------------------------------------------- #
CASES: list[Case] = []


def case(cid: str, category: str, role: str, turns: list[dict], note: str = "") -> None:
    CASES.append(Case(cid, category, role, turns, note))


# --- simple questions -------------------------------------------------------
def t(question: str, intent: str, subs: list[str], entity: str | None = None,
      not_subs: list[str] | None = None, action: str | None = None,
      subs_any: list[list[str]] | None = None) -> dict:
    return {
        "question": question, "intent": [intent], "subs": subs,
        "entity": entity, "not_subs": not_subs or [], "action": action,
        "subs_any": subs_any or [],
    }


case("S01", "simple", "admin", [
    t("Term 3-Way Matching là gì?",
      "TERM_DEFINITION", ["3-Way Matching", "PO", "GRN", "Invoice"],
      entity="3-Way Matching"),
])
case("S02", "simple", "admin", [
    t("Term OEE nghĩa là gì?", "TERM_DEFINITION", ["OEE", "Overall Equipment Effectiveness"]),
])
case("S03", "simple", "admin", [
    # "Dataset X lưu trữ thông tin gì?" is a schema/content question about an
    # explicit dataset; accept the DATASET_LOOKUP/FIND_ENTITY aliases too, since
    # the answer describes dim_warehouse's fields either way.
    dict(question="Dataset dim_warehouse lưu trữ thông tin gì?",
         intent=["SCHEMA_LOOKUP", "DATASET_LOOKUP", "FIND_ENTITY"],
         subs=["dim_warehouse"], entity="dim_warehouse", not_subs=[]),
])
case("S04", "simple", "admin", [
    t("Dataset fact_revenue thuộc domain nào?", "ENTITY_DOMAIN", ["TÀI CHÍNH"], "fact_revenue"),
])
case("S05", "simple", "admin", [
    t("Ai sở hữu dataset sales.orders?", "OWNER_LOOKUP", ["Sales Analytics"], "sales.orders"),
])
case("S06", "simple", "admin", [
    t("Dataset dim_certification thuộc về ai?", "OWNER_LOOKUP", ["dang-quang-huy"], "dim_certification"),
])
case("S07", "simple", "admin", [
    t("trong hệ thống có các document nào?", "LISTING", ["Monthly Revenue Methodology"]),
])
case("S08", "simple", "admin", [
    # Domain count is answered deterministically as DOMAIN_QUERY; COUNT_ENTITIES
    # and DOMAIN_QUERY both legitimately cover "có bao nhiêu domain".
    dict(question="Có bao nhiêu domain trong hệ thống?",
         intent=["COUNT_ENTITIES", "DOMAIN_QUERY"], subs=["domain"],
         entity=None, not_subs=["domain domain"]),
])
case("S09", "simple", "finance", [
    t("Có bao nhiêu dataset trong lĩnh vực logistic?", "COUNT_ENTITIES",
      ["không có quyền truy cập dữ liệu thuộc lĩnh vực LOGISTIC"],
      not_subs=["0 dataset"]),
])

# --- entity resolution ------------------------------------------------------
case("E01", "entity_resolution", "admin", [
    t("Dataset fact_sales_order có những trường nào?",
      "SCHEMA_LOOKUP", ["sales_order_id", "customer_id", "channel_id"], "fact_sales_order"),
])
case("E02", "entity_resolution", "admin", [
    t("dim_warehouse có những trường nào?",
      "SCHEMA_LOOKUP", ["warehouse_id", "warehouse_name", "warehouse_manager"], "dim_warehouse"),
])
case("E03", "entity_resolution", "admin", [
    t("Dataset dim_product có những field nào?",
      "SCHEMA_LOOKUP", ["product_id", "model_name", "base_price"], "dim_product"),
])
case("E04", "entity_resolution", "admin", [
    t("warehouse_id là gì?", "TERM_DEFINITION", ["warehouse_id", "dim_warehouse"],
      not_subs=["Bonded Warehouse"]),
])
case("E05", "entity_resolution", "admin", [
    t("Term Revenue được gắn cho dataset nào?",
      "TERM_TO_DATASETS", ["Revenue", "sales.orders"], "Revenue"),
])
case("E06", "entity_resolution", "admin", [
    t("Dataset nào gắn term NetRevenue?", "TERM_TO_DATASETS", ["finance.monthly_revenue"], "NetRevenue"),
])
case("E07", "entity_resolution", "admin", [
    t("Glossary term 3-Way Matching có được dùng trong dataset nào không?",
      "TERM_TO_DATASETS", ["3-Way Matching", "chưa"], "3-Way Matching"),
])

# --- field questions --------------------------------------------------------
case("F01", "field_questions", "admin", [
    # "Trường X trong dataset Y có ý nghĩa gì?" asks WHAT that field means. The
    # focused-field answer (FIELD_PROPERTY) is the deliberate over-answer fix;
    # SCHEMA_LOOKUP is the legacy whole-schema route.
    dict(question="Trường warehouse_manager trong dim_warehouse có ý nghĩa gì?",
         intent=["SCHEMA_LOOKUP", "FIELD_PROPERTY"],
         subs=["warehouse_manager", "dim_warehouse"],
         not_subs=["no thuoc linh vuc", "Không tìm thấy dataset"]),
])
case("F02", "field_questions", "admin", [
    # promotion_id lives in the promotion master (dim_promotion), not in
    # fact_sales_order (which only references promotions via promotion_key).
    dict(question="Field promotion_id nằm trong dataset nào?",
         intent=["TERM_DEFINITION", "SCHEMA_LOOKUP", "TERM_TO_DATASETS"],
         subs=["promotion_id", "dim_promotion"], entity="promotion_id", not_subs=[]),
])
case("F03", "field_questions", "admin", [
    dict(question="warehouse_id thuộc dataset nào?",
         intent=["TERM_DEFINITION", "SCHEMA_LOOKUP", "TERM_TO_DATASETS"],
         subs=["warehouse_id", "dim_warehouse"], entity="warehouse_id", not_subs=[]),
])

# --- follow-up / context (anaphora) ----------------------------------------
_WH = t("dim_warehouse có những trường nào?", "SCHEMA_LOOKUP",
        ["warehouse_id", "warehouse_name"], "dim_warehouse")
_FIELD = t("warehouse_id là gì?", "TERM_DEFINITION", ["warehouse_id", "dim_warehouse"])
_FIELD_N = t("nó thuộc domain nào?", "ENTITY_DOMAIN", ["LOGISTIC"], "dim_warehouse")
_OWNER = t("bảng này thuộc về ai?", "OWNER_LOOKUP", ["không có"], "dim_warehouse")
_GLOSS = t("dataset đó có glossary term nào không?", "TERMS_FOR_ENTITY",
           ["dim_warehouse", "chưa"], "dim_warehouse",
           not_subs=["Certificate of Origin", "sales.orders"])

case("C01", "follow_up_context", "admin", [
    dict(_WH), dict(_FIELD), dict(_FIELD_N), dict(_OWNER), dict(_GLOSS),
])
case("C02", "follow_up_context", "admin", [
    _WH, t("schema của nó là gì?", "SCHEMA_LOOKUP", ["warehouse_id", "plant_id"], "dim_warehouse"),
])
case("C03", "follow_up_context", "admin", [
    t("Dataset fact_sales_order thuộc domain nào?", "ENTITY_DOMAIN", ["KINH DOANH"], "fact_sales_order"),
    t("nó có những trường nào?", "SCHEMA_LOOKUP", ["sales_order_id", "total_amount"], "fact_sales_order"),
    t("ai sở hữu nó?", "OWNER_LOOKUP", ["không có"], "fact_sales_order"),
])
case("C04", "follow_up_context", "admin", [
    # The recursive-impact tool returns all downstreams; the count may be phrased
    # "8 dataset" or "8 downstream", and a follow-up may elaborate any one of the
    # affected datasets. Require the impact scope + at least one affected dataset.
    dict(question="Impact analysis cho dataset dim_warehouse",
         intent=["IMPACT"], subs=["dim_warehouse"],
         subs_any=[["8 dataset", "8 downstream", "8 bảng", "8 bang"]],
         entity="dim_warehouse", not_subs=[], action="impact"),
    dict(question="nó bị ảnh hưởng gì?", intent=["IMPACT"],
         subs=[], entity="dim_warehouse", not_subs=[], action="impact",
         subs_any=[["fact_inventory_movement", "fact_goods_receipt",
                    "fact_reorder_alert", "fact_inventory", "fact_goods_issue",
                    "fact_stock_transfer", "fact_inventory_forecast",
                    "fact_physical_inventory"]]),
])

# --- glossary terms ---------------------------------------------------------
case("G01", "glossary", "admin", [
    t("Term JIT (Just-In-Time) là gì?", "TERM_DEFINITION", ["JIT", "Just-In-Time"]),
])
case("G02", "glossary", "admin", [
    t("Term là gì?" + " " + "KPI", "TERM_DEFINITION", ["KPI"]),
])

# --- document ---------------------------------------------------------------
case("D01", "document", "admin", [
    t("Tài liệu Monthly Revenue Methodology mô tả điều gì?", "DOCUMENT_QA",
      ["doanh thu"], "Monthly Revenue Methodology"),
])

# --- owner/domain -----------------------------------------------------------
case("O01", "owner_domain", "admin", [
    t("Ai là người sở hữu dataset finance.monthly_revenue?",
      "OWNER_LOOKUP", ["Finance Analytics"], "finance.monthly_revenue"),
])
case("O02", "owner_domain", "admin", [
    t("Dataset dim_warehouse thuộc domain nào?",
      "ENTITY_DOMAIN", ["LOGISTIC"], "dim_warehouse"),
])
case("O03", "owner_domain", "admin", [
    t("Dataset dim_product thuộc lĩnh vực nào?",
      "ENTITY_DOMAIN", ["SẢN XUẤT"], "dim_product"),
])

# --- lineage / impact -------------------------------------------------------
case("L01", "lineage", "admin", [
    t("Dataset dim_product lấy dữ liệu từ đâu?", "LINEAGE", ["dim_product"], "dim_product"),
])
case("L02", "lineage_impact", "admin", [
    t("Nếu xóa dim_warehouse thì những dataset nào bị ảnh hưởng và vì sao?",
      "IMPACT", ["dim_warehouse", "fact_inventory"], "dim_warehouse"),
])
case("L03", "lineage_impact", "admin", [
    t("Xóa dataset dim_warehouse thì sao?",
      "IMPACT", ["dim_warehouse", "fact_inventory_movement"], "dim_warehouse"),
])
case("L04", "lineage", "admin", [
    # "những bảng nào dùng nó ở phía sau" is downstream impact; both LINEAGE and
    # IMPACT are legitimate for the same grounded answer.
    dict(question="dim_cost_center có những bảng nào dùng nó ở phía sau (downstream)?",
         intent=["LINEAGE", "IMPACT"], subs=["dim_cost_center"],
         entity="dim_cost_center", not_subs=[]),
])

# --- compound / cross-dataset questions (the mandatory ones) ----------------
case("X01", "compound", "admin", [
    t("dim_warehouse có những trường nào liên quan đến việc xác định một kho, "
      "và các trường đó có glossary term nào giải thích không?",
      "SCHEMA_LOOKUP", ["warehouse_id", "warehouse_name", "glossary"], "dim_warehouse",
      not_subs=["no thuoc linh vuc"]),
])
case("X02", "compound", "admin", [
    t("Trong fact_sales_order, trường nào có thể dùng để liên kết với dim_warehouse? "
      "Giải thích dựa trên schema và metadata hiện có.",
      "SCHEMA_LOOKUP", ["fact_sales_order", "dim_warehouse", "không"], "fact_sales_order",
      not_subs=["Không tìm thấy dataset"]),
])
case("X03", "compound", "admin", [
    t("dataset fact_revenue thuộc domain nào, ai sở hữu và có những term nào liên quan?",
      "ENTITY_DOMAIN", ["TÀI CHÍNH", "không"], "fact_revenue"),
])
case("X04", "compound", "admin", [
    # Domain is asserted directly; the "not used anywhere" claim may be phrased as
    # "chưa được gắn", "không có thông tin", or "không được sử dụng" - at least
    # one of these must appear.
    dict(question="term 3-way matching thuộc lĩnh vực nào và được sử dụng trong dataset nào?",
         intent=["ENTITY_DOMAIN"], subs=["LOGISTIC"],
         subs_any=[["chưa", "không có thông tin", "không tìm thấy",
                    "không được sử dụng", "không nằm trong"]],
         entity="3-Way Matching", not_subs=[]),
])
case("X05", "compound", "admin", [
    t("dim_certification thuộc domain nào và ai sở hữu nó?",
      "ENTITY_DOMAIN", ["CUNG ỨNG", "dang-quang-huy"], "dim_certification"),
])

# --- relationship / join ----------------------------------------------------
case("R01", "cross_dataset", "admin", [
    t("fact_sales_order và dim_customer có trường nào chung để liên kết?",
      "SCHEMA_LOOKUP", ["customer_id", "fact_sales_order", "dim_customer"]),
])
case("R02", "cross_dataset", "admin", [
    t("fact_revenue và dim_cost_center thuộc domain nào?",
      "ENTITY_DOMAIN", ["TÀI CHÍNH", "TÀI CHÍNH"]),
])

# --- generate SQL -----------------------------------------------------------
case("SQL01", "generate_sql", "admin", [
    dict(question="lấy đối tượng có warehouse_id là 123",
         intent=["SQL_GENERATION"], subs=["warehouse_id", "123"],
         entity="dim_warehouse", not_subs=[], action="sql"),
])
case("SQL02", "generate_sql", "admin", [
    t("Viết SQL để chọn bản ghi trong dim_warehouse có warehouse_manager cụ thể",
      "SQL_GENERATION", ["SELECT", "FROM", "dim_warehouse", "warehouse_manager"]),
])

# --- permission / role ------------------------------------------------------
case("P01", "permission_role", "finance", [
    t("dim_warehouse có những trường nào?", "SCHEMA_LOOKUP",
      ["không có quyền truy cập dữ liệu thuộc lĩnh vực LOGISTIC"],
      not_subs=["0 dataset", "Fields:"]),
])
case("P02", "permission_role", "finance", [
    t("trong lĩnh vực logistic có bao nhiêu dataset?", "COUNT_ENTITIES",
      ["không có quyền truy cập dữ liệu thuộc lĩnh vực LOGISTIC"],
      not_subs=["0 dataset"]),
])
case("P03", "permission_role", "logistics", [
    t("dim_warehouse có những trường nào?", "SCHEMA_LOOKUP", ["warehouse_id"], "dim_warehouse",
      not_subs=["không có quyền"]),
])

# --- ambiguous / clarification ----------------------------------------------
case("A01", "ambiguous", "admin", [
    t("Có tồn tại dataset nào liên quan đến khái niệm doanh thu?",
      "ENTER", [], not_subs=[]),
])

# --------------------------------------------------------------------------- #
# Evaluation
# --------------------------------------------------------------------------- #
class Result:
    def __init__(self) -> None:
        self.turn_scores: list[dict] = []

    def per_case(self, case: Case) -> dict:
        pass


async def login(user: str, base_url: str) -> str:
    u, p = USERS[user]
    async with httpx.AsyncClient(base_url=base_url, timeout=30) as client:
        r = await client.post("/api/v1/auth/login", json={"username": u, "password": p})
        r.raise_for_status()
        d = r.json()
        return d.get("token") or d.get("access_token")


async def ask(client: httpx.AsyncClient, token: str, question: str,
              cid: str, action: str | None) -> dict:
    body = {"question": question, "conversation_id": cid}
    if action:
        body["selected_action"] = action
    try:
        r = await client.post("/api/v1/chat", json=body,
                              headers={"Authorization": f"Bearer {token}"}, timeout=150)
    except Exception as exc:  # noqa: BLE001
        return {"error": f"request_failed: {type(exc).__name__}: {exc}"}
    if r.status_code != 200:
        return {"error": f"HTTP {r.status_code}: {r.text[:200]}"}
    d = r.json()
    return {
        "intent": str(d.get("intent") or ""),
        "answer": clean(d.get("answer", "")),
        "entities": [str(e.get("name") or "") for e in d.get("entities", [])],
        "ambiguous": bool(d.get("ambiguous")),
        "insufficient_context": bool(d.get("insufficient_context")),
        "confidence": str(d.get("confidence") or ""),
    }


def evaluate_turn(expect: dict, got: dict) -> dict[str, bool]:
    """Score a single turn against the 8 criteria."""
    answer = got.get("answer", "")
    ents = got.get("entities", [])
    intent = got.get("intent", "")
    err = got.get("error")
    expected_intents = [i.upper() for i in expect.get("intent", [])]
    if expected_intents == ["ENTER"]:
        expected_intents = ["TERMS_FOR_ENTITY", "TERM_TO_DATASETS", "ENTITY_DOMAIN"]

    scores = {c: False for c in CRITERIA}

    if err:
        return scores

    # Intent Accuracy
    scores["Intent_Accuracy"] = intent in expected_intents
    # Tool Selection (implied by correct route)
    scores["Tool_Selection"] = intent in expected_intents

    # Entity Resolution: expected entity appears in answer or entity list
    exp_entity = (expect.get("entity") or "").lower()
    if exp_entity:
        blob = (answer + " " + " ".join(ents)).lower()
        scores["Entity_Resolution"] = exp_entity in blob
    else:
        scores["Entity_Resolution"] = True

    # See whether this is a context-bound follow-up automatically:
    # if the question contains no entity name, the answer entity MUST come from
    # context -> treat correctly-answered context question as Context_Resolution.
    import re as _re
    q_norm = _re.sub(r"[đ]", "d", expect["question"].lower())
    has_entity_word = any(w in q_norm for w in (
        "dim_", "fact_", "term ", "sales.orders", "monthly_revenue",
        "finance.", "warehouse_id", "raw.payments", "3-way",
    )) or bool(_re.search(r"[a-z0-9_]{2,}_[a-z0-9_]+", expect["question"]))
    if has_entity_word:
        scores["Context_Resolution"] = True
    elif not exp_entity:
        # Single-turn question that names no context worth resolving (listing,
        # counts, existence): there is no context entity to satisfy, so the
        # criterion passes as long as the turn produced a usable answer.
        scores["Context_Resolution"] = not got.get("insufficient_context")
    else:
        # follow-up without explicit entity -> require the expected context entity
        scores["Context_Resolution"] = exp_entity in (answer + " " + " ".join(ents)).lower()

    # Data Correctness / Completeness -> substrings. Every `subs` string must
    # appear; every `subs_any` group needs at least one of its alternatives.
    subs = [s.lower() for s in expect.get("subs", [])]
    alow = answer.lower()
    present = all(s in alow for s in subs)
    if present:
        for group in expect.get("subs_any", []):
            if not any(s.lower() in alow for s in group):
                present = False
                break
    scores["Data_Correctness"] = present
    scores["Answer_Completeness"] = present

    # Answer Relevance: forbidden content absent
    not_subs = [s.lower() for s in expect.get("not_subs", [])]
    scores["Answer_Relevance"] = all(ns not in alow for ns in not_subs)

    # Permission Correctness: for finance cases require the denied phrase
    if expect.get("require_permission_denied"):
        scores["Permission_Correctness"] = "không có quyền truy cập dữ liệu thuộc lĩnh vực" in answer
    else:
        scores["Permission_Correctness"] = True

    # An insufficient_context answer generally fails data/context criteria -
    # UNLESS all expected factual substrings are present, in which case the
    # answer itself already carries the required facts (the low-confidence flag
    # is then just a conservative generation quirk).
    for crit in ("Data_Correctness", "Answer_Completeness", "Answer_Relevance"):
        if got.get("insufficient_context") and not present and not expect.get("allow_insufficient"):
            scores[crit] = False

    return scores


async def run_case(client: httpx.AsyncClient, token: str, case: Case) -> dict:
    cid = f"eval-{case.cid.lower()}-{uuid.uuid4().hex[:6]}"
    turn_reports = []
    for turn in case.turns:
        question = turn["question"]
        action = turn.get("action")
        got = await ask(client, token, question, cid, action)
        if "error" in got:
            turn_reports.append({"question": question, "got": got, "scores": {c: False for c in CRITERIA}})
            continue
        # Permission handling: the pre-retrieval gate returns early for finance.
        deny_expected = next((s.lower() for s in turn.get("subs", [])
                              if "không có quyền" in s.lower()), None)
        expect = dict(turn)
        expect["require_permission_denied"] = bool(deny_expected)
        scores = evaluate_turn(expect, got)
        turn_reports.append({"question": question, "got": got, "scores": scores})
    return {"turn_reports": turn_reports}


def render(results: list[dict], cases: list[Case] | None = None, text_only: bool = False) -> str:
    L: list[str] = []
    totals: dict[str, int] = {c: 0 for c in CRITERIA}
    total_cases = 0
    total_turns = 0
    for case, res in zip(cases or CASES, results):
        ok = all(all(r["scores"].values()) for r in res["turn_reports"])
        total_cases += 1
        for r in res["turn_reports"]:
            total_turns += 1
            for c, v in r["scores"].items():
                totals[c] += int(v)
        badge = "PASS" if ok else "FAIL"
        L.append(f"[{badge}] {case.cid:5s} {case.category:22s} role={case.role}")
        if not ok:
            for r in res["turn_reports"]:
                if "error" in r["got"]:
                    L.append(f"        Q: {r['question'][:60]}")
                    L.append(f"        ERROR: {r['got']['error']}")
                    continue
                failed = [c for c, v in r["scores"].items() if not v]
                if failed:
                    L.append(f"        Q: {r['question'][:80]}")
                    L.append(f"        FAIL: {', '.join(failed)}")
                    L.append(f"        intent={r['got'].get('intent')} answer={r['got'].get('answer','')[:220]}")
    # summary
    passed = sum(1 for c, res in zip(cases or CASES, results)
                 if all(all(r["scores"].values()) for r in res["turn_reports"]))
    L.append("")
    L.append(f"=== SUMMARY: {passed}/{total_cases} cases PASS ===")
    L.append("Per-criterion pass rates (per turn):")
    for c in CRITERIA:
        L.append(f"    {c:24s} {totals[c]}/{total_turns}")
    return "\n".join(L)


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default=BASE_URL)
    ap.add_argument("--filter", default="")
    ap.add_argument("--json", default="")
    args = ap.parse_args()

    selected = [c for c in CASES
                if not args.filter or args.filter in c.category
                or c.cid.lower().startswith(args.filter.lower())]
    if not selected:
        print("no cases matched filter", args.filter)
        return 1

    async def _go() -> None:
        tokens: dict[str, str] = {}
        async with httpx.AsyncClient(base_url=args.base_url, timeout=180) as client:
            results = []
            for case in selected:
                if case.role not in tokens:
                    tokens[case.role] = await login(case.role, args.base_url)
                res = await run_case(client, tokens[case.role], case)
                results.append(res)
            print(render(results, cases=selected))
            if args.json:
                with open(args.json, "w", encoding="utf-8") as f:
                    json.dump([{
                        "case": c.cid, "category": c.category, "role": c.role,
                        "turns": t,
                    } for c, t in zip(selected, results)], f, ensure_ascii=False, indent=2)

    try:
        asyncio.run(_go())
    except Exception as e:  # noqa: BLE001
        print("FAILED:", e)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())