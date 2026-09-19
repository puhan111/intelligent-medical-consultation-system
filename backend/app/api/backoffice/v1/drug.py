from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db, transaction
from app.schemas.backoffice.drug import DrugCreate, DrugResponse, DrugUpdate
from app.services.backoffice.drug import drug_service
from app.api.backoffice.deps import get_current_admin
from app.models.admin import Admin
from app.schemas.response import ApiResponse
from app.schemas.paginator import Paginator
from app.exceptions.http_exceptions import APIException


router = APIRouter()


def _require_superadmin(current_admin: Admin) -> None:
    """药品目录维护仅限超级管理员"""
    if current_admin.role != "superadmin":
        raise APIException(status_code=403, message="Not enough permissions")


@router.get("", response_model=list[DrugResponse])
async def list_drugs(
    page: int = 1,
    per_page: int = 20,
    keyword: str = None,
    is_active: bool = None,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """
    药品目录列表

    医生开处方需要读目录，故不限超管；写操作才限超管。
    """
    query = drug_service.get_drugs_query(keyword=keyword, is_active=is_active)
    result = await Paginator(query, db).paginate(page, min(per_page, 200))

    return ApiResponse.success(data={
        "items": drug_service.list_drugs(result.items),
        "total": result.total,
        "per_page": result.per_page,
        "current_page": result.current_page,
        "last_page": result.last_page,
        "has_more": result.has_more,
    })


@router.post("", response_model=DrugResponse)
async def create_drug(
    drug_data: DrugCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """新增药品（仅超级管理员）"""
    _require_superadmin(current_admin)

    async with transaction(db):
        result = await drug_service.create_drug(db, drug_data)
        return ApiResponse.success(data=result)


@router.put("/{drug_id}", response_model=DrugResponse)
async def update_drug(
    drug_id: int,
    drug_data: DrugUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """更新药品（仅超级管理员）"""
    _require_superadmin(current_admin)

    async with transaction(db):
        result = await drug_service.update_drug(
            db, drug_id, drug_data.model_dump(exclude_unset=True)
        )
        if not result:
            raise APIException(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Drug not found"
            )
        return ApiResponse.success(data=result)


@router.delete("/{drug_id}")
async def deactivate_drug(
    drug_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """停用药品（软删除，仅超级管理员）"""
    _require_superadmin(current_admin)

    async with transaction(db):
        if not await drug_service.deactivate_drug(db, drug_id):
            raise APIException(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Drug not found"
            )
        return ApiResponse.success_without_data()
