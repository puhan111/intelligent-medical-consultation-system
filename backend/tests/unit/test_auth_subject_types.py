import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.security import AuthBase
from app.services.backoffice.auth import BackofficeAuthService
from app.services.client.auth import ClientAuthService


@pytest.mark.parametrize("service", [ClientAuthService, BackofficeAuthService])
@pytest.mark.parametrize("action", ["refresh_token", "logout"])
def test_string_jwt_subject_uses_integer_database_bind(monkeypatch, service, action):
    monkeypatch.setattr(AuthBase, "verify_token", staticmethod(lambda token, scope=None: {"sub": "7"}))
    monkeypatch.setattr(AuthBase, "verify_token_hash", staticmethod(lambda plain, hashed: True))
    monkeypatch.setattr(AuthBase, "create_access_token", staticmethod(lambda *args, **kwargs: "synthetic-access"))
    stored = SimpleNamespace(token="synthetic-hash", is_active=True, last_used_at=None)

    async def execute(statement):
        # The fake session still checks the parameter sent to PostgreSQL.
        assert list(statement.compile().params.values()) == [7]
        return SimpleNamespace(scalar_one_or_none=lambda: stored)

    db = SimpleNamespace(execute=execute, commit=AsyncMock())
    asyncio.run(getattr(service, action)(db, "synthetic-refresh"))
