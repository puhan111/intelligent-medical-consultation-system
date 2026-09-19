from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.appointment import Appointment
from app.models.user import User
from app.models.department import Department
from app.models.report import Report
from app.schemas.backoffice.appointment import (
    AppointmentReportSummary,
    AppointmentResponse,
    AppointmentUpdate,
)
from app.exceptions.http_exceptions import APIException
from typing import List, Optional
from fastapi import status


class AppointmentService:
    @staticmethod
    async def _to_response(db: AsyncSession, appointment: Appointment) -> AppointmentResponse:
        """组装预约响应（补充患者、科室名称与本次就诊的检查报告）"""
        user_query = select(User).where(User.id == appointment.patient_id)
        user = (await db.execute(user_query)).scalar_one_or_none()

        department_query = select(Department).where(Department.id == appointment.department_id)
        department = (await db.execute(department_query)).scalar_one_or_none()

        response = AppointmentResponse.model_validate(appointment)
        if user:
            response.patient_name = f"{user.last_name}{user.first_name}" if user.last_name and user.first_name else user.email
        if department:
            response.department_name = department.name

        # 带出本次就诊的检查报告，医生凭报告下诊断
        reports = (
            await db.execute(
                select(Report)
                .where(Report.appointment_id == appointment.id)
                .order_by(Report.created_at.desc())
            )
        ).scalars().all()
        response.reports = [AppointmentReportSummary.model_validate(r) for r in reports]
        response.report_count = len(reports)

        return response

    @staticmethod
    async def get_doctor_appointments_query(db: AsyncSession, doctor_id: int, status_filter: Optional[str] = None):
        """获取医生的接诊预约列表查询对象（用于分页）"""
        query = select(Appointment).where(Appointment.doctor_id == doctor_id)

        if status_filter:
            query = query.where(Appointment.status == status_filter)

        query = query.order_by(Appointment.appointment_time.asc())
        return query

    @staticmethod
    async def list_appointments(db: AsyncSession, appointments: List[Appointment]) -> List[AppointmentResponse]:
        """批量转换预约列表为响应模型"""
        return [await AppointmentService._to_response(db, apt) for apt in appointments]

    @staticmethod
    async def update_appointment_status(
        db: AsyncSession,
        doctor_id: int,
        appointment_id: int,
        update_data: AppointmentUpdate
    ) -> Optional[AppointmentResponse]:
        """医生更新预约状态（只能更新分配给自己的预约）"""
        appointment_query = select(Appointment).where(
            Appointment.id == appointment_id,
            Appointment.doctor_id == doctor_id
        )
        appointment = (await db.execute(appointment_query)).scalar_one_or_none()

        if not appointment:
            return None

        if update_data.status not in ["confirmed", "waiting_exam", "completed"]:
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Invalid status. Only 'confirmed', 'waiting_exam' or 'completed' allowed."
            )

        # 已完成是终态，不允许回退，否则会重复生成账单
        if appointment.status == "completed":
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Appointment already completed"
            )

        if appointment.status == "cancelled":
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Cannot update a cancelled appointment"
            )

        allowed_transitions = {
            "pending": {"confirmed"},
            "confirmed": {"waiting_exam", "completed"},
            "waiting_exam": {"completed"},
        }
        if update_data.status not in allowed_transitions.get(appointment.status, set()):
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=f"Cannot change appointment from '{appointment.status}' to '{update_data.status}'"
            )

        if appointment.status == "waiting_exam" and update_data.status == "completed":
            report_exists = await db.scalar(
                select(Report.id).where(Report.appointment_id == appointment.id).limit(1)
            )
            if report_exists is None:
                raise APIException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message="An exam report is required before completing this appointment",
                )

        stmt = update(Appointment).where(Appointment.id == appointment_id).values(status=update_data.status)
        await db.execute(stmt)

        if update_data.status == "completed":
            from app.services.backoffice.bill import bill_service
            await bill_service.create_bill_for_appointment(db, appointment.patient_id, appointment.id)

        appointment_query = select(Appointment).where(Appointment.id == appointment_id)
        appointment = (await db.execute(appointment_query)).scalar_one_or_none()

        return await AppointmentService._to_response(db, appointment)


appointment_service = AppointmentService()
