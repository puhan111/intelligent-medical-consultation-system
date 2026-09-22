import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from openai import APIConnectionError, APITimeoutError, RateLimitError
from tenacity import wait_none

from app.exceptions.http_exceptions import InputTooLongError, LLMServiceError
from app.services.common import llm_service


class RecordingDatabase:
    def __init__(self):
        self.added = []

    def add(self, value):
        self.added.append(value)


def timeout_error(secret="private-prompt-or-key"):
    error = APITimeoutError(request=httpx.Request("POST", "https://model.invalid"))
    error.args = (secret,)
    return error


def connection_error(secret="private-connection-detail"):
    return APIConnectionError(
        message=secret,
        request=httpx.Request("POST", "https://model.invalid"),
    )


def rate_limit_error(secret="private-rate-limit-detail"):
    response = httpx.Response(
        429,
        request=httpx.Request("POST", "https://model.invalid"),
    )
    return RateLimitError(secret, response=response, body=None)


@pytest.mark.asyncio
async def test_non_streaming_call_runs_blocking_sdk_in_thread(monkeypatch):
    db = RecordingDatabase()
    monkeypatch.setattr(llm_service, "_check_budget", AsyncMock())
    monkeypatch.setattr(llm_service, "_record_budget_usage", AsyncMock())
    blocking_call = lambda *_args: ("ok", 11, 7)
    monkeypatch.setattr(llm_service, "_call_deepseek_sync", blocking_call)
    to_thread = AsyncMock(side_effect=lambda func, *args: func(*args))
    monkeypatch.setattr(asyncio, "to_thread", to_thread)

    result = await llm_service.call(db, "hello", "triage")

    to_thread.assert_awaited_once_with(blocking_call, "hello", None, 30)
    assert result.content == "ok"
    assert db.added[0].status == "success"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error,expected_status",
    [
        (timeout_error(), "timeout"),
        (connection_error(), "connection_error"),
        (rate_limit_error(), "rate_limited"),
    ],
)
async def test_model_failures_are_classified_and_redacted(
    monkeypatch, caplog, error, expected_status
):
    db = RecordingDatabase()
    monkeypatch.setattr(llm_service, "_check_budget", AsyncMock())

    def fail(*_args):
        raise error

    monkeypatch.setattr(llm_service, "_call_deepseek_sync", fail)

    with pytest.raises(LLMServiceError):
        await llm_service.call(db, "private-patient-prompt", "triage")

    assert db.added[0].status == expected_status
    assert db.added[0].error_message == type(error).__name__
    combined = caplog.text + str(db.added[0].error_message)
    assert "private-patient-prompt" not in combined
    assert "private-" not in combined


@pytest.mark.asyncio
async def test_input_length_is_rejected_before_budget_or_model_call(monkeypatch):
    budget = AsyncMock()
    model_call = AsyncMock()
    monkeypatch.setattr(llm_service, "_check_budget", budget)
    monkeypatch.setattr(asyncio, "to_thread", model_call)

    with pytest.raises(InputTooLongError):
        await llm_service.call(RecordingDatabase(), "x" * 3001, "triage")

    budget.assert_not_awaited()
    model_call.assert_not_awaited()


@pytest.mark.parametrize("error_factory", [timeout_error, connection_error, rate_limit_error])
def test_transient_provider_errors_are_retried_three_times_without_waiting(
    monkeypatch, error_factory
):
    attempts = 0

    def fail(**_kwargs):
        nonlocal attempts
        attempts += 1
        raise error_factory()

    monkeypatch.setattr(llm_service._client.chat.completions, "create", fail)
    call_without_wait = llm_service._call_deepseek_sync.retry_with(wait=wait_none())

    with pytest.raises((APITimeoutError, APIConnectionError, RateLimitError)):
        call_without_wait("hello", None, 30)

    assert attempts == 3


@pytest.mark.asyncio
async def test_invalid_provider_response_has_stable_redacted_failure(monkeypatch):
    db = RecordingDatabase()
    monkeypatch.setattr(llm_service, "_check_budget", AsyncMock())
    monkeypatch.setattr(
        llm_service._client.chat.completions,
        "create",
        lambda **_kwargs: SimpleNamespace(choices=[], usage=None),
    )

    with pytest.raises(LLMServiceError):
        await llm_service.call(db, "private-patient-prompt", "triage")

    assert db.added[0].status == "invalid_response"
    assert db.added[0].error_message == "LLMResponseError"
