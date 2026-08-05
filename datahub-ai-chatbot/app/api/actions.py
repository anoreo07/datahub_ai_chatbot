from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_auth_service, require_role
from app.auth.authorization import AuthorizationService
from app.auth.models import UserContext
from app.schemas.actions import (
    DatasetQuery,
    ImpactResponse,
    QualityResponse,
    ReportResponse,
    SchemaCompareRequest,
    SchemaCompareResponse,
    SqlResponse,
)
from app.schemas.chat import LineageData
from app.services.action_service import ActionService
from database.session import get_session

router = APIRouter()


def _service(session: AsyncSession, auth_service: AuthorizationService) -> ActionService:
    return ActionService(session, auth_service=auth_service)


@router.post("/schema-compare")
async def schema_compare(
    request: SchemaCompareRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserContext = Depends(require_role("admin", "editor", "steward", "viewer", "user")),
    auth_service: AuthorizationService = Depends(get_auth_service),
) -> SchemaCompareResponse:
    return await _service(session, auth_service).compare_schema(
        request.columns, preferred_query=request.preferred_query, user=current_user
    )


@router.post("/sql")
async def generate_sql(
    request: DatasetQuery,
    session: AsyncSession = Depends(get_session),
    current_user: UserContext = Depends(require_role("admin", "editor", "steward", "viewer", "user")),
    auth_service: AuthorizationService = Depends(get_auth_service),
) -> SqlResponse:
    return await _service(session, auth_service).generate_sql(
        request.dataset, requested_columns=request.columns, user=current_user
    )


@router.post("/impact")
async def impact_analysis(
    request: DatasetQuery,
    session: AsyncSession = Depends(get_session),
    current_user: UserContext = Depends(require_role("admin", "editor", "steward", "viewer", "user")),
    auth_service: AuthorizationService = Depends(get_auth_service),
) -> ImpactResponse:
    result = await _service(session, auth_service).impact_analysis(request.dataset, user=current_user)
    if not result.valid:
        raise HTTPException(status_code=404, detail=result.business_impact[0] if result.business_impact else "Không tìm thấy dataset.")
    return result


@router.post("/lineage")
async def lineage_graph(
    request: DatasetQuery,
    session: AsyncSession = Depends(get_session),
    current_user: UserContext = Depends(require_role("admin", "editor", "steward", "viewer", "user")),
    auth_service: AuthorizationService = Depends(get_auth_service),
) -> LineageData:
    service = _service(session, auth_service)
    entity = await service.resolve_dataset(request.dataset, user=current_user)
    if entity is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy dataset.")
    data = await service.build_lineage_data(entity.urn, entity.display_name or entity.name, entity.datahub_url)
    if data is None:
        return LineageData(entity_name=entity.display_name or entity.name, entity_urn=entity.urn)
    return data


@router.post("/quality")
async def quality_check(
    request: DatasetQuery,
    session: AsyncSession = Depends(get_session),
    current_user: UserContext = Depends(require_role("admin", "editor", "steward", "viewer", "user")),
    auth_service: AuthorizationService = Depends(get_auth_service),
) -> QualityResponse:
    result = await _service(session, auth_service).quality_check(request.dataset, user=current_user)
    if not result.valid:
        raise HTTPException(status_code=404, detail=result.recommendations[0] if result.recommendations else "Không tìm thấy dataset.")
    return result


@router.post("/report")
async def metadata_report(
    request: DatasetQuery,
    session: AsyncSession = Depends(get_session),
    current_user: UserContext = Depends(require_role("admin", "editor", "steward", "viewer", "user")),
    auth_service: AuthorizationService = Depends(get_auth_service),
) -> ReportResponse:
    result = await _service(session, auth_service).metadata_report(request.dataset, user=current_user)
    if not result.valid:
        raise HTTPException(status_code=404, detail=result.recommendations[0] if result.recommendations else "Không tìm thấy dataset.")
    return result