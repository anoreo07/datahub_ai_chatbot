"""Admin API for the data-driven role management module.

Role definitions, their granted domains, and user↔role assignments are stored
in the database (rbac_roles / rbac_role_domains / rbac_users /
rbac_user_roles). Every mutation refreshes the permission snapshot so the new
grant/revoke takes effect immediately without an application restart.
"""
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_admin_user, get_auth_service
from app.auth.authorization import AuthorizationService
from app.auth.models import UserContext
from database.models import Entity
from database.repositories.rbac_repository import RbacRepository
from database.session import get_session

log = structlog.get_logger()

router = APIRouter()


class RoleCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str | None = None
    is_admin: bool = False
    group_names: list[str] = []
    domains: list[str] = []


class RoleUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = None
    is_admin: bool | None = None
    group_names: list[str] | None = None


class RoleDomainsRequest(BaseModel):
    domains: list[str]


class UserRolesRequest(BaseModel):
    role_ids: list[int]


class RoleResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    is_admin: bool
    group_names: list[str]
    domains: list[str]
    user_count: int


class UserRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=128)
    username: str = Field(min_length=1, max_length=128)
    email: str = ""
    display_name: str = ""
    is_active: bool = True
    is_admin: bool = False
    role_ids: list[int] = []


class UserResponse(BaseModel):
    id: int
    user_id: str
    username: str
    email: str
    display_name: str
    is_active: bool
    is_admin: bool
    role_ids: list[int]


SessionDep = Annotated[AsyncSession, Depends(get_session)]
AdminDep = Annotated[UserContext, Depends(get_admin_user)]


async def _repo(session: AsyncSession) -> RbacRepository:
    return RbacRepository(session)


# ----------------------------------------------------------------------
# Roles
# ----------------------------------------------------------------------

@router.get("/domains", response_model=list[str])
async def list_domains(
    _: AdminDep,
    session: SessionDep,
) -> list[str]:
    """Distinct domains available for role grants: domains already granted to a
    role plus domains present on catalog entities (data-driven, so new domains
    synced from DataHub appear here automatically)."""
    repo = await _repo(session)
    domains: set[str] = set()
    for role in await repo.list_roles():
        domains.update(await repo.list_role_domains(role.id))
    try:
        result = await session.execute(select(Entity.domain).where(Entity.domain.isnot(None)))
        for (d,) in result.all():
            if d and d.strip():
                domains.add(d.strip())
        payloads = await session.execute(select(Entity.payload))
        for (payload,) in payloads.all():
            if isinstance(payload, dict):
                d = (payload.get("domain") or "").strip()
                if d:
                    domains.add(d)
    except Exception:  # noqa: BLE001
        log.warning("admin_domains_entity_scan_failed")
    return sorted(domains, key=str.lower)


@router.get("/roles", response_model=list[RoleResponse])
async def list_roles(
    _: AdminDep,
    session: SessionDep,
) -> list[RoleResponse]:
    repo = await _repo(session)
    roles = await repo.list_roles()
    result: list[RoleResponse] = []
    for role in roles:
        domains = await repo.list_role_domains(role.id)
        user_count = await repo.count_role_users(role.id)
        result.append(RoleResponse(
            id=role.id, name=role.name, description=role.description,
            is_admin=bool(role.is_admin), group_names=list(role.group_names or []),
            domains=domains, user_count=user_count,
        ))
    return result


@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    req: RoleCreateRequest,
    _: AdminDep,
    session: SessionDep,
    auth_service: AuthorizationService = Depends(get_auth_service),
) -> RoleResponse:
    repo = await _repo(session)
    if await repo.get_role_by_name(req.name):
        raise HTTPException(status.HTTP_409_CONFLICT, detail=f"Role '{req.name}' already exists")
    role = await repo.create_role(
        name=req.name, description=req.description,
        is_admin=req.is_admin, group_names=req.group_names,
    )
    if req.domains:
        await repo.set_role_domains(role.id, req.domains)
    await auth_service.refresh_permissions()
    domains = await repo.list_role_domains(role.id)
    return RoleResponse(
        id=role.id, name=role.name, description=role.description,
        is_admin=bool(role.is_admin), group_names=list(role.group_names or []),
        domains=domains, user_count=0,
    )


@router.get("/roles/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: int,
    _: AdminDep,
    session: SessionDep,
) -> RoleResponse:
    repo = await _repo(session)
    role = await repo.get_role(role_id)
    if role is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Role not found")
    domains = await repo.list_role_domains(role.id)
    user_count = await repo.count_role_users(role.id)
    return RoleResponse(
        id=role.id, name=role.name, description=role.description,
        is_admin=bool(role.is_admin), group_names=list(role.group_names or []),
        domains=domains, user_count=user_count,
    )


@router.put("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: int,
    req: RoleUpdateRequest,
    _: AdminDep,
    session: SessionDep,
    auth_service: AuthorizationService = Depends(get_auth_service),
) -> RoleResponse:
    repo = await _repo(session)
    role = await repo.get_role(role_id)
    if role is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Role not found")
    updated = await repo.update_role(
        role_id=role_id,
        description=req.description,
        is_admin=req.is_admin,
        group_names=req.group_names,
    )
    if updated is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Role not found")
    if req.name and req.name != role.name:
        repo_session_updated = await repo.get_role(role_id)
        if repo_session_updated is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Role not found")
        repo_session_updated.name = req.name
        await session.commit()
        await session.refresh(repo_session_updated)
        updated = repo_session_updated
    await auth_service.refresh_permissions()
    domains = await repo.list_role_domains(role.id)
    user_count = await repo.count_role_users(role.id)
    return RoleResponse(
        id=updated.id, name=updated.name, description=updated.description,
        is_admin=bool(updated.is_admin), group_names=list(updated.group_names or []),
        domains=domains, user_count=user_count,
    )


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: int,
    _: AdminDep,
    session: SessionDep,
    auth_service: AuthorizationService = Depends(get_auth_service),
) -> None:
    repo = await _repo(session)
    role = await repo.get_role(role_id)
    if role is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Role not found")
    await repo.delete_role(role_id)
    await auth_service.refresh_permissions()
    log.info("rbac_role_deleted", role_id=role_id, actor=None)


# ----------------------------------------------------------------------
# Role domains
# ----------------------------------------------------------------------

@router.put("/roles/{role_id}/domains", response_model=RoleResponse)
async def set_role_domains(
    role_id: int,
    req: RoleDomainsRequest,
    _: AdminDep,
    session: SessionDep,
    auth_service: AuthorizationService = Depends(get_auth_service),
) -> RoleResponse:
    repo = await _repo(session)
    role = await repo.get_role(role_id)
    if role is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Role not found")
    await repo.set_role_domains(role_id, req.domains)
    await auth_service.refresh_permissions()
    domains = await repo.list_role_domains(role_id)
    user_count = await repo.count_role_users(role_id)
    return RoleResponse(
        id=role.id, name=role.name, description=role.description,
        is_admin=bool(role.is_admin), group_names=list(role.group_names or []),
        domains=domains, user_count=user_count,
    )


# ----------------------------------------------------------------------
# Users
# ----------------------------------------------------------------------

@router.get("/users", response_model=list[UserResponse])
async def list_users(
    _: AdminDep,
    session: SessionDep,
) -> list[UserResponse]:
    repo = await _repo(session)
    users = await repo.list_users()
    result: list[UserResponse] = []
    for u in users:
        role_ids = await repo.list_user_role_ids(u.user_id)
        result.append(UserResponse(
            id=u.id, user_id=u.user_id, username=u.username, email=u.email,
            display_name=u.display_name, is_active=bool(u.is_active),
            is_admin=bool(u.is_admin), role_ids=role_ids,
        ))
    return result


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    req: UserRequest,
    _: AdminDep,
    session: SessionDep,
    auth_service: AuthorizationService = Depends(get_auth_service),
) -> UserResponse:
    repo = await _repo(session)
    if await repo.get_user(req.user_id):
        raise HTTPException(status.HTTP_409_CONFLICT, detail=f"User '{req.user_id}' already exists")
    user = await repo.upsert_user(
        user_id=req.user_id, username=req.username, email=req.email,
        display_name=req.display_name, is_active=req.is_active,
        is_admin=req.is_admin,
    )
    if req.role_ids:
        await repo.set_user_roles(req.user_id, req.role_ids)
    await auth_service.refresh_permissions()
    role_ids = await repo.list_user_role_ids(req.user_id)
    return UserResponse(
        id=user.id, user_id=user.user_id, username=user.username, email=user.email,
        display_name=user.display_name, is_active=bool(user.is_active),
        is_admin=bool(user.is_admin), role_ids=role_ids,
    )


@router.put("/users/{user_id}/roles", response_model=UserResponse)
async def set_user_roles(
    user_id: str,
    req: UserRolesRequest,
    _: AdminDep,
    session: SessionDep,
    auth_service: AuthorizationService = Depends(get_auth_service),
) -> UserResponse:
    repo = await _repo(session)
    user = await repo.get_user(user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")
    await repo.set_user_roles(user_id, req.role_ids)
    await auth_service.refresh_permissions()
    assigned = await repo.list_user_role_ids(user_id)
    return UserResponse(
        id=user.id, user_id=user.user_id, username=user.username, email=user.email,
        display_name=user.display_name, is_active=bool(user.is_active),
        is_admin=bool(user.is_admin), role_ids=assigned,
    )


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    _: AdminDep,
    session: SessionDep,
    auth_service: AuthorizationService = Depends(get_auth_service),
) -> None:
    repo = await _repo(session)
    if await repo.get_user(user_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")
    await repo.delete_user(user_id)
    await auth_service.refresh_permissions()
