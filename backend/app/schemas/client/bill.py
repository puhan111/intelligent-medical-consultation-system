from ..base import BaseSchema, BaseResponseSchema, add_padded_id
from typing import List, Optional
from datetime import datetime


class PaymentOrderResponse(BaseSchema):
    """支付流水响应（患者端）"""
    order_no: str
    amount: float
    channel: str  # online / cash / card
    status: str  # pending / success / failed
    fail_reason: Optional[str] = None
    paid_at: Optional[datetime] = None


class BillItemResponse(BaseSchema):
    """账单明细行"""
    item_type: str  # consultation / medication
    name: str
    unit_price: float
    quantity: int
    subtotal: float


@add_padded_id()
class BillResponse(BaseResponseSchema):
    """账单响应（患者端）"""
    appointment_id: int
    amount: float
    status: str  # unpaid / paid
    bill_type: str = "consultation"  # consultation / prescription
    prescription_id: Optional[int] = None
    paid_at: Optional[datetime] = None
    payment_method: Optional[str] = None  # online / cash / card
    paid_by_type: Optional[str] = None  # patient / cashier
    padded_id: Optional[str] = None
    items: List[BillItemResponse] = []
