from unittest.mock import AsyncMock

import pytest

from app.exceptions.http_exceptions import APIException
from app.services.common import rate_limit


@pytest.mark.asyncio
async def test_rate_limit_allows_requests_within_window(monkeypatch):
    eval_call = AsyncMock(return_value=[3, 42])
    monkeypatch.setattr(rate_limit.redis_client.redis, "eval", eval_call)
    await rate_limit.enforce_rate_limit("triage:17", limit=20, window_seconds=60)
    eval_call.assert_awaited_once()


@pytest.mark.asyncio
async def test_rate_limit_returns_retry_after_when_exceeded(monkeypatch):
    monkeypatch.setattr(
        rate_limit.redis_client.redis, "eval", AsyncMock(return_value=[21, 37])
    )
    with pytest.raises(APIException) as error:
        await rate_limit.enforce_rate_limit("triage:17", limit=20, window_seconds=60)
    assert error.value.status_code == 429
    assert error.value.data == {"retry_after_seconds": 37}


@pytest.mark.asyncio
async def test_rate_limit_fails_open_when_redis_is_unavailable(monkeypatch, caplog):
    monkeypatch.setattr(
        rate_limit.redis_client.redis,
        "eval",
        AsyncMock(side_effect=ConnectionError("private redis detail")),
    )
    await rate_limit.enforce_rate_limit("triage:17", limit=20, window_seconds=60)
    assert "ConnectionError" in caplog.text
    assert "private redis detail" not in caplog.text
