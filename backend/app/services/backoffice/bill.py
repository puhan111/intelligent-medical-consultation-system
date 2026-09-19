from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, case
from app.models.bill import Bill
from app.models.bill_item import BillItem
from app.models.user import User
from app.schemas.backoffice.bill import BillResponse
from app.services.common import payment
from app.exceptions.http_exceptions import APIException
from typing import List, Optional
from fastapi import status

CONSULTATION_FEE = 100.00


class BillService:
    @staticmethod
    async def _to_response(db: AsyncSession, bill: Bill) -> BillResponse:
        """组装账单响应（补充患者姓名与经办收费员姓名）"""
        user_query = select(User).where(User.id == bill.patient_id)
        user = (await db.execute(user_query)).scalar_one_or_none()

        response = BillResponse.model_validate(bill)
        if user:
            response.patient_name = f"{user.last_name}{user.first_name}" if user.last_name and user.first_name else user.email

        if bill.cashier_id:
            from app.models.admin import Admin
            cashier_query = select(Admin).where(Admin.id == bill.cashier_id)
            cashier = (await db.execute(cashier_query)).scalar_one_or_none()
            if cashier:
                response.cashier_name = (
                    f"{cashier.last_name}{cashier.first_name}"
                    if cashier.last_name and cashier.first_name
                    else cashier.email
                )

        return response

    @staticmethod
    async def create_bill_for_appointment(db: AsyncSession, patient_id: int, appointment_id: int) -> Bill:
        """接诊完成后自动生成问诊费账单（药费走处方账单，患者选购后单独生成）"""
        bill = Bill(
            patient_id=patient_id,
            appointment_id=appointment_id,
            amount=CONSULTATION_FEE,
            bill_type="consultation",
            status="unpaid"
        )
        db.add(bill)
        await db.flush()

        db.add(BillItem(
            bill_id=bill.id,
            item_type="consultation",
            name="挂号问诊费",
            unit_price=CONSULTATION_FEE,
            quantity=1,
            subtotal=CONSULTATION_FEE,
        ))
        await db.flush()
        return bill

    @staticmethod
    async def get_bills_query(db: AsyncSession, status_filter: Optional[str] = None):
        """
        获取账单查询对象（收费员端，用于分页）

        不传 status_filter 时返回全部账单，作为收费记录查询；
        未结算的排在前面，便于收费员优先处理待办。
        """
        query = select(Bill)

        if status_filter:
            query = query.where(Bill.status == status_filter)

        # 未支付优先，其次按创建时间倒序（最新的账单在前）
        query = query.order_by(
            case((Bill.status == "unpaid", 0), else_=1),
            Bill.created_at.desc(),
        )
        return query

    @staticmethod
    async def list_bills(db: AsyncSession, bills: List[Bill]) -> List[BillResponse]:
        """批量转换账单列表为响应模型"""
        return [await BillService._to_response(db, bill) for bill in bills]

    @staticmethod
    async def settle_bill(
        db: AsyncSession,
        bill_id: int,
        cashier_id: int,
        payment_method: str = "cash"
    ) -> Optional[BillResponse]:
        """收费员窗口结算账单（记录经办人与收款方式，便于对账追溯）"""
        bill_query = select(Bill).where(Bill.id == bill_id)
        bill = (await db.execute(bill_query)).scalar_one_or_none()

        if not bill:
            return None

        if bill.status == "paid":
            # 区分「患者已线上支付」和「已在窗口收过款」，避免收费员重复收钱
            if bill.paid_by_type == "patient":
                raise APIException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message="Patient already paid online, no need to collect again"
                )
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Bill already paid"
            )

        # 患者正在线上支付时，避免窗口重复收款
        pending = await payment.get_pending_order(db, bill_id)
        if pending:
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Patient is paying online, please wait or ask the patient to cancel"
            )

        # 现金/刷卡当场到账，无需等回调，直接落成功流水并同步账单
        await payment.create_order(
            db,
            bill,
            channel=payment_method,
            operator_type="cashier",
            operator_id=cashier_id,
            status="success",
        )

        bill_query = select(Bill).where(Bill.id == bill_id)
        bill = (await db.execute(bill_query)).scalar_one_or_none()

        return await BillService._to_response(db, bill)


bill_service = BillService()
