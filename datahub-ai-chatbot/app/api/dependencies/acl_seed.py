import unicodedata

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.authorization import AuthorizationService
from app.auth.models import EntityAcl
from database.models import Entity
from database.repositories.entity_repository import EntityRepository
from database.repositories.rbac_repository import RbacRepository

log = structlog.get_logger()

_DOMAIN_ACL_RULES = [
    {
        "domains": ["Finance", "TÀI CHÍNH"],
        "allowed_groups": ["finance-team", "admin-group"],
    },
    {
        "domains": ["Logistics", "LOGISTIC", "Supply Chain", "CUNG ỨNG (NĐH)", "CUNG ỨNG (TT)"],
        "allowed_groups": ["logistics-team", "admin-group"],
    },
    {
        "domains": ["Sản Xuất", "Manufacturing"],
        "allowed_groups": ["manufacturing-team", "admin-group"],
    },
    {
        "domains": ["VGreen", "Vehicle Development"],
        "allowed_groups": ["engineering-team", "admin-group"],
    },
]

_PUBLIC_DOMAINS = ["Sales", "After Sales", "Data Governance"]

# Roles are data-driven: every rule maps to an RBAC role with the same granted
# domains and the group fallback used by legacy identity providers.
_RBAC_ROLE_RULES: list[dict[str, object]] = [
    {
        "role": "Tài chính",
        "domains": ["Finance", "TÀI CHÍNH"],
        "group_names": ["finance-team"],
    },
    {
        "role": "Logistics",
        "domains": [
            "Logistics", "LOGISTIC", "Supply Chain",
            "CUNG ỨNG (NĐH)", "CUNG ỨNG (TT)",
        ],
        "group_names": ["logistics-team"],
    },
    {
        "role": "Sản Xuất",
        "domains": ["Sản Xuất", "Manufacturing"],
        "group_names": ["manufacturing-team"],
    },
    {
        "role": "VGreen",
        "domains": ["VGreen", "Vehicle Development"],
        "group_names": ["engineering-team"],
    },
    {
        "role": "Sales",
        "domains": ["Sales", "After Sales", "Data Governance"],
        "group_names": ["sales-team"],
    },
]


def _norm_vn(s: str | None) -> str:
    if not s:
        return ""
    s = s.lower()
    s = s.replace("đ", "d").replace("Đ", "d")
    s = unicodedata.normalize("NFKD", s)
    return s.encode("ascii", "ignore").decode("ascii")


async def seed_acls(session: AsyncSession) -> None:
    auth_service = AuthorizationService(session=session)
    repo = EntityRepository(session)

    all_entities: list[Entity] = []
    for etype in ["dataset", "dashboard", "glossary_term", "document", "glossary_node"]:
        all_entities.extend(await repo.list_by_type(etype, limit=100000))

    public_domains = {_norm_vn(d) for d in _PUBLIC_DOMAINS}

    total = 0
    for rule in _DOMAIN_ACL_RULES:
        rule_domains = {_norm_vn(d) for d in rule["domains"]}
        for entity in all_entities:
            entity_domain = _norm_vn(entity.domain)
            if entity_domain in rule_domains:
                acl = EntityAcl(
                    entity_urn=entity.urn,
                    is_public=False,
                    allowed_groups=rule["allowed_groups"],
                )
                await auth_service.set_acl_db(acl)
                total += 1

    for entity in all_entities:
        if _norm_vn(entity.domain) in public_domains:
            acl = EntityAcl(entity_urn=entity.urn, is_public=True)
            await auth_service.set_acl_db(acl)
            total += 1

    log.info("acl_seeding_complete", total=total)


async def seed_rbac_roles(session: AsyncSession) -> None:
    """Bootstrap the data-driven roles from the static rule table.

    Idempotent: roles are matched by name; an existing role is only updated when
    its grant/group set drifted from the seed definition. Call this on startup
    so the permission model works even before any admin touches the module.
    """
    repo = RbacRepository(session)
    for rule in _RBAC_ROLE_RULES:
        role_name = str(rule["role"])
        raw_domains = rule["domains"]
        raw_groups = rule["group_names"]
        domains = (
            [d for d in raw_domains if isinstance(d, str)]
            if isinstance(raw_domains, list)
            else []
        )
        group_names = (
            [g for g in raw_groups if isinstance(g, str)]
            if isinstance(raw_groups, list)
            else []
        )
        existing = await repo.get_role_by_name(role_name)
        if existing is None:
            role = await repo.create_role(
                name=role_name,
                description="Domain role seeded from authorization rules",
                group_names=group_names,
            )
            await repo.set_role_domains(role.id, domains)
            log.info("rbac_role_seeded", role=role_name, domains=domains)
            continue
        current = await repo.list_role_domains(existing.id)
        if sorted(set(current)) != sorted(set(domains)):
            await repo.set_role_domains(existing.id, domains)
            log.info("rbac_role_domains_updated", role=role_name)
    log.info("rbac_role_seeding_complete", roles=len(_RBAC_ROLE_RULES))
