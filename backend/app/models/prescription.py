from sqlalchemy import Boolean, Column, Integer, String, ForeignKey, DECIMAL
from .base import BaseModel


class Prescription(BaseModel):
    """处方"""
    __tablename__ = "prescriptions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False, index=True)
    status = Column(
        String(20),
        nullable=False,
        default="pending",
        index=True,
        comment="pending: 待发药, dispensed: 已发药"
    )


class PrescriptionItem(BaseModel):
    """处方明细"""
    __tablename__ = "prescription_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    prescription_id = Column(Integer, ForeignKey("prescriptions.id"), nullable=False, index=True)
    drug_name = Column(String(200), nullable=False, comment="药品名称快照")
    dosage = Column(String(100), nullable=False)
    quantity = Column(Integer, nullable=False)
    drug_id = Column(
        Integer,
        ForeignKey("drugs.id"),
        nullable=True,
        index=True,
        comment="关联药品目录。为空表示存量的自由文本药名"
    )
    unit_price = Column(
        DECIMAL(10, 2),
        nullable=True,
        comment="单价快照。为空表示存量数据，药费按 0 计"
    )
    is_selected = Column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="患者是否选购该药。取消勾选视为拒药，药师不再配发"
    )
