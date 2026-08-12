from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_auth_service, require_role
from app.auth.authorization import AuthorizationService
from app.auth.models import UserContext
from app.schemas.actions import (
    DatasetQuery,
    ImpactResponse,
    ReportResponse,
    SchemaCompareRequest,
    SchemaCompareResponse,
    SqlResponse,
)
from app.schemas.chat import LineageData
from app.schemas.quality import QualityReport
from app.services.action_service import ActionService
from app.services.quality_report import render_pdf_bytes, render_txt
from database.session import get_session

router = APIRouter()

_VIEWER_ROLES = ("admin", "editor", "steward", "viewer", "user")


def _service(session: AsyncSession, auth_service: AuthorizationService) -> ActionService:
    return ActionService(session, auth_service=auth_service)


@router.post("/schema-compare")
async def schema_compare(
    request: SchemaCompareRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserContext = Depends(require_role(*_VIEWER_ROLES)),
    auth_service: AuthorizationService = Depends(get_auth_service),
) -> SchemaCompareResponse:
    return await _service(session, auth_service).compare_schema(
        request.columns, preferred_query=request.preferred_query, user=current_user
    )


@router.post("/sql")
async def generate_sql(
    request: DatasetQuery,
    session: AsyncSession = Depends(get_session),
    current_user: UserContext = Depends(require_role(*_VIEWER_ROLES)),
    auth_service: AuthorizationService = Depends(get_auth_service),
) -> SqlResponse:
    return await _service(session, auth_service).generate_sql(
        request.dataset, requested_columns=request.columns, user=current_user
    )


@router.post("/impact")
async def impact_analysis(
    request: DatasetQuery,
    session: AsyncSession = Depends(get_session),
    current_user: UserContext = Depends(require_role(*_VIEWER_ROLES)),
    auth_service: AuthorizationService = Depends(get_auth_service),
) -> ImpactResponse:
    result = await _service(session, auth_service).impact_analysis(
        request.dataset, user=current_user,
    )
    if not result.valid:
        _msg = result.business_impact[0] if result.business_impact else "Không tìm thấy dataset."
        raise HTTPException(status_code=404, detail=_msg)
    return result


@router.post("/lineage")
async def lineage_graph(
    request: DatasetQuery,
    session: AsyncSession = Depends(get_session),
    current_user: UserContext = Depends(require_role(*_VIEWER_ROLES)),
    auth_service: AuthorizationService = Depends(get_auth_service),
) -> LineageData:
    service = _service(session, auth_service)
    entity = await service.resolve_dataset(request.dataset, user=current_user)
    if entity is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy dataset.")
    data = await service.build_lineage_data(
        entity.urn, entity.display_name or entity.name, entity.datahub_url,
    )
    if data is None:
        return LineageData(entity_name=entity.display_name or entity.name, entity_urn=entity.urn)
    return data


@router.post("/quality")
async def quality_check(
    request: DatasetQuery,
    session: AsyncSession = Depends(get_session),
    current_user: UserContext = Depends(require_role(*_VIEWER_ROLES)),
    auth_service: AuthorizationService = Depends(get_auth_service),
) -> QualityReport:
    result = await _service(session, auth_service).quality_check(
        request.dataset, user=current_user
    )
    if not result.valid:
        raise HTTPException(status_code=404, detail=result.dataset or "Không tìm thấy dataset.")
    return result


class QualityExportRequest(BaseModel):
    report: QualityReport
    format: str = "pdf"  # pdf | txt


@router.post("/quality/export")
async def quality_export(
    request: QualityExportRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserContext = Depends(require_role(*_VIEWER_ROLES)),
) -> StreamingResponse:
    """Export an already-generated Data Quality Report as PDF or TXT.

    The full report is supplied in the request body, so no regeneration is
    needed and the feature is reusable for any dataset.
    """
    report = request.report
    if report.generated_by in (None, "") and current_user is not None:
        report.generated_by = (
            current_user.display_name or current_user.user_id or "anonymous"
        )
    fmt = (request.format or "txt").lower()
    filename = f"data-quality-report-{report.dataset or 'dataset'}".replace("/", "-")
    if fmt == "pdf":
        body = render_pdf_bytes(report)
        media = "application/pdf"
        filename += ".pdf"
    else:
        body = render_txt(report).encode("utf-8")
        media = "text/plain"
        filename += ".txt"
    return StreamingResponse(
        iter([body]),
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/report")
async def metadata_report(
    request: DatasetQuery,
    session: AsyncSession = Depends(get_session),
    current_user: UserContext = Depends(require_role(*_VIEWER_ROLES)),
    auth_service: AuthorizationService = Depends(get_auth_service),
) -> ReportResponse:
    result = await _service(session, auth_service).metadata_report(
        request.dataset, user=current_user,
    )
    if not result.valid:
        _msg = result.recommendations[0] if result.recommendations else "Không tìm thấy dataset."
        raise HTTPException(status_code=404, detail=_msg)
    return result
