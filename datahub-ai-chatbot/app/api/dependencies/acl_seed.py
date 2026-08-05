import unicodedata

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.authorization import AuthorizationService
from app.auth.models import EntityAcl
from database.models import Entity
from database.repositories.entity_repository import EntityRepository

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
