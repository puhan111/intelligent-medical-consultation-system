from fastapi import APIRouter
from app.schemas.response import ApiResponse
from app.common.release import RELEASE_CONFIG
from app.services.common.redis import redis_client
from app.db.session import get_db
from sqlalchemy import text

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    健康检查端点
    检查应用状态、数据库连接和 Redis 连接
    """
    health_status = {
        "status": "healthy",
        "services": {
            "api": "up",
            "database": "unknown",
            "redis": "unknown"
        }
    }

    # 检查数据库连接
    try:
        async for db in get_db():
            result = await db.execute(text("SELECT 1"))
            if result.scalar() == 1:
                health_status["services"]["database"] = "up"
            break
    except Exception:
        health_status["services"]["database"] = "down"
        health_status["status"] = "unhealthy"

    # 检查 Redis 连接
    try:
        # 使用 Redis PING 命令测试连接
        await redis_client.redis.ping()
        health_status["services"]["redis"] = "up"
    except Exception:
        health_status["services"]["redis"] = "down"
        health_status["status"] = "unhealthy"

    # 若任一服务不健康，返回 503 状态码
    if health_status["status"] == "unhealthy":
        return ApiResponse.failed(
            message="Service unhealthy",
            body_code=503,
            http_code=503,
            data=health_status
        )

    return ApiResponse.success(data=health_status)


@router.get("/release")
async def get_release_config():
    return ApiResponse.success(data=RELEASE_CONFIG)
    

