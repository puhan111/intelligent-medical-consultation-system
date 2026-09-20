import asyncio
import logging
import socket
import threading
import time
from contextlib import asynccontextmanager
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
import uvicorn
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from starlette.testclient import TestClient

from app.core.security import AuthBase
from app import mcp_server
from app.mcp_server import create_app
from app.services.common import mcp_readonly as service


class SyntheticDatabase:
    """Interpret the real SQL predicates over two synthetic patients/reports."""

    def __init__(self):
        self.disabled = set()

    async def execute(self, statement):
        params = statement.compile().params
        if "users" in str(statement):
            user_id = params["id_1"]
            user = SimpleNamespace(id=user_id, is_active=user_id not in self.disabled) if user_id in (17, 18) else None
            return SimpleNamespace(scalar_one_or_none=lambda: user)
        owner = {101: 17, 202: 18}.get(params["id_1"])
        row = None
        if owner is not None and owner == params["patient_id_1"]:
            row = SimpleNamespace(id=params["id_1"], type="合成报告", interpretation_status="pending", interpretation_at=None)
        return SimpleNamespace(one_or_none=lambda: row)


def make_app(db=None):
    db = db or SyntheticDatabase()

    @asynccontextmanager
    async def session_factory():
        yield db

    return create_app(session_factory)


def headers(subject="17", scope="client"):
    return {"Authorization": "Bearer " + AuthBase.create_access_token(subject, scope),
            "Accept": "application/json, text/event-stream"}


def rpc(client, method, params=None, credential=None):
    return client.post("/mcp/", headers=credential or headers(), json={
        "jsonrpc": "2.0", "id": 1, "method": method, "params": params or {},
    })


@pytest.mark.parametrize("credential", [None, "Bearer broken", "Basic anything",
    "Bearer " + AuthBase.create_access_token("17", "backoffice"),
    "Bearer " + AuthBase.create_access_token("17", "client", timedelta(seconds=-1)),
], ids=["missing", "malformed", "wrong-scheme", "wrong-scope", "expired"])
def test_http_auth_required_even_for_discovery(credential):
    with TestClient(make_app(), base_url="http://127.0.0.1:8765") as client:
        response = client.post("/mcp/", headers={"Authorization": credential} if credential else {}, json={})
        assert response.status_code == 401
        assert response.json() == {"error": "AUTH_REQUIRED"}


def test_discovery_schema_exposes_only_two_bounded_readonly_tools():
    with TestClient(make_app(), base_url="http://127.0.0.1:8765") as client:
        response = rpc(client, "tools/list")
        assert response.status_code == 200
        tools = {tool["name"]: tool for tool in response.json()["result"]["tools"]}
        assert set(tools) == {"get_my_report_status", "search_medical_references"}
        for tool in tools.values():
            assert tool["annotations"]["readOnlyHint"] is True
            assert tool["inputSchema"]["additionalProperties"] is False
            assert not {"patient_id", "token", "source_type"} & set(tool["inputSchema"]["properties"])
        assert tools["search_medical_references"]["inputSchema"]["properties"]["top_k"]["maximum"] == 5


@pytest.mark.parametrize("name,arguments,code", [
    ("get_my_report_status", {"report_id": 202}, "NOT_FOUND"),
    ("get_my_report_status", {"report_id": 999}, "NOT_FOUND"),
    ("get_my_report_status", {"report_id": 101, "patient_id": 18}, "INVALID_ARGUMENT"),
    ("search_medical_references", {"query": "sensitive-input", "top_k": 6}, "INVALID_ARGUMENT"),
    ("search_medical_references", {"query": "sensitive-input", "source_type": "分诊指引"}, "INVALID_ARGUMENT"),
    ("write_report", {}, "UNKNOWN_TOOL"),
])
def test_protocol_error_codes_do_not_echo_private_arguments(name, arguments, code):
    with TestClient(make_app(), base_url="http://127.0.0.1:8765") as client:
        response = rpc(client, "tools/call", {"name": name, "arguments": arguments})
        result = response.json()["result"]
        assert result["isError"] is True
        assert result["structuredContent"] == {"error": {"code": code}}
        assert "sensitive-input" not in response.text


@pytest.mark.parametrize("subject", ["18", "19"])
def test_disabled_or_missing_user_cannot_call_tools(subject):
    db = SyntheticDatabase()
    db.disabled.add(18)
    with TestClient(make_app(db), base_url="http://127.0.0.1:8765") as client:
        result = rpc(client, "tools/call", {"name": "get_my_report_status", "arguments": {"report_id": 101}}, headers(subject)).json()["result"]
        assert result["structuredContent"]["error"]["code"] == "AUTH_REQUIRED"


def test_dependency_errors_are_redacted_from_results_and_application_logs(monkeypatch, caplog):
    monkeypatch.setattr(service.rag_service, "search", AsyncMock(side_effect=RuntimeError("private-key-and-sql")))
    caplog.set_level(logging.INFO, logger="medical_mcp")
    with TestClient(make_app(), base_url="http://127.0.0.1:8765") as client:
        response = rpc(client, "tools/call", {"name": "search_medical_references", "arguments": {"query": "private-question"}})
        assert response.json()["result"]["structuredContent"]["error"]["code"] == "SERVICE_UNAVAILABLE"
        assert "private-key-and-sql" not in response.text + caplog.text
        assert "private-question" not in caplog.text
        assert "outcome=SERVICE_UNAVAILABLE" in caplog.text


def test_database_failure_returns_safe_error():
    db = SimpleNamespace(execute=AsyncMock(side_effect=RuntimeError("private-connection-url")))
    with TestClient(make_app(db), base_url="http://127.0.0.1:8765") as client:
        response = rpc(client, "tools/call", {"name": "get_my_report_status", "arguments": {"report_id": 101}})
        assert response.json()["result"]["structuredContent"]["error"]["code"] == "SERVICE_UNAVAILABLE"
        assert "private-connection-url" not in response.text


def test_same_token_stops_working_when_patient_is_disabled():
    db = SyntheticDatabase()
    credential = headers()
    params = {"name": "get_my_report_status", "arguments": {"report_id": 101}}
    with TestClient(make_app(db), base_url="http://127.0.0.1:8765") as client:
        assert rpc(client, "tools/call", params, credential).json()["result"]["isError"] is False
        db.disabled.add(17)
        assert rpc(client, "tools/call", params, credential).json()["result"]["structuredContent"]["error"]["code"] == "AUTH_REQUIRED"


def test_default_engine_uses_private_readonly_configuration_and_is_disposed(monkeypatch):
    engine = SimpleNamespace(dispose=AsyncMock())
    observed = {}

    def build_engine(url, **kwargs):
        observed.update(kwargs)
        return engine

    monkeypatch.setattr(mcp_server, "create_async_engine", build_engine)
    monkeypatch.setattr(mcp_server, "async_sessionmaker", lambda *args, **kwargs: None)
    with TestClient(create_app(), base_url="http://127.0.0.1:8765") as client:
        assert client.post("/mcp/", json={}).status_code == 401
    assert observed["echo"] is False
    assert observed["hide_parameters"] is True
    assert observed["connect_args"]["server_settings"]["default_transaction_read_only"] == "on"
    engine.dispose.assert_awaited_once()


@pytest.mark.parametrize("extra_headers", [{"Host": "evil.example"}, {"Origin": "https://evil.example"}])
def test_transport_rejects_untrusted_host_and_origin(extra_headers):
    with TestClient(make_app(), base_url="http://127.0.0.1:8765") as client:
        response = rpc(client, "tools/list", credential=headers() | extra_headers)
        assert response.status_code in (403, 421)


@pytest.mark.asyncio
async def test_real_sdk_discovery_calls_and_concurrent_identity_isolation(monkeypatch):
    monkeypatch.setattr(service.rag_service, "search", AsyncMock(return_value=[
        SimpleNamespace(id=1, source="synthetic://reference", content="合成参考片段",
                        chunk_metadata={"source_type": "医学参考资料"}),
    ]))
    app = make_app()

    async def patient_session(patient, own_report, foreign_report):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), headers=headers(patient)) as http:
            async with streamable_http_client("http://127.0.0.1:8765/mcp/", http_client=http) as (read, write, _):
                async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=10)) as session:
                    await session.initialize()
                    assert len((await session.list_tools()).tools) == 2
                    result = await session.call_tool("get_my_report_status", {"report_id": own_report})
                    assert not result.isError
                    assert result.structuredContent["report_id"] == own_report
                    denied = await session.call_tool("get_my_report_status", {"report_id": foreign_report})
                    assert denied.isError
                    assert denied.structuredContent["error"]["code"] == "NOT_FOUND"
                    references = await session.call_tool("search_medical_references", {"query": "参考资料"})
                    assert not references.isError
                    assert references.structuredContent["references"][0]["source"] == "synthetic://reference"

    async with app.router.lifespan_context(app):
        await asyncio.wait_for(asyncio.gather(patient_session("17", 101, 202), patient_session("18", 202, 101)), timeout=20)


def test_sdk_over_real_loopback_http_with_synthetic_dependencies(monkeypatch):
    """Real TCP + SDK; never touches PostgreSQL, Redis or model APIs."""
    monkeypatch.setattr(service.rag_service, "search", AsyncMock(return_value=[]))
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(make_app(), host="127.0.0.1", port=port,
                                          log_level="warning", access_log=False))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
    thread.start()

    async def client_demo():
        async with httpx.AsyncClient(headers=headers(), timeout=5) as http:
            async with streamable_http_client(f"http://127.0.0.1:{port}/mcp/", http_client=http) as (read, write, _):
                async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=5)) as client:
                    initialized = await client.initialize()
                    assert initialized.serverInfo.name == "medical-readonly"
                    assert len((await client.list_tools()).tools) == 2
                    report = await client.call_tool("get_my_report_status", {"report_id": 101})
                    assert not report.isError
                    assert report.structuredContent["report_id"] == 101
                    references = await client.call_tool("search_medical_references", {"query": "不存在的合成资料"})
                    assert references.structuredContent == {"references": []}
    try:
        deadline = time.monotonic() + 5
        while not server.started and thread.is_alive() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert server.started
        asyncio.run(asyncio.wait_for(client_demo(), timeout=15))
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        listener.close()
    assert not thread.is_alive()
