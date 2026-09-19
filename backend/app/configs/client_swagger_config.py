"""
客户端 Swagger UI 配置文件
专用于客户端 API 文档
"""

from typing import Dict, Any
from app.core.config import settings

# 客户端 Swagger UI 配置
CLIENT_SWAGGER_UI_PARAMETERS = {
    "deepLinking": True,
    "displayRequestDuration": True,
    "docExpansion": "list",  # 展开标签但不展开操作
    "operationsSorter": "alpha",  # 按字母顺序排序
    "filter": True,
    "tryItOutEnabled": True,
}

# 客户端 OpenAPI 元数据配置
CLIENT_OPENAPI_INFO = {
    "title": f"{settings.PROJECT_NAME} - Client API",
    "description": f"""
# 客户端 API 服务

这是面向客户端应用的公开 API 接口文档。

## 功能模块

### 演示功能（Demo）
- 基础演示接口
- 功能测试接口

### 配置管理（Config）
- 客户端配置获取
- 系统配置查询

### 云存储服务（AWS）
- 文件上传功能
- S3 存储集成

## 技术特性

- 🚀 **高性能**：基于 FastAPI 异步框架
- 📊 **数据库**：PostgreSQL + SQLAlchemy ORM
- 🎯 **缓存**：Redis 缓存系统
- ☁️ **云存储**：AWS S3 集成
- 📝 **文档**：自动生成 OpenAPI 文档
- ⚡ **异步**：全异步处理以提升性能

## 响应格式

所有 API 响应遵循统一格式：

```json
{{
    "success": true,
    "message": "Operation successful",
    "data": {{}},
    "code": 200
}}
```

## 环境信息

- **当前环境**：{settings.ENV}
- **API 版本**：v1
- **文档类型**：客户端 API
    """,
    "version": "1.0.0",
    "contact": {
        "name": "Development Team",
        "email": settings.ADMIN_EMAIL,
    },
    "license_info": {
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
}

# 客户端 OpenAPI 标签配置
CLIENT_OPENAPI_TAGS = [
    {
        "name": "client-demo",
        "description": "客户端演示接口",
        "externalDocs": {
            "description": "了解更多",
            "url": "https://fastapi.tiangolo.com/",
        },
    },
    {
        "name": "client-config",
        "description": "客户端配置接口",
        "externalDocs": {
            "description": "配置文档",
            "url": "https://fastapi.tiangolo.com/tutorial/",
        },
    },
    {
        "name": "client-aws",
        "description": "客户端云存储接口",
        "externalDocs": {
            "description": "AWS S3 文档",
            "url": "https://docs.aws.amazon.com/s3/",
        },
    },
]

def get_client_openapi_config() -> Dict[str, Any]:
    """
    获取客户端 OpenAPI 配置
    """
    return {
        **CLIENT_OPENAPI_INFO,
        "openapi": "3.0.2",
        "tags": CLIENT_OPENAPI_TAGS,
    }