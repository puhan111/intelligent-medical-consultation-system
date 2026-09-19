from ..base import BaseSchema
from pydantic import EmailStr, Field, field_validator
import re


class Login(BaseSchema):
    email: EmailStr
    password: str


class Register(BaseSchema):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=50)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """密码必须包含字母和数字"""
        if not re.search(r'[A-Za-z]', v):
            raise ValueError('密码必须包含至少一个字母')
        if not re.search(r'\d', v):
            raise ValueError('密码必须包含至少一个数字')
        return v


class Token(BaseSchema):
    access_token: str
    refresh_token: str
    token_type: str


class RefreshToken(BaseSchema):
    refresh_token: str


class Logout(BaseSchema):
    refresh_token: str
