"""
支付流水服务

两个渠道共用这一套逻辑，保证账单状态只由成功流水派生：
- 患者线上支付：创建 pending 流水 -> Celery 模拟支付回调 -> 回调置 success 并同步账单
- 收费员窗口收款：现金/刷卡当场到手，直接创建 success 流水并同步账单
"""
import random
from datetime import datetime, UTC
from decimal import Decimal
from typing import Optional, Tuple

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bill import Bill
from app.models.payment_order import PaymentOrder


def generate_order_no() -> str:
    """生成支付流水号：PAY + 时间戳 + 6 位随机数"""
    return f"PAY{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}{random.randint(100000, 999999)}"


async def get_success_order(db: AsyncSession, bill_id: int) -> Optional[PaymentOrder]:
    """查询账单的成功支付流水"""
    query = select(PaymentOrder).where(
        PaymentOrder.bill_id == bill_id,
        PaymentOrder.status == "success",
    )
    return (await db.execute(query)).scalar_one_or_none()


async def get_pending_order(db: AsyncSession, bill_id: int) -> Optional[PaymentOrder]:
    """查询账单进行中的支付流水（用于提示「患者正在线上支付」）"""
    query = select(PaymentOrder).where(
        PaymentOrder.bill_id == bill_id,
        PaymentOrder.status == "pending",
    )
    return (await db.execute(query)).scalar_one_or_none()


async def create_order(
    db: AsyncSession,
    bill: Bill,
    channel: str,
    operator_type: str,
    operator_id: int,
    status: str = "pending",
) -> PaymentOrder:
    """创建支付流水。status=success 时同时同步账单为已付"""
    order = PaymentOrder(
        bill_id=bill.id,
        order_no=generate_order_no(),
        amount=bill.amount,
        channel=channel,
        status=status,
        operator_type=operator_type,
        operator_id=operator_id,
        paid_at=datetime.now(UTC) if status == "success" else None,
    )
    db.add(order)
    await db.flush()

    if status == "success":
        await _sync_bill_paid(db, bill.id, order)

    return order


async def confirm_order(db: AsyncSession, order_id: int) -> Tuple[str, Optional[str]]:
    """
    确认支付流水（模拟支付网关回调）

    Returns:
        (结果状态, 失败原因)
    """
    order = (
        await db.execute(select(PaymentOrder).where(PaymentOrder.id == order_id))
    ).scalar_one_or_none()
    if not order:
        return "not_found", None

    # 幂等：回调重复到达时直接返回，不重复写库
    if order.status != "pending":
        return f"already_{order.status}", None

    bill = (await db.execute(select(Bill).where(Bill.id == order.bill_id))).scalar_one_or_none()
    if not bill:
        await _fail_order(db, order, "Bill not found")
        return "failed", "Bill not found"

    # 回调期间账单已被其它渠道付掉（如收费员抢先在窗口收了现金）
    if bill.status == "paid":
        await _fail_order(db, order, "Bill already paid by another channel")
        return "failed", "Bill already paid by another channel"

    order.status = "success"
    order.paid_at = datetime.now(UTC)
    await db.flush()
    await _sync_bill_paid(db, bill.id, order)
    await db.commit()
    return "success", None


async def _fail_order(db: AsyncSession, order: PaymentOrder, reason: str) -> None:
    """将流水标记为失败并落库"""
    order.status = "failed"
    order.fail_reason = reason
    await db.flush()
    await db.commit()


async def _sync_bill_paid(db: AsyncSession, bill_id: int, order: PaymentOrder) -> None:
    """依据成功流水同步账单状态（账单已付状态的唯一来源）"""
    values = {
        "status": "paid",
        "paid_at": order.paid_at,
        "payment_method": order.channel,
        "paid_by_type": order.operator_type,
    }
    if order.operator_type == "cashier":
        values["cashier_id"] = order.operator_id

    await db.execute(update(Bill).where(Bill.id == bill_id).values(**values))


def to_decimal(value) -> Decimal:
    """金额统一转 Decimal，避免浮点误差"""
    return Decimal(str(value))
