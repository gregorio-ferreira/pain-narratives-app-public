#!/usr/bin/env python3
"""Report all high/critical image findings; fail on findings with an available fix."""

import json
import sys
from pathlib import Path


def check_report(path: Path) -> int:
    report = json.loads(path.read_text())
    if report.get("ArtifactType") != "container_image" or not report.get("Results"):
        raise ValueError("Expected a completed Trivy container-image report")
    fixable = 0
    unfixed = 0
    for result in report.get("Results", []):
        for issue in result.get("Vulnerabilities", []):
            if issue.get("Severity") not in {"HIGH", "CRITICAL"}:
                continue
            fixed = issue.get("FixedVersion")
            fixable += bool(fixed)
            unfixed += not bool(fixed)
            print(
                f"{issue['Severity']} {issue['VulnerabilityID']} {issue['PkgName']} "
                f"{issue['InstalledVersion']} -> {fixed or 'no upstream fix recorded'}"
            )
    print(f"Runtime image: {fixable} fixable and {unfixed} upstream-unfixed high/critical findings")
    # Do not hide unfixed findings or pretend they are resolved. Weekly CI rescans
    # begin blocking them when the distribution publishes a fixed version.
    return int(fixable > 0)


if __name__ == "__main__":
    sys.exit(check_report(Path(sys.argv[1])))
