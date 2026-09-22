import pytest
from pydantic import ValidationError

from app.core.config import Settings


def production_settings(**overrides):
    values = {
        "ENV": "production",
        "SECRET_KEY": "s" * 32,
        "DASHSCOPE_API_KEY": "dashscope-realistic-test-value",
        "DEEPSEEK_API_KEY": "deepseek-realistic-test-value",
        "CORS_ORIGINS": "https://patient.example.com, https://admin.example.com",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_production_requires_non_placeholder_secrets():
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        production_settings(SECRET_KEY="your-secret-key-change-in-production")


def test_production_rejects_wildcard_cors():
    with pytest.raises(ValidationError, match="CORS_ORIGINS"):
        production_settings(CORS_ORIGINS="*")


def test_production_parses_explicit_cors_origins():
    settings = production_settings()
    assert settings.allowed_origins == [
        "https://patient.example.com",
        "https://admin.example.com",
    ]
