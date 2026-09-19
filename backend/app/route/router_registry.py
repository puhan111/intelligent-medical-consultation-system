"""
路由注册中心
集中管理所有路由配置，避免重复配置
"""

from typing import List, Dict
from app.core.config import settings


class RouteConfig:
    """路由配置类"""
    def __init__(self, module_path: str, prefix: str, tags: List[str]):
        self.module_path = module_path
        self.prefix = prefix
        self.tags = tags


# 客户端路由配置
CLIENT_ROUTES = [
    RouteConfig(
        module_path="app.api.client.v1.auth",
        prefix=f"{settings.API_V1_STR}/auth",
        tags=["client-auth"]
    ),
    RouteConfig(
        module_path="app.api.client.v1.user",
        prefix=f"{settings.API_V1_STR}/users",
        tags=["client-user"]
    ),
    RouteConfig(
        module_path="app.api.client.v1.demo",
        prefix=f"{settings.API_V1_STR}/demo",
        tags=["client-demo"]
    ),
    RouteConfig(
        module_path="app.api.client.v1.config",
        prefix=f"{settings.API_V1_STR}/config",
        tags=["client-config"]
    ),
    RouteConfig(
        module_path="app.api.client.v1.aws",
        prefix=f"{settings.API_V1_STR}/aws",
        tags=["client-aws"]
    ),
    RouteConfig(
        module_path="app.api.client.v1.department",
        prefix=f"{settings.API_V1_STR}/departments",
        tags=["client-department"]
    ),
    RouteConfig(
        module_path="app.api.client.v1.doctor",
        prefix=f"{settings.API_V1_STR}/doctors",
        tags=["client-doctor"]
    ),
    RouteConfig(
        module_path="app.api.client.v1.appointment",
        prefix=f"{settings.API_V1_STR}/appointments",
        tags=["client-appointment"]
    ),
    RouteConfig(
        module_path="app.api.client.v1.prescription",
        prefix=f"{settings.API_V1_STR}/prescriptions",
        tags=["client-prescription"]
    ),
    RouteConfig(
        module_path="app.api.client.v1.medical_record",
        prefix=f"{settings.API_V1_STR}/medical-records",
        tags=["client-medical-record"]
    ),
    RouteConfig(
        module_path="app.api.client.v1.bill",
        prefix=f"{settings.API_V1_STR}/bills",
        tags=["client-bill"]
    ),
    RouteConfig(
        module_path="app.api.client.v1.report",
        prefix=f"{settings.API_V1_STR}/reports",
        tags=["client-report"]
    ),
    RouteConfig(
        module_path="app.api.client.v1.triage",
        prefix=f"{settings.API_V1_STR}/triage",
        tags=["client-triage"]
    ),
]

# 后台路由配置
BACKOFFICE_ROUTES = [
    RouteConfig(
        module_path="app.api.backoffice.v1.auth",
        prefix=f"{settings.API_V1_STR}/backoffice/auth",
        tags=["backoffice-auth"]
    ),
    RouteConfig(
        module_path="app.api.backoffice.v1.admin",
        prefix=f"{settings.API_V1_STR}/backoffice/admins",
        tags=["backoffice-admin"]
    ),
    RouteConfig(
        module_path="app.api.backoffice.v1.aws",
        prefix=f"{settings.API_V1_STR}/backoffice/aws",
        tags=["backoffice-aws"]
    ),
    RouteConfig(
        module_path="app.api.backoffice.v1.department",
        prefix=f"{settings.API_V1_STR}/backoffice/departments",
        tags=["backoffice-department"]
    ),
    RouteConfig(
        module_path="app.api.backoffice.v1.doctor",
        prefix=f"{settings.API_V1_STR}/backoffice/doctors",
        tags=["backoffice-doctor"]
    ),
    RouteConfig(
        module_path="app.api.backoffice.v1.drug",
        prefix=f"{settings.API_V1_STR}/backoffice/drugs",
        tags=["backoffice-drug"]
    ),
    RouteConfig(
        module_path="app.api.backoffice.v1.appointment",
        prefix=f"{settings.API_V1_STR}/backoffice/appointments",
        tags=["backoffice-appointment"]
    ),
    RouteConfig(
        module_path="app.api.backoffice.v1.medical_record",
        prefix=f"{settings.API_V1_STR}/backoffice/medical-records",
        tags=["backoffice-medical-record"]
    ),
    RouteConfig(
        module_path="app.api.backoffice.v1.prescription",
        prefix=f"{settings.API_V1_STR}/backoffice/prescriptions",
        tags=["backoffice-prescription"]
    ),
    RouteConfig(
        module_path="app.api.backoffice.v1.bill",
        prefix=f"{settings.API_V1_STR}/backoffice/bills",
        tags=["backoffice-bill"]
    ),
    RouteConfig(
        module_path="app.api.backoffice.v1.knowledge",
        prefix=f"{settings.API_V1_STR}/backoffice/knowledge",
        tags=["backoffice-knowledge"]
    ),
    RouteConfig(
        module_path="app.api.backoffice.v1.report",
        prefix=f"{settings.API_V1_STR}/backoffice/reports",
        tags=["backoffice-report"]
    ),
    RouteConfig(
        module_path="app.api.backoffice.v1.ai_monitor",
        prefix=f"{settings.API_V1_STR}/backoffice/ai-monitor",
        tags=["backoffice-ai-monitor"]
    ),
]

# 通用路由配置（非 client 或 backoffice 专属的路由）
COMMON_ROUTES = [
    RouteConfig(
        module_path="app.api.docs_export",
        prefix="",
        tags=["API Documentation Export"]
    ),
]


def register_routes(app, route_configs: List[RouteConfig]):
    """
    动态注册路由

    Args:
        app: FastAPI 应用实例
        route_configs: 路由配置列表
    """
    for route_config in route_configs:
        # 动态导入模块
        module_parts = route_config.module_path.split('.')
        module_name = module_parts[-1]

        # 导入模块
        module = __import__(route_config.module_path, fromlist=[module_name])

        # 注册路由
        app.include_router(
            module.router,
            prefix=route_config.prefix,
            tags=route_config.tags
        )


def get_client_routes() -> List[RouteConfig]:
    """获取客户端路由配置"""
    return CLIENT_ROUTES


def get_backoffice_routes() -> List[RouteConfig]:
    """获取后台路由配置"""
    return BACKOFFICE_ROUTES


def get_common_routes() -> List[RouteConfig]:
    """获取通用路由配置"""
    return COMMON_ROUTES


def get_all_routes() -> Dict[str, List[RouteConfig]]:
    """获取所有路由配置"""
    return {
        "client": CLIENT_ROUTES,
        "backoffice": BACKOFFICE_ROUTES,
        "common": COMMON_ROUTES
    }
