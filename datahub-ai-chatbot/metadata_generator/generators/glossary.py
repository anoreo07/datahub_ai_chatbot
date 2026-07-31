import logging

from datahub.emitter.mcp import MetadataChangeProposalWrapper
from datahub.metadata.schema_classes import GlossaryTermInfoClass, DomainsClass

from config import glossary_term_urn, domain_urn, emitter

log = logging.getLogger(__name__)


def emit_glossary_terms(terms_by_domain: dict[str, list[dict]]) -> None:
    for domain_id, terms in terms_by_domain.items():
        for term in terms:
            urn = glossary_term_urn(term["name"])
            info = GlossaryTermInfoClass(
                name=term["displayName"],
                definition=term.get("business_definition") or term["description"],
                termSource="",
                sourceRef="",
                customProperties={
                    "domain": domain_id,
                    "formula": term.get("formula", ""),
                    "example": term.get("example", ""),
                    "description": term.get("description", ""),
                },
            )
            mcp = MetadataChangeProposalWrapper(
                entityType="glossaryTerm",
                entityUrn=urn,
                aspectName="glossaryTermInfo",
                aspect=info,
            )
            try:
                emitter.emit_mcp(mcp)
                if domain_id:
                    domain_mcp = MetadataChangeProposalWrapper(
                        entityType="glossaryTerm",
                        entityUrn=urn,
                        aspectName="domains",
                        aspect=DomainsClass(domains=[domain_urn(domain_id)]),
                    )
                    emitter.emit_mcp(domain_mcp)
                log.info("Glossary term %s created", term["name"])
            except Exception as e:
                log.error("Failed to create glossary term %s: %s", term["name"], e)
