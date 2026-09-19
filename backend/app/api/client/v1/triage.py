import json
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.client.deps import get_current_user
from app.models.user import User
from app.schemas.response import ApiResponse
from app.schemas.client.triage import TriageChatRequest, TriageChatResponse
from app.exceptions.http_exceptions import APIException
from app.services.client.triage import chat as triage_chat, chat_stream as triage_chat_stream


router = APIRouter()
logger = logging.getLogger("triage")


@router.post("/chat", response_model=TriageChatResponse)
async def chat(
    request: TriageChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    预约分诊多轮对话

    患者描述症状，AI推荐挂号科室
    """
    session_id, ai_response, recommendations, turn_count = await triage_chat(
        db=db,
        user_id=current_user.id,
        message=request.message,
        session_id=request.session_id,
    )

    return ApiResponse.success(data={
        "session_id": session_id,
        "message": ai_response,
        "recommendations": recommendations,
        "turn_count": turn_count,
    })


@router.post("/chat/stream")
async def chat_stream(
    request: TriageChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """预约分诊流式对话，使用 NDJSON 逐行返回事件。"""

    async def event_stream():
        try:
            async for event in triage_chat_stream(
                db=db,
                user_id=current_user.id,
                message=request.message,
                session_id=request.session_id,
            ):
                yield json.dumps(event, ensure_ascii=False) + "\n"
        except APIException as exc:
            yield json.dumps({"type": "error", "message": exc.detail}, ensure_ascii=False) + "\n"
        except Exception:
            logger.exception(
                "Triage stream failed for user_id=%s",
                current_user.id,
            )
            yield json.dumps(
                {"type": "error", "message": "智能分诊暂时不可用，请稍后重试。"},
                ensure_ascii=False,
            ) + "\n"

    return StreamingResponse(
        event_stream(),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
