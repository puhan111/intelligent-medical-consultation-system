from typing import Dict, Optional

# 错误消息翻译表
ERROR_MESSAGES = {
    # 权限错误
    "Permission denied": {
        "en": "Permission denied",
        "kr": "권한이 거부되었습니다"
    },

    # 资源错误
    "Resource not found": {
        "en": "Resource not found",
        "kr": "리소스를 찾을 수 없습니다"
    },

    # 通用错误
    "API exception": {
        "en": "API exception",
        "kr": "API 예외"
    },
    "Internal server error": {
        "en": "Internal server error",
        "kr": "내부 서버 오류"
    },
    "Operation failed": {
        "en": "Operation failed",
        "kr": "작업 실패"
    }
}

def get_message(message: str, language: Optional[str] = None) -> str:
    """
    根据指定语言获取翻译后的消息。

    Args:
        message: 英文原始消息
        language: 语言代码（en、kr）

    Returns:
        请求语言对应的翻译消息；若未找到翻译，则返回原始消息
    """
    if not language or language.lower() not in ["en", "kr"]:
        language = "en"  # 默认使用英文

    language = language.lower()

    # 若消息存在于翻译表中
    if message in ERROR_MESSAGES:
        return ERROR_MESSAGES[message].get(language, ERROR_MESSAGES[message]["en"])

    # 若未找到翻译，返回原始消息
    return message