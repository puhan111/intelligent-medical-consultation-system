from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.medical_record import MedicalRecord
from app.models.appointment import Appointment
from app.models.user import User
from app.schemas.backoffice.medical_record import MedicalRecordCreate, MedicalRecordResponse
from app.exceptions.http_exceptions import APIException
from fastapi import status


class MedicalRecordService:
    @staticmethod
    async def _to_response(db: AsyncSession, record: MedicalRecord) -> MedicalRecordResponse:
        """组装病历响应（补充患者姓名）"""
        user_query = select(User).where(User.id == record.patient_id)
        user = (await db.execute(user_query)).scalar_one_or_none()

        response = MedicalRecordResponse.model_validate(record)
        if user:
            response.patient_name = f"{user.last_name}{user.first_name}" if user.last_name and user.first_name else user.email

        return response

    @staticmethod
    async def create_medical_record(
        db: AsyncSession,
        doctor_id: int,
        record_data: MedicalRecordCreate
    ) -> MedicalRecordResponse:
        """医生录入病历（只能为分配给自己的预约录入）"""
        appointment_query = select(Appointment).where(
            Appointment.id == record_data.appointment_id,
            Appointment.doctor_id == doctor_id
        )
        appointment = (await db.execute(appointment_query)).scalar_one_or_none()
        if not appointment:
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Appointment not found"
            )

        record = MedicalRecord(
            appointment_id=appointment.id,
            patient_id=appointment.patient_id,
            doctor_id=doctor_id,
            diagnosis=record_data.diagnosis,
            content=record_data.content
        )
        db.add(record)
        await db.flush()
        await db.refresh(record)

        return await MedicalRecordService._to_response(db, record)


medical_record_service = MedicalRecordService()
