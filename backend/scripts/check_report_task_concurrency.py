"""Manually verify PostgreSQL advisory locking with concurrent task processes.

Creates one synthetic user/report in the isolated database, invokes the real
Celery task entry point concurrently in two spawned processes, and deletes the
fixture in a finally block. RAG and LLM calls are stubbed to avoid external
model requests. This verifies task-process concurrency and the real database
lock, but does not exercise delivery through a running Redis broker/worker.
"""

import asyncio
import json
import multiprocessing
import queue
import sys
import time
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.base import SQLALCHEMY_DATABASE_URL
from app.models.report import Report
from app.models.user import User


def run_task(report_id: int, rag_started, results) -> None:
    """Child process: use actual task/SQL lock, with external AI calls stubbed."""
    from app.schedule.jobs import report_interpret as task_module

    async def fake_search(*_args, **_kwargs):
        rag_started.set()
        await asyncio.sleep(3)
        return []

    async def fake_llm_call(*_args, **_kwargs):
        return SimpleNamespace(content="合成并发验证结果，不构成医疗建议。")

    async def no_redis_close():
        return None

    task_module.rag_service.search = fake_search
    task_module.llm_service.call = fake_llm_call
    task_module.load_prompt = lambda *_args, **_kwargs: "synthetic concurrency check"
    task_module.review_content = lambda _content: (True, "")
    task_module._close_redis = no_redis_close

    results.put(task_module.execute(report_id))


async def create_fixture(session_factory):
    async with session_factory() as db:
        marker = f"{time.time_ns()}"
        user = User(email=f"task-lock-{marker}@example.invalid", is_active=True)
        db.add(user)
        await db.flush()
        report = Report(
            patient_id=user.id,
            type="并发锁合成验证",
            content={"synthetic": True},
            interpretation_status="pending",
        )
        db.add(report)
        await db.commit()
        return user.id, report.id


async def verify_completed(session_factory, report_id: int) -> bool:
    async with session_factory() as db:
        report = (await db.execute(select(Report).where(Report.id == report_id))).scalar_one()
        return report.interpretation_status == "completed"


async def cleanup_fixture(session_factory, user_id: int, report_id: int) -> None:
    async with session_factory() as db:
        await db.execute(delete(Report).where(Report.id == report_id))
        await db.execute(delete(User).where(User.id == user_id))
        await db.commit()


async def main() -> None:
    engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=False, hide_parameters=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    user_id = report_id = None
    processes = []
    try:
        user_id, report_id = await create_fixture(session_factory)
        context = multiprocessing.get_context("spawn")
        rag_started = context.Event()
        results = context.Queue()

        first = context.Process(target=run_task, args=(report_id, rag_started, results))
        first.start()
        processes.append(first)
        if not rag_started.wait(20):
            raise RuntimeError("First task did not reach RAG; lock test setup failed")

        second = context.Process(target=run_task, args=(report_id, rag_started, results))
        second.start()
        processes.append(second)
        for process in processes:
            process.join(45)
            if process.is_alive():
                process.terminate()
                process.join(5)
                raise RuntimeError("Concurrent task process timed out")
            if process.exitcode != 0:
                raise RuntimeError(f"Concurrent task process failed with exit code {process.exitcode}")

        outcomes = [results.get(timeout=5), results.get(timeout=5)]
        completed_once = sum(result.get("status") == "completed" for result in outcomes) == 1
        duplicate_skipped = sum(result.get("status") == "already_processing" for result in outcomes) == 1
        report_completed = await verify_completed(session_factory, report_id)
        if not (completed_once and duplicate_skipped and report_completed):
            raise AssertionError("Concurrent task outcomes did not satisfy advisory-lock expectations")

        print(json.dumps({
            "one_task_completed": completed_once,
            "duplicate_skipped": duplicate_skipped,
            "report_completed": report_completed,
            "external_llm_called": False,
            "delivery_via_redis_worker_tested": False,
        }))
    finally:
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join(5)
        if user_id is not None and report_id is not None:
            await cleanup_fixture(session_factory, user_id, report_id)
        await engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except queue.Empty as error:
        raise SystemExit("Concurrent task did not return both outcomes") from error
