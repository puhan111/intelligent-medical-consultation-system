import logging
import os
import tempfile
from fastapi import FastAPI

# 导入 Celery 应用
from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


def setup_scheduler(app: FastAPI = None):
    """
    使用 Celery 初始化定时任务调度器

    Args:
        app: FastAPI 应用实例
    """
    if not app:
        logger.error("FastAPI app instance is required for scheduler setup")
        return

    # 使用文件锁确保只有一个进程执行调度器初始化
    lock_file_path = os.path.join(tempfile.gettempdir(), "tip_scheduler.lock")
    logger.info(f"Lock file path: {lock_file_path}")

    try:
        # 检查锁文件是否存在
        if os.path.exists(lock_file_path):
            # 从锁文件中读取进程 ID
            try:
                with open(lock_file_path, "r") as f:
                    pid = f.read().strip()

                # 检查该进程是否仍在运行
                try:
                    os.kill(int(pid), 0)  # 检查进程是否存在
                    logger.info(f"Scheduler lock exists. Process {pid} is running the scheduler.")
                    # 本进程不执行调度器初始化
                    logger.info(f"Process {os.getpid()} will not initialize the scheduler.")
                    scheduler_enabled = False
                except ProcessLookupError:
                    # 进程不存在，删除过期锁文件
                    logger.warning(f"Process {pid} in lock file is not running. Removing stale lock file.")
                    os.remove(lock_file_path)
                    # 创建新的锁文件
                    with open(lock_file_path, "w") as f:
                        f.write(str(os.getpid()))
                    logger.info(f"Acquired scheduler lock. This process (PID: {os.getpid()}) will initialize the scheduler.")
                    scheduler_enabled = True
            except Exception as e:
                # 若读取锁文件失败，删除后重新创建
                logger.warning(f"Could not read scheduler lock file: {e}. Creating new lock.")
                os.remove(lock_file_path)
                with open(lock_file_path, "w") as f:
                    f.write(str(os.getpid()))
                logger.info(f"Acquired scheduler lock. This process (PID: {os.getpid()}) will initialize the scheduler.")
                scheduler_enabled = True
        else:
            # 锁文件不存在，创建新的锁文件
            with open(lock_file_path, "w") as f:
                f.write(str(os.getpid()))
            logger.info(f"Acquired scheduler lock. This process (PID: {os.getpid()}) will initialize the scheduler.")
            scheduler_enabled = True
    except Exception as e:
        logger.error(f"Error handling scheduler lock: {e}")
        # 出错时默认不启用调度器
        scheduler_enabled = False

    if scheduler_enabled:
        logger.info("Celery task scheduler initialized")
        # 将 Celery 应用实例存入 FastAPI app state，供其他地方使用
        app.state.celery_app = celery_app

def shutdown_scheduler():
    """
    关闭调度器 - 对于 Celery 无需特殊操作，
    因为 Celery worker 和 beat 进程是独立的进程
    """
    logger.info("Celery scheduler shutdown - no special actions needed")