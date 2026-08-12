"""Generate DataHub enrichment report artifacts (READ-only, no writes).

Artifacts:
  - datahub_similar_name_groups.json        (section 13: deterministic name groups)
  - datahub_glossary_relationship_enrichment.json (section 9: dataset<->term links)
  - datahub_lineage_enrichment_report.json  (section 11: per-dataset lineage status)
  - datahub_owner_enrichment_report.json    (section 12: per-dataset owner status)
  - datahub_exact_entity_inventory.json     (section 14: canonical inventory)
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import yaml

MOCK = Path(__file__).resolve().parent.parent.parent / "mock-data"
SNAP = "enrichment/datahub_snapshot_fresh.json"


def load_src_datasets() -> list[dict]:
    return [d for f in sorted((MOCK / "datasets").glob("*.yaml")) for d in yaml.safe_load(f.read_text()).get("datasets", [])]


def load_src_glossary() -> list[dict]:
    return [t for f in sorted((MOCK / "glossary").glob("*.yaml")) for t in yaml.safe_load(f.read_text()).get("glossary_terms", [])]


def load_src_owners() -> dict[str, dict]:
    out = {}
    for f in sorted((MOCK / "owners").glob("*.yaml")):
        for o in yaml.safe_load(f.read_text()).get("owners", []):
            out[o["id"]] = o
    return out


def main() -> None:
    snap = json.load(open(SNAP))
    datasets = snap["datasets"]
    terms = snap["glossary_terms"]
    lineage = snap["lineage"]
    src_ds = {d["name"]: d for d in load_src_datasets()}
    src_glossary = {(t.get("name") or "").lower(): t for t in load_src_glossary()}
    src_owners = load_src_owners()

    dh_by_name = {}
    for d in datasets:
        nm = (d.get("properties") or {}).get("name") or d.get("name")
        dh_by_name.setdefault(nm, []).append(d)

    # ---------------- similar name groups ----------------
    def core_tokens(name: str) -> list[str]:
        m = re.match(r"(?:dim_|fact_)?(.+)", name)
        return (m.group(1) if m else name).split("_")

    all_names = sorted(dh_by_name)

    groups: dict[str, list[str]] = defaultdict(list)
    # 1) single-token root (deterministic): fact_inventory* -> inventory, dim_charging* -> charging
    for n in all_names:
        tok = core_tokens(n)[0]
        if tok:
            groups["token_" + tok].append(n)
    # 2) two-token prefix: fact_import_cost / fact_import_order / fact_import_schedule
    for n in all_names:
        t2 = "_".join(core_tokens(n)[:2])
        if t2:
            groups["prefix_" + t2].append(n)
    # 3) same core across dim_/fact_ namespaces
    for n in all_names:
        core = n[len("dim_"):] if n.startswith("dim_") else (n[len("fact_"):] if n.startswith("fact_") else n)
        groups["cross_" + core].append(n)

    final_groups = []
    for key, members in sorted(groups.items()):
        members = sorted(members)
        if len(members) >= 2:
            kind = key.split("_", 1)[0]
            reason = {
                "token": "shared normalized single-token root",
                "prefix": "shared normalized two-token prefix",
                "cross": "same normalized core name across dim_/fact_ namespaces -> exact-name ambiguity risk",
            }[kind]
            final_groups.append({"group_id": key, "datasets": members, "reason": reason})

    with open("enrichment/datahub_similar_name_groups.json", "w") as f:
        json.dump({"generated_at": __import__("datetime").datetime.now().isoformat(), "groups": final_groups}, f, ensure_ascii=False, indent=2)
    print(f"similar_name_groups: {len(final_groups)}")

    # ---------------- glossary relationships ----------------
    rels = []
    # dataset-level terms
    for d in datasets:
        nm = (d.get("properties") or {}).get("name") or d.get("name")
        gt = d.get("glossaryTerms") or {}
        for x in (gt.get("terms") or []) if isinstance(gt, dict) else []:
            rels.append({
                "dataset_urn": d["urn"], "dataset": nm, "level": "dataset",
                "term_urn": x["term"]["urn"], "term": x["term"]["name"],
                "evidence": "explicit DataHub dataset.glossaryTerms",
            })
        for f in (d.get("schemaMetadata") or {}).get("fields") or []:
            fgt = f.get("glossaryTerms") or {}
            for x in (fgt.get("terms") or []) if isinstance(fgt, dict) else []:
                rels.append({
                    "dataset_urn": d["urn"], "dataset": nm, "level": "field",
                    "field": f.get("fieldPath"),
                    "term_urn": x["term"]["urn"], "term": x["term"]["name"],
                    "evidence": "explicit DataHub field.glossaryTerms",
                })
    with open("enrichment/datahub_glossary_relationship_enrichment.json", "w") as f:
        json.dump({
            "generated_at": __import__("datetime").datetime.now().isoformat(),
            "relationships_found": len(rels),
            "total_datasets": len(datasets),
            "total_glossary_terms": len(terms),
            "relationships": rels,
            "note": "No dataset<->term relationships were auto-inferred. "
                    "Only explicit DataHub terminology (dataset.glossaryTerms / field.glossaryTerms) is reported. "
                    "Semantic similarity is NOT used to create relationships (no-hallucination policy).",
        }, f, ensure_ascii=False, indent=2)
    print(f"glossary relationships found: {len(rels)}")

    # ---------------- lineage status ----------------
    # expected upstream per source FK text (same semantics as ingest_real_datahub.py)
    urn_of = lambda n: f"urn:li:dataset:(urn:li:dataPlatform:redshift,{n},PROD)"
    expected_up: dict[str, set[str]] = defaultdict(set)
    for ds in src_ds.values():
        nm = ds["name"]
        for col in ds.get("columns", []):
            bd = (col.get("business_definition") or "").lower()
            m = re.search(r"tham chiếu đến ([a-z0-9_.]{1,64})", bd)
            if m and m.group(1) in src_ds and m.group(1) != nm:
                expected_up[nm].add(urn_of(m.group(1)))

    lineages = []
    for d in datasets:
        nm = (d.get("properties") or {}).get("name") or d.get("name")
        urn = d["urn"]
        lin = lineage.get(urn, {})
        ups = [(x.get("entity") or {}).get("urn") for x in (lin.get("upstream") or {}).get("relationships") or []]
        dns = [(x.get("entity") or {}).get("urn") for x in (lin.get("downstream") or {}).get("relationships") or []]
        exp = sorted(expected_up.get(nm, set()))
        got = sorted(set(ups))
        status = "NONE" if not (ups or dns) else "PRESENT"
        gap = "consistent" if sorted(exp) == got else ("missing_some" if not set(exp).issubset(set(got)) else "extra_only")
        lineages.append({
            "dataset": nm,
            "urn": urn,
            "lineage_status": status,
            "has_upstream": bool(ups),
            "has_downstream": bool(dns),
            "upstream": got,
            "downstream": sorted(dns),
            "expected_upstream_from_source": exp,
            "lineage_vs_source": gap,
            "classification": (
                "NONE" if not (ups or dns) and not exp else
                ("PRESENT" if not gap == "missing_some" else "PARTIAL_MISSING")
            ),
        })
    with open("enrichment/datahub_lineage_enrichment_report.json", "w") as f:
        json.dump({"generated_at": __import__("datetime").datetime.now().isoformat(), "datasets": lineages}, f, ensure_ascii=False, indent=2)
    st = Counter(x["classification"] for x in lineages)
    print(f"lineage classification: {dict(st)}")

    # ---------------- owner report ----------------
    owner_rows = []
    for d in datasets:
        nm = (d.get("properties") or {}).get("name") or d.get("name")
        urn = d["urn"]
        own = d.get("ownership") or {}
        owners = own.get("owners") or []
        src_own_ids = src_ds.get(nm, {}).get("owners", [])
        resolvable = [o for o in src_own_ids if o in src_owners]
        status = "NONE" if not owners else "PRESENT"
        note = None
        if owners:
            note = f"DataHub owner present: {json.dumps(owners, ensure_ascii=False)[:200]}"
        elif src_own_ids and not resolvable:
            status = "NONE"
            note = f"source references unresolved owner id(s) {src_own_ids} (not defined in owners.yaml, no corpuser entity) -> left NONE, not fabricated"
        owner_rows.append({
            "dataset": nm, "urn": urn, "owner_status": status,
            "datahub_owners": owners,
            "source_owner_ids": src_own_ids,
            "source_owner_ids_resolvable": resolvable,
            "note": note,
        })
    with open("enrichment/datahub_owner_enrichment_report.json", "w") as f:
        json.dump({"generated_at": __import__("datetime").datetime.now().isoformat(), "datasets": owner_rows}, f, ensure_ascii=False, indent=2)
    oc = Counter(r["owner_status"] for r in owner_rows)
    print(f"owner status: {dict(oc)}")

    # ---------------- exact entity inventory ----------------
    def term_name(t):
        return (t.get("properties") or {}).get("name") or t.get("name")
    term_urn_mask = {t["urn"]: 1 for t in terms}
    inventory = []
    for d in datasets:
        nm = (d.get("properties") or {}).get("name") or d.get("name")
        sm = d.get("schemaMetadata") or {}
        props = d.get("properties") or {}
        dom = d.get("domain")
        domain = (dom.get("domain") or {}) if isinstance(dom, dict) else {}
        lin = lineage.get(d["urn"], {})
        inventory.append({
            "dataset": nm,
            "urn": d["urn"],
            "platform": (d.get("platform") or {}).get("name"),
            "environment": "PROD",
            "domain_urn": (domain.get("urn") or None),
            "domain_name": ((domain.get("properties") or {}).get("name") or None),
            "description": props.get("description") or (d.get("editableProperties") or {}).get("description"),
            "owner": d.get("ownership"),
            "schema_fields_count": len(sm.get("fields") or []),
            "schema_version": sm.get("version"),
            "primary_keys": sm.get("primaryKeys") or [],
            "foreign_keys_count": len(sm.get("foreignKeys") or []),
            "dataset_glossary_terms": [(x["term"]["urn"], x["term"]["name"]) for x in (d.get("glossaryTerms") or {}).get("terms", [])] if isinstance(d.get("glossaryTerms"), dict) else [],
            "upstream_count": (lin.get("upstream") or {}).get("total", 0),
            "downstream_count": (lin.get("downstream") or {}).get("total", 0),
        })
    with open("enrichment/datahub_exact_entity_inventory.json", "w") as f:
        json.dump({
            "generated_at": __import__("datetime").datetime.now().isoformat(),
            "datasets": inventory,
            "glossary_terms": [{"urn": t["urn"], "name": term_name(t)} for t in terms],
        }, f, ensure_ascii=False, indent=2)
    print(f"inventory datasets: {len(inventory)}, terms: {len(terms)}")


if __name__ == "__main__":
    main()