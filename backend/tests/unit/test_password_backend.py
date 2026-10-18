import pytest

from app.models.admin import Admin
from app.models.user import User


@pytest.mark.parametrize("model,password_field", [(Admin, "password"), (User, "hashed_password")])
def test_password_backend_hashes_and_verifies_real_credentials(model, password_field):
    password = "DeploymentCheck2026!"
    hashed = model.get_password_hash(password)
    assert hashed != password
    account = model(**{password_field: hashed})
    assert account.verify_password(password)
    assert not account.verify_password("different-password")
