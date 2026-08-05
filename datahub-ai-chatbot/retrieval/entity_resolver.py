from dataclasses import dataclass, field

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from database.models import Entity
from database.repositories.entity_repository import EntityRepository
from retrieval.fuzzy import fuzzy_score, tokenize

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

    async def resolve(self, name: str, entity_type: str | None = None,
                      trace_id: str | None = None) -> ResolutionResult:
        result = ResolutionResult()
        log.info("resolver_start", trace_id=trace_id, query=name, entity_type=entity_type)

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
            log.info("resolver_result", trace_id=trace_id, query=name, source="exact_urn",
                     resolved=exact_by_urn.name, urn=exact_by_urn.urn, candidates=1,
                     ambiguous=False, exact=True)
            return result

        entities = await self._repo.search_by_name(name, entity_type)
        log.info("resolver_name_query", trace_id=trace_id, query=name,
                 db_rows=len(entities))
        for e in entities:
            score = self._score(name, e.name)
            result.candidates.append(Candidate(
                urn=e.urn,
                name=e.name,
                entity_type=e.entity_type,
                score=score,
                datahub_url=e.datahub_url,
                reason=f"name match (score={score:.2f})",
            ))

        # Fuzzy / phonetic fallback for typo'd or accent-free queries.
        scored_candidates = [c for c in result.candidates]
        strong = any(c.score >= settings.ENTITY_RESOLVER_SUBSTRING_THRESHOLD
                     for c in scored_candidates)
        if not scored_candidates or not strong:
            fuzzy_candidates = await self._fuzzy_candidates(name, entity_type)
            for fc in fuzzy_candidates:
                existing = next(
                    (c for c in result.candidates if c.urn == fc.urn), None
                )
                if existing:
                    if fc.score > existing.score:
                        existing.score = fc.score
                        existing.reason = fc.reason
                else:
                    result.candidates.append(fc)
            if not result.candidates:
                log.info("resolver_result", trace_id=trace_id, query=name,
                         source="fuzzy", candidates=0, resolved=None,
                         ambiguous=False)
                return result

        if not result.candidates:
            log.info("resolver_result", trace_id=trace_id, query=name,
                     source="name_match", candidates=0, resolved=None, ambiguous=False)
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
            log.warning("entity_ambiguous", trace_id=trace_id, query=name,
                         top=result.candidates[0].name,
                         runner_up=result.candidates[1].name,
                         top_score=result.candidates[0].score,
                         runner_up_score=result.candidates[1].score)
        elif top.score >= settings.ENTITY_RESOLVER_SUBSTRING_THRESHOLD:
            result.resolved = top
        else:
            result.resolved = top

        log.info("resolver_result", trace_id=trace_id, query=name, source="name_match",
                 candidates=len(result.candidates),
                 resolved=result.resolved.name if result.resolved else None,
                 urn=result.resolved.urn if result.resolved else None,
                 top_score=top.score, ambiguous=result.ambiguous,
                 exact=result.exact_match)
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

    async def _fuzzy_candidates(
        self, name: str, entity_type: str | None = None
    ) -> list[Candidate]:
        entities = await self._repo.list_all(
            entity_type=entity_type, limit=2000
        )
        scored: list[tuple[float, Entity]] = []
        for e in entities:
            if getattr(e, "deleted", False):
                continue
            cand_names = {e.name, e.display_name or ""}
            cand_names.discard("")
            name_tokens = tokenize(e.name or e.display_name or "")
            best_score = 0.0
            for cand in cand_names:
                sc = fuzzy_score(name, cand, name_tokens=name_tokens)
                if sc > best_score:
                    best_score = sc
            if best_score >= settings.ENTITY_RESOLVER_FUZZY_MIN_THRESHOLD:
                scored.append((best_score, e))

        scored.sort(
            key=lambda t: (
                -t[0],
                bool(getattr(t[1], "deleted", False)),
                t[1].environment != "PROD",
            )
        )
        max_cands = settings.ENTITY_RESOLVER_FUZZY_MAX_CANDIDATES
        return [
            Candidate(
                urn=e.urn,
                name=e.name,
                entity_type=e.entity_type,
                score=score,
                datahub_url=e.datahub_url,
                reason=f"fuzzy/phonetic match (score={score:.2f})",
            )
            for score, e in scored[:max_cands]
        ]
