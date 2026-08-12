"""Vision Service — orchestrate the vision model call + vision cache + enrichment.

Runs the underlying :class:`VisualUnderstandingSkill` against a single image,
consults the vision cache first (by content hash) so identical images never
re-hit the model, and optionally enriches the detected dataset against DataHub
metadata (domain, owner, description, platform, glossary).
"""

from __future__ import annotations

from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.vision_cache import VisionCache
from config.settings import settings
from retrieval.entity_resolver import EntityResolver
from retrieval.visual import VisualUnderstandingSkill

log = structlog.get_logger()


class VisionService:
    def __init__(self, session: AsyncSession,
                 client: Any | None = None,
                 skill: VisualUnderstandingSkill | None = None) -> None:
        self._session = session
        self._cache = VisionCache(session)
        self._skill = skill or VisualUnderstandingSkill(session, client=client)
        self._resolver = EntityResolver(session)

    async def analyze(
        self,
        content_hash: str,
        data_url: str,
        image_text_hint: str = "",
        *,
        use_cache: bool = True,
        cache_model_id: str | None = None,
    ) -> dict[str, Any]:
        """Analyze one image (data URL) and return a normalised vision dict.

        Uses the vision cache when the content hash matches a previous analysis
        and ``use_cache`` is true (the default). The returned dict mirrors the
        VisionResult contract plus ``image_id``-agnostic keys.
        """
        model_id = cache_model_id or settings.FIREWORKS_VISION_MODEL_ID
        cached = None
        if use_cache:
            cached = await self._cache.get(content_hash)
        if cached and cached.get("vision_result"):
            log.info("vision_cache_hit", content_hash=content_hash[:12],
                     cache_id=cached.get("cache_id"))
            return dict(cached["vision_result"])

        log.info("vision_cache_miss", content_hash=content_hash[:12])
        result = await self._skill.analyze(data_url, image_text_hint)
        payload = result.to_dict()

        await self._cache.put(
            content_hash,
            model_id=model_id,
            vision_result=payload,
            image_context=None,
        )
        return payload

    async def enrich_dataset(self, dataset_name: str) -> dict[str, Any]:
        """Resolve a dataset name against DataHub metadata (best-effort)."""
        if not dataset_name:
            return {}
        try:
            resolution = await self._resolver.resolve(dataset_name)
        except Exception:  # noqa: BLE001
            log.exception("vision_dataset_resolve_failed", name=dataset_name)
            return {}
        best = resolution.resolved or (
            resolution.candidates[0] if resolution.candidates else None
        )
        if best is None:
            return {"dataset_name": dataset_name}
        from database.repositories.entity_repository import EntityRepository

        repo = EntityRepository(self._session)
        entity = await repo.get_by_urn(best.urn)
        payload = entity.payload or {} if entity else {}
        entity_desc = entity.description if entity else None
        return {
            "dataset_name": best.name,
            "dataset_urn": best.urn,
            "domain": (payload.get("domain") or "").strip() or None,
            "owner": (payload.get("owner") or "").strip() or None,
            "description": (payload.get("description") or entity_desc or "").strip() or None,
            "platform": (payload.get("platform") or "").strip() or None,
            "datahub_url": best.datahub_url,
        }
