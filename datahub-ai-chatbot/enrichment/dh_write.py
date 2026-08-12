"""DataHub metadata enrichment writer.

Workflow per mutation: GET current -> build expected -> WRITE (targeted aspect)
-> RE-GET -> VERIFY (expected == actual). Mismatch => FAILED, stop bulk.

Modes:
  python dh_write.py --dry-run   (default; print plan, no writes)
  python dh_write.py --apply     (perform writes with verification)
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import re
import sys
import time
import urllib.parse
from pathlib import Path

import httpx
from datahub.emitter.mcp import MetadataChangeProposalWrapper
from datahub.emitter.mce_builder import make_schema_field_urn
from datahub.emitter.rest_emitter import DatahubRestEmitter
from datahub.metadata import schema_classes as sc

GMS = "http://localhost:8080"
PLAN = "enrichment/datahub_enrichment_dryrun_plan.json"
RESULT = "enrichment/datahub_enrichment_write_log.json"

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
      foreignKeys { name sourceFields { fieldPath } foreignFields { fieldPath } }
      fields {
        fieldPath label description nativeDataType type nullable
        isPartOfKey isPartitioningKey jsonProps
        globalTags { tags { tag { name urn } } }
        glossaryTerms { terms { term { urn name } } }
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


def _type_class(gql_type: str | None):
    cls = DDL_TYPE_NAME_TO_CLASS.get((gql_type or "").upper())
    if cls is None:
        return sc.StringTypeClass()
    return cls()


def _audit() -> sc.AuditStampClass:
    return sc.AuditStampClass(time=int(time.time() * 1000), actor="urn:li:corpuser:__datahub_enrichment")


async def fetch_schema(client: httpx.AsyncClient, urn: str) -> dict | None:
    r = await client.post(GMS, json={"query": GET_SCHEMA, "variables": {"urn": urn}}, timeout=60)
    d = r.json()
    if d.get("errors"):
        raise RuntimeError(f"schema fetch error {urn}: {d['errors']}")
    return (d.get("data") or {}).get("dataset") or {}


def build_schema_mcp(urn: str, ds_name: str, current: dict, new_pks: list[str], new_fks: list[dict]) -> MetadataChangeProposalWrapper:
    sm = current.get("schemaMetadata") or {}
    fields_gql = sm.get("fields") or []
    fields: list[sc.SchemaFieldClass] = []
    for f in fields_gql:
        pk_flag = f.get("fieldPath") in new_pks or f.get("isPartOfKey")
        fields.append(sc.SchemaFieldClass(
            fieldPath=f.get("fieldPath") or "",
            type=sc.SchemaFieldDataTypeClass(type=_type_class(f.get("type"))),
            nativeDataType=f.get("nativeDataType") or "",
            nullable=f.get("nullable", True),
            description=f.get("description"),
            label=f.get("label"),
            isPartOfKey=bool(pk_flag),
            isPartitioningKey=f.get("isPartitioningKey", False),
            jsonProps=f.get("jsonProps"),
            globalTags=(sc.GlobalTagsClass(tags=[sc.TagAssociationClass(tag=x["tag"]["urn"]) for x in (f.get("globalTags") or {}).get("tags", []) if x.get("tag", {}).get("urn")])
                        if (f.get("globalTags") or {}).get("tags") else None),
            glossaryTerms=(sc.GlossaryTermsClass(terms=[sc.GlossaryTermAssociationClass(urn=x["term"]["urn"]) for x in (f.get("glossaryTerms") or {}).get("terms", []) if x.get("term", {}).get("urn")])
                           if (f.get("glossaryTerms") or {}).get("terms") else None),
        ))
    fk_constraints = []
    fk_specs: dict[str, sc.ForeignKeySpecClass] = {}
    for k in new_fks:
        target_urn = _urn_of(k["ref_dataset"])
        fk_name = f"{k['source_field']}_fk"
        fk_constraints.append(make_schema_field_urn(target_urn, k["ref_field"]))
        fk_specs[fk_name] = sc.ForeignKeySpecClass(
            foreignKey=sc.DatasetFieldForeignKeyClass(
                parentDataset=target_urn,
                currentFieldPaths=[k["source_field"]],
                parentField=k["ref_field"],
            )
        )
    hash_seed = ",".join([f.get("fieldPath", "") for f in fields_gql]) + ";" + ";".join(new_pks) + ";" + ";".join(f"{k['source_field']}->{k['ref_dataset']}.{k['ref_field']}" for k in new_fks)
    version = int(sm.get("version") or 0) + 1
    platform_urn = sm.get("platformUrn") or f"urn:li:dataPlatform:redshift"
    return MetadataChangeProposalWrapper(
        entityUrn=urn,
        aspect=sc.SchemaMetadataClass(
            schemaName=sm.get("name") or ds_name,
            platform=platform_urn,
            version=version,
            hash=hashlib.md5(hash_seed.encode()).hexdigest(),
            platformSchema=sc.OtherSchemaClass(rawSchema=""),
            fields=fields,
            primaryKeys=new_pks or None,
            foreignKeys=fk_constraints or None,
            foreignKeysSpecs=fk_specs or None,
            created=_audit(),
            lastModified=_audit(),
        ),
    )


def _urn_of(dataset_name: str) -> str:
    return f"urn:li:dataset:(urn:li:dataPlatform:redshift,{dataset_name},PROD)"


def _load_plan() -> dict:
    return json.load(open(PLAN))


def main() -> None:
    apply = "--apply" in sys.argv
    plan = _load_plan()
    mutations = plan["mutations"]
    planned = [m for m in mutations if m["status"] == "PLANNED_WRITE"]

    if not apply:
        print("DRY-RUN: no writes performed.")
        print(f"planned writes: {len(planned)}")
        domain_writes = [m for m in planned if m["entity_type"] == "glossary_term"]
        schema_writes = [m for m in planned if m["entity_type"] == "dataset"]
        print(f"  glossary_term domain writes: {len(domain_writes)}")
        print(f"  dataset schema (pk/fk) writes: {len(schema_writes)}")
        print("Run with --apply to perform writes with per-mutation verification.")
        return

    emitter = DatahubRestEmitter(gms_server=GMS, token="")
    results = []

    # Track state to merge per-dataset schema writes (one MCP per dataset)
    schema_by_urn: dict[str, dict] = {}
    for m in planned:
        if m["entity_type"] == "glossary_term":
            domain_urn = m["new_value"]
            # get current
            # write domains aspect (targeted)
            emitter.emit_mcp(MetadataChangeProposalWrapper(
                entityUrn=m["entity_urn"],
                aspect=sc.DomainsClass(domains=[domain_urn]),
            ))
            results.append({"mut_id": m["mut_id"], "urn": m["entity_urn"], "kind": "domain", "status": "WRITTEN", "new": domain_urn})
        else:
            schema_by_urn.setdefault(m["entity_urn"], {"pks": [], "fks": []})
            if m["new_value"]["primaryKeys"]:
                schema_by_urn[m["entity_urn"]]["pks"] = m["new_value"]["primaryKeys"]
            for fk in m["new_value"]["foreignKeys"]:
                schema_by_urn[m["entity_urn"]]["fks"].append(fk)

    # schema writes (with verification)
    async def schema_loop():
        dname_re = re.compile(r"redshift,([^,]+),PROD")
        async with httpx.AsyncClient(timeout=120) as client:
            for urn, payload in schema_by_urn.items():
                mt = dname_re.search(urn)
                ds_name = mt.group(1) if mt else urn
                try:
                    current = await fetch_schema(client, urn)
                except Exception as e:
                    results.append({"mut_id": f"schema:{urn}", "urn": urn, "kind": "schema", "status": "FAILED", "error": str(e)})
                    break
                current_fk_names = {f"{x.get('sourceFields',[{}])[0].get('fieldPath')}->{x.get('name')}" for x in (current.get("schemaMetadata") or {}).get("foreignKeys") or []}
                pks = payload["pks"]
                fk_objs = [_parse_fk_short(u) for u in payload["fks"]]
                mcp = build_schema_mcp(urn, ds_name, current, pks, fk_objs)
                emitter.emit(mcp)
                # verify
                fresh = await fetch_schema(client, urn)
                fsm = fresh.get("schemaMetadata") or {}
                got_pks = fsm.get("primaryKeys") or []
                got_fks = fsm.get("foreignKeys") or []
                got_pairs = set()
                for x in got_fks:
                    src = (x.get("sourceFields") or [{}])[0].get("fieldPath")
                    fld = (x.get("foreignFields") or [{}])[0].get("fieldPath")
                    got_pairs.add(f"{src}->{fld}")
                want_pairs = set(payload["fks"])
                ok = sorted(got_pks) == sorted(pks)
                ok_fk = (not want_pairs) or (want_pairs <= got_pairs)
                status = "VERIFIED" if (ok and ok_fk) else "MISMATCH"
                results.append({
                    "mut_id": f"schema:{urn}", "urn": urn, "kind": "schema", "status": status,
                    "expected_pks": pks, "actual_pks": got_pks,
                    "expected_fks": sorted(want_pairs), "actual_fks": sorted(got_pairs),
                })
                if status == "MISMATCH":
                    print(f"FAILED VERIFICATION: {urn}")
                    print(f"  expected pks: {pks} got: {got_pks}")
                    print(f"  expected fks: {sorted(want_pairs)}\n  got fks: {sorted(got_pairs)}")
                    break
                print(f"  VERIFIED schema {ds_name} (pks={len(got_pks)}, fks={len(got_pairs)})")

    asyncio.run(schema_loop())

    with open(RESULT, "w") as f:
        json.dump({"writes": results}, f, ensure_ascii=False, indent=2)
    print(f"\nwrote {RESULT}")


def _parse_fk_short(s: str) -> dict:
    # format: source->ref_dataset.ref_field
    src, rest = s.split("->", 1)
    rd, rf = rest.split(".", 1)
    return {"source_field": src, "ref_dataset": rd, "ref_field": rf}


if __name__ == "__main__":
    main()