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


    async def domain_constrained_discovery(self, question: str, trace_id: str,
                                           conversation_id: str) -> ChatResponse | None:
        """'chỉ nêu báo cáo thuộc domain X về keyword1 hoặc keyword2' -> list
        datasets inside domain X whose name matches the keywords. Surfaces the
        domain so the answer never leaks datasets from other domains."""
        q = _norm_vn(question)
        if not re.search(r"chi\s+(?:neu|liet ke|cho|de cap)", q):
            return None
        if "domain" not in q:
            return None
        kw_m = re.search(r"\bve\s+([^.!?]+)$", q)
        if not kw_m:
            return None
        keywords = [
            k.strip() for k in re.split(r"\s+(?:hoặc|hoac|và|va|hay)\s*|\s*[,;]\s*", kw_m.group(1))
            if k.strip()
        ]
        keywords = [k for k in keywords if not re.search(r"chỉ|nêu|cho|thuộc", k)]
        if not keywords:
            return None
        if self._ctx.access is None:
            return None
        domains = await self._ctx.access.detect_requested_domains(question)
        if not domains:
            return None
        domain = domains[0]
        try:
            entities = await self._ctx.entity_repo.list_by_domain(domain)
        except Exception:  # noqa: BLE001
            return None
        matched = [
            e for e in entities
            if any(k in _norm_vn(e.name or "") for k in keywords)
        ]
        if not matched:
            return None
        entity_list = []
        seen_urns: set[str] = set()
        for e in matched:
            if e.urn in seen_urns:
                continue
            seen_urns.add(e.urn)
            entity_list.append(
                EntityItem(urn=e.urn, name=e.display_name or e.name, url=e.datahub_url)
            )
            if len(entity_list) >= 50:
                break
        names = sorted({(e.display_name or e.name) for e in matched})
        answer_text = (
            f"Các báo cáo thuộc domain **{domain}** liên quan đến "
            f"{' / '.join(keywords)}: {', '.join(names)}."
        )
        log.info("route_domain_constrained_discovery", trace_id=trace_id,
                 domain=domain, keywords=keywords, matches=len(names))
        return ChatResponse(
            answer=answer_text, intent="GENERAL", entities=entity_list,
            confidence="high", ambiguous=False, insufficient_context=False,
            trace_id=trace_id, conversation_id=conversation_id,
        )

    async def deterministic_listing(self, question: str, intent: QueryIntent,
                                     user_ctx: UserContext, trace_id: str,
                                     conversation_id: str,
                                     suggested_name: str | None = None) -> ChatResponse | None:
        entity_type = _detect_entity_type(question)
        label = _ENTITY_TYPE_LABELS.get(entity_type, "assets")

        if intent == QueryIntent.DOMAIN_QUERY and _DOMAIN_LISTING_RE.search(question):
            all_entities = await self._ctx.entity_repo.list_all()
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
            # Global count phrasings ("tính tổng số dataset ...", "tổng số
            # dashboard ...") count the whole entity type, never a dimension
            # extracted from a trailing clause ("trên nền tảng của chúng ta",
            # "của chúng ta" would otherwise be misread as an owner filter).
            has_explicit_filter = any(
                bool(_extract_filter_value(question, ti))
                for ti in (QueryIntent.DOMAIN_QUERY, QueryIntent.TAG_QUERY,
                           QueryIntent.ENTITIES_BY_OWNER, QueryIntent.PLATFORM_QUERY)
            )
            global_count = (
                intent == QueryIntent.COUNT_ENTITIES
                and not has_explicit_filter
                and bool(re.search(
                    r"(tính tổng số|tinh tong so|tổng số|tong so|tổng cộng|tong cong)",
                    question, re.I,
                ))
            )
            # Count-with-exact-name ("có bao nhiêu dataset tên 'stas'?"): the
            # quoted name is the whole scope. Answer with the datasets whose
            # NAME equals that name (across platforms / containers) instead of
            # counting the entire entity type.
            quoted = re.search(
                r"""["“”‘’']\s*([A-Za-z0-9_\.\-]+)\s*["“”‘’']""",
                question,
            )
            exact_name_scope = (
                intent == QueryIntent.COUNT_ENTITIES
                and quoted is not None
                and bool(re.search(
                    r"(tên|ten\b|named|name)\s*(là|la|:|['\"])?|tên\s+['\"“”]",
                    question, re.I,
                ))
            )
            dimension, value = "", ""
            if exact_name_scope:
                qname = quoted.group(1)
                if entity_type:
                    name_matches = await self._ctx.entity_repo.search_by_name(
                        qname, entity_type)
                else:
                    name_matches = await self._ctx.entity_repo.search_by_name(qname)
                entities = [
                    e for e in name_matches
                    if e.entity_type == "dataset"
                    and (e.display_name or e.name or "").lower() == qname.lower()
                ]
                dimension, value = "name", qname
            elif not global_count:
                for try_intent in (QueryIntent.DOMAIN_QUERY, QueryIntent.TAG_QUERY,
                                   QueryIntent.ENTITIES_BY_OWNER, QueryIntent.PLATFORM_QUERY):
                    v = _extract_filter_value(question, try_intent)
                    if v:
                        if v in _ANAPHORA_WORDS:
                            return None
                        dimension = _DIMENSION_MAP[try_intent]
                        value = v
                        break
            if dimension == "domain" and value:
                from app.services.chat.question_analysis import _DOMAINS_MAP
                norm_v = _norm_vn(value)
                if norm_v in _DOMAINS_MAP:
                    value = _DOMAINS_MAP[norm_v]
                elif any(k in norm_v for k in _DOMAINS_MAP):
                    for k, v_dom in _DOMAINS_MAP.items():
                        if k in norm_v:
                            value = v_dom
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
            elif dimension == "name":
                pass
            elif entity_type:
                entities = await self._ctx.entity_repo.list_by_type(entity_type)
            else:
                entities = await self._ctx.entity_repo.list_all()

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

        sub_platform = None
        if dimension == "domain":
            _known_platforms = {"sap", "powerbi", "mes", "redshift", "glue", "dms", "excel", "jira", "ignition", "tfs", "sq"}
            for p in sorted(_known_platforms, key=len, reverse=True):
                if re.search(rf"\b{p}\b", question, re.I):
                    sub_platform = p
                    break

        if sub_platform:
            filtered_entities = [
                e for e in entities
                if (e.platform or "").strip().lower() == sub_platform.lower()
            ]
            lines = [
                f"Có tổng cộng {count} {label}{scope}.",
                f"Trong đó, có {len(filtered_entities)} dataset thuộc nền tảng **{sub_platform.upper()}**:\n",
            ]
            for e in filtered_entities:
                lines.append(f"- {e.display_name or e.name}")
            answer_text = mask_secrets("\n".join(lines).strip())
            entity_list = [
                EntityItem(urn=e.urn, name=e.display_name or e.name, url=e.datahub_url)
                for e in filtered_entities
            ]
            return ChatResponse(
                answer=answer_text, intent=intent.value, entities=entity_list,
                confidence="high", ambiguous=False, insufficient_context=False,
                trace_id=trace_id, conversation_id=conversation_id,
            )

        lines = [f"Có tổng cộng {count} {label}{scope}."]

        platforms: dict[str, list[str]] = {}
        for e in entities:
            p = e.platform or "unknown"
            platforms.setdefault(p, []).append(e.display_name or e.name)
        # Same-name count across platforms ("có bao nhiêu dataset tên
        # 'DIM_PACKED'?"): the name alone does not identify one dataset — say
        # so explicitly and break the total down by platform, because only the
        # platform (plus URN/container) tells the copies apart.
        if exact_name_scope and count > 1:
            plat_names = "các platform khác nhau" if len(platforms) > 1 else "nhiều URN"
            if value:
                lines = [(
                    f"Tồn tại {count} dataset trùng tên '{value}' trên "
                    f"{plat_names}. Phải nêu rõ platform để phân biệt."
                )]
        for plat, names in sorted(platforms.items()):
            sample = sorted(names)
            lines.append(f"**{plat}:**")
            for name in sample:
                lines.append(f"- {name}")
            lines.append("")
        answer_text = mask_secrets("\n".join(lines))

        entity_list = [
            EntityItem(urn=e.urn, name=e.display_name or e.name, url=e.datahub_url)
            for e in entities
        ]

        return ChatResponse(
            answer=answer_text, intent=intent.value, entities=entity_list,
            confidence="high", ambiguous=False, insufficient_context=False,
            trace_id=trace_id, conversation_id=conversation_id,
        )


    async def listing_retrieval(self, entity_type: str) -> list[SearchResult]:
        count = await self._ctx.entity_repo.count_by_type(entity_type)
        entities = await self._ctx.entity_repo.list_by_type(entity_type)
        platforms: dict[str, list[str]] = {}
        for e in entities:
            p = e.platform or "unknown"
            platforms.setdefault(p, []).append(e.display_name or e.name)
        summary_parts = [f"Có tổng cộng {count} {entity_type} trong hệ thống."]
        if platforms:
            summary_parts.append(f"Platforms: {', '.join(sorted(platforms.keys()))}.")
            for plat, names in sorted(platforms.items()):
                summary_parts.append(
                    f"- {plat}: {', '.join(sorted(names))}"
                )
        summary_text = "\n".join(summary_parts)
        results: list[SearchResult] = []
        for e in entities:
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
