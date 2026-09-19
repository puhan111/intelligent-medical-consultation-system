from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.client.medical_record import MedicalRecordResponse
from app.services.client.medical_record import medical_record_service
from app.api.client.deps import get_current_user
from app.models.user import User
from app.schemas.response import ApiResponse
from app.schemas.paginator import Paginator


router = APIRouter()


@router.get("", response_model=list[MedicalRecordResponse])
async def list_my_medical_records(
    page: int = 1,
    per_page: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取我的病历列表（分页）"""
    query = await medical_record_service.get_my_records_query(db, current_user.id)

    paginator = Paginator(query, db)
    result = await paginator.paginate(page, per_page)
    response_items = await medical_record_service.list_records(db, result.items)

    return ApiResponse.success(data={
        "items": response_items,
        "total": result.total,
        "per_page": result.per_page,
        "current_page": result.current_page,
        "last_page": result.last_page,
        "has_more": result.has_more
    })
