"""
患者端处方服务

患者可查看自己的处方与药价、按需取消勾选不想要的药、就已勾选项生成药费账单。
账单一经支付即锁定勾选，避免已付金额与实际配药不一致。
"""
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import status

from app.models.appointment import Appointment
from app.models.bill import Bill
from app.models.bill_item import BillItem
from app.models.department import Department
from app.models.doctor import Doctor
from app.models.admin import Admin
from app.models.prescription import Prescription, PrescriptionItem
from app.schemas.client.prescription import PrescriptionItemResponse, PrescriptionResponse
from app.exceptions.http_exceptions import APIException


async def _get_prescription_bill(db: AsyncSession, prescription_id: int) -> Optional[Bill]:
    """查询处方对应的药费账单"""
    return (
        await db.execute(
            select(Bill).where(
                Bill.prescription_id == prescription_id,
                Bill.bill_type == "prescription",
            )
        )
    ).scalar_one_or_none()


async def _to_response(db: AsyncSession, prescription: Prescription) -> PrescriptionResponse:
    """组装处方响应（补充医生、科室、价格合计与账单状态）"""
    items = (
        await db.execute(
            select(PrescriptionItem)
            .where(PrescriptionItem.prescription_id == prescription.id)
            .order_by(PrescriptionItem.id.asc())
        )
    ).scalars().all()

    response = PrescriptionResponse.model_validate(prescription)

    item_responses = []
    total = Decimal("0")
    for item in items:
        r = PrescriptionItemResponse.model_validate(item)
        if item.unit_price is not None:
            subtotal = Decimal(str(item.unit_price)) * item.quantity
            r.subtotal = float(subtotal)
            if item.is_selected:
                total += subtotal
        item_responses.append(r)

    response.items = item_responses
    response.selected_total = float(total)

    # 医生与科室
    doctor = (
        await db.execute(select(Doctor).where(Doctor.id == prescription.doctor_id))
    ).scalar_one_or_none()
    if doctor:
        admin = (
            await db.execute(select(Admin).where(Admin.id == doctor.admin_id))
        ).scalar_one_or_none()
        if admin:
            response.doctor_name = (
                f"{admin.last_name}{admin.first_name}"
                if admin.last_name and admin.first_name
                else admin.email
            )
        department = (
            await db.execute(select(Department).where(Department.id == doctor.department_id))
        ).scalar_one_or_none()
        if department:
            response.department_name = department.name

    # 账单状态决定能否继续改勾选
    bill = await _get_prescription_bill(db, prescription.id)
    if bill:
        response.bill_id = bill.id
        response.bill_status = bill.status
        response.can_modify_selection = bill.status != "paid"
    else:
        response.bill_status = "none"
        response.can_modify_selection = True

    return response


async def get_my_prescriptions_query(db: AsyncSession, patient_id: int):
    """患者的处方列表查询对象（通过预约关联，用于分页）"""
    return (
        select(Prescription)
        .join(Appointment, Appointment.id == Prescription.appointment_id)
        .where(Appointment.patient_id == patient_id)
        .order_by(Prescription.created_at.desc())
    )


async def list_prescriptions(
    db: AsyncSession, prescriptions: List[Prescription]
) -> List[PrescriptionResponse]:
    """批量转换处方列表"""
    return [await _to_response(db, p) for p in prescriptions]


async def _get_owned_prescription(
    db: AsyncSession, patient_id: int, prescription_id: int
) -> Prescription:
    """取患者本人的处方，不存在或不属于本人则 404"""
    prescription = (
        await db.execute(
            select(Prescription)
            .join(Appointment, Appointment.id == Prescription.appointment_id)
            .where(
                Prescription.id == prescription_id,
                Appointment.patient_id == patient_id,
            )
        )
    ).scalar_one_or_none()

    if not prescription:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Prescription not found",
        )
    return prescription


async def get_prescription(
    db: AsyncSession, patient_id: int, prescription_id: int
) -> PrescriptionResponse:
    """获取处方详情"""
    prescription = await _get_owned_prescription(db, patient_id, prescription_id)
    return await _to_response(db, prescription)


async def update_item_selection(
    db: AsyncSession,
    patient_id: int,
    prescription_id: int,
    item_id: int,
    is_selected: bool,
) -> PrescriptionResponse:
    """
    勾选或取消勾选某项药品

    取消勾选视为拒药，药师不再配发该项。药费已支付后禁止修改，
    否则已付金额与实际配药不一致。
    """
    prescription = await _get_owned_prescription(db, patient_id, prescription_id)

    if prescription.status == "dispensed":
        raise APIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Prescription already dispensed, cannot modify selection",
        )

    bill = await _get_prescription_bill(db, prescription_id)
    if bill and bill.status == "paid":
        raise APIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Medication fee already paid, cannot modify selection",
        )

    item = (
        await db.execute(
            select(PrescriptionItem).where(
                PrescriptionItem.id == item_id,
                PrescriptionItem.prescription_id == prescription_id,
            )
        )
    ).scalar_one_or_none()
    if not item:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Prescription item not found",
        )

    await db.execute(
        update(PrescriptionItem)
        .where(PrescriptionItem.id == item_id)
        .values(is_selected=is_selected)
    )

    # 勾选变了金额就变了，未支付的旧账单连同明细一并作废，待患者重新生成
    if bill and bill.status == "unpaid":
        await db.execute(delete(BillItem).where(BillItem.bill_id == bill.id))
        await db.execute(delete(Bill).where(Bill.id == bill.id))

    await db.flush()
    return await _to_response(db, prescription)


async def create_bill(
    db: AsyncSession, patient_id: int, prescription_id: int
) -> PrescriptionResponse:
    """
    按已勾选的药品生成药费账单

    生成后走既有的账单支付流程（POST /bills/{id}/pay）。
    """
    prescription = await _get_owned_prescription(db, patient_id, prescription_id)

    existing = await _get_prescription_bill(db, prescription_id)
    if existing:
        if existing.status == "paid":
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Medication fee already paid",
            )
        # 未支付账单直接复用，避免重复下单
        return await _to_response(db, prescription)

    items = (
        await db.execute(
            select(PrescriptionItem).where(
                PrescriptionItem.prescription_id == prescription_id,
                PrescriptionItem.is_selected.is_(True),
            )
        )
    ).scalars().all()

    if not items:
        raise APIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="No item selected, nothing to pay",
        )

    priced = [i for i in items if i.unit_price is not None]
    if not priced:
        raise APIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Selected items have no price, please contact the counter",
        )

    total = sum(
        (Decimal(str(i.unit_price)) * i.quantity for i in priced), Decimal("0")
    )

    bill = Bill(
        patient_id=patient_id,
        appointment_id=prescription.appointment_id,
        prescription_id=prescription_id,
        bill_type="prescription",
        amount=total,
        status="unpaid",
    )
    db.add(bill)
    await db.flush()

    for i in priced:
        unit_price = Decimal(str(i.unit_price))
        db.add(BillItem(
            bill_id=bill.id,
            item_type="medication",
            name=i.drug_name,
            unit_price=unit_price,
            quantity=i.quantity,
            subtotal=unit_price * i.quantity,
        ))

    await db.flush()
    return await _to_response(db, prescription)
