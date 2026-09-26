"""Smoke-test the configured DeepSeek path with a tiny synthetic prompt.

The normal LLM service is exercised, including Redis budget checks and database
logging. The uniquely tagged call-log row is deleted afterward. No patient data
or credentials are printed; the request may incur a small provider charge.
"""

import asyncio
import json
import sys
import uuid
from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.db.base import SQLALCHEMY_DATABASE_URL
from app.models.llm_call_log import LLMCallLog
from app.services.common import llm_service


async def main() -> None:
    if settings.DEEPSEEK_API_KEY in {"", "dummy-api-key", "your_deepseek_api_key"}:
        raise RuntimeError("DeepSeek API key is not configured")

    nonce = uuid.uuid4().hex
    prompt = f"Connectivity check only. Reply exactly: LLM_SMOKE_OK_{nonce}"
    prompt_hash = llm_service._prompt_hash(prompt)
    engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=False, hide_parameters=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    result = None
    failure_type = None
    try:
        async with session_factory() as db:
            result = await llm_service.call(
                db,
                prompt,
                agent_type="report_interpret",
                system_prompt="You are running a synthetic software connectivity check. Do not provide medical advice.",
            )
    except Exception as error:  # Print the class only; provider messages may contain sensitive details.
        failure_type = type(error).__name__
    finally:
        try:
            async with session_factory() as db:
                await db.execute(delete(LLMCallLog).where(LLMCallLog.prompt_hash == prompt_hash))
                await db.commit()
        finally:
            await engine.dispose()

    if result is None:
        print(json.dumps({"ok": False, "error_type": failure_type}, ensure_ascii=False))
        raise SystemExit(1)

    print(json.dumps({
        "ok": True,
        "model": settings.DEEPSEEK_MODEL,
        "latency_ms": result.latency_ms,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "synthetic_prompt_log_cleaned": True,
    }, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
