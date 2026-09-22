from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.api.client.v1 import auth as client_auth_api
from app.route import route as route_module
from app.schemas.client.auth import Register


def test_production_does_not_register_documentation_routes(monkeypatch):
    monkeypatch.setattr(route_module.settings, "ENV", "production")

    app = route_module.create_app()
    paths = {route.path for route in app.routes}

    assert "/api-docs/client.json" not in paths
    assert "/api-docs/backoffice.json" not in paths
    assert "/client" not in paths
    assert "/backoffice" not in paths


@pytest.mark.asyncio
async def test_registration_is_rate_limited_by_client_address(monkeypatch):
    enforce = AsyncMock()
    register_user = AsyncMock(return_value={"id": 17})
    monkeypatch.setattr(client_auth_api, "enforce_rate_limit", enforce)
    monkeypatch.setattr(client_auth_api.client_auth_service, "register", register_user)
    request = SimpleNamespace(client=SimpleNamespace(host="203.0.113.9"))
    payload = Register(
        email="patient@example.com",
        password="password123",
        first_name="Test",
        last_name="Patient",
    )

    await client_auth_api.register(request, payload, db=object())

    enforce.assert_awaited_once_with(
        "client_register:203.0.113.9",
        limit=5,
        window_seconds=3600,
    )
    register_user.assert_awaited_once()
