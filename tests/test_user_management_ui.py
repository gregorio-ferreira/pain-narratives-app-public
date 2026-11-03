"""User management uses an injected SQLite database, never runtime credentials."""

import hashlib

import pytest
from sqlmodel import select

from pain_narratives.batch.user_setup import get_or_create_batch_user
from pain_narratives.core.security import DISABLED_PASSWORD, LEGACY_BATCH_HASH, LoginThrottle
from pain_narratives.db.models_sqlmodel import User

PASSWORD = "test-only-long-password"


def test_password_hash_and_reset_invalidate_session(db):
    user = db.create_user("researcher", PASSWORD)
    assert user.hashed_password.startswith("$argon2id$")
    assert user.hashed_password != db.create_user("other", PASSWORD).hashed_password
    auth = db.authenticate_user(user.username, PASSWORD)
    assert auth and not auth["is_admin"]
    assert db.authenticate_user(user.username, "wrong") is None
    assert db.reset_user_password(user.id, "replacement-test-password")
    assert db.validate_user_session(user.id, auth["auth_version"]) is None
    assert db.authenticate_user(user.username, PASSWORD) is None
    assert db.authenticate_user(user.username, "replacement-test-password")


@pytest.mark.parametrize("password", ["six-ok", PASSWORD])
def test_legacy_hash_upgrades_only_on_success(db, password):
    with db.get_session() as session:
        user = User(username="legacy", hashed_password=hashlib.sha256(password.encode()).hexdigest())
        session.add(user)
        session.commit()
    assert db.authenticate_user("legacy", "wrong") is None
    assert db.authenticate_user("legacy", password)
    with db.get_session() as session:
        assert (
            session.exec(select(User).where(User.username == "legacy")).one().hashed_password.startswith("$argon2id$")
        )


def test_batch_identity_cannot_login_or_reset(db):
    uid = get_or_create_batch_user(db)
    with db.get_session() as session:
        assert session.get(User, uid).hashed_password == DISABLED_PASSWORD
    assert db.authenticate_user("batch_processor", PASSWORD) is None
    with pytest.raises(ValueError, match="Automation"):
        db.reset_user_password(uid, PASSWORD)
    with db.get_session() as session:
        session.add(User(username="old-custom-batch", hashed_password=LEGACY_BATCH_HASH, is_admin=True))
        session.commit()
    assert db.authenticate_user("old-custom-batch", PASSWORD) is None


def test_demotion_refresh_and_actor_authorization(db):
    admin = db.create_user("admin", PASSWORD, True)
    other = db.create_user("other", PASSWORD)
    auth = db.authenticate_user(admin.username, PASSWORD)
    db.update_user_admin_status(admin.id, False)
    assert db.validate_user_session(admin.id, auth["auth_version"])["is_admin"] is False
    with pytest.raises(PermissionError):
        db.update_user_admin_status(other.id, True, actor_id=admin.id)
    with pytest.raises(PermissionError):
        db.reset_user_password(other.id, PASSWORD, actor_id=admin.id)
    db.delete_user(admin.id)
    assert db.validate_user_session(admin.id, auth["auth_version"]) is None


def test_password_policy_enforced_in_database(db):
    with pytest.raises(ValueError, match="6–1024"):
        db.create_user("short", "short")
    with pytest.raises(ValueError, match="6–1024"):
        db.create_user("oversized", "x" * 1025)
    user = db.create_user("minimum-length", "six-ok")
    assert db.authenticate_user(user.username, "six-ok")
    with pytest.raises(ValueError, match="6–1024"):
        db.reset_user_password(user.id, "short")
    assert db.reset_user_password(user.id, "new-ok")
    assert db.authenticate_user(user.username, "new-ok")


def test_login_throttle_is_bounded_shared_and_expires(monkeypatch):
    from pain_narratives.core import security

    now = [100.0]
    monkeypatch.setattr(security.time, "monotonic", lambda: now[0])
    throttle = LoginThrottle(attempts=2, window=10, max_entries=2)
    assert throttle.allow("Alice") and throttle.allow("alice")
    assert not throttle.allow("ALICE")
    now[0] += 11
    assert throttle.allow("alice")
    throttle.allow("bob")
    throttle.allow("carol")
    assert len(throttle._entries) == 2


def test_short_legacy_password_requires_reset(db):
    with db.get_session() as session:
        session.add(User(username="weak-legacy", hashed_password=hashlib.sha256(b"short").hexdigest()))
        session.commit()
    assert db.authenticate_user("weak-legacy", "short") is None


def test_batch_setup_does_not_disable_a_human_account(db):
    human = db.create_user("human", PASSWORD, True)
    with pytest.raises(ValueError, match="dedicated automation"):
        get_or_create_batch_user(db, username=human.username)
    assert db.authenticate_user(human.username, PASSWORD)
