import logging
from datetime import date, datetime, time, timedelta, timezone
from typing import Optional

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.llm_call_log import LLMCallLog
from app.models.rag_query_log import RAGQueryLog
from app.services.common.redis import redis_client

logger = logging.getLogger("ai_monitor")


def _as_int(value) -> int:
    return int(value or 0)


def _as_float(value) -> float:
    return round(float(value or 0), 1)


async def get_overview(
    db: AsyncSession,
    days: int,
    agent_type: Optional[str] = None,
) -> dict:
    today = datetime.now(timezone.utc).date()
    start_date = today - timedelta(days=days - 1)
    start_at = datetime.combine(start_date, time.min, tzinfo=timezone.utc)

    llm_filters = [LLMCallLog.created_at >= start_at]
    rag_filters = [RAGQueryLog.created_at >= start_at]
    if agent_type:
        llm_filters.append(LLMCallLog.agent_type == agent_type)
        rag_filters.append(RAGQueryLog.agent_type == agent_type)

    llm_row = (
        await db.execute(
            select(
                func.count(LLMCallLog.id),
                func.coalesce(
                    func.sum(LLMCallLog.input_tokens + LLMCallLog.output_tokens), 0
                ),
                func.coalesce(func.avg(LLMCallLog.latency_ms), 0),
                func.coalesce(
                    func.sum(case((LLMCallLog.status == "success", 1), else_=0)), 0
                ),
                func.coalesce(
                    func.sum(case((LLMCallLog.status == "error", 1), else_=0)), 0
                ),
                func.coalesce(
                    func.sum(case((LLMCallLog.status == "timeout", 1), else_=0)), 0
                ),
            ).where(*llm_filters)
        )
    ).one()

    call_count = _as_int(llm_row[0])
    success_count = _as_int(llm_row[3])

    rag_row = (
        await db.execute(
            select(
                func.count(RAGQueryLog.id),
                func.coalesce(func.avg(RAGQueryLog.latency_ms), 0),
            ).where(*rag_filters)
        )
    ).one()

    llm_day = func.date(LLMCallLog.created_at).label("day")
    llm_daily_rows = (
        await db.execute(
            select(
                llm_day,
                func.count(LLMCallLog.id),
                func.coalesce(
                    func.sum(LLMCallLog.input_tokens + LLMCallLog.output_tokens), 0
                ),
            )
            .where(*llm_filters)
            .group_by(llm_day)
            .order_by(llm_day)
        )
    ).all()

    rag_day = func.date(RAGQueryLog.created_at).label("day")
    rag_daily_rows = (
        await db.execute(
            select(rag_day, func.count(RAGQueryLog.id))
            .where(*rag_filters)
            .group_by(rag_day)
            .order_by(rag_day)
        )
    ).all()

    trend = {
        start_date + timedelta(days=offset): {
            "date": (start_date + timedelta(days=offset)).isoformat(),
            "calls": 0,
            "tokens": 0,
            "rag_queries": 0,
        }
        for offset in range(days)
    }
    for day_value, calls, tokens in llm_daily_rows:
        if day_value in trend:
            trend[day_value]["calls"] = _as_int(calls)
            trend[day_value]["tokens"] = _as_int(tokens)
    for day_value, rag_queries in rag_daily_rows:
        if day_value in trend:
            trend[day_value]["rag_queries"] = _as_int(rag_queries)

    breakdown_rows = (
        await db.execute(
            select(LLMCallLog.agent_type, func.count(LLMCallLog.id))
            .where(LLMCallLog.created_at >= start_at)
            .group_by(LLMCallLog.agent_type)
            .order_by(func.count(LLMCallLog.id).desc())
        )
    ).all()

    recent_llm = (
        await db.execute(
            select(LLMCallLog)
            .where(*llm_filters)
            .order_by(LLMCallLog.created_at.desc())
            .limit(10)
        )
    ).scalars().all()
    recent_rag = (
        await db.execute(
            select(RAGQueryLog)
            .where(*rag_filters)
            .order_by(RAGQueryLog.created_at.desc())
            .limit(10)
        )
    ).scalars().all()

    budget_limit = settings.LLM_DAILY_TOKEN_BUDGET
    budget_used = None
    try:
        budget_value = await redis_client.get(f"llm:token_budget:{date.today().isoformat()}")
        budget_used = _as_int(budget_value)
    except Exception as exc:
        logger.warning("Failed to read LLM budget from Redis: %s", exc)

    return {
        "period": {
            "days": days,
            "start_date": start_date.isoformat(),
            "end_date": today.isoformat(),
            "agent_type": agent_type,
        },
        "metrics": {
            "call_count": call_count,
            "token_count": _as_int(llm_row[1]),
            "average_latency_ms": _as_float(llm_row[2]),
            "success_count": success_count,
            "error_count": _as_int(llm_row[4]),
            "timeout_count": _as_int(llm_row[5]),
            "success_rate": round(success_count / call_count * 100, 1) if call_count else 0,
            "rag_query_count": _as_int(rag_row[0]),
            "rag_average_latency_ms": _as_float(rag_row[1]),
        },
        "budget": {
            "available": budget_used is not None,
            "used": budget_used,
            "limit": budget_limit,
            "usage_rate": (
                round(budget_used / budget_limit * 100, 1)
                if budget_used is not None and budget_limit
                else None
            ),
        },
        "trend": list(trend.values()),
        "agent_breakdown": [
            {"agent_type": row[0], "count": _as_int(row[1])}
            for row in breakdown_rows
        ],
        "recent_llm_calls": [
            {
                "id": item.id,
                "agent_type": item.agent_type,
                "input_tokens": item.input_tokens,
                "output_tokens": item.output_tokens,
                "latency_ms": item.latency_ms,
                "status": item.status,
                "error_message": item.error_message,
                "created_at": item.created_at,
            }
            for item in recent_llm
        ],
        "recent_rag_queries": [
            {
                "id": item.id,
                "agent_type": item.agent_type,
                "query": item.query,
                "top_k": item.top_k,
                "result_count": len(item.result_ids or []),
                "latency_ms": item.latency_ms,
                "created_at": item.created_at,
            }
            for item in recent_rag
        ],
    }
