"""Verify the MCP database connection rejects writes in the isolated DB."""

import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.base import SQLALCHEMY_DATABASE_URL


async def main() -> None:
    engine = create_async_engine(
        SQLALCHEMY_DATABASE_URL,
        echo=False,
        hide_parameters=True,
        connect_args={"server_settings": {"default_transaction_read_only": "on"}},
    )
    try:
        async with engine.connect() as connection:
            read_only = (await connection.execute(text("SHOW transaction_read_only"))).scalar_one()
            if read_only != "on":
                raise RuntimeError("MCP database transaction is not read-only")
            try:
                await connection.execute(text("CREATE TEMP TABLE mcp_readonly_probe (id integer)"))
            except DBAPIError as error:
                if "read-only" not in str(error).lower() and "25006" not in str(error):
                    raise
            else:
                raise RuntimeError("MCP database connection unexpectedly allowed a write")
        print(json.dumps({"transaction_read_only": True, "write_blocked": True}))
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
