"""Check MCP report ownership against the isolated PostgreSQL database.

Two synthetic patients and one report exist only inside an uncommitted
transaction. The transaction is rolled back even when an assertion fails.
"""

import asyncio
import json
import sys
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.security import AuthBase
from app.db.base import SQLALCHEMY_DATABASE_URL
from app.models.report import Report
from app.models.user import User
from app.services.common.mcp_readonly import ReadOnlyError, get_my_report_status


async def main() -> None:
    engine = create_async_engine(
        SQLALCHEMY_DATABASE_URL, echo=False, hide_parameters=True,
    )
    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            patient_ids = []
            report_id = None
            try:
                async with AsyncSession(bind=connection, expire_on_commit=False) as db:
                    marker = uuid.uuid4().hex
                    owner = User(email=f"mcp-owner-{marker}@example.invalid", is_active=True)
                    other = User(email=f"mcp-other-{marker}@example.invalid", is_active=True)
                    db.add_all([owner, other])
                    await db.flush()
                    patient_ids = [owner.id, other.id]

                    report = Report(
                        patient_id=owner.id,
                        type="MCP合成权限测试",
                        content={"synthetic": True},
                        interpretation_status="pending",
                    )
                    db.add(report)
                    await db.flush()
                    report_id = report.id

                    owner_token = AuthBase.create_access_token(str(owner.id), "client")
                    other_token = AuthBase.create_access_token(str(other.id), "client")
                    owned = await get_my_report_status(db, owner_token, {"report_id": report_id})
                    if owned["report_id"] != report_id:
                        raise AssertionError("Owner could not read own report")
                    try:
                        await get_my_report_status(db, other_token, {"report_id": report_id})
                    except ReadOnlyError as error:
                        if error.code != "NOT_FOUND":
                            raise AssertionError(f"Unexpected cross-patient error: {error.code}") from error
                    else:
                        raise AssertionError("Another patient could read the report")
            finally:
                await transaction.rollback()

            async with AsyncSession(bind=connection) as check:
                remaining_users = (await check.execute(
                    select(User.id).where(User.id.in_(patient_ids))
                )).all()
                remaining_report = (await check.execute(
                    select(Report.id).where(Report.id == report_id)
                )).first()
                if remaining_users or remaining_report:
                    raise AssertionError("Rollback left synthetic data in the database")

        print(json.dumps({
            "owner_allowed": True,
            "other_patient_blocked": True,
            "database_rolled_back": True,
        }))
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
