"""
OpenAPI JSON 导出路由
提供独立的 API 文档 JSON 下载功能，可导入到其他 API 管理工具
"""

from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse
from app.configs.docs_apps import create_client_app, create_backoffice_app
import json

router = APIRouter(prefix="/api-docs", tags=["API Documentation Export"])

@router.get("/client.json", summary="客户端 API 文档 JSON", description="下载客户端 API OpenAPI JSON 文档，可导入 Postman、Insomnia 等工具")
async def get_client_openapi_json():
    """
    获取客户端 API OpenAPI JSON 文档
    用于导入 Postman、Insomnia、ApiPost 等 API 管理工具
    """
    client_app = create_client_app()
    openapi_schema = client_app.openapi()

    # 设置响应头，提示下载
    headers = {
        "Content-Disposition": "attachment; filename=client-api.json",
        "Content-Type": "application/json"
    }

    return JSONResponse(
        content=openapi_schema,
        headers=headers
    )

@router.get("/backoffice.json", summary="后台 API 文档 JSON", description="下载后台 API OpenAPI JSON 文档，包含 JWT 认证配置")
async def get_backoffice_openapi_json():
    """
    获取后台 API OpenAPI JSON 文档
    包含完整的 JWT 认证配置，用于导入 API 管理工具
    """
    backoffice_app = create_backoffice_app()
    openapi_schema = backoffice_app.openapi()

    # 设置响应头，提示下载
    headers = {
        "Content-Disposition": "attachment; filename=backoffice-api.json",
        "Content-Type": "application/json"
    }

    return JSONResponse(
        content=openapi_schema,
        headers=headers
    )

@router.get("/", summary="API 文档导出指南")
async def api_docs_info():
    """
    API 文档导出功能说明
    """
    return {
        "message": "FastAPI Template - API Documentation Export",
        "description": "Provide OpenAPI JSON format API documentation for importing to various API management tools",
        "downloads": {
            "client": {
                "url": "/api-docs/client.json",
                "description": "Client API documentation (no authentication, includes AWS features)",
                "filename": "client-api.json",
                "features": ["Demo endpoints", "Configuration management", "AWS S3 upload"]
            },
            "backoffice": {
                "url": "/api-docs/backoffice.json",
                "description": "Backoffice API documentation (includes JWT authentication)",
                "filename": "backoffice-api.json",
                "features": ["Authentication management", "Admin management", "AWS management", "Permission control"]
            }
        },
        "import_guides": {
            "postman": "In Postman, select Import > Upload Files to import JSON file",
            "insomnia": "In Insomnia, select Import/Export > Import Data to import JSON file",
            "apipost": "In ApiPost, select Import > OpenAPI to import JSON file",
            "swagger_editor": "In Swagger Editor, select File > Import File to import JSON file",
            "apifox": "In Apifox, select Import > From URL/File > OpenAPI format"
        },
        "authentication": {
            "client": "Client API requires no authentication, use directly",
            "backoffice": "Backoffice API requires JWT authentication, configure Bearer Token authentication in tool after import"
        },
        "technical_info": {
            "openapi_version": "3.0.2",
            "framework": "FastAPI",
            "authentication": "JWT Bearer Token",
            "response_format": "Unified ApiResponse format"
        }
    }