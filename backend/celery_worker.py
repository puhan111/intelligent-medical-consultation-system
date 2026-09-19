from app.core.celery_app import celery_app

if __name__ == '__main__':
    # 此文件用于启动 Celery worker
    celery_app.start(['celery', 'worker', '--loglevel=info'])