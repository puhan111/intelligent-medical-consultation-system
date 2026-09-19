from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db, transaction
from kombu.exceptions import OperationalError
from app.schemas.client.bill import BillResponse, PaymentOrderResponse
from app.schedule.jobs.payment_callback import execute as payment_callback_task
from app.services.client.bill import bill_service
from app.api.client.deps import get_current_user
from app.models.user import User
from app.schemas.response import ApiResponse
from app.schemas.paginator import Paginator
from app.exceptions.http_exceptions import APIException


router = APIRouter()


@router.get("", response_model=list[BillResponse])
async def list_my_bills(
    page: int = 1,
    per_page: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取我的账单列表（分页）"""
    query = await bill_service.get_my_bills_query(db, current_user.id)

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


@router.post("/{bill_id}/pay", response_model=PaymentOrderResponse)
async def pay_bill(
    bill_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    患者发起线上支付（模拟）

    立即返回 pending 流水，随后由支付回调任务确认到账，
    前端可轮询 GET /bills/{bill_id}/payment-status 获取结果。
    """
    async with transaction(db):
        order = await bill_service.pay_bill(db, current_user.id, bill_id)
        if not order:
            raise APIException(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Bill not found"
            )
        order_id = order.id
        response = PaymentOrderResponse.model_validate(order)

    # 事务提交后再投递，否则回调任务可能查不到刚创建的流水
    try:
        payment_callback_task.apply_async(args=[order_id], countdown=3)
    except OperationalError:
        raise APIException(
            code=1005,
            message="Task queue unavailable, please retry later",
            status_code=503
        )

    return ApiResponse.success(data=response)


@router.get("/{bill_id}/payment-status", response_model=PaymentOrderResponse)
async def get_payment_status(
    bill_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """查询账单最近一条支付流水状态（供前端轮询支付结果）"""
    order = await bill_service.get_payment_status(db, current_user.id, bill_id)
    if not order:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Payment order not found"
        )

    return ApiResponse.success(data=PaymentOrderResponse.model_validate(order))
