import asyncio
import re

import pytest

from app.exceptions.http_exceptions import APIException
from app.services.client.report import ReportService
from app.services.client.report_chat import chat, resolve_session_id


class _EmptyScalarResult:
    def scalar_one_or_none(self):
        return None


class _CapturingDatabaseSession:
    def __init__(self):
        self.statement = None

    async def execute(self, statement):
        self.statement = statement
        return _EmptyScalarResult()


def _compiled_query(statement):
    compiled = statement.compile()
    return str(compiled), set(compiled.params.values())


def test_report_list_query_is_scoped_to_current_patient():
    statement = asyncio.run(ReportService.get_my_reports_query(None, patient_id=17))

    sql, parameter_values = _compiled_query(statement)

    assert "reports.patient_id" in sql
    assert 17 in parameter_values


def test_new_report_chat_session_is_namespaced_to_patient_and_report():
    session_id = resolve_session_id(patient_id=17, report_id=101, session_id=None)

    assert re.fullmatch(r"17:101:[0-9a-f]{8}", session_id)
    assert resolve_session_id(17, 101, session_id) == session_id


@pytest.mark.parametrize(
    "session_id",
    [
        "18:101:abcdef12",
        "17:102:abcdef12",
        "17:101:not-hex",
    ],
)
def test_foreign_or_invalid_report_chat_session_is_rejected(session_id):
    with pytest.raises(APIException) as exc_info:
        resolve_session_id(patient_id=17, report_id=101, session_id=session_id)

    assert exc_info.value.status_code == 400


def test_report_chat_lookup_filters_by_report_and_current_patient():
    db = _CapturingDatabaseSession()

    with pytest.raises(APIException) as exc_info:
        asyncio.run(
            chat(
                db=db,
                patient_id=17,
                report_id=101,
                user_message="请解释这个指标",
            )
        )

    sql, parameter_values = _compiled_query(db.statement)
    assert "reports.id" in sql
    assert "reports.patient_id" in sql
    assert {17, 101}.issubset(parameter_values)
    assert exc_info.value.status_code == 404
