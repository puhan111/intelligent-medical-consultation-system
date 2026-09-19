from sqlalchemy import Column, Integer, String, ForeignKey, TIMESTAMP, DECIMAL, Index, text
from .base import BaseModel


class PaymentOrder(BaseModel):
    """
    支付流水（支付尝试记录）

    与账单是多对一：一笔账单可能有多次支付尝试（失败、重试），
    但最多只能有一条 success。账单的已付状态由 success 流水派生，
    不在别处直接改 bills.status，避免两处状态不一致。
    """
    __tablename__ = "payment_orders"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    bill_id = Column(Integer, ForeignKey("bills.id"), nullable=False, index=True)
    order_no = Column(String(40), nullable=False, unique=True, index=True, comment="支付流水号")
    amount = Column(DECIMAL(10, 2), nullable=False)
    channel = Column(
        String(20),
        nullable=False,
        comment="支付渠道：online 线上支付, cash 现金, card 刷卡"
    )
    status = Column(
        String(20),
        nullable=False,
        default="pending",
        index=True,
        comment="pending: 支付中, success: 支付成功, failed: 支付失败"
    )
    operator_type = Column(
        String(20),
        nullable=False,
        comment="发起方：patient 患者自助, cashier 收费员代收"
    )
    operator_id = Column(
        Integer,
        nullable=False,
        comment="发起人 ID（patient 时为 users.id，cashier 时为 admins.id）"
    )
    fail_reason = Column(String(200), nullable=True, comment="支付失败原因")
    paid_at = Column(TIMESTAMP(timezone=True), nullable=True, comment="支付成功时间")

    __table_args__ = (
        # 数据库层面保证一笔账单最多一条成功流水，防并发重复支付
        Index(
            "uq_payment_orders_bill_success",
            "bill_id",
            unique=True,
            postgresql_where=text("status = 'success'"),
        ),
    )
