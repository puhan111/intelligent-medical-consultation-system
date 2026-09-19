from fastapi import HTTPException
from typing import Any, Optional
from app.common.language import get_message


class APIException(HTTPException):
    def __init__(
        self,
        code: int = 10000,
        message: str = "API exception",
        status_code: int = 400,
        data: Any = None,
        language: Optional[str] = None
    ) -> None:
        # 根据语言翻译消息
        translated_message = get_message(message, language)
        super().__init__(status_code=status_code, detail=translated_message)
        self.code = code  # 业务错误码
        self.data = data  # 可选的附加数据


# 常用异常类型
class ValidationError(APIException):
    def __init__(self, message: str = "Validation error", data: Any = None, language: Optional[str] = None):
        super().__init__(code=1001, message=message, status_code=400, data=data, language=language)


class AuthenticationError(APIException):
    def __init__(self, message: str = "Authentication failed", data: Any = None, language: Optional[str] = None):
        super().__init__(code=1002, message=message, status_code=401, data=data, language=language)


class AuthorizationError(APIException):
    def __init__(self, message: str = "Permission denied", data: Any = None, language: Optional[str] = None):
        super().__init__(code=1003, message=message, status_code=403, data=data, language=language)


class NotFoundError(APIException):
    def __init__(self, message: str = "Resource not found", data: Any = None, language: Optional[str] = None):
        super().__init__(code=1004, message=message, status_code=404, data=data, language=language)


class ServerError(APIException):
    def __init__(self, message: str = "Internal server error", data: Any = None, language: Optional[str] = None):
        super().__init__(code=1005, message=message, status_code=500, data=data, language=language)


class ForeignKeyViolationError(APIException):
    def __init__(
        self,
        message: str = "It is linked to trips or other resources. Please mark it as \"inactive\" to hide it from users",
        data: Any = None,
        language: Optional[str] = None
    ):
        super().__init__(code=1006, message=message, status_code=400, data=data, language=language)


class BudgetExceededError(APIException):
    """LLM 每日 token 预算已耗尽"""
    def __init__(self, message: str = "Daily LLM token budget exceeded", data: Any = None, language: Optional[str] = None):
        super().__init__(code=1007, message=message, status_code=429, data=data, language=language)


class LLMServiceError(APIException):
    """LLM 调用失败（重试耗尽后仍失败）"""
    def __init__(self, message: str = "LLM service unavailable", data: Any = None, language: Optional[str] = None):
        super().__init__(code=1008, message=message, status_code=503, data=data, language=language)


class InputTooLongError(APIException):
    """输入长度超出限制"""
    def __init__(self, message: str = "Input exceeds maximum length", data: Any = None, language: Optional[str] = None):
        super().__init__(code=1009, message=message, status_code=400, data=data, language=language)


class ContentReviewError(APIException):
    """输出内容审核未通过"""
    def __init__(self, message: str = "Generated content failed review", data: Any = None, language: Optional[str] = None):
        super().__init__(code=1010, message=message, status_code=503, data=data, language=language)