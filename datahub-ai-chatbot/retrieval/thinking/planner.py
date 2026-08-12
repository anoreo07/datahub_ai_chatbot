"""Thinking planner: decomposes a complex question into an ExecutionPlan.

Each step is a sub-question with:
- a concrete ``sub_question`` (what we try to answer),
- the retrieval ``sources`` it needs,
- the entity/entities it targets,
- a ``conclusion_criteria`` (what counts as an answer),
- a ``stop_condition`` (when the step can be considered settled).

The decomposition is deterministic: it reads the complexity verdict (sources +
intent hint) plus the resolved context (entities / domains / terms) and emits a
plan of ordered, semi-independent steps. Execution order respects dependencies
(impact must run after the root entity is known; comparison runs per entity).
"""

from __future__ import annotations

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from retrieval.thinking.complexity import ComplexityVerdict
from retrieval.thinking.context import ContextResolver
from retrieval.thinking.models import ExecutionPlan, KnowledgeSource, PlanStep, ThinkingContext

log = structlog.get_logger()


def _uniq(items: list[str]) -> list[str]:
    out: list[str] = []
    for i in items:
        if i and i not in out:
            out.append(i)
    return out


class ThinkingPlanner:
    def __init__(self, session: AsyncSession) -> None:
        self._context_resolver = ContextResolver(session)

    async def plan(
        self,
        question: str,
        verdict: ComplexityVerdict,
        history: list[tuple[str, str]] | None = None,
    ) -> tuple[ExecutionPlan, ThinkingContext]:
        ctx = await self._context_resolver.resolve(question, history=history)
        entities = _uniq((ctx.active_entities or []) + (ctx.all_entities or []))
        domains = _uniq(ctx.related_domains)
        sources = list(verdict.sources)
        hint = verdict.intent_hint

        steps: list[PlanStep] = []
        seq = [0]

        def _sid() -> str:
            seq[0] += 1
            return f"step-{seq[0]}"

        # Step 0: establish the subject entities (metadata + lineage root).
        if entities:
            steps.append(self._resolve_step(_sid(), entities))

        # Cross-domain term<->dataset linkage.
        if hint == "THINKING_CROSS_DOMAIN" or _cross_ref(question, sources):
            steps.append(self._cross_ref_step(_sid(), question, entities))

        # Comparison / selection.
        if hint == "THINKING_COMPARISON" or _has(question, [
                "so sánh", "compare", "so voi", "nên dùng", "phù hợp"
            ]):
            steps.append(self._compare_step(_sid(), entities or ["datasets"]))

        # Impact / what-if-delete.
        if hint == "THINKING_IMPACT" or _has(question, ["xóa", "xoá", "delete", "drop", "thay"]):
            steps.append(self._impact_step(_sid(), entities))

        # Multi-constraint: ownerless + low quality + heavy use.
        if _has(question, ["thiếu owner", "thieu owner", "missing owner"]) and \
           _has(question, ["chất lượng", "quality", "kem"]):
            steps.append(self._ownerless_step(_sid()))

        # Join-key / schema analysis.
        if _has(question, ["join key", "khóa nối", "khoa noi"]):
            steps.append(self._join_key_step(_sid(), entities))

        # System-level overview.
        if hint == "THINKING_OVERVIEW":
            steps.append(self._overview_step(_sid(), question, domains))

        # Coverage of any extra requested sources (quality/doc/permission).
        for extra in _extra_steps(question, sources, entities):
            if extra.step_id not in {s.step_id for s in steps}:
                steps.append(extra)

        # If nothing matched, emit a generic reasoning step over the sources.
        if not steps:
            steps.append(self._generic_step(_sid(), question, entities, sources))

        goal = _goal_for(hint, question)
        plan = ExecutionPlan(
            question=question,
            intent=hint,
            goal=goal,
            entities=entities,
            steps=steps,
        )
        log.info("thinking_plan", intent=plan.intent, steps=len(steps),
                 entities=plan.entities, question=question[:100])
        return plan, ctx

    # ------------------------------------------------------------------ #
    # Step factories
    # ------------------------------------------------------------------ #
    def _resolve_step(self, sid: str, entities: list[str]) -> PlanStep:
        names = ", ".join(entities)
        return PlanStep(
            step_id=sid,
            name="Resolve entities",
            sub_question=(
                f"Xác định chính xác các dataset/entity '{names}' trong metadata DataHub"
            ),
            goal="Establish a unique, grounded identity for every entity the question touches.",
            sources=[KnowledgeSource.DATASET_METADATA],
            entity=entities[0] if entities else None,
            conclusion_criteria=(
                "Each named entity resolves to exactly one catalog entity with metadata."
            ),
            stop_condition=(
                "Stop when every entity is resolved to a URN; else keep the unresolved names."
            ),
        )

    def _cross_ref_step(self, sid: str, question: str,
                        entities: list[str]) -> PlanStep:
        return PlanStep(
            step_id=sid,
            name="Glossary<->domain<->dataset",
            sub_question=(
                "Tìm glossary term gắn với domain/entity, rồi tìm dataset nào đang dùng các term đó"
            ),
            goal=(
                "Relate glossary terms, their domain, and the datasets referencing them."
            ),
            sources=[KnowledgeSource.GLOSSARY, KnowledgeSource.DOMAIN,
                     KnowledgeSource.DOWNSTREAM],
            entity=entities[0] if entities else None,
            conclusion_criteria=(
                "A term is linked to its definition, domain, and every dataset tagged with it."
            ),
            stop_condition=(
                "Stop when all referenced terms are listed with their using datasets."
            ),
        )

    def _compare_step(self, sid: str, entities: list[str]) -> PlanStep:
        return PlanStep(
            step_id=sid,
            name="Compare candidates",
            sub_question=(
                "So sánh các dataset/entity dựa trên metadata, schema, lineage, quality"
            ),
            goal="Rank the candidates by fit to the user's stated goal and justify the pick.",
            sources=[KnowledgeSource.DATASET_METADATA, KnowledgeSource.SCHEMA_FIELD,
                     KnowledgeSource.LINEAGE, KnowledgeSource.DATA_QUALITY],
            entity=entities[0] if entities else None,
            conclusion_criteria="A clear winner (or a tie + criteria) emerges with reasons.",
            stop_condition="Stop once each candidate has metadata+schema+lineage+quality compared.",
        )

    def _impact_step(self, sid: str, entities: list[str]) -> PlanStep:
        return PlanStep(
            step_id=sid,
            name="What-if impact",
            sub_question=(
                "Tính downstream bị ảnh hưởng (datasets/dashboards/ETL) nếu xóa/thay đổi entity"
            ),
            goal="Produce the blast radius: immediate + indirect consumers, dashboards, pipelines.",
            sources=[KnowledgeSource.DOWNSTREAM, KnowledgeSource.LINEAGE,
                     KnowledgeSource.DOCUMENT],
            entity=entities[0] if entities else None,
            conclusion_criteria=(
                "Downstream graph enumerated with affected dashboards / ETL flagged."
            ),
            stop_condition=(
                "Stop at the configured lineage depth once no new consumers appear."
            ),
        )

    def _ownerless_step(self, sid: str) -> PlanStep:
        return PlanStep(
            step_id=sid,
            name="Owner+quality+usage",
            sub_question=(
                "Tìm dataset thiếu owner, chất lượng kém nhưng vẫn được dùng nhiều"
            ),
            goal="Flag datasets that are risky but heavily consumed (governance blind spot).",
            sources=[KnowledgeSource.OWNER, KnowledgeSource.DATA_QUALITY,
                     KnowledgeSource.DOWNSTREAM],
            conclusion_criteria=(
                "Every dataset scored on owner/quality/usage; risky-but-used ones listed."
            ),
            stop_condition="Stop after scoring all candidate datasets.",
        )

    def _join_key_step(self, sid: str, entities: list[str]) -> PlanStep:
        return PlanStep(
            step_id=sid,
            name="Join-key analysis",
            sub_question="Tìm field dùng làm join key trong dataset",
            goal=(
                "Identify candidate primary/foreign keys and overlapping key fields "
                "between datasets."
            ),
            sources=[KnowledgeSource.SCHEMA_FIELD],
            entity=entities[0] if entities else None,
            conclusion_criteria=(
                "Candidate key fields (unique-ish / FK-named) enumerated per dataset."
            ),
            stop_condition=(
                "Stop once schema fields are scanned for key-like names/types."
            ),
        )

    def _overview_step(self, sid: str, question: str,
                       domains: list[str]) -> PlanStep:
        return PlanStep(
            step_id=sid,
            name="System overview",
            sub_question=(
                "Tổng quan kiến trúc dữ liệu theo domain / lineage / governance"
            ),
            goal=(
                "Answer from the architectural viewpoint: domain coverage, "
                "lineage complexity, fan-in/out, completeness."
            ),
            sources=[KnowledgeSource.DATASET_METADATA, KnowledgeSource.DOMAIN,
                     KnowledgeSource.LINEAGE, KnowledgeSource.OWNER,
                     KnowledgeSource.DATA_QUALITY],
            conclusion_criteria="Overview answer organized by domain/architecture/governance.",
            stop_condition="Stop after aggregating datasets per domain and per lineage complexity.",
        )

    def _generic_step(self, sid: str, question: str, entities: list[str],
                      sources: list[KnowledgeSource]) -> PlanStep:
        return PlanStep(
            step_id=sid,
            name="Reasoning",
            sub_question=question,
            goal="Reason across the available knowledge sources to answer the question.",
            sources=sources or [KnowledgeSource.DATASET_METADATA],
            entity=entities[0] if entities else None,
            conclusion_criteria="A grounded, sourced answer with explicit gaps.",
            stop_condition="Stop when the sources are exhausted or the answer is grounded.",
        )


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _has(question: str, keys: list[str]) -> bool:
    q = (question or "").lower()
    return any(k.lower() in q for k in keys)


def _cross_ref(question: str, sources: list[KnowledgeSource]) -> bool:
    return KnowledgeSource.GLOSSARY in sources and bool(
        re_search(r"\b(?:domain|dataset|bang)\b", question)
    )


def _extra_steps(question: str, sources: list[KnowledgeSource],
                 entities: list[str]) -> list[PlanStep]:
    steps: list[PlanStep] = []
    # A dedicated quality step whenever quality is part of the ask.
    if KnowledgeSource.DATA_QUALITY in sources and "quality" not in question.lower():
        steps.append(PlanStep(
            step_id="step-quality",
            name="Data quality",
            sub_question="Đánh giá chất lượng dữ liệu của các dataset liên quan",
            goal="Quantify data quality (score, issues) for each involved dataset.",
            sources=[KnowledgeSource.DATA_QUALITY],
            entity=entities[0] if entities else None,
            conclusion_criteria="A quality score / rating per dataset.",
            stop_condition="Stop when every involved dataset has a quality score.",
        ))
    return steps


def _goal_for(hint: str, question: str) -> str:
    mapping = {
        "THINKING_COMPARISON": "Chọn / so sánh các asset theo mục tiêu người dùng.",
        "THINKING_OVERVIEW": "Trả lời theo góc nhìn kiến trúc dữ liệu & governance.",
        "THINKING_IMPACT": "Xác định phạm vi ảnh hưởng khi thay đổi/xóa asset.",
        "THINKING_CROSS_DOMAIN": "Liên kết các thực thể / term / domain chéo nhau.",
        "THINKING_PLANNING": "Lập kế hoạch xây dựng dựa trên các asset hiện có.",
    }
    return mapping.get(hint, "Phân tích tổng quan, nhiều bước với nhiều nguồn dữ liệu.")


def re_search(pattern: str, text: str) -> bool:
    import re
    return re.search(pattern, text, re.I) is not None
