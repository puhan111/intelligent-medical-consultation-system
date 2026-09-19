from sqlalchemy import Column, Integer, String, Text, ForeignKey
from .base import BaseModel


class MedicalRecord(BaseModel):
    """电子病历"""
    __tablename__ = "medical_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False, index=True)
    diagnosis = Column(String(500), nullable=False)
    content = Column(Text, nullable=True)
