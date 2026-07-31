from dataclasses import dataclass, field

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from database.repositories.entity_repository import EntityRepository

log = structlog.get_logger()


@dataclass
class Candidate:
    urn: str
    name: str
    entity_type: str
    score: float = 0.0
    datahub_url: str | None = None
    reason: str = ""


@dataclass
class ResolutionResult:
    candidates: list[Candidate] = field(default_factory=list)
    ambiguous: bool = False
    exact_match: bool = False
    resolved: Candidate | None = None


class EntityResolver:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = EntityRepository(session)

    async def resolve(self, name: str, entity_type: str | None = None) -> ResolutionResult:
        result = ResolutionResult()

        exact_by_urn = await self._repo.get_by_urn(name)
        if exact_by_urn:
            c = Candidate(
                urn=exact_by_urn.urn,
                name=exact_by_urn.name,
                entity_type=exact_by_urn.entity_type,
                score=1.0,
                datahub_url=exact_by_urn.datahub_url,
                reason="exact URN match",
            )
            result.candidates = [c]
            result.exact_match = True
            result.resolved = c
            return result

        entities = await self._repo.search_by_name(name, entity_type)
        for ent in entities:
            score = self._score(name, ent.name)
            result.candidates.append(Candidate(
                urn=ent.urn,
                name=ent.name,
                entity_type=ent.entity_type,
                score=score,
                datahub_url=ent.datahub_url,
                reason=f"name match (score={score:.2f})",
            ))

        if not result.candidates:
            return result

        result.candidates.sort(key=lambda c: c.score, reverse=True)
        top = result.candidates[0]

        if top.score >= settings.ENTITY_RESOLVER_HIGH_THRESHOLD:
            result.exact_match = True
            result.resolved = top
        elif (
            len(result.candidates) > 1
            and abs(result.candidates[0].score - result.candidates[1].score) < settings.ENTITY_RESOLVER_AMBIGUITY_MARGIN
            and result.candidates[1].score >= settings.ENTITY_RESOLVER_SUBSTRING_THRESHOLD
        ):
            result.ambiguous = True
            log.warning("entity_ambiguous", query=name,
                         top=result.candidates[0].name,
                         runner_up=result.candidates[1].name,
                         top_score=result.candidates[0].score,
                         runner_up_score=result.candidates[1].score)
        elif top.score >= settings.ENTITY_RESOLVER_SUBSTRING_THRESHOLD:
            result.resolved = top
        else:
            result.resolved = top

        return result

    def _score(self, query: str, name: str) -> float:
        ql = query.lower().strip()
        nl = name.lower().strip()
        if ql == nl:
            return settings.ENTITY_RESOLVER_EXACT_THRESHOLD
        if nl.endswith("." + ql) or nl.startswith(ql + " ") or nl.endswith(" " + ql):
            return settings.ENTITY_RESOLVER_HIGH_THRESHOLD
        if ql in nl:
            return settings.ENTITY_RESOLVER_SUBSTRING_THRESHOLD
        if any(w in nl for w in ql.split()):
            return 0.4
        return 0.1
