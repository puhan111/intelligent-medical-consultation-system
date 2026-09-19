from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.models.department import Department
from app.schemas.client.appointment import AppointmentCreate, AppointmentResponse
from app.exceptions.http_exceptions import APIException
from typing import List, Optional
from fastapi import status


class AppointmentService:
    @staticmethod
    async def _to_response(db: AsyncSession, appointment: Appointment) -> AppointmentResponse:
        """组装预约响应（补充医生和科室名称）"""
        doctor_query = select(Doctor).where(Doctor.id == appointment.doctor_id)
        doctor = (await db.execute(doctor_query)).scalar_one_or_none()

        department_query = select(Department).where(Department.id == appointment.department_id)
        department = (await db.execute(department_query)).scalar_one_or_none()

        response = AppointmentResponse.model_validate(appointment)
        if doctor:
            from app.models.admin import Admin
            admin_query = select(Admin).where(Admin.id == doctor.admin_id)
            admin = (await db.execute(admin_query)).scalar_one_or_none()
            if admin:
                response.doctor_name = f"{admin.last_name}{admin.first_name}" if admin.last_name and admin.first_name else admin.email
        if department:
            response.department_name = department.name

        return response

    @staticmethod
    async def create_appointment(
        db: AsyncSession,
        patient_id: int,
        appointment_data: AppointmentCreate
    ) -> AppointmentResponse:
        """患者创建预约"""
        # 验证医生和科室是否存在
        doctor_query = select(Doctor).where(Doctor.id == appointment_data.doctor_id)
        if not (await db.execute(doctor_query)).scalar_one_or_none():
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Doctor not found"
            )

        department_query = select(Department).where(Department.id == appointment_data.department_id)
        if not (await db.execute(department_query)).scalar_one_or_none():
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Department not found"
            )

        appointment = Appointment(
            patient_id=patient_id,
            doctor_id=appointment_data.doctor_id,
            department_id=appointment_data.department_id,
            appointment_time=appointment_data.appointment_time,
            status="pending"
        )
        db.add(appointment)
        await db.flush()
        await db.refresh(appointment)

        return await AppointmentService._to_response(db, appointment)

    @staticmethod
    async def get_my_appointments_query(db: AsyncSession, patient_id: int):
        """获取患者的预约列表查询对象（用于分页）"""
        query = select(Appointment).where(Appointment.patient_id == patient_id)
        query = query.order_by(Appointment.appointment_time.desc())
        return query

    @staticmethod
    async def list_appointments(db: AsyncSession, appointments: List[Appointment]) -> List[AppointmentResponse]:
        """批量转换预约列表为响应模型"""
        return [await AppointmentService._to_response(db, apt) for apt in appointments]

    @staticmethod
    async def cancel_appointment(db: AsyncSession, patient_id: int, appointment_id: int) -> bool:
        """患者取消预约（只能取消自己的预约）"""
        appointment_query = select(Appointment).where(
            Appointment.id == appointment_id,
            Appointment.patient_id == patient_id
        )
        appointment = (await db.execute(appointment_query)).scalar_one_or_none()

        if not appointment:
            return False

        if appointment.status == "cancelled":
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Appointment already cancelled"
            )

        if appointment.status != "pending":
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Only a pending appointment can be cancelled"
            )

        stmt = update(Appointment).where(Appointment.id == appointment_id).values(status="cancelled")
        await db.execute(stmt)

        return True


appointment_service = AppointmentService()
