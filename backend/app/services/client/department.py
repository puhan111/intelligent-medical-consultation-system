from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.department import Department


class DepartmentService:
    @staticmethod
    async def get_departments_query(db: AsyncSession):
        """获取科室列表查询对象（供患者端浏览）"""
        return select(Department).order_by(Department.name.asc())

    @staticmethod
    async def get_department(db: AsyncSession, department_id: int):
        """获取科室详情"""
        department_query = select(Department).where(Department.id == department_id)
        result = await db.execute(department_query)
        return result.scalar_one_or_none()


department_service = DepartmentService()
