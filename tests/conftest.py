import os
import sys

import pytest

# Ensure src directory is on path for all tests
ROOT = os.path.dirname(os.path.dirname(__file__))
SRC_PATH = os.path.join(ROOT, "src")
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)


def pytest_configure(config):
    config.addinivalue_line("markers", "live_db: tests that require configured live database/cloud credentials")


def pytest_collection_modifyitems(config, items):
    if os.environ.get("RUN_LIVE_DB_TESTS") == "1":
        return

    skip_live = pytest.mark.skip(reason="set RUN_LIVE_DB_TESTS=1 to run live database/cloud tests")
    for item in items:
        if "live_db" in item.keywords:
            item.add_marker(skip_live)
