import json
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.client.report import ReportChatRequest, ReportChatResponse, ReportResponse
from app.services.client.report import report_service
from app.services.client import report_chat
from app.api.client.deps import get_current_user
from app.models.user import User
from app.schemas.response import ApiResponse
from app.schemas.paginator import Paginator
from app.exceptions.http_exceptions import APIException


router = APIRouter()
logger = logging.getLogger("report_chat")


@router.get("", response_model=list[ReportResponse])
async def list_my_reports(
    page: int = 1,
    per_page: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取我的报告列表（含 AI 解读，分页）"""
    query = await report_service.get_my_reports_query(db, current_user.id)

    paginator = Paginator(query, db)
    result = await paginator.paginate(page, per_page)
    response_items = await report_service.list_reports(db, result.items)

    return ApiResponse.success(data={
        "items": response_items,
        "total": result.total,
        "per_page": result.per_page,
        "current_page": result.current_page,
        "last_page": result.last_page,
        "has_more": result.has_more
    })


@router.post("/{report_id}/chat", response_model=ReportChatResponse)
async def chat_about_report(
    report_id: int,
    request: ReportChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    就某份已解读完成的报告多轮追问

    首轮不传 session_id，后续轮次携带返回的 session_id 以保持上下文。
    """
    session_id, reply, turn_count = await report_chat.chat(
        db=db,
        patient_id=current_user.id,
        report_id=report_id,
        user_message=request.message,
        session_id=request.session_id,
    )

    return ApiResponse.success(data={
        "session_id": session_id,
        "message": reply,
        "turn_count": turn_count,
    })


@router.post("/{report_id}/chat/stream")
async def chat_about_report_stream(
    report_id: int,
    request: ReportChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """流式回答报告追问，使用 NDJSON 逐行返回事件。"""

    async def event_stream():
        try:
            async for event in report_chat.chat_stream(
                db=db,
                patient_id=current_user.id,
                report_id=report_id,
                user_message=request.message,
                session_id=request.session_id,
            ):
                yield json.dumps(event, ensure_ascii=False) + "\n"
        except APIException as exc:
            yield json.dumps(
                {"type": "error", "message": exc.detail}, ensure_ascii=False
            ) + "\n"
        except Exception:
            logger.exception(
                "Report chat stream failed for patient_id=%s report_id=%s",
                current_user.id,
                report_id,
            )
            yield json.dumps(
                {"type": "error", "message": "报告追问暂时不可用，请稍后重试。"},
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
