import asyncio
import json
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.auth.authorization import AuthorizationService
from app.auth.models import UserContext
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService
from database.session import get_session
from llm.registry import available_models

router = APIRouter()


@router.get("/models")
async def list_models(
    current_user: UserContext = Depends(get_current_user),
) -> dict[str, list[dict[str, str]]]:
    """Models selectable from the chat model selector."""
    return {"models": [m.__dict__ for m in available_models()]}


@router.post("")
async def chat(
    request: ChatRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserContext = Depends(get_current_user),
) -> ChatResponse:
    auth_service = AuthorizationService(session=session)
    service = ChatService(session, auth_service=auth_service)
    return await service.answer(request.question, user=current_user,
                                conversation_id=request.conversation_id,
                                suggested_name=request.suggested_name,
                                model=request.model,
                                selected_action=request.selected_action,
                                images=request.images)


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserContext = Depends(get_current_user),
) -> StreamingResponse:
    auth_service = AuthorizationService(session=session)
    service = ChatService(session, auth_service=auth_service)

    async def _sse(event: str, data: dict[str, object]) -> str:
        return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    async def event_gen() -> AsyncGenerator[str, None]:
        queue: asyncio.Queue[str | None] = asyncio.Queue()

        async def on_status(step: str) -> None:
            await queue.put(await _sse("status", {"step": step}))

        async def on_token(text: str) -> None:
            await queue.put(await _sse("token", {"text": text}))

        async def produce() -> None:
            try:
                response = await service.answer(
                    request.question, user=current_user,
                    conversation_id=request.conversation_id,
                    suggested_name=request.suggested_name,
                    model=request.model,
                    selected_action=request.selected_action,
                    images=request.images,
                    on_status=on_status,
                    on_token=on_token,
                )
            except Exception as exc:  # noqa: BLE001
                from guardrails.sanitizer import mask_secrets
                await queue.put(await _sse("error", {"detail": mask_secrets(str(exc))}))
            else:
                await queue.put(await _sse("done", response.model_dump(mode="json")))
            finally:
                await queue.put(None)

        task = asyncio.create_task(produce())
        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                yield item
        finally:
            await task

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
