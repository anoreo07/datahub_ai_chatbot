"""Query plan executor.

Executes a ``QueryPlan`` produced by the intent classifier as a small DAG of
tool calls:

- Steps declare ``depends_on`` (indices into the plan step list).
- Independent steps run concurrently via ``asyncio.gather`` (parallel tool
  orchestration); dependent steps wait for their prerequisites.
- Each tool call retries transient failures before giving up (returns []).
- Results are de-duplicated by URN so parallel branches don't duplicate
  retrieval or downstream LLM calls.
"""

from __future__ import annotations

import asyncio
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from retrieval.hybrid_search import SearchResult
from retrieval.query_models import PlanStep, QueryPlan
from retrieval.tools import ToolRegistry

log = structlog.get_logger()

# Map a QueryPlan.intent to a default tool op + param mapping.
_SINGLE_OPS: dict[str, str] = {
    "SCHEMA_LOOKUP": "schema_lookup",
    "OWNER_LOOKUP": "owner_lookup",
    "TERM_DEFINITION": "glossary_lookup",
    "COUNT_ENTITIES": "count_entities",
    "TERM_TO_DATASETS": "term_to_datasets",
    "ENTITY_EXISTS": "existence",
    "LISTING": "list_by_type",
    "DOCUMENT_QA": "document_qa",
}

# Accepts either a sync sessionmaker or async_sessionmaker bound to the app engine.
SessionFactory = Any


class PlannerExecutor:
    def __init__(self, session: AsyncSession,
                 session_factory: SessionFactory | None = None) -> None:
        self._session = session
        self._session_factory = session_factory
        self._tools = ToolRegistry(session)

    def _params(self, plan: QueryPlan, op: str | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if plan.primary_entity:
            params["name"] = plan.primary_entity
        if plan.entity_type:
            params["entity_type"] = plan.entity_type
        if plan.filter.dimension:
            params["dimension"] = plan.filter.dimension
        if plan.filter.value:
            params["value"] = plan.filter.value
        if plan.direction:
            params["direction"] = plan.direction
        if plan.params.depth:
            params["depth"] = plan.params.depth
        if plan.params.top_k:
            params["top_k"] = plan.params.top_k
        return params

    def _default_op(self, plan: QueryPlan) -> str | None:
        intent = plan.intent
        if intent == "IMPACT":
            return "recursive_impact"
        if intent == "LINEAGE":
            return "lineage"
        if intent in ("DOMAIN_QUERY", "PLATFORM_QUERY", "TAG_QUERY",
                      "ENTITIES_BY_OWNER", "CERTIFIED_LIST"):
            return "list_by_dimension"
        if intent == "FIND_ENTITY":
            return "resolve_entity"
        return _SINGLE_OPS.get(intent)

    def _default_steps(self, plan: QueryPlan) -> list[PlanStep]:
        if plan.intent in ("COMPOSITE_QUERY", "MULTI_ENTITY_QUERY"):
            # Expand a composite query into one resolve step per referenced
            # entity, run as independent (parallel) branches in the DAG.
            refs = [r for r in (plan.entity_refs or []) if (r or "").strip()] \
                or ([plan.filter.value] if plan.filter.value else [])
            steps = [
                PlanStep(op="resolve_entity", params={"name": r.strip()},
                         purpose=f"resolve {r.strip()}")
                for r in refs
            ]
            if steps:
                return steps
        op = self._default_op(plan)
        if op is None:
            return []
        return [PlanStep(op=op, params=self._params(plan), purpose=f"{plan.intent} intent")]

    async def execute(self, plan: QueryPlan) -> list[SearchResult]:
        if not plan.entity_refs and plan.filter.value is None and not plan.steps:
            # Nothing to resolve -> let the hybrid/vector path handle it.
            if plan.intent not in ("COMPOSITE_QUERY", "MULTI_ENTITY_QUERY"):
                return []

        steps = plan.steps if plan.steps else (
            self._default_steps(plan)
            if plan.is_composite or plan.intent in ("COMPOSITE_QUERY", "MULTI_ENTITY_QUERY")
            else []
        )
        if steps:
            results = await self._execute_dag(steps)
        else:
            op = self._default_op(plan)
            if op is None:
                return []
            results = await self._run_op(op, self._params(plan))

        results = self._dedupe(results)
        log.info("planner_executed", intent=plan.intent, result_count=len(results))
        return results

    async def _run_op(
        self, op: str, params: dict[str, Any], retries: int = 1
    ) -> list[SearchResult]:
        """Run one tool op with bounded retries (tool-orchestrator resilience).

        When a session factory is available, each op runs on its own short-lived
        session. This is the only safe way to execute independent DAG branches
        concurrently: SQLAlchemy forbids sharing a single ``AsyncSession`` across
        concurrent operations (race condition otherwise surfaced as ISCE).
        """
        for attempt in range(retries + 1):
            try:
                if self._session_factory is None:
                    results = await self._tools.execute(op, params)
                else:
                    async with self._session_factory() as op_session:
                        branch_tools = ToolRegistry(op_session)
                        results = await branch_tools.execute(op, params)
                if results:
                    return results
            except Exception:  # noqa: BLE001
                log.warning("planner_op_attempt_failed", op=op, attempt=attempt)
            await asyncio.sleep(0)
        return []

    async def _execute_steps_concurrent(self, steps: list[PlanStep]) -> list[SearchResult]:
        """Legacy sequential runner kept as a plain ordered fallback."""
        return await self._execute_dag(steps)

    async def _execute_dag(self, steps: list[PlanStep]) -> list[SearchResult]:
        """Execute the plan as a DAG: run independent steps concurrently.

        ``depends_on`` holds indices into ``steps``. A step is runnable once all
        its dependencies have completed. Independent steps (same front layer)
        run together via ``asyncio.gather`` (parallel tool orchestration).

        Parallelism requires a dedicated session per branch (``session_factory``):
        without one, steps run sequentially on the shared session — SQLAlchemy
        forbids concurrent use of a single ``AsyncSession`` (ISCE race).
        """
        if not steps:
            return []
        if len(steps) == 1:
            return await self._run_op(steps[0].op, steps[0].params)

        def _ready(i: int) -> bool:
            if i in completed:
                return False
            for dep in steps[i].depends_on or []:
                if dep not in completed:
                    return False
            return True

        results_per_step: dict[int, list[SearchResult]] = {}
        completed: set[int] = set()

        while len(completed) < len(steps):
            ready = [i for i in range(len(steps)) if _ready(i)]
            if not ready:
                # Cycle or ordering issue -> run the first unfinished sequentially.
                ready = [next(i for i in range(len(steps)) if i not in completed)]

            if self._session_factory is None:
                # Sequential fallback: one op at a time on the shared session.
                for i in ready:
                    results_per_step[i] = await self._run_op(
                        steps[i].op, steps[i].params)
                    completed.add(i)
            else:
                batch = await asyncio.gather(
                    *[self._run_op(steps[i].op, steps[i].params) for i in ready]
                )
                for i, step_results in zip(ready, batch):
                    results_per_step[i] = step_results
                    completed.add(i)

        # Aggregate in topological (original) order.
        results: list[SearchResult] = []
        for i, step in enumerate(steps):
            results.extend(results_per_step.get(i, []))
        return results


    def _dedupe(self, results: list[SearchResult]) -> list[SearchResult]:
        seen: set[str] = set()
        out: list[SearchResult] = []
        for r in results:
            if r.urn in seen:
                continue
            seen.add(r.urn)
            out.append(r)
        return out
