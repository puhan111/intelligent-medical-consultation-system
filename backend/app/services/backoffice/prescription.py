from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime, UTC
from app.models.prescription import Prescription, PrescriptionItem
from app.models.appointment import Appointment
from app.models.bill import Bill
from app.models.dispense_record import DispenseRecord
from app.models.drug import Drug
from app.models.user import User
from app.schemas.backoffice.prescription import PrescriptionCreate, PrescriptionResponse, PrescriptionItemResponse
from app.exceptions.http_exceptions import APIException
from decimal import Decimal
from typing import List, Optional
from fastapi import status


class PrescriptionService:
    @staticmethod
    async def _to_response(db: AsyncSession, prescription: Prescription) -> PrescriptionResponse:
        """组装处方响应（补充医生、患者姓名与处方明细）"""
        from app.models.doctor import Doctor
        from app.models.admin import Admin

        doctor_query = select(Doctor).where(Doctor.id == prescription.doctor_id)
        doctor = (await db.execute(doctor_query)).scalar_one_or_none()

        appointment_query = select(Appointment).where(Appointment.id == prescription.appointment_id)
        appointment = (await db.execute(appointment_query)).scalar_one_or_none()

        items_query = select(PrescriptionItem).where(PrescriptionItem.prescription_id == prescription.id)
        items = (await db.execute(items_query)).scalars().all()

        response = PrescriptionResponse.model_validate(prescription)
        item_responses = []
        total = Decimal("0")
        for item in items:
            r = PrescriptionItemResponse.model_validate(item)
            if item.unit_price is not None:
                subtotal = Decimal(str(item.unit_price)) * item.quantity
                r.subtotal = float(subtotal)
                # 合计只累加已勾选项，与实际生成账单的口径一致
                if item.is_selected:
                    total += subtotal
            item_responses.append(r)

        response.items = item_responses
        response.total_amount = float(total)

        if doctor:
            admin_query = select(Admin).where(Admin.id == doctor.admin_id)
            admin = (await db.execute(admin_query)).scalar_one_or_none()
            if admin:
                response.doctor_name = f"{admin.last_name}{admin.first_name}" if admin.last_name and admin.first_name else admin.email

        if appointment:
            user_query = select(User).where(User.id == appointment.patient_id)
            user = (await db.execute(user_query)).scalar_one_or_none()
            if user:
                response.patient_name = f"{user.last_name}{user.first_name}" if user.last_name and user.first_name else user.email

        return response

    @staticmethod
    async def create_prescription(
        db: AsyncSession,
        doctor_id: int,
        prescription_data: PrescriptionCreate
    ) -> PrescriptionResponse:
        """医生开处方（只能为分配给自己的预约开处方）"""
        appointment_query = select(Appointment).where(
            Appointment.id == prescription_data.appointment_id,
            Appointment.doctor_id == doctor_id
        )
        appointment = (await db.execute(appointment_query)).scalar_one_or_none()
        if not appointment:
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Appointment not found"
            )

        if not prescription_data.items:
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Prescription must contain at least one item"
            )

        prescription = Prescription(
            appointment_id=appointment.id,
            doctor_id=doctor_id,
            status="pending"
        )
        db.add(prescription)
        await db.flush()

        for item_data in prescription_data.items:
            drug_name = item_data.drug_name
            unit_price = None

            # 从药品目录选药时，快照药名与单价：目录日后调价不影响历史处方金额
            if item_data.drug_id is not None:
                drug = (
                    await db.execute(select(Drug).where(Drug.id == item_data.drug_id))
                ).scalar_one_or_none()
                if not drug:
                    raise APIException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        message="Drug not found"
                    )
                if not drug.is_active:
                    raise APIException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        message=f"Drug '{drug.name}' is discontinued"
                    )
                drug_name = drug.name
                unit_price = drug.unit_price

            item = PrescriptionItem(
                prescription_id=prescription.id,
                drug_id=item_data.drug_id,
                drug_name=drug_name,
                dosage=item_data.dosage,
                quantity=item_data.quantity,
                unit_price=unit_price,
                is_selected=True,
            )
            db.add(item)
        await db.flush()
        await db.refresh(prescription)

        return await PrescriptionService._to_response(db, prescription)

    @staticmethod
    async def get_pending_prescriptions_query(db: AsyncSession):
        """获取待发药处方查询对象（药师端，用于分页）"""
        query = select(Prescription).where(Prescription.status == "pending")
        query = query.order_by(Prescription.created_at.asc())
        return query

    @staticmethod
    async def list_prescriptions(db: AsyncSession, prescriptions: List[Prescription]) -> List[PrescriptionResponse]:
        """批量转换处方列表为响应模型"""
        return [await PrescriptionService._to_response(db, p) for p in prescriptions]

    @staticmethod
    async def dispense_prescription(
        db: AsyncSession,
        pharmacist_id: int,
        prescription_id: int
    ) -> Optional[PrescriptionResponse]:
        """药师发药"""
        prescription_query = select(Prescription).where(Prescription.id == prescription_id)
        prescription = (await db.execute(prescription_query)).scalar_one_or_none()

        if not prescription:
            return None

        if prescription.status == "dispensed":
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Prescription already dispensed"
            )

        items = (
            await db.execute(
                select(PrescriptionItem).where(
                    PrescriptionItem.prescription_id == prescription_id
                )
            )
        ).scalars().all()

        selected = [i for i in items if i.is_selected]
        if not selected:
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Patient declined all items in this prescription"
            )

        # 有计价药品时必须先收到药费，未付款不予配发。
        # 存量处方（unit_price 全为空）无从计费，直接放行以兼容旧数据。
        billable = any(i.unit_price is not None for i in selected)
        if billable:
            paid_bill = (
                await db.execute(
                    select(Bill).where(
                        Bill.prescription_id == prescription_id,
                        Bill.bill_type == "prescription",
                        Bill.status == "paid",
                    )
                )
            ).scalar_one_or_none()
            if not paid_bill:
                raise APIException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message="Medication fee not paid yet, cannot dispense"
                )

        stmt = update(Prescription).where(Prescription.id == prescription_id).values(status="dispensed")
        await db.execute(stmt)

        dispense_record = DispenseRecord(
            prescription_id=prescription_id,
            pharmacist_id=pharmacist_id,
            dispensed_at=datetime.now(UTC),
            status="dispensed"
        )
        db.add(dispense_record)
        await db.flush()

        prescription_query = select(Prescription).where(Prescription.id == prescription_id)
        prescription = (await db.execute(prescription_query)).scalar_one_or_none()

        return await PrescriptionService._to_response(db, prescription)


prescription_service = PrescriptionService()
