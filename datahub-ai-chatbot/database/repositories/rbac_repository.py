from collections.abc import Sequence

from sqlalchemy import delete as sa_delete
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import RbacRoleDB, RbacRoleDomainDB, RbacUserRole, UserAccount


class RbacRepository:
    """Persistence layer for the data-driven RBAC model.

    Roles, role-domain grants and user-role assignments live in the database so
    permission evaluation is fully data-driven and new roles can be added by
    administrators without code changes.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # --- roles -----------------------------------------------------------

    async def list_roles(self) -> Sequence[RbacRoleDB]:
        stmt = select(RbacRoleDB).order_by(RbacRoleDB.name)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_role(self, role_id: int) -> RbacRoleDB | None:
        stmt = select(RbacRoleDB).where(RbacRoleDB.id == role_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_role_by_name(self, name: str) -> RbacRoleDB | None:
        stmt = select(RbacRoleDB).where(RbacRoleDB.name == name)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_role(
        self,
        name: str,
        description: str | None = None,
        is_admin: bool = False,
        group_names: list[str] | None = None,
    ) -> RbacRoleDB:
        role = RbacRoleDB(
            name=name,
            description=description,
            is_admin=is_admin,
            group_names=group_names or [],
        )
        self._session.add(role)
        await self._session.commit()
        await self._session.refresh(role)
        return role

    async def update_role(
        self,
        role_id: int,
        description: str | None = None,
        is_admin: bool | None = None,
        group_names: list[str] | None = None,
    ) -> RbacRoleDB | None:
        role = await self.get_role(role_id)
        if not role:
            return None
        if description is not None:
            role.description = description
        if is_admin is not None:
            role.is_admin = is_admin
        if group_names is not None:
            role.group_names = group_names
        await self._session.commit()
        await self._session.refresh(role)
        return role

    async def delete_role(self, role_id: int) -> bool:
        # Domains and user-role rows cascade on delete (FK ondelete=CASCADE).
        stmt = sa_delete(RbacRoleDB).where(RbacRoleDB.id == role_id)
        await self._session.execute(stmt)
        await self._session.commit()
        existing = await self.get_role(role_id)
        return existing is None

    # --- role domains ----------------------------------------------------

    async def list_role_domains(self, role_id: int) -> list[str]:
        stmt = select(RbacRoleDomainDB.domain).where(
            RbacRoleDomainDB.role_id == role_id
        ).order_by(RbacRoleDomainDB.domain)
        result = await self._session.execute(stmt)
        return [row[0] for row in result.all()]

    async def set_role_domains(self, role_id: int, domains: list[str]) -> None:
        await self._session.execute(
            sa_delete(RbacRoleDomainDB).where(RbacRoleDomainDB.role_id == role_id)
        )
        seen: set[str] = set()
        for d in domains:
            normalized = (d or "").strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            self._session.add(RbacRoleDomainDB(role_id=role_id, domain=normalized))
        await self._session.commit()

    # --- users -----------------------------------------------------------

    async def list_users(self) -> Sequence[UserAccount]:
        stmt = select(UserAccount).order_by(UserAccount.username)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_user(self, user_id: str) -> UserAccount | None:
        stmt = select(UserAccount).where(UserAccount.user_id == user_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_by_username(self, username: str) -> UserAccount | None:
        stmt = select(UserAccount).where(UserAccount.username == username)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_user(
        self,
        user_id: str,
        username: str,
        email: str = "",
        display_name: str = "",
        is_active: bool = True,
        is_admin: bool = False,
        password_hash: str | None = None,
    ) -> UserAccount:
        user = await self.get_user(user_id)
        if user:
            user.username = username
            user.email = email
            user.display_name = display_name
            user.is_active = is_active
            user.is_admin = is_admin
            if password_hash is not None:
                user.password_hash = password_hash
        else:
            user = UserAccount(
                user_id=user_id,
                username=username,
                email=email,
                display_name=display_name,
                is_active=is_active,
                is_admin=is_admin,
                password_hash=password_hash,
            )
            self._session.add(user)
        await self._session.commit()
        await self._session.refresh(user)
        return user

    async def set_user_admin(self, user_id: str, is_admin: bool) -> UserAccount | None:
        user = await self.get_user(user_id)
        if not user:
            return None
        user.is_admin = is_admin
        await self._session.commit()
        await self._session.refresh(user)
        return user

    async def delete_user(self, user_id: str) -> bool:
        await self._session.execute(
            sa_delete(RbacUserRole).where(RbacUserRole.user_id == user_id)
        )
        stmt = sa_delete(UserAccount).where(UserAccount.user_id == user_id)
        await self._session.execute(stmt)
        await self._session.commit()
        existing = await self.get_user(user_id)
        return existing is None

    # --- user roles ------------------------------------------------------

    async def list_user_role_ids(self, user_id: str) -> list[int]:
        stmt = select(RbacUserRole.role_id).where(RbacUserRole.user_id == user_id)
        result = await self._session.execute(stmt)
        return [row[0] for row in result.all()]

    async def set_user_roles(self, user_id: str, role_ids: list[int]) -> None:
        await self._session.execute(
            sa_delete(RbacUserRole).where(RbacUserRole.user_id == user_id)
        )
        for rid in dict.fromkeys(role_ids):
            self._session.add(RbacUserRole(user_id=user_id, role_id=rid))
        await self._session.commit()

    async def count_role_users(self, role_id: int) -> int:
        stmt = select(func.count(RbacUserRole.id)).where(
            RbacUserRole.role_id == role_id
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()
