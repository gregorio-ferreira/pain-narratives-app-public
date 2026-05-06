# Hand-off to Claude Code — Continue the Consolidation

This document is the operational follow-up to `CONSOLIDATION_PLAN.md`. It describes **exactly what state the public repo is in right now** (after a Cowork session did the file moves) and **what is left for you to do**, with copy-pasteable commands.

The full plan with rationale and risk register is in `CONSOLIDATION_PLAN.md` in the same folder. Read that first if you need context. This file assumes you've read it.

---

## Where things stand right now

**Repo on disk:** `~/mines/pain-narratives-app-public` (path may differ on your machine — adjust accordingly).

**Branch:** `chore/consolidate-from-private`. It was created off `main` at commit `078385e`. The tip is **still** `078385e` — **no commits have been made yet** on this branch.

**Tags created:** `pre-consolidation-public` (on public@078385e) and `pre-consolidation-private` (on private@0fe255f). Both are local-only; you'll want to push them.

**Working tree:** 41 files staged for commit (27 modified, 14 untracked). All file moves and content reconciliations from §2 / §3 / §4 of the plan have been done. **None of them are committed yet** — the Cowork sandbox can't write to `.git/`, so commits were left for you.

**What was NOT done in this session** (waiting for you):

1. The git commits themselves (all the work is in the working tree, ready to stage)
2. §1.1 — pg_dump backup
3. §1.2 — record current alembic head
4. §5 — alembic upgrade head + optional backfill
5. §5.4 — ACM schema reconciliation decision
6. §6 — verification (make check, make test, app smoke, batch dry-run)
7. §7 — push branch, open PR
8. §8 — archive private repo

---

## Inventory of working-tree changes

### Modified (27 files — content forward-ported from private)

```
.gitignore                                                  — restructured: notebooks/, sql/ no longer ignored;
                                                              .streamlit/config.toml added; docs/_build/, notebooks/outputs/ added
README.md                                                   — only 2 small terminology tweaks at top, public's
                                                              structure & content kept (it was strictly more current)
docs/EDIT_EXPERIMENT_GROUPS_GUIDE.md                        — forward-ported from private
docs/PROMPTS_MIGRATION_SUMMARY.md                           — forward-ported from private
docs/TRANSLATION_MODEL_CONFIG.md                            — forward-ported from private
docs/conf.py                                                — forward-ported from private
scripts/debug_translation.py                                — forward-ported
scripts/deploy_ec2.sh                                       — forward-ported (no hostname leak)
scripts/deploy_ec2_fixed.sh                                 — forward-ported (no hostname leak)
scripts/dev/build_docs.py                                   — forward-ported
scripts/fix_css_error.sh                                    — forward-ported AND sanitized: EC2 hostname
                                                              ec2-63-176-147-227.eu-central-1.compute.amazonaws.com
                                                              replaced with YOUR_DEPLOYMENT_DOMAIN.example.com
scripts/manage_users.py                                     — forward-ported
scripts/register_user.py                                    — forward-ported
scripts/register_user_batch.py                              — forward-ported
scripts/run_app.py                                          — forward-ported
scripts/setup/complete_setup.py                             — forward-ported
scripts/setup/init_database.py                              — forward-ported
scripts/setup/init_uv_env.ps1                               — forward-ported
scripts/user_demo.py                                        — forward-ported
src/pain_narratives/__init__.py                             — forward-ported
src/pain_narratives/config/default_prompts.yaml             — forward-ported
src/pain_narratives/config/settings.py                      — language handling refactor
src/pain_narratives/locales/en.yml                          — terminology + i18n polish
src/pain_narratives/locales/es.yml                          — terminology + i18n polish
src/pain_narratives/ui/app.py                               — UI updates (terminology, evaluation, questionnaire)
src/pain_narratives/ui/components/evaluation_display.py     — UI updates
src/pain_narratives/ui/components/questionnaire.py          — UI updates
```

### Untracked / new (14 paths)

```
src/pain_narratives/db/models_acm_202512.py                 — ACM 202512 analysis schema models (571 lines)

notebooks/                                                  — 6 publication notebooks, outputs cleared,
                                                              local /home/gferreir paths replaced with ./
notebooks/01_pain_narratives_mapping_description_author_demographics.ipynb
notebooks/02_patient_demographics_for_publication.ipynb
notebooks/03_expert_feedback_for_publication.ipynb
notebooks/04_batch_repetitions_data.ipynb
notebooks/05_real_vs_synthetic.ipynb
notebooks/06_analyses_consolidation.ipynb

scripts/consolidate_publication_tables.py                   — publication CSV → Excel
scripts/run_all_notebooks.sh                                — notebook runner; NOTEBOOKS array updated
                                                              to the new 6-notebook set
scripts/run_batch_evaluation.py                             — batch evaluation pipeline
scripts/tokens_count.py                                     — token estimator

scripts/dev/test_gpt5_compatibility.py                      — moved from scripts/ (was top-level CLI utility)
scripts/dev/test_multilingual_display.py                    — moved from scripts/
scripts/dev/test_multilingual_functionality.py              — moved from scripts/
scripts/dev/test_translation_comprehensive.py               — moved from scripts/
scripts/dev/test_translation_config.py                      — moved from scripts/
scripts/dev/test_translation_service.py                     — moved from scripts/

sql/                                                        — dev/debug queries (temp.sql excluded)
sql/batch_progress.sql
sql/debug_queries.sql
sql/experts_ui_master_dimension_evaluation.sql
sql/experts_ui_master_questionnaires.sql
sql/setup_user_prompts.sql
sql/verify_user_prompts.sql

.streamlit/config.toml.example                              — sanitized: EC2 hostname replaced
```

### What was NOT moved (per the plan / your decisions)

- `publications/` (you said keep private)
- `.streamlit/config.toml` (live config; only the sanitized `*.example` is in the public repo, and `.gitignore` blocks the live one)
- `sql/temp.sql` (5-line scratchpad)
- `docs/plan_technical_paper.md` (paper is published; planning doc no longer relevant)
- `docs/public_repo_license.md` (superseded by `LICENSE` and `NOTICE` in public)
- `.DS_Store` files (gitignored)

### Manual decisions made

- **README.md merge:** Public's README was strictly more current (Docker quick start, post-dedup narrative model fields, GPT-4o references, current config schema). Only 2 terminology refinements were grafted from private (line 3 "evaluating chronic pain patient narratives" and line 9 "AINarratives is designed").
- **Makefile merge:** Public was strictly ahead — it has `experiments`, `run-notebooks`, `publication`, `docs` targets that private lacks; private's only unique change was the kernel name (`ainarratives`), which is inferior to public's `pain-narratives`. **Kept public's Makefile unchanged.**
- **pyproject.toml:** Public's branding ("AINarratives Research Team") and broader keyword (`chronic-pain`) preferred over private's ("Pain Narratives Research Team", `fibromyalgia`). Kept public's.
- **.github/copilot-instructions.md:** Public's current defaults (`temperature=1.0, max_tokens=8000`) preferred. Kept public's.
- **.gitignore:** Removed the lines that ignored `notebooks/` and `sql/` (which would have silently blocked the migrated content from being added). Added `.streamlit/config.toml`, `notebooks/outputs/`, `docs/_build/`. Kept `publications/` ignored.
- **Stale NOTEBOOKS array** in `scripts/run_all_notebooks.sh` was updated from the old 14-notebook set (which no longer exists) to the new 6-notebook publication set.
- **EC2 hostname sanitization** in `scripts/fix_css_error.sh`. Note: the same hostname is **already in public git history** from the original Apr 27 import — if you care, run `git filter-repo --replace-text` to scrub history before publishing the consolidation. That's a separate cleanup task from this plan.

---

## Phase A — Take the working tree and turn it into a sequence of commits

Run from inside the public repo. The order below maps to the plan's §2/§3/§4 sections so each commit is reviewable.

```bash
cd ~/mines/pain-narratives-app-public

# Sanity check: confirm you're on the right branch with the expected diff
git status --short
git branch --show-current   # expect: chore/consolidate-from-private
git log --oneline -1        # expect: 078385e ... (no consolidation commits yet)
```

### A.1 — Group A: language + locale + config refactor

```bash
git add \
  src/pain_narratives/__init__.py \
  src/pain_narratives/config/settings.py \
  src/pain_narratives/config/default_prompts.yaml \
  src/pain_narratives/locales/en.yml \
  src/pain_narratives/locales/es.yml

git commit -m "feat: forward-port language handling and locale updates from private repo

Brings the public repo up to date with private commits 'feat: improved
language handling' and 'feat: updated terminology'. Includes:

- src/pain_narratives/__init__.py
- src/pain_narratives/config/settings.py (language handling refactor)
- src/pain_narratives/config/default_prompts.yaml (prompt tweaks)
- src/pain_narratives/locales/{en,es}.yml (terminology + i18n polish)

Part of the consolidate-from-private migration."
```

### A.2 — Group B: UI changes

```bash
git add \
  src/pain_narratives/ui/app.py \
  src/pain_narratives/ui/components/evaluation_display.py \
  src/pain_narratives/ui/components/questionnaire.py

git commit -m "feat: forward-port UI updates from private

Updates Streamlit UI: terminology refinements, evaluation display tweaks,
and questionnaire component improvements. Roughly +70/-12 lines on app.py.
Part of the consolidate-from-private migration."
```

### A.3 — ACM 202512 analysis schema models

```bash
git add src/pain_narratives/db/models_acm_202512.py

git commit -m "feat: add ACM 202512 analysis schema models

Adds SQLModel definitions for the pain_narratives_acm_202512 schema used
by the publication notebooks. Tables cover:
- Real patient demographics, PCS, BPI, TSK, and master data
- Expert users and their feedback (dimension evaluation, questionnaire)
- LLM synthetic results (dimension evaluation, PCS, BPI, TSK)

These models are not under alembic; they are used read-mostly by notebooks/.
The corresponding tables already exist in production from the ACM run."
```

### A.4 — Drifted scripts (incl. EC2 hostname sanitization)

```bash
git add \
  scripts/debug_translation.py \
  scripts/deploy_ec2.sh \
  scripts/deploy_ec2_fixed.sh \
  scripts/dev/build_docs.py \
  scripts/fix_css_error.sh \
  scripts/manage_users.py \
  scripts/register_user.py \
  scripts/register_user_batch.py \
  scripts/run_app.py \
  scripts/setup/complete_setup.py \
  scripts/setup/init_database.py \
  scripts/setup/init_uv_env.ps1 \
  scripts/user_demo.py

git commit -m "chore: forward-port drifted scripts (deploy, user mgmt, setup, dev tools)

Forward-ports 13 scripts that drifted ahead in the private repo. Also
sanitizes scripts/fix_css_error.sh: replaces a hardcoded EC2 hostname with
a placeholder 'YOUR_DEPLOYMENT_DOMAIN.example.com'. (Note: the original
hostname is still present in earlier git history from the Apr 27 import.)"
```

### A.5 — Drifted documentation

```bash
git add \
  docs/EDIT_EXPERIMENT_GROUPS_GUIDE.md \
  docs/PROMPTS_MIGRATION_SUMMARY.md \
  docs/TRANSLATION_MODEL_CONFIG.md \
  docs/conf.py

git commit -m "docs: forward-port drifted documentation from private repo"
```

### A.6 — README terminology refinements

```bash
git add README.md
git commit -m "docs: refine README terminology

- 'evaluating pain narratives from chronic pain patients' →
  'evaluating chronic pain patient narratives'
- 'The AINarratives project is designed' → 'AINarratives is designed'

Minimal merge from private; public's README structure (Docker quick start,
post-dedup narrative model, current config schema) was strictly preferred."
```

### A.7 — .gitignore restructure

```bash
git add .gitignore
git commit -m "chore: restructure .gitignore for migrated content

- Stop ignoring notebooks/ and sql/ (the publication notebooks and dev
  queries are now first-class content in this repo).
- Ignore notebooks/outputs/ (notebook execution artifacts).
- Ignore .streamlit/config.toml (operator-specific live config).
- Ignore docs/_build/ (Sphinx build output).
- Continue ignoring publications/ per the consolidation decision."
```

### A.8 — Publication pipeline scripts (resolves the dangling Makefile targets)

```bash
git add \
  scripts/run_batch_evaluation.py \
  scripts/consolidate_publication_tables.py \
  scripts/run_all_notebooks.sh \
  scripts/tokens_count.py

git commit -m "feat: add publication pipeline scripts

- run_batch_evaluation.py: batch processing of narratives through OpenAI
- consolidate_publication_tables.py: CSV outputs → Excel workbook
- run_all_notebooks.sh: orchestrates the 6 publication notebooks
  (NOTEBOOKS array updated to match notebooks/ contents)
- tokens_count.py: token-count estimator for narratives

Resolves the dangling Makefile targets (experiments, run-notebooks,
consolidate-tables, publication) that referenced these scripts."
```

### A.9 — Dev/translation utilities → scripts/dev/

```bash
git add \
  scripts/dev/test_gpt5_compatibility.py \
  scripts/dev/test_multilingual_display.py \
  scripts/dev/test_multilingual_functionality.py \
  scripts/dev/test_translation_comprehensive.py \
  scripts/dev/test_translation_config.py \
  scripts/dev/test_translation_service.py

git commit -m "chore: move translation/multilingual diagnostics to scripts/dev/

These are CLI utilities, not pytest tests. Moving them out of scripts/
top level keeps the surface area clean."
```

### A.10 — SQL dev/debug queries

```bash
git add sql/

git commit -m "chore: import SQL dev/debug queries from private repo

Imports 6 SQL files used for development, batch monitoring, and verifying
expert UI dimensions. (sql/temp.sql was excluded — 5-line scratchpad.)"
```

### A.11 — Sanitized Streamlit config example

```bash
git add .streamlit/config.toml.example

git commit -m "feat: add Streamlit config template

Sanitized version of the operational .streamlit/config.toml.
The hardcoded EC2 hostname is replaced with a placeholder; the live
config is gitignored so operators don't accidentally leak deployment URLs."
```

### A.12 — Notebooks (last so the diff is large but isolated)

```bash
git add notebooks/

git commit -m "feat: migrate publication analysis notebooks

Brings the 6 Software Impacts publication notebooks from the private repo:
  01_pain_narratives_mapping_description_author_demographics.ipynb
  02_patient_demographics_for_publication.ipynb
  03_expert_feedback_for_publication.ipynb
  04_batch_repetitions_data.ipynb
  05_real_vs_synthetic.ipynb
  06_analyses_consolidation.ipynb

All cell outputs cleared (109 outputs total). Hardcoded local paths of
the form /home/<user>/... replaced with relative './' so the notebooks
are portable across collaborators."
```

After all 12 commits:

```bash
git log --oneline pre-consolidation-public..HEAD
# Expect 12 commits.
git status --short        # Expect: empty.
```

---

## Phase B — Database backup & alembic state recording (plan §1.1, §1.2)

Do this **before** running the migration in Phase C.

```bash
# Adjust host/user/db to your prod values
pg_dump -Fc -d pain_narratives -h <host> -U pain_narratives \
  > ~/backups/pain_narratives_pre_consolidation_$(date +%Y%m%d_%H%M).dump

# Record the current alembic head — paste the output into the PR description
uv run alembic current
# Expected: 1a2b3c4d5e6f (head of the private repo's alembic chain)
```

If `alembic current` shows something else, **stop** and inspect — the consolidation plan assumes you're at `1a2b3c4d5e6f`.

---

## Phase C — Apply the dedup migration (plan §5)

This is the only schema change to your DB. It is **purely additive** (3 new columns on `narratives`, all nullable).

```bash
# Make sure you're on the working branch with all 12 commits
git status --short
git log --oneline -1

# Pre-flight
uv run alembic current        # expected: 1a2b3c4d5e6f
uv run alembic heads          # expected: 0000000dedup
uv run alembic history --verbose | head -40

# Apply
uv run alembic upgrade head
uv run alembic current        # expected after: 0000000dedup
```

### Optional backfill (only if your notebooks need non-null values)

```sql
-- run via psql against the prod DB
UPDATE pain_narratives_app.narratives
SET narrative_hash = encode(digest(narrative_text, 'sha256'), 'hex'),
    word_count     = array_length(regexp_split_to_array(narrative_text, '\s+'), 1),
    char_count     = char_length(narrative_text)
WHERE narrative_hash IS NULL;
```

(Requires the `pgcrypto` extension. If `digest()` errors, run `CREATE EXTENSION pgcrypto;` first.)

### ACM analysis schema (plan §5.4) — decide

If `pain_narratives_acm_202512` schema and tables already exist in your prod DB (they should, since you ran the ACM analyses), **do nothing here**. The new `models_acm_202512.py` module just gives the notebooks SQLModel typing; it doesn't create or modify anything on its own.

If you want this schema under alembic going forward (recommended for long-term hygiene), generate a single autogen revision **after** importing the model module in `alembic/env.py`:

```bash
# In src/pain_narratives/db/alembic/env.py, add:
#     from pain_narratives.db import models_acm_202512  # noqa
# (just the import — its presence in the registry is enough)

uv run alembic revision --autogenerate -m "Add ACM 202512 analysis schema"
# REVIEW the generated file. It should only CREATE TABLE in the
# pain_narratives_acm_202512 schema, never DROP anything in pain_narratives_app.

# If prod tables already match exactly:
uv run alembic stamp <new_revision>      # mark as applied without running DDL

# If prod doesn't have the tables yet:
uv run alembic upgrade head
```

---

## Phase D — Verification (plan §6)

```bash
# Static checks
make check         # format + lint + typecheck — expect green

# Tests
make test          # pytest — expect green

# App smoke (visual)
make app
# Open http://localhost:8501 and click through:
#   - language toggle (en/es)
#   - terminology shows updated text
#   - evaluation dimensions render
#   - questionnaire feedback loads
#   - expert UI loads experiments
```

### One-notebook smoke (cheapest)

```bash
uv run jupyter nbconvert --to notebook --execute \
  notebooks/02_patient_demographics_for_publication.ipynb \
  --output notebooks/_smoke_test_02.ipynb
# If green, delete the smoke output:
rm notebooks/_smoke_test_02.ipynb
```

### Batch evaluation dry-run (no tokens spent)

```bash
uv run python scripts/run_batch_evaluation.py --input data/narratives.xlsx --dry-run
```

---

## Phase E — Push & open PR (plan §7)

```bash
git push --tags                                       # pushes pre-consolidation-public/-private tags
git push -u origin chore/consolidate-from-private

gh pr create --title "Consolidate private repo into public (close the fork gap)" \
  --body "$(cat <<'EOF'
## Summary

Forward-ports 107 commits of application work from the now-archived
private repo `gregorio-ferreira/pain-narratives-app` into this public
repo, so all future work happens here.

## What changed

- Language handling refactor + locales/terminology updates
- UI: app.py, evaluation_display.py, questionnaire.py
- New ACM 202512 analysis schema models (read-mostly, used by notebooks)
- 13 drifted scripts forward-ported; EC2 hostname sanitized in fix_css_error.sh
- 4 docs updates
- README: 2 terminology refinements (rest of public's README kept — strictly
  more current)
- .gitignore restructured: notebooks/ and sql/ no longer ignored;
  notebooks/outputs/, docs/_build/, .streamlit/config.toml added
- 4 publication-pipeline scripts (resolves the previously dangling
  Makefile targets: run-notebooks, consolidate-tables, publication)
- 6 dev/translation diagnostics moved to scripts/dev/
- 6 dev/debug SQL queries moved into sql/
- 6 publication notebooks (outputs cleared, local paths replaced)
- .streamlit/config.toml.example (sanitized)

## Database

Adds 3 nullable columns to narratives via the existing
`0000000dedup_add_narrative_deduplication` migration. Purely additive,
fully reversible. Apply with `alembic upgrade head`.

Prod DB was at revision `1a2b3c4d5e6f` before this PR; will be at
`0000000dedup` after.

## Test plan

- [ ] make check (format/lint/typecheck) — green
- [ ] make test — green
- [ ] alembic upgrade head against staging clone — green
- [ ] streamlit app smoke (language toggle, evaluation, questionnaire)
- [ ] one notebook executes end-to-end against staging
- [ ] batch_evaluation.py --dry-run — green

## Rollback

\`git reset --hard pre-consolidation-public\` + \`pg_restore\` from the
backup taken in Phase B.
EOF
)"
```

Merge style: **rebase merge**, so the 12 commits keep their identity in `main` history.

---

## Phase F — Archive the private repo (plan §8)

After `main` is green and deployed:

```bash
cd ~/mines/pain-narratives-app

git checkout main
git pull
git checkout -b archive
cat > README.md <<'EOF'
# pain-narratives-app (archived)

Active development moved to
https://github.com/gregorio-ferreira/pain-narratives-app-public on 2026-05.

This repository is preserved read-only for historical reference and as
the snapshot accompanying the Software Impacts publication.
EOF
git add README.md
git commit -m "chore: archive notice — moved to pain-narratives-app-public"
git push origin archive

# On GitHub:
#   Settings → General → Default branch → set to `archive`
#   Settings → Danger Zone → Archive this repository
```

---

## What to watch out for

- **Don't run `alembic downgrade` past `260d578db51b`, `47f5ef239b72`, or `bad99e59d04b` on prod.** Those revisions exist with the same IDs in both repos but the public versions of their downgrade bodies are no-ops. A downgrade-then-upgrade cycle would leave the schema in an inconsistent state. Forward-only is fine; the dedup migration `0000000dedup` has a real downgrade and can be reversed safely.
- **The EC2 hostname is in earlier public-repo git history** from the Apr 27 import (`scripts/fix_css_error.sh` and possibly elsewhere). Sanitization in this PR only affects the post-merge tree. If you want it gone from history, do a separate `git filter-repo --replace-text` pass *after* this PR is merged.
- **`config.yaml` and `.streamlit/config.toml` are gitignored.** If you copy them onto a new dev machine, expect to copy them by hand from your password manager / 1Password / wherever — they will not flow through git.
- **Notebooks now write to `notebooks/outputs/`**, which is gitignored. The Makefile target `publication` writes its consolidated Excel to `notebooks/outputs/publication/publication_tables.xlsx`. If you want the consolidated workbook tracked, move it explicitly somewhere else (e.g. `data/publication/`) which is currently ignored by `data/`.

---

## Useful one-liners

```bash
# See exactly what each commit will contain (after Phase A)
git log --stat pre-consolidation-public..HEAD

# Compare your prod alembic head vs. the repo's heads
uv run alembic current
uv run alembic heads

# Verify no operational secrets remain in tracked files
git grep -nE "ec2-|amazonaws|password\s*=\s*['\"]" \
   -- ':!*.example' ':!CONSOLIDATION_PLAN.md' ':!HANDOFF_TO_CLAUDE_CODE.md'

# If something goes wrong before push, full reset:
git reset --hard pre-consolidation-public
```
