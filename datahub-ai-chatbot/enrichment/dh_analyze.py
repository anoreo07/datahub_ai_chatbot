"""Analyze the DataHub snapshot: inventory, schema field stats, glossary, lineage gaps."""
from __future__ import annotations

import json
import sys
from collections import Counter


def load(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else "enrichment/datahub_snapshot_raw.json"
    snap = load(path)
    datasets = snap["datasets"]
    terms = snap["glossary_terms"]
    lineage = snap["lineage"]

    print("=" * 80)
    print("DATASET INVENTORY")
    print("=" * 80)
    print(f"total datasets: {len(datasets)}")
    print(f"total glossary terms: {len(terms)}")

    platforms = Counter()
    domains = Counter()
    owners_count = 0
    no_owner = 0
    with_desc = 0
    no_desc = 0
    with_schema = 0
    no_schema = 0
    field_counter = 0
    type_counter: Counter[str] = Counter()
    nullable_true = 0
    nullable_false = 0
    nullable_none = 0
    is_part_of_key_true = 0
    with_glossary = 0
    field_glossary_terms = 0
    with_pk_list = 0
    with_fk_list = 0
    total_fk = 0

    for ds in datasets:
        props = ds.get("properties") or {}
        desc = props.get("description") or (ds.get("editableProperties") or {}).get("description") or ds.get("description")
        platform = (ds.get("platform") or {}).get("name") or "?"
        domain = ""
        d = ds.get("domain") or {}
        if isinstance(d, dict):
            inner = d.get("domain") or {}
            domain = (inner.get("properties") or {}).get("name") or inner.get("name") or ""
        platforms[platform] += 1
        domains[domain or "NO_DOMAIN"] += 1
        if desc:
            with_desc += 1
        else:
            no_desc += 1
        own = ds.get("ownership") or {}
        owners = own.get("owners") or []
        if owners:
            owners_count += 1
        else:
            no_owner += 1
        schema = ds.get("schemaMetadata") or {}
        fields = schema.get("fields") or []
        if schema:
            with_schema += 1
        else:
            no_schema += 1
        pks = schema.get("primaryKeys") or []
        fks = schema.get("foreignKeys") or []
        if pks:
            with_pk_list += 1
        if fks:
            with_fk_list += 1
            total_fk += len(fks)
        for f in fields:
            field_counter += 1
            ftype = f.get("nativeDataType") or f.get("type") or ""
            type_counter[ftype or "MISSING"] += 1
            nullable = f.get("nullable")
            if nullable is True:
                nullable_true += 1
            elif nullable is False:
                nullable_false += 1
            else:
                nullable_none += 1
            if f.get("isPartOfKey"):
                is_part_of_key_true += 1
            if f.get("glossaryTerms"):
                field_glossary_terms += 1
        gt = ds.get("glossaryTerms") or {}
        if (gt.get("terms") or []) if isinstance(gt, dict) else []:
            with_glossary += 1

    print(f"\nplatforms: {dict(platforms)}")
    print(f"domains: {dict(domains)}")
    print(f"with description: {with_desc}, without: {no_desc}")
    print(f"with owner: {owners_count}, without: {no_owner}")
    print(f"with schemaMetadata: {with_schema}, without: {no_schema}")
    print(f"fields total: {field_counter}")
    print(f"nullable true: {nullable_true}, false: {nullable_false}, none: {nullable_none}")
    print(f"isPartOfKey true: {is_part_of_key_true}")
    print(f"datasets with dataset-level glossaryTerms: {with_glossary}")
    print(f"fields with glossaryTerms: {field_glossary_terms}")
    print(f"datasets with primaryKeys list: {with_pk_list}")
    print(f"datasets with foreignKeys list: {with_fk_list}, total FK constraints: {total_fk}")
    print("\nType distribution (nativeDataType or type):")
    for t, c in type_counter.most_common():
        print(f"  {t!r}: {c}")

    print("\n" + "=" * 80)
    print("LINEAGE")
    print("=" * 80)
    up_count = 0
    dn_count = 0
    none_lineage = 0
    for urn, lin in lineage.items():
        up_total = (lin["upstream"] or {}).get("total", 0)
        dn_total = (lin["downstream"] or {}).get("total", 0)
        if up_total + dn_total == 0:
            none_lineage += 1
        up_count += up_total
        dn_count += dn_total
    print(f"upstream relationships total: {up_count}")
    print(f"downstream relationships total: {dn_count}")
    print(f"datasets with NO lineage at all: {none_lineage}")

    print("\n" + "=" * 80)
    print("GLOSSARY TERMS")
    print("=" * 80)
    term_with_domain = 0
    term_no_domain = 0
    term_with_parent = 0
    term_parents = Counter()
    for t in terms:
        d = t.get("domain") or {}
        if isinstance(d, dict):
            inner = d.get("domain") or {}
            if inner:
                term_with_domain += 1
            else:
                term_no_domain += 1
        else:
            term_no_domain += 1
        pn = t.get("parentNodes") or {}
        nodes = pn.get("nodes") or []
        if nodes:
            term_with_parent += 1
            term_parents[nodes[0].get("properties", {}).get("name") or nodes[0].get("name") or "?"] += 1
    print(f"terms with domain: {term_with_domain}, without: {term_no_domain}")
    print(f"terms with parent node: {term_with_parent}")
    print(f"top parent nodes: {dict(term_parents.most_common(20))}")


if __name__ == "__main__":
    main()
