from sqlalchemy import Column, Integer, String, Text, ForeignKey
from .base import BaseModel


class Doctor(BaseModel):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    admin_id = Column(Integer, ForeignKey("admins.id"), nullable=False, unique=True, index=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False, index=True)
    title = Column(String(50), nullable=True)
    introduction = Column(Text, nullable=True)
