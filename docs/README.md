# Documentation Index

AINarratives is a Streamlit research app that uses LLMs to evaluate chronic-pain
patient narratives across clinical dimensions and validated questionnaires
(PCS, BPI-IS, TSK-11SV). It was first published in *Software Impacts* and is
under revision for ACM HEALTH-2026-0160.

Start with the project [`README.md`](../README.md) for installation and a feature
tour. This folder holds reference material for operators and coding assistants
who need to extend, deploy, or rerun the system.

## Topics

| File | What's in it |
|---|---|
| [`architecture.md`](architecture.md) | Layout of the codebase, key database tables, alembic state, and the narratives dataset (152 ACM baseline narratives, 40 with human ground truth). |
| [`configuration.md`](configuration.md) | `config.yaml` shape, YAML-based default prompts, translation-model settings, deprecated `user_prompts` table. |
| [`deployment.md`](deployment.md) | EC2 deploy steps, AWS Bedrock auth (IAM role / MFA profile / bearer token), `systemd` service template. |
| [`user_management.md`](user_management.md) | Admin UI for creating users, toggling admin rights, resetting passwords, deleting users, and assigning experiment groups. |
| [`revision_experiments.md`](revision_experiments.md) | Active rebuttal experiments: DeepSeek-R1 and Claude Sonnet 4.5 (with extended thinking) on the 152-narrative baseline. |
| [`improvements.md`](improvements.md) | Backlog of performance and hardening tracks (DB pooling, systemd limits, Streamlit caching, batch parallelism). |

## Generated reference data

- [`revision/narratives_inventory.csv`](revision/narratives_inventory.csv) — one
  row per non-empty narrative, with size metadata and provenance flags. The CSV
  contains no narrative text. Regenerate with
  [`scripts/dev/build_narratives_inventory.py`](../scripts/dev/build_narratives_inventory.py).

## Local-only notes

The `local/` subfolder is gitignored (see [`.gitignore`](../.gitignore)) and is
where operators keep machine-specific runbooks and handoff notes.
