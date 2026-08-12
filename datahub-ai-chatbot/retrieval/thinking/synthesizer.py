"""Synthesizer: merges per-step evidence into the final structured answer.

Reads the executed ExecutionPlan and builds an ``EffortResult`` with:
- a concise conclusion
- the key reasons (per step: what was found + how it was decided)
- the reasoning trace (which step ran, which sources, what it returned)
- related entities (deduplicated)
- risks / uncertainty (derived from low-confidence or insufficient steps)
- next recommendations
- an explicit ``missing`` list describing each step with no data, so gaps are
  reported instead of guessed.

The answer is grounded only in the evidence records produced by the executor.
"""

from __future__ import annotations

import structlog

from retrieval.thinking.models import EffortResult, EvidenceRecord, ExecutionPlan, PlanStep

log = structlog.get_logger()


class ThinkingSynthesizer:
    def synthesize(self, plan: ExecutionPlan) -> EffortResult:
        steps = plan.steps
        related: dict[str, str] = {}
        reasons: list[str] = []
        steps_log: list[str] = []
        risks: list[str] = []
        missing: list[str] = []
        all_evidence: list[EvidenceRecord] = []

        for step in steps:
            ev = step.evidence or []
            all_evidence.extend(ev)
            for e in ev:
                related.setdefault(e.snippet or e.urn, e.urn)

            if step.status == "done":
                reasons.append(
                    f"{_label(step)}: {_summarize(ev)}"
                )
                steps_log.append(
                    f"- **{step.name}**: {step.sub_question} → {_count_summary(ev)} "
                    f"(sources: {step.sources_str()})"
                )
            elif step.status == "insufficient":
                missing.append(
                    f"- {step.name}: {step.sub_question} (sources: {step.sources_str()})"
                )
                steps_log.append(
                    f"- **{step.name}**: {step.sub_question} → không tìm thấy dữ liệu."
                )
                risks.append(f"Không đủ dữ liệu ở bước '{step.name}' nên kết luận chưa chắc chắn.")
            if step.note:
                steps_log.append(f"  ({step.note})")

        # Low-confidence evidence -> risk.
        low = [e for e in all_evidence if e.confidence < 0.6]
        if low:
            risks.append(f"{len(low)} thông tin có độ tin cậy thấp, cần xác nhận.")

        conclusion = self._conclusion(plan, all_evidence, missing)
        next_steps = self._next_steps(plan, missing)

        result = EffortResult(
            conclusion=conclusion,
            key_reasons=_dedupe_lines(reasons),
            steps_log=steps_log,
            related_entities=sorted(related.items()),
            risks=_dedupe_lines(risks),
            next_steps=next_steps,
            missing=_dedupe_lines(missing),
        )
        log.info("thinking_synthesized", steps=len(steps), evidence=len(all_evidence),
                 missing=len(result.missing), question=plan.question[:80])
        return result

    # ------------------------------------------------------------------ #
    def _conclusion(self, plan: ExecutionPlan, evidence: list[EvidenceRecord],
                    missing: list[str]) -> str:
        if not evidence:
            return (
                "Chưa đủ dữ liệu để trả lời. Các nguồn truy vấn đều không có kết quả — "
                "không nên đoán; cần bổ sung metadata hoặc làm rõ câu hỏi."
            )
        if plan.intent == "THINKING_IMPACT":
            consumers = [e for e in evidence if e.source.value == "downstream"]
            if consumers:
                names = _unique_names(consumers)
                return (
                    f"Khi xóa/thay đổi asset này, có {len(names)} consumer "
                    f"bị ảnh hưởng: {', '.join(names[:8])}{'...' if len(names) > 8 else ''}."
                )
            return "Không tìm thấy consumer bị ảnh hưởng trong phạm vi đã duyệt."
        if plan.intent == "THINKING_COMPARISON":
            entities = [e for e in evidence if e.entity_type == "dataset"]
            names = _unique_names(entities)
            return (
                f"Đã so sánh {len(names)} dataset ứng viên: {', '.join(names[:6])}. "
                "Khuyến nghị cụ thể nằm ở phần lý do."
            )
        if plan.intent == "THINKING_OVERVIEW":
            domains = [e for e in evidence if e.source.value == "domain"]
            if domains:
                return (
                    "Tổng quan hệ thống: " + "; ".join(e.snippet for e in domains[:8])
                    + "."
                )
        # Generic conclusion from the strongest evidence.
        best = sorted(evidence, key=lambda e: e.confidence, reverse=True)[:1]
        if best:
            return f"Phân tích dựa trên {len(evidence)} mảnh dữ liệu; kết luận chi tiết bên dưới."
        return "Không đủ dữ liệu."

    def _next_steps(self, plan: ExecutionPlan, missing: list[str]) -> list[str]:
        out: list[str] = []
        if missing:
            out.append(
                "Bổ sung metadata còn thiếu (owner, mô, schema, lineage) để trả lời đầy đủ hơn."
            )
        if plan.intent == "THINKING_COMPARISON":
            out.append(
                "Xác nhận tiêu chí ưu tiên (chất lượng / lineage / mức dùng) trước khi chốt."
            )
        elif plan.intent == "THINKING_IMPACT":
            out.append(
                "Liên hệ team sở hữu các consumer để xác nhận phương án xử lý."
            )
        elif plan.intent == "THINKING_OVERVIEW":
            out.append(
                "Đi sâu vào một domain cụ thể nếu cần chi tiết hơn."
            )
        return out


def _label(step: PlanStep) -> str:
    return step.name


def _summarize(evidence: list[EvidenceRecord]) -> str:
    if not evidence:
        return "không có dữ liệu"
    parts = []
    for e in evidence[:5]:
        s = e.snippet or e.detail or e.urn
        parts.append(s)
    return ", ".join(dict.fromkeys(parts)) + (" (và các bản ghi khác)" if len(evidence) > 5 else "")


def _count_summary(evidence: list[EvidenceRecord]) -> str:
    if not evidence:
        return "0 bản ghi"
    return f"{len(evidence)} bản ghi"


def _unique_names(records: list[EvidenceRecord]) -> list[str]:
    seen: list[str] = []
    for r in records:
        n = r.snippet or r.urn
        if n and n not in seen:
            seen.append(n)
    return seen


def _dedupe_lines(lines: list[str]) -> list[str]:
    out: list[str] = []
    for line in lines:
        if line and line not in out:
            out.append(line)
    return out
