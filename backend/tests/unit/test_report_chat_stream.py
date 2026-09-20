import asyncio
import json
from types import SimpleNamespace

from app.api.client.v1 import report as report_api
from app.exceptions.http_exceptions import APIException
from app.schemas.client.report import ReportChatRequest
from app.services.client import report_chat


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _DatabaseSession:
    async def execute(self, _statement):
        report = SimpleNamespace(
            type="血常规",
            content={"白细胞": "6.2"},
            ai_interpretation="已有解读",
            interpretation_status="completed",
        )
        return _ScalarResult(report)


async def _collect_events(iterator):
    return [event async for event in iterator]


def _install_stream_stubs(monkeypatch, *, review_passed=True):
    saved_turns = []

    async def history(_session_id):
        return [
            {"role": "assistant", "content": "上一轮回答"},
            {"role": "user", "content": "上一轮问题"},
        ]

    async def search(*_args, **_kwargs):
        return [SimpleNamespace(content="医学参考片段")]

    async def stream(*_args, **_kwargs):
        yield "第一段"
        yield "第二段"

    async def save_turn(session_id, user_message, reply):
        saved_turns.append((session_id, user_message, reply))

    monkeypatch.setattr(report_chat, "get_conversation_history", history)
    monkeypatch.setattr(report_chat.rag_service, "search", search)
    monkeypatch.setattr(report_chat.llm_service, "stream", stream)
    monkeypatch.setattr(report_chat, "load_prompt", lambda *_args, **_kwargs: "prompt")
    monkeypatch.setattr(
        report_chat,
        "review_content",
        lambda _content: (review_passed, "unsafe" if not review_passed else ""),
    )
    monkeypatch.setattr(report_chat, "save_turn", save_turn)
    return saved_turns


def test_report_chat_stream_emits_start_deltas_and_done(monkeypatch):
    saved_turns = _install_stream_stubs(monkeypatch)

    events = asyncio.run(
        _collect_events(
            report_chat.chat_stream(
                db=_DatabaseSession(),
                patient_id=17,
                report_id=101,
                user_message="请解释白细胞指标",
                session_id="17:101:abcdef12",
            )
        )
    )

    assert [event["type"] for event in events] == ["start", "delta", "delta", "done"]
    assert events[0] == {
        "type": "start",
        "session_id": "17:101:abcdef12",
        "turn_count": 2,
    }
    assert "".join(event["content"] for event in events if event["type"] == "delta") == "第一段第二段"
    assert events[-1] == {
        "type": "done",
        "session_id": "17:101:abcdef12",
        "turn_count": 2,
    }
    assert saved_turns == [("17:101:abcdef12", "请解释白细胞指标", "第一段第二段")]


def test_failed_content_review_emits_replace_and_saves_safe_text(monkeypatch):
    saved_turns = _install_stream_stubs(monkeypatch, review_passed=False)

    events = asyncio.run(
        _collect_events(
            report_chat.chat_stream(
                db=_DatabaseSession(),
                patient_id=17,
                report_id=101,
                user_message="请给我下诊断",
                session_id="17:101:abcdef12",
            )
        )
    )

    assert [event["type"] for event in events] == [
        "start",
        "delta",
        "delta",
        "replace",
        "done",
    ]
    safe_text = events[-2]["content"]
    assert "咨询医生" in safe_text
    assert saved_turns == [("17:101:abcdef12", "请给我下诊断", safe_text)]


async def _collect_ndjson(response):
    chunks = []
    async for chunk in response.body_iterator:
        chunks.append(chunk.decode() if isinstance(chunk, bytes) else chunk)
    return "".join(chunks)


def test_stream_endpoint_encodes_events_as_ndjson(monkeypatch):
    async def fake_stream(**_kwargs):
        yield {"type": "start", "session_id": "17:101:abcdef12", "turn_count": 1}
        yield {"type": "delta", "content": "你好"}
        yield {"type": "done", "session_id": "17:101:abcdef12", "turn_count": 1}

    monkeypatch.setattr(report_api.report_chat, "chat_stream", fake_stream)
    response = asyncio.run(
        report_api.chat_about_report_stream(
            report_id=101,
            request=ReportChatRequest(message="解释报告"),
            db=object(),
            current_user=SimpleNamespace(id=17),
        )
    )
    body = asyncio.run(_collect_ndjson(response))
    lines = [json.loads(line) for line in body.splitlines()]

    assert response.media_type == "application/x-ndjson"
    assert response.headers["cache-control"] == "no-cache"
    assert response.headers["x-accel-buffering"] == "no"
    assert [line["type"] for line in lines] == ["start", "delta", "done"]
    assert lines[1]["content"] == "你好"


def test_stream_endpoint_turns_api_exception_into_error_event(monkeypatch):
    async def fail_stream(**_kwargs):
        raise APIException(status_code=404, message="Report not found or access denied")
        yield

    monkeypatch.setattr(report_api.report_chat, "chat_stream", fail_stream)
    response = asyncio.run(
        report_api.chat_about_report_stream(
            report_id=999,
            request=ReportChatRequest(message="解释报告"),
            db=object(),
            current_user=SimpleNamespace(id=17),
        )
    )
    body = asyncio.run(_collect_ndjson(response))
    event = json.loads(body)

    assert event == {
        "type": "error",
        "message": "Report not found or access denied",
    }
