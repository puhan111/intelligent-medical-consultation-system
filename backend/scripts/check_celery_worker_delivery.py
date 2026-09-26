"""Verify Redis broker delivery to a running Celery worker without model calls.

Creates a synthetic report already marked completed, enqueues the real report
interpretation task, waits for the worker result, then removes the fixture.
The task exits before RAG/LLM because completed reports are idempotently skipped.
"""

import asyncio
import json
import sys
import uuid
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.base import SQLALCHEMY_DATABASE_URL
from app.models.report import Report
from app.models.user import User
from app.schedule.jobs.report_interpret import execute


async def create_fixture(session_factory):
    async with session_factory() as db:
        user = User(email=f"celery-delivery-{uuid.uuid4().hex}@example.invalid", is_active=True)
        db.add(user)
        await db.flush()
        report = Report(
            patient_id=user.id,
            type="Celery队列合成验证",
            content={"synthetic": True},
            interpretation_status="completed",
            ai_interpretation="合成任务投递验证；不构成医疗建议。",
        )
        db.add(report)
        await db.commit()
        return user.id, report.id


async def cleanup_fixture(session_factory, user_id: int, report_id: int) -> None:
    async with session_factory() as db:
        await db.execute(delete(Report).where(Report.id == report_id))
        await db.execute(delete(User).where(User.id == user_id))
        await db.commit()


async def verify_fixture(session_factory, report_id: int) -> bool:
    async with session_factory() as db:
        report = (await db.execute(select(Report).where(Report.id == report_id))).scalar_one_or_none()
        return report is not None and report.interpretation_status == "completed"


async def main() -> None:
    engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=False, hide_parameters=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    user_id = report_id = None
    async_result = None
    try:
        user_id, report_id = await create_fixture(session_factory)
        async_result = execute.apply_async(args=[report_id], queue="celery")
        result = async_result.get(timeout=60, propagate=True)
        fixture_preserved = await verify_fixture(session_factory, report_id)
        if result != {"status": "already_completed"} or not fixture_preserved:
            raise AssertionError("Worker result or report state did not match the expected idempotent skip")

        print(json.dumps({
            "broker_delivery": "passed",
            "worker_consumed_task": True,
            "task_status": result["status"],
            "fixture_preserved_until_cleanup": fixture_preserved,
            "rag_or_llm_called": False,
        }, ensure_ascii=False))
    finally:
        if async_result is not None and not async_result.ready():
            async_result.revoke(terminate=False)
        if user_id is not None and report_id is not None:
            await cleanup_fixture(session_factory, user_id, report_id)
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
