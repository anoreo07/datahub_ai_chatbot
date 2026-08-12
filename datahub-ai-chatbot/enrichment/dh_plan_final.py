"""Build final DRY-RUN mutation plan for DataHub metadata enrichment.

Categories:
  1. glossary_term domain attachment   (aspect: domains)
  2. dataset schema PK (primaryKeys + isPartOfKey)   (aspect: schemaMetadata)
  3. dataset schema FK (foreignKeys)                 (aspect: schemaMetadata)

Sources of evidence: mock-data yaml (verified source), current DataHub state (snapshot).
DRY only — produces plan JSON; no writes.
"""
from __future__ import annotations

import hashlib
import json
import re
import urllib.parse
from pathlib import Path

import yaml

MOCK = Path(__file__).resolve().parent.parent.parent / "mock-data"
SNAP = "enrichment/datahub_snapshot_raw.json"
OUT = "enrichment/datahub_enrichment_dryrun_plan.json"

DOMAIN_MAP = {
    "CUNG ỨNG (NĐH)": "urn:li:domain:cungngnh",
    "CUNG ỨNG (TT)": "urn:li:domain:cungngtt",
    "HẬU MÃI": "urn:li:domain:humi",
    "KINH DOANH": "urn:li:domain:kinhdoanh",
    "LOGISTIC": "urn:li:domain:logistic",
    "PHÁT TRIỂN XE": "urn:li:domain:phttrinxe",
    "SẢN XUẤT": "urn:li:domain:snxut",
    "TÀI CHÍNH": "urn:li:domain:tichnh",
    "VGREEN": "urn:li:domain:vgreen",
}


def load_datasets() -> list[dict]:
    out = []
    for f in sorted((MOCK / "datasets").glob("*.yaml")):
        out.extend(yaml.safe_load(f.read_text()).get("datasets", []))
    return out


def load_glossary() -> list[dict]:
    out = []
    for f in sorted((MOCK / "glossary").glob("*.yaml")):
        out.extend(yaml.safe_load(f.read_text()).get("glossary_terms", []))
    return out


def main() -> None:
    snap = json.load(open(SNAP))
    datasets_src = load_datasets()
    glossary_src = load_glossary()

    ds_name_to_urn = {}
    for d in snap["datasets"]:
        name = (d.get("properties") or {}).get("name") or d.get("name")
        ds_name_to_urn[name] = d["urn"]

    term_by_urn = {t["urn"]: t for t in snap["glossary_terms"]}
    term_current_domain = {}
    for t in snap["glossary_terms"]:
        d = t.get("domain") or {}
        inner = (d.get("domain") or {}) if isinstance(d, dict) else {}
        term_current_domain[t["urn"]] = inner.get("urn")

    src_term_by_lower = {}
    for t in glossary_src:
        src_term_by_lower.setdefault((t.get("name") or "").lower(), t)

    mutations = []

    # ---------------- 1. glossary term domain ----------------
    for t in snap["glossary_terms"]:
        name = (t.get("properties") or {}).get("name") or t.get("name") or ""
        lower = name.lower()
        src = src_term_by_lower.get(lower)
        if not src:
            mutations.append({
                "mut_id": f"glossary_domain:{t['urn']}",
                "entity_urn": t["urn"], "entity_type": "glossary_term",
                "property": "domain",
                "old_value": term_current_domain.get(t["urn"]), "new_value": None,
                "status": "SKIP_NO_SOURCE", "confidence": "n/a",
                "evidence": "term not present in verified source mock-data/glossary",
                "reason": "no source metadata to attach domain; leave UNKNOWN",
            })
            continue
        dom_name = (src.get("domain") or "").strip()
        if not dom_name:
            mutations.append({
                "mut_id": f"glossary_domain:{t['urn']}",
                "entity_urn": t["urn"], "entity_type": "glossary_term",
                "property": "domain",
                "old_value": term_current_domain.get(t["urn"]), "new_value": None,
                "status": "SKIP_NO_DOMAIN_IN_SOURCE", "confidence": "n/a",
                "evidence": "source yaml defines no domain for this term",
                "reason": "no evidence to attach a domain",
            })
            continue
        durn = DOMAIN_MAP.get(dom_name.upper())
        if not durn:
            mutations.append({
                "mut_id": f"glossary_domain:{t['urn']}",
                "entity_urn": t["urn"], "entity_type": "glossary_term",
                "property": "domain",
                "old_value": term_current_domain.get(t["urn"]),
                "new_value": f"<unmapped:{dom_name}>",
                "status": "SKIP_UNMAPPED_DOMAIN", "confidence": "n/a",
                "evidence": f"source domain '{dom_name}' has no matching DataHub domain entity",
                "reason": "domain entity not found; do not fabricate",
            })
            continue
        cur = term_current_domain.get(t["urn"])
        if cur == durn:
            mutations.append({
                "mut_id": f"glossary_domain:{t['urn']}",
                "entity_urn": t["urn"], "entity_type": "glossary_term",
                "property": "domain", "old_value": cur, "new_value": durn,
                "status": "SKIP_ALREADY_CORRECT", "confidence": "CONFIRMED",
                "evidence": f"source yaml domain '{dom_name}'; current DataHub domain matches",
                "reason": "idempotent skip",
            })
        elif cur:
            mutations.append({
                "mut_id": f"glossary_domain:{t['urn']}",
                "entity_urn": t["urn"], "entity_type": "glossary_term",
                "property": "domain",
                "old_value": cur, "new_value": durn,
                "status": "SKIP_CONFLICT_EXISTING", "confidence": "CONFIRMED(source)/conflict",
                "evidence": f"source yaml domain '{dom_name}' vs current DataHub '{cur}'",
                "reason": "existing domain value is valid; no-overwrite policy (requires explicit migration rule)",
            })
        else:
            mutations.append({
                "mut_id": f"glossary_domain:{t['urn']}",
                "entity_urn": t["urn"], "entity_type": "glossary_term",
                "property": "domain",
                "old_value": None, "new_value": durn,
                "status": "PLANNED_WRITE", "confidence": "CONFIRMED",
                "evidence": f"source yaml glossary/{lower} domain: '{dom_name}'",
                "reason": "verified source defines term domain; DataHub currently has none",
            })

    # ---------------- PK / FK from source ----------------
    fields_by_ds = {d["name"]: {c.get("name") for c in d.get("columns", [])} for d in datasets_src}
    pk_by_ds: dict[str, set[str]] = {}
    # pass 1: collect PKs
    for d in datasets_src:
        for col in d.get("columns", []):
            bd = (col.get("business_definition") or "").strip()
            if bd and "khóa chính" in bd.lower():
                pk_by_ds.setdefault(d["name"], set()).add(col["name"])
    # pass 2: collect FKs (needs full pk_by_ds)
    fk_by_ds: dict[str, list[dict]] = {}
    for d in datasets_src:
        name = d["name"]
        for col in d.get("columns", []):
            bd = (col.get("business_definition") or "").strip()
            if not bd:
                continue
            bd_l = bd.lower()
            fld = col["name"]
            m = re.search(r"tham chiếu (?:đến|tới)\s*([\w.]+)", bd_l)
            if m and m.group(1) in fields_by_ds:
                ref = m.group(1)
                ref_field = fld
                if ref_field in fields_by_ds.get(ref, set()):
                    fk_by_ds.setdefault(name, []).append({
                        "source_field": fld,
                        "ref_dataset": ref,
                        "ref_field": ref_field,
                    })
                else:
                    # table-level confirmed FK; ref field = PK of target if known
                    tgt_pk = pk_by_ds.get(ref)
                    if tgt_pk and len(tgt_pk) == 1:
                        fk_by_ds.setdefault(name, []).append({
                            "source_field": fld,
                            "ref_dataset": ref,
                            "ref_field": sorted(tgt_pk)[0],
                            "ref_field_derived": True,
                        })

    # schema-current info from snapshot
    cur_schema = {}
    for d in snap["datasets"]:
        name = (d.get("properties") or {}).get("name") or d.get("name")
        sm = d.get("schemaMetadata") or {}
        cur_schema[name] = {
            "version": sm.get("version", 0),
            "primaryKeys": sm.get("primaryKeys") or [],
            "fields": sm.get("fields") or [],
            "schemaName": sm.get("name"),
            "platformUrn": sm.get("platformUrn"),
        }

    all_ds = sorted(set(pk_by_ds) | set(fk_by_ds))
    for name in all_ds:
        urn = ds_name_to_urn.get(name)
        if not urn:
            mutations.append({
                "mut_id": f"schema:{name}",
                "entity_urn": "<unknown>", "entity_type": "dataset",
                "property": "schemaMetadata(primaryKeys/foreignKeys)",
                "old_value": None, "new_value": None,
                "status": "SKIP_UNKNOWN_URN", "confidence": "n/a",
                "evidence": "dataset name not found in DataHub",
                "reason": "cannot resolve URN",
            })
            continue
        pks = sorted(pk_by_ds.get(name, set()))
        fks = fk_by_ds.get(name, [])
        cur = cur_schema.get(name, {})
        cur_pks = cur.get("primaryKeys") or []
        cur_fk_names = []
        want_fk_names = sorted(f"{k['source_field']}->{k['ref_dataset']}.{k['ref_field']}" for k in fks)
        if pks == cur_pks and not want_fk_names:
            # no change: not planned (shouldn't happen since no pks exist yet)
            pass
        need_pk = bool(pks) and pks != sorted(cur_pks)
        need_fk = bool(fks) and want_fk_names != cur_fk_names
        if not (need_pk or need_fk):
            continue
        pk_ev = {
            f"{name}.{f}": "explicit 'Khóa chính' in source business_definition" for f in pks
        } if need_pk else {}
        fk_ev = {
            f"{name}.{k['source_field']}->{k['ref_dataset']}.{k['ref_field']}":
                ("explicit 'tham chiếu đến <table>' in source business_definition"
                 + ("; ref field derived = target PK" if k.get("ref_field_derived") else ""))
            for k in fks
        } if need_fk else {}
        mutations.append({
            "mut_id": f"schema:{urn}",
            "entity_urn": urn, "entity_type": "dataset",
            "property": "schemaMetadata(primaryKeys, foreignKeys, field.isPartOfKey)",
            "old_value": {
                "primaryKeys": cur_pks,
                "foreignKeys": cur_fk_names,
                "isPartOfKey_fields": [],
            },
            "new_value": {
                "primaryKeys": pks,
                "foreignKeys": want_fk_names,
                "isPartOfKey_fields": pks,
            },
            "status": "PLANNED_WRITE", "confidence": "CONFIRMED",
            "evidence": {**pk_ev, **fk_ev},
            "reason": "primary/foreign key metadata explicitly declared in verified source "
                      "(mock-data/*.yaml business_definition); DataHub schema currently lacks them",
        })

    plan = {
        "dry_run": True,
        "generated_at": __import__("datetime").datetime.now().isoformat(),
        "summary": {
            "total_mutations": len(mutations),
        },
        "mutations": mutations,
    }
    with open(OUT, "w") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
    print(f"wrote {OUT}: {len(mutations)} mutations")
    # quick stats
    from collections import Counter
    c = Counter(m["status"] for m in mutations)
    for k, v in c.most_common():
        print(f"  {k}: {v}")
    # list planned writes
    planned = [m for m in mutations if m["status"] == "PLANNED_WRITE"]
    print(f"\nPLANNED_WRITE total: {len(planned)}")
    for m in planned:
        if m["entity_type"] == "glossary_term":
            print("  TERM ", m["entity_urn"], "->", m["new_value"])
        else:
            print("  SCHEMA", m["property"], m["entity_urn"], "old:", m["old_value"], "new:", m["new_value"])


if __name__ == "__main__":
    main()