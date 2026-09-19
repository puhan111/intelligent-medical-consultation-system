from fastapi import FastAPI, Request, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
# 路由导入已迁移至集中式路由注册中心

from app.core.config import settings
from app.configs.docs_apps import create_client_app, create_backoffice_app
from fastapi.exceptions import RequestValidationError
from app.exceptions.http_exceptions import APIException
from app.schemas.response import ApiResponse
from contextlib import asynccontextmanager
from app.core.log_config import setup_logging, shutdown_logging, is_master_process
from app.services.common.redis import redis_client
from app.services.common.thread_pool import thread_pool_service
from app.db.base import close_db_engine
import logging
from app.common.log_consumer import consume_logs_forever
import threading
import asyncio

logger = logging.getLogger(__name__)

# 根据环境设置 CORS 允许来源
ALLOWED_ORIGINS = ["*"] if settings.ENV == "development" or settings.ENV == "preview" else [
    "*"  # TODO: 生产环境请替换为具体域名
]


@asynccontextmanager
async def lifespan(application: FastAPI):
    # 应用启动时执行
    setup_logging()
    logger.info("Application starting up")

    # 日志消费线程（仅在主进程中启动，防止重复）
    if is_master_process():
        try:
            # 创建包装函数以在线程中运行异步函数
            def run_log_consumer():
                asyncio.run(consume_logs_forever())

            log_thread = threading.Thread(target=run_log_consumer, daemon=True)
            log_thread.start()
            logger.info("[LogConsumer] Log consumer thread started (master process)")
        except Exception as e:
            logger.warning(f"[LogConsumer] Failed to start log consumer thread: {e}")

    yield  # 应用运行期间

    # 应用关闭时执行
    if is_master_process():
        shutdown_logging()  # 关闭日志

    await close_db_engine()  # 清理数据库引擎
    await redis_client.close()  # 关闭 Redis 连接
    thread_pool_service.shutdown()  # 关闭邮件线程池
    logger.info("Application shutting down")


def create_app():
    app = FastAPI(
        lifespan=lifespan,
        title=settings.PROJECT_NAME,
        description="FastAPI Template - Unified Entry",
        version="1.0.0",
        docs_url=None,  # 禁用默认 docs
        redoc_url=None,  # 禁用默认 ReDoc
        openapi_url=None,  # 禁用默认 OpenAPI
    )

    # 配置 CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,  # 生产环境应设置具体域名
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 开发环境提供文档访问导航，生产环境隐藏
    if settings.ENV in ["development", "preview"]:
        @app.get("/", tags=["Documentation Navigation"])
        async def swagger_navigation():
            """
            开发环境 Swagger 文档导航
            """
            return {
                "message": "FastAPI Template - Development Environment",
                "environment": settings.ENV,
                "documentation": {
                    "client_api": {
                        "swagger": "/client/docs",
                        "redoc": "/client/redoc",
                        "openapi": "/client/openapi.json",
                        "description": "Client API documentation (no authentication required)"
                    },
                    "backoffice_api": {
                        "swagger": "/backoffice/docs",
                        "redoc": "/backoffice/redoc",
                        "openapi": "/backoffice/openapi.json",
                        "description": "Backoffice API documentation (JWT authentication required)"
                    }
                },
                "api_exports": {
                    "client_json": "/api-docs/client.json",
                    "backoffice_json": "/api-docs/backoffice.json",
                    "info": "/api-docs/"
                },
                "health_check": "/api/v1/config/health"
            }

    # 使用路由注册中心统一注册所有路由
    from app.route.router_registry import register_routes, get_client_routes, get_backoffice_routes, get_common_routes

    # 注册客户端路由
    register_routes(app, get_client_routes())

    # 注册后台路由
    register_routes(app, get_backoffice_routes())

    # 注册通用路由
    register_routes(app, get_common_routes())

    # 挂载分离的文档应用
    client_docs_app = create_client_app()
    backoffice_docs_app = create_backoffice_app()

    app.mount("/client", client_docs_app)
    app.mount("/backoffice", backoffice_docs_app)

    @app.exception_handler(APIException)
    async def api_exception_handler(request: Request, exc: APIException):
        logger.error(f"API Exception: {exc.status_code} - {exc.code} - {exc.detail}",
                    extra={"request": f"{request.method} {request.url}"})
        return ApiResponse.failed(
            message=exc.detail,
            body_code=exc.code,  # 业务错误码
            http_code=exc.status_code,
            data=exc.data
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        logger.error(f"HTTP Exception: {exc.status_code} - {exc.detail}",
                    extra={"request": f"{request.method} {request.url}"})
        return ApiResponse.failed(
            message=exc.detail,
            body_code=exc.status_code,  # 回退为 HTTP 状态码
            http_code=exc.status_code,
            data=None
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.warning(f"Validation Error: {exc.errors()}",
                    extra={"request": f"{request.method} {request.url}"})
        return ApiResponse.failed(
            message="Validation error",
            body_code=1001,
            http_code=status.HTTP_400_BAD_REQUEST,
            data=exc.errors()
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.exception(f"Unhandled Exception: {str(exc)}",
                        extra={"request": f"{request.method} {request.url}"})
        return ApiResponse.failed(
            message="Internal server error",
            body_code=1005,
            http_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return app