"""Tests for ``DatabaseManager`` user authentication and management.

All tests are tagged ``live_db`` and so only run when
``RUN_LIVE_DB_TESTS=1`` is set (see ``tests/conftest.py``). They use a
uuid-suffixed throwaway username and clean up after themselves.

What this exercises:
- ``create_user`` whitespace stripping and case-insensitive duplicate refusal.
- ``authenticate_user`` case-insensitive lookup, whitespace tolerance, wrong
  password, nonexistent user.
- ``reset_user_password`` round-trip via the existing ``user_id`` based API.
- ``delete_user`` invalidates a previously valid login.
"""

from __future__ import annotations

import uuid
from typing import Iterator

import pytest

from pain_narratives.core.database import DatabaseManager

pytestmark = pytest.mark.live_db


def _unique_username() -> str:
    return f"AuthTest_{uuid.uuid4().hex[:8]}"


@pytest.fixture()
def db() -> DatabaseManager:
    return DatabaseManager()


@pytest.fixture()
def throwaway_user(db: DatabaseManager) -> Iterator[tuple[int, str, str]]:
    """Create a unique user; yield ``(user_id, username, password)``; clean up after."""
    username = _unique_username()
    password = "Test-Password-123"
    user = db.create_user(username=username, password=password, is_admin=False)
    try:
        yield user.id, username, password
    finally:
        db.delete_user(user.id)


# ---------------------------------------------------------------------------
# create_user
# ---------------------------------------------------------------------------


def test_create_user_strips_whitespace(db: DatabaseManager) -> None:
    base = _unique_username()
    user = db.create_user(username=f"  {base}  ", password="pw")
    try:
        assert user.username == base, "leading/trailing whitespace should be stripped"
    finally:
        db.delete_user(user.id)


def test_create_user_rejects_empty(db: DatabaseManager) -> None:
    with pytest.raises(ValueError):
        db.create_user(username="   ", password="pw")
    with pytest.raises(ValueError):
        db.create_user(username="", password="pw")


def test_create_user_rejects_case_insensitive_duplicate(db: DatabaseManager) -> None:
    base = _unique_username()
    first = db.create_user(username=base, password="pw")
    try:
        with pytest.raises(ValueError):
            db.create_user(username=base.lower(), password="pw")
        with pytest.raises(ValueError):
            db.create_user(username=base.upper(), password="pw")
    finally:
        db.delete_user(first.id)


# ---------------------------------------------------------------------------
# authenticate_user
# ---------------------------------------------------------------------------


def test_authenticate_user_exact_match(throwaway_user) -> None:
    db = DatabaseManager()
    user_id, username, password = throwaway_user
    result = db.authenticate_user(username=username, password=password)
    assert result is not None
    assert result["id"] == user_id
    assert result["username"] == username


def test_authenticate_user_case_insensitive_username(throwaway_user) -> None:
    db = DatabaseManager()
    _, username, password = throwaway_user
    assert db.authenticate_user(username=username.upper(), password=password) is not None
    assert db.authenticate_user(username=username.lower(), password=password) is not None


def test_authenticate_user_strips_username_whitespace(throwaway_user) -> None:
    db = DatabaseManager()
    _, username, password = throwaway_user
    assert db.authenticate_user(username=f"  {username}  ", password=password) is not None


def test_authenticate_user_wrong_password_returns_none(throwaway_user) -> None:
    db = DatabaseManager()
    _, username, _ = throwaway_user
    assert db.authenticate_user(username=username, password="wrong-password") is None


def test_authenticate_user_nonexistent_returns_none(db: DatabaseManager) -> None:
    assert db.authenticate_user(username=f"nobody_{uuid.uuid4().hex}", password="pw") is None


def test_authenticate_user_empty_username_returns_none(db: DatabaseManager) -> None:
    assert db.authenticate_user(username="", password="pw") is None
    assert db.authenticate_user(username="   ", password="pw") is None


# ---------------------------------------------------------------------------
# reset_user_password / delete_user
# ---------------------------------------------------------------------------


def test_reset_user_password_roundtrip(throwaway_user) -> None:
    db = DatabaseManager()
    user_id, username, old_password = throwaway_user
    new_password = "Different-Password-456"
    assert db.reset_user_password(user_id=user_id, new_password=new_password) is True
    # Old credentials no longer authenticate.
    assert db.authenticate_user(username=username, password=old_password) is None
    # New credentials do.
    result = db.authenticate_user(username=username, password=new_password)
    assert result is not None
    assert result["id"] == user_id


def test_delete_user_invalidates_login(db: DatabaseManager) -> None:
    username = _unique_username()
    password = "pw-to-delete"
    user = db.create_user(username=username, password=password)
    # Sanity: works before delete.
    assert db.authenticate_user(username=username, password=password) is not None
    assert db.delete_user(user.id) is True
    # No longer authenticates.
    assert db.authenticate_user(username=username, password=password) is None
