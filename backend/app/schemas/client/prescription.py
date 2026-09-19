from ..base import BaseSchema, BaseResponseSchema, add_padded_id
from typing import Optional, List


class PrescriptionItemResponse(BaseSchema):
    """处方明细（患者端，含价格与勾选状态）"""
    id: int
    drug_name: str
    dosage: str
    quantity: int
    unit_price: Optional[float] = None
    subtotal: Optional[float] = None
    is_selected: bool


class ItemSelectionRequest(BaseSchema):
    """勾选/取消勾选某项药品"""
    is_selected: bool


@add_padded_id()
class PrescriptionResponse(BaseResponseSchema):
    """处方响应（患者端）"""
    appointment_id: int
    status: str  # pending / dispensed
    padded_id: Optional[str] = None
    doctor_name: Optional[str] = None
    department_name: Optional[str] = None
    items: List[PrescriptionItemResponse] = []
    # 已勾选项的药费合计
    selected_total: float = 0
    # 处方账单状态：none 未生成 / unpaid 待支付 / paid 已支付
    bill_status: str = "none"
    bill_id: Optional[int] = None
    # 账单生成并支付后不可再改勾选，避免金额与实际配药不一致
    can_modify_selection: bool = True
