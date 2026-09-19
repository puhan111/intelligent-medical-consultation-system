from functools import wraps
from sqlalchemy.exc import IntegrityError
from app.exceptions.http_exceptions import ForeignKeyViolationError
import re


def handle_db_exceptions(func):
    """
    用于处理数据库操作异常的装饰器，尤其是外键约束违规

    使用示例：
    @handle_db_exceptions
    async def delete_item(db: AsyncSession, item_id: int):
        # 删除操作代码
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except IntegrityError as e:
            error_msg = str(e)
            # 检查是否为外键约束错误
            if "foreign key constraint fails" in error_msg.lower() or "FOREIGN KEY constraint failed" in error_msg:
                # 尝试从错误消息中提取关联表名
                referenced_table = extract_referenced_table(error_msg)
                if referenced_table:
                    raise ForeignKeyViolationError(
                        message=f"It is linked to trips or other resources. Please mark it as \"inactive\" to hide it from users"
                    )
                else:
                    raise ForeignKeyViolationError()
            # 重新抛出原始异常
            raise
    return wrapper


def extract_referenced_table(error_message: str) -> str:
    """
    从错误消息中提取被引用的表名
    """
    # MySQL 外键错误消息格式："FOREIGN KEY constraint failed (table_name, CONSTRAINT ...)"
    # 或 "foreign key constraint fails (`database`.`table`, CONSTRAINT ...)"
    try:
        # 尝试匹配 MySQL 错误格式
        match = re.search(r"constraint fails \(`[^`]*`.`([^`]*)`", error_message)
        if match:
            return match.group(1)

        # 尝试匹配 SQLite 错误格式
        match = re.search(r"FOREIGN KEY constraint failed \(([^,]*)", error_message)
        if match:
            return match.group(1)

        return ""
    except:
        return ""