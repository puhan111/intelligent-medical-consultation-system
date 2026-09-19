from sqlalchemy import Column, Integer, String, ForeignKey, TIMESTAMP
from .base import BaseModel


class DispenseRecord(BaseModel):
    """发药记录"""
    __tablename__ = "dispense_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    prescription_id = Column(Integer, ForeignKey("prescriptions.id"), nullable=False, index=True)
    pharmacist_id = Column(Integer, ForeignKey("admins.id"), nullable=False, index=True)
    dispensed_at = Column(TIMESTAMP(timezone=True), nullable=False)
    status = Column(String(20), nullable=False, default="dispensed")
