from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db, transaction
from app.schemas.backoffice.bill import BillResponse, BillSettleRequest
from app.services.backoffice.bill import bill_service
from app.api.backoffice.deps import get_current_cashier
from app.models.admin import Admin
from app.schemas.response import ApiResponse
from app.schemas.paginator import Paginator
from app.exceptions.http_exceptions import APIException


router = APIRouter()


@router.get("", response_model=list[BillResponse])
async def list_bills(
    page: int = 1,
    per_page: int = 10,
    status_filter: str = None,
    db: AsyncSession = Depends(get_db),
    current_cashier: Admin = Depends(get_current_cashier)
):
    """
    获取账单列表（收费员）

    Args:
        status_filter: 可选状态过滤，unpaid 待结算 / paid 已结算，不传则返回全部
    """
    if status_filter and status_filter not in ("unpaid", "paid"):
        raise APIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="status_filter must be 'unpaid' or 'paid'"
        )

    query = await bill_service.get_bills_query(db, status_filter=status_filter)

    paginator = Paginator(query, db)
    result = await paginator.paginate(page, per_page)
    response_items = await bill_service.list_bills(db, result.items)

    return ApiResponse.success(data={
        "items": response_items,
        "total": result.total,
        "per_page": result.per_page,
        "current_page": result.current_page,
        "last_page": result.last_page,
        "has_more": result.has_more
    })


@router.post("/{bill_id}/settle", response_model=BillResponse)
async def settle_bill(
    bill_id: int,
    settle_data: BillSettleRequest = BillSettleRequest(),
    db: AsyncSession = Depends(get_db),
    current_cashier: Admin = Depends(get_current_cashier)
):
    """收费员窗口结算账单（记录经办人，便于对账追溯）"""
    async with transaction(db):
        result = await bill_service.settle_bill(
            db,
            bill_id,
            cashier_id=current_cashier.id,
            payment_method=settle_data.payment_method
        )
        if not result:
            raise APIException(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Bill not found"
            )

        return ApiResponse.success(data=result)
