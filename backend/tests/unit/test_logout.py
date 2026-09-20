import asyncio
from types import SimpleNamespace

import pytest

from app.core.security import AuthBase
from app.services.backoffice.auth import BackofficeAuthService
from app.services.client.auth import ClientAuthService


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _DatabaseSession:
    def __init__(self, stored_token):
        self.stored_token = stored_token
        self.commit_count = 0

    async def execute(self, _query):
        return _ScalarResult(self.stored_token)

    async def commit(self):
        self.commit_count += 1


@pytest.mark.parametrize(
    "logout",
    [ClientAuthService.logout, BackofficeAuthService.logout],
)
def test_logout_validates_refresh_scope_and_revokes_stored_token(monkeypatch, logout):
    requested_scopes = []

    def verify_refresh_token(_token, scope=None):
        requested_scopes.append(scope)
        return {"sub": "7"} if scope == "refresh" else None

    monkeypatch.setattr(AuthBase, "verify_token", staticmethod(verify_refresh_token))

    stored_token = SimpleNamespace(is_active=True)
    db = _DatabaseSession(stored_token)

    asyncio.run(logout(db, "signed-refresh-token"))

    assert requested_scopes == ["refresh"]
    assert stored_token.is_active is False
    assert db.commit_count == 1
