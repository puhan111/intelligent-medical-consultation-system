"""Read-only local MCP client. Paste an access token into a hidden prompt."""

import argparse
import asyncio
import getpass
import json

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def run(report_id: int, query: str, token: str):
    async with httpx.AsyncClient(
        headers={"Authorization": f"Bearer {token}"}, timeout=30,
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
    parser.add_argument("--report-id", type=int, required=True)
    parser.add_argument("--query", required=True)
    args = parser.parse_args()
    access_token = getpass.getpass("患者 access token（不会回显）: ")
    asyncio.run(run(args.report_id, args.query, access_token))
