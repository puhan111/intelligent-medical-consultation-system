import logging
from celery import shared_task
from app.db.base import create_scheduler_engine, create_scheduler_session_factory
import asyncio

logger = logging.getLogger(__name__)

@shared_task(name="app.schedule.jobs.demo.execute")
def execute():
    """
    用于测试 Celery 执行的演示任务
    这是一个简单的任务，用于记录日志并演示数据库连接
    """
    logger.info("=== DEMO TASK EXECUTION STARTED ===")

    # 为该任务创建专用的数据库引擎和 session 工厂
    scheduler_engine = create_scheduler_engine()
    SchedulerSessionLocal = create_scheduler_session_factory(scheduler_engine)

    # 使用新创建的 session 工厂
    try:
        # 在 FastAPI 上下文中这会是异步函数，但 Celery 任务应为同步
        # 因此这里使用同步方式处理
        logger.info("Connecting to database...")
        # 在此处添加数据库操作
        logger.info("Database operations completed")

    except Exception as e:
        logger.error(f"Error in demo task: {e}", exc_info=True)
        raise
    finally:
        # 通过在事件循环中运行协程来正确关闭引擎
        logger.info("Closing database connection")
        # 创建新的事件循环来运行异步 dispose 方法
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(scheduler_engine.dispose())
        finally:
            loop.close()

    logger.info("=== DEMO TASK EXECUTION COMPLETED SUCCESSFULLY ===")
    return {"status": "success", "message": "Demo task executed successfully"}