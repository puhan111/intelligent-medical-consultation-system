import csv
import io
import logging

from fastapi import APIRouter, Depends, File, Form, UploadFile
from kombu.exceptions import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db, transaction
from app.schemas.backoffice.report import ReportCreate, ReportPatientResponse, ReportResponse
from app.services.backoffice.report import report_service
from app.api.backoffice.deps import get_current_lab
from app.schemas.response import ApiResponse
from app.schedule.jobs.report_interpret import execute as report_interpret_task
from app.exceptions.http_exceptions import APIException
from app.schemas.paginator import Paginator


router = APIRouter()
logger = logging.getLogger(__name__)
MAX_CSV_SIZE = 1024 * 1024
MAX_CSV_ROWS = 200
CSV_COLUMNS = ("项目名称", "缩写", "结果", "单位", "参考范围", "状态", "检验结论")
STATUS_MAP = {
    "正常": "normal", "偏高": "high", "高": "high", "偏低": "low", "低": "low",
    "危急": "critical", "异常": "abnormal",
    "normal": "normal", "high": "high", "low": "low",
    "critical": "critical", "abnormal": "abnormal",
}


def _enqueue_report_interpretation(report_id: int):
    publish_options = {
        "queue": "celery",
        "retry": True,
        "retry_policy": {
            "max_retries": 3,
            "interval_start": 0,
            "interval_step": 0.5,
            "interval_max": 1,
        },
    }
    try:
        return report_interpret_task.apply_async(args=[report_id], **publish_options)
    except OperationalError:
        report_interpret_task.app.close()
        return report_interpret_task.apply_async(args=[report_id], **publish_options)


async def _create_and_enqueue_report(db: AsyncSession, report_data: ReportCreate):
    async with transaction(db):
        result = await report_service.create_report(db, report_data)

    try:
        _enqueue_report_interpretation(result.id)
    except OperationalError as exc:
        logger.exception("Failed to enqueue report interpretation task: report_id=%s", result.id)
        raise APIException(
            code=1005,
            message="Task queue unavailable, please retry later",
            status_code=503,
        ) from exc
    return result


def _decode_csv(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise APIException(status_code=400, message="CSV file must use UTF-8 encoding")


def _parse_report_csv(raw: bytes) -> dict:
    reader = csv.DictReader(io.StringIO(_decode_csv(raw)))
    headers = [header.strip() for header in (reader.fieldnames or []) if header]
    required = {"项目名称", "结果"}
    if not required.issubset(headers):
        raise APIException(status_code=400, message="CSV must contain columns: 项目名称, 结果")

    items = []
    conclusion = None
    for index, row in enumerate(reader, start=2):
        if len(items) >= MAX_CSV_ROWS:
            raise APIException(status_code=400, message=f"CSV cannot contain more than {MAX_CSV_ROWS} data rows")
        normalized = {(key or "").strip(): (value or "").strip() for key, value in row.items()}
        if not any(normalized.values()):
            continue
        name = normalized.get("项目名称", "")
        value = normalized.get("结果", "")
        if not name or not value:
            raise APIException(status_code=400, message=f"CSV row {index}: 项目名称 and 结果 are required")
        raw_status = normalized.get("状态", "")
        if raw_status and raw_status not in STATUS_MAP:
            raise APIException(
                status_code=400,
                message=f"CSV row {index}: 状态 must be 正常/偏高/偏低/危急/异常",
            )
        items.append({
            "name": name,
            "code": normalized.get("缩写") or None,
            "value": value,
            "unit": normalized.get("单位") or None,
            "reference_range": normalized.get("参考范围") or None,
            "status": STATUS_MAP.get(raw_status) if raw_status else None,
        })
        if normalized.get("检验结论"):
            conclusion = normalized["检验结论"]

    if not items:
        raise APIException(status_code=400, message="CSV does not contain any report items")
    return {"items": items, "conclusion": conclusion}


@router.get("/patients")
async def list_report_patients(
    page: int = 1,
    per_page: int = 10,
    keyword: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_lab),
):
    """检验检查人员分页查询患者，用于直接选择报告归属人。"""
    query = report_service.get_patients_query(keyword)
    result = await Paginator(query, db).paginate(page, min(per_page, 100))
    return ApiResponse.success(data={
        "items": [ReportPatientResponse.model_validate(item) for item in result.items],
        "total": result.total,
        "per_page": result.per_page,
        "current_page": result.current_page,
        "last_page": result.last_page,
        "has_more": result.has_more,
    })


@router.get("/exam-pending")
async def list_exam_pending_appointments(
    page: int = 1,
    per_page: int = 10,
    keyword: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_lab),
):
    """检验科查询医生已标记为等待检查结果的就诊。"""
    query = report_service.get_exam_pending_appointments_query(keyword)
    result = await Paginator(query, db).paginate(page, min(per_page, 100))
    response_items = await report_service.list_exam_pending(db, result.items)
    return ApiResponse.success(data={
        "items": response_items,
        "total": result.total,
        "per_page": result.per_page,
        "current_page": result.current_page,
        "last_page": result.last_page,
        "has_more": result.has_more,
    })


@router.get("", response_model=list[ReportResponse])
async def list_reports(
    page: int = 1,
    per_page: int = 10,
    status_filter: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_lab),
):
    """
    检验科查看已录入的报告列表

    Args:
        status_filter: 可选解读状态过滤，pending / completed / failed，不传返回全部
    """
    if status_filter and status_filter not in ("pending", "completed", "failed"):
        raise APIException(
            status_code=400,
            message="status_filter must be 'pending', 'completed' or 'failed'",
        )

    query = report_service.get_reports_query(status_filter)
    result = await Paginator(query, db).paginate(page, min(per_page, 100))
    response_items = await report_service.list_reports(db, result.items)

    return ApiResponse.success(data={
        "items": response_items,
        "total": result.total,
        "per_page": result.per_page,
        "current_page": result.current_page,
        "last_page": result.last_page,
        "has_more": result.has_more,
    })


@router.post("/{report_id}/retry-interpretation", response_model=ReportResponse)
async def retry_interpretation(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_lab),
):
    """重新触发解读失败报告的 AI 解读（仅检验科）"""
    async with transaction(db):
        result = await report_service.prepare_retry(db, report_id)

    try:
        _enqueue_report_interpretation(report_id)
    except OperationalError as exc:
        logger.exception("Failed to enqueue retry interpretation: report_id=%s", report_id)
        raise APIException(
            code=1005,
            message="Task queue unavailable, please retry later",
            status_code=503,
        ) from exc

    return ApiResponse.success(data=result)


@router.post("", response_model=ReportResponse)
async def create_report(
    report_data: ReportCreate,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_lab)
):
    """检验科上传报告，落库后触发 Celery 异步 AI 解读"""
    result = await _create_and_enqueue_report(db, report_data)
    return ApiResponse.success(data=result)


@router.post("/upload-csv", response_model=ReportResponse)
async def upload_report_csv(
    patient_id: int = Form(...),
    appointment_id: int = Form(...),
    report_type: str = Form(..., min_length=1, max_length=50),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_lab),
):
    """上传 UTF-8 CSV 最终报告，解析为结构化指标后触发 AI 解读。"""
    filename = file.filename or ""
    if not filename.lower().endswith(".csv"):
        raise APIException(status_code=400, message="Only CSV files are supported")

    raw = await file.read(MAX_CSV_SIZE + 1)
    await file.close()
    if len(raw) > MAX_CSV_SIZE:
        raise APIException(status_code=400, message="CSV file size cannot exceed 1 MB")

    report_data = ReportCreate(
        patient_id=patient_id,
        appointment_id=appointment_id,
        type=report_type.strip(),
        content=_parse_report_csv(raw),
    )
    result = await _create_and_enqueue_report(db, report_data)
    return ApiResponse.success(data=result)
