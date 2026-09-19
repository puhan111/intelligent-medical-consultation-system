from ..base import BaseSchema, BaseResponseSchema, add_padded_id
from typing import Optional


class DepartmentBase(BaseSchema):
    name: str
    description: Optional[str] = None


@add_padded_id()
class DepartmentResponse(BaseResponseSchema, DepartmentBase):
    padded_id: Optional[str] = None
