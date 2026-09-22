from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from kombu.exceptions import OperationalError

from app.api.backoffice.v1 import report as report_api
from app.exceptions.http_exceptions import APIException
from app.services.backoffice.report import ReportService


class Database:
    def __init__(self, report=None):
        self.report = report
        self.commit_count = 0
        self.rollback_count = 0
        self.flush_count = 0

    async def execute(self, _statement):
        return SimpleNamespace(scalar_one_or_none=lambda: self.report)

    async def flush(self):
        self.flush_count += 1

    async def commit(self):
        self.commit_count += 1

    async def rollback(self):
        self.rollback_count += 1


@pytest.mark.asyncio
async def test_publish_failure_marks_pending_report_failed_for_retry(monkeypatch):
    report = SimpleNamespace(id=101, interpretation_status="pending")
    db = Database(report)

    def fail_publish(_report_id):
        raise OperationalError("broker unavailable")

    monkeypatch.setattr(report_api, "_enqueue_report_interpretation", fail_publish)

    with pytest.raises(APIException) as exc_info:
        await report_api._enqueue_or_mark_failed(db, report.id)

    assert exc_info.value.status_code == 503
    assert report.interpretation_status == "failed"
    assert db.flush_count == 1
    assert db.commit_count == 1
    assert db.rollback_count == 0


@pytest.mark.asyncio
async def test_successful_publish_does_not_change_report_state(monkeypatch):
    report = SimpleNamespace(id=101, interpretation_status="pending")
    db = Database(report)
    publish = Mock()
    monkeypatch.setattr(report_api, "_enqueue_report_interpretation", publish)

    await report_api._enqueue_or_mark_failed(db, report.id)

    publish.assert_called_once_with(101)
    assert report.interpretation_status == "pending"
    assert db.commit_count == 0


@pytest.mark.asyncio
async def test_failure_marker_does_not_overwrite_terminal_state():
    for status in ("completed", "failed"):
        report = SimpleNamespace(id=101, interpretation_status=status)
        db = Database(report)

        await ReportService.mark_enqueue_failed(db, report.id)

        assert report.interpretation_status == status
        assert db.flush_count == 0
