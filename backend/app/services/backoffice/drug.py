from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from fastapi import status
from typing import List, Optional

from app.models.drug import Drug
from app.schemas.backoffice.drug import DrugCreate, DrugResponse
from app.exceptions.http_exceptions import APIException


class DrugService:
    @staticmethod
    def get_drugs_query(keyword: Optional[str] = None, is_active: Optional[bool] = None):
        """药品目录查询对象（供分页）"""
        query = select(Drug)

        if keyword and keyword.strip():
            query = query.where(Drug.name.ilike(f"%{keyword.strip()}%"))

        if is_active is not None:
            query = query.where(Drug.is_active == is_active)

        return query.order_by(Drug.name.asc())

    @staticmethod
    def list_drugs(drugs: List[Drug]) -> List[DrugResponse]:
        """批量转换为响应模型"""
        return [DrugResponse.model_validate(d) for d in drugs]

    @staticmethod
    async def create_drug(db: AsyncSession, drug_data: DrugCreate) -> DrugResponse:
        """新增药品，药品名不可重复"""
        existing = (
            await db.execute(select(Drug).where(Drug.name == drug_data.name))
        ).scalar_one_or_none()
        if existing:
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Drug name already exists",
            )

        drug = Drug(**drug_data.model_dump())
        db.add(drug)
        await db.flush()
        await db.refresh(drug)

        return DrugResponse.model_validate(drug)

    @staticmethod
    async def update_drug(
        db: AsyncSession, drug_id: int, update_data: dict
    ) -> Optional[DrugResponse]:
        """更新药品。改名时校验不与其它药品重名"""
        drug = (
            await db.execute(select(Drug).where(Drug.id == drug_id))
        ).scalar_one_or_none()
        if not drug:
            return None

        new_name = update_data.get("name")
        if new_name and new_name != drug.name:
            dup = (
                await db.execute(
                    select(Drug).where(Drug.name == new_name, Drug.id != drug_id)
                )
            ).scalar_one_or_none()
            if dup:
                raise APIException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message="Drug name already exists",
                )

        if update_data:
            await db.execute(update(Drug).where(Drug.id == drug_id).values(**update_data))
            drug = (
                await db.execute(select(Drug).where(Drug.id == drug_id))
            ).scalar_one_or_none()

        return DrugResponse.model_validate(drug)

    @staticmethod
    async def deactivate_drug(db: AsyncSession, drug_id: int) -> bool:
        """
        停用药品（软删除）

        不做物理删除，否则历史处方的 drug_id 外键会失效。
        停用后医生不可再选，但既有处方仍能正常显示。
        """
        drug = (
            await db.execute(select(Drug).where(Drug.id == drug_id))
        ).scalar_one_or_none()
        if not drug:
            return False

        await db.execute(update(Drug).where(Drug.id == drug_id).values(is_active=False))
        return True


drug_service = DrugService()
