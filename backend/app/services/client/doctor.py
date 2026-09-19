from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.doctor import Doctor
from app.models.admin import Admin
from app.models.department import Department
from app.schemas.client.doctor import DoctorResponse
from typing import List, Optional


class DoctorService:
    @staticmethod
    async def _to_response(db: AsyncSession, doctor: Doctor) -> DoctorResponse:
        """组装医生详情响应（患者端，脱敏展示）"""
        admin_query = select(Admin).where(Admin.id == doctor.admin_id)
        admin = (await db.execute(admin_query)).scalar_one_or_none()

        department_query = select(Department).where(Department.id == doctor.department_id)
        department = (await db.execute(department_query)).scalar_one_or_none()

        response = DoctorResponse.model_validate(doctor)
        if admin:
            response.first_name = admin.first_name
            response.last_name = admin.last_name
        if department:
            response.department_name = department.name

        return response

    @staticmethod
    async def get_doctors_query(db: AsyncSession, department_id: int = None):
        """获取医生列表查询对象（供患者端浏览）"""
        query = select(Doctor)

        if department_id:
            query = query.where(Doctor.department_id == department_id)

        return query

    @staticmethod
    async def list_doctors(db: AsyncSession, doctors: List[Doctor]) -> List[DoctorResponse]:
        """将医生列表批量转换为响应模型"""
        return [await DoctorService._to_response(db, doctor) for doctor in doctors]

    @staticmethod
    async def get_doctor(db: AsyncSession, doctor_id: int) -> Optional[DoctorResponse]:
        """获取医生详情"""
        doctor_query = select(Doctor).where(Doctor.id == doctor_id)
        result = await db.execute(doctor_query)
        doctor = result.scalar_one_or_none()

        if not doctor:
            return None

        return await DoctorService._to_response(db, doctor)


doctor_service = DoctorService()
