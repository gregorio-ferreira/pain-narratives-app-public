# Documentation

This directory contains public, reusable documentation for AINarratives. It is
organized by topic rather than by one-off project history.

| Topic | File |
|---|---|
| Codebase layout, runtime components, database tables | [architecture.md](architecture.md) |
| Config files, environment override, OpenAI/Bedrock settings | [configuration.md](configuration.md) |
| EC2/systemd deployment and production smoke tests | [deployment.md](deployment.md) |
| Batch runs, prompt versions, providers, checkpoints | [experiments.md](experiments.md) |
| Notebooks, revision data layer, generated outputs | [analysis.md](analysis.md) |
| Operational hardening and maintenance guidance | [operations.md](operations.md) |
| Admin UI and user/group management | [user_management.md](user_management.md) |

## Generated and Private Material

Generated analysis outputs are not tracked. Recreate them from the documented
commands when needed. Private inputs such as patient data, local workbooks,
checkpoints, credentials, and operator notes must stay outside git.

`docs/local/` is intentionally ignored and can be used for machine-specific
handoff notes.

The metadata-only file [revision/narratives_inventory.csv](revision/narratives_inventory.csv)
is safe to track because it contains counts, hashes, and provenance flags, not
narrative text.
