"""Administrative CLI operations share password policy and protect generated credentials."""

import csv
import importlib.util
from pathlib import Path

import pytest


def load_management_script():
    path = Path(__file__).resolve().parents[1] / "scripts" / "manage_users.py"
    spec = importlib.util.spec_from_file_location("management_cli_for_tests", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cli_reset_uses_argon2(db):
    script = load_management_script()
    user = db.create_user("cli-user", "original-test-password")
    script.reset_password(db, user.username, "six-ok")
    assert db.authenticate_user(user.username, "six-ok")
    assert not db.authenticate_user(user.username, "original-test-password")


def test_csv_import_creates_private_separate_credentials(db, tmp_path):
    script = load_management_script()
    source = tmp_path / "participants.csv"
    source.write_text("Email,Name Surname\nresearcher@example.com,Synthetic Researcher\n")
    script.import_users_from_csv(db, str(source))
    credentials = Path(str(source) + ".credentials.csv")
    assert credentials.stat().st_mode & 0o777 == 0o600
    assert source.stat().st_mode & 0o777 == 0o600
    assert "Password" not in next(csv.reader(source.open()))
    with credentials.open() as handle:
        account = next(csv.DictReader(handle))
    assert db.authenticate_user(account["username"], account["password"])
    with pytest.raises(FileExistsError):
        script.import_users_from_csv(db, str(source))
