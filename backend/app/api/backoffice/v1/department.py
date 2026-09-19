from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db, transaction
from app.schemas.backoffice.department import (
    DepartmentCreate,
    DepartmentResponse,
    DepartmentUpdate,
    DepartmentImportRequest,
    DepartmentImportResult,
)
from app.services.backoffice.department import department_service
from app.api.backoffice.deps import get_current_admin
from app.models.admin import Admin
from app.schemas.response import ApiResponse
from app.schemas.paginator import Paginator
from app.exceptions.http_exceptions import APIException


router = APIRouter()


@router.post("", response_model=DepartmentResponse)
async def create_department(
    department_data: DepartmentCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """创建科室（仅超级管理员）"""
    if not current_admin.role == "superadmin":
        raise APIException(
            status_code=403,
            message="Not enough permissions"
        )

    async with transaction(db):
        result = await department_service.create_department(db, department_data)
        return ApiResponse.success(data=DepartmentResponse.model_validate(result))


@router.get("", response_model=list[DepartmentResponse])
async def list_departments(
    page: int = 1,
    per_page: int = 10,
    name: str = None,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """获取科室列表（分页）"""
    query = await department_service.get_departments_query(db, name=name)

    paginator = Paginator(query, db)
    result = await paginator.paginate(page, per_page)
    result = result.map(DepartmentResponse)

    return result.response()


@router.get("/{department_id}", response_model=DepartmentResponse)
async def get_department(
    department_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """获取科室详情"""
    result = await department_service.get_department(db, department_id)
    if not result:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Department not found"
        )

    return ApiResponse.success(data=DepartmentResponse.model_validate(result))


@router.put("/{department_id}", response_model=DepartmentResponse)
async def update_department(
    department_id: int,
    department_data: DepartmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """更新科室信息（仅超级管理员）"""
    if not current_admin.role == "superadmin":
        raise APIException(
            status_code=403,
            message="Not enough permissions"
        )

    async with transaction(db):
        result = await department_service.update_department(db, department_id, department_data.model_dump(exclude_unset=True))
        if not result:
            raise APIException(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Department not found"
            )

        return ApiResponse.success(data=DepartmentResponse.model_validate(result))


@router.delete("/{department_id}")
async def delete_department(
    department_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """删除科室（仅超级管理员）"""
    if not current_admin.role == "superadmin":
        raise APIException(
            status_code=403,
            message="Not enough permissions"
        )

    async with transaction(db):
        result = await department_service.delete_department(db, department_id)
        if not result:
            raise APIException(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Department not found"
            )

        return ApiResponse.success_without_data()


@router.post("/import-md", response_model=DepartmentImportResult)
async def import_departments_from_markdown(
    import_data: DepartmentImportRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """批量导入科室（Markdown格式，## 标题为科室名，仅超级管理员）"""
    if not current_admin.role == "superadmin":
        raise APIException(status_code=403, message="Not enough permissions")

    async with transaction(db):
        result = await department_service.import_from_markdown(db, import_data.content)
        return ApiResponse.success(data=result)
