"""Compare DataHub state vs verified source (mock-data yaml + ingest_real_datahub.py semantics).

Outputs gap reports: lineage diff, PK/FK candidates, owner ids, glossary domain mapping.
"""
from __future__ import annotations

import json
import re
import sys
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


def load_domain_map() -> dict[str, str]:
    # name.upper() -> domain urn key (as ingested)
    m = {}
    for f in sorted((MOCK / "domains").glob("*.yaml")):
        data = yaml.safe_load(f.read_text())
        name = data.get("domain", "")
        key = re.sub(r"[^A-Za-z0-9]+", "", name.lower()) or "unknown"
        m[name.upper()] = key
    return m


def dataset_urn(name: str, platform: str = "redshift") -> str:
    return f"urn:li:dataset:(urn:li:dataPlatform:{platform.lower()},{name},PROD)"


def main() -> None:
    datasets = load_datasets()
    glossary = load_glossary()
    dom_map = load_domain_map()
    print(f"source datasets: {len(datasets)}, glossary: {len(glossary)}")

    snap = json.load(open("enrichment/datahub_snapshot_raw.json"))
    dh_ds_by_name = {}
    for ds in snap["datasets"]:
        name = (ds.get("properties") or {}).get("name") or ds.get("name")
        dh_ds_by_name[name] = ds["urn"]
    dh_lineage = snap["lineage"]
    print(f"datahub datasets: {len(dh_ds_by_name)}, lineage keys: {len(dh_lineage)}")

    # --- expected lineage from source (same semantics as ingest script) ---
    urn_by_name = {ds["name"]: dataset_urn(ds["name"], "redshift") for ds in datasets}
    expected_up: dict[str, set[str]] = {}
    for ds in datasets:
        name = ds["name"]
        ups = set()
        for col in ds.get("columns", []):
            bd = (col.get("business_definition") or "").lower()
            m = re.search(r"tham chiếu đến (\w+)", bd)
            if m:
                ref = m.group(1)
                for tn, tu in urn_by_name.items():
                    if tn.lower() == ref.lower() and tu != urn_by_name[name]:
                        ups.add(tu)
        expected_up[name] = ups

    present_up = 0
    missing_up = 0
    extra_up = 0
    missing_details = []
    for name, ups in expected_up.items():
        if not ups:
            continue
        dh = dh_lineage.get(urn_by_name[name], {})
        dh_up = []
        for rel in (dh.get("upstream", {}) or {}).get("relationships", []) or []:
            dh_up.append(rel["entity"]["urn"])
        dh_set = set(dh_up)
        missing = ups - dh_set
        extra = dh_set - ups
        if missing:
            missing_up += 1
            missing_details.append((name, sorted(missing)))
        if extra:
            extra_up += 1
        if ups and dh_set & ups:
            present_up += 1
    print(f"\nexpected up-streams from source: {sum(bool(v) for v in expected_up.values())} datasets")
    print(f"datasets with expected lineage present in DH: {present_up}, missing some: {missing_up}, extra: {extra_up}")

    # --- PK / FK candidates from explicit source text ---
    pk_candidates = []
    fk_candidates = []
    for ds in datasets:
        name = ds["name"]
        for col in ds.get("columns", []):
            bd = (col.get("business_definition") or "") or (col.get("description") or "")
            bd_l = bd.lower()
            fld = col.get("name", "")
            if "khóa chính" in bd_l or "khóa chính" in bd_l or "primary key" in bd_l:
                pk_candidates.append((name, fld, bd.strip()))
            m = re.search(r"tham chiếu (?:đến|tới) (\w+)", bd_l)
            if m or "khóa ngoại" in bd_l:
                ref = m.group(1) if m else (
                    re.search(r"khóa ngoại[^,]*(?:tham chiếu)?\s*(?:đến|tới)?\s*(\w+)", bd_l).group(1)
                    if re.search(r"khóa ngoại[^,]*(?:tham chiếu)?\s*(?:đến|tới)?\s*(\w+)", bd_l) else None
                )
                fk_candidates.append((name, fld, ref, bd.strip()))
    print(f"\nPK candidates (explicit 'khóa chính' in source): {len(pk_candidates)}")
    for name, fld, bd in pk_candidates[:20]:
        print(f"  {name}.{fld} :: {bd}")
    print(f"\nFK candidates (explicit 'tham chiếu/khóa ngoại' in source): {len(fk_candidates)}")
    for name, fld, ref, bd in fk_candidates[:25]:
        print(f"  {name}.{fld} -> {ref} :: {bd}")

    # --- glossary domain mapping ---
    uw = {}
    for term in glossary:
        dom = (term.get("domain") or "").upper()
        key = dom_map.get(dom, None)
        uw[term["name"].lower()] = {"domain_name": dom, "domain_key": key}
    no_map = [n for n, v in uw.items() if v["domain_key"] is None]
    mapped = [n for n, v in uw.items() if v["domain_key"] is not None]
    print(f"\nglossary terms source: {len(uw)}, with mappable domain: {len(mapped)}, unmappable: {no_map}")

    # term urn helper (matches ingestion _glossary_urn)
    def term_urn(lower: str) -> str:
        import urllib.parse
        return f"urn:li:glossaryTerm:{urllib.parse.quote(lower)}"

    # check terms with domain already in DataHub
    terms_with_dh_domain = set()
    for t in snap["glossary_terms"]:
        d = (t.get("domain") or {})
        if isinstance(d, dict) and (d.get("domain") or {}):
            terms_with_dh_domain.add(t["urn"])
    print(f"terms already have domain in DH: {sorted(terms_with_dh_domain)}")

    # Output JSON gap file
    gap = {
        "pk_candidates": [{"dataset": n, "field": f, "evidence": bd} for n, f, bd in pk_candidates],
        "fk_candidates": [{"dataset": n, "field": f, "referenced_table": r, "evidence": bd} for n, f, r, bd in fk_candidates],
        "glossary_domain": {k: v for k, v in uw.items()},
        "expected_lineage": {n: sorted(ups) for n, ups in expected_up.items()},
        "lineage_missing": missing_details,
    }
    with open("enrichment/source_gap_analysis.json", "w") as f:
        json.dump(gap, f, ensure_ascii=False, indent=2)
    print("\nwrote enrichment/source_gap_analysis.json")


if __name__ == "__main__":
    main()