"""完整数据库初始基线。

Revision ID: 7d2a61f4c9be
Revises:
Create Date: 2026-09-02

项目正式交付前将开发阶段的历史迁移合并为该基线。revision ID 沿用原迁移
链的 head，使已经迁移到 7d2a61f4c9be 的开发数据库无需重复执行建表；全新
数据库执行 ``alembic upgrade head`` 时会一次创建当前版本的完整结构。

该文件是发布基线，不应随模型变化而修改。发布后的结构变化必须新增迁移。
"""

from typing import Optional, Sequence, Union

from alembic import op


revision: str = "7d2a61f4c9be"
down_revision: Optional[str] = None
branch_labels: Optional[Union[str, Sequence[str]]] = None
depends_on: Optional[Union[str, Sequence[str]]] = None

BASELINE_TABLES = {
    "admins",
    "admin_tokens",
    "appointments",
    "bills",
    "bill_items",
    "departments",
    "dispense_records",
    "doctors",
    "drugs",
    "knowledge_chunks",
    "llm_call_logs",
    "medical_records",
    "payment_orders",
    "prescriptions",
    "prescription_items",
    "rag_query_logs",
    "reports",
    "tokens",
    "users",
}


def _baseline_metadata_tables():
    from app.db.models import Base
    import app.models  # noqa: F401 - 将全部业务模型注册到 Base.metadata

    metadata_tables = {table.name for table in Base.metadata.sorted_tables}
    if metadata_tables != BASELINE_TABLES:
        missing = sorted(BASELINE_TABLES - metadata_tables)
        unexpected = sorted(metadata_tables - BASELINE_TABLES)
        raise RuntimeError(
            "Initial migration metadata does not match its frozen table list: "
            f"missing={missing}, unexpected={unexpected}. "
            "Create a new Alembic revision instead of editing this baseline."
        )
    return Base.metadata.sorted_tables


def upgrade() -> None:
    """启用 pgvector，并创建当前版本的全部业务表和索引。"""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    bind = op.get_bind()
    for table in _baseline_metadata_tables():
        table.create(bind=bind, checkfirst=False)


def downgrade() -> None:
    """按外键依赖的逆序删除全部业务表。"""
    bind = op.get_bind()
    for table in reversed(_baseline_metadata_tables()):
        table.drop(bind=bind, checkfirst=False)
