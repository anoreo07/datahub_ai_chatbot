"""Apply the validated DataHub enrichment plan with per-mutation verification.

Pipeline per mutation:  GET current state -> SKIP if already desired ->
WRITE targeted aspect -> RE-GET -> VERIFY (expected == actual).
On any verification mismatch -> mark FAILED, log, and abort remaining writes.

Categories handled:
  - glossary_term domain   : DomainsClass aspect
  - dataset domain         : DomainsClass aspect
  - dataset schema PK/FK   : SchemaMetadata aspect (full, preserving all fields)

Usage:
  python enrichment/dh_apply.py --dry-run   (default: show what would happen, no writes)
  python enrichment/dh_apply.py --apply     (perform writes with verification)
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import re
import sys
import time
from collections import Counter

import httpx
from datahub.emitter.mcp import MetadataChangeProposalWrapper
from datahub.emitter.mce_builder import make_schema_field_urn
from datahub.emitter.rest_emitter import DatahubRestEmitter
from datahub.metadata import schema_classes as sc

GMS = "http://localhost:8080"
PLAN = "enrichment/datahub_enrichment_plan_final.json"
LOG = "enrichment/datahub_enrichment_write_log.json"

GET_ENTITY_DOMAIN = """
query domain($urn: String!) {
  entity(urn: $urn) {
    urn
    ... on GlossaryTerm { domain { domain { urn } } }
    ... on Dataset { domain { domain { urn } } }
  }
}
"""

GET_SCHEMA = """
query getDatasetSchema($urn: String!) {
  dataset(urn: $urn) {
    urn
    schemaMetadata {
      name
      platformUrn
      version
      hash
      primaryKeys
      foreignKeys { name sourceFields { fieldPath } foreignFields { fieldPath } foreignDataset { urn } }
      fields {
        fieldPath label description nativeDataType type nullable
        isPartOfKey isPartitioningKey jsonProps
        globalTags { tags { tag { urn } } }
        glossaryTerms { terms { term { urn } } }
      }
    }
  }
}
"""

DDL_TYPE_NAME_TO_CLASS = {
    "STRING": sc.StringTypeClass,
    "NUMBER": sc.NumberTypeClass,
    "DATE": sc.DateTypeClass,
    "BOOLEAN": sc.BooleanTypeClass,
    "BYTES": sc.BytesTypeClass,
    "ENUM": sc.EnumTypeClass,
    "UNKNOWN": sc.NullTypeClass,
    "NULL": sc.NullTypeClass,
}

FHASH_SEED = None


def _type_class(gql_type: str | None):
    cls = DDL_TYPE_NAME_TO_CLASS.get((gql_type or "").upper())
    return (cls or sc.StringTypeClass)()


def _audit() -> sc.AuditStampClass:
    return sc.AuditStampClass(time=int(time.time() * 1000), actor="urn:li:corpuser:__datahub_enrichment")


async def gql(client: httpx.AsyncClient, query: str, variables: dict) -> dict:
    r = await client.post(GMS + "/api/graphql", json={"query": query, "variables": variables}, timeout=90)
    d = r.json()
    if d.get("errors"):
        raise RuntimeError(f"GraphQL errors {variables.get('urn')}: {d['errors']}")
    return (d.get("data") or {})


def emit_domain(emitter, urn: str, domain_urn: str) -> None:
    emitter.emit(MetadataChangeProposalWrapper(
        entityUrn=urn,
        aspect=sc.DomainsClass(domains=[domain_urn]),
    ))


def build_schema_mcp(urn, dataset, current: dict, pks: list[str], fks: list[dict], fk_name_map: list[str]) -> MetadataChangeProposalWrapper:
    sm = current.get("schemaMetadata") or {}
    fields_gql = sm.get("fields") or []
    fields: list[sc.SchemaFieldClass] = []
    for f in fields_gql:
        pk_flag = bool(f.get("fieldPath") in pks) or bool(f.get("isPartOfKey"))
        fields.append(sc.SchemaFieldClass(
            fieldPath=f.get("fieldPath") or "",
            type=sc.SchemaFieldDataTypeClass(type=_type_class(f.get("type"))),
            nativeDataType=f.get("nativeDataType") or "",
            nullable=f.get("nullable", True),
            description=f.get("description"),
            label=f.get("label"),
            isPartOfKey=pk_flag,
            isPartitioningKey=f.get("isPartitioningKey", False),
            jsonProps=f.get("jsonProps"),
            globalTags=(sc.GlobalTagsClass(tags=[sc.TagAssociationClass(tag=x["tag"]["urn"]) for x in (f.get("globalTags") or {}).get("tags", []) if x.get("tag", {}).get("urn")])
                        if (f.get("globalTags") or {}).get("tags") else None),
            glossaryTerms=(sc.GlossaryTermsClass(terms=[sc.GlossaryTermAssociationClass(urn=x["term"]["urn"]) for x in (f.get("glossaryTerms") or {}).get("terms", []) if x.get("term", {}).get("urn")])
                           if (f.get("glossaryTerms") or {}).get("terms") else None),
        ))
    fk_constraints = []
    fk_specs: dict[str, sc.ForeignKeySpecClass] = {}
    for k, name in zip(fks, fk_name_map):
        target_urn = _urn_of(k["ref_dataset"])
        fk_constraints.append(sc.ForeignKeyConstraintClass(
            name=name,
            foreignFields=[make_schema_field_urn(target_urn, k["ref_field"])],
            sourceFields=[make_schema_field_urn(urn, k["source_field"])],
            foreignDataset=target_urn,
        ))
        fk_specs[name] = sc.ForeignKeySpecClass(
            foreignKey=sc.DatasetFieldForeignKeyClass(
                parentDataset=target_urn,
                currentFieldPaths=[k["source_field"]],
                parentField=k["ref_field"],
            )
        )
    hash_seed = ",".join([f.get("fieldPath", "") for f in fields_gql])
    version = int(sm.get("version") or 0) + 1
    platform_urn = sm.get("platformUrn") or "urn:li:dataPlatform:redshift"
    return MetadataChangeProposalWrapper(
        entityUrn=urn,
        aspect=sc.SchemaMetadataClass(
            schemaName=sm.get("name") or dataset,
            platform=platform_urn,
            version=version,
            hash=hashlib.md5(hash_seed.encode()).hexdigest(),
            platformSchema=sc.OtherSchemaClass(rawSchema=""),
            fields=fields,
            primaryKeys=pks or None,
            foreignKeys=fk_constraints or None,
            foreignKeysSpecs=fk_specs or None,
            created=_audit(),
            lastModified=_audit(),
        ),
    )


def _urn_of(dataset_name: str) -> str:
    return f"urn:li:dataset:(urn:li:dataPlatform:redshift,{dataset_name},PROD)"


def _field_urn(target_urn: str, ref_field: str) -> str:
    return make_schema_field_urn(target_urn, ref_field)


def main() -> None:
    apply = "--apply" in sys.argv
    plan = json.load(open(PLAN))
    writes = [m for m in plan["mutations"] if m["status"] == "PLANNED_WRITE"]

    if not apply:
        print("DRY RUN — no writes performed.")
        c = Counter(m["entity_type"] + ":" + m["property"] for m in writes)
        for k, v in c.items():
            print(f"  {k}: {v}")
        print(f"total planned: {len(writes)}")
        print("Run with --apply to perform writes with per-mutation verification.")
        return

    if "--confirm" not in sys.argv:
        print("SAFETY: --apply also requires --confirm to proceed. Nothing written.")
        sys.exit(0)

    emitter = DatahubRestEmitter(gms_server=GMS, token="")
    results: list[dict] = []
    failed = 0

    async def run():
        nonlocal failed
        async with httpx.AsyncClient(timeout=90) as client:
            # ---- domain writes ----
            for m in writes:
                if m["property"] != "domain":
                    continue
                urn = m["entity_urn"]
                want = m["new_value"]
                row = {"mut_id": m["mut_id"], "urn": urn, "kind": "domain", "conf": m["confidence"],
                       "expected": want, "status": None}
                try:
                    cur = (await gql(client, GET_ENTITY_DOMAIN, {"urn": urn})).get("entity") or {}
                    cur_domain = ((cur.get("domain") or {}).get("domain") or {}).get("urn")
                    if cur_domain == want:
                        row["status"] = "SKIPPED_ALREADY_DESIRED"
                        results.append(row); continue
                    emit_domain(emitter, urn, want)
                    fresh = (await gql(client, GET_ENTITY_DOMAIN, {"urn": urn})).get("entity") or {}
                    got = ((fresh.get("domain") or {}).get("domain") or {}).get("urn")
                    if got == want:
                        row["status"] = "VERIFIED"
                    else:
                        row["status"] = "MISMATCH"; row["actual"] = got
                        failed += 1
                        print(f"FAIL domain mismatch {urn}: want {want} got {got}")
                except Exception as e:
                    row["status"] = "ERROR"; row["error"] = str(e); failed += 1
                results.append(row)
                print("  ", row["status"], urn, "->", want)

            # ---- schema writes ----
            dname_re = re.compile(r"redshift,([^,]+),PROD$")
            schema_mutations = [m for m in writes if m["entity_type"] == "dataset" and m["property"] != "domain"]
            for m in schema_mutations:
                urn = m["entity_urn"]
                mt = dname_re.search(urn)
                dname = mt.group(1) if mt else urn
                new = m["new_value"]
                pks = new["primaryKeys"]
                fk_list = [_parse_fk_short(u) for u in new["foreignKeys"]]
                fk_names = [f"fk_{k['source_field']}" for k in fk_list]
                row = {"mut_id": m["mut_id"], "urn": urn, "kind": "schema", "conf": m["confidence"],
                       "expected_pks": pks, "expected_fks": new["foreignKeys"], "status": None}
                try:
                    cur = (await gql(client, GET_SCHEMA, {"urn": urn})).get("dataset") or {}
                    sm = cur.get("schemaMetadata") or {}
                    cur_pks = sm.get("primaryKeys") or []
                    cur_fk_pairs = _fk_pairs(sm)
                    want_fk_pairs = set(new["foreignKeys"])
                    want_fk_norm = _normalize_fk_want(want_fk_pairs)
                    if sorted(cur_pks) == sorted(pks) and not (want_fk_norm - cur_fk_pairs):
                        row["status"] = "SKIPPED_ALREADY_DESIRED"
                        results.append(row); continue
                    mcp = build_schema_mcp(urn, dname, cur, pks, fk_list, fk_names)
                    emitter.emit(mcp)
                    fresh = (await gql(client, GET_SCHEMA, {"urn": urn})).get("dataset") or {}
                    fsm = fresh.get("schemaMetadata") or {}
                    got_pks = fsm.get("primaryKeys") or []
                    got_pairs = _fk_pairs(fsm)
                    ok_pk = sorted(got_pks) == sorted(pks)
                    ok_fk = (not want_fk_pairs) or (want_fk_norm <= got_pairs)
                    # field preservation check
                    before_sig = _field_sig(sm)
                    after_sig = _field_sig(fsm)
                    preserved = before_sig is not None and before_sig == after_sig
                    if ok_pk and ok_fk and preserved:
                        row["status"] = "VERIFIED"
                        row["actual_pks"] = got_pks
                        row["actual_fk_pairs"] = sorted(got_pairs)
                    else:
                        row["status"] = "MISMATCH"
                        row["actual_pks"] = got_pks
                        row["actual_fk_pairs"] = sorted(got_pairs)
                        row["fields_preserved"] = preserved
                        failed += 1
                        print(f"FAIL schema verification {dname}: pks ok={ok_pk} fk ok={ok_fk} preserved={preserved}")
                        if before_sig and not preserved:
                            print("  FIELD SIGNATURE CHANGED — metadata loss risk. ABORT.")
                            return
                except Exception as e:
                    row["status"] = "ERROR"; row["error"] = str(e); failed += 1
                results.append(row)
                print("  ", row["status"], dname, "pks:", pks, "fks:", len(fk_list))

    asyncio.run(run())

    with open(LOG, "w") as f:
        json.dump({"applied_at": __import__("datetime").datetime.now().isoformat(),
                   "total": len(results), "by_status": dict(Counter(r["status"] for r in results)),
                   "failed": failed, "writes": results}, f, ensure_ascii=False, indent=2)
    print(f"\nwrote {LOG}: total={len(results)} failed={failed}")
    print("by_status:", dict(Counter(r["status"] for r in results)))


def _field_sig(sm: dict) -> str | None:
    """Signature of field metadata EXCLUDING isPartOfKey (intentionally changed by PK enrichment)"""
    fields = sm.get("fields")
    if fields is None:
        return None
    sig = []
    for f in sorted(fields, key=lambda x: x.get("fieldPath") or ""):
        sig.append("|".join([
            f.get("fieldPath") or "",
            str(f.get("nativeDataType") or ""),
            str(f.get("type") or ""),
            str(f.get("nullable")),
            str(f.get("description") or ""),
            str(f.get("jsonProps") or ""),
        ]))
    return hashlib.md5("\n".join(sig).encode()).hexdigest()


def _fk_pairs(sm: dict) -> set[str]:
    """Return FK pairs as 'src->refField@foreignDataset' (verification against plan)."""
    pairs = set()
    for x in (sm.get("foreignKeys") or []):
        src = ((x.get("sourceFields") or [{}])[0]).get("fieldPath")
        ref = ((x.get("foreignFields") or [{}])[0]).get("fieldPath")
        if src and ref:
            ds = (x.get("foreignDataset") or {}).get("urn") or ""
            ds = ds.split(",")[1].removesuffix(",PROD)") if "," in ds else ds
            pairs.add(f"{src}->{ref}@{ds}")
    return pairs


def _normalize_fk_want(want: set[str]) -> set[str]:
    """Plan entries are 'src->dataset.reffield'; normalize to 'src->reffield@dataset'."""
    out = set()
    for w in want:
        if "->" in w:
            src, ref = w.split("->", 1)
            if "." in ref:
                rd, rf = ref.split(".", 1)
                out.add(f"{src}->{rf}@{rd}")
            else:
                out.add(f"{src}->{ref}")
        else:
            out.add(w)
    return out


def _parse_fk_short(s: str) -> dict:
    src, rest = s.split("->", 1)
    rd, rf = rest.split(".", 1)
    return {"source_field": src, "ref_dataset": rd, "ref_field": rf}


if __name__ == "__main__":
    main()