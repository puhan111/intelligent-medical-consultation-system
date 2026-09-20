from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from jose import jwt
from pydantic import ValidationError

from app.core.config import settings
from app.core.security import AuthBase
from app.services.common import mcp_readonly as service


def token(subject="17", scope="client", **kwargs):
    return AuthBase.create_access_token(subject, scope, **kwargs)


def database(user=..., report=None):
    if user is ...:
        user = SimpleNamespace(id=17, is_active=True)
    result = SimpleNamespace(scalar_one_or_none=lambda: user, one_or_none=lambda: report)
    return SimpleNamespace(execute=AsyncMock(return_value=result))


@pytest.mark.asyncio
@pytest.mark.parametrize("credential", [
    None, "invalid", token(scope="backoffice"), token(scope="refresh"),
    token(expires_delta=timedelta(seconds=-1)), token(subject="abc"), token(subject="0"),
    token(subject="2147483648"),
    jwt.encode({"sub": "17", "scope": "client"}, settings.SECRET_KEY, algorithm=settings.ALGORITHM),
    jwt.encode({"sub": "17", "scope": "client", "exp": 9999999999}, "different-test-key", algorithm=settings.ALGORITHM),
], ids=["missing", "malformed", "backoffice", "refresh", "expired", "bad-subject", "zero-subject", "oversize-subject", "missing-expiry", "bad-signature"])
async def test_invalid_identity_rejected_before_database(credential):
    db = database()
    with pytest.raises(service.ReadOnlyError, match="AUTH_REQUIRED"):
        await service.get_my_report_status(db, credential, {"report_id": 101})
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("user", [None, SimpleNamespace(id=17, is_active=False)])
@pytest.mark.parametrize("operation,arguments", [
    (service.get_my_report_status, {"report_id": 101}),
    (service.search_medical_references, {"query": "参考资料"}),
])
async def test_missing_or_disabled_user_rejected(user, operation, arguments):
    db = database(user=user)
    with pytest.raises(service.ReadOnlyError, match="AUTH_REQUIRED"):
        await operation(db, token(), arguments)
    assert db.execute.await_count == 1


@pytest.mark.asyncio
async def test_report_projection_and_owner_filter():
    row = SimpleNamespace(id=101, type="血常规", interpretation_status="pending", interpretation_at=None)
    db = database(report=row)
    result = await service.get_my_report_status(db, token(), {"report_id": 101})
    statement = db.execute.call_args.args[0]
    compiled = statement.compile()
    assert "reports.patient_id =" in str(compiled)
    assert "reports.id =" in str(compiled)
    assert set(compiled.params.values()) == {101, 17}
    assert "reports.content" not in str(compiled)
    assert "reports.ai_interpretation" not in str(compiled)
    assert result == {"report_id": 101, "type": "血常规", "interpretation_status": "pending", "interpretation_at": None}


@pytest.mark.asyncio
async def test_missing_or_foreign_report_returns_same_not_found():
    with pytest.raises(service.ReadOnlyError, match="NOT_FOUND"):
        await service.get_my_report_status(database(), token(), {"report_id": 202})


@pytest.mark.asyncio
@pytest.mark.parametrize("arguments", [
    {"query": "医学", "top_k": 0}, {"query": "医学", "top_k": 6},
    {"query": "医学", "top_k": True}, {"query": "医学", "top_k": "3"},
    {"query": "   "}, {"query": "a" * 501},
    {"query": "医学", "source_type": "分诊指引"},
    {"query": "医学", "patient_id": 18},
])
async def test_bad_search_arguments_never_reach_retrieval(monkeypatch, arguments):
    search = AsyncMock()
    monkeypatch.setattr(service.rag_service, "search", search)
    with pytest.raises(ValidationError):
        await service.search_medical_references(database(), token(), arguments)
    search.assert_not_awaited()


@pytest.mark.parametrize("arguments", [{"report_id": 0}, {"report_id": True}, {"report_id": 1, "patient_id": 18}])
def test_report_arguments_reject_identity_override(arguments):
    with pytest.raises(ValidationError):
        service.ReportStatusInput.model_validate(arguments)


@pytest.mark.asyncio
async def test_references_are_filtered_bounded_and_do_not_write_query_logs(monkeypatch):
    chunks = [SimpleNamespace(id=i, source="reference", content="x" * 700,
                             chunk_metadata={"source_type": kind, "secret": "never-return"})
              for i, kind in enumerate(["分诊指引", "医学参考资料", "医学参考资料", "医学参考资料"])]
    search = AsyncMock(return_value=chunks)
    monkeypatch.setattr(service.rag_service, "search", search)
    db = database()
    result = await service.search_medical_references(db, token(), {"query": " 医学 ", "top_k": 2})
    search.assert_awaited_once_with(db, query="医学", top_k=2, source_type="医学参考资料", rerank=False, log_query=False)
    assert len(result["references"]) == 2
    assert result["references"][0]["chunk_id"] == 1
    assert len(result["references"][0]["snippet"]) == 500
    assert set(result["references"][0]) == {"chunk_id", "source", "snippet"}
