from sqlalchemy import Column, Integer, String, ForeignKey, DECIMAL
from .base import BaseModel


class BillItem(BaseModel):
    """
    账单明细行

    生成账单时把当时的名称与单价快照进来，之后药品目录调价不影响历史账单金额。
    """
    __tablename__ = "bill_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    bill_id = Column(Integer, ForeignKey("bills.id"), nullable=False, index=True)
    item_type = Column(
        String(20),
        nullable=False,
        comment="consultation: 问诊费, medication: 药费"
    )
    name = Column(String(200), nullable=False, comment="收费项目名称（快照）")
    unit_price = Column(DECIMAL(10, 2), nullable=False, comment="单价快照")
    quantity = Column(Integer, nullable=False, default=1)
    subtotal = Column(DECIMAL(10, 2), nullable=False, comment="小计 = 单价 × 数量")
