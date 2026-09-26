"""Run one end-to-end synthetic report interpretation through the real stack.

Creates a synthetic user/report, publishes the real task through Redis, and
waits for the running Celery worker to perform DashScope retrieval, DeepSeek
generation, content review, and PostgreSQL persistence. The synthetic report
and user are deleted afterward. Aggregate LLM/RAG telemetry is retained.
This invokes paid external APIs and must only run in the isolated dev stack.
"""

import asyncio
import json
import sys
import uuid
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.db.base import SQLALCHEMY_DATABASE_URL
from app.models.report import Report
from app.models.user import User
from app.services.common.content_review import has_disclaimer
from app.schedule.jobs.report_interpret import execute


async def create_fixture(session_factory):
    marker = uuid.uuid4().hex
    async with session_factory() as db:
        user = User(email=f"report-e2e-{marker}@example.invalid", is_active=True)
        db.add(user)
        await db.flush()
        report = Report(
            patient_id=user.id,
            type="合成报告测试",
            content={
                "test_marker": marker,
                "notice": "纯软件集成测试，无真实患者或医学检测数据。",
            },
            interpretation_status="pending",
        )
        db.add(report)
        await db.commit()
        return user.id, report.id


async def read_result(session_factory, report_id: int):
    async with session_factory() as db:
        report = (await db.execute(select(Report).where(Report.id == report_id))).scalar_one()
        content = report.ai_interpretation or ""
        return {
            "report_status": report.interpretation_status,
            "has_interpretation": bool(content.strip()),
            "has_disclaimer": has_disclaimer(content),
            "referenced_chunk_count": len(report.referenced_chunks or []),
        }


async def cleanup_fixture(session_factory, user_id: int, report_id: int) -> None:
    async with session_factory() as db:
        await db.execute(delete(Report).where(Report.id == report_id))
        await db.execute(delete(User).where(User.id == user_id))
        await db.commit()


async def main() -> None:
    placeholders = {"", "dummy-api-key", "your_dashscope_api_key", "your_deepseek_api_key"}
    if settings.DASHSCOPE_API_KEY in placeholders or settings.DEEPSEEK_API_KEY in placeholders:
        raise RuntimeError("DashScope or DeepSeek API key is not configured")

    engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=False, hide_parameters=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    user_id = report_id = None
    async_result = None
    outcome = None
    error_type = None
    cleanup_ok = False
    try:
        user_id, report_id = await create_fixture(session_factory)
        async_result = execute.apply_async(args=[report_id], queue="celery")
        task_result = async_result.get(timeout=180, propagate=True)
        report_result = await read_result(session_factory, report_id)
        outcome = {
            "broker_delivery": True,
            "worker_status": task_result.get("status"),
            **report_result,
        }
    except Exception as error:  # Provider/worker errors may contain sensitive details; expose only the class.
        error_type = type(error).__name__
    finally:
        if async_result is not None and not async_result.ready():
            async_result.revoke(terminate=False)
        if user_id is not None and report_id is not None:
            try:
                await cleanup_fixture(session_factory, user_id, report_id)
                cleanup_ok = True
            except Exception as cleanup_error:
                error_type = error_type or type(cleanup_error).__name__
        await engine.dispose()

    passed = bool(
        outcome
        and outcome.get("worker_status") == "completed"
        and outcome.get("report_status") == "completed"
        and outcome.get("has_interpretation")
        and outcome.get("has_disclaimer")
        and cleanup_ok
    )
    print(json.dumps({
        "ok": passed,
        "result": outcome,
        "synthetic_user_and_report_cleaned": cleanup_ok,
        "telemetry_retained": True,
        "error_type": error_type,
    }, ensure_ascii=False))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
