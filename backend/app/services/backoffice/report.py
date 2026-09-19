from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import case, or_, select
from fastapi import status

from app.exceptions.http_exceptions import APIException
from app.models.admin import Admin
from app.models.appointment import Appointment
from app.models.department import Department
from app.models.doctor import Doctor
from app.models.report import Report
from app.models.user import User
from app.schemas.backoffice.report import (
    ExamPendingAppointmentResponse,
    ReportCreate,
    ReportResponse,
)


class ReportService:
    @staticmethod
    def get_patients_query(keyword: str | None = None):
        """返回供检验检查人员选择的患者列表查询。"""
        query = select(User)
        if keyword and keyword.strip():
            pattern = f"%{keyword.strip()}%"
            query = query.where(
                or_(
                    User.email.ilike(pattern),
                    User.first_name.ilike(pattern),
                    User.last_name.ilike(pattern),
                )
            )
        return query.order_by(User.created_at.desc())

    @staticmethod
    async def _to_response(db: AsyncSession, report: Report) -> ReportResponse:
        """组装报告响应（补充患者姓名与邮箱）"""
        user = (
            await db.execute(select(User).where(User.id == report.patient_id))
        ).scalar_one_or_none()

        response = ReportResponse.model_validate(report)
        if user:
            response.patient_email = user.email
            response.patient_name = (
                f"{user.last_name}{user.first_name}"
                if user.last_name and user.first_name
                else user.email
            )
        return response

    @staticmethod
    def get_reports_query(status_filter: str | None = None):
        """
        检验科查看报告列表的查询对象

        不传 status_filter 返回全部；解读失败的排最前，便于优先处理重试。
        """
        query = select(Report)

        if status_filter:
            query = query.where(Report.interpretation_status == status_filter)

        return query.order_by(
            case((Report.interpretation_status == "failed", 0), else_=1),
            Report.created_at.desc(),
        )

    @staticmethod
    async def list_reports(db: AsyncSession, reports: list[Report]) -> list[ReportResponse]:
        """批量转换报告列表为响应模型"""
        return [await ReportService._to_response(db, r) for r in reports]

    @staticmethod
    async def prepare_retry(db: AsyncSession, report_id: int) -> ReportResponse:
        """
        重置报告解读状态为 pending，供重新投递解读任务

        仅允许重试 failed 的报告：pending 可能任务仍在执行，重复投递会产生并发写；
        completed 已有结果，重跑纯属浪费 LLM 额度。
        """
        report = (
            await db.execute(select(Report).where(Report.id == report_id))
        ).scalar_one_or_none()

        if report is None:
            raise APIException(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Report not found",
            )

        if report.interpretation_status == "pending":
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Interpretation is still in progress, please wait",
            )

        if report.interpretation_status == "completed":
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Interpretation already completed, no need to retry",
            )

        # 清空上次失败的残留，避免旧数据与新状态混淆
        report.interpretation_status = "pending"
        report.ai_interpretation = None
        report.interpretation_at = None
        report.referenced_chunks = None
        await db.flush()
        await db.refresh(report)

        return await ReportService._to_response(db, report)

    @staticmethod
    def get_exam_pending_appointments_query(keyword: str | None = None):
        """
        返回等待检查结果的就诊记录，供检验科选择后录入报告

        只列 waiting_exam 状态：医生已确认接诊并开出检查，正等报告回来。
        """
        query = (
            select(Appointment)
            .join(User, User.id == Appointment.patient_id)
            .where(Appointment.status == "waiting_exam")
        )
        if keyword and keyword.strip():
            pattern = f"%{keyword.strip()}%"
            query = query.where(
                or_(
                    User.email.ilike(pattern),
                    User.first_name.ilike(pattern),
                    User.last_name.ilike(pattern),
                )
            )
        return query.order_by(Appointment.appointment_time.asc())

    @staticmethod
    async def list_exam_pending(db: AsyncSession, appointments) -> list[ExamPendingAppointmentResponse]:
        """组装待检查就诊记录（补充科室、医生姓名与已录报告数）"""
        result = []
        for appointment in appointments:
            user = (
                await db.execute(select(User).where(User.id == appointment.patient_id))
            ).scalar_one_or_none()
            if user is None:
                continue
            department = (
                await db.execute(
                    select(Department).where(Department.id == appointment.department_id)
                )
            ).scalar_one_or_none()

            doctor_name = None
            doctor = (
                await db.execute(select(Doctor).where(Doctor.id == appointment.doctor_id))
            ).scalar_one_or_none()
            if doctor:
                admin = (
                    await db.execute(select(Admin).where(Admin.id == doctor.admin_id))
                ).scalar_one_or_none()
                if admin:
                    doctor_name = (
                        f"{admin.last_name}{admin.first_name}"
                        if admin.last_name and admin.first_name
                        else admin.email
                    )

            report_count = len(
                (
                    await db.execute(
                        select(Report.id).where(Report.appointment_id == appointment.id)
                    )
                ).scalars().all()
            )

            result.append(ExamPendingAppointmentResponse(
                id=appointment.id,
                patient_id=appointment.patient_id,
                patient_name=(
                    f"{user.last_name}{user.first_name}"
                    if user.last_name and user.first_name
                    else user.email
                ),
                patient_email=user.email,
                department_name=department.name if department else None,
                doctor_name=doctor_name,
                appointment_time=appointment.appointment_time,
                status=appointment.status,
                report_count=report_count,
            ))
        return result

    @staticmethod
    async def create_report(db: AsyncSession, report_data: ReportCreate) -> ReportResponse:
        """检验科上传报告，落库后由路由层触发异步 AI 解读"""
        patient_exists = await db.scalar(select(User.id).where(User.id == report_data.patient_id))
        if patient_exists is None:
            raise APIException(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Patient not found",
            )

        appointment = (
            await db.execute(
                select(Appointment).where(Appointment.id == report_data.appointment_id)
            )
        ).scalar_one_or_none()
        if appointment is None:
            raise APIException(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Appointment not found",
            )
        if appointment.patient_id != report_data.patient_id:
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Appointment does not belong to the selected patient",
            )
        if appointment.status != "waiting_exam":
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Only appointments waiting for exam results can receive a report",
            )

        report = Report(
            patient_id=report_data.patient_id,
            appointment_id=report_data.appointment_id,
            type=report_data.type,
            content=report_data.content.model_dump(mode="json"),
            interpretation_status="pending",
        )
        db.add(report)
        await db.flush()
        await db.refresh(report)

        return await ReportService._to_response(db, report)


report_service = ReportService()
