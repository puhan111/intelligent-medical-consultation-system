from ..base import BaseSchema, BaseResponseSchema, add_padded_id
from pydantic import EmailStr
from typing import Optional


@add_padded_id()
class UserProfileResponse(BaseResponseSchema):
    """患者个人资料响应"""
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    avatar: Optional[str] = None
    gender: Optional[str] = None
    is_active: bool
    is_verified: bool
    padded_id: Optional[str] = None


class UserProfileUpdate(BaseSchema):
    """患者个人资料更新（邮箱与密码不在此修改）"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    avatar: Optional[str] = None
    gender: Optional[str] = None
