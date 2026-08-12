"""Executor: runs each plan step against the real metadata catalog.

Each step maps to one or more retrieval calls over the existing repository /
graph / entity resolver. Independent steps run sequentially here (cheap,
grounded); results are de-duplicated by (urn, source). A step with no
retrievable data is marked ``insufficient`` so the synthesizer can report
the gap honestly instead of guessing.
"""

from __future__ import annotations

import re
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from database.models import Entity
from database.repositories.entity_repository import EntityRepository
from retrieval.entity_resolver import EntityResolver
from retrieval.graph import MetadataGraph
from retrieval.thinking.models import (
    EvidenceRecord,
    ExecutionPlan,
    KnowledgeSource,
    PlanStep,
)

log = structlog.get_logger()

_MAX_STEPS = int(getattr(settings, "THINKING_MAX_STEPS", 8) or 8)


def _name(entity: Entity | None) -> str:
    if entity is None:
        return ""
    return (entity.display_name or entity.name or entity.urn)


def _detail(entity: Entity | None) -> str:
    if entity is None:
        return ""
    payload = entity.payload or {}
    parts: list[str] = []
    d = entity.description or payload.get("description")
    if d:
        parts.append(str(d)[:180])
    domain = entity.domain or payload.get("domain")
    if domain:
        parts.append(f"domain: {domain}")
    platform = entity.platform
    if platform:
        parts.append(f"platform: {platform}")
    return " | ".join(parts)


def _is_key_like(field: dict[str, Any]) -> bool:
    name = str(field.get("name") or "").lower()
    return bool(re.search(r"(?:^|_)(id|key|fk|pk|code)($|_)|_id$|_key$", name))


def _quality_score(payload: dict[str, Any]) -> int:
    try:
        profiling = payload.get("profiling") or {}
        if profiling:
            nonnull = 0
            total = 0
            for col in profiling.get("columnProfiles") or []:
                total += 1
                if col.get("nullCount") == 0:
                    nonnull += 1
            if total:
                return round(100 * nonnull / total)
    except Exception:  # noqa: BLE001
        pass
    return 100  # no profiling data -> assume ok (reported honestly upstream)


class ThinkingExecutor:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = EntityRepository(session)
        self._graph = MetadataGraph(session)
        self._resolver = EntityResolver(session)

    async def execute(self, plan: ExecutionPlan) -> ExecutionPlan:
        for i, step in enumerate(plan.steps):
            if i >= _MAX_STEPS:
                step.status = "insufficient"
                step.note = "step budget exceeded; skipped."
                continue
            if step.status in ("done", "insufficient"):
                continue
            try:
                recs = await self._run_step(step, plan)
            except Exception:  # noqa: BLE001
                log.exception("thinking_step_failed", step=step.step_id,
                              name=step.name, question=plan.question[:80])
                recs = []
            step.evidence = _dedup(recs)
            if step.evidence:
                step.status = "done"
            else:
                step.status = "insufficient"
                step.note = "No metadata found for this step."
        return plan

    # ------------------------------------------------------------------ #
    async def _run_step(self, step: PlanStep, plan: ExecutionPlan) -> list[EvidenceRecord]:
        name = step.name or ""
        if name == "Resolve entities":
            return await self._resolve(step, plan)
        if name == "Compare candidates":
            return await self._compare(step, plan)
        if name == "What-if impact":
            return await self._impact(step)
        if name == "Owner+quality+usage":
            return await self._ownerless_quality(step)
        if name == "System overview":
            return await self._overview(step)
        if name == "Join-key analysis":
            return await self._join_key(step)
        if name == "Glossary<->domain<->dataset":
            return await self._cross_ref(step)
        # Generic fallback: resolve then pull requested sources.
        out: list[EvidenceRecord] = []
        for src in step.sources or [KnowledgeSource.DATASET_METADATA]:
            out.extend(await self._by_source(step, src))
        return out

    # ------------------------------------------------------------------ #
    # Resolve
    # ------------------------------------------------------------------ #
    async def _resolve_urn(self, name: str,
                           entity_type: str | None = None) -> str | None:
        if not name:
            return None
        try:
            res = await self._resolver.resolve(name, entity_type=entity_type)
            if res and res.resolved is not None:
                return res.resolved.urn
        except Exception:  # noqa: BLE001
            pass
        return None

    async def _resolve(self, step: PlanStep,
                       plan: ExecutionPlan) -> list[EvidenceRecord]:
        names = (plan.entities or [step.entity] if step.entity else [])
        out: list[EvidenceRecord] = []
        for nm in names:
            if not nm:
                continue
            urn = await self._resolve_urn(nm)
            if not urn:
                continue
            ent = await self._repo.get_by_urn(urn)
            if ent:
                out.append(EvidenceRecord(
                    urn=urn,
                    detail=_detail(ent),
                    source=KnowledgeSource.DATASET_METADATA,
                    snippet=_name(ent),
                    confidence=0.95,
                    entity_type=ent.entity_type,
                ))
        return out

    async def _by_source(self, step: PlanStep, source: KnowledgeSource) -> list[EvidenceRecord]:
        name = (step.entity or "").strip()
        if source == KnowledgeSource.SCHEMA_FIELD:
            return await self._schema(step, name)
        if source == KnowledgeSource.OWNER:
            return await self._owners(step, name)
        if source == KnowledgeSource.GLOSSARY:
            return await self._glossary(step, name)
        if source == KnowledgeSource.LINEAGE:
            return await self._lineage(step, name)
        if source in (KnowledgeSource.DOWNSTREAM, KnowledgeSource.UPSTREAM):
            return await self._downup(step, name, source)
        if source == KnowledgeSource.DATA_QUALITY:
            return await self._quality(step, name)
        return []

    # -- schema ---------------------------------------------------------
    async def _schema(self, step: PlanStep, name: str) -> list[EvidenceRecord]:
        if not name:
            return []
        urn = await self._resolve_urn(name, "dataset")
        if not urn:
            return []
        ent = await self._repo.get_by_urn(urn)
        fields = (ent.payload or {}).get("schema_fields") or [] if ent else []
        return [
            EvidenceRecord(
                urn=urn,
                detail=f"field {f.get('name')} ({f.get('type')})",
                source=KnowledgeSource.SCHEMA_FIELD,
                snippet=str(f.get("name", "")),
                confidence=0.85,
                entity_type="dataset",
            )
            for f in fields if f.get("name")
        ]

    # -- owners ---------------------------------------------------------
    async def _owners(self, step: PlanStep, name: str) -> list[EvidenceRecord]:
        if not name:
            return []
        urn = await self._resolve_urn(name)
        if not urn:
            return []
        ent = await self._repo.get_by_urn(urn)
        owners = (ent.payload or {}).get("owners") or [] if ent else []
        if not owners:
            return [EvidenceRecord(
                urn=urn, detail="No owner recorded",
                source=KnowledgeSource.OWNER,
                snippet="ownerless",
                confidence=0.9, entity_type="dataset",
            )]
        return [EvidenceRecord(
            urn=urn,
            detail="Owners: " + ", ".join(str(o.get("name")) for o in owners),
            source=KnowledgeSource.OWNER,
            snippet="owned", confidence=0.9, entity_type="dataset",
        )]

    # -- glossary -------------------------------------------------------
    async def _glossary(self, step: PlanStep, name: str) -> list[EvidenceRecord]:
        if not name:
            return []
        urn = await self._resolve_urn(name, "glossary_term")
        if not urn:
            urn = await self._resolve_urn(name)
        if not urn:
            return []
        ent = await self._repo.get_by_urn(urn)
        desc = (ent.payload or {}).get("description") or "" if ent else ""
        return [EvidenceRecord(urn=urn, detail=str(desc),
                               source=KnowledgeSource.GLOSSARY,
                               snippet=_name(ent), confidence=0.9,
                               entity_type=ent.entity_type if ent else "glossary_term")]

    # -- lineage --------------------------------------------------------
    async def _lineage(self, step: PlanStep, name: str) -> list[EvidenceRecord]:
        if not name:
            return []
        urn = await self._resolve_urn(name, "dataset")
        if not urn:
            return []
        try:
            up = await self._graph.neighbors(urn, "upstream")
            down = await self._graph.neighbors(urn, "downstream")
        except Exception:
            up, down = [], []
        out: list[EvidenceRecord] = []
        out.append(_path_record(urn, "upstream", up))
        out.append(_path_record(urn, "downstream", down))
        return out

    async def _downup(self, step: PlanStep, name: str,
                      source: KnowledgeSource) -> list[EvidenceRecord]:
        if not name:
            return []
        urn = await self._resolve_urn(name, "dataset")
        if not urn:
            return []
        try:
            nodes = await self._graph.neighbors(urn, source.value)
        except Exception:
            nodes = []
        out: list[EvidenceRecord] = []
        for n in nodes:
            ent = await self._repo.get_by_urn(n)
            out.append(EvidenceRecord(
                urn=n, detail=_detail(ent) if ent else "",
                source=source, snippet=_name(ent) if ent else n,
                confidence=0.8, entity_type=ent.entity_type if ent else None,
            ))
        return out

    # -- quality --------------------------------------------------------
    async def _quality(self, step: PlanStep, name: str) -> list[EvidenceRecord]:
        urn = await self._resolve_urn(name, "dataset") if name else None
        if urn:
            ent = await self._repo.get_by_urn(urn)
            if ent:
                score = _quality_score(ent.payload or {})
                return [EvidenceRecord(
                    urn=urn, detail=f"quality ~{score}/100",
                    source=KnowledgeSource.DATA_QUALITY,
                    snippet=f"quality {score}/100", confidence=0.85,
                    entity_type="dataset",
                )]
        # Quality across the catalog.
        out: list[EvidenceRecord] = []
        datasets = await self._repo.list_by_type("dataset", limit=500)
        for ent in datasets:
            score = _quality_score(ent.payload or {})
            if score < 70:
                out.append(EvidenceRecord(
                    urn=ent.urn, detail=f"low quality ~{score}",
                    source=KnowledgeSource.DATA_QUALITY,
                    snippet=f"{_name(ent)} quality {score}/100",
                    confidence=0.8, entity_type="dataset",
                ))
        return out

    # -- compare --------------------------------------------------------
    async def _compare(self, step: PlanStep, plan: ExecutionPlan) -> list[EvidenceRecord]:
        out: list[EvidenceRecord] = []
        names = plan.entities or ([step.entity] if step.entity else [])
        for nm in names:
            if not nm:
                continue
            urn = await self._resolve_urn(nm)
            if not urn:
                continue
            ent = await self._repo.get_by_urn(urn)
            if ent:
                out.append(EvidenceRecord(
                    urn=urn, detail=_detail(ent),
                    source=KnowledgeSource.DATASET_METADATA,
                    snippet=_name(ent), confidence=0.9,
                    entity_type=ent.entity_type,
                ))
        return _dedup(out)

    # -- impact ---------------------------------------------------------
    async def _impact(self, step: PlanStep) -> list[EvidenceRecord]:
        if not step.entity:
            return []
        urn = await self._resolve_urn(step.entity, "dataset")
        if not urn:
            return []
        try:
            depth = int(getattr(settings, "IMPACT_DEFAULT_DEPTH", 3) or 3)
            max_nodes = int(getattr(settings, "IMPACT_MAX_NODES", 200) or 200)
            summary = await self._graph.impact_summary(urn, depth=depth, max_nodes=max_nodes) or {}
        except Exception:
            summary = {}
        recs: list[EvidenceRecord] = []
        for u in summary.get("immediate", []) or []:
            ent = await self._repo.get_by_urn(u)
            recs.append(EvidenceRecord(urn=u, detail="immediate consumer",
                                       source=KnowledgeSource.DOWNSTREAM,
                                       snippet=_name(ent) if ent else u,
                                       confidence=0.9,
                                       entity_type=ent.entity_type if ent else None))
        for u in summary.get("indirect", []) or []:
            ent = await self._repo.get_by_urn(u)
            recs.append(EvidenceRecord(urn=u, detail="indirect consumer",
                                       source=KnowledgeSource.DOWNSTREAM,
                                       snippet=_name(ent) if ent else u,
                                       confidence=0.7,
                                       entity_type=ent.entity_type if ent else None))
        for d in summary.get("affected_dashboards", []) or []:
            recs.append(EvidenceRecord(urn=str(d), detail="dashboard",
                                       source=KnowledgeSource.DOWNSTREAM,
                                       snippet=str(d), confidence=0.9,
                                       entity_type="dashboard"))
        for p in summary.get("affected_pipelines", []) or []:
            recs.append(EvidenceRecord(urn=str(p), detail="pipeline/ETL",
                                       source=KnowledgeSource.DOWNSTREAM,
                                       snippet=str(p), confidence=0.9,
                                       entity_type="dataJob"))
        return recs

    # -- ownerless + quality + usage ------------------------------------
    async def _ownerless_quality(self, step: PlanStep) -> list[EvidenceRecord]:
        datasets = await self._repo.list_by_type("dataset", limit=1000)
        out: list[EvidenceRecord] = []
        for ent in datasets:
            payload = ent.payload or {}
            owners = payload.get("owners") or []
            ownerless = not owners
            score = _quality_score(payload)
            usage = len(payload.get("downstreams") or []) or 0
            if ownerless and score < 70:
                out.append(EvidenceRecord(
                    urn=ent.urn,
                    detail=_detail(ent),
                    source=KnowledgeSource.OWNER,
                    snippet=f"{_name(ent)}: no owner, quality {score}/100, {usage} consumers",
                    confidence=0.95, entity_type=ent.entity_type,
                    extra={"ownerless": True, "quality": score, "usage": usage},
                ))
        return out

    # -- overview -------------------------------------------------------
    async def _overview(self, step: PlanStep) -> list[EvidenceRecord]:
        all_ds = await self._repo.list_all(entity_type="dataset", limit=2000)
        out: list[EvidenceRecord] = []
        domains: dict[str, int] = {}
        for ent in all_ds:
            d = (ent.domain or "") or (ent.payload or {}).get("domain") or "unknown"
            domains[d] = domains.get(d, 0) + 1
        for d, cnt in sorted(domains.items()):
            out.append(EvidenceRecord(urn=f"domain:{d}", detail=f"{cnt} datasets",
                                      source=KnowledgeSource.DOMAIN,
                                      snippet=f"domain {d}: {cnt} datasets",
                                      confidence=0.95, entity_type="domain"))
        heavy = [e for e in all_ds
                 if len((e.payload or {}).get("downstreams") or []) >= 2]
        out.append(EvidenceRecord(urn="system:fanout", detail="fan-out",
                                  source=KnowledgeSource.LINEAGE,
                                  snippet=f"{len(heavy)} datasets with many consumers",
                                  confidence=0.8))
        unowned = [e for e in all_ds if not (e.payload or {}).get("owners")]
        out.append(EvidenceRecord(urn="system:owners", detail="governance",
                                  source=KnowledgeSource.OWNER,
                                  snippet=f"{len(unowned)} datasets without an owner",
                                  confidence=0.8))
        return out

    # -- join key -------------------------------------------------------
    async def _join_key(self, step: PlanStep) -> list[EvidenceRecord]:
        if not step.entity:
            return []
        urn = await self._resolve_urn(step.entity, "dataset")
        if not urn:
            return []
        ent = await self._repo.get_by_urn(urn)
        fields = (ent.payload or {}).get("schema_fields") or [] if ent else []
        return [EvidenceRecord(
            urn=urn,
            detail=f"key-like field {f.get('name')} ({f.get('type')})",
            source=KnowledgeSource.SCHEMA_FIELD,
            snippet=f"join key {f.get('name')}",
            confidence=0.8, entity_type="dataset",
        ) for f in fields if _is_key_like(f)]

    # -- cross ref ------------------------------------------------------
    async def _cross_ref(self, step: PlanStep) -> list[EvidenceRecord]:
        terms = await self._repo.list_by_type("glossary_term", limit=2000)
        datasets = await self._repo.list_by_type("dataset", limit=2000)
        term_urns = {t.urn for t in terms}
        out: list[EvidenceRecord] = []
        for ds in datasets:
            used = (ds.payload or {}).get("glossary_terms") or []
            hits = [str(g) for g in used if g in term_urns]
            if hits:
                out.append(EvidenceRecord(urn=ds.urn, detail=_detail(ds),
                                          source=KnowledgeSource.GLOSSARY,
                                          snippet=f"{_name(ds)} uses terms: {', '.join(hits)}",
                                          confidence=0.9, entity_type=ds.entity_type))
        return out


def _dedup(records: list[EvidenceRecord]) -> list[EvidenceRecord]:
    seen: set[tuple[str, KnowledgeSource, str]] = set()
    out: list[EvidenceRecord] = []
    for r in records:
        key = (r.urn, r.source, r.snippet)
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def _path_record(urn: str, label: str, nodes: list[str]) -> EvidenceRecord:
    return EvidenceRecord(
        urn=urn,
        detail=f"{label}: {', '.join(nodes) if nodes else 'none'}",
        source=KnowledgeSource.LINEAGE,
        snippet=f"{label} ({len(nodes)}): {', '.join(nodes[:10])}",
        confidence=0.85,
    )
