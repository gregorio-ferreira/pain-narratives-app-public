#!/usr/bin/env python3
"""Install reviewed Linux x86_64 scanners, checking fixed SHA-256 digests."""

import argparse
import hashlib
import io
import platform
import tarfile
import urllib.request
from pathlib import Path

TOOLS = {
    "gitleaks": (
        "gitleaks/gitleaks",
        "8.30.1",
        "gitleaks_8.30.1_linux_x64.tar.gz",
        "551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb",
    ),
    "trivy": (
        "aquasecurity/trivy",
        "0.76.0",
        "trivy_0.76.0_Linux-64bit.tar.gz",
        "e24b1c51293c1b15e4ba8d45bbc7891ba053f90278ec2698f3562c993e145fe7",
    ),
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", type=Path, required=True)
    args = parser.parse_args()
    if platform.system() != "Linux" or platform.machine() not in {"x86_64", "AMD64"}:
        parser.error("Use the upstream installer for your platform; these checksums are Linux x86_64")
    args.dest.mkdir(parents=True, exist_ok=True)
    for name, (repo, version, archive, checksum) in TOOLS.items():
        request = urllib.request.Request(
            f"https://github.com/{repo}/releases/download/v{version}/{archive}",
            headers={"User-Agent": "pain-narratives-security-checks"},
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = response.read()
        if hashlib.sha256(payload).hexdigest() != checksum:
            raise RuntimeError(f"Checksum mismatch for {name}; refusing to install")
        with tarfile.open(fileobj=io.BytesIO(payload)) as bundle:
            member = bundle.getmember(name)
            if not member.isfile():
                raise RuntimeError("Invalid scanner archive")
            handle = bundle.extractfile(member)
            assert handle is not None
            target = args.dest / name
            target.write_bytes(handle.read())
            target.chmod(0o755)
        print(f"Installed {name} {version} (verified SHA-256)")


if __name__ == "__main__":
    main()
