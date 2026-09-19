import asyncio
import logging

from app.core.celery_app import celery_app
from app.db.base import create_scheduler_engine, create_scheduler_session_factory
from app.services.common.payment import confirm_order

logger = logging.getLogger("payment_callback")


@celery_app.task(name="app.schedule.jobs.payment_callback.execute")
def execute(order_id: int):
    """
    模拟支付网关异步回调

    真实场景下这里由第三方支付平台回调触发；本项目用 Celery 延迟任务模拟，
    以还原「发起支付 -> 等待回调 -> 确认到账」的异步链路。
    """
    logger.info(f"=== PAYMENT CALLBACK STARTED: order_id={order_id} ===")

    scheduler_engine = create_scheduler_engine()
    SchedulerSessionLocal = create_scheduler_session_factory(scheduler_engine)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result, reason = loop.run_until_complete(_confirm(SchedulerSessionLocal, order_id))
        logger.info(
            f"=== PAYMENT CALLBACK COMPLETED: order_id={order_id} "
            f"result={result} reason={reason} ==="
        )
        return {"status": result, "reason": reason}
    finally:
        loop.run_until_complete(scheduler_engine.dispose())
        loop.close()


async def _confirm(session_factory, order_id: int):
    async with session_factory() as db:
        return await confirm_order(db, order_id)
