from sqlalchemy import Column, Integer, String, ForeignKey, TIMESTAMP, DECIMAL
from .base import BaseModel


class Bill(BaseModel):
    """账单"""
    __tablename__ = "bills"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=False, index=True)
    amount = Column(DECIMAL(10, 2), nullable=False)
    bill_type = Column(
        String(20),
        nullable=False,
        default="consultation",
        index=True,
        comment="consultation: 问诊费账单, prescription: 处方药费账单"
    )
    prescription_id = Column(
        Integer,
        ForeignKey("prescriptions.id"),
        nullable=True,
        index=True,
        comment="处方账单关联的处方，问诊账单为空"
    )
    status = Column(
        String(20),
        nullable=False,
        default="unpaid",
        index=True,
        comment="unpaid: 未支付, paid: 已支付"
    )
    paid_at = Column(TIMESTAMP(timezone=True), nullable=True)
    payment_method = Column(
        String(20),
        nullable=True,
        comment="支付方式：online 线上支付, cash 现金, card 刷卡"
    )
    paid_by_type = Column(
        String(20),
        nullable=True,
        comment="支付发起方：patient 患者自助, cashier 收费员代收"
    )
    cashier_id = Column(
        Integer,
        ForeignKey("admins.id"),
        nullable=True,
        index=True,
        comment="经办收费员（线上支付时为空）"
    )
