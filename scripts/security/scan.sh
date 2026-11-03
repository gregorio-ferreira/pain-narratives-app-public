#!/usr/bin/env bash
# Scan Git history and a safe export of current public files, never ignored config/data.
set -euo pipefail
cd "$(dirname "$0")/../.."
python3 scripts/security/check_publication.py
export_root=$(mktemp -d)
trap 'rm -rf "$export_root"' EXIT
python3 - "$export_root" <<'PY'
import shutil, sys
from pathlib import Path
sys.path.insert(0, 'scripts/security')
from check_publication import ROOT, public_files
for name in public_files():
    source = ROOT / name
    if source.is_file() and not source.is_symlink():
        destination = Path(sys.argv[1]) / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
PY
gitleaks git --redact --log-opts=--all --config .gitleaks.toml .
gitleaks dir --redact --config .gitleaks.toml "$export_root"
trivy fs --include-dev-deps --scanners vuln,misconfig --severity HIGH,CRITICAL --exit-code 1 "$export_root"
