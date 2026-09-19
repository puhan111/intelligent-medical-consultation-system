import re
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from app.models.department import Department
from app.models.doctor import Doctor
from app.schemas.backoffice.department import DepartmentCreate, DepartmentImportResult
from app.exceptions.http_exceptions import APIException
from typing import List, Optional
from fastapi import status


class DepartmentService:
    @staticmethod
    async def create_department(db: AsyncSession, department_data: DepartmentCreate) -> Department:
        """创建科室"""
        name_query = select(Department).where(Department.name == department_data.name)
        result = await db.execute(name_query)
        if result.scalar_one_or_none():
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Department name already exists"
            )

        department = Department(
            name=department_data.name,
            description=department_data.description
        )

        db.add(department)
        await db.flush()
        await db.refresh(department)

        return department

    @staticmethod
    async def get_department(db: AsyncSession, department_id: int) -> Optional[Department]:
        """获取科室详情"""
        department_query = select(Department).where(Department.id == department_id)
        result = await db.execute(department_query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_departments_query(db: AsyncSession, name: str = None):
        """获取用于分页的科室查询对象"""
        query = select(Department)

        if name:
            query = query.where(Department.name.ilike(f"%{name}%"))

        query = query.order_by(Department.created_at.desc())

        return query

    @staticmethod
    async def update_department(db: AsyncSession, department_id: int, department_data: dict) -> Optional[Department]:
        """更新科室信息"""
        department_query = select(Department).where(Department.id == department_id)
        result = await db.execute(department_query)
        department = result.scalar_one_or_none()

        if not department:
            return None

        update_data = {}

        if "name" in department_data and department_data["name"] != department.name:
            name_query = select(Department).where(
                Department.name == department_data["name"],
                Department.id != department_id
            )
            result = await db.execute(name_query)
            if result.scalar_one_or_none():
                raise APIException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message="Department name already exists"
                )
            update_data["name"] = department_data["name"]

        if "description" in department_data:
            update_data["description"] = department_data["description"]

        if update_data:
            stmt = update(Department).where(Department.id == department_id).values(**update_data)
            await db.execute(stmt)

            department_query = select(Department).where(Department.id == department_id)
            result = await db.execute(department_query)
            department = result.scalar_one_or_none()

        return department

    @staticmethod
    async def delete_department(db: AsyncSession, department_id: int) -> bool:
        """删除科室"""
        department_query = select(Department).where(Department.id == department_id)
        result = await db.execute(department_query)
        department = result.scalar_one_or_none()

        if not department:
            return False

        # 若科室下仍有医生，禁止删除
        doctor_query = select(Doctor).where(Doctor.department_id == department_id)
        result = await db.execute(doctor_query)
        if result.scalar_one_or_none():
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Cannot delete department with doctors assigned"
            )

        stmt = delete(Department).where(Department.id == department_id)
        await db.execute(stmt)

        return True

    @staticmethod
    def parse_markdown(content: str) -> List[dict]:
        """解析科室 Markdown：## 标题为科室名，标题下方文本为描述，直到下一个## 或文件结束"""
        sections = re.split(r"^##\s+(.+)$", content, flags=re.MULTILINE)
        # re.split 结果为 [前置文本, 标题1, 正文1, 标题2, 正文2, ...]
        parsed = []
        for i in range(1, len(sections), 2):
            name = sections[i].strip()
            description = sections[i + 1].strip() if i + 1 < len(sections) else ""
            if name:
                parsed.append({"name": name, "description": description or None})
        return parsed

    @staticmethod
    async def import_from_markdown(db: AsyncSession, content: str) -> DepartmentImportResult:
        """批量导入科室，已存在的同名科室跳过"""
        parsed = DepartmentService.parse_markdown(content)

        existing_query = select(Department.name)
        existing_names = set((await db.execute(existing_query)).scalars().all())

        created, skipped = [], []
        for item in parsed:
            if item["name"] in existing_names:
                skipped.append(item["name"])
                continue
            db.add(Department(name=item["name"], description=item["description"]))
            existing_names.add(item["name"])
            created.append(item["name"])

        await db.flush()
        return DepartmentImportResult(created=created, skipped=skipped)


department_service = DepartmentService()
