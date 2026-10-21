#!/usr/bin/env python3
"""Reject notebook execution artifacts and private files in the publication tree."""

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRIVATE = re.compile(
    r"(^|/)(?:config\.yaml|\.yaml|\.env(?:\..*)?|secrets\.(?:yaml|toml)|\.aws|data|backups|publication|publications)(/|$)|\.(?:pem|key|dump|backup|sql\.gz|p12|pfx)$"
)


def public_files() -> list[str]:
    return (
        subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT)
        .decode()
        .split("\0")[:-1]
    )


def check() -> list[str]:
    issues = []
    for name in public_files():
        path = ROOT / name
        if not path.exists():
            continue
        if PRIVATE.search(name) and name not in {"config.yaml.example", ".env.example"}:
            issues.append(f"{name}: private path is included in publication files")
        if name.endswith(".sql") and not name.startswith(("sql/", "docker/")):
            issues.append(f"{name}: SQL exports must not be published outside reviewed SQL source directories")
        if ".ssh" in path.parts or path.name.startswith(("id_rsa", "id_ed25519")):
            issues.append(f"{name}: SSH material must remain private")
        if path.is_symlink():
            issues.append(f"{name}: symlinks are not permitted in publication exports")
        if name.endswith(".ipynb"):
            notebook = json.loads(path.read_text())
            if notebook.get("metadata", {}).get("widgets"):
                issues.append(f"{name}: widget state is embedded")
            for index, cell in enumerate(notebook.get("cells", [])):
                if cell.get("outputs") or cell.get("execution_count") is not None or cell.get("attachments"):
                    issues.append(f"{name}: cell {index} has output, execution state or attachments")
    return issues


if __name__ == "__main__":
    problems = check()
    print("\n".join(problems) if problems else "Publication checks passed")
    sys.exit(bool(problems))
