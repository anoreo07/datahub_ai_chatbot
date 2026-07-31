from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.auth.authorization import AuthorizationService
from app.auth.models import UserContext
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService
from database.session import get_session

router = APIRouter()


@router.post("")
async def chat(
    request: ChatRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserContext = Depends(get_current_user),
) -> ChatResponse:
    auth_service = AuthorizationService(session=session)
    service = ChatService(session, auth_service=auth_service)
    return await service.answer(request.question, user=current_user, conversation_id=request.conversation_id)
