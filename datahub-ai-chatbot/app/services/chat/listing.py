import re

import structlog

from app.auth.models import UserContext
from app.schemas.chat import ChatResponse, EntityItem
from app.services.chat.context import ChatContext
from app.services.chat.question_analysis import (
    _ANAPHORA_WORDS,
    _DIMENSION_MAP,
    _DOMAIN_LISTING_RE,
    _ENTITY_TYPE_LABELS,
    _detect_entity_type,
    _entity_payload_to_text,
    _extract_filter_value,
    _scope_text,
)
from guardrails.sanitizer import mask_secrets
from retrieval.hybrid_search import SearchResult
from retrieval.intent import QueryIntent, _norm_vn

log = structlog.get_logger()


class ListingService:
    """ListingService."""

    def __init__(self, ctx: ChatContext) -> None:
        self._ctx = ctx


    async def deterministic_listing(self, question: str, intent: QueryIntent,
                                     user_ctx: UserContext, trace_id: str,
                                     conversation_id: str,
                                     suggested_name: str | None = None) -> ChatResponse | None:
        entity_type = _detect_entity_type(question)
        label = _ENTITY_TYPE_LABELS.get(entity_type, "assets")

        if intent == QueryIntent.DOMAIN_QUERY and _DOMAIN_LISTING_RE.search(question):
            all_entities = await self._ctx.entity_repo.list_all(limit=2000)
            if self._ctx.auth_service:
                accessible = await self._ctx.auth_service.filter_accessible_urns(
                    user_ctx, [e.urn for e in all_entities]
                )
                all_entities = [e for e in all_entities if e.urn in accessible]
            counts: dict[str, int] = {}
            for e in all_entities:
                domain = (e.domain or (e.payload or {}).get("domain") or "").strip()
                if domain:
                    counts[domain] = counts.get(domain, 0) + 1
            is_count = bool(re.search(
                r"(có bao nhiêu|co bao nhieu|bao nhiêu|how many|số lượng|so luong)",
                question, re.I))
            if is_count:
                answer_text = f"Có tổng cộng {len(counts)} domain trong hệ thống."
            else:
                lines = [f"Có tổng cộng {len(counts)} domain trong hệ thống:"]
                for d, c in sorted(counts.items(), key=lambda kv: (-kv[1], _norm_vn(kv[0]))):
                    lines.append(f"- {d} ({c} assets)")
                answer_text = mask_secrets("\n".join(lines))
            log.info("route_domain_listing", trace_id=trace_id, question=question[:100],
                     domain_count=len(counts), source="deterministic_db")
            return ChatResponse(
                answer=answer_text, intent="DOMAIN_QUERY", entities=[],
                confidence="high", ambiguous=False, insufficient_context=False,
                trace_id=trace_id, conversation_id=conversation_id,
            )

        if intent == QueryIntent.CERTIFIED_LIST:
            entities = await self._ctx.entity_repo.list_certified(entity_type)
            dimension, value = "certified", ""
        else:
            dimension, value = "", ""
            for try_intent in (QueryIntent.DOMAIN_QUERY, QueryIntent.TAG_QUERY,
                               QueryIntent.ENTITIES_BY_OWNER, QueryIntent.PLATFORM_QUERY):
                v = _extract_filter_value(question, try_intent)
                if v:
                    if v in _ANAPHORA_WORDS:
                        return None
                    dimension = _DIMENSION_MAP[try_intent]
                    value = v
                    break
            if suggested_name and dimension == "domain":
                value = suggested_name
            if dimension == "domain" and value and self._ctx.auth_service:
                denied = await self._ctx.auth_service.access_message(user_ctx, value)
                if denied:
                    log.info("chat_domain_denied", trace_id=trace_id,
                             user=user_ctx.user_id, domain=value)
                    return ChatResponse(
                        answer=denied, intent="DOMAIN_QUERY", entities=[],
                        confidence="high", ambiguous=False,
                        insufficient_context=False, trace_id=trace_id,
                        conversation_id=conversation_id,
                    )
            if dimension == "domain":
                entities = await self._ctx.entity_repo.list_by_domain(value, entity_type)
            elif dimension == "platform":
                entities = await self._ctx.entity_repo.list_by_platform(value, entity_type)
            elif dimension == "tag":
                entities = await self._ctx.entity_repo.list_by_tag(value, entity_type)
            elif dimension == "owner":
                entities = await self._ctx.entity_repo.list_by_owner(value, entity_type)
            elif entity_type:
                entities = await self._ctx.entity_repo.list_by_type(entity_type, limit=500)
            else:
                entities = await self._ctx.entity_repo.list_all(limit=500)

            if (dimension == "domain" and not entities and not suggested_name
                    and intent != QueryIntent.CERTIFIED_LIST):
                suggestion = await self._ctx.entities.suggest_entity(
                    value, None, question, trace_id,
                )
                if suggestion is not None:
                    answer_text = (
                        f"'{suggestion.original}' không tồn tại trong hệ thống. "
                        f"Ý bạn là '{suggestion.suggested}'?"
                    )
                    log.info("chat_suggestion", trace_id=trace_id, intent=intent.value,
                             original=suggestion.original, suggested=suggestion.suggested,
                             conversation_id=conversation_id)
                    return ChatResponse(
                        answer=answer_text, intent=intent.value, confidence="high",
                        ambiguous=False, insufficient_context=False,
                        trace_id=trace_id, conversation_id=conversation_id,
                        suggestion=suggestion,
                    )

        if self._ctx.auth_service:
            accessible = await self._ctx.auth_service.filter_accessible_urns(
                user_ctx, [e.urn for e in entities]
            )
            entities = [e for e in entities if e.urn in accessible]

        count = len(entities)
        scope = _scope_text(dimension, value, entities)
        lines = [f"Có tổng cộng {count} {label}{scope}."]

        platforms: dict[str, list[str]] = {}
        for e in entities:
            p = e.platform or "unknown"
            platforms.setdefault(p, []).append(e.display_name or e.name)
        for plat, names in sorted(platforms.items()):
            sample = sorted(names)
            shown = ", ".join(sample[:50])
            lines.append(f"\n{plat}: {shown}{', ...' if len(sample) > 50 else ''}")
        answer_text = mask_secrets("\n".join(lines))

        entity_list = [
            EntityItem(urn=e.urn, name=e.display_name or e.name, url=e.datahub_url)
            for e in entities[:200]
        ]

        return ChatResponse(
            answer=answer_text, intent=intent.value, entities=entity_list,
            confidence="high", ambiguous=False, insufficient_context=False,
            trace_id=trace_id, conversation_id=conversation_id,
        )


    async def listing_retrieval(self, entity_type: str) -> list[SearchResult]:
        count = await self._ctx.entity_repo.count_by_type(entity_type)
        entities = await self._ctx.entity_repo.list_by_type(entity_type, limit=200)
        platforms: dict[str, list[str]] = {}
        for e in entities:
            p = e.platform or "unknown"
            platforms.setdefault(p, []).append(e.display_name or e.name)
        summary_parts = [f"Có tổng cộng {count} {entity_type} trong hệ thống."]
        if platforms:
            summary_parts.append(f"Platforms: {', '.join(sorted(platforms.keys()))}.")
            for plat, names in sorted(platforms.items()):
                summary_parts.append(
                    f"- {plat}: {', '.join(sorted(names)[:30])}"
                    f"{'...' if len(names) > 30 else ''}"
                )
        summary_text = "\n".join(summary_parts)
        results: list[SearchResult] = []
        for e in entities[:20]:
            payload = e.payload or {}
            content = _entity_payload_to_text(e.entity_type, payload)
            results.append(SearchResult(
                urn=e.urn, entity_type=e.entity_type,
                name=e.display_name or e.name,
                score=1.0, datahub_url=e.datahub_url,
                payload={**payload, "content": content},
            ))
        if results:
            results[0].payload["content"] = (
                summary_text + "\n\n" + results[0].payload.get("content", "")
            )
        return results
