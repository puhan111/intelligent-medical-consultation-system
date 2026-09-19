from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.core.security import AuthBase
from app.models.admin import Admin
from app.core.config import settings
from app.exceptions.http_exceptions import APIException

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/backoffice/auth/login")


async def get_current_admin(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> Admin:
    payload = AuthBase.verify_token(token, scope="backoffice")
    if not payload:
        raise HTTPException(
            status_code=403,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    admin_id = payload.get("sub")
    admin_query = select(Admin).where(Admin.id == int(admin_id))
    result = await db.execute(admin_query)
    admin = result.scalar_one_or_none()
    if admin is None or not admin.is_active:
        raise HTTPException(status_code=403, detail="Inactive admin")
    return admin


async def get_current_doctor_id(
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
) -> int:
    """校验当前登录账号是医生角色，并返回对应的 doctor_id"""
    if current_admin.role != "doctor":
        raise APIException(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Not enough permissions"
        )

    from app.models.doctor import Doctor
    doctor_query = select(Doctor).where(Doctor.admin_id == current_admin.id)
    doctor = (await db.execute(doctor_query)).scalar_one_or_none()
    if not doctor:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Doctor profile not found"
        )
    return doctor.id


async def get_current_pharmacist(
    current_admin: Admin = Depends(get_current_admin)
) -> Admin:
    """校验当前登录账号是药师角色"""
    if current_admin.role != "pharmacist":
        raise APIException(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Not enough permissions"
        )
    return current_admin


async def get_current_cashier(
    current_admin: Admin = Depends(get_current_admin)
) -> Admin:
    """校验当前登录账号是收费员角色"""
    if current_admin.role != "cashier":
        raise APIException(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Not enough permissions"
        )
    return current_admin


async def get_current_lab(
    current_admin: Admin = Depends(get_current_admin)
) -> Admin:
    """校验当前登录账号是检验科角色"""
    if current_admin.role != "lab":
        raise APIException(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Not enough permissions"
        )
    return current_admin


async def get_current_superadmin(
    current_admin: Admin = Depends(get_current_admin)
) -> Admin:
    """校验当前登录账号是超级管理员。"""
    if current_admin.role != "superadmin":
        raise APIException(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Not enough permissions",
        )
    return current_admin
