import logging

from datahub.emitter.mcp import MetadataChangeProposalWrapper
from datahub.metadata.schema_classes import (
    AuditStampClass,
    BrowsePathsClass,
    DatasetPropertiesClass,
    DateTypeClass,
    GlobalTagsClass,
    GlossaryTermAssociationClass,
    GlossaryTermsClass,
    NullTypeClass,
    NumberTypeClass,
    OtherSchemaClass,
    OwnerClass,
    OwnershipClass,
    OwnershipTypeClass,
    SchemaFieldClass,
    SchemaFieldDataTypeClass,
    SchemaMetadataClass,
    StatusClass,
    StringTypeClass,
    SubTypesClass,
    TagAssociationClass,
    DomainsClass,
)

from config import (
    data_platform_urn,
    dataset_urn,
    domain_urn,
    emitter,
    glossary_term_urn,
    user_urn,
)

log = logging.getLogger(__name__)

_DATATYPE_MAP = {
    "VARCHAR": StringTypeClass,
    "INTEGER": NumberTypeClass,
    "DECIMAL": NumberTypeClass,
    "DATE": DateTypeClass,
    "TIMESTAMP": DateTypeClass,
    "BOOLEAN": NumberTypeClass,
    "TEXT": StringTypeClass,
    "BIGINT": NumberTypeClass,
    "SMALLINT": NumberTypeClass,
    "FLOAT": NumberTypeClass,
    "NUMERIC": NumberTypeClass,
    "CHAR": StringTypeClass,
    "NVARCHAR": StringTypeClass,
    "NCHAR": StringTypeClass,
    "CLOB": StringTypeClass,
    "BLOB": NullTypeClass,
    "RAW": NullTypeClass,
}


def _to_schema_field(col: dict) -> SchemaFieldClass:
    base_type = col["datatype"].split("(")[0].upper()
    type_cls = _DATATYPE_MAP.get(base_type, StringTypeClass)
    return SchemaFieldClass(
        fieldPath=col["name"],
        type=SchemaFieldDataTypeClass(type=type_cls()),
        nativeDataType=col["datatype"],
        description=col.get("business_definition") or col.get("description", ""),
        nullable=col.get("nullable", True),
    )


def emit_datasets(datasets: list[dict]) -> None:
    for ds in datasets:
        name = ds["name"]
        urn = dataset_urn(name, ds.get("platform", "sap"))
        domain = ds.get("domain")
        tags = ds.get("tags", [])

        # Status (soft-delete = False)
        emitter.emit_mcp(
            MetadataChangeProposalWrapper(
                entityType="dataset",
                entityUrn=urn,
                aspectName="status",
                aspect=StatusClass(removed=False),
            )
        )

        # DatasetProperties
        emitter.emit_mcp(
            MetadataChangeProposalWrapper(
                entityType="dataset",
                entityUrn=urn,
                aspectName="datasetProperties",
                aspect=DatasetPropertiesClass(
                    name=name,
                    description=ds["description"],
                    customProperties={"domain": domain} if domain else {},
                ),
            )
        )

        # BrowsePaths
        if domain:
            emitter.emit_mcp(
                MetadataChangeProposalWrapper(
                    entityType="dataset",
                    entityUrn=urn,
                    aspectName="browsePaths",
                    aspect=BrowsePathsClass(
                        paths=[f"/{domain}/{name}"]
                    ),
                )
            )

        # SchemaMetadata
        if ds.get("columns"):
            fields = [_to_schema_field(col) for col in ds["columns"]]
            emitter.emit_mcp(
                MetadataChangeProposalWrapper(
                    entityType="dataset",
                    entityUrn=urn,
                    aspectName="schemaMetadata",
                    aspect=SchemaMetadataClass(
                        schemaName=name,
                        platform=data_platform_urn(ds.get("platform", "sap")),
                        version=0,
                        fields=fields,
                        hash="",
                        platformSchema=OtherSchemaClass(rawSchema=""),
                        created=AuditStampClass(time=0, actor="urn:li:corpUser:ingestion"),
                    ),
                )
            )

        # SubTypes
        et = ds.get("domain", "unknown")
        subtype = "fact" if name.startswith("fact_") else "dim" if name.startswith("dim_") else "agg" if name.startswith("agg_") else "staging" if name.startswith("stg_") else "sap" if name.startswith("sap_") else "other"
        emitter.emit_mcp(
            MetadataChangeProposalWrapper(
                entityType="dataset",
                entityUrn=urn,
                aspectName="subTypes",
                aspect=SubTypesClass(typeNames=[subtype]),
            )
        )

        # Ownership
        owner_map = {
            "manufacturing": "truong.nguyen@vinfast.vn",
            "logistics": "anh.tran@vinfast.vn",
            "finance": "thuy.nguyen@vinfast.vn",
            "supply_chain": "cuong.vo@vinfast.vn",
            "sales": "ha.le@vinfast.vn",
            "after_sales": "hieu.nguyen@vinfast.vn",
            "vehicle_development": "tuan.le@vinfast.vn",
            "vgreen": "mai.nguyen@vinfast.vn",
            "data_governance": "thao.le@vinfast.vn",
        }
        owner_email = owner_map.get(domain, "platform-team@vinfast.vn")
        emitter.emit_mcp(
            MetadataChangeProposalWrapper(
                entityType="dataset",
                entityUrn=urn,
                aspectName="ownership",
                aspect=OwnershipClass(
                    owners=[
                        OwnerClass(
                            owner=user_urn(owner_email),
                            type=OwnershipTypeClass.BUSINESS_OWNER,
                        ),
                    ]
                ),
            )
        )

        # GlobalTags
        if tags:
            emitter.emit_mcp(
                MetadataChangeProposalWrapper(
                    entityType="dataset",
                    entityUrn=urn,
                    aspectName="globalTags",
                    aspect=GlobalTagsClass(
                        tags=[TagAssociationClass(tag=f"urn:li:tag:{t}") for t in tags]
                    ),
                )
            )

        # Domain association
        if domain:
            emitter.emit_mcp(
                MetadataChangeProposalWrapper(
                    entityType="dataset",
                    entityUrn=urn,
                    aspectName="domains",
                    aspect=DomainsClass(domains=[domain_urn(domain)]),
                )
            )

        log.info("Dataset %s created", name)
