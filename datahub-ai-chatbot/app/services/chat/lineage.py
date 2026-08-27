from collections.abc import Sequence

from app.schemas.chat import LineageData, LineageNode
from app.services.chat.context import ChatContext
from guardrails.sanitizer import mask_secrets
from retrieval.hybrid_search import SearchResult


class LineageService:
    """LineageService."""

    def __init__(self, ctx: ChatContext) -> None:
        self._ctx = ctx


    async def build_lineage_data(self, result: SearchResult) -> LineageData | None:
        payload = result.payload or {}
        main_urn = result.urn

        def _dedupe(urns: Sequence[str]) -> list[str]:
            seen: set[str] = set()
            out: list[str] = []
            for u in urns:
                if not u or u == main_urn or u in seen:
                    continue
                seen.add(u)
                out.append(u)
            return out

        upstreams = _dedupe(payload.get("upstreams", []) or [])
        downstreams = _dedupe(payload.get("downstreams", []) or [])
        # A dataset appearing on BOTH sides would render twice; keep it upstream only.
        upstream_set = set(upstreams)
        downstreams = [d for d in downstreams if d not in upstream_set]
        if not upstreams and not downstreams:
            return None

        async def _node(urn: str) -> LineageNode:
            e = await self._ctx.entity_repo.get_by_urn(urn)
            if e:
                return LineageNode(
                    name=e.display_name or e.name, urn=e.urn,
                    url=e.datahub_url, entity_type=e.entity_type,
                )
            return LineageNode(name=urn, urn=urn)

        up_nodes = [await _node(u) for u in upstreams]
        down_nodes = [await _node(d) for d in downstreams]
        return LineageData(
            entity_name=result.name,
            entity_urn=result.urn,
            entity_url=result.datahub_url,
            upstreams=up_nodes,
            downstreams=down_nodes,
        )


    async def build_lineage_answer(
        self, result: SearchResult,
        history: list[tuple[str, str]] | None = None,
    ) -> tuple[str, list, str]:
        """Deterministic lineage answer, built from the SAME payload that drives the SVG."""
        from retrieval.citation import Citation

        payload = result.payload or {}
        main_urn = result.urn

        def _dedupe(urns):
            seen, out = set(), []
            for u in urns:
                if not u or u == main_urn or u in seen:
                    continue
                seen.add(u)
                out.append(u)
            return out

        upstreams = _dedupe(payload.get("upstreams", []) or [])
        downstreams = _dedupe(payload.get("downstreams", []) or [])
        up_set = set(upstreams)
        downstreams = [d for d in downstreams if d not in up_set]

        async def _name(urn: str) -> str:
            e = await self._ctx.entity_repo.get_by_urn(urn)
            return (e.display_name or e.name) if e else urn

        async def _url(urn: str) -> str | None:
            e = await self._ctx.entity_repo.get_by_urn(urn)
            return e.datahub_url if e else None

        parts: list[str] = []
        citations: list = []
        idx = 1

        async def _fmt(urn: str) -> str:
            nonlocal idx
            cid = f"E{idx}"
            idx += 1
            e = await self._ctx.entity_repo.get_by_urn(urn)
            name = (e.display_name or e.name) if e else urn
            plat = f" ({e.platform})" if (e and e.platform) else ""
            citations.append(Citation(cid=cid, source_type="datahub_entity",
                                      entity_urn=urn, entity_name=name,
                                      url=e.datahub_url if e else None))
            return f"{name}{plat} [{cid}]"

        if upstreams:
            names = ", ".join([await _fmt(u) for u in upstreams])
            parts.append(f"{len(upstreams)} upstream: {names}")
        if downstreams:
            names = ", ".join([await _fmt(d) for d in downstreams])
            parts.append(f"{len(downstreams)} downstream: {names}")

        if not parts:
            answer = mask_secrets(
                f"Dataset **{result.name}** hiện không có lineage (upstream/downstream) được ghi nhận trong DataHub."
            )
        else:
            answer = mask_secrets(
                f"Dataset **{result.name}** có lineage theo DataHub: " + "; ".join(parts) + "."
            )
        return answer, citations, result.name
