"""Probe the authenticated report follow-up NDJSON stream with synthetic data.

Creates a completed synthetic report, calls the running API over the Compose
network, and verifies streamed events plus Redis conversation persistence.
The probe calls DashScope and DeepSeek and should only run in the isolated dev
stack. It deletes its synthetic user, report, conversation, and rate-limit key;
LLM/RAG telemetry is retained.
"""

import asyncio
import json
import sys
import uuid
from pathlib import Path

import httpx
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.core.security import AuthBase
from app.db.base import SQLALCHEMY_DATABASE_URL
from app.models.report import Report
from app.models.user import User
from app.services.common.redis import redis_client
from app.services.client.report_chat import CONV_KEY_PREFIX


async def create_fixture(session_factory):
    marker = uuid.uuid4().hex
    async with session_factory() as db:
        user = User(email=f"report-chat-e2e-{marker}@example.invalid", is_active=True)
        db.add(user)
        await db.flush()
        report = Report(
            patient_id=user.id,
            type="合成检验报告",
            content={
                "test_marker": marker,
                "notice": "纯软件集成测试，无真实患者或医学检测数据。",
            },
            ai_interpretation="这是合成软件测试报告，不构成医疗诊断。",
            interpretation_status="completed",
        )
        db.add(report)
        await db.commit()
        return user.id, report.id


async def delete_fixture(session_factory, user_id: int, report_id: int) -> None:
    async with session_factory() as db:
        await db.execute(delete(Report).where(Report.id == report_id))
        await db.execute(delete(User).where(User.id == user_id))
        await db.commit()


async def run_stream(user_id: int, report_id: int):
    token = AuthBase.create_access_token(str(user_id), scope="client")
    url = (
        f"http://app:{settings.API_PORT}{settings.API_V1_STR}"
        f"/reports/{report_id}/chat/stream"
    )
    request_message = "请解释这份合成测试报告的用途，并说明不能据此做什么决定。"
    events = []
    http_status = None
    media_type_ok = False

    timeout = httpx.Timeout(180.0, connect=5.0)
    async with httpx.AsyncClient(timeout=timeout, trust_env=False) as client:
        async with client.stream(
            "POST",
            url,
            headers={"Authorization": f"Bearer {token}"},
            json={"message": request_message},
        ) as response:
            http_status = response.status_code
            media_type_ok = response.headers.get("content-type", "").startswith(
                "application/x-ndjson"
            )
            if http_status != 200 or not media_type_ok:
                return {
                    "http_status": http_status,
                    "media_type_ok": media_type_ok,
                    "events": events,
                    "request_message": request_message,
                    "session_id": None,
                }

            async for line in response.aiter_lines():
                if line.strip():
                    events.append(json.loads(line))

    start_events = [event for event in events if event.get("type") == "start"]
    session_id = start_events[0].get("session_id") if len(start_events) == 1 else None
    return {
        "http_status": http_status,
        "media_type_ok": media_type_ok,
        "events": events,
        "request_message": request_message,
        "session_id": session_id,
    }


async def main() -> None:
    placeholders = {"", "dummy-api-key", "your_dashscope_api_key", "your_deepseek_api_key"}
    if settings.DASHSCOPE_API_KEY in placeholders or settings.DEEPSEEK_API_KEY in placeholders:
        raise RuntimeError("DashScope or DeepSeek API key is not configured")

    engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=False, hide_parameters=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    user_id = report_id = None
    session_id = None
    cleanup_ok = False
    outcome = None
    error_type = None
    try:
        user_id, report_id = await create_fixture(session_factory)
        outcome = await run_stream(user_id, report_id)
        session_id = outcome.pop("session_id")
        history = []
        if session_id:
            key = f"{CONV_KEY_PREFIX}:{session_id}"
            history = await redis_client.redis.lrange(key, 0, 15)
        parsed_history = [json.loads(item) for item in history]
        outcome["conversation_saved"] = bool(
            len(parsed_history) >= 2
            and parsed_history[0].get("role") == "user"
            and parsed_history[0].get("content") == outcome["request_message"]
            and parsed_history[1].get("role") == "assistant"
            and bool(parsed_history[1].get("content", "").strip())
        )
    except Exception as error:  # Do not print prompts, generated text, or provider details.
        error_type = type(error).__name__
    finally:
        cleanup_errors = []
        if session_id:
            try:
                await redis_client.redis.delete(f"{CONV_KEY_PREFIX}:{session_id}")
            except Exception as error:
                cleanup_errors.append(type(error).__name__)
        if user_id is not None:
            try:
                await redis_client.redis.delete(f"rate_limit:report_chat:{user_id}")
            except Exception as error:
                cleanup_errors.append(type(error).__name__)
        if user_id is not None and report_id is not None:
            try:
                await delete_fixture(session_factory, user_id, report_id)
            except Exception as error:
                cleanup_errors.append(type(error).__name__)
        cleanup_ok = not cleanup_errors and user_id is not None and report_id is not None
        if cleanup_errors and error_type is None:
            error_type = cleanup_errors[0]
        await redis_client.close()
        await engine.dispose()

    events = outcome.get("events", []) if outcome else []
    event_types = [event.get("type") for event in events]
    delta_char_count = sum(
        len(event.get("content", ""))
        for event in events
        if event.get("type") == "delta"
    )
    session_id = outcome.get("session_id") if outcome else session_id
    passed = bool(
        outcome
        and outcome.get("http_status") == 200
        and outcome.get("media_type_ok")
        and event_types[:1] == ["start"]
        and event_types[-1:] == ["done"]
        and "error" not in event_types
        and delta_char_count > 0
        and outcome.get("conversation_saved")
        and cleanup_ok
    )
    print(json.dumps({
        "ok": passed,
        "http_status": outcome.get("http_status") if outcome else None,
        "ndjson_content_type": outcome.get("media_type_ok") if outcome else False,
        "event_types": event_types,
        "delta_char_count": delta_char_count,
        "conversation_saved": outcome.get("conversation_saved", False) if outcome else False,
        "synthetic_user_report_and_redis_state_cleaned": cleanup_ok,
        "telemetry_retained": True,
        "error_type": error_type,
    }, ensure_ascii=False))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
