import logging

from datahub.emitter.mcp import MetadataChangeProposalWrapper
from datahub.metadata.schema_classes import DomainPropertiesClass, OwnershipClass, OwnerClass, OwnershipTypeClass

from config import domain_urn, user_urn, group_urn, emitter

log = logging.getLogger(__name__)


def emit_domains(domains: list[dict]) -> None:
    for d in domains:
        urn = domain_urn(d["id"])
        props = MetadataChangeProposalWrapper(
            entityType="domain",
            entityUrn=urn,
            aspectName="domainProperties",
            aspect=DomainPropertiesClass(
                name=d["name"],
                description=d["description"],
            ),
        )
        try:
            emitter.emit_mcp(props)
            log.info("Domain %s created", d["id"])
        except Exception as e:
            log.error("Failed to create domain %s: %s", d["id"], e)

        ownership = MetadataChangeProposalWrapper(
            entityType="domain",
            entityUrn=urn,
            aspectName="ownership",
            aspect=OwnershipClass(
                owners=[
                    OwnerClass(
                        owner=user_urn(d["business_owner"]),
                        type=OwnershipTypeClass.BUSINESS_OWNER,
                    ),
                    OwnerClass(
                        owner=user_urn(d["technical_owner"]),
                        type=OwnershipTypeClass.TECHNICAL_OWNER,
                    ),
                    OwnerClass(
                        owner=group_urn(d["system_owner"]),
                        type=OwnershipTypeClass.DATAOWNER,
                    ),
                ]
            ),
        )
        try:
            emitter.emit_mcp(ownership)
            log.info("Domain %s ownership set", d["id"])
        except Exception as e:
            log.error("Failed to set ownership for domain %s: %s", d["id"], e)
