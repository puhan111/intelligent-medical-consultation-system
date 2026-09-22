import pytest
from jose import jwt

from app.core.config import settings
from app.core.security import AuthBase


def signed(payload):
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


@pytest.mark.parametrize(
    "payload",
    [
        {"sub": "17", "scope": "client"},
        {"sub": "17", "exp": 9_999_999_999},
        {"scope": "client", "exp": 9_999_999_999},
        {"sub": "abc", "scope": "client", "exp": 9_999_999_999},
        {"sub": "0", "scope": "client", "exp": 9_999_999_999},
        {"sub": "2147483648", "scope": "client", "exp": 9_999_999_999},
    ],
)
def test_verify_token_rejects_missing_or_invalid_required_claims(payload):
    assert AuthBase.verify_token(signed(payload), scope="client") is None


def test_verify_token_accepts_created_access_token():
    token = AuthBase.create_access_token("17", "client")
    payload = AuthBase.verify_token(token, scope="client")
    assert payload is not None
    assert payload["sub"] == "17"
