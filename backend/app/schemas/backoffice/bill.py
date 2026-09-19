from ..base import BaseSchema, BaseResponseSchema, add_padded_id
from pydantic import field_validator
from typing import Optional
from datetime import datetime


class BillSettleRequest(BaseSchema):
    """收费员结算请求"""
    payment_method: str = "cash"  # cash 现金 / card 刷卡

    @field_validator("payment_method")
    @classmethod
    def validate_payment_method(cls, v: str) -> str:
        # 线上支付走患者端接口，窗口只能收现金或刷卡
        allowed = {"cash", "card"}
        if v not in allowed:
            raise ValueError(f"payment_method 必须是以下之一: {', '.join(sorted(allowed))}")
        return v


@add_padded_id()
class BillResponse(BaseResponseSchema):
    """账单响应（收费员端）"""
    patient_id: int
    appointment_id: int
    amount: float
    status: str  # unpaid / paid
    paid_at: Optional[datetime] = None
    payment_method: Optional[str] = None  # online / cash / card
    paid_by_type: Optional[str] = None  # patient / cashier
    cashier_id: Optional[int] = None
    padded_id: Optional[str] = None
    patient_name: Optional[str] = None
    cashier_name: Optional[str] = None
