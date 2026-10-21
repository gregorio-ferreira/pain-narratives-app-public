"""Build and dependency identity for persisted research runs, without secrets."""

import os
import subprocess
from importlib.metadata import PackageNotFoundError, version


def build_revision() -> str:
    revision = os.environ.get("PAIN_NARRATIVES_REVISION", "").strip()
    if revision:
        return revision
    try:
        result = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5, check=True)
        return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def runtime_versions() -> dict[str, str]:
    result = {}
    for package in ("pain-narratives", "openai", "boto3", "streamlit", "numpy", "pandas", "sqlmodel"):
        try:
            result[package] = version(package)
        except PackageNotFoundError:
            result[package] = "unknown"
    return result
