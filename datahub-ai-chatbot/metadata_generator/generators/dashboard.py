import logging

from datahub.emitter.mcp import MetadataChangeProposalWrapper
from datahub.metadata.schema_classes import (
    BrowsePathsClass,
    ChangeAuditStampsClass,
    ChartInfoClass,
    ChartKeyClass,
    DashboardInfoClass,
    DashboardKeyClass,
    GlobalTagsClass,
    AuditStampClass,
    OwnerClass,
    OwnershipClass,
    OwnershipTypeClass,
    StatusClass,
    SubTypesClass,
    TagAssociationClass,
    DomainsClass,
)

from config import (
    chart_urn,
    dashboard_urn,
    domain_urn,
    emitter,
    user_urn,
)

log = logging.getLogger(__name__)


def emit_dashboards(dashboards: list[dict]) -> None:
    for db in dashboards:
        name = db["name"]
        dash_urn = dashboard_urn(name)
        domain = db.get("domain")
        tags = db.get("tags", [])

        # Status
        emitter.emit_mcp(
            MetadataChangeProposalWrapper(
                entityType="dashboard",
                entityUrn=dash_urn,
                aspectName="status",
                aspect=StatusClass(removed=False),
            )
        )

        # DashboardKey
        emitter.emit_mcp(
            MetadataChangeProposalWrapper(
                entityType="dashboard",
                entityUrn=dash_urn,
                aspectName="dashboardKey",
                aspect=DashboardKeyClass(dashboardTool="powerbi", dashboardId=name),
            )
        )

        # BrowsePaths
        if domain:
            emitter.emit_mcp(
                MetadataChangeProposalWrapper(
                    entityType="dashboard",
                    entityUrn=dash_urn,
                    aspectName="browsePaths",
                    aspect=BrowsePathsClass(
                        paths=[f"/{domain}/dashboards/{name}"]
                    ),
                )
            )

        # Charts
        chart_urns = []
        for ch in db.get("charts", []):
            ch_urn = chart_urn(ch["name"])
            chart_urns.append(ch_urn)

            # Chart status + key + info
            emitter.emit_mcp(
                MetadataChangeProposalWrapper(
                    entityType="chart",
                    entityUrn=ch_urn,
                    aspectName="status",
                    aspect=StatusClass(removed=False),
                )
            )
            emitter.emit_mcp(
                MetadataChangeProposalWrapper(
                    entityType="chart",
                    entityUrn=ch_urn,
                    aspectName="chartKey",
                    aspect=ChartKeyClass(dashboardTool="powerbi", chartId=ch["name"]),
                )
            )
            emitter.emit_mcp(
                MetadataChangeProposalWrapper(
                    entityType="chart",
                    entityUrn=ch_urn,
                    aspectName="chartInfo",
                    aspect=ChartInfoClass(
                        title=ch["displayName"],
                        description=ch.get("description", ""),
                        type=ch.get("chart_type", "Bar"),
                        lastModified=ChangeAuditStampsClass(
                            created=AuditStampClass(time=0, actor="urn:li:corpUser:ingestion"),
                            lastModified=AuditStampClass(time=0, actor="urn:li:corpUser:ingestion"),
                        ),
                    ),
                )
            )

            # Tag charts
            if tags:
                emitter.emit_mcp(
                    MetadataChangeProposalWrapper(
                        entityType="chart",
                        entityUrn=ch_urn,
                        aspectName="globalTags",
                        aspect=GlobalTagsClass(
                            tags=[TagAssociationClass(tag=f"urn:li:tag:{t}") for t in tags]
                        ),
                    )
                )

            log.info("Chart %s created", ch["name"])

        # DashboardInfo
        emitter.emit_mcp(
            MetadataChangeProposalWrapper(
                entityType="dashboard",
                entityUrn=dash_urn,
                aspectName="dashboardInfo",
                    aspect=DashboardInfoClass(
                        title=db.get("displayName", name),
                        description=db.get("description", ""),
                        charts=chart_urns,
                        lastModified=ChangeAuditStampsClass(
                            created=AuditStampClass(time=0, actor="urn:li:corpUser:ingestion"),
                            lastModified=AuditStampClass(time=0, actor="urn:li:corpUser:ingestion"),
                        ),
                        customProperties={
                        "update_frequency": db.get("update_frequency", ""),
                        "powerbi_url": db.get("powerbi_url", ""),
                        "documentation": db.get("documentation", ""),
                    },
                ),
            )
        )

        # SubTypes
        emitter.emit_mcp(
            MetadataChangeProposalWrapper(
                entityType="dashboard",
                entityUrn=dash_urn,
                aspectName="subTypes",
                aspect=SubTypesClass(typeNames=["powerbi"]),
            )
        )

        # Ownership
        owner_email = db.get("owner", "platform-team@vinfast.vn")
        emitter.emit_mcp(
            MetadataChangeProposalWrapper(
                entityType="dashboard",
                entityUrn=dash_urn,
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
                    entityType="dashboard",
                    entityUrn=dash_urn,
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
                    entityType="dashboard",
                    entityUrn=dash_urn,
                    aspectName="domains",
                    aspect=DomainsClass(domains=[domain_urn(domain)]),
                )
            )

        log.info("Dashboard %s created", name)
