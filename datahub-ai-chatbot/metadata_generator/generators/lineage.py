import logging

from datahub.emitter.mcp import MetadataChangeProposalWrapper
from datahub.metadata.schema_classes import UpstreamLineageClass, UpstreamClass, AuditStampClass

from config import emitter

log = logging.getLogger(__name__)


def emit_lineage(lineage_chains: list[dict]) -> None:
    for chain in lineage_chains:
        upstream_urns = chain["upstream_urns"]
        downstream_urns = chain["downstream_urns"]

        for target_urn in downstream_urns:
            upstreams = [
                UpstreamClass(
                    dataset=u_urn,
                    type="TRANSFORMED",
                    auditStamp=AuditStampClass(time=0, actor="urn:li:corpUser:ingestion"),
                )
                for u_urn in upstream_urns
            ]

            if ":dataset:" not in target_urn:
                log.debug("Skipping lineage for non-dataset %s", target_urn)
                continue

            mcp = MetadataChangeProposalWrapper(
                entityType="dataset",
                entityUrn=target_urn,
                aspectName="upstreamLineage",
                aspect=UpstreamLineageClass(upstreams=upstreams),
            )
            try:
                emitter.emit_mcp(mcp)
                log.info("Lineage set for %s", target_urn)
            except Exception as e:
                log.error("Failed to set lineage for %s: %s", target_urn, e)
