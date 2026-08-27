"""Metadata listing execution flow."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

from app.auth.models import UserContext
from app.schemas.chat import ChatResponse, EntityItem
from guardrails.sanitizer import mask_secrets
from retrieval.metadata_filter_engine import MetadataFilterEngine
from retrieval.metadata_query_parser import parse_metadata_query

if TYPE_CHECKING:
    from app.services.chat.context import ChatContext

log = structlog.get_logger()


async def try_metadata_listing(
    ctx: ChatContext,
    question: str,
    user_ctx: UserContext,
    trace_id: str,
    cid: str,
    postprocess_fn: Any,
    t_start: float = 0.0,
) -> ChatResponse | None:
    """Try to parse and execute a generic metadata listing query."""
    mq = parse_metadata_query(question)
    if mq is None:
        return None

    log.info(
        "metadata_listing_detected",
        trace_id=trace_id,
        query=mq.to_dict(),
        message=question[:100],
    )

    engine = MetadataFilterEngine(ctx.session)
    result = await engine.execute(mq)

    # Apply RBAC filtering
    if ctx.auth_service:
        entities = await ctx.auth_service.filter_entities_by_domain(
            user_ctx, result.entities
        )
        accessible = await ctx.auth_service.filter_accessible_urns(
            user_ctx, [e.urn for e in entities]
        )
        result.entities = [e for e in entities if e.urn in accessible]
        result.returned_count = len(result.entities)

    answer_text = mask_secrets(result.to_answer_text())

    entity_list = [
        EntityItem(
            urn=e.urn,
            name=e.display_name or e.name,
            url=e.datahub_url,
            entity_type=e.entity_type,
            platform=e.platform,
            domain=e.domain,
            description=e.description,
            environment=e.environment,
        )
        for e in result.entities
    ]

    await ctx.memory.add_turn_db(
        ctx.session, user_ctx.user_id, cid, question, answer_text
    )

    res = ChatResponse(
        answer=answer_text,
        intent="METADATA_LISTING",
        entities=entity_list,
        confidence="high",
        ambiguous=False,
        insufficient_context=False,
        trace_id=trace_id,
        conversation_id=cid,
    )
    return await postprocess_fn(res, t_start, user_ctx.user_id, cid, question)
