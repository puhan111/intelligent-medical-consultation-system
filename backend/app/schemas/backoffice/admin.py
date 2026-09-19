from ..base import BaseSchema, BaseResponseSchema, add_padded_id
from pydantic import EmailStr, Field, field_validator
from typing import Optional

# 可通过管理员管理页面创建的角色（医生账号走独立的医生创建流程，不在此列）
ASSIGNABLE_ROLES = {"admin", "superadmin", "pharmacist", "cashier", "lab"}


class AdminBase(BaseSchema):
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: Optional[bool] = None


class AdminCreate(AdminBase):
    password: str
    role: str = "admin"

    @field_validator('role')
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in ASSIGNABLE_ROLES:
            raise ValueError(f"role 必须是以下之一: {', '.join(sorted(ASSIGNABLE_ROLES))}")
        return v


class AdminUpdate(BaseSchema):
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None

@add_padded_id()
class AdminResponse(BaseResponseSchema, AdminBase):
    is_active: bool
    role: str
    padded_id: Optional[str] = None

    @classmethod
    def model_validate(cls, admin):
        return super().model_validate(admin)


class AdminChangePassword(BaseSchema):
    current_password: str
    new_password: str = Field(..., min_length=8)

class ResetPassword(BaseSchema):
    password: str = Field(..., min_length=8)


class AdminFilter(BaseSchema):
    email: Optional[str] = None
    is_active: Optional[bool] = None
