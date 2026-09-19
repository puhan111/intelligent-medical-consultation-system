import os
from celery import Celery
from kombu import Queue
from app.core.config import settings

# 配置 Celery
celery_app = Celery(
    "tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        'app.schedule.celery_job',  # 主任务注册模块
        'app.schedule.jobs.demo',    # 在此添加具体的任务模块
        'app.schedule.jobs.knowledge_embed',
        'app.schedule.jobs.report_interpret',
        'app.schedule.jobs.payment_callback'
    ]
)

# 配置 Celery Beat（定时任务调度）
# 默认不启用任何定时任务。如需注册周期性任务，在此添加配置项。示例（每分钟执行一次 demo 任务）：
# celery_app.conf.beat_schedule = {
#     'demo-every-minute': {
#         'task': 'app.schedule.jobs.demo.execute',
#         'schedule': 60.0,  # 每分钟执行一次
#         'options': {'queue': 'scheduled_tasks'}
#     },
# }
celery_app.conf.beat_schedule = {}

celery_app.conf.timezone = 'UTC'

# 显式声明 celery（默认队列，业务代码 .delay() 直接投递到这里）和
# scheduled_tasks（定时任务专用队列）两个队列，避免 worker 只监听
# scheduled_tasks 而漏消费默认队列里的任务
celery_app.conf.task_default_queue = 'celery'
celery_app.conf.task_queues = (
    Queue('celery', routing_key='celery'),
    Queue('scheduled_tasks', routing_key='scheduled_tasks'),
)

# 可选：配置其他 Celery 设置
celery_app.conf.update(
    broker_connection_retry=True,
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=3,
    broker_transport_options={
        'socket_connect_timeout': 5,
        'socket_timeout': 5,
        'retry_on_timeout': True,
    },
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    task_track_started=True,
    worker_concurrency=os.cpu_count(),
    task_time_limit=30 * 60,  # 30 minutes time limit
    task_soft_time_limit=15 * 60,  # 15 minutes soft time limit
)
