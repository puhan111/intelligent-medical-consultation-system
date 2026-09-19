from sqlalchemy import Boolean, Column, Integer, String, DECIMAL
from .base import BaseModel


class Drug(BaseModel):
    """药品目录（超管维护，医生开处方时从此选药）"""
    __tablename__ = "drugs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(200), unique=True, nullable=False, index=True, comment="药品名称")
    spec = Column(String(100), nullable=True, comment="规格，如 0.25g×24粒")
    unit = Column(String(20), nullable=False, default="盒", comment="计价单位：盒/瓶/粒/支")
    unit_price = Column(DECIMAL(10, 2), nullable=False, comment="单价（元）")
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="是否启用。停用后医生不可再选，但历史处方仍正常显示（软删除）"
    )
