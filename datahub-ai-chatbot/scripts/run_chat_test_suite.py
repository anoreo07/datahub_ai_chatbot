"""Run a real test suite of chat questions against both integrated LLMs
(Fireworks DeepSeek V4 Flash + NVIDIA Llama 3.3 70B) via the live API,
then generate a Markdown report for human evaluation.

Questions range from basic (term/dataset definition) to advanced
(linked / impact questions about lineage).

Usage:
    source .venv/bin/activate
    python -m scripts.run_chat_test_suite --out /tmp/chat_test_suite.md
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

import httpx

BASE_URL = "http://localhost:8000"
USERNAME = "admin"
PASSWORD = "admin123"

MODELS = [
    ("deepseek-v4-flash", "Fireworks - DeepSeek V4 Flash"),
]

QUESTIONS: list[dict] = [
    # --- CƠ BẢN: định nghĩa term ---
    {"id": "Q01", "category": "Term definition", "question": "Term BOM (Bill of Materials) nghĩa là gì?"},
    {"id": "Q02", "category": "Term definition", "question": "Term COGS (Cost of Goods Sold) là gì?"},
    {"id": "Q03", "category": "Term definition", "question": "Term GRN (Goods Received Note) định nghĩa như thế nào?"},
    {"id": "Q04", "category": "Term definition", "question": "Term Aging Inventory có ý nghĩa gì trong quản lý kho?"},

    # --- CƠ BẢN: dataset / schema ---
    {"id": "Q05", "category": "Dataset discovery", "question": "Dataset fact_revenue lưu trữ thông tin gì?"},
    {"id": "Q06", "category": "Dataset discovery", "question": "Dataset dim_product có những trường (field) nào?"},
    {"id": "Q07", "category": "Dataset discovery", "question": "Dataset fact_inventory thuộc domain nào và nội dung là gì?"},

    # --- CƠ BẢN: owner / domain ---
    {"id": "Q08", "category": "Owner / Domain", "question": "Ai là người sở hữu dataset dim_product?"},
    {"id": "Q09", "category": "Owner / Domain", "question": "Dataset fact_goods_issue thuộc domain nào?"},

    # --- TRUNG GIAN: lineage đơn giản ---
    {"id": "Q10", "category": "Lineage - simple", "question": "Dataset dim_product lấy dữ liệu từ đâu (upstream)?"},
    {"id": "Q11", "category": "Lineage - simple", "question": "Dataset fact_general_ledger phụ thuộc vào những bảng upstream nào?"},
    {"id": "Q12", "category": "Schema detail", "question": "Field gross_revenue trong fact_revenue có ý nghĩa gì?"},

    # --- TRUNG BÌNH: lineage downstream 1 mức thực tế ---
    {"id": "Q13", "category": "Lineage - downstream", "question": "Nếu tôi xóa bảng dim_product thì những bảng nào bị ảnh hưởng trực tiếp?"},
    {"id": "Q14", "category": "Lineage - downstream", "question": "dim_material được sử dụng (downstream) bởi những bảng nào?"},
    {"id": "Q15", "category": "Lineage - downstream", "question": "Xóa bảng dim_supplier sẽ ảnh hưởng đến các bảng nào?"},

    # --- KHÓ HƠN: lineage nhiều mức / ảnh hưởng dây chuyền ---
    {"id": "Q16", "category": "Lineage - deep impact", "question": "Xóa dim_assembly_line thì những bảng nào bị ảnh hưởng (kể cả gián tiếp)?"},
    {"id": "Q17", "category": "Lineage - deep impact", "question": "Xóa bảng dim_plant thì ảnh hưởng đến những bảng nào?"},
    {"id": "Q18", "category": "Lineage - deep impact", "question": "Nếu xóa fact_production_order, các bảng nào bị ảnh hưởng?"},

    # --- KHÓ: phân tích kết hợp lineage + domain ---
    {"id": "Q19", "category": "Composite", "question": "Những dataset nào trong domain TÀI CHÍNH có lineage liên quan đến dim_cost_center?"},
    {"id": "Q20", "category": "Composite", "question": "Bảng nào trong dây chuyền của dim_product thuộc domain LOGISTIC?"},

    # --- NÂNG CAO: xóa cascading, nhiều chiều ---
    {"id": "Q21", "category": "Advanced impact", "question": "Xóa dim_material thì danh sách đầy đủ các bảng bị ảnh hưởng gồm những bảng nào?"},
    {"id": "Q22", "category": "Advanced impact", "question": "Nếu xóa dim_warehouse, chuỗi ảnh hưởng dài nhất đến bảng nào và qua những bước nào?"},
    {"id": "Q23", "category": "Advanced impact", "question": "Bảng dim_cost_center ảnh hưởng upstream lẫn downstream như thế nào khi bị xóa?"},

    # --- TỔNG HỢP: kết hợp term + dataset + lineage ---
    {"id": "Q24", "category": "Synthesis", "question": "Term nào liên quan đến doanh thu và những dataset nào chứa nó?"},
    {"id": "Q25", "category": "Synthesis", "question": "Tổng hợp dữ liệu của bảng dim_supplier tham gia vào dây chuyền nào và ảnh hưởng các bảng nào?"},
]


def _clean(s: str) -> str:
    return " ".join(str(s).replace("\n", " ").split())


async def login(base_url: str) -> str:
    async with httpx.AsyncClient(base_url=base_url, timeout=30) as client:
        r = await client.post("/api/v1/auth/login", json={"username": USERNAME, "password": PASSWORD})
        r.raise_for_status()
        return r.json()["token"]


_TOKEN: dict[str, str] = {}


async def ask(client: httpx.AsyncClient, question: str, model: str) -> dict:
    try:
        r = await client.post(
            "/api/v1/chat",
            json={"question": question, "model": model},
            headers={"Authorization": f"Bearer {_TOKEN.get('value', '')}"},
            timeout=120,
        )
    except Exception as exc:  # noqa: BLE001
        return {"error": f"request_failed: {type(exc).__name__}: {exc}"}
    if r.status_code != 200:
        return {"error": f"HTTP {r.status_code}: {r.text[:200]}"}
    d = r.json()
    return {
        "intent": d.get("intent"),
        "confidence": d.get("confidence"),
        "ambiguous": d.get("ambiguous"),
        "insufficient_context": d.get("insufficient_context"),
        "answer": _clean(d.get("answer", "")),
        "entities": [e.get("name") for e in d.get("entities", [])],
        "citations": len(d.get("citations", [])),
        "lineage_downstream": len((d.get("lineage") or {}).get("downstreams", [])),
        "lineage_upstream": len((d.get("lineage") or {}).get("upstreams", [])),
    }


def render_report(results: list[dict]) -> str:
    L: list[str] = []
    L.append("# Chatbot Test Suite — Đánh giá chất lượng trả lời\n")
    L.append("> Dữ liệu thật từ DataHub (135 redshift datasets, không mock). Câu hỏi từ cơ bản đến phức tạp.\n")
    L.append("> Tiêu chí đánh giá: **Trả lời đúng trọng tâm**, **Guardrails**, **Trả lời + thực hiện đúng chức năng**.\n")
    L.append("## Tóm tắt nhanh\n")
    for model_id, label in MODELS:
        rows = [r for r in results if r["model_id"] == model_id]
        ok = sum(1 for r in rows if r.get("ok") == "YES")
        part = sum(1 for r in rows if r.get("ok") == "PARTIAL")
        L.append(f"- **{label}**: Đạt {ok}, Đạt một phần {part}, Tổng {len(rows)} câu")
    L.append("\n---\n")

    for model_id, label in MODELS:
        L.append(f"\n## {label}\n")
        for q in QUESTIONS:
            row = next((r for r in results if r["model_id"] == model_id and r["id"] == q["id"]), None)
            L.append(f"### {q['id']} — {q['category']}")
            L.append(f"**Câu hỏi:** {q['question']}")
            if not row:
                L.append("> (không có kết quả)")
            elif "error" in row:
                L.append(f"**Lỗi:** {row['error']}")
            else:
                L.append(f"- **Intent:** `{row.get('intent')}` | Confidence: `{row.get('confidence')}` "
                         f"| Ambiguous: `{row.get('ambiguous')}` | Insufficient: `{row.get('insufficient_context')}`")
                L.append(f"- **Entities:** {', '.join(row.get('entities') or []) or '-'}")
                L.append(f"- **Citations:** {row.get('citations')} | Lineage down: {row.get('lineage_downstream')} "
                         f"| up: {row.get('lineage_upstream')}")
                L.append(f"- **Trả lời:** {row.get('answer')}")
            L.append("")
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default=BASE_URL)
    ap.add_argument("--out", default="/tmp/chatbot_test_suite.md")
    args = ap.parse_args()
    url = args.base_url.rstrip("/")

    results: list[dict] = []

    async def _go() -> None:
        _TOKEN["value"] = await login(url)
        print("[login] ok")
        async with httpx.AsyncClient(base_url=url, timeout=180) as client:
            for model_id, label in MODELS:
                print(f"\n=== MODEL: {label} ===")
                for q in QUESTIONS:
                    print(f"  {q['id']} ... ", end="", flush=True)
                    resp = await ask(client, q["question"], model_id)
                    resp.update({"model_id": model_id, "model_label": label, "id": q["id"], "question": q["question"]})
                    if "error" in resp:
                        resp["ok"] = "NO"
                    elif resp.get("ambiguous") or resp.get("insufficient_context"):
                        resp["ok"] = "PARTIAL"
                    else:
                        resp["ok"] = "YES"
                    print(resp.get("ok"), resp.get("intent"))
                    results.append(resp)

    try:
        asyncio.run(_go())
    except Exception as e:  # noqa: BLE001
        print("FAILED:", e)

    out = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(render_report(results))
    with open(out.replace(".md", ".json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n[ok] report written to {out} (+ .json)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
