# Deployment

The supported production path is Docker Compose with Caddy on the host and an
external PostgreSQL database. `docker-compose.yml` is for local development.
The nginx installers under `scripts/deploy_ec2*.sh` are retired. The systemd app
unit is an alternative for operators who deliberately run without Docker.

## Prepare a production upgrade

Back up the database before upgrading. Review these behavior changes:

- The checkout and Docker image now default to Python 3.13.16. Rebuild the image;
  `uv sync --frozen` selects the pinned interpreter for a local checkout. The
  interpreter upgrade alone requires no database schema migration. Python 3.11
  and 3.12 remain covered by CI.
- New/reset login passwords require 6–1024 characters. Successful login upgrades
  policy-compliant SHA-256 passwords to Argon2id. Existing shorter passwords must
  be reset by an administrator/CLI before login. Password storage fits the existing column.
- The old fixed batch password is rejected even before the batch utility is run.
  Running the utility locks the automation identity's password. Automation users
  retain their database ownership/admin flag but cannot log into the UI. The helper
  refuses to convert an existing human account with a non-legacy password; use a
  dedicated automation username.
- Existing browser sessions must log in again. Roles and group assignments are
  rechecked; password reset/deletion invalidates sessions. Sessions last at most
  eight hours. Five failed attempts for one username cause a five-minute wait.
  This throttle is process-local and resets on restart.
- External DB connections require verified TLS. Configure the CA before starting
  the upgraded container. This is independent of the temporary HTTP browser URL.
- New checkpoints use format version 2 and contain successful items only. Old
  checkpoints require manual review; do not silently reuse them. Failed items are
  retried as new attempts, with failed experiments excluded via their status.
- UI evaluations now reference their actual narrative. Existing rows erroneously
  linked to narrative ID 1 need a separate provenance audit; this upgrade does not
  guess how to relink historical research data.

## Private configuration

Copy `config.yaml.example` to a private host file. Inside the container, use:

```yaml
pg-prod:
  host: YOUR_RDS_ENDPOINT
  port: 5432
  database: YOUR_DATABASE
  user: YOUR_APP_USER
  password: YOUR_DATABASE_PASSWORD
  sslmode: verify-full
  sslrootcert: /config/rds-ca-bundle.pem
```

Use `openai.api_key`; the former `api_key_pain_narratives` spelling remains a
fallback. Configure Bedrock's scoped bearer token in `bedrock.api_key` when an
instance role is unavailable. Do not mount a personal AWS credential directory.
The Bedrock UI is intentionally absent; its models are available in the batch CLI.

Download the RDS CA bundle from AWS's official trust store and keep it separate
from the secrets file:

```bash
install -d -m 700 /home/ubuntu/config
curl --fail --location https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem \
  -o /home/ubuntu/config/rds-ca-bundle.pem
chmod 644 /home/ubuntu/config/rds-ca-bundle.pem
chmod 600 /home/ubuntu/config/config.yaml
```

The container uses UID/GID 1000. Ensure that UID can read the mode-600 config;
read-only bind mounts preserve host ownership. Override `PAIN_CONFIG_FILE` and
`PAIN_DB_CA_FILE` if the host paths differ. The compose file refuses to create a
missing config path as a directory.

Use a dedicated runtime DB role, not the RDS master or the local-development
Postgres superuser. Give it CONNECT, schema USAGE, and required table/sequence
operations in the application schema. Keep schema ownership/DDL and research
migration permissions in a separate operator role. Revoke public DB ingress and
use the private same-VPC endpoint, allowing 5432 only from the app security group.
These cloud/role changes require operator access; they are not applied by compose.

## Build and run

```bash
export APP_REVISION=$(git rev-parse HEAD)
export PAIN_PUBLIC_HOST=YOUR_EC2_HOSTNAME.example.com
docker compose -f deploy/docker-compose.prod.yml config --quiet
docker compose -f deploy/docker-compose.prod.yml build
docker compose -f deploy/docker-compose.prod.yml up -d
```

Build a reviewed, committed revision so the injected SHA identifies the source.
The image contains the source tree and locked dependencies, without the project
wheel; `PYTHONPATH=/app/src` supplies application imports. No config/data/history
enters the allowlisted Docker context. Runtime code is owned by root and runs as
an unprivileged user with a read-only root filesystem and bounded logs/resources.

For an existing database, do not run migrations blindly. If a reviewed migration
is required, run Alembic from an operator checkout using its private configuration:

```bash
cd src/pain_narratives/db
uv run alembic upgrade head
```

Normal tests are isolated; `uv run pytest` never discovers private runtime config
and blocks network/default database access. Live tests require both explicit
`RUN_LIVE_DB_TESTS=1` and a private config and may write data. Do not run them on a
production database.

## Temporary HTTP access

The current deployment deliberately retains HTTP. Adapt
`deploy/Caddyfile.http.example` to the real hostname and team CIDRs, and apply the
same team-IP restriction to port 80 in the EC2 security group. Keep SSH restricted
to the admin IP, 8501 bound to loopback, and 5432 restricted to the app group.
`remote_ip` assumes Caddy receives clients directly; proxy deployments need their
own trusted-proxy configuration. Close unused inbound ports.

An IP allowlist does not encrypt passwords or narratives. Prefer synthetic data
and avoid entering personal API keys in this UI while HTTP remains necessary.
The image disables telemetry, detailed client errors and content previews in logs.
CORS and XSRF protections remain enabled; HTTP does not justify disabling either.

When HTTPS becomes possible, change the Caddy site address to the domain and keep
proxying to the same loopback port. No application redesign is needed.

## Verification and recovery

```bash
docker compose -f deploy/docker-compose.prod.yml ps
docker compose -f deploy/docker-compose.prod.yml logs --tail=50 app
curl --fail http://127.0.0.1:8501/_stcore/health
```

Confirm login, group assignment, one synthetic evaluation and its saved narrative
ID. The healthcheck verifies Streamlit's HTTP endpoint, not the DB or providers.
Docker restarts a stopped process; an unhealthy status alone does not restart it.
Monitor disk space, memory, health and backup age. See `docs/operations.md` for
logical backup scheduling and an isolated restore test.

`sql/runtime_role.example.sql` provides scoped runtime grants for an existing
non-owner role. It is an operator template; review inherited/PUBLIC privileges
and role memberships before applying it. It does not provision or rotate secrets.

Questionnaire saves now commit the experiment, questionnaire, evaluation and full
request/response together. Edited narrative text resolves to its own narrative ID.
Checkpoints bind the owner, input-content hash, configuration and repetition;
use a separate checkpoint path when changing any of those inputs.
