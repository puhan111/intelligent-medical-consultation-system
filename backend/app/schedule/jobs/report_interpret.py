import asyncio
import json
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.celery_app import celery_app
from app.db.base import create_scheduler_engine, create_scheduler_session_factory
from app.exceptions.http_exceptions import LLMServiceError
from app.models.report import Report
from app.services.common import llm_service, rag_service
from app.services.common.content_review import review_content
from app.services.common.prompt_loader import load_prompt
from app.services.common.redis import redis_client

logger = logging.getLogger("report_interpret")


@celery_app.task(name="app.schedule.jobs.report_interpret.execute")
def execute(report_id: int):
    """报告解读任务：RAG 检索医学资料 -> 调用 LLM 生成解读 -> 内容审核 -> 落库"""
    logger.info(f"=== REPORT INTERPRET TASK STARTED: report_id={report_id} ===")

    scheduler_engine = create_scheduler_engine()
    SchedulerSessionLocal = create_scheduler_session_factory(scheduler_engine)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(_interpret(SchedulerSessionLocal, report_id))
        logger.info(f"=== REPORT INTERPRET TASK COMPLETED: report_id={report_id} status={result} ===")
        return {"status": result}
    finally:
        loop.run_until_complete(scheduler_engine.dispose())
        # redis_client 是模块级单例，连接池会绑定首次使用它的事件循环。
        # 每个任务用的是新循环，若不在此关闭，下一个任务会拿到绑定已关闭循环
        # 的连接并抛 RuntimeError: Event loop is closed。
        loop.run_until_complete(_close_redis())
        loop.close()


async def _close_redis() -> None:
    """关闭 redis 连接池，使下个任务能在自己的事件循环上重建连接"""
    try:
        await redis_client.redis.aclose()
    except Exception as e:  # 关闭失败不应影响任务结果
        logger.warning(f"Failed to close redis connection: {e}")


async def _interpret(session_factory, report_id: int) -> str:
    async with session_factory() as db:
        report = (await db.execute(select(Report).where(Report.id == report_id))).scalar_one_or_none()
        if report is None:
            logger.error(f"Report not found: report_id={report_id}")
            return "not_found"

        # 幂等性：Celery 重试或重复触发时，已完成的报告直接返回，避免重复调用 LLM
        if report.interpretation_status == "completed":
            logger.info(f"Report {report_id} already interpreted, skip")
            return "already_completed"

        chunks = await rag_service.search(
            db,
            query=f"{report.type} 报告解读",
            top_k=5,
            source_type="医学参考资料",
            agent_type="report_interpret",
        )
        reference_chunks = [c.content for c in chunks]
        referenced_ids = [c.id for c in chunks]

        prompt = load_prompt(
            "report_interpret",
            report_type=report.type,
            report_content=json.dumps(report.content, ensure_ascii=False, indent=2),
            reference_chunks=reference_chunks,
        )

        try:
            # llm_service.call 内部已用 tenacity 做 3 次指数退避重试，这里不再对 LLMServiceError 做外层重试
            # 否则会变成 3x3=9 次调用才彻底失败
            llm_result = await llm_service.call(db, prompt, agent_type="report_interpret")
        except LLMServiceError as e:
            logger.error(f"LLM call failed for report_id={report_id}: {e}")
            report.interpretation_status = "failed"
            await db.commit()
            return "failed"

        passed, reason = review_content(llm_result.content)
        if not passed:
            logger.error(f"Content review failed for report_id={report_id}: {reason}")
            report.interpretation_status = "failed"
            await db.commit()
            return "failed"

        report.ai_interpretation = llm_result.content
        report.interpretation_status = "completed"
        report.interpretation_at = datetime.now(timezone.utc)
        report.referenced_chunks = referenced_ids
        await db.commit()
        return "completed"
