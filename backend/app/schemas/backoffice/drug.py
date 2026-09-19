from ..base import BaseSchema, BaseResponseSchema, add_padded_id
from pydantic import Field
from typing import Optional
from decimal import Decimal


class DrugCreate(BaseSchema):
    """新增药品"""
    name: str = Field(..., min_length=1, max_length=200)
    spec: Optional[str] = Field(None, max_length=100)
    unit: str = Field("盒", min_length=1, max_length=20)
    unit_price: Decimal = Field(..., gt=0, decimal_places=2)
    is_active: bool = True


class DrugUpdate(BaseSchema):
    """更新药品（仅传需要修改的字段）"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    spec: Optional[str] = Field(None, max_length=100)
    unit: Optional[str] = Field(None, min_length=1, max_length=20)
    unit_price: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    is_active: Optional[bool] = None


@add_padded_id()
class DrugResponse(BaseResponseSchema):
    """药品响应"""
    name: str
    spec: Optional[str] = None
    unit: str
    unit_price: float
    is_active: bool
    padded_id: Optional[str] = None
