import logging

from datahub.emitter.mcp import MetadataChangeProposalWrapper
from datahub.metadata.schema_classes import TagPropertiesClass

from config import emitter, tag_urn

log = logging.getLogger(__name__)


def emit_tags(tags: list[dict]) -> None:
    for tag in tags:
        urn = tag_urn(tag["name"])
        mcp = MetadataChangeProposalWrapper(
            entityType="tag",
            entityUrn=urn,
            aspectName="tagProperties",
            aspect=TagPropertiesClass(
                name=tag["name"],
                description=tag["description"],
            ),
        )
        try:
            emitter.emit_mcp(mcp)
            log.info("Tag %s created", tag["name"])
        except Exception as e:
            log.error("Failed to create tag %s: %s", tag["name"], e)
