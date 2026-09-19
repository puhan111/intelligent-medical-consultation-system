from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.medical_record import MedicalRecord
from app.models.user import User
from app.schemas.client.medical_record import MedicalRecordResponse
from typing import List


class MedicalRecordService:
    @staticmethod
    async def _to_response(db: AsyncSession, record: MedicalRecord) -> MedicalRecordResponse:
        """组装病历响应（补充医生姓名）"""
        from app.models.doctor import Doctor
        from app.models.admin import Admin

        doctor_query = select(Doctor).where(Doctor.id == record.doctor_id)
        doctor = (await db.execute(doctor_query)).scalar_one_or_none()

        response = MedicalRecordResponse.model_validate(record)
        if doctor:
            admin_query = select(Admin).where(Admin.id == doctor.admin_id)
            admin = (await db.execute(admin_query)).scalar_one_or_none()
            if admin:
                response.doctor_name = f"{admin.last_name}{admin.first_name}" if admin.last_name and admin.first_name else admin.email

        return response

    @staticmethod
    async def get_my_records_query(db: AsyncSession, patient_id: int):
        """获取患者的病历列表查询对象（用于分页）"""
        query = select(MedicalRecord).where(MedicalRecord.patient_id == patient_id)
        query = query.order_by(MedicalRecord.created_at.desc())
        return query

    @staticmethod
    async def list_records(db: AsyncSession, records: List[MedicalRecord]) -> List[MedicalRecordResponse]:
        """批量转换病历列表为响应模型"""
        return [await MedicalRecordService._to_response(db, record) for record in records]


medical_record_service = MedicalRecordService()
