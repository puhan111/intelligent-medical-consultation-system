"""Read-only application services; independent of the MCP SDK/transport."""

import re
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.core.security import AuthBase
from app.models.report import Report
from app.models.user import User
from app.services.common import rag_service


class ReadOnlyError(Exception):
    """Stable public error code, with no credentials or dependency details."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class ReportStatusInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    report_id: int = Field(gt=0, le=2147483647)


class ReferenceSearchInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)
    query: str = Field(min_length=1, max_length=500)
    top_k: int = Field(default=3, ge=1, le=5)


def patient_id_from_token(token: str | None) -> int:
    if not token:
        raise ReadOnlyError("AUTH_REQUIRED")
    payload = AuthBase.verify_token(token, scope="client")
    if not payload:
        raise ReadOnlyError("AUTH_REQUIRED")
    subject = payload.get("sub")
    expiry = payload.get("exp")
    # The existing decoder accepts tokens without exp; this entry requires it.
    if (
        not isinstance(subject, str)
        or not re.fullmatch(r"[1-9][0-9]{0,9}", subject)
        or int(subject) > 2147483647
        or type(expiry) not in (int, float)
        or not expiry > datetime.now(timezone.utc).timestamp()
    ):
        raise ReadOnlyError("AUTH_REQUIRED")
    return int(subject)


async def current_patient(db, token: str | None) -> int:
    patient_id = patient_id_from_token(token)
    result = await db.execute(select(User).where(User.id == patient_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise ReadOnlyError("AUTH_REQUIRED")
    return patient_id


async def get_my_report_status(db, token: str | None, arguments: dict) -> dict:
    patient_id = await current_patient(db, token)
    params = ReportStatusInput.model_validate(arguments)
    result = await db.execute(
        select(Report.id, Report.type, Report.interpretation_status, Report.interpretation_at)
        .where(Report.id == params.report_id, Report.patient_id == patient_id)
    )
    row = result.one_or_none()
    if row is None:
        raise ReadOnlyError("NOT_FOUND")
    return {
        "report_id": row.id,
        "type": row.type,
        "interpretation_status": row.interpretation_status,
        "interpretation_at": row.interpretation_at.isoformat() if row.interpretation_at else None,
    }


async def search_medical_references(db, token: str | None, arguments: dict) -> dict:
    await current_patient(db, token)
    params = ReferenceSearchInput.model_validate(arguments)
    chunks = await rag_service.search(
        db, query=params.query, top_k=params.top_k,
        source_type="医学参考资料", rerank=False, log_query=False,
    )
    return {"references": [
        {"chunk_id": chunk.id, "source": chunk.source[:500], "snippet": chunk.content[:500]}
        for chunk in chunks
        if (chunk.chunk_metadata or {}).get("source_type") == "医学参考资料"
    ][:params.top_k]}
