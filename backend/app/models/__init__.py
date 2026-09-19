"""
模型集中注册

SQLAlchemy 解析外键需要目标表已在 metadata 中注册。Celery worker 只导入任务
用到的模型，若不在此集中导入，跨表外键（如 reports.patient_id -> users.id）
会在写库时报 NoReferencedTableError。所有新增模型都要加到这里。
"""
from .admin import Admin, UserRole
from .appointment import Appointment
from .base import BaseModel
from .bill import Bill
from .bill_item import BillItem
from .department import Department
from .dispense_record import DispenseRecord
from .doctor import Doctor
from .drug import Drug
from .knowledge_chunk import KnowledgeChunk
from .llm_call_log import LLMCallLog
from .medical_record import MedicalRecord
from .payment_order import PaymentOrder
from .prescription import Prescription, PrescriptionItem
from .rag_query_log import RAGQueryLog
from .report import Report
from .token import AdminToken, Token
from .user import User

__all__ = [
    "Admin",
    "UserRole",
    "Appointment",
    "BaseModel",
    "Bill",
    "BillItem",
    "Department",
    "DispenseRecord",
    "Doctor",
    "Drug",
    "KnowledgeChunk",
    "LLMCallLog",
    "MedicalRecord",
    "PaymentOrder",
    "Prescription",
    "PrescriptionItem",
    "RAGQueryLog",
    "Report",
    "AdminToken",
    "Token",
    "User",
]
