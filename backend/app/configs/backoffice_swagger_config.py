"""
后台 Swagger UI 配置文件
专用于后台管理 API 文档
"""

from typing import Dict, Any
from app.core.config import settings

# 后台 Swagger UI 配置
BACKOFFICE_SWAGGER_UI_PARAMETERS = {
    "deepLinking": True,
    "displayRequestDuration": True,
    "docExpansion": "list",  # 展开标签但不展开操作
    "operationsSorter": "alpha",  # 按字母顺序排序
    "filter": True,
    "tryItOutEnabled": True,
}

# 后台 OpenAPI 元数据配置
BACKOFFICE_OPENAPI_INFO = {
    "title": f"{settings.PROJECT_NAME} - Backoffice Management API",
    "description": f"""
# 后台管理 API 服务

这是后台管理系统的内部 API 接口文档。

## 功能模块

### 认证管理（Auth）
- 管理员登录/登出
- JWT token 管理
- token 刷新操作

### 管理员管理（Admin）
- 管理员账户增删改查
- 权限管理
- 用户信息维护
- 密码管理功能

### 云存储管理（AWS）
- 文件管理功能
- S3 存储操作
- 上传权限控制

## 认证说明

⚠️ **所有后台接口都需要 JWT 认证**（登录接口除外）

### 如何使用认证：
1. 调用 `/login` 接口获取 access token
2. 点击右上角的 🔒 **Authorize** 按钮
3. 在输入框中输入：`Bearer your-access-token`
4. 点击 **Authorize** 完成认证设置

## 技术特性

- 🔒 **安全**：JWT 认证 + 权限控制
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

## 错误码说明

- **400**：参数错误（展示给用户）
- **401**：认证失败
- **403**：权限不足
- **404**：资源未找到
- **500**：服务器错误

## 环境信息

- **当前环境**：{settings.ENV}
- **API 版本**：v1
- **文档类型**：后台管理 API
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

# 后台 OpenAPI 标签配置
BACKOFFICE_OPENAPI_TAGS = [
    {
        "name": "backoffice-auth",
        "description": "后台认证接口",
        "externalDocs": {
            "description": "认证文档",
            "url": "https://fastapi.tiangolo.com/tutorial/security/",
        },
    },
    {
        "name": "backoffice-admin",
        "description": "后台管理员接口",
        "externalDocs": {
            "description": "管理员文档",
            "url": "https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/",
        },
    },
    {
        "name": "backoffice-aws",
        "description": "后台云存储管理",
        "externalDocs": {
            "description": "AWS 管理文档",
            "url": "https://docs.aws.amazon.com/s3/",
        },
    },
]

# JWT 认证配置
BACKOFFICE_SECURITY_SCHEMES = {
    "BearerAuth": {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "JWT authentication token, format: Bearer {token}. Please obtain the token through the login interface first.",
    }
}

def get_backoffice_openapi_config() -> Dict[str, Any]:
    """
    获取后台管理 OpenAPI 配置
    """
    return {
        **BACKOFFICE_OPENAPI_INFO,
        "openapi": "3.0.2",
        "tags": BACKOFFICE_OPENAPI_TAGS,
        "components": {
            "securitySchemes": BACKOFFICE_SECURITY_SCHEMES
        },
    }