"""Ingest business metadata from mock-data YAML into a REAL DataHub instance.

Reads domains, glossary terms, tags, owners, and datasets from ../mock-data
and emits real MetadataChangeProposal events to the DataHub GMS REST API.
This is NOT mock mode — data is written into the live DataHub graph.
"""
from __future__ import annotations

import hashlib
import json
import re
import urllib.parse
from datetime import date, datetime
from pathlib import Path

import structlog
import yaml
from datahub.emitter.mcp import MetadataChangeProposalWrapper
from datahub.emitter.rest_emitter import DatahubRestEmitter
from datahub.metadata import schema_classes as sc

log = structlog.get_logger()

MOCK_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "mock-data"

GMS_URL = "http://localhost:8080"
GMS_TOKEN = ""


def _urn(entity_type: str, *parts: str) -> str:
    return f"urn:li:{entity_type}:{':'.join(parts)}"


def _glossary_urn(name: str) -> str:
    return _urn("glossaryTerm", urllib.parse.quote(name.lower()))


def _emit(emitter: DatahubRestEmitter, mcp: MetadataChangeProposalWrapper) -> None:
    emitter.emit(mcp)


def _audit_stamp() -> sc.AuditStampClass:
    return sc.AuditStampClass(time=0, actor="urn:li:corpuser:__datahub_system")


def _json_dumps(obj: dict) -> str | None:
    def _default(o):
        if isinstance(o, (date, datetime)):
            return o.isoformat()
        raise TypeError(f"Object of type {o.__class__.__name__} is not JSON serializable")

    return json.dumps(obj, ensure_ascii=False, default=_default)


def _status_mcp(entity_urn: str) -> MetadataChangeProposalWrapper:
    return MetadataChangeProposalWrapper(
        entityUrn=entity_urn,
        aspect=sc.StatusClass(removed=False),
    )


def _browse_mcp(entity_urn: str, paths: list[str]) -> MetadataChangeProposalWrapper:
    return MetadataChangeProposalWrapper(
        entityUrn=entity_urn,
        aspect=sc.BrowsePathsClass(paths=paths),
    )


def load_owners() -> list[dict]:
    data = yaml.safe_load((MOCK_DATA_DIR / "owners" / "owners.yaml").read_text())
    return data.get("owners", [])


def load_domains() -> list[dict]:
    domains = []
    for f in sorted((MOCK_DATA_DIR / "domains").glob("*.yaml")):
        data = yaml.safe_load(f.read_text())
        domains.append(data)
    return domains


def load_tags() -> list[dict]:
    data = yaml.safe_load((MOCK_DATA_DIR / "tags" / "tags.yaml").read_text())
    return data.get("tags", [])


def load_glossary_terms() -> list[dict]:
    terms = []
    for f in sorted((MOCK_DATA_DIR / "glossary").glob("*.yaml")):
        data = yaml.safe_load(f.read_text())
        terms.extend(data.get("glossary_terms", []))
    return terms


def load_datasets() -> list[dict]:
    datasets = []
    for f in sorted((MOCK_DATA_DIR / "datasets").glob("*.yaml")):
        data = yaml.safe_load(f.read_text())
        datasets.extend(data.get("datasets", []))
    return datasets


def ingest_owners(emitter: DatahubRestEmitter, owners: list[dict]) -> dict[str, str]:
    """Return mapping of owner id -> corpuser urn."""
    id_to_urn: dict[str, str] = {}
    for owner in owners:
        oid = owner.get("id", "")
        username = oid
        urn = _urn("corpuser", username)
        id_to_urn[oid] = urn
        key = MetadataChangeProposalWrapper(
            entityUrn=urn,
            aspect=sc.CorpUserKeyClass(username=username),
        )
        _emit(emitter, key)
        info = MetadataChangeProposalWrapper(
            entityUrn=urn,
            aspect=sc.CorpUserInfoClass(
                active=True,
                displayName=owner.get("name", username),
                email=owner.get("email", f"{username}@vinfast.vn"),
                title=owner.get("title", ""),
                departmentName=owner.get("department", ""),
            ),
        )
        _emit(emitter, info)
        _emit(emitter, _status_mcp(urn))
        log.info("owner_ingested", username=username, name=owner.get("name"))
    return id_to_urn


def ingest_domains(emitter: DatahubRestEmitter, domains: list[dict], owners: dict[str, str]) -> dict[str, str]:
    """Return mapping of domain name (uppercase) -> domain urn."""
    name_to_urn: dict[str, str] = {}
    for dom in domains:
        name = dom.get("domain", "")
        dkey = re.sub(r"[^A-Za-z0-9]+", "", name.lower()) or "unknown"
        urn = _urn("domain", dkey)
        name_to_urn[name.upper()] = urn
        _emit(
            emitter,
            MetadataChangeProposalWrapper(
                entityUrn=urn,
                aspect=sc.DomainKeyClass(id=dkey),
            ),
        )
        owner_urn = owners.get(dom.get("owner", ""))
        custom_props: dict[str, str] = {}
        if dom.get("business_objective"):
            custom_props["businessObjective"] = dom["business_objective"]
        if dom.get("technical_owner"):
            custom_props["technicalOwner"] = dom["technical_owner"]
        props = sc.DomainPropertiesClass(
            name=name,
            description=dom.get("description", ""),
            customProperties=custom_props or None,
        )
        _emit(
            emitter,
            MetadataChangeProposalWrapper(entityUrn=urn, aspect=props),
        )
        if owner_urn:
            ownership = sc.OwnershipClass(
                owners=[
                    sc.OwnerClass(
                        owner=owner_urn,
                        type=sc.OwnershipTypeClass.DATAOWNER,
                    )
                ]
            )
            _emit(
                emitter,
                MetadataChangeProposalWrapper(entityUrn=urn, aspect=ownership),
            )
        log.info("domain_ingested", name=name, urn=urn)
    return name_to_urn


def ingest_tags(emitter: DatahubRestEmitter, tags: list[dict]) -> dict[str, str]:
    name_to_urn: dict[str, str] = {}
    for tag in tags:
        name = tag.get("name", "")
        urn = _urn("tag", name.lower())
        name_to_urn[name.lower()] = urn
        _emit(
            emitter,
            MetadataChangeProposalWrapper(
                entityUrn=urn,
                aspect=sc.TagKeyClass(name=name.lower()),
            ),
        )
        _emit(
            emitter,
            MetadataChangeProposalWrapper(
                entityUrn=urn,
                aspect=sc.TagPropertiesClass(
                    name=name,
                    description=tag.get("description", ""),
                ),
            ),
        )
        log.info("tag_ingested", name=name)
    return name_to_urn


def ingest_glossary_terms(
    emitter: DatahubRestEmitter,
    terms: list[dict],
    domains: dict[str, str],
) -> dict[str, str]:
    """Return mapping of term name (lowercase) -> glossaryTerm urn."""
    name_to_urn: dict[str, str] = {}
    for term in terms:
        name = term.get("name", "")
        urn = _glossary_urn(name)
        name_to_urn[name.lower()] = urn
        _emit(
            emitter,
            MetadataChangeProposalWrapper(
                entityUrn=urn,
                aspect=sc.GlossaryTermKeyClass(name=name.lower()),
            ),
        )
        custom_props: dict[str, str] = {}
        if term.get("business_meaning"):
            custom_props["businessMeaning"] = term["business_meaning"]
        if term.get("example"):
            custom_props["example"] = term["example"]
        info = sc.GlossaryTermInfoClass(
            definition=term.get("definition", ""),
            termSource="CLASSIFICATION",
            customProperties=custom_props or None,
            name=name,
        )
        _emit(
            emitter,
            MetadataChangeProposalWrapper(entityUrn=urn, aspect=info),
        )
        log.info("glossary_term_ingested", name=name)

    # Related terms (knowledge graph relationships)
    for term in terms:
        name = term.get("name", "")
        urn = name_to_urn.get(name.lower())
        if not urn:
            continue
        related = term.get("related_terms", [])
        related_urns = [name_to_urn[r.lower()] for r in related if r.lower() in name_to_urn]
        if related_urns:
            _emit(
                emitter,
                MetadataChangeProposalWrapper(
                    entityUrn=urn,
                    aspect=sc.GlossaryRelatedTermsClass(relatedTerms=related_urns),
                ),
            )
    return name_to_urn


def _schema_type(raw: str) -> sc.SchemaFieldDataTypeClass:
    t = (raw or "string").lower()
    if t in ("int", "integer", "bigint", "smallint", "tinyint", "float", "double", "decimal", "numeric", "number"):
        return sc.SchemaFieldDataTypeClass(sc.NumberTypeClass())
    if t in ("bool", "boolean"):
        return sc.SchemaFieldDataTypeClass(sc.BooleanTypeClass())
    if t in ("date", "datetime", "timestamp", "time"):
        return sc.SchemaFieldDataTypeClass(sc.DateTypeClass())
    return sc.SchemaFieldDataTypeClass(sc.StringTypeClass())


def ingest_datasets(
    emitter: DatahubRestEmitter,
    datasets: list[dict],
    owners: dict[str, str],
    tags: dict[str, str],
    glossary: dict[str, str],
    domains: dict[str, str],
) -> list[str]:
    dataset_urns: list[str] = []
    for ds in datasets:
        name = ds.get("name", "")
        platform = (ds.get("platform", "redshift") or "redshift").lower()
        urn = _urn("dataset", f"(urn:li:dataPlatform:{platform},{name},PROD)")
        dataset_urns.append(urn)

        _emit(
            emitter,
            MetadataChangeProposalWrapper(
                entityUrn=urn,
                aspect=sc.DatasetKeyClass(platform=platform, name=name, origin="PROD"),
            ),
        )
        custom_props: dict[str, str] = {}
        if ds.get("refresh_frequency"):
            custom_props["refreshFrequency"] = ds["refresh_frequency"]
        _emit(
            emitter,
            MetadataChangeProposalWrapper(
                entityUrn=urn,
                aspect=sc.DatasetPropertiesClass(
                    name=name,
                    description=ds.get("description", ""),
                    customProperties=custom_props or None,
                ),
            ),
        )

        # Schema
        fields: list[sc.SchemaFieldClass] = []
        primary_keys: list[str] = []
        for col in ds.get("columns", []):
            field_path = col.get("name", "")
            field_props: dict[str, str] = {}
            if col.get("business_definition"):
                field_props["businessDefinition"] = col["business_definition"]
            if col.get("example"):
                field_props["example"] = col["example"]
            fields.append(
                sc.SchemaFieldClass(
                    fieldPath=field_path,
                    type=_schema_type(col.get("data_type", "string")),
                    nativeDataType=col.get("data_type", "string"),
                    nullable=col.get("nullable", True),
                    description=col.get("description", "") or None,
                    jsonProps=_json_dumps(field_props) if field_props else None,
                )
            )
        schema_hash = hashlib.md5(
            ",".join(f.fieldPath for f in fields).encode()
        ).hexdigest()
        _emit(
            emitter,
            MetadataChangeProposalWrapper(
                entityUrn=urn,
                aspect=sc.SchemaMetadataClass(
                    schemaName=name,
                    platform=f"urn:li:dataPlatform:{platform}",
                    version=0,
                    hash=schema_hash,
                    platformSchema=sc.OtherSchemaClass(rawSchema=""),
                    fields=fields,
                    created=_audit_stamp(),
                    lastModified=_audit_stamp(),
                    primaryKeys=primary_keys or None,
                ),
            ),
        )

        # Ownership
        ds_owners = []
        for oid in ds.get("owners", []):
            owner_urn = owners.get(oid)
            if owner_urn:
                ds_owners.append(
                    sc.OwnerClass(
                        owner=owner_urn,
                        type=sc.OwnershipTypeClass.DATAOWNER,
                    )
                )
        if ds_owners:
            _emit(
                emitter,
                MetadataChangeProposalWrapper(
                    entityUrn=urn,
                    aspect=sc.OwnershipClass(owners=ds_owners),
                ),
            )

        # Tags
        ds_tags = [tags[t.lower()] for t in ds.get("tags", []) if t.lower() in tags]
        if ds_tags:
            _emit(
                emitter,
                MetadataChangeProposalWrapper(
                    entityUrn=urn,
                    aspect=sc.GlobalTagsClass(
                        tags=[sc.TagAssociationClass(tag=t) for t in ds_tags]
                    ),
                ),
            )

        # Domain
        domain_name = ds.get("domain", "")
        domain_urn = domains.get(domain_name.upper())
        if domain_urn:
            _emit(
                emitter,
                MetadataChangeProposalWrapper(
                    entityUrn=urn,
                    aspect=sc.DomainsClass(domains=[domain_urn]),
                ),
            )

        _emit(emitter, _status_mcp(urn))
        _emit(
            emitter,
            _browse_mcp(urn, [f"/prod/{platform}/{name}"]),
        )
        log.info("dataset_ingested", name=name, urn=urn)
    return dataset_urns


def ingest_lineage(emitter: DatahubRestEmitter, datasets: list[dict], dataset_urns: list[str]) -> None:
    """Create upstream lineage based on column-level foreign-key references."""
    urn_by_name = {ds["name"]: dataset_urns[i] for i, ds in enumerate(datasets)}
    for i, ds in enumerate(datasets):
        urn = dataset_urns[i]
        upstream_urns: list[str] = []
        for col in ds.get("columns", []):
            bd = (col.get("business_definition") or "").lower()
            m = re.search(r"tham chiếu đến (\w+)", bd)
            if m:
                ref = m.group(1)
                for target_name, target_urn in urn_by_name.items():
                    if target_name.lower() == ref.lower() and target_urn != urn:
                        upstream_urns.append(target_urn)
        if upstream_urns:
            _emit(
                emitter,
                MetadataChangeProposalWrapper(
                    entityUrn=urn,
                    aspect=sc.UpstreamLineageClass(
                        upstreams=[
                            sc.UpstreamClass(
                                dataset=u,
                                type=sc.DatasetLineageTypeClass.TRANSFORMED,
                            )
                            for u in dict.fromkeys(upstream_urns)
                        ]
                    ),
                ),
            )
            log.info("lineage_ingested", dataset=ds["name"], upstreams=upstream_urns)


def main() -> None:
    emitter = DatahubRestEmitter(gms_server=GMS_URL, token=GMS_TOKEN)

    log.info("loading_mock_data")
    owners = load_owners()
    domains = load_domains()
    tags = load_tags()
    glossary_terms = load_glossary_terms()
    datasets = load_datasets()
    log.info(
        "data_loaded",
        owners=len(owners),
        domains=len(domains),
        tags=len(tags),
        glossary_terms=len(glossary_terms),
        datasets=len(datasets),
    )

    log.info("ingesting_owners")
    owner_urns = ingest_owners(emitter, owners)
    log.info("ingesting_domains")
    domain_urns = ingest_domains(emitter, domains, owner_urns)
    log.info("ingesting_tags")
    tag_urns = ingest_tags(emitter, tags)
    log.info("ingesting_glossary_terms")
    glossary_urns = ingest_glossary_terms(emitter, glossary_terms, domain_urns)
    log.info("ingesting_datasets")
    dataset_urns = ingest_datasets(
        emitter, datasets, owner_urns, tag_urns, glossary_urns, domain_urns
    )
    log.info("ingesting_lineage")
    ingest_lineage(emitter, datasets, dataset_urns)

    log.info(
        "ingest_complete",
        owners=len(owner_urns),
        domains=len(domain_urns),
        tags=len(tag_urns),
        glossary_terms=len(glossary_urns),
        datasets=len(dataset_urns),
    )


if __name__ == "__main__":
    main()
