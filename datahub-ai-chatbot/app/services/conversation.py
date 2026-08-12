import time
from dataclasses import dataclass, field

import structlog
from sqlalchemy import select
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import ConversationHistory

log = structlog.get_logger()


@dataclass
class Turn:
    question: str
    answer: str
    timestamp: float = 0.0


@dataclass
class ActiveEntity:
    """A resolved entity the conversation currently refers to (for coreference).

    ``name`` is the canonical DataHub display name (e.g. ``3-Way Matching``),
    ``entity_type`` one of dataset/dashboard/glossary_term/document, and ``urn``
    the resolved URN when known. Storing the canonical name (not a raw token)
    is what lets follow-ups like ``"Nó thuộc lĩnh vực nào?"`` target the term
    the previous turn resolved, even when that name contains hyphens/spaces
    that no identifier regex can pick out of free text.
    """
    name: str
    entity_type: str | None = None
    urn: str | None = None


@dataclass
class Conversation:
    user_id: str
    conversation_id: str
    turns: list[Turn] = field(default_factory=list)
    active_entities: list[ActiveEntity] = field(default_factory=list)
    image_focus: ActiveEntity | None = None
    evidence: list[dict] = field(default_factory=list)
    created_at: float = 0.0
    last_accessed: float = 0.0
    title: str | None = None
    is_pinned: bool = False
    is_favorite: bool = False


class ConversationMemory:
    def __init__(self, ttl: int = 1800, max_turns: int = 20) -> None:
        self._conversations: dict[str, Conversation] = {}
        self._ttl = ttl
        self._max_turns = max_turns

    def _key(self, user_id: str, conversation_id: str) -> str:
        return f"{user_id}::{conversation_id}"

    def get_or_create(self, user_id: str, conversation_id: str) -> Conversation:
        now = time.time()
        self._expire(now)
        key = self._key(user_id, conversation_id)
        if key not in self._conversations:
            self._conversations[key] = Conversation(
                user_id=user_id,
                conversation_id=conversation_id,
                created_at=now,
                last_accessed=now,
            )
        conv = self._conversations[key]
        conv.last_accessed = now
        return conv

    def add_turn(self, user_id: str, conversation_id: str, question: str, answer: str) -> None:
        conv = self.get_or_create(user_id, conversation_id)
        conv.turns.append(Turn(question=question, answer=answer, timestamp=time.time()))
        if len(conv.turns) > self._max_turns:
            conv.turns = conv.turns[-self._max_turns:]

    async def add_turn_db(self, session: AsyncSession, user_id: str, conversation_id: str,
                          question: str, answer: str) -> None:
        conv = self.get_or_create(user_id, conversation_id)
        self.add_turn(user_id, conversation_id, question, answer)
        try:
            db_entry = ConversationHistory(
                user_id=user_id,
                conversation_id=conversation_id,
                question=question,
                answer=answer,
                title=conv.title,
                is_pinned=conv.is_pinned,
                is_favorite=conv.is_favorite,
            )
            session.add(db_entry)
            await session.commit()
        except Exception:
            log.exception(
                "conversation_save_failed",
                user_id=user_id, conversation_id=conversation_id,
            )

    def get_history(self, user_id: str, conversation_id: str,
                    last_k: int = 5) -> list[tuple[str, str]]:
        conv = self.get_or_create(user_id, conversation_id)
        recent = conv.turns[-last_k:] if conv.turns else []
        return [(t.question, t.answer) for t in recent]

    def record_active_entities(self, user_id: str, conversation_id: str,
                               entities: list[dict]) -> None:
        """Persist the entities this conversation last talked about (canonical)."""
        conv = self.get_or_create(user_id, conversation_id)
        clean: list[ActiveEntity] = []
        for e in entities or []:
            name = str((e or {}).get("name") or "").strip()
            if not name:
                continue
            clean.append(ActiveEntity(
                name=name,
                entity_type=str(e.get("entity_type") or "") or None,
                urn=str(e.get("urn") or "") or None,
            ))
        if clean:
            conv.active_entities = clean[-3:]

    def get_active_entities(self, user_id: str, conversation_id: str) -> list[dict]:
        conv = self.get_or_create(user_id, conversation_id)
        return [
            {"name": e.name, "entity_type": e.entity_type, "urn": e.urn}
            for e in conv.active_entities
        ]

    def set_image_focus(self, user_id: str, conversation_id: str,
                        name: str, urn: str | None = None) -> None:
        """Remember the dataset derived from the uploaded image.

        The image-derived dataset is the conversation's anaphora subject ("nó",
        "đó", ellipsis) until the user explicitly names a different catalog
        entity, so a topic switch ("có những document nào trong hệ thống?")
        does not silently drop the image entity before a follow-up like
        "lineage của nó?".
        """
        conv = self.get_or_create(user_id, conversation_id)
        conv.image_focus = ActiveEntity(
            name=name, entity_type="dataset", urn=urn,
        )

    def get_image_focus(self, user_id: str, conversation_id: str) -> dict[str, str | None] | None:
        conv = self.get_or_create(user_id, conversation_id)
        if conv.image_focus is None:
            return None
        return {
            "name": conv.image_focus.name,
            "entity_type": conv.image_focus.entity_type or "dataset",
            "urn": conv.image_focus.urn,
        }

    def clear_image_focus(self, user_id: str, conversation_id: str) -> None:
        """Explicitly named catalog entity supersedes the image-derived subject."""
        conv = self.get_or_create(user_id, conversation_id)
        conv.image_focus = None

    def record_evidence(self, user_id: str, conversation_id: str,
                        record: dict) -> None:
        """Persist a structured metadata extract (E1, E2, ...) for this turn.

        Evidence items are labelled sequentially with a stable citation id and
        capped so the follow-up resolver works on the recent window only.
        """
        conv = self.get_or_create(user_id, conversation_id)
        rec = dict(record or {})
        if not rec.get("evidence_id"):
            index = len(conv.evidence) + 1
            rec["evidence_id"] = f"E{index}"
        if not rec.get("citation"):
            rec["citation"] = rec.get("evidence_id")
        # Replaces an existing record with the same entity+kind (the most
        # recent fetch of the same metadata supersedes the older one) and
        # otherwise appends, keeping the sliding window bounded.
        replaced = False
        for i, existing in enumerate(conv.evidence):
            if (existing.get("entity_name") == rec.get("entity_name")
                    and existing.get("kind") == rec.get("kind")):
                rec["evidence_id"] = existing.get("evidence_id", rec["evidence_id"])
                rec["citation"] = existing.get("citation", rec["citation"])
                conv.evidence[i] = rec
                replaced = True
                break
        if not replaced:
            conv.evidence.append(rec)
        conv.evidence = conv.evidence[-8:]

    def get_evidence(self, user_id: str, conversation_id: str) -> list[dict]:
        conv = self.get_or_create(user_id, conversation_id)
        return list(conv.evidence)

    def clear_evidence(self, user_id: str, conversation_id: str) -> None:
        conv = self.get_or_create(user_id, conversation_id)
        conv.evidence.clear()

    async def load_history_from_db(self, session: AsyncSession, user_id: str,
                                   conversation_id: str, last_k: int = 5) -> list[tuple[str, str]]:
        """Load conversation history from DB into in-memory cache and return it."""
        conv = self.get_or_create(user_id, conversation_id)
        if not conv.turns:
            try:
                result = await session.execute(
                    select(ConversationHistory)
                    .where(
                        ConversationHistory.user_id == user_id,
                        ConversationHistory.conversation_id == conversation_id,
                    )
                    .order_by(ConversationHistory.created_at.asc())
                    .limit(last_k)
                )
                for row in result.scalars().all():
                    conv.turns.append(Turn(
                        question=row.question,
                        answer=row.answer,
                        timestamp=row.created_at.timestamp() if row.created_at else 0,
                    ))
            except Exception:
                log.exception(
                    "conversation_load_failed",
                    user_id=user_id, conversation_id=conversation_id,
                )
        return self.get_history(user_id, conversation_id, last_k)

    def list_conversations(self, user_id: str) -> list[dict]:
        now = time.time()
        self._expire(now)
        result = []
        prefix = f"{user_id}::"
        for key, conv in self._conversations.items():
            if key.startswith(prefix):
                result.append({
                    "conversation_id": conv.conversation_id,
                    "turn_count": len(conv.turns),
                    "last_question": conv.turns[-1].question if conv.turns else "",
                    "last_accessed": conv.last_accessed,
                    "title": conv.title,
                    "is_pinned": conv.is_pinned,
                    "is_favorite": conv.is_favorite,
                })
        return result

    async def list_conversations_from_db(self, session: AsyncSession, user_id: str) -> list[dict]:
        in_memory = self.list_conversations(user_id)
        seen_ids = {c["conversation_id"] for c in in_memory}
        try:
            from sqlalchemy import Integer as sa_Integer
            from sqlalchemy import cast as sa_cast
            from sqlalchemy import func as sa_func
            from sqlalchemy import select as sa_select
            pinned_max = sa_func.max(sa_cast(ConversationHistory.is_pinned, sa_Integer))
            favorite_max = sa_func.max(sa_cast(ConversationHistory.is_favorite, sa_Integer))
            result = await session.execute(
                sa_select(
                    ConversationHistory.conversation_id,
                    sa_func.count(ConversationHistory.id).label("turn_count"),
                    sa_func.max(ConversationHistory.created_at).label("last_accessed"),
                    sa_func.max(ConversationHistory.title).label("title"),
                    pinned_max.label("is_pinned"),
                    favorite_max.label("is_favorite"),
                )
                .where(ConversationHistory.user_id == user_id)
                .group_by(ConversationHistory.conversation_id)
                .order_by(sa_func.max(ConversationHistory.created_at).desc())
            )
            for row in result.all():
                cid = row[0]
                if cid not in seen_ids:
                    in_memory.append({
                        "conversation_id": cid,
                        "turn_count": row[1],
                        "last_question": "",
                        "last_accessed": row[2].timestamp() if row[2] else 0,
                        "title": row[3],
                        "is_pinned": bool(row[4]) if row[4] is not None else False,
                        "is_favorite": bool(row[5]) if row[5] is not None else False,
                    })
                    seen_ids.add(cid)
                else:
                    # Refresh in-memory meta for conversations we already know about
                    for conv in in_memory:
                        if conv["conversation_id"] == cid:
                            if row[3] is not None:
                                conv["title"] = row[3]
                            pinned_v = bool(row[4]) if row[4] is not None else conv["is_pinned"]
                            conv["is_pinned"] = pinned_v
                            fav_v = bool(row[5]) if row[5] is not None else conv["is_favorite"]
                            conv["is_favorite"] = fav_v
                            break
        except Exception:
            log.exception("conversation_list_db_failed", user_id=user_id)
        return in_memory

    async def get_conversation_detail(self, session: AsyncSession, user_id: str,
                                      conversation_id: str) -> list[dict]:
        turns = self.get_history(user_id, conversation_id, last_k=1000)
        if not turns:
            try:
                result = await session.execute(
                    select(ConversationHistory)
                    .where(
                        ConversationHistory.user_id == user_id,
                        ConversationHistory.conversation_id == conversation_id,
                    )
                    .order_by(ConversationHistory.created_at.asc())
                )
                for row in result.scalars().all():
                    turns.append((row.question, row.answer))
            except Exception:
                log.exception("conversation_detail_failed", user_id=user_id,
                              conversation_id=conversation_id)
        return [{"question": q, "answer": a} for q, a in turns]

    async def update_conversation_db(self, session: AsyncSession, user_id: str,
                                     conversation_id: str, title: str | None = None,
                                     is_pinned: bool | None = None,
                                     is_favorite: bool | None = None) -> dict:
        """Persist conversation metadata (title/pin/favorite) to DB and memory."""
        key = self._key(user_id, conversation_id)
        conv = self._conversations.get(key) or Conversation(
            user_id=user_id, conversation_id=conversation_id,
        )
        values: dict = {}
        if title is not None:
            conv.title = title.strip() or None
            values["title"] = conv.title
        if is_pinned is not None:
            conv.is_pinned = bool(is_pinned)
            values["is_pinned"] = conv.is_pinned
        if is_favorite is not None:
            conv.is_favorite = bool(is_favorite)
            values["is_favorite"] = conv.is_favorite
        self._conversations[key] = conv

        if values:
            try:
                await session.execute(
                    sa_update(ConversationHistory)
                    .where(
                        ConversationHistory.user_id == user_id,
                        ConversationHistory.conversation_id == conversation_id,
                    )
                    .values(**values)
                )
                await session.commit()
            except Exception:
                log.exception("conversation_meta_update_failed",
                              user_id=user_id, conversation_id=conversation_id)

        return {
            "conversation_id": conversation_id,
            "title": conv.title,
            "is_pinned": conv.is_pinned,
            "is_favorite": conv.is_favorite,
        }

    def _expire(self, now: float) -> None:
        expired = [key for key, conv in self._conversations.items()
                   if now - conv.last_accessed > self._ttl]
        for key in expired:
            del self._conversations[key]


_conversation_memory: ConversationMemory | None = None


def get_conversation_memory() -> ConversationMemory:
    global _conversation_memory
    if _conversation_memory is None:
        _conversation_memory = ConversationMemory()
    return _conversation_memory
