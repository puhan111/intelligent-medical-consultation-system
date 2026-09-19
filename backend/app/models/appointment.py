from sqlalchemy import Column, Integer, String, ForeignKey, TIMESTAMP
from sqlalchemy.sql import func
from .base import BaseModel


class Appointment(BaseModel):
    """预约记录"""
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False, index=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False, index=True)
    appointment_time = Column(TIMESTAMP(timezone=True), nullable=False, index=True)
    status = Column(
        String(20),
        nullable=False,
        default="pending",
        index=True,
        comment=(
            "pending: 待确认, confirmed: 已确认, "
            "waiting_exam: 待检查结果（医生已开检查，等检验科出报告）, "
            "completed: 已完成, cancelled: 已取消"
        )
    )
