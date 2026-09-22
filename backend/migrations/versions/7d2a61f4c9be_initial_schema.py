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

# 冻结发布基线的列名。模型增加或删除列时必须新增revision，不能让初始迁移
# 静默读取新metadata并使旧库缺列。
BASELINE_COLUMNS = {
    "admins": ("id", "role", "email", "first_name", "last_name", "password", "is_active", "created_at", "updated_at"),
    "departments": ("id", "name", "description", "created_at", "updated_at"),
    "drugs": ("id", "name", "spec", "unit", "unit_price", "is_active", "created_at", "updated_at"),
    "knowledge_chunks": ("id", "source", "content", "embedding", "metadata", "content_tsv", "created_at", "updated_at"),
    "llm_call_logs": ("id", "agent_type", "prompt_hash", "input_tokens", "output_tokens", "latency_ms", "status", "error_message", "created_at", "updated_at"),
    "rag_query_logs": ("id", "agent_type", "query", "top_k", "result_ids", "latency_ms", "created_at", "updated_at"),
    "users": ("id", "email", "hashed_password", "first_name", "last_name", "avatar", "gender", "is_active", "is_verified", "last_active_at", "created_at", "updated_at"),
    "admin_tokens": ("id", "admin_id", "token", "expires_at", "last_used_at", "is_active", "created_at", "updated_at"),
    "doctors": ("id", "admin_id", "department_id", "title", "introduction", "created_at", "updated_at"),
    "tokens": ("id", "user_id", "token", "expires_at", "last_used_at", "is_active", "created_at", "updated_at"),
    "appointments": ("id", "patient_id", "doctor_id", "department_id", "appointment_time", "status", "created_at", "updated_at"),
    "medical_records": ("id", "appointment_id", "patient_id", "doctor_id", "diagnosis", "content", "created_at", "updated_at"),
    "prescriptions": ("id", "appointment_id", "doctor_id", "status", "created_at", "updated_at"),
    "reports": ("id", "patient_id", "appointment_id", "type", "content", "ai_interpretation", "interpretation_status", "interpretation_at", "referenced_chunks", "created_at", "updated_at"),
    "bills": ("id", "patient_id", "appointment_id", "amount", "bill_type", "prescription_id", "status", "paid_at", "payment_method", "paid_by_type", "cashier_id", "created_at", "updated_at"),
    "dispense_records": ("id", "prescription_id", "pharmacist_id", "dispensed_at", "status", "created_at", "updated_at"),
    "prescription_items": ("id", "prescription_id", "drug_name", "dosage", "quantity", "drug_id", "unit_price", "is_selected", "created_at", "updated_at"),
    "bill_items": ("id", "bill_id", "item_type", "name", "unit_price", "quantity", "subtotal", "created_at", "updated_at"),
    "payment_orders": ("id", "bill_id", "order_no", "amount", "channel", "status", "operator_type", "operator_id", "fail_reason", "paid_at", "created_at", "updated_at"),
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
    metadata_columns = {
        table.name: tuple(column.name for column in table.columns)
        for table in Base.metadata.sorted_tables
    }
    if metadata_columns != BASELINE_COLUMNS:
        changed = sorted(
            table_name
            for table_name in BASELINE_TABLES
            if metadata_columns.get(table_name) != BASELINE_COLUMNS.get(table_name)
        )
        raise RuntimeError(
            "Initial migration metadata does not match its frozen column list: "
            f"changed_tables={changed}. Create a new Alembic revision instead of "
            "editing this baseline."
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
