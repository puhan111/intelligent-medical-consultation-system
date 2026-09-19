from ..base import BaseSchema, BaseResponseSchema, add_padded_id
from typing import Optional, List
from pydantic import Field


class DepartmentBase(BaseSchema):
    name: str
    description: Optional[str] = None


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentUpdate(BaseSchema):
    name: Optional[str] = None
    description: Optional[str] = None


@add_padded_id()
class DepartmentResponse(BaseResponseSchema, DepartmentBase):
    padded_id: Optional[str] = None


class DepartmentFilter(BaseSchema):
    name: Optional[str] = None


class DepartmentImportRequest(BaseSchema):
    """科室 Markdown 批量导入请求，二级标题(##)分隔每个科室，标题下方为描述"""
    content: str = Field(..., min_length=1)


class DepartmentImportResult(BaseSchema):
    created: List[str] = []
    skipped: List[str] = []
