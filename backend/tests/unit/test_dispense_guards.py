import asyncio
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.exceptions.http_exceptions import APIException
from app.services.backoffice.prescription import PrescriptionService


class _Result:
    def __init__(self, *, scalar=None, items=None):
        self._scalar = scalar
        self._items = items

    def scalar_one_or_none(self):
        return self._scalar

    def scalars(self):
        return self

    def all(self):
        return self._items


class _SequencedDatabaseSession:
    def __init__(self, results):
        self._results = iter(results)
        self.executed_statements = []
        self.added_objects = []
        self.flush_count = 0

    async def execute(self, statement):
        self.executed_statements.append(statement)
        return next(self._results)

    def add(self, value):
        self.added_objects.append(value)

    async def flush(self):
        self.flush_count += 1


def test_unpaid_billable_prescription_cannot_be_dispensed():
    prescription = SimpleNamespace(status="pending")
    selected_item = SimpleNamespace(is_selected=True, unit_price=Decimal("12.50"))
    db = _SequencedDatabaseSession(
        [
            _Result(scalar=prescription),
            _Result(items=[selected_item]),
            _Result(scalar=None),
        ]
    )

    with pytest.raises(APIException) as exc_info:
        asyncio.run(
            PrescriptionService.dispense_prescription(
                db=db,
                pharmacist_id=9,
                prescription_id=101,
            )
        )

    assert exc_info.value.status_code == 400
    assert "not paid" in str(exc_info.value.detail).lower()
    assert len(db.executed_statements) == 3
    assert db.added_objects == []
    assert db.flush_count == 0


def test_already_dispensed_prescription_is_rejected_before_writing_again():
    db = _SequencedDatabaseSession(
        [_Result(scalar=SimpleNamespace(status="dispensed"))]
    )

    with pytest.raises(APIException) as exc_info:
        asyncio.run(
            PrescriptionService.dispense_prescription(
                db=db,
                pharmacist_id=9,
                prescription_id=101,
            )
        )

    assert exc_info.value.status_code == 400
    assert "already dispensed" in str(exc_info.value.detail).lower()
    assert len(db.executed_statements) == 1
    assert db.added_objects == []
    assert db.flush_count == 0
