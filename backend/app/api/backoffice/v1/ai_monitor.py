from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.backoffice.deps import get_current_superadmin
from app.db.session import get_db
from app.exceptions.http_exceptions import ValidationError
from app.models.admin import Admin
from app.schemas.response import ApiResponse
from app.services.backoffice.ai_monitor import get_overview
from app.services.backoffice.rag_evaluation import run_evaluation
from app.services.common.rate_limit import enforce_rate_limit

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


@router.post("/rag-evaluation")
async def rag_evaluation(
    top_k: int = Query(default=3, ge=1, le=5),
    rerank: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_superadmin),
):
    """运行固定合成数据集，不写入线上RAG查询日志。"""
    await enforce_rate_limit(
        f"rag_evaluation:{current_admin.id}", limit=5, window_seconds=3600
    )
    return ApiResponse.success(
        data=await run_evaluation(db, top_k=top_k, rerank=rerank)
    )
