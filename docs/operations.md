# Operations

## Security checks

Install the reviewed scanner versions (Linux x86_64) in a temporary directory,
then run the same commands as CI:

```bash
python3 scripts/security/install_tools.py --dest /tmp/pain-scanners
PATH=/tmp/pain-scanners:$PATH make security
uv sync --frozen --group dev
uv run pytest
make lint
```

Gitleaks scans all locally reachable Git history and a current public-file export;
output is redacted. Trivy scans the export's lockfile and infrastructure. Ignored
private config, local virtual environments, data and publication drafts are not
copied into that export. Vulnerability checks use a current public advisory DB;
no source/config is uploaded. CI also builds/scans the runtime image and tests
Python 3.11/3.12/3.13. Security workflows run on PRs, pushes and weekly schedules.

No scanner result establishes that narratives are anonymous. Notebook outputs and
private paths are checked separately by `scripts/security/check_publication.py`.
Install pre-commit and the Gitleaks executable to get staged-secret/publication
checks locally. Gitleaks does not replace review of passwords, screenshots or
institutional identifiers. Do not broadly suppress scanner findings. Record any
necessary narrow exception with a reason and review date.

## Logical backups

RDS snapshots and automated retention complement logical dumps. Keep both. The
repository provides `deploy/backup/logical-backup.sh`, a systemd oneshot and a daily
UTC timer. They are templates and have not been installed or enabled remotely.

Before enabling them:

1. Install PostgreSQL 16 client tools (matching the server) and the AWS CLI.
2. Create a private libpq service file and passfile (both mode 600), with verified
   TLS and a DB role allowed to read all intended application/research tables.
3. Create `/etc/pain-narratives-backup.env` (mode 600) containing `PGSERVICE`,
   `PGSERVICEFILE`, `PGPASSFILE`, `BACKUP_DIRECTORY`, and `BACKUP_S3_PREFIX`.
   Passwords belong in the passfile, not commands or Git. Configure a narrowly
   scoped AWS credential source for the backup user; a role is preferred when
   available. App Bedrock tokens cannot authorize S3 backups.
4. Create a mode-700 backup directory owned by that user. Fill all placeholders in
   the oneshot unit, including its writable directory. Review S3 bucket block-public
   access, encryption and lifecycle retention independently.
5. Copy the script/units to the intended host, reload systemd, run a manual backup,
   inspect the upload and enable the timer only after a successful restore test.

The script uses a lock, a private partial file, structural archive validation and
an encrypted S3 upload. It retains seven days of local dumps after successful
uploads. Configure off-host retention independently and alert on failed/late jobs.
`Persistent=true` catches missed runs after downtime. A listing is not a restore.

## Isolated restore test

Use a dedicated disposable PostgreSQL 16 instance, never the production target.
Download a selected private dump into a mode-700 directory. Configure a separate
libpq service named `pain-restore-test`, then run on that isolated instance:

```bash
PGSERVICE=pain-restore-test pg_restore --exit-on-error --single-transaction \
  --no-owner --no-acl --dbname='service=pain-restore-test' /private/path/backup.dump
```

Use an empty database; intentionally omit `--clean`. Compare expected table counts,
constraints, application/research schemas and representative relationships. Check
that the application can read restored data using a restricted runtime role.
Document the dump timestamp, elapsed recovery time, checks and outcome privately.
Backups contain sensitive narratives and account hashes; protect their access as
carefully as the live database. Restore roles/grants separately when needed.

## Incident and runtime hygiene

Rotate an exposed provider/DB credential before attempting history cleanup.
Changing the running config requires restarting the app because settings are
cached. Discard pre-hardening logs containing narrative previews according to the
project's retention requirements. Keep Docker logs bounded and restrict journal
access. Review stale accounts, team-IP rules, backup age and scanner results.

The DB engine checks stale pooled connections and uses verified remote TLS. The
container's resource limits and read-only filesystem reduce the impact of parser
failures. Uploads are restricted to PDF/DOCX/TXT, five MiB, with a 20-MiB expanded
DOCX bound. Operator-run research scripts still need private writable data and
checkpoint directories outside the production UI container.

The paired interval-alpha bootstrap uses the exact two-coder interval formula
instead of building coincidence matrices for each resample. Regression tests
compare it with the reference Krippendorff implementation. The estimator, paired
missing-value policy and seeded bootstrap resampling remain the same. Analysis
parsers preserve zero scores and map questionnaire items by code, including when
provider responses reorder items. Rebuild private derived analysis artifacts
explicitly if earlier parser behavior affected them; no historical DB rows or
results are automatically rewritten.

Runtime-image policy: Trivy reports **all** high/critical advisories, including
ones without an available upstream fix. CI fails when a fixed package version is
available, using `scripts/security/check_image_report.py`. Unfixed distribution
advisories remain visible and require operator review; they are not marked
resolved or silently allowlisted. The weekly job rechecks them and blocks once a
fix is published. Dependency-lock and infrastructure checks remain blocking.
The runtime uses a maintained Debian 13 base, applies available package upgrades,
and removes global pip/setuptools/wheel and unused curl/libpq runtime tools. Its
healthcheck uses Python's standard library. Dependency installation remains frozen
in the builder; container runtime code does not install packages.
