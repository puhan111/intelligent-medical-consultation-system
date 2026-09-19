"""
报告追问对话服务

复用分诊对话的架构：Redis 会话、RAG 检索医学参考资料、LLM 生成、内容审核。
关键差异：prompt 注入报告的原始指标数值 + 已生成的解读，确保口径一致。
"""
import json
import logging
import uuid
from typing import AsyncIterator, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import status

from app.models.report import Report
from app.services.common import rag_service, llm_service
from app.services.common.redis import redis_client
from app.services.common.content_review import review_content
from app.services.common.prompt_loader import load_prompt
from app.exceptions.http_exceptions import APIException

logger = logging.getLogger("report_chat")

CONV_KEY_PREFIX = "report_chat:conversation"
CONV_MAX_MESSAGES = 16  # 最多保留最近 8 轮问答
CONV_EXPIRE = 3600  # 对话历史保留 1 小时


async def get_conversation_history(session_id: str) -> list[dict]:
    """从 Redis 读取对话历史（LPUSH 头插，返回的是倒序）"""
    key = f"{CONV_KEY_PREFIX}:{session_id}"
    raw = await redis_client.redis.lrange(key, 0, CONV_MAX_MESSAGES - 1)
    return [json.loads(msg) for msg in raw]


async def save_turn(session_id: str, user_msg: str, ai_msg: str) -> None:
    """保存一轮问答并刷新过期时间"""
    key = f"{CONV_KEY_PREFIX}:{session_id}"
    await redis_client.redis.lpush(
        key, json.dumps({"role": "assistant", "content": ai_msg}, ensure_ascii=False)
    )
    await redis_client.redis.lpush(
        key, json.dumps({"role": "user", "content": user_msg}, ensure_ascii=False)
    )
    await redis_client.redis.ltrim(key, 0, CONV_MAX_MESSAGES - 1)
    await redis_client.redis.expire(key, CONV_EXPIRE)


async def chat(
    db: AsyncSession,
    patient_id: int,
    report_id: int,
    user_message: str,
    session_id: Optional[str] = None,
) -> tuple[str, str, int]:
    """
    就某份报告进行多轮追问

    Returns:
        (session_id, 助手回复, 当前轮数)
    """
    # 验证报告归属
    report = (
        await db.execute(
            select(Report).where(Report.id == report_id, Report.patient_id == patient_id)
        )
    ).scalar_one_or_none()

    if not report:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Report not found or access denied",
        )

    # 只允许对已解读完成的报告追问，否则 AI 没有基线可参照
    if report.interpretation_status != "completed":
        raise APIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=f"Cannot chat about report with interpretation status '{report.interpretation_status}'",
        )

    if not session_id:
        session_id = f"{patient_id}:{report_id}:{uuid.uuid4().hex[:8]}"

    history = await get_conversation_history(session_id)

    # RAG 检索医学参考资料
    search_query = f"{report.type} {user_message}"
    chunks = await rag_service.search(
        db,
        query=search_query,
        top_k=5,
        source_type="医学参考资料",
        agent_type="report_followup",
    )
    reference_texts = [c.content for c in chunks]

    # 拼装 prompt
    prompt = load_prompt(
        "report_followup",
        report_type=report.type,
        report_content=json.dumps(report.content, ensure_ascii=False, indent=2),
        ai_interpretation=report.ai_interpretation or "(本报告解读尚未完成)",
        conversation_history=list(reversed(history)),  # Redis lpush 是头插，取出后需反转
        user_message=user_message,
        reference_chunks=reference_texts,
    )

    # 调 LLM
    llm_result = await llm_service.call(db, prompt, agent_type="report_followup")
    reply = llm_result.content

    # 内容审核不通过时降级为固定文案，与分诊保持一致的处理方式
    passed, reason = review_content(reply)
    if not passed:
        logger.warning(
            f"Content review failed for report_chat: report_id={report_id} reason={reason}"
        )
        reply = "抱歉，本次回答未能通过内容审核。建议您携带报告咨询医生获得专业解读。仅供参考。"

    await save_turn(session_id, user_message, reply)

    turn_count = len(history) // 2 + 1

    return session_id, reply, turn_count


async def chat_stream(
    db: AsyncSession,
    patient_id: int,
    report_id: int,
    user_message: str,
    session_id: Optional[str] = None,
) -> AsyncIterator[dict]:
    """流式回答报告追问，并在完成后审核、保存本轮会话。"""
    report = (
        await db.execute(
            select(Report).where(Report.id == report_id, Report.patient_id == patient_id)
        )
    ).scalar_one_or_none()

    if not report:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Report not found or access denied",
        )
    if report.interpretation_status != "completed":
        raise APIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=f"Cannot chat about report with interpretation status '{report.interpretation_status}'",
        )

    if not session_id:
        session_id = f"{patient_id}:{report_id}:{uuid.uuid4().hex[:8]}"

    history = await get_conversation_history(session_id)
    chunks = await rag_service.search(
        db,
        query=f"{report.type} {user_message}",
        top_k=5,
        source_type="医学参考资料",
        agent_type="report_followup",
    )
    prompt = load_prompt(
        "report_followup",
        report_type=report.type,
        report_content=json.dumps(report.content, ensure_ascii=False, indent=2),
        ai_interpretation=report.ai_interpretation or "(本报告解读尚未完成)",
        conversation_history=list(reversed(history)),
        user_message=user_message,
        reference_chunks=[chunk.content for chunk in chunks],
    )

    turn_count = len(history) // 2 + 1
    yield {"type": "start", "session_id": session_id, "turn_count": turn_count}

    response_parts: list[str] = []
    async for text_delta in llm_service.stream(db, prompt, agent_type="report_followup"):
        response_parts.append(text_delta)
        yield {"type": "delta", "content": text_delta}

    reply = "".join(response_parts)
    passed, reason = review_content(reply)
    if not passed:
        logger.warning(
            "Content review failed for report_chat stream: report_id=%s reason=%s",
            report_id,
            reason,
        )
        reply = "抱歉，本次回答未能通过内容审核。建议您携带报告咨询医生获得专业解读。仅供参考。"
        yield {"type": "replace", "content": reply}

    await save_turn(session_id, user_message, reply)
    yield {"type": "done", "session_id": session_id, "turn_count": turn_count}
