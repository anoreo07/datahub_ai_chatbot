"""Multi-entity comparison flow."""
from __future__ import annotations

import json as _json
import re
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import structlog

from app.auth.models import UserContext
from app.schemas.chat import ChatResponse, EntityItem
from guardrails.sanitizer import mask_secrets

if TYPE_CHECKING:
    from app.services.chat.context import ChatContext

log = structlog.get_logger()


def deterministic_comparison(
    entity_details: list[dict[str, Any]],
    aspects: list[str],
) -> str:
    """Fallback comparison when LLM fails — render structured markdown from metadata."""
    lines: list[str] = ["### So sánh entities\n"]

    for ent in entity_details:
        lines.append(f"#### {ent['name']}")
        lines.append(f"- **URN**: `{ent['urn']}`")
        lines.append(f"- **Type**: {ent['entity_type']}")
        if ent.get("domain"):
            lines.append(f"- **Domain**: {ent['domain']}")
        if ent.get("owner"):
            lines.append(f"- **Owner**: {ent['owner']}")
        if ent.get("description"):
            lines.append(f"- **Description**: {ent['description'][:200]}")

        if "schema" in aspects and ent.get("schema"):
            lines.append(f"- **Schema** ({len(ent['schema'])} fields):")
            for f in ent["schema"][:10]:
                fname = f.get("name", "?")
                ftype = f.get("type", f.get("native_data_type", "?"))
                lines.append(f"  - `{fname}` ({ftype})")
            if len(ent["schema"]) > 10:
                lines.append(f"  - ... và {len(ent['schema']) - 10} trường khác")

        if "lineage" in aspects:
            up = ent["lineage"]["upstreams"]
            down = ent["lineage"]["downstreams"]
            if up or down:
                lines.append(f"- **Lineage**: {len(up)} upstream, {len(down)} downstream")
            else:
                lines.append("- **Lineage**: Không có lineage được ghi nhận")

        if "tags" in aspects and ent.get("tags"):
            lines.append(f"- **Tags**: {', '.join(ent['tags'][:5])}")

        if "glossary" in aspects and ent.get("glossary_terms"):
            lines.append(f"- **Glossary**: {', '.join(ent['glossary_terms'][:5])}")

        lines.append("")

    lines.append("### Kết luận")
    lines.append("So sánh trên dựa trên metadata thực tế từ catalog.")
    return "\n".join(lines)


async def comparison_flow(
    ctx: ChatContext,
    query: str,
    entity_names: list[str],
    user_ctx: UserContext | None,
    trace_id: str,
    cid: str,
    on_token: Callable[..., Any] | None = None,
    on_status: Callable[..., Any] | None = None,
) -> ChatResponse | None:
    """Compare multiple entities side-by-side."""
    if on_status:
        await on_status("retrieve")

    resolved_entities: list[dict[str, Any]] = []
    failed_entities: list[str] = []

    # Step 1: Resolve each entity independently
    for name in entity_names:
        try:
            res = await ctx.entity_resolver.resolve(name, entity_type=None, trace_id=trace_id)
            if res and res.resolved:
                best = res.resolved
                best_name = (
                    getattr(best, "display_name", None)
                    or getattr(best, "name", str(best))
                )
                resolved_entities.append({
                    "name": name,
                    "resolved_name": best_name,
                    "urn": best.urn,
                    "entity_type": best.entity_type,
                    "score": 1.0,
                })
            else:
                hybrid_search = getattr(ctx, "hybrid_search", None)
                if hybrid_search:
                    results = await hybrid_search.search(name, entity_type=None)
                else:
                    results = []
                if results:
                    best_res = results[0]
                    resolved_entities.append({
                        "name": name,
                        "resolved_name": best_res.name,
                        "urn": best_res.urn,
                        "entity_type": best_res.entity_type,
                        "score": best_res.score,
                    })
                else:
                    failed_entities.append(name)
        except Exception:  # noqa: BLE001
            log.exception("comparison_resolve_failed", entity=name, trace_id=trace_id)
            failed_entities.append(name)

    if not resolved_entities:
        entity_list = ", ".join(entity_names)
        answer = (
            f"Không tìm thấy entity nào trong số: {entity_list}. "
            "Vui lòng kiểm tra lại tên và thử lại."
        )
        return ChatResponse(
            answer=answer,
            intent="COMPARISON",
            confidence="low",
            ambiguous=False,
            insufficient_context=True,
            trace_id=trace_id,
            conversation_id=cid,
        )

    # Step 2: Retrieve metadata for each resolved entity
    entity_details: list[dict[str, Any]] = []
    for ent in resolved_entities:
        detail: dict[str, Any] = {
            "name": ent["resolved_name"],
            "urn": ent["urn"],
            "entity_type": ent["entity_type"],
            "schema": [],
            "lineage": {"upstreams": [], "downstreams": []},
            "domain": None,
            "owner": None,
            "description": None,
            "tags": [],
            "glossary_terms": [],
        }
        try:
            db_entity = await ctx.entity_repo.get_by_urn(ent["urn"])
            if db_entity:
                payload = db_entity.payload or {}
                detail["schema"] = payload.get("schema_fields") or []
                detail["domain"] = db_entity.domain
                detail["description"] = db_entity.description
                owners = payload.get("owners") or []
                detail["owner"] = payload.get("owner") or (owners[0] if owners else None)
                detail["tags"] = payload.get("tags") or []
                detail["glossary_terms"] = payload.get("glossary_terms") or []
        except Exception:  # noqa: BLE001
            log.exception("comparison_detail_failed", urn=ent["urn"], trace_id=trace_id)

        try:
            lineage_data = await ctx.source.get_lineage(
                ent["urn"], direction="both", depth=1,
            )
            for rel in lineage_data.get("relationships", []):
                entity_info = rel.get("entity", {})
                node = {
                    "name": entity_info.get("urn", ""),
                    "type": entity_info.get("type", "unknown"),
                }
                if rel.get("type") == "UPSTREAM":
                    detail["lineage"]["upstreams"].append(node)
                elif rel.get("type") == "DOWNSTREAM":
                    detail["lineage"]["downstreams"].append(node)
        except Exception:  # noqa: BLE001
            log.exception("comparison_lineage_failed", urn=ent["urn"], trace_id=trace_id)

        if not detail["lineage"]["upstreams"] and not detail["lineage"]["downstreams"]:
            db_ent = await ctx.entity_repo.get_by_urn(ent["urn"])
            if db_ent and db_ent.payload:
                for u in db_ent.payload.get("upstreams") or []:
                    detail["lineage"]["upstreams"].append({"name": u, "type": "dataset"})
                for d in db_ent.payload.get("downstreams") or []:
                    detail["lineage"]["downstreams"].append({"name": d, "type": "dataset"})

        entity_details.append(detail)

    # Step 3: Build comparison prompt and generate answer
    entities_text = _json.dumps(entity_details, ensure_ascii=False, indent=2, default=str)

    compare_aspects: list[str] = []
    aspect_patterns = [
        (r"schema|field|column|cột|trường", "schema"),
        (r"quality|chất lượng|chat luong|kém|sạch", "quality"),
        (r"lineage|upstream|downstream|nguồn|nguon", "lineage"),
        (r"owner|sở hữu|so huu|thuộc về ai", "owner"),
        (r"domain|lĩnh vực|linh vuc|miền|mien", "domain"),
        (r"description|mô tả|mo ta|nội dung", "description"),
        (r"tag|nhãn|nhan|gắn tag", "tags"),
        (r"glossary|term|thuật ngữ|thuat ngu|khái niệm", "glossary"),
    ]
    query_lower = query.lower()
    for pattern, aspect in aspect_patterns:
        if re.search(pattern, query_lower):
            compare_aspects.append(aspect)
    if not compare_aspects:
        compare_aspects = ["schema", "quality", "lineage", "domain"]

    comparison_prompt = (
        f"Bạn là trợ lý metadata. Hãy so sánh các entity sau dựa trên "
        f"các khía cạnh: {', '.join(compare_aspects)}.\n\n"
        f"Dữ liệu entities:\n{entities_text}\n\n"
        f"Câu hỏi gốc: {query}\n\n"
        f"Yêu cầu:\n"
        f"1. Liệt kê thông tin thực tế từ dữ liệu cho mỗi entity\n"
        f"2. So sánh rõ ràng giữa các entity\n"
        f"3. Đưa ra recommendation có căn cứ\n"
        f"4. Chỉ dùng thông tin có trong dữ liệu, KHÔNG bịa đặt\n"
        f"5. Trả lời bằng tiếng Việt, format markdown\n"
    )

    if on_status:
        await on_status("generate")

    try:
        llm = getattr(ctx, "llm", None) or getattr(ctx, "generator", None)
        answer_text = await llm.generate(comparison_prompt) if llm else ""
    except Exception:  # noqa: BLE001
        log.exception("comparison_llm_failed", trace_id=trace_id)
        answer_text = ""

    if answer_text and answer_text.strip().startswith("{"):
        try:
            parsed_ans = _json.loads(answer_text)
            if isinstance(parsed_ans, dict) and "answer" in parsed_ans:
                answer_text = str(parsed_ans["answer"])
        except Exception:
            pass

    if not answer_text or not answer_text.strip():
        answer_text = deterministic_comparison(entity_details, compare_aspects)

    answer_text = mask_secrets(answer_text)

    # Record evidence for each entity
    if hasattr(ctx, "evidence") and ctx.evidence is not None:
        for ent in resolved_entities:
            await ctx.evidence.record_active_entities(
                uid=user_ctx.user_id if user_ctx else "anonymous",
                cid=cid,
                results=[],
                question=query,
                extra=[{
                    "name": ent["resolved_name"],
                    "urn": ent["urn"],
                    "entity_type": ent["entity_type"],
                }],
            )

    return ChatResponse(
        answer=answer_text,
        intent="COMPARISON",
        confidence="high",
        ambiguous=len(resolved_entities) < 2,
        insufficient_context=bool(failed_entities),
        trace_id=trace_id,
        conversation_id=cid,
        entities=[
            EntityItem(
                urn=ent["urn"],
                name=ent["resolved_name"],
                url=f"https://datahub.vinfastauto.com/dataset/{ent['urn']}",
            )
            for ent in resolved_entities
        ],
    )
