from fastapi import APIRouter, Depends
from sqlalchemy import delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.auth.models import UserContext
from app.services.conversation import get_conversation_memory
from database.models import ConversationHistory
from database.session import get_session

router = APIRouter()


@router.get("")
async def list_conversations(
    current_user: UserContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    memory = get_conversation_memory()
    convs = await memory.list_conversations_from_db(session, current_user.user_id)
    return {"conversations": convs}


@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    current_user: UserContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    memory = get_conversation_memory()
    turns = await memory.get_conversation_detail(session, current_user.user_id, conversation_id)
    return {
        "conversation_id": conversation_id,
        "turns": turns,
    }


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: UserContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    uid = current_user.user_id
    stmt = sa_delete(ConversationHistory).where(
        ConversationHistory.user_id == uid,
        ConversationHistory.conversation_id == conversation_id,
    )
    await session.execute(stmt)
    await session.commit()

    memory = get_conversation_memory()
    memory._conversations.pop(f"{uid}::{conversation_id}", None)

    return {"status": "deleted", "conversation_id": conversation_id}


@router.delete("")
async def clear_conversations(
    current_user: UserContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Delete all of the current user's chat history."""
    uid = current_user.user_id
    stmt = sa_delete(ConversationHistory).where(ConversationHistory.user_id == uid)
    await session.execute(stmt)
    await session.commit()

    memory = get_conversation_memory()
    prefix = f"{uid}::"
    memory._conversations = {
        key: conv
        for key, conv in memory._conversations.items()
        if not key.startswith(prefix)
    }

    return {"status": "deleted", "user_id": uid}
