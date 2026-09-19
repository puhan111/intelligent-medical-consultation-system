from ..base import BaseSchema, BaseResponseSchema, add_padded_id
from pydantic import EmailStr, Field
from typing import Optional


class DoctorCreate(BaseSchema):
    department_id: int
    title: Optional[str] = None
    introduction: Optional[str] = None
    # 关联的管理员账号信息（创建医生时同步创建对应的 Admin 账号）
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class DoctorUpdate(BaseSchema):
    department_id: Optional[int] = None
    title: Optional[str] = None
    introduction: Optional[str] = None


@add_padded_id()
class DoctorResponse(BaseResponseSchema):
    admin_id: int
    department_id: int
    title: Optional[str] = None
    introduction: Optional[str] = None
    padded_id: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    department_name: Optional[str] = None


class DoctorFilter(BaseSchema):
    department_id: Optional[int] = None
    title: Optional[str] = None
