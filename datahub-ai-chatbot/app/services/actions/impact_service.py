"""Impact analysis and lineage graph builder service."""
from __future__ import annotations

from collections.abc import Sequence

import structlog

from app.auth.models import UserContext
from app.schemas.actions import ImpactItem, ImpactResponse
from app.schemas.chat import LineageData, LineageNode
from app.services.actions.base import BaseActionService

log = structlog.get_logger()


def urn_kind(urn: str) -> str:
    if ":dashboard:" in urn or ":dashboard(" in urn:
        return "dashboard"
    if ":dataJob:" in urn or ":dataJob(" in urn:
        return "job"
    if ":dataFlow:" in urn or ":dataFlow(" in urn:
        return "pipeline"
    if ":dataset:" in urn or ":dataset(" in urn:
        return "dataset"
    if ":document:" in urn:
        return "document"
    return "other"


class ImpactActionService(BaseActionService):
    """Handles upstream/downstream impact analysis and lineage visualization payloads."""

    async def build_lineage_data(
        self, urn: str, name: str, url: str | None
    ) -> LineageData | None:
        upstreams, downstreams = await self._lineage_urns(urn)
        nodes = await self._resolve_urns(upstreams + downstreams)

        def _nodes(urns: Sequence[str]) -> list[LineageNode]:
            result: list[LineageNode] = []
            for u in urns:
                if u == urn:
                    continue
                e = nodes.get(u)
                if e:
                    result.append(
                        LineageNode(
                            name=e.display_name or e.name,
                            urn=e.urn,
                            url=e.datahub_url,
                            entity_type=e.entity_type,
                        )
                    )
                else:
                    result.append(LineageNode(name=u, urn=u))
            return result

        if not upstreams and not downstreams:
            return None
        return LineageData(
            entity_name=name,
            entity_urn=urn,
            entity_url=url,
            upstreams=_nodes(upstreams),
            downstreams=_nodes(downstreams),
        )

    async def impact_analysis(
        self,
        dataset_query: str,
        user: UserContext | None = None,
    ) -> ImpactResponse:
        entity = await self.resolve_dataset(dataset_query, user=user)
        if entity is None:
            return ImpactResponse(
                dataset=dataset_query,
                business_impact=["Không tìm thấy dataset trong metadata DataHub."],
                valid=False,
            )

        upstreams, downstreams = await self._lineage_urns(entity.urn)
        entities = await self._resolve_urns(downstreams)
        dashboards: list[ImpactItem] = []
        datasets: list[ImpactItem] = []
        pipelines: list[ImpactItem] = []
        jobs: list[ImpactItem] = []

        for d_urn in downstreams:
            e = entities.get(d_urn)
            name = (e.display_name or e.name) if e else d_urn
            kind = urn_kind(d_urn)
            item = ImpactItem(urn=d_urn, name=name, url=e.datahub_url if e else None, kind=kind)
            if kind == "dashboard":
                dashboards.append(item)
            elif kind == "pipeline":
                pipelines.append(item)
            elif kind == "job":
                jobs.append(item)
            else:
                datasets.append(item)

        # Also consider dashboards that reference this dataset in their payload.
        if self._auth_service is None or user is None or user.is_admin:
            for dash in await self._repo.list_by_type("dashboard", limit=1000):
                up_urns = set((dash.payload or {}).get("upstreams") or [])
                if entity.urn in up_urns and dash.urn not in {d.urn for d in dashboards}:
                    dashboards.append(
                        ImpactItem(
                            urn=dash.urn,
                            name=dash.display_name or dash.name,
                            url=dash.datahub_url,
                            kind="dashboard",
                        )
                    )

        total = len(datasets) + len(dashboards) + len(pipelines) + len(jobs)
        risk = "low"
        if total >= 6:
            risk = "high"
        elif total >= 3:
            risk = "medium"

        business_impact: list[str] = []
        if datasets:
            business_impact.append(
                f"{len(datasets)} dataset hạ nguồn phụ thuộc vào dataset này: "
                + ", ".join(d.name for d in datasets[:5])
                + ("..." if len(datasets) > 5 else "")
                + "."
            )
        if dashboards:
            business_impact.append(
                f"{len(dashboards)} dashboard có thể bị ảnh hưởng: "
                + ", ".join(d.name for d in dashboards[:5])
                + ("..." if len(dashboards) > 5 else "")
                + "."
            )
        if pipelines:
            business_impact.append(f"{len(pipelines)} pipeline có thể bị ảnh hưởng.")
        if jobs:
            business_impact.append(f"{len(jobs)} job có thể bị ảnh hưởng.")
        if not business_impact:
            business_impact.append("Không tìm thấy phụ thuộc hạ nguồn nào từ lineage DataHub.")

        return ImpactResponse(
            dataset=entity.display_name or entity.name,
            urn=entity.urn,
            affected_datasets=datasets,
            affected_dashboards=dashboards,
            affected_pipelines=pipelines,
            affected_jobs=jobs,
            business_impact=business_impact,
            risk_level=risk,
            valid=True,
        )
