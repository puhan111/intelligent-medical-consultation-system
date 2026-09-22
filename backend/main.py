from app.route import create_app
from app.core.config import settings
import logging
import os

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
        env_file=".env",  # 使用环境变量文件
        proxy_headers=True,
        # 默认仅信任本机代理；Compose中应用端口不对外发布，可显式设为*信任同网络Nginx。
        forwarded_allow_ips=os.getenv("FORWARDED_ALLOW_IPS", "127.0.0.1"),
    )
