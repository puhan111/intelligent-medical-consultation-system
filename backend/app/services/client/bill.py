from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.bill import Bill
from app.models.bill_item import BillItem
from app.models.payment_order import PaymentOrder
from app.schemas.client.bill import BillItemResponse, BillResponse
from app.services.common import payment
from app.exceptions.http_exceptions import APIException
from typing import List, Optional
from fastapi import status


class BillService:
    @staticmethod
    async def get_my_bills_query(db: AsyncSession, patient_id: int):
        """获取患者的账单列表查询对象（用于分页）"""
        query = select(Bill).where(Bill.patient_id == patient_id)
        query = query.order_by(Bill.created_at.desc())
        return query

    @staticmethod
    async def list_bills(db: AsyncSession, bills: List[Bill]) -> List[BillResponse]:
        """批量转换账单列表为响应模型（附带收费明细）"""
        result = []
        for bill in bills:
            response = BillResponse.model_validate(bill)
            items = (
                await db.execute(
                    select(BillItem)
                    .where(BillItem.bill_id == bill.id)
                    .order_by(BillItem.id.asc())
                )
            ).scalars().all()
            response.items = [BillItemResponse.model_validate(i) for i in items]
            result.append(response)
        return result

    @staticmethod
    async def pay_bill(db: AsyncSession, patient_id: int, bill_id: int) -> Optional[PaymentOrder]:
        """
        患者发起线上支付（只能支付自己的账单）

        这里只创建 pending 流水，不直接改账单状态；
        账单由支付回调（app.schedule.jobs.payment_callback）确认后才置为已付。
        """
        bill_query = select(Bill).where(
            Bill.id == bill_id,
            Bill.patient_id == patient_id
        )
        bill = (await db.execute(bill_query)).scalar_one_or_none()

        if not bill:
            return None

        if bill.status == "paid":
            # 区分「窗口已收款」和「自己已付过」，给患者更明确的提示
            if bill.paid_by_type == "cashier":
                raise APIException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message="Bill already settled at the counter"
                )
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Bill already paid"
            )

        # 已有进行中的支付则复用，避免重复下单
        existing = await payment.get_pending_order(db, bill_id)
        if existing:
            return existing

        return await payment.create_order(
            db,
            bill,
            channel="online",
            operator_type="patient",
            operator_id=patient_id,
            status="pending",
        )

    @staticmethod
    async def get_payment_status(
        db: AsyncSession,
        patient_id: int,
        bill_id: int
    ) -> Optional[PaymentOrder]:
        """查询账单最近一条支付流水（供前端轮询支付结果）"""
        bill_query = select(Bill).where(
            Bill.id == bill_id,
            Bill.patient_id == patient_id
        )
        if not (await db.execute(bill_query)).scalar_one_or_none():
            return None

        order_query = (
            select(PaymentOrder)
            .where(PaymentOrder.bill_id == bill_id)
            .order_by(PaymentOrder.created_at.desc())
            .limit(1)
        )
        return (await db.execute(order_query)).scalar_one_or_none()


bill_service = BillService()
