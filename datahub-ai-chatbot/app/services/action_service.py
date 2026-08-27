"""Reusable, grounded services for the "+" action menu.

Facade integrating specialized domain services:
- SchemaActionService (schema comparison, column normalization)
- SqlActionService (candidate discovery, grounded SQL generation)
- ImpactActionService (impact analysis, lineage graph data)
- QualityActionService (data quality reports)
- MetadataReportService (metadata maturity overview)
"""
from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.authorization import AuthorizationService
from app.auth.models import UserContext
from app.schemas.actions import (
    ImpactResponse,
    ReportResponse,
    SchemaColumn,
    SchemaCompareResponse,
    SqlResponse,
)
from app.schemas.chat import LineageData
from app.schemas.quality import QualityReport
from app.services.actions import (
    SCHEMA_MATCH_MIN_SIMILARITY,
    BaseActionService,
    ImpactActionService,
    MetadataReportService,
    PermissionDeniedError,
    QualityActionService,
    SchemaActionService,
    SqlActionService,
    SqlCandidate,
    extract_filter_fields,
    extract_filter_values,
    extract_schema_columns,
    normalize_column_name,
    owner_names,
    profiling_stats,
    urn_kind,
)
from database.models import Entity

# Backward compatibility aliases
_norm = normalize_column_name
_schema_columns = extract_schema_columns
_owner_names = owner_names
_profiling_stats = profiling_stats
_urn_kind = urn_kind


class ActionService(BaseActionService):
    """Facade coordinator exposing all action capabilities to API and Chat services."""

    def __init__(
        self,
        session: AsyncSession,
        auth_service: AuthorizationService | None = None,
    ) -> None:
        super().__init__(session, auth_service=auth_service)
        self._schema_svc = SchemaActionService(session, auth_service=auth_service)
        self._sql_svc = SqlActionService(session, auth_service=auth_service)
        self._impact_svc = ImpactActionService(session, auth_service=auth_service)
        self._quality_svc = QualityActionService(session, auth_service=auth_service)
        self._report_svc = MetadataReportService(session, auth_service=auth_service)

    async def build_lineage_data(
        self, urn: str, name: str, url: str | None
    ) -> LineageData | None:
        return await self._impact_svc.build_lineage_data(urn, name, url)

    async def compare_schema(
        self,
        columns: Sequence[SchemaColumn],
        preferred_query: str = "",
        limit: int = 5,
        user: UserContext | None = None,
    ) -> SchemaCompareResponse:
        return await self._schema_svc.compare_schema(
            columns, preferred_query=preferred_query, limit=limit, user=user
        )

    async def discover_sql_candidates(
        self,
        question: str,
        user: UserContext | None = None,
        limit: int = 5,
    ) -> list[SqlCandidate]:
        return await self._sql_svc.discover_sql_candidates(
            question, user=user, limit=limit
        )

    async def generate_sql(
        self,
        dataset_query: str,
        requested_columns: Sequence[str] = (),
        user: UserContext | None = None,
        question: str = "",
    ) -> SqlResponse:
        return await self._sql_svc.generate_sql(
            dataset_query,
            requested_columns=requested_columns,
            user=user,
            question=question,
        )

    async def impact_analysis(
        self,
        dataset_query: str,
        user: UserContext | None = None,
    ) -> ImpactResponse:
        return await self._impact_svc.impact_analysis(dataset_query, user=user)

    async def quality_check(
        self,
        dataset_query: str,
        user: UserContext | None = None,
        entity_type: str | None = None,
    ) -> QualityReport:
        return await self._quality_svc.quality_check(
            dataset_query, user=user, entity_type=entity_type
        )

    async def metadata_report(
        self,
        dataset_query: str,
        user: UserContext | None = None,
    ) -> ReportResponse:
        return await self._report_svc.metadata_report(dataset_query, user=user)


__all__ = [
    "ActionService",
    "PermissionDeniedError",
    "SqlCandidate",
    "SCHEMA_MATCH_MIN_SIMILARITY",
    "_norm",
    "_schema_columns",
    "_owner_names",
    "_profiling_stats",
    "_urn_kind",
    "extract_filter_fields",
    "extract_filter_values",
]
