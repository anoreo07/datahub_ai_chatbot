import time
from collections import defaultdict
from dataclasses import dataclass, field

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import ConversationHistory

log = structlog.get_logger()


@dataclass
class Turn:
    question: str
    answer: str
    timestamp: float = 0.0


@dataclass
class Conversation:
    user_id: str
    conversation_id: str
    turns: list[Turn] = field(default_factory=list)
    created_at: float = 0.0
    last_accessed: float = 0.0


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
        self.add_turn(user_id, conversation_id, question, answer)
        try:
            db_entry = ConversationHistory(
                user_id=user_id,
                conversation_id=conversation_id,
                question=question,
                answer=answer,
            )
            session.add(db_entry)
            await session.commit()
        except Exception:
            log.exception("conversation_save_failed", user_id=user_id, conversation_id=conversation_id)

    def get_history(self, user_id: str, conversation_id: str, last_k: int = 5) -> list[tuple[str, str]]:
        conv = self.get_or_create(user_id, conversation_id)
        recent = conv.turns[-last_k:] if conv.turns else []
        return [(t.question, t.answer) for t in recent]

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
                log.exception("conversation_load_failed", user_id=user_id, conversation_id=conversation_id)
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
                })
        return result

    async def list_conversations_from_db(self, session: AsyncSession, user_id: str) -> list[dict]:
        in_memory = self.list_conversations(user_id)
        seen_ids = {c["conversation_id"] for c in in_memory}
        try:
            from sqlalchemy import select as sa_select, func as sa_func
            result = await session.execute(
                sa_select(
                    ConversationHistory.conversation_id,
                    sa_func.count(ConversationHistory.id).label("turn_count"),
                    sa_func.max(ConversationHistory.created_at).label("last_accessed"),
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
                    })
                    seen_ids.add(cid)
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
