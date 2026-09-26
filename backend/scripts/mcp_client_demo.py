"""Read-only local MCP client. Login or paste a token without echoing secrets."""

import argparse
import asyncio
import getpass
import json

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def login(email: str, password: str) -> str:
    async with httpx.AsyncClient(timeout=30, trust_env=False) as http:
        response = await http.post(
            "http://127.0.0.1:18001/api/v1/auth/login",
            json={"email": email, "password": password},
        )
    if response.status_code != 200:
        raise RuntimeError(f"患者登录失败（HTTP {response.status_code}）")
    data = response.json().get("data") or {}
    token = data.get("access_token") if isinstance(data, dict) else None
    if not isinstance(token, str) or not token:
        raise RuntimeError("患者登录响应未包含访问令牌")
    return token


async def run(report_id: int, query: str, token: str):
    async with httpx.AsyncClient(
        headers={"Authorization": f"Bearer {token}"}, timeout=30, trust_env=False,
    ) as http:
        async with streamable_http_client(
            "http://127.0.0.1:8765/mcp/", http_client=http,
        ) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print("Tools:", ", ".join(tool.name for tool in (await session.list_tools()).tools))
                for name, arguments in (
                    ("get_my_report_status", {"report_id": report_id}),
                    ("search_medical_references", {"query": query, "top_k": 3}),
                ):
                    result = await session.call_tool(name, arguments)
                    print(json.dumps({"tool": name, "isError": result.isError,
                                      "data": result.structuredContent}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-id", type=int, default=1)
    parser.add_argument("--query", default="合成参考资料 XQ-9")
    parser.add_argument("--login", action="store_true", help="通过患者账号登录，不显示密码或令牌")
    args = parser.parse_args()
    if args.login:
        email = input("患者邮箱: ").strip()
        password = getpass.getpass("患者密码（不会回显）: ")
        access_token = asyncio.run(login(email, password))
    else:
        access_token = getpass.getpass("患者 access token（不会回显）: ")
    asyncio.run(run(args.report_id, args.query, access_token))
