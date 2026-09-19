from fastapi.testclient import TestClient

from app.api.client.v1 import config as health_config
from main import app


class _ScalarResult:
    def scalar(self) -> int:
        return 1


class _HealthyDatabaseSession:
    async def execute(self, _query):
        return _ScalarResult()


class _HealthyRedis:
    async def ping(self) -> bool:
        return True


class _UnavailableRedis:
    async def ping(self) -> bool:
        raise ConnectionError("Redis unavailable")


async def _healthy_database():
    yield _HealthyDatabaseSession()


async def _unavailable_database():
    if False:
        yield None
    raise ConnectionError("Database unavailable")


def test_health_returns_200_when_database_and_redis_are_available(monkeypatch):
    monkeypatch.setattr(health_config, "get_db", _healthy_database)
    monkeypatch.setattr(health_config.redis_client, "redis", _HealthyRedis())

    response = TestClient(app).get("/api/v1/config/health")

    assert response.status_code == 200
    assert response.json() == {
        "code": 200,
        "message": "Success",
        "data": {
            "status": "healthy",
            "services": {
                "api": "up",
                "database": "up",
                "redis": "up",
            },
        },
    }


def test_health_returns_503_when_dependencies_are_unavailable(monkeypatch):
    monkeypatch.setattr(health_config, "get_db", _unavailable_database)
    monkeypatch.setattr(health_config.redis_client, "redis", _UnavailableRedis())

    response = TestClient(app).get("/api/v1/config/health")

    assert response.status_code == 503
    assert response.json() == {
        "code": 503,
        "message": "Service unhealthy",
        "data": {
            "status": "unhealthy",
            "services": {
                "api": "up",
                "database": "down",
                "redis": "down",
            },
        },
    }
