from typing import Optional
from uuid import uuid4
import boto3
from botocore.exceptions import ClientError
from app.core.config import settings
from app.exceptions.http_exceptions import APIException
import mimetypes


class S3Service:
    """S3 文件服务 - 提供文件上传、下载和管理功能"""

    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        self.bucket_name = settings.AWS_BUCKET_NAME

    def generate_file_key(
        self,
        user_id: int,
        file_name: str,
        module: Optional[str] = None,
        sub_path: Optional[str] = None,
        module_id: Optional[int] = None
    ) -> str:
        """
        生成标准化的 S3 文件 key

        Args:
            user_id: 用户 ID
            file_name: 原始文件名
            module: 模块名称（如 positions、interviews 等）- 可选
            sub_path: 子路径（如 jd、cv、cover_letter 等）- 可选
            module_id: 模块记录 ID（可选，如 position_id）

        Returns:
            标准化的文件 key 路径
        """
        # 获取文件扩展名
        file_ext = file_name.split('.')[-1].lower() if '.' in file_name else ''

        # 生成唯一文件名
        unique_filename = f"{uuid4()}.{file_ext}" if file_ext else str(uuid4())

        # 根据可用参数构建文件路径
        path_parts = [f"users/{user_id}"]

        if module:
            path_parts.append(module)
            if module_id:
                path_parts.append(str(module_id))

        if sub_path:
            path_parts.append(sub_path)

        path_parts.append(unique_filename)

        return "/".join(path_parts)

    def generate_presigned_upload_url(
        self,
        file_key: str,
        file_type: str,
        expires_in: int = 900,  # 15 分钟
        max_file_size: int = 10 * 1024 * 1024  # 10MB
    ) -> dict:
        """
        生成 S3 预签名上传 URL

        Args:
            file_key: S3 文件 key
            file_type: 文件 MIME 类型
            expires_in: URL 有效期（秒）
            max_file_size: 最大文件大小（字节）

        Returns:
            {
                "presigned_url": "...",
                "file_key": "...",
                "expires_in": 900
            }
        """
        try:
            # 生成预签名 URL
            presigned_url = self.s3_client.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': file_key,
                    'ContentType': file_type
                },
                ExpiresIn=expires_in,
                HttpMethod='PUT'
            )

            return {
                "presigned_url": presigned_url,
                "file_key": file_key,
                "expires_in": expires_in,
                "max_file_size": max_file_size
            }

        except ClientError as e:
            raise APIException(
                status_code=500,
                message=f"Failed to generate presigned URL: {str(e)}"
            )

    def generate_presigned_download_url(
        self,
        file_key: str,
        expires_in: int = 3600  # 1 小时
    ) -> str:
        """
        生成 S3 预签名下载 URL

        Args:
            file_key: S3 文件 key
            expires_in: URL 有效期（秒）

        Returns:
            预签名下载 URL
        """
        try:
            presigned_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': file_key
                },
                ExpiresIn=expires_in
            )
            return presigned_url

        except ClientError as e:
            raise APIException(
                status_code=500,
                message=f"Failed to generate download URL: {str(e)}"
            )

    def get_file_url(self, file_key: str) -> str:
        """
        获取文件公开访问 URL

        Args:
            file_key: S3 文件 key

        Returns:
            文件 S3 URL
        """
        if settings.AWS_ENDPOINT:
            return f"{settings.AWS_ENDPOINT}/{file_key}"
        else:
            if settings.AWS_REGION and settings.AWS_REGION.startswith('cn-'):
                return f"https://{self.bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com.cn/{file_key}"
            else:
                return f"https://{self.bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com/{file_key}"

    def delete_file(self, file_key: str) -> bool:
        """
        删除 S3 文件

        Args:
            file_key: S3 文件 key

        Returns:
            是否删除成功
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=file_key
            )
            return True

        except ClientError as e:
            raise APIException(
                status_code=500,
                message=f"Failed to delete file: {str(e)}"
            )

    def validate_file_type(self, file_name: str, allowed_types: list) -> bool:
        """
        校验文件类型

        Args:
            file_name: 文件名
            allowed_types: 允许的文件类型列表（如 ['pdf', 'docx']）

        Returns:
            文件类型是否允许
        """
        file_ext = file_name.split('.')[-1].lower() if '.' in file_name else ''
        return file_ext in allowed_types

    def get_mime_type(self, file_name: str) -> str:
        """
        获取文件 MIME 类型

        Args:
            file_name: 文件名

        Returns:
            MIME 类型
        """
        mime_type, _ = mimetypes.guess_type(file_name)
        return mime_type or 'application/octet-stream'


# 创建全局实例
s3_service = S3Service()
