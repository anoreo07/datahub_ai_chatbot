"""Tighten the enrichment candidates: PK/FK validation vs existing datasets & fields;
reconcile glossary terms (source vs DataHub); glossary domain mapping."""
from __future__ import annotations

import json
import re
import urllib.parse
from pathlib import Path

import yaml

MOCK = Path(__file__).resolve().parent.parent.parent / "mock-data"


def load_datasets() -> list[dict]:
    out = []
    for f in sorted((MOCK / "datasets").glob("*.yaml")):
        data = yaml.safe_load(f.read_text())
        out.extend(data.get("datasets", []))
    return out


def load_glossary() -> list[dict]:
    out = []
    for f in sorted((MOCK / "glossary").glob("*.yaml")):
        data = yaml.safe_load(f.read_text())
        out.extend(data.get("glossary_terms", []))
    return out


def term_urn(lower: str) -> str:
    return f"urn:li:glossaryTerm:{urllib.parse.quote(lower)}"


def main() -> None:
    datasets = load_datasets()
    glossary = load_glossary()
    ds_names = {d["name"] for d in datasets}
    ds_by_name = {d["name"]: d for d in datasets}
    fields_by_ds = {d["name"]: {c.get("name") for c in d.get("columns", [])} for d in datasets}

    snap = json.load(open("enrichment/datahub_snapshot_raw.json"))
    dh_terms = snap["glossary_terms"]
    dh_term_by_lower = {}
    for t in dh_terms:
        name = (t.get("properties") or {}).get("name") or t.get("name") or ""
        dh_term_by_lower[name.lower()] = t

    # ---------------- PK: explicit 'khóa chính' ----------------
    pks = []
    for d in datasets:
        for col in d.get("columns", []):
            bd = (col.get("business_definition") or "").strip()
            if not bd:
                continue
            if "khóa chính" in bd.lower():
                pks.append({"dataset": d["name"], "field": col["name"], "evidence": bd})
    print(f"PK candidates with explicit 'khóa chính': {len(pks)}")

    # ---------------- FK: target must be a real dataset ----------------
    fks = []
    fk_ambiguous = []
    for d in datasets:
        for col in d.get("columns", []):
            bd = (col.get("business_definition") or "").strip()
            if not bd:
                continue
            bd_l = bd.lower()
            is_fk_phrase = "khóa ngoại" in bd_l
            m = re.search(r"tham chiếu (?:đến|tới)\s*(\w+)", bd_l)
            target = None
            if m:
                cand = m.group(1)
                if cand in ds_names:
                    target = cand
                else:
                    # allow underscore-heavy names captured differently
                    m2 = re.search(r"tham chiếu (?:đến|tới)\s*([\w.]+)", bd_l)
                    if m2 and m2.group(1) in ds_names:
                        target = m2.group(1)
            if is_fk_phrase and not m:
                m3 = re.search(r"tham chiếu (?:đến|tới)\s*([\w.]+)", bd_l)
                target = m3.group(1) if m3 and m3.group(1) in ds_names else None
            if target:
                ref_field = col["name"]
                if ref_field in fields_by_ds.get(target, set()):
                    fks.append({
                        "dataset": d["name"],
                        "field": ref_field,
                        "ref_dataset": target,
                        "ref_field": ref_field,
                        "evidence": bd,
                    })
                else:
                    fk_ambiguous.append({
                        "dataset": d["name"],
                        "field": ref_field,
                        "ref_dataset": target,
                        "evidence": bd,
                    })
    print(f"FK confirmed candidates (target table + same-name field exist): {len(fks)}")
    if fk_ambiguous:
        print(f"FK table-confirmed but ref-field missing in target: {len(fk_ambiguous)}")
        for x in fk_ambiguous[:15]:
            print("   ", x)

    # also explicit FK to known dataset even without 'tham chiếu' word
    fk_only_phrase = []
    for d in datasets:
        for col in d.get("columns", []):
            bd = (col.get("business_definition") or "").strip()
            if not bd or "khóa ngoại" not in bd.lower():
                continue
            if any(k["dataset"] == d["name"] and k["field"] == col["name"] for k in fks):
                continue
            fk_only_phrase.append((d["name"], col["name"], bd))
    print(f"FK phrase-only no resolvable dataset: {len(fk_only_phrase)}")
    for n, f, bd in fk_only_phrase[:15]:
        print("   ", n, f, "::", bd)

    # ---------------- Glossary reconciliation ----------------
    src_by_lower = {}
    for t in glossary:
        k = (t.get("name") or "").lower()
        src_by_lower.setdefault(k, t)
    missing_in_dh = set(src_by_lower) - set(dh_term_by_lower)
    extra_in_dh = set(dh_term_by_lower) - set(src_by_lower)
    print(f"\nsource unique terms: {len(src_by_lower)}, DH terms: {len(dh_term_by_lower)}")
    print(f"source terms NOT in DH: {len(missing_in_dh)} -> {sorted(missing_in_dh)[:20]}")
    print(f"DH terms NOT in source: {len(extra_in_dh)} -> {sorted(extra_in_dh)[:30]}")

    domain_map = {
        "CUNG ỨNG (NĐH)": "urn:li:domain:cungngnh",
        "CUNG ỨNG (TT)": "urn:li:domain:cungngtt",
        "HẬU MÃI": "urn:li:domain:humi",
        "KINH DOANH": "urn:li:domain:kinhdoanh",
        "LOGISTIC": "urn:li:domain:logistic",
        "PHÁT TRIỂN XE": "urn:li:domain:phttrinxe",
        "SẢN XUẤT": "urn:li:domain:snxut",
        "TÀI CHÍNH": "urn:li:domain:tichnh",
        "VGreen": "urn:li:domain:vgreen",
    }
    # verify against actual DH domain entities from snapshot dataset domains
    dh_domain_names = {}
    for ds in snap["datasets"]:
        d = ds.get("domain") or {}
        if isinstance(d, dict):
            inner = d.get("domain") or {}
            if inner:
                dh_domain_names[inner["urn"]] = (inner.get("properties") or {}).get("name")
    print("\nDH domain entities seen on datasets:", json.dumps(dh_domain_names, ensure_ascii=False))

    to_attach = []
    already = []
    for lower, t in dh_term_by_lower.items():
        src = src_by_lower.get(lower)
        if not src:
            continue
        dom_name = (src.get("domain") or "").strip()
        if not dom_name:
            continue
        dkey = dom_name.upper()
        if dkey not in domain_map:
            print("   !! domain not in map:", dom_name, "term:", lower)
            continue
        durn = domain_map[dkey]
        current_d = ((t.get("domain") or {}).get("domain") or {}).get("urn")
        if current_d == durn:
            already.append(lower)
        else:
            to_attach.append({"term_urn": dh_term_by_lower[lower]["urn"], "term_name": lower, "domain_urn": durn})
    print(f"\nglossary domain: already correct: {len(already)}, to attach: {len(to_attach)}")
    # sample check for 3-way matching domain correctness
    for lower in ("3-way matching", "abc classification"):
        src = src_by_lower.get(lower)
        if src:
            print("   source domain for", lower, "=", src.get("domain"))

    out = {
        "pk": pks,
        "fk": fks,
        "fk_ref_field_missing": fk_ambiguous,
        "glossary_domain_attach": to_attach,
    }
    with open("enrichment/enrichment_plan_draft.json", "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("\nwrote enrichment/enrichment_plan_draft.json")


if __name__ == "__main__":
    main()