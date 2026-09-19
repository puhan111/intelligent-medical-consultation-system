from app.route import create_app
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

app = create_app()

if __name__ == "__main__":
    import uvicorn

    # 生产环境建议使用配置文件启动
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.API_PORT,
        reload=settings.ENV == "development",  # 开发环境启用热重载
        workers=1 if settings.ENV == "development" else 4,  # 生产环境使用多进程
        env_file=".env"  # 使用环境变量文件
    )
