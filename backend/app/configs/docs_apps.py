"""
分离的 FastAPI 应用工厂
为 Client 和 Backoffice 提供独立的文档应用
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from app.core.config import settings
from app.configs.client_swagger_config import (
    CLIENT_OPENAPI_INFO,
    CLIENT_OPENAPI_TAGS,
    CLIENT_SWAGGER_UI_PARAMETERS
)
from app.configs.backoffice_swagger_config import (
    BACKOFFICE_OPENAPI_INFO,
    BACKOFFICE_OPENAPI_TAGS,
    BACKOFFICE_SWAGGER_UI_PARAMETERS,
    BACKOFFICE_SECURITY_SCHEMES
)

# 根据环境设置 CORS 允许来源
ALLOWED_ORIGINS = ["*"] if settings.ENV == "development" or settings.ENV == "preview" else [
    "*"  # TODO: 生产环境请替换为具体域名
]

def create_client_app() -> FastAPI:
    """
    创建 Client API 文档应用
    """
    app = FastAPI(
        title=CLIENT_OPENAPI_INFO["title"],
        description=CLIENT_OPENAPI_INFO["description"],
        version=CLIENT_OPENAPI_INFO["version"],
        contact=CLIENT_OPENAPI_INFO["contact"],
        license_info=CLIENT_OPENAPI_INFO["license_info"],
        openapi_url="/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_tags=CLIENT_OPENAPI_TAGS,
        swagger_ui_parameters=CLIENT_SWAGGER_UI_PARAMETERS,
    )

    # 配置 CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 使用路由注册中心注册客户端路由
    from app.route.router_registry import register_routes, get_client_routes
    register_routes(app, get_client_routes())

    return app


def create_backoffice_app() -> FastAPI:
    """
    创建 Backoffice 管理 API 文档应用
    """
    app = FastAPI(
        title=BACKOFFICE_OPENAPI_INFO["title"],
        description=BACKOFFICE_OPENAPI_INFO["description"],
        version=BACKOFFICE_OPENAPI_INFO["version"],
        contact=BACKOFFICE_OPENAPI_INFO["contact"],
        license_info=BACKOFFICE_OPENAPI_INFO["license_info"],
        openapi_url="/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_tags=BACKOFFICE_OPENAPI_TAGS,
        swagger_ui_parameters=BACKOFFICE_SWAGGER_UI_PARAMETERS,
    )

    # 配置 CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 使用路由注册中心注册后台路由
    from app.route.router_registry import register_routes, get_backoffice_routes
    register_routes(app, get_backoffice_routes())

    # 自定义 OpenAPI schema 以添加 JWT 认证配置
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema

        openapi_schema = get_openapi(
            title=BACKOFFICE_OPENAPI_INFO["title"],
            version=BACKOFFICE_OPENAPI_INFO["version"],
            description=BACKOFFICE_OPENAPI_INFO["description"],
            routes=app.routes,
            openapi_version="3.0.2",
            contact=BACKOFFICE_OPENAPI_INFO["contact"],
            license_info=BACKOFFICE_OPENAPI_INFO["license_info"],
        )

        # 添加 JWT 认证配置
        openapi_schema["components"]["securitySchemes"] = BACKOFFICE_SECURITY_SCHEMES

        # 为需要认证的端点添加安全配置（登录端点除外）
        for path, methods in openapi_schema["paths"].items():
            if "/backoffice/auth/login" not in path:  # 登录端点无需认证
                for method_name, method_info in methods.items():
                    if method_name in ["get", "post", "put", "delete", "patch"]:
                        method_info["security"] = [{"BearerAuth": []}]

        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi

    return app