"""Build the FINAL DataHub enrichment plan (validated, no writes).

Categories:
  1. glossary_term domain   (aspect: domains)          — source: mock-data/glossary/*.yaml domain
  2. dataset domain         (aspect: domains)          — source: mock-data/datasets/*.yaml domain
  3. dataset schema PK/FK   (aspect: schemaMetadata)   — source: business_definition explicit text

Rules (deterministic, auditable, no hallucination):
  - PK : field whose source business_definition contains 'khóa chính'
  - FK : field whose source business_definition contains 'tham chiếu đến <table>' or
         'khóa ngoại … tham chiếu đến <table>' where <table> is an existing dataset
  - FK ref field : same-name field in target if present; else target's single PK (mark DERIVED)
  - domain value is only written when a live DataHub domain entity exists for the mapped name
  - if source has no evidence -> SKIP_*, never fabricate
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

import yaml

MOCK = Path(__file__).resolve().parent.parent.parent / "mock-data"
SNAP = "enrichment/datahub_snapshot_fresh.json"
OUT = "enrichment/datahub_enrichment_plan_final.json"

DOMAIN_ENTITY_URNS = frozenset({
    "urn:li:domain:cungngnh", "urn:li:domain:cungngtt", "urn:li:domain:humi",
    "urn:li:domain:kinhdoanh", "urn:li:domain:logistic", "urn:li:domain:phttrinxe",
    "urn:li:domain:snxut", "urn:li:domain:tichnh", "urn:li:domain:vgreen",
})


def load_src_datasets() -> list[dict]:
    return [d for f in sorted((MOCK / "datasets").glob("*.yaml")) for d in yaml.safe_load(f.read_text()).get("datasets", [])]


def load_src_glossary() -> list[dict]:
    return [t for f in sorted((MOCK / "glossary").glob("*.yaml")) for t in yaml.safe_load(f.read_text()).get("glossary_terms", [])]


def load_src_domains() -> list[dict]:
    out = []
    for f in sorted((MOCK / "domains").glob("*.yaml")):
        d = yaml.safe_load(f.read_text())
        out.append({"name": d.get("domain", "")})
    return out


def domain_urn(name: str) -> str:
    key = re.sub(r"[^A-Za-z0-9]+", "", name.lower()) or "unknown"
    return f"urn:li:domain:{key}"


def dataset_urn(name: str) -> str:
    return f"urn:li:dataset:(urn:li:dataPlatform:redshift,{name},PROD)"


def main() -> None:
    snap = json.load(open(SNAP))
    src_datasets = load_src_datasets()
    src_glossary = load_src_glossary()
    src_domain_names = {(d["name"].upper()): d["name"] for d in load_src_domains()}

    dh_datasets = {d["urn"]: d for d in snap["datasets"]}
    dh_by_name = {}
    for d in snap["datasets"]:
        nm = (d.get("properties") or {}).get("name") or d.get("name")
        dh_by_name.setdefault(nm, []).append(d)
    dh_terms = {t["urn"]: t for t in snap["glossary_terms"]}
    dh_term_by_lower = {}
    for t in snap["glossary_terms"]:
        nm = (t.get("properties") or {}).get("name") or t.get("name")
        dh_term_by_lower.setdefault((nm or "").lower().strip(), t)

    src_ds = {d["name"]: d for d in src_datasets}
    src_term_by_lower = {}
    for t in src_glossary:
        src_term_by_lower.setdefault((t.get("name") or "").lower().strip(), t)

    # current values
    def cur_domain(entity: dict) -> str | None:
        d = entity.get("domain")
        return (d.get("domain") or {}).get("urn") if isinstance(d, dict) and (d.get("domain") or {}) else None

    mutations = []

    # ---------------- 1. glossary term domain ----------------
    for urn, t in dh_terms.items():
        nm = (t.get("properties") or {}).get("name") or t.get("name")
        lower = (nm or "").lower().strip()
        src = src_term_by_lower.get(lower)
        cur = cur_domain(t)
        mid = f"glossary_domain:{urn}"
        if not src:
            mutations.append({"mut_id": mid, "entity_urn": urn, "entity_type": "glossary_term",
                              "property": "domain", "old_value": cur, "new_value": None,
                              "status": "SKIP_NO_SOURCE", "confidence": "n/a",
                              "evidence": "term not present in verified source mock-data/glossary",
                              "reason": "no source metadata; leave UNKNOWN"})
            continue
        dom_name = (src.get("domain") or "").strip()
        if not dom_name:
            mutations.append({"mut_id": mid, "entity_urn": urn, "entity_type": "glossary_term",
                              "property": "domain", "old_value": cur, "new_value": None,
                              "status": "SKIP_NO_DOMAIN_IN_SOURCE", "confidence": "n/a",
                              "evidence": f"source term {nm!r} has no domain field", "reason": "no evidence"})
            continue
        want = domain_urn(dom_name)
        if want not in DOMAIN_ENTITY_URNS:
            mutations.append({"mut_id": mid, "entity_urn": urn, "entity_type": "glossary_term",
                              "property": "domain", "old_value": cur, "new_value": None,
                              "status": "SKIP_UNMAPPED_DOMAIN", "confidence": "n/a",
                              "evidence": f"source domain {dom_name!r} -> {want} not a live DataHub domain",
                              "reason": "do not fabricate domain entity"})
            continue
        if cur == want:
            mutations.append({"mut_id": mid, "entity_urn": urn, "entity_type": "glossary_term",
                              "property": "domain", "old_value": cur, "new_value": want,
                              "status": "SKIP_ALREADY_CORRECT", "confidence": "CONFIRMED",
                              "evidence": f"source domain {dom_name!r} matches DataHub", "reason": "idempotent"})
        elif cur:
            mutations.append({"mut_id": mid, "entity_urn": urn, "entity_type": "glossary_term",
                              "property": "domain", "old_value": cur, "new_value": want,
                              "status": "SKIP_CONFLICT_EXISTING", "confidence": "CONFLICT",
                              "evidence": f"source {dom_name!r} vs DataHub {cur}", "reason": "no-overwrite policy"})
        else:
            mutations.append({"mut_id": mid, "entity_urn": urn, "entity_type": "glossary_term",
                              "property": "domain", "old_value": None, "new_value": want,
                              "status": "PLANNED_WRITE", "confidence": "CONFIRMED",
                              "evidence": f"source glossary/{lower} domain: {dom_name!r}",
                              "reason": "verified source defines term domain; DataHub has none"})

    # ---------------- 2. dataset domain ----------------
    for name, urn in sorted(((n, dataset_urn(n)) for n in dh_by_name)):
        ds = dh_by_name[name][0]
        cur = cur_domain(ds)
        src = src_ds.get(name)
        mid = f"dataset_domain:{urn}"
        if not src:
            mutations.append({"mut_id": mid, "entity_urn": urn, "entity_type": "dataset",
                              "property": "domain", "old_value": cur, "new_value": None,
                              "status": "SKIP_NO_SOURCE", "confidence": "n/a",
                              "evidence": "not in source", "reason": "no evidence"})
            continue
        dom_name = (src.get("domain") or "").strip()
        if not dom_name:
            mutations.append({"mut_id": mid, "entity_urn": urn, "entity_type": "dataset",
                              "property": "domain", "old_value": cur, "new_value": None,
                              "status": "SKIP_NO_DOMAIN_IN_SOURCE", "confidence": "n/a",
                              "evidence": "source has no domain", "reason": "no evidence"})
            continue
        # resolve: exact name first, then base name before '(' (deterministic)
        want = None
        if dom_name.upper() in src_domain_names:
            want = domain_urn(dom_name)
        else:
            base = dom_name.split("(")[0].strip()
            if base.upper() in src_domain_names:
                want = domain_urn(base)
        if want is None or want not in DOMAIN_ENTITY_URNS:
            mutations.append({"mut_id": mid, "entity_urn": urn, "entity_type": "dataset",
                              "property": "domain", "old_value": cur, "new_value": None,
                              "status": "SKIP_UNMAPPED_DOMAIN", "confidence": "n/a",
                              "evidence": f"source domain {dom_name!r} unmappable to live domain entity",
                              "reason": "do not fabricate"})
            continue
        if cur == want:
            mutations.append({"mut_id": mid, "entity_urn": urn, "entity_type": "dataset",
                              "property": "domain", "old_value": cur, "new_value": want,
                              "status": "SKIP_ALREADY_CORRECT", "confidence": "CONFIRMED",
                              "evidence": f"source domain {dom_name!r} already attached", "reason": "idempotent"})
        elif cur:
            mutations.append({"mut_id": mid, "entity_urn": urn, "entity_type": "dataset",
                              "property": "domain", "old_value": cur, "new_value": want,
                              "status": "SKIP_CONFLICT_EXISTING", "confidence": "CONFLICT",
                              "evidence": f"source {dom_name!r} vs DataHub {cur}", "reason": "no-overwrite"})
        else:
            mutations.append({"mut_id": mid, "entity_urn": urn, "entity_type": "dataset",
                              "property": "domain", "old_value": None, "new_value": want,
                              "status": "PLANNED_WRITE", "confidence": "CONFIRMED",
                              "evidence": f"source dataset yaml domain: {dom_name!r} -> {want}",
                              "reason": "verified source defines dataset domain; DataHub has none"})

    # ---------------- 3. dataset schema PK / FK ----------------
    fields_by_ds = {d["name"]: {c.get("name") for c in d.get("columns", [])} for d in src_datasets}
    pk_by_ds: dict[str, set[str]] = {}
    fk_raw_by_ds: dict[str, list[dict]] = {}
    for ds in src_datasets:
        nm = ds["name"]
        for col in ds.get("columns", []):
            fld = col.get("name", "")
            bd = (col.get("business_definition") or "").strip()
            bd_l = bd.lower()
            if "khóa chính" in bd_l:
                pk_by_ds.setdefault(nm, set()).add(fld)
            is_fk_phrase = "khóa ngoại" in bd_l
            m = re.search(r"tham chiếu (?:đến|tới)\s*([\w.]{1,64})", bd_l)
            target = None
            if m:
                cand = m.group(1)
                if cand in fields_by_ds:
                    target = cand
            if is_fk_phrase and not m:
                m2 = re.search(r"khóa ngoại.{0,40}?tham chiếu (?:đến|tới)\s*([\w.]{1,64})", bd_l)
                if m2 and m2.group(1) in fields_by_ds:
                    target = m2.group(1)
            if target is None:
                if is_fk_phrase:
                    fk_raw_by_ds.setdefault(nm, []).append({
                        "source_field": fld, "ref_dataset": None, "evidence": bd,
                        "reason": "khóa ngoại without resolvable target dataset",
                    })
                continue
            ref_field = fld
            derived = False
            if ref_field not in fields_by_ds[target]:
                tgt_pk = pk_by_ds.get(target)
                if tgt_pk and len(tgt_pk) == 1:
                    ref_field = sorted(tgt_pk)[0]
                    derived = True
                else:
                    fk_raw_by_ds.setdefault(nm, []).append({
                        "source_field": fld, "ref_dataset": target, "evidence": bd,
                        "reason": "target exists but ref field unknown (no same-name field, no single-PK)",
                    })
                    continue
            fk_raw_by_ds.setdefault(nm, []).append({
                "source_field": fld, "ref_dataset": target, "ref_field": ref_field,
                "ref_field_derived": derived, "evidence": bd,
            })

    current_schema = {}
    for urn, d in dh_datasets.items():
        nm = (d.get("properties") or {}).get("name") or d.get("name")
        sm = d.get("schemaMetadata") or {}
        current_schema[nm] = {
            "version": sm.get("version", 0),
            "primaryKeys": sm.get("primaryKeys") or [],
            "fields": {f.get("fieldPath"): f for f in sm.get("fields") or []},
        }

    all_ds = sorted(set(pk_by_ds) | set(k for k, v in fk_raw_by_ds.items() if any(x.get("ref_dataset") for x in v)))
    for name in all_ds:
        urn = dataset_urn(name)
        pks = sorted(pk_by_ds.get(name, set()))
        fks = [x for x in fk_raw_by_ds.get(name, []) if x.get("ref_field")]
        cur_sc = current_schema.get(name, {})
        cur_pks = cur_sc.get("primaryKeys") or []
        cur_fields = cur_sc.get("fields") or {}
        mid = f"schema:{urn}"

        # skip unresolved FKs documented separately (SKIP)
        unresolved = [x for x in fk_raw_by_ds.get(name, []) if not x.get("ref_field")]
        want_fk_set = sorted(f"{x['source_field']}->{x['ref_dataset']}.{x['ref_field']}" for x in fks)

        need_pk = bool(pks) and sorted(pks) != sorted(cur_pks)
        need_fk = bool(want_fk_set)

        # fields must exist in DataHub schema
        missing_pk = [p for p in pks if p not in cur_fields]
        missing_fk_src = [x["source_field"] for x in fks if x["source_field"] not in cur_fields]
        missing_fk_ref = [f"{x['ref_dataset']}.{x['ref_field']}" for x in fks
                          if x["ref_field"] not in current_schema.get(x["ref_dataset"], {}).get("fields", {})]

        if not (need_pk or need_fk):
            continue
        if missing_pk or missing_fk_src or missing_fk_ref:
            mutations.append({
                "mut_id": mid, "entity_urn": urn, "entity_type": "dataset",
                "property": "schemaMetadata(primaryKeys/foreignKeys)",
                "old_value": {"primaryKeys": cur_pks}, "new_value": None,
                "status": "SKIP_SCHEMA_MISMATCH", "confidence": "n/a",
                "evidence": f"source declares but DataHub schema lacks fields: pk={missing_pk}, fk_src={missing_fk_src}, fk_ref={missing_fk_ref}",
                "reason": "cannot write constraint referencing missing field",
            })
            continue

        pk_ev = {f"{name}.{p}": "explicit 'Khóa chính' in source business_definition" for p in pks}
        fk_ev = {f"{name}.{f['source_field']}->{f['ref_dataset']}.{f['ref_field']}":
                 ("explicit 'tham chiếu đến <table>' in source business_definition"
                  + ("; ref field DERIVED = target single PK" if f["ref_field_derived"] else "")) for f in fks}
        mutations.append({
            "mut_id": mid, "entity_urn": urn, "entity_type": "dataset",
            "property": "schemaMetadata(primaryKeys, foreignKeys, field.isPartOfKey)",
            "old_value": {"primaryKeys": cur_pks, "foreignKeys": [], "isPartOfKey_fields": []},
            "new_value": {"primaryKeys": pks, "foreignKeys": want_fk_set, "isPartOfKey_fields": pks},
            "status": "PLANNED_WRITE", "confidence": "CONFIRMED",
            "evidence": {**pk_ev, **fk_ev},
            "reason": "PK/FK explicitly declared in verified source business_definition; DataHub schema lacks them",
        })
        for u in unresolved:
            mutations.append({
                "mut_id": f"schema_skip:{name}.{u['source_field']}", "entity_urn": urn, "entity_type": "dataset",
                "property": "foreignKey", "old_value": None, "new_value": None,
                "status": "SKIP_FK_UNRESOLVED", "confidence": "n/a",
                "evidence": u["evidence"], "reason": u["reason"],
            })

    plan = {
        "dry_run": True,
        "generated_at": __import__("datetime").datetime.now().isoformat(),
        "note": "values only from verified source (mock-data yaml) or DataHub; nothing hallucinated",
    }
    stats = Counter(m["status"] for m in mutations)
    plan["summary"] = {"total_mutations": len(mutations), "by_status": dict(stats)}
    plan["mutations"] = mutations

    with open(OUT, "w") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)

    print(f"wrote {OUT}: {len(mutations)} mutations")
    for k, v in stats.most_common():
        print(f"  {k}: {v}")
    planned = [m for m in mutations if m["status"] == "PLANNED_WRITE"]
    print(f"\nPLANNED_WRITE total: {len(planned)}")
    tc = Counter(m["entity_type"] + ":" + m["property"] for m in planned)
    print(dict(tc))
    for m in planned:
        if m["entity_type"] == "glossary_term":
            print("  TERMDOMAIN", m["entity_urn"], "->", m["new_value"])
        elif m["property"] == "domain":
            print("  DSDOMAIN  ", m["entity_urn"], "->", m["new_value"])
        else:
            print("  SCHEMA    ", m["entity_urn"], "->", {k: m["new_value"][k] for k in ("primaryKeys", "foreignKeys")})


if __name__ == "__main__":
    main()