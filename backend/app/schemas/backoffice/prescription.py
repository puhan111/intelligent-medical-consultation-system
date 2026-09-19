from ..base import BaseSchema, BaseResponseSchema, add_padded_id
from pydantic import Field, model_validator
from typing import Optional, List


class PrescriptionItemCreate(BaseSchema):
    """
    处方明细

    优先传 drug_id 从药品目录选药，后端据此快照药名与单价。
    仅当无法从目录选择时才回退到自由文本 drug_name（此时无价格，药费按 0 计）。
    """
    drug_id: Optional[int] = None
    drug_name: Optional[str] = Field(None, max_length=200)
    dosage: str = Field(..., min_length=1, max_length=100)
    quantity: int = Field(..., gt=0)

    @model_validator(mode="after")
    def check_drug_source(self):
        if self.drug_id is None and not (self.drug_name or "").strip():
            raise ValueError("必须提供 drug_id 或 drug_name")
        return self


class PrescriptionCreate(BaseSchema):
    """医生开处方"""
    appointment_id: int
    items: List[PrescriptionItemCreate]


class PrescriptionItemResponse(BaseSchema):
    """处方明细响应"""
    id: int
    drug_name: str
    dosage: str
    quantity: int
    drug_id: Optional[int] = None
    unit_price: Optional[float] = None
    is_selected: bool = True
    subtotal: Optional[float] = None


@add_padded_id()
class PrescriptionResponse(BaseResponseSchema):
    """处方响应（医生/药师端）"""
    appointment_id: int
    doctor_id: int
    status: str  # pending / dispensed
    padded_id: Optional[str] = None
    doctor_name: Optional[str] = None
    patient_name: Optional[str] = None
    items: List[PrescriptionItemResponse] = []
    total_amount: Optional[float] = None
