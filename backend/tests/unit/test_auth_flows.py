import asyncio
from types import SimpleNamespace

import pytest

from app.core.security import AuthBase
from app.exceptions.http_exceptions import APIException
from app.services.backoffice.auth import BackofficeAuthService
from app.services.client.auth import ClientAuthService


AUTH_CASES = [
    (ClientAuthService, "authenticate_user", "client", "user_id"),
    (BackofficeAuthService, "authenticate_admin", "backoffice", "admin_id"),
]


class _ScalarResult:
    def __init__(self, value=None):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _DatabaseSession:
    def __init__(self, result=None):
        self.result = result
        self.execute_count = 0
        self.added_objects = []
        self.flush_count = 0
        self.commit_count = 0
        self.rollback_count = 0

    async def execute(self, _statement):
        self.execute_count += 1
        return _ScalarResult(self.result)

    def add(self, value):
        self.added_objects.append(value)

    async def flush(self):
        self.flush_count += 1

    async def commit(self):
        self.commit_count += 1

    async def rollback(self):
        self.rollback_count += 1


@pytest.mark.parametrize("service,authenticate_name,scope,id_field", AUTH_CASES)
def test_login_success_replaces_old_token_and_uses_role_scope(
    monkeypatch, service, authenticate_name, scope, id_field
):
    account = SimpleNamespace(id=7, is_active=True)

    async def authenticate(*_args, **_kwargs):
        return account

    access_calls = []

    def create_access_token(subject, scope, expires_delta=None):
        access_calls.append((subject, scope, expires_delta))
        return "signed-access-token"

    monkeypatch.setattr(service, authenticate_name, staticmethod(authenticate))
    monkeypatch.setattr(AuthBase, "create_access_token", staticmethod(create_access_token))
    monkeypatch.setattr(
        AuthBase,
        "create_refresh_token",
        staticmethod(lambda subject: f"refresh-for-{subject}"),
    )
    monkeypatch.setattr(AuthBase, "hash_token", staticmethod(lambda token: f"hash:{token}"))
    db = _DatabaseSession()

    result = asyncio.run(service.login(db, "person@example.com", "correct-password"))

    assert result == {
        "access_token": "signed-access-token",
        "refresh_token": "refresh-for-7",
        "token_type": "bearer",
    }
    assert access_calls[0][0:2] == ("7", scope)
    assert db.execute_count == 1
    assert db.flush_count == 1
    assert db.commit_count == 1
    assert db.rollback_count == 0
    assert len(db.added_objects) == 1
    assert getattr(db.added_objects[0], id_field) == 7
    assert db.added_objects[0].token == "hash:refresh-for-7"
    assert db.added_objects[0].is_active is True


@pytest.mark.parametrize("service,authenticate_name,_scope,_id_field", AUTH_CASES)
def test_login_wrong_credentials_roll_back_transaction(
    monkeypatch, service, authenticate_name, _scope, _id_field
):
    async def reject_credentials(*_args, **_kwargs):
        return None

    monkeypatch.setattr(service, authenticate_name, staticmethod(reject_credentials))
    db = _DatabaseSession()

    with pytest.raises(APIException) as exc_info:
        asyncio.run(service.login(db, "person@example.com", "wrong-password"))

    assert exc_info.value.status_code == 400
    assert db.commit_count == 0
    assert db.rollback_count == 1
    assert db.added_objects == []


@pytest.mark.parametrize("service,_authenticate_name,scope,_id_field", AUTH_CASES)
def test_refresh_token_success_updates_last_used_and_uses_role_scope(
    monkeypatch, service, _authenticate_name, scope, _id_field
):
    stored_token = SimpleNamespace(token="stored-hash", last_used_at=None)
    db = _DatabaseSession(result=stored_token)
    verified_scopes = []
    access_calls = []

    def verify_token(_token, scope=None):
        verified_scopes.append(scope)
        return {"sub": "7"}

    def create_access_token(subject, scope, expires_delta=None):
        access_calls.append((subject, scope, expires_delta))
        return "new-access-token"

    monkeypatch.setattr(AuthBase, "verify_token", staticmethod(verify_token))
    monkeypatch.setattr(
        AuthBase,
        "verify_token_hash",
        staticmethod(lambda plain, hashed: (plain, hashed) == ("refresh-token", "stored-hash")),
    )
    monkeypatch.setattr(AuthBase, "create_access_token", staticmethod(create_access_token))

    result = asyncio.run(service.refresh_token(db, "refresh-token"))

    assert result == {"access_token": "new-access-token", "token_type": "bearer"}
    assert verified_scopes == ["refresh"]
    assert access_calls[0][0:2] == ("7", scope)
    assert stored_token.last_used_at is not None
    assert stored_token.last_used_at.tzinfo is not None
    assert db.execute_count == 1
    assert db.commit_count == 1


@pytest.mark.parametrize("service,_authenticate_name,_scope,_id_field", AUTH_CASES)
def test_invalid_refresh_token_is_rejected_before_database_lookup(
    monkeypatch, service, _authenticate_name, _scope, _id_field
):
    monkeypatch.setattr(
        AuthBase,
        "verify_token",
        staticmethod(lambda _token, scope=None: None),
    )
    db = _DatabaseSession()

    with pytest.raises(APIException) as exc_info:
        asyncio.run(service.refresh_token(db, "invalid-token"))

    assert exc_info.value.status_code == 401
    assert db.execute_count == 0
    assert db.commit_count == 0
