from dataclasses import dataclass, field
from enum import StrEnum

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from database.models import Entity
from database.repositories.entity_repository import EntityRepository
from retrieval.fuzzy import fuzzy_score, tokenize

log = structlog.get_logger()


class ResolutionState(StrEnum):
    """Confidence state of an entity resolution.

    The resolver never guesses: it either resolves to a concrete catalog
    entity confidently, flags a genuinely ambiguous tie, reports a low-
    confidence (suggestion-worthy) hit, or states that nothing matched.
    """
    RESOLVED = "resolved"
    NEED_CLARIFICATION = "need_clarification"
    LOW_CONFIDENCE = "low_confidence"
    NOT_FOUND = "not_found"


@dataclass
class Candidate:
    urn: str
    name: str
    entity_type: str
    score: float = 0.0
    datahub_url: str | None = None
    reason: str = ""
    domain: str | None = None
    platform: str | None = None


@dataclass
class ResolutionResult:
    candidates: list[Candidate] = field(default_factory=list)
    ambiguous: bool = False
    exact_match: bool = False
    resolved: Candidate | None = None
    state: ResolutionState = ResolutionState.NOT_FOUND
    confidence: float = 0.0
    source: str = ""


@dataclass
class QueryScope:
    """Constraints extracted from the question that scope entity resolution.

    ``entity_type`` (e.g. "dataset" for a dataset ask), ``domain`` (e.g.
    "SẢN XUẤT" for "term X trong domain SẢN XUẤT") and ``platform`` narrow the
    candidate space so a name that exists in several domains/platforms resolves
    to the one the user actually means instead of a cross-domain tie.
    """
    entity_type: str | None = None
    domain: str | None = None
    platform: str | None = None


class EntityResolver:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = EntityRepository(session)

    async def resolve(self, name: str, entity_type: str | None = None,
                      scope: QueryScope | None = None,
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
                domain=exact_by_urn.domain or (exact_by_urn.payload or {}).get("domain"),
                platform=exact_by_urn.platform or (exact_by_urn.payload or {}).get("platform"),
            )
            result.candidates = [c]
            result.exact_match = True
            result.resolved = c
            result.state = ResolutionState.RESOLVED
            result.confidence = 1.0
            result.source = "exact_urn"
            log.info("resolver_result", trace_id=trace_id, query=name, source="exact_urn",
                     resolved=exact_by_urn.name, urn=exact_by_urn.urn, candidates=1,
                     ambiguous=False, exact=True)
            return result

        entities = await self._repo.search_by_name(name, entity_type)
        log.info("resolver_name_query", trace_id=trace_id, query=name,
                 db_rows=len(entities))
        for e in entities:
            score = self._score(name, e.name, e.urn)
            result.candidates.append(Candidate(
                urn=e.urn,
                name=e.name,
                entity_type=e.entity_type,
                score=score,
                datahub_url=e.datahub_url,
                reason=f"name match (score={score:.2f})",
                domain=e.domain or (e.payload or {}).get("domain"),
                platform=e.platform or (e.payload or {}).get("platform"),
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
                result.state = ResolutionState.NOT_FOUND
                result.confidence = 0.0
                result.source = "fuzzy"
                log.info("resolver_result", trace_id=trace_id, query=name,
                         source="fuzzy", candidates=0, resolved=None,
                         ambiguous=False)
                return result

        if not result.candidates:
            result.state = ResolutionState.NOT_FOUND
            result.confidence = 0.0
            result.source = "name_match"
            log.info("resolver_result", trace_id=trace_id, query=name,
                     source="name_match", candidates=0, resolved=None, ambiguous=False)
            return result

        if scope is not None:
            self._apply_scope(result.candidates, scope)
            log.info("resolver_scope_applied", trace_id=trace_id, query=name,
                     scope_type=scope.entity_type, scope_domain=scope.domain,
                     scope_platform=scope.platform)

        result.candidates.sort(key=lambda c: c.score, reverse=True)
        top = result.candidates[0]
        result.confidence = top.score

        if top.score >= settings.ENTITY_RESOLVER_HIGH_THRESHOLD:
            result.exact_match = True
            result.resolved = top
            result.state = ResolutionState.RESOLVED
            result.source = "exact_name"
        elif (
            len(result.candidates) > 1
            and abs(result.candidates[0].score
                    - result.candidates[1].score) < settings.ENTITY_RESOLVER_AMBIGUITY_MARGIN
            and result.candidates[1].score >= settings.ENTITY_RESOLVER_SUBSTRING_THRESHOLD
            # RC1a fix: a runner-up of a DIFFERENT entity type is not a real
            # ambiguity — the user named a concrete entity and the top candidate
            # of the matching type wins. Only same-type ties ask for a
            # clarification ("Coverage Date" -> two glossary terms; a report vs
            # a dashboard sharing a name is NOT a tie to clarify).
            and result.candidates[1].entity_type == top.entity_type
        ):
            result.ambiguous = True
            result.state = ResolutionState.NEED_CLARIFICATION
            result.source = "same_type_tie"
            log.warning("entity_ambiguous", trace_id=trace_id, query=name,
                         top=result.candidates[0].name,
                         runner_up=result.candidates[1].name,
                         top_score=result.candidates[0].score,
                         runner_up_score=result.candidates[1].score)
        elif top.score >= settings.ENTITY_RESOLVER_SUBSTRING_THRESHOLD:
            result.resolved = top
            result.state = ResolutionState.RESOLVED
            result.source = "name_match"
        else:
            result.state = ResolutionState.LOW_CONFIDENCE
            result.source = "low_confidence"

        log.info("resolver_result", trace_id=trace_id, query=name, source="name_match",
                 candidates=len(result.candidates),
                 resolved=result.resolved.name if result.resolved else None,
                 urn=result.resolved.urn if result.resolved else None,
                 top_score=top.score, ambiguous=result.ambiguous,
                 exact=result.exact_match, state=result.state.value)
        return result

    def _apply_scope(self, candidates: list[Candidate], scope: QueryScope) -> None:
        """Re-rank candidates by scope constraints, breaking ties only.

        A name that exists in several domains/platforms resolves to the one the
        question scopes to. The scope is a tie-breaker, never a hard filter:
        candidates that match the scoped domain/platform get a small boost over
        the rest, but only when a genuine scope match exists. If no candidate
        carries the scoped metadata (many glossary terms have no domain), the
        candidate set is left untouched so a clean exact match still resolves
        instead of being demoted by missing metadata (abstention > fabrication).
        """
        from retrieval.intent import _norm_vn

        boost = settings.ENTITY_RESOLVER_AMBIGUITY_MARGIN / 2
        if scope.domain:
            dn = _norm_vn(scope.domain)
            matched = [
                c for c in candidates
                if _norm_vn(c.domain or "") and dn in _norm_vn(c.domain)
            ]
            if matched:
                for c in candidates:
                    if c in matched:
                        c.score = min(1.0, c.score + boost)
                    else:
                        c.score = min(c.score, settings.ENTITY_RESOLVER_SUBSTRING_THRESHOLD - 0.01)
                        c.reason = f"{c.reason}; domain-scope demote"
        if scope.platform:
            pn = _norm_vn(scope.platform)
            matched = [
                c for c in candidates
                if _norm_vn(c.platform or "") and pn in _norm_vn(c.platform)
            ]
            if matched:
                for c in candidates:
                    if c in matched:
                        c.score = min(1.0, c.score + boost)
                    else:
                        c.score = min(c.score, settings.ENTITY_RESOLVER_SUBSTRING_THRESHOLD - 0.01)
                        c.reason = f"{c.reason}; platform-scope demote"

    def _score(self, query: str, name: str, urn: str = "") -> float:
        ql = query.lower().strip()
        nl = name.lower().strip()
        ul = (urn or "").lower()
        if ql == nl:
            return settings.ENTITY_RESOLVER_EXACT_THRESHOLD
        if nl.endswith("." + ql) or nl.startswith(ql + " ") or nl.endswith(" " + ql):
            return settings.ENTITY_RESOLVER_HIGH_THRESHOLD
        if ql in nl:
            return settings.ENTITY_RESOLVER_SUBSTRING_THRESHOLD
        # Users often refer to a dataset by its full dotted path / platform
        # container ("VF_VN_DEX_PLANNING.v_ec1v_2025") while the catalog stores
        # only the short name ("v_ec1v_2025"). Match the identifier tail against
        # the URN path so the dotted reference resolves instead of falling to a
        # low fuzzy score. The final dotted segment is the table name; prefer a
        # name that equals that segment over variants with suffixes.
        if ql and "." in ql:
            last_seg = ql.rsplit(".", 1)[-1]
            if last_seg and nl == last_seg:
                return settings.ENTITY_RESOLVER_HIGH_THRESHOLD
            if last_seg and nl.startswith(last_seg):
                return settings.ENTITY_RESOLVER_SUBSTRING_THRESHOLD
        if ql and ul and ql in ul:
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
                domain=e.domain or (e.payload or {}).get("domain"),
                platform=e.platform or (e.payload or {}).get("platform"),
            )
            for score, e in scored[:max_cands]
        ]
