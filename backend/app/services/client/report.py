from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.report import Report
from app.schemas.client.report import ReportResponse
from typing import List


class ReportService:
    @staticmethod
    async def get_my_reports_query(db: AsyncSession, patient_id: int):
        """获取患者的报告列表查询对象（用于分页）"""
        query = select(Report).where(Report.patient_id == patient_id)
        query = query.order_by(Report.created_at.desc())
        return query

    @staticmethod
    async def list_reports(db: AsyncSession, reports: List[Report]) -> List[ReportResponse]:
        """批量转换报告列表为响应模型"""
        return [ReportResponse.model_validate(r) for r in reports]


report_service = ReportService()
