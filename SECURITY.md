# Security Policy

## Reporting a Vulnerability

If you believe you have found a security vulnerability in AINarratives, please
report it privately rather than opening a public GitHub issue. We will work
with you to verify the issue and ship a fix.

**Please do not** disclose the vulnerability publicly until it has been
addressed.

### How to report

- Open a **private GitHub Security Advisory** on this repository:
  <https://github.com/gregorio-ferreira/pain-narratives-app-public/security/advisories/new>
- Or email the repository owner (see the `git log` author for the most recent
  releases for the active maintainer's address).

Please include:

- A description of the vulnerability and its potential impact
- Steps to reproduce, ideally with a minimal example
- Any proposed remediation, if you have one
- Whether you would like to be credited in the resulting advisory

We will acknowledge your report within five working days and aim to provide
a remediation timeline within ten.

## Sensitive data in this repository

AINarratives is research software that processes clinical pain narratives,
which are sensitive personal data. The repository structure reflects this:

- `data/`, `config.yaml`, `.streamlit/config.toml`, `publications/`, and
  `*.csv` (with the one safe exception `docs/revision/narratives_inventory.csv`,
  which contains metadata-only counts and hashes) are **gitignored** and must
  never be committed.
- `config.yaml.example` is the only file in the repo that describes the shape
  of the credentials; it contains placeholder values.
- Database migrations are additive where possible; the active head and
  rollback notes are documented in `docs/consolidation/CONSOLIDATION_PLAN.md`.

If you find any committed file that contains a real credential, API key,
patient identifier, or other piece of sensitive information, **report it the
same way you would a vulnerability** — it should be treated and remediated as
one.

## Supported versions

This is research-grade software released alongside an academic publication.
Security fixes are applied to the `main` branch as needed; we do not maintain
parallel stable / LTS branches.
