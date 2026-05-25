# Operations

This page collects reusable maintenance and hardening guidance for operators.

## Database Connections

For production-like deployments, configure SQLAlchemy with stale-connection
protection:

```python
create_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=1800,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
)
```

This avoids common long-lived Streamlit/RDS failures caused by idle TCP
connections being closed outside the application.

## Service Hardening

When running through `systemd`, prefer:

- `Restart=on-failure` instead of `Restart=always`.
- A restart burst limit to prevent crash-loop log floods.
- Memory and file descriptor limits sized for the host.
- `EnvironmentFile=-/etc/pain-narratives.env` for host-specific settings.
- Restricted writable paths for logs, checkpoints, and data directories.

The template in `deploy/pain-narratives.service` is intentionally minimal; tune
it per host.

## Generated Files

Generated outputs should stay out of git:

- `notebooks/outputs/`
- `docs/revision/data/`
- private report/package directories
- `checkpoints/`
- logs and cache directories

Use release artifacts, object storage, or private archives for vetted generated
outputs that need to be shared.

## Routine Checks

Before deployment or publication:

```bash
git status --short --ignored
git diff --check
uv run pytest
```

For live checks:

```bash
RUN_LIVE_DB_TESTS=1 PAIN_NARRATIVES_CONFIG=/secure/path/config.yaml uv run pytest -m live_db
```

## Incident Hygiene

If credentials appear in terminal output, logs, notebooks, or issue text,
rotate them. The repository ignores common private config and log paths, but
operators should still review `git status --ignored` before publishing.
