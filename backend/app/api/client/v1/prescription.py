from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db, transaction
from app.schemas.client.prescription import ItemSelectionRequest, PrescriptionResponse
from app.services.client import prescription as prescription_service
from app.api.client.deps import get_current_user
from app.models.user import User
from app.schemas.response import ApiResponse
from app.schemas.paginator import Paginator


router = APIRouter()


@router.get("", response_model=list[PrescriptionResponse])
async def list_my_prescriptions(
    page: int = 1,
    per_page: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取我的处方列表（含药价与勾选状态，分页）"""
    query = await prescription_service.get_my_prescriptions_query(db, current_user.id)
    result = await Paginator(query, db).paginate(page, per_page)
    items = await prescription_service.list_prescriptions(db, result.items)

    return ApiResponse.success(data={
        "items": items,
        "total": result.total,
        "per_page": result.per_page,
        "current_page": result.current_page,
        "last_page": result.last_page,
        "has_more": result.has_more,
    })


@router.get("/{prescription_id}", response_model=PrescriptionResponse)
async def get_prescription(
    prescription_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取处方详情"""
    result = await prescription_service.get_prescription(db, current_user.id, prescription_id)
    return ApiResponse.success(data=result)


@router.put("/{prescription_id}/items/{item_id}/selection", response_model=PrescriptionResponse)
async def update_item_selection(
    prescription_id: int,
    item_id: int,
    request: ItemSelectionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    勾选或取消勾选某项药品

    取消勾选视为拒药，药师不再配发。已支付药费后不可修改。
    """
    async with transaction(db):
        result = await prescription_service.update_item_selection(
            db, current_user.id, prescription_id, item_id, request.is_selected
        )
        return ApiResponse.success(data=result)


@router.post("/{prescription_id}/bill", response_model=PrescriptionResponse)
async def create_prescription_bill(
    prescription_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    按已勾选药品生成药费账单

    生成后用返回的 bill_id 调 POST /bills/{bill_id}/pay 支付。
    """
    async with transaction(db):
        result = await prescription_service.create_bill(db, current_user.id, prescription_id)
        return ApiResponse.success(data=result)
