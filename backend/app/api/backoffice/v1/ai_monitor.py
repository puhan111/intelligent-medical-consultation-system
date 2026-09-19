from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.backoffice.deps import get_current_superadmin
from app.db.session import get_db
from app.exceptions.http_exceptions import ValidationError
from app.models.admin import Admin
from app.schemas.response import ApiResponse
from app.services.backoffice.ai_monitor import get_overview

router = APIRouter()

AgentType = Literal["triage", "report_interpret", "report_followup", "eval_judge"]


@router.get("/overview")
async def overview(
    days: int = Query(default=7),
    agent_type: Optional[AgentType] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: Admin = Depends(get_current_superadmin),
):
    """AI 调用、Token、延迟、成功率与 RAG 检索聚合监控。"""
    if days not in (7, 14, 30):
        raise ValidationError(message="Days must be one of 7, 14, or 30")
    data = await get_overview(db=db, days=days, agent_type=agent_type)
    return ApiResponse.success(data=data)
