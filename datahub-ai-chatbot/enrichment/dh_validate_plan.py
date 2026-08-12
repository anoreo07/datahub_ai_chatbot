"""Validate every planned enrichment mutation against verified source + live DataHub state.

For each mutation in the dry-run plan:
  - resolve entity URN exists in DataHub
  - for schema writes: PK fields exist in DataHub schema; FK source+ref fields exist;
    target dataset exists; explicit source evidence for each PK/FK declared.
  - for term domain writes: term exists in DataHub; source yaml defines domain; map exists.

Outputs validated plan plus a separate issue report. No writes.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

MOCK = Path(__file__).resolve().parent.parent.parent / "mock-data"
SNAP = "enrichment/datahub_snapshot_fresh.json"
PLAN = "enrichment/datahub_enrichment_dryrun_plan.json"
OUT = "enrichment/datahub_enrichment_plan_validated.json"
ISSUES = "enrichment/datahub_enrichment_validation_issues.json"


def load_src_datasets() -> list[dict]:
    out = []
    for f in sorted((MOCK / "datasets").glob("*.yaml")):
        out.extend(yaml.safe_load(f.read_text()).get("datasets", []))
    return out


def load_src_glossary() -> list[dict]:
    out = []
    for f in sorted((MOCK / "glossary").glob("*.yaml")):
        out.extend(yaml.safe_load(f.read_text()).get("glossary_terms", []))
    return out


def load_src_domains() -> list[dict]:
    out = []
    for f in sorted((MOCK / "domains").glob("*.yaml")):
        out.append({"name": yaml.safe_load(f.read_text()).get("domain", ""), **yaml.safe_load(f.read_text())})
    return out


def domain_urn_for(name: str) -> str | None:
    """Replicate ingest_real_datahub.py ingest_domains URN mapping."""
    key = re.sub(r"[^A-Za-z0-9]+", "", name.lower()) or "unknown"
    return f"urn:li:domain:{key}" if name else None


def main() -> None:
    snap = json.load(open(SNAP))
    plan = json.load(open(PLAN))

    dh_ds = {d["urn"]: d for d in snap["datasets"]}
    dh_ds_by_name = {}
    for d in snap["datasets"]:
        name = (d.get("properties") or {}).get("name") or d.get("name")
        if name:
            dh_ds_by_name.setdefault(name, []).append(d)

    dh_terms = {t["urn"]: t for t in snap["glossary_terms"]}
    dh_terms_by_name = {}
    for t in snap["glossary_terms"]:
        nm = (t.get("properties") or {}).get("name") or t.get("name")
        dh_terms_by_name.setdefault((nm or "").lower().replace(" ", " "), t)

    src_ds = {d["name"]: d for d in load_src_datasets()}
    src_terms = {}
    for t in load_src_glossary():
        src_terms.setdefault((t.get("name") or "").lower(), t)
    src_domains_names = {d["name"].upper(): d["name"] for d in load_src_domains()}

    def dh_schema_fields(urn: str) -> dict[str, dict]:
        d = dh_ds.get(urn)
        if not d:
            return {}
        return {f.get("fieldPath"): f for f in (d.get("schemaMetadata") or {}).get("fields") or []}

    issues: list[dict] = []
    errors = 0

    for m in plan["mutations"]:
        m["validated"] = True
        m["validations"] = []

        def issue(code: str, msg: str) -> None:
            nonlocal errors
            errors += 1
            m["validated"] = False
            issues.append({"mut_id": m.get("mut_id"), "code": code, "message": msg, "urn": m.get("entity_urn")})

        if m["status"] != "PLANNED_WRITE":
            continue

        if m["entity_type"] == "glossary_term":
            urn = m["entity_urn"]
            if urn not in dh_terms:
                issue("TERM_URN_MISSING", "glossary term URN not present in DataHub")
                continue
            want_domain = m["new_value"]
            if not want_domain:
                issue("DOMAIN_NONE", "planned write to None domain")
                continue
            # source evidence check
            term = dh_terms[urn]
            name = (term.get("properties") or {}).get("name") or term.get("name")
            src = src_terms.get((name or "").lower())
            if not src:
                issue("TERM_NO_SOURCE", f"no source yaml term for {name!r}")
                continue
            if not (src.get("domain") or "").strip():
                issue("TERM_SOURCE_NO_DOMAIN", f"source term {name!r} has no domain")
                continue
            if domain_urn_for(src["domain"]) != want_domain:
                issue("DOMAIN_SOURCE_MISMATCH", f"{name!r}: source domain {src['domain']!r} -> {domain_urn_for(src['domain'])} != planned {want_domain}")
            m["validations"].append(f"source domain {src['domain']!r} -> {want_domain}")

        elif m["entity_type"] == "dataset":
            urn = m["entity_urn"]
            if urn not in dh_ds:
                issue("DS_URN_MISSING", "dataset URN not present in DataHub")
                continue
            fields = dh_schema_fields(urn)
            dname = (dh_ds[urn].get("properties") or {}).get("name") or dh_ds[urn].get("name")
            sds = src_ds.get(dname)
            if not sds:
                issue("DS_NO_SOURCE", f"no source dataset for {dname!r}")
            src_fields = {c.get("name"): c for c in (sds or {}).get("columns", [])}
            # check URN name matches canonical form
            expected_urn = f"urn:li:dataset:(urn:li:dataPlatform:redshift,{dname},PROD)"
            if expected_urn != urn:
                issue("URN_CANONICAL", f"URN {urn} != canonical {expected_urn}")

            new = m["new_value"]
            for pk in new.get("primaryKeys") or []:
                if pk not in fields:
                    issue("PK_FIELD_MISSING", f"PK {dname}.{pk} not in DataHub schema")
                elif not src_fields.get(pk):
                    issue("PK_NO_SOURCE_FIELD", f"PK {dname}.{pk} not in source yaml")
                else:
                    bd = (src_fields[pk].get("business_definition") or "").lower()
                    if "khóa chính" not in bd:
                        issue("PK_NO_EVIDENCE", f"PK {dname}.{pk} has no 'khóa chính' evidence in source")
            for fk_s in new.get("foreignKeys") or []:
                src_f, ref = fk_s.split("->", 1)
                ref_ds, ref_fld = ref.rsplit(".", 1)
                if src_f not in fields:
                    issue("FK_SRC_FIELD_MISSING", f"FK src {dname}.{src_f} not in DataHub schema")
                if not src_fields.get(src_f):
                    issue("FK_SRC_NO_SOURCE", f"FK src {dname}.{src_f} not in source yaml")
                else:
                    bd = (src_fields[src_f].get("business_definition") or "").lower()
                    if "tham chiếu" not in bd and "khóa ngoại" not in bd:
                        issue("FK_NO_EVIDENCE", f"FK {dname}.{src_f}->{ref} no 'tham chiếu/khóa ngoại' evidence")
                # target dataset + field
                tgt = dh_ds_by_name.get(ref_ds)
                if not tgt:
                    issue("FK_TARGET_MISSING", f"FK target dataset {ref_ds!r} not in DataHub")
                    continue
                if ref_fld not in dh_schema_fields(tgt[0]["urn"]):
                    issue("FK_REF_FIELD_MISSING", f"FK ref field {ref}.{ref_fld} not in {ref_ds} DataHub schema")

        else:
            issue("UNKNOWN_TYPE", f"unknown entity type {m['entity_type']}")

    # summary
    total = len(plan["mutations"])
    planned = [m for m in plan["mutations"] if m["status"] == "PLANNED_WRITE"]
    ok = [m for m in planned if m.get("validated")]
    bad = [m for m in planned if not m.get("validated")]

    with open(OUT, "w") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
    with open(ISSUES, "w") as f:
        json.dump({"total_issues": len(issues), "issues": issues}, f, ensure_ascii=False, indent=2)

    print(f"total mutations: {total}")
    print(f"planned writes: {len(planned)}, validated OK: {len(ok)}, with issues: {len(bad)}")
    print(f"total issues: {len(issues)}")
    from collections import Counter
    for code, n in Counter(i["code"] for i in issues).most_common():
        print(f"  {code}: {n}")
    for i in issues:
        print(f"  [{i['code']}] {i['message']}")


if __name__ == "__main__":
    main()