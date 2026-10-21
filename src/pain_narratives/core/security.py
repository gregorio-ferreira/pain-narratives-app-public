"""Password storage and process-wide login throttling (no user content in logs)."""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import threading
import time
from collections import OrderedDict

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

MIN_PASSWORD_LENGTH = 6
MAX_PASSWORD_LENGTH = 1024
DISABLED_PASSWORD = "!service-account"
PASSWORD_HASHER = PasswordHasher()
# Reject the previously shipped batch credential, including custom batch usernames.
LEGACY_BATCH_HASH = "11bcd9736e2eae8b27512ff28f3eba8575d42a544a43bb0003ac01bc1c6289d8"
_DUMMY_HASH = PASSWORD_HASHER.hash(secrets.token_urlsafe(32))


def validate_password(password: str) -> None:
    if not MIN_PASSWORD_LENGTH <= len(password) <= MAX_PASSWORD_LENGTH:
        raise ValueError(f"Password must contain {MIN_PASSWORD_LENGTH}–{MAX_PASSWORD_LENGTH} characters")


def hash_password(password: str) -> str:
    validate_password(password)
    return PASSWORD_HASHER.hash(password)


def login_disabled(encoded: str) -> bool:
    return encoded.startswith("!") or hmac.compare_digest(encoded, LEGACY_BATCH_HASH)


def verify_password(encoded: str, password: str) -> bool:
    if not MIN_PASSWORD_LENGTH <= len(password) <= MAX_PASSWORD_LENGTH or login_disabled(encoded):
        return False
    if re.fullmatch(r"[a-f0-9]{64}", encoded):
        # Upgrade legacy hashes only after the correct password is supplied.
        return hmac.compare_digest(encoded, hashlib.sha256(password.encode()).hexdigest())
    try:
        return PASSWORD_HASHER.verify(encoded, password)
    except (VerificationError, InvalidHashError):
        return False


def needs_rehash(encoded: str) -> bool:
    return not encoded.startswith("$argon2") or PASSWORD_HASHER.check_needs_rehash(encoded)


def session_version(encoded: str) -> str:
    return hashlib.sha256(encoded.encode()).hexdigest()


def dummy_password_check(password: str) -> None:
    verify_password(_DUMMY_HASH, password)


class LoginThrottle:
    """Bounded, shared by Streamlit sessions; failed attempts expire after five minutes."""

    def __init__(self, attempts: int = 5, window: float = 300, max_entries: int = 4096) -> None:
        self.attempts = attempts
        self.window = window
        self.max_entries = max_entries
        self._key = secrets.token_bytes(32)
        self._entries: OrderedDict[str, tuple[int, float]] = OrderedDict()
        self._lock = threading.Lock()

    def allow(self, username: str) -> bool:
        key = hmac.new(self._key, username.strip().casefold().encode(), "sha256").hexdigest()
        now = time.monotonic()
        with self._lock:
            count, start = self._entries.get(key, (0, now))
            if now - start >= self.window:
                count, start = 0, now
            if count >= self.attempts:
                return False
            self._entries[key] = (count + 1, start)
            self._entries.move_to_end(key)
            while len(self._entries) > self.max_entries:
                self._entries.popitem(last=False)
            return True

    def reset(self, username: str) -> None:
        key = hmac.new(self._key, username.strip().casefold().encode(), "sha256").hexdigest()
        with self._lock:
            self._entries.pop(key, None)


LOGIN_THROTTLE = LoginThrottle()
