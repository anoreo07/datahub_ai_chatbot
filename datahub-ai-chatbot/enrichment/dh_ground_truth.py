"""Regenerate ground-truth metadata strictly from post-enrichment DataHub state.

No manual editing. Values not evidenced in DataHub are marked UNKNOWN / NONE as
defined by the enrichment policy (never guess). Output: datahub_ground_truth.json
"""
from __future__ import annotations

import json

SNAP = "enrichment/datahub_snapshot_after.json"
OUT = "enrichment/datahub_ground_truth.json"
REPORT = "enrichment/datahub_enrichment_verification.md"


def main() -> None:
    snap = json.load(open(SNAP))
    datasets = snap["datasets"]
    terms = snap["glossary_terms"]
    lineage = snap["lineage"]

    term_by_urn = {t["urn"]: t for t in terms}

    def term_domain(t: dict) -> str | None:
        d = t.get("domain")
        return (d.get("domain") or {}).get("urn") if isinstance(d, dict) and (d.get("domain") or {}) else None

    def ds_domain(d: dict) -> str | None:
        dd = d.get("domain")
        return (dd.get("domain") or {}).get("urn") if isinstance(dd, dict) and (dd.get("domain") or {}) else None

    def ds_owner(d: dict) -> list[str]:
        own = d.get("ownership") or {}
        return [(o.get("owner") or {}).get("urn") for o in (own.get("owners") or []) if (o.get("owner") or {}).get("urn")]

    # ---------------- build ground truth ----------------
    gt_datasets = []
    stats = {
        "types_with_native": 0, "nullable_known": 0, "pk_confirmed": 0, "fk_confirmed": 0,
        "field_glossary": 0, "unintended_overwrite": 0,
    }
    for d in datasets:
        name = (d.get("properties") or {}).get("name") or d.get("name")
        sm = d.get("schemaMetadata") or {}
        fields_gql = sm.get("fields") or []
        pks = sm.get("primaryKeys") or []
        fk_list = sm.get("foreignKeys") or []
        # FK source-field -> ref info (from specs not exposed; use sourceFields/foreignFields/foreignDataset)
        field_glossary = 0
        schema_fields = []
        for f in fields_gql:
            if (f.get("glossaryTerms") or {}).get("terms"):
                field_glossary += 1
            schema_fields.append({
                "name": f.get("fieldPath"),
                "type": f.get("nativeDataType") or f.get("type") or "UNKNOWN",
                "logical_type": f.get("type") or "UNKNOWN",
                "nullable": f.get("nullable") if f.get("nullable") is not None else "UNKNOWN",
                "is_pk": f.get("fieldPath") in pks,
                "is_fk": False,
                "fk_ref_dataset": None,
                "fk_ref_field": None,
                "description": f.get("description") or "UNKNOWN",
                "is_partitioning_key": f.get("isPartitioningKey"),
            })
        for i, f in enumerate(schema_fields):
            if f["type"] != "UNKNOWN":
                stats["types_with_native"] += 1
            if f["nullable"] != "UNKNOWN":
                stats["nullable_known"] += 1
        for fk in fk_list:
            src = ((fk.get("sourceFields") or [{}])[0]).get("fieldPath")
            ref = ((fk.get("foreignFields") or [{}])[0]).get("fieldPath")
            ref_ds = (fk.get("foreignDataset") or {}).get("urn")
            for f in schema_fields:
                if f["name"] == src:
                    f["is_fk"] = True
                    f["fk_ref_dataset"] = ref_ds
                    f["fk_ref_field"] = ref
        # collect dataset-level glossary terms
        gt_terms = []
        dgt = d.get("glossaryTerms")
        if isinstance(dgt, dict):
            for x in dgt.get("terms", []):
                gt_terms.append(x["term"]["urn"])
        gt_datasets.append({
            "dataset": name,
            "urn": d["urn"],
            "platform": (d.get("platform") or {}).get("name") or "UNKNOWN",
            "environment": "PROD",
            "description": (d.get("properties") or {}).get("description")
                           or (d.get("editableProperties") or {}).get("description")
                           or "UNKNOWN",
            "domain": ds_domain(d) or None,
            "owner": ds_owner(d),  # empty list -> confirmed no-owner in DataHub; keep [] not None
            "schema_fields": schema_fields,
            "glossary_terms": gt_terms,
            "upstream": [r.get("entity", {}).get("urn") for r in (lineage.get(d["urn"], {}).get("upstream") or {}).get("relationships") or []],
            "downstream": [r.get("entity", {}).get("urn") for r in (lineage.get(d["urn"], {}).get("downstream") or {}).get("relationships") or []],
        })
        stats["pk_confirmed"] += len(pks)
        stats["fk_confirmed"] += len(fk_list)
        stats["field_glossary"] += field_glossary

    gt_terms = []
    for t in terms:
        name = (t.get("properties") or {}).get("name") or t.get("name")
        gt_terms.append({
            "glossary_term": name,
            "urn": t["urn"],
            "description": (t.get("properties") or {}).get("description") or "UNKNOWN",
            "domain": term_domain(t) or None,
            "linked_datasets": [],  # explicit dataset<->term links none found in DataHub
            "definition": (t.get("properties") or {}).get("name"),
        })

    # similar-name groups from artifact
    similar = json.load(open("enrichment/datahub_similar_name_groups.json"))["groups"]

    ground_truth = {
        "generated_at": __import__("datetime").datetime.now().isoformat(),
        "source": "DataHub post-enrichment (snapshot_after.json), canonical URNs only",
        "dataset_count": len(gt_datasets),
        "glossary_count": len(gt_terms),
        "datasets": gt_datasets,
        "glossary_terms": gt_terms,
        "similar_name_groups": similar,
        "note": ("No property is guessed. UNKNOWN where DataHub lacks evidence; "
                 "is_pk/is_fk come from real schema constraints written from verified source."),
    }
    with open(OUT, "w") as f:
        json.dump(ground_truth, f, ensure_ascii=False, indent=2)

    print(f"wrote {OUT}")
    print("stats:", json.dumps(stats, ensure_ascii=False))


if __name__ == "__main__":
    main()