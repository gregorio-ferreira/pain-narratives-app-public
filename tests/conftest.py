"""Tests never discover private config or connect to a network by default."""

import os
import socket
import sys
from pathlib import Path

import pytest

# Small scientific unit tests should not spawn host-sized BLAS thread pools.
for _thread_variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_thread_variable] = "1"

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# Set before test collection: imports must not load the checkout's real config.
_LIVE = os.environ.get("RUN_LIVE_DB_TESTS") == "1"
if not _LIVE:
    os.environ["PAIN_NARRATIVES_CONFIG"] = str(ROOT / "tests" / "offline-config.yaml")
    os.environ["AWS_EC2_METADATA_DISABLED"] = "true"


def pytest_collection_modifyitems(config, items):
    if not _LIVE:
        for item in items:
            if "live_db" in item.keywords:
                item.add_marker(pytest.mark.skip(reason="live integrations require RUN_LIVE_DB_TESTS=1"))


@pytest.fixture(autouse=True)
def offline_only(request, monkeypatch):
    if "live_db" in request.keywords:
        return
    import psycopg2

    from pain_narratives.config import settings
    from pain_narratives.core import database, security

    def denied(*args, **kwargs):
        raise AssertionError("Network/default database access is prohibited in unit tests")

    monkeypatch.setenv("PAIN_NARRATIVES_CONFIG", str(ROOT / "tests" / "offline-config.yaml"))
    monkeypatch.setattr(settings, "_config_manager", None)
    monkeypatch.setattr(database, "_db_manager", None)
    monkeypatch.setattr(security, "LOGIN_THROTTLE", security.LoginThrottle())
    monkeypatch.setattr(database, "LOGIN_THROTTLE", security.LOGIN_THROTTLE)
    monkeypatch.setattr(database.DatabaseManager, "_create_engine", denied)
    monkeypatch.setattr(psycopg2, "connect", denied)
    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket.socket, "connect_ex", denied)


@pytest.fixture
def db():
    from sqlalchemy.pool import StaticPool
    from sqlmodel import SQLModel, create_engine

    from pain_narratives.core.database import DatabaseManager
    from pain_narratives.db.base import SCHEMA_NAME

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        execution_options={"schema_translate_map": {SCHEMA_NAME: None}},
    )
    SQLModel.metadata.create_all(engine)
    yield DatabaseManager(engine)
    engine.dispose()
