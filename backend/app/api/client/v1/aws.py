from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session
from app.models.user import User
from app.utils import utils
from app.db.session import get_db
from app.api.client.deps import get_current_user
from app.exceptions.http_exceptions import APIException
from app.schemas.response import ApiResponse
from app.schemas.client.aws import (
    PresignedUrlRequest,
    PresignedUrlResponse,
    PresignedDownloadUrlResponse
)
from app.services.common import s3_service

router = APIRouter()


@router.get("/temporary-credentials")
async def get_temporary_credentials(
    language: str = Header(None),
    current_user: User = Depends(get_current_user)
):
    """获取 S3 临时访问凭证"""
    try:
        temporary_credentials = utils.get_temporary_credentials()
        return ApiResponse.success(data=temporary_credentials)
    except Exception as e:
        raise APIException(status_code=500, message=str(e), language=language)


@router.post("/presigned-upload-url", response_model=PresignedUrlResponse)
async def generate_presigned_upload_url(
    request: PresignedUrlRequest,
    current_user: User = Depends(get_current_user)
):
    """
    生成 S3 预签名上传 URL

    - **file_name**: 带扩展名的文件名
    - **file_type**: 文件 MIME 类型
    - **file_size**: 文件大小（字节）
    - **module**: 模块名称（如 positions、interviews 等）
    - **module_id**: 模块记录 ID（可选）
    - **sub_path**: 子路径类型（如 jd、cv、cover-letter）
    """
    # 校验文件大小（最大 10MB）
    max_size = 10 * 1024 * 1024  # 10MB
    if request.file_size > max_size:
        raise APIException(
            status_code=400,
            message=f"File size exceeds maximum limit of {max_size / (1024 * 1024)}MB"
        )

    # 校验文件类型
    allowed_types = ['pdf', 'docx']
    if not s3_service.validate_file_type(request.file_name, allowed_types):
        raise APIException(
            status_code=400,
            message=f"Unsupported file type. Allowed types: {', '.join(allowed_types)}"
        )

    # 生成文件 key
    file_key = s3_service.generate_file_key(
        user_id=current_user.id,
        file_name=request.file_name,
        module=request.module,
        sub_path=request.sub_path,
        module_id=request.module_id
    )

    # 生成预签名上传 URL
    result = s3_service.generate_presigned_upload_url(
        file_key=file_key,
        file_type=request.file_type,
        expires_in=900,  # 15 分钟
        max_file_size=max_size
    )

    return ApiResponse.success(data=result)


@router.get("/presigned-download-url", response_model=PresignedDownloadUrlResponse)
async def generate_presigned_download_url(
    file_key: str,
    current_user: User = Depends(get_current_user)
):
    """
    生成 S3 预签名下载 URL

    - **file_key**: S3 文件 key
    """
    # 校验文件 key 是否属于当前用户
    if not file_key.startswith(f"users/{current_user.id}/"):
        raise APIException(
            status_code=403,
            message="Access denied: You don't have permission to access this file"
        )

    download_url = s3_service.generate_presigned_download_url(file_key)

    return ApiResponse.success(data={
        "download_url": download_url,
        "file_key": file_key,
        "expires_in": 3600  # 1 hour
    })
