from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from app.models.doctor import Doctor
from app.models.admin import Admin, UserRole
from app.models.department import Department
from app.schemas.backoffice.doctor import DoctorCreate, DoctorResponse
from app.exceptions.http_exceptions import APIException
from app.core.security import AuthBase
from typing import List, Optional
from fastapi import status


class DoctorService:
    @staticmethod
    async def _to_response(db: AsyncSession, doctor: Doctor) -> DoctorResponse:
        """组装医生详情响应（补充关联的管理员与科室信息）"""
        admin_query = select(Admin).where(Admin.id == doctor.admin_id)
        admin = (await db.execute(admin_query)).scalar_one_or_none()

        department_query = select(Department).where(Department.id == doctor.department_id)
        department = (await db.execute(department_query)).scalar_one_or_none()

        response = DoctorResponse.model_validate(doctor)
        if admin:
            response.first_name = admin.first_name
            response.last_name = admin.last_name
            response.email = admin.email
        if department:
            response.department_name = department.name

        return response

    @staticmethod
    async def create_doctor(db: AsyncSession, doctor_data: DoctorCreate) -> DoctorResponse:
        """创建医生（同步创建关联的管理员账号）"""
        department_query = select(Department).where(Department.id == doctor_data.department_id)
        result = await db.execute(department_query)
        if not result.scalar_one_or_none():
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Department not found"
            )

        email_query = select(Admin).where(Admin.email == doctor_data.email)
        result = await db.execute(email_query)
        if result.scalar_one_or_none():
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Email already exists"
            )

        admin = Admin(
            email=doctor_data.email,
            first_name=doctor_data.first_name,
            last_name=doctor_data.last_name,
            password=AuthBase.hash_token(doctor_data.password),
            role=UserRole.DOCTOR,
            is_active=True
        )
        db.add(admin)
        await db.flush()

        doctor = Doctor(
            admin_id=admin.id,
            department_id=doctor_data.department_id,
            title=doctor_data.title,
            introduction=doctor_data.introduction
        )
        db.add(doctor)
        await db.flush()
        await db.refresh(doctor)

        return await DoctorService._to_response(db, doctor)

    @staticmethod
    async def get_doctor(db: AsyncSession, doctor_id: int) -> Optional[DoctorResponse]:
        """获取医生详情"""
        doctor_query = select(Doctor).where(Doctor.id == doctor_id)
        result = await db.execute(doctor_query)
        doctor = result.scalar_one_or_none()

        if not doctor:
            return None

        return await DoctorService._to_response(db, doctor)

    @staticmethod
    async def get_doctors_query(db: AsyncSession, department_id: int = None, title: str = None):
        """获取用于分页的医生查询对象"""
        query = select(Doctor)

        if department_id:
            query = query.where(Doctor.department_id == department_id)

        if title:
            query = query.where(Doctor.title.ilike(f"%{title}%"))

        query = query.order_by(Doctor.created_at.desc())

        return query

    @staticmethod
    async def list_doctors(db: AsyncSession, doctors: List[Doctor]) -> List[DoctorResponse]:
        """将医生列表批量转换为响应模型"""
        return [await DoctorService._to_response(db, doctor) for doctor in doctors]

    @staticmethod
    async def update_doctor(db: AsyncSession, doctor_id: int, doctor_data: dict) -> Optional[DoctorResponse]:
        """更新医生信息"""
        doctor_query = select(Doctor).where(Doctor.id == doctor_id)
        result = await db.execute(doctor_query)
        doctor = result.scalar_one_or_none()

        if not doctor:
            return None

        update_data = {}

        if "department_id" in doctor_data:
            department_query = select(Department).where(Department.id == doctor_data["department_id"])
            result = await db.execute(department_query)
            if not result.scalar_one_or_none():
                raise APIException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message="Department not found"
                )
            update_data["department_id"] = doctor_data["department_id"]

        if "title" in doctor_data:
            update_data["title"] = doctor_data["title"]

        if "introduction" in doctor_data:
            update_data["introduction"] = doctor_data["introduction"]

        if update_data:
            stmt = update(Doctor).where(Doctor.id == doctor_id).values(**update_data)
            await db.execute(stmt)

            doctor_query = select(Doctor).where(Doctor.id == doctor_id)
            result = await db.execute(doctor_query)
            doctor = result.scalar_one_or_none()

        return await DoctorService._to_response(db, doctor)

    @staticmethod
    async def delete_doctor(db: AsyncSession, doctor_id: int) -> bool:
        """删除医生（同步删除关联的管理员账号）"""
        doctor_query = select(Doctor).where(Doctor.id == doctor_id)
        result = await db.execute(doctor_query)
        doctor = result.scalar_one_or_none()

        if not doctor:
            return False

        admin_id = doctor.admin_id

        stmt = delete(Doctor).where(Doctor.id == doctor_id)
        await db.execute(stmt)

        from app.models.token import AdminToken
        delete_tokens_stmt = delete(AdminToken).where(AdminToken.admin_id == admin_id)
        await db.execute(delete_tokens_stmt)

        delete_admin_stmt = delete(Admin).where(Admin.id == admin_id)
        await db.execute(delete_admin_stmt)

        return True


doctor_service = DoctorService()
