import asyncio
from types import SimpleNamespace

import pytest

from app.exceptions.http_exceptions import LLMServiceError
from app.schedule.jobs import report_interpret


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _DatabaseSession:
    def __init__(self, report):
        self.report = report
        self.commit_count = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def execute(self, _statement):
        return _ScalarResult(self.report)

    async def commit(self):
        self.commit_count += 1


class _SessionFactory:
    def __init__(self, db):
        self.db = db

    def __call__(self):
        return self.db


def _pending_report():
    return SimpleNamespace(
        type="血常规",
        content={"白细胞": "6.2"},
        interpretation_status="pending",
        ai_interpretation=None,
        interpretation_at=None,
        referenced_chunks=None,
    )


def _install_generation_stubs(monkeypatch, *, content="指标处于参考范围内"):
    async def search(*_args, **_kwargs):
        return [SimpleNamespace(id=11, content="白细胞参考范围资料")]

    async def call(*_args, **_kwargs):
        return SimpleNamespace(content=content)

    monkeypatch.setattr(report_interpret.rag_service, "search", search)
    monkeypatch.setattr(report_interpret.llm_service, "call", call)
    monkeypatch.setattr(report_interpret, "load_prompt", lambda *_args, **_kwargs: "prompt")


def test_completed_report_is_skipped_without_calling_rag(monkeypatch):
    report = _pending_report()
    report.interpretation_status = "completed"
    db = _DatabaseSession(report)

    async def unexpected_search(*_args, **_kwargs):
        pytest.fail("completed report must not call RAG")

    monkeypatch.setattr(report_interpret.rag_service, "search", unexpected_search)

    result = asyncio.run(report_interpret._interpret(_SessionFactory(db), report_id=101))

    assert result == "already_completed"
    assert db.commit_count == 0


def test_successful_interpretation_saves_content_references_and_completion_time(monkeypatch):
    report = _pending_report()
    db = _DatabaseSession(report)
    _install_generation_stubs(monkeypatch)
    monkeypatch.setattr(report_interpret, "review_content", lambda _content: (True, ""))

    result = asyncio.run(report_interpret._interpret(_SessionFactory(db), report_id=101))

    assert result == "completed"
    assert report.interpretation_status == "completed"
    assert report.ai_interpretation == "指标处于参考范围内"
    assert report.referenced_chunks == [11]
    assert report.interpretation_at is not None
    assert report.interpretation_at.tzinfo is not None
    assert db.commit_count == 1


def test_llm_failure_marks_report_failed(monkeypatch):
    report = _pending_report()
    db = _DatabaseSession(report)

    async def search(*_args, **_kwargs):
        return []

    async def fail_call(*_args, **_kwargs):
        raise LLMServiceError(message="model unavailable")

    monkeypatch.setattr(report_interpret.rag_service, "search", search)
    monkeypatch.setattr(report_interpret.llm_service, "call", fail_call)
    monkeypatch.setattr(report_interpret, "load_prompt", lambda *_args, **_kwargs: "prompt")

    result = asyncio.run(report_interpret._interpret(_SessionFactory(db), report_id=101))

    assert result == "failed"
    assert report.interpretation_status == "failed"
    assert report.ai_interpretation is None
    assert db.commit_count == 1


def test_content_review_failure_marks_report_failed(monkeypatch):
    report = _pending_report()
    db = _DatabaseSession(report)
    _install_generation_stubs(monkeypatch, content="未通过审核的内容")
    monkeypatch.setattr(
        report_interpret,
        "review_content",
        lambda _content: (False, "unsafe content"),
    )

    result = asyncio.run(report_interpret._interpret(_SessionFactory(db), report_id=101))

    assert result == "failed"
    assert report.interpretation_status == "failed"
    assert report.ai_interpretation is None
    assert db.commit_count == 1


def test_rag_failure_marks_report_failed_instead_of_leaving_it_pending(monkeypatch):
    report = _pending_report()
    db = _DatabaseSession(report)

    async def fail_search(*_args, **_kwargs):
        raise RuntimeError("embedding service unavailable")

    monkeypatch.setattr(report_interpret.rag_service, "search", fail_search)

    result = asyncio.run(report_interpret._interpret(_SessionFactory(db), report_id=101))

    assert result == "failed"
    assert report.interpretation_status == "failed"
    assert db.commit_count == 1
