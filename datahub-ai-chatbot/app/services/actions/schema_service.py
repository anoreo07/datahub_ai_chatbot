"""Schema comparison and normalization action service."""
from __future__ import annotations

import unicodedata
from collections.abc import Sequence

import structlog

from app.auth.models import UserContext
from app.schemas.actions import SchemaColumn, SchemaCompareResponse, SchemaMatchItem
from app.services.actions.base import BaseActionService
from database.models import Entity

log = structlog.get_logger()

SCHEMA_MATCH_MIN_SIMILARITY = 0.15


def normalize_column_name(s: str | None) -> str:
    """Accent- and case-insensitive normalization for column/name matching."""
    if not s:
        return ""
    s = s.lower().strip()
    s = s.replace("đ", "d").replace("Đ", "d")
    s = unicodedata.normalize("NFKD", s)
    return s.encode("ascii", "ignore").decode("ascii")


def extract_schema_columns(payload: dict | None) -> list[dict]:
    fields = (payload or {}).get("schema_fields") or []
    return [f for f in fields if isinstance(f, dict)]


class SchemaActionService(BaseActionService):
    """Handles schema comparison and matching against DataHub catalogs."""

    async def compare_schema(
        self,
        columns: Sequence[SchemaColumn],
        preferred_query: str = "",
        limit: int = 5,
        user: UserContext | None = None,
    ) -> SchemaCompareResponse:
        uploaded = {normalize_column_name(c.name) for c in columns if c.name}
        if not uploaded:
            return SchemaCompareResponse(candidates=[], total=0)

        # Prefer a user-named dataset, but still compute matches for all tables
        # so the comparison list is complete.
        datasets = await self._repo.list_by_type("dataset", limit=2000)

        def _jaccard(a: set[str], b: set[str]) -> float:
            union = a | b
            if not union:
                return 0.0
            return len(a & b) / len(union)

        scored: list[tuple[float, Entity]] = []
        for ds in datasets:
            ds_cols = {
                normalize_column_name(f.get("name") or "")
                for f in extract_schema_columns(ds.payload)
            }
            if not ds_cols:
                continue
            sim = _jaccard(uploaded, ds_cols)
            if sim >= SCHEMA_MATCH_MIN_SIMILARITY:
                scored.append((sim, ds))

        scored.sort(key=lambda t: -t[0])

        # Rank an explicitly-preferred dataset first when it overlaps at all.
        preferred = None
        if preferred_query:
            preferred = await self.resolve_dataset(preferred_query, user=user)
        if preferred:
            scored.sort(key=lambda t: (t[1].urn != preferred.urn, -t[0]))

        if self._auth_service is not None and user is not None:
            accessible = await self._auth_service.filter_accessible_urns(
                user, [e.urn for _, e in scored]
            )
            allowed = [t for t in scored if t[1].urn in accessible]
        else:
            allowed = list(scored)

        items: list[SchemaMatchItem] = []
        for sim, ds in allowed[:limit]:
            ds_cols = {
                normalize_column_name(f.get("name") or "")
                for f in extract_schema_columns(ds.payload)
            }
            matched = sorted(uploaded & ds_cols)
            missing = sorted(uploaded - ds_cols)
            additional = sorted(ds_cols - uploaded)
            payload = ds.payload or {}
            items.append(
                SchemaMatchItem(
                    urn=ds.urn,
                    name=ds.display_name or ds.name,
                    description=(payload.get("description") or ""),
                    platform=(payload.get("platform") or ""),
                    domain=(payload.get("domain") or ""),
                    url=ds.datahub_url,
                    similarity=round(sim, 3),
                    matched_columns=matched,
                    missing_columns=missing,
                    additional_columns=additional,
                )
            )
        return SchemaCompareResponse(candidates=items, total=len(items))
