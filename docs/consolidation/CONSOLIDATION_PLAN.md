# Consolidation Plan — `pain-narratives-app` (private) → `pain-narratives-app-public`

**Goal.** Make `pain-narratives-app-public` the single repository going forward. Archive the private repo. Keep the existing experiment Postgres database working without data loss.

**Decisions captured upfront (your answers):**

1. **Private repo fate** → archive entirely. All future work happens in the public repo.
2. **Publications folder** → stays out of the public repo. Public repo will reference papers via citation/DOI only.
3. **Notebooks (`notebooks_new/`)** → move all 6 to the public repo.
4. **DB schema** → you said "same today." The diff says **almost** — see §3. Net effect is one additive migration to apply; nothing destructive.

---

## 0 — Snapshot of the diff (what we are reconciling)

I ran a recursive diff between `pain-narratives-app` and `pain-narratives-app-public` (commit `0fe255f` and `078385e` respectively). Public has 12 commits total, all dating from the initial seed at `6bcc9a6 feat: init from our private repo` (Apr 27) plus README/locale/image polish for the paper. Private has continued to 119 commits with real application work — language handling, Streamlit config, terminology, Makefile, notebooks, batch evaluation, ACM analysis models. **In every code path, private is ahead.** In every "open-source scaffolding" path (Dockerfile, LICENSE, NOTICE, CONTRIBUTING, uv.lock, images, init-db.sql, the dedup alembic migration), public is ahead.

### 0.1 Files only in private (must decide: move, sanitize, or drop)

| Path | Lines | Disposition |
|---|---|---|
| `src/pain_narratives/db/models_acm_202512.py` | 571 | **Move** (notebooks depend on it) |
| `notebooks_new/01..06_*.ipynb` | ~10,640 | **Move, after clearing outputs** |
| `scripts/consolidate_publication_tables.py` | 324 | **Move** (Makefile already references it in public) |
| `scripts/run_batch_evaluation.py` | 570 | **Move** |
| `scripts/run_all_notebooks.sh` | 166 | **Move** (Makefile already references it) |
| `scripts/tokens_count.py` | 292 | **Move** |
| `scripts/test_gpt5_compatibility.py` | — | **Move to `scripts/dev/`** (utility, not pytest) |
| `scripts/test_translation_*.py` (4 files) | — | **Move to `scripts/dev/`** |
| `scripts/test_multilingual_*.py` (2 files) | — | **Move to `scripts/dev/`** |
| `sql/*.sql` (7 files) | 601 | **Move to `sql/`** in public — they are dev/debug queries, schema-aware but no PII |
| `.streamlit/config.toml` | 38 | **Sanitize → `.streamlit/config.toml.example`** (currently hard-codes EC2 host `ec2-63-176-147-227.eu-central-1.compute.amazonaws.com`) |
| `docs/plan_technical_paper.md` | — | **Drop** — paper is published, plan no longer relevant |
| `docs/public_repo_license.md` | — | **Drop** — superseded by `LICENSE`/`NOTICE` |
| `publications/*.pdf`, `*.tex` | — | **Stay private per your decision** |
| `.DS_Store` | — | Drop, gitignore |

### 0.2 Files only in public (keep as-is)

`LICENSE`, `NOTICE`, `CONTRIBUTING.md`, `Dockerfile`, `docker-compose.yml`, `docker/init-db.sql`, `config.yaml.example`, `images/`, `uv.lock`, plus the alembic migration `0000000dedup_add_narrative_deduplication.py`.

### 0.3 Files in both, drifted (private is ahead)

| Path | Δ (pub→priv) | Notes |
|---|---|---|
| `src/pain_narratives/ui/app.py` | +70 / −12 | Largest drift; recent terminology + language work |
| `src/pain_narratives/locales/{en,es}.yml` | +15/−10, +22/−17 | Locale polish |
| `src/pain_narratives/config/settings.py` | +10 / −24 | Language handling refactor |
| `src/pain_narratives/config/default_prompts.yaml` | +9 / −6 | Prompt tweaks |
| `src/pain_narratives/ui/components/{evaluation_display,questionnaire}.py` | small | Cosmetic + i18n |
| `src/pain_narratives/__init__.py` | +1/−1 | Likely version bump |
| `README.md` | +34 / −93 | Public README is **larger** (LICENSE/Docker sections) — be careful, this needs **merge**, not overwrite |
| `Makefile` | +5 / −55 | Public has **more** targets (notebooks, publication, docs) — also merge |
| `.gitignore` | +106 / −60 | Private is more thorough; merge |
| `pyproject.toml` | +2 / −2 | Trivial |
| `example.yaml` | +4 / −4 | Public uses `YOUR_DB_HOST` placeholders — **keep public's** version |
| `.github/copilot-instructions.md` | small | `temperature` and `max_tokens` defaults differ — keep public's |
| `docs/EDIT_EXPERIMENT_GROUPS_GUIDE.md`, `PROMPTS_MIGRATION_SUMMARY.md`, `TRANSLATION_MODEL_CONFIG.md`, `conf.py` | small | Doc drift; take private's |

### 0.4 Files in both with **same revision ID but different code** (alembic)

`260d578db51b_add_questionnaire_feedback_table.py`, `47f5ef239b72_add_questionnaire_feedback_table.py`, `bad99e59d04b_add_questionnaire_prompts_table.py`. The public versions were rewritten as **safe-for-fresh-install no-ops** (or `IF EXISTS` / `pass`). The private versions retain the original column-rename/drop logic. **Keep the public versions** — they don't touch your DB on `upgrade head` because alembic sees those revisions are already applied. Switching does mean you must never run `alembic downgrade` past these revisions on your prod DB.

---

## 1 — Pre-flight (do this before touching anything)

1.1 **Back up the production database.**

```bash
pg_dump -Fc -d pain_narratives -h <host> -U <user> \
  > ~/backups/pain_narratives_$(date +%Y%m%d_%H%M).dump
```

1.2 **Snapshot the current alembic head on prod.**

```bash
cd ~/mines/pain-narratives-app
uv run alembic current   # record this revision somewhere safe
```

1.3 **Tag both repos** so the pre-merge state is preserved.

```bash
cd ~/mines/pain-narratives-app
git tag pre-consolidation-private && git push --tags

cd ~/mines/pain-narratives-app-public
git tag pre-consolidation-public && git push --tags
```

1.4 **In the public repo, create a working branch** for the merge.

```bash
git checkout -b chore/consolidate-from-private
```

1.5 **Stop the deployed Streamlit instance** (if any users could be writing) for the duration of the DB migration step in §6.

---

## 2 — Bring the public repo's application code up to date

For each drifted file in §0.3, copy from private to public, then commit logically grouped diffs. Doing it in small commits makes review and rollback feasible.

### 2.1 Source modules (one commit per logical group)

```bash
cd ~/mines/pain-narratives-app-public

# Group A — language handling refactor
cp ../pain-narratives-app/src/pain_narratives/__init__.py src/pain_narratives/__init__.py
cp ../pain-narratives-app/src/pain_narratives/config/settings.py src/pain_narratives/config/settings.py
cp ../pain-narratives-app/src/pain_narratives/config/default_prompts.yaml src/pain_narratives/config/default_prompts.yaml
cp ../pain-narratives-app/src/pain_narratives/locales/en.yml src/pain_narratives/locales/en.yml
cp ../pain-narratives-app/src/pain_narratives/locales/es.yml src/pain_narratives/locales/es.yml
git add -p src/pain_narratives/                # review hunk-by-hunk
git commit -m "feat: forward-port language handling and locale updates from private"

# Group B — UI changes
cp ../pain-narratives-app/src/pain_narratives/ui/app.py src/pain_narratives/ui/app.py
cp ../pain-narratives-app/src/pain_narratives/ui/components/evaluation_display.py src/pain_narratives/ui/components/evaluation_display.py
cp ../pain-narratives-app/src/pain_narratives/ui/components/questionnaire.py src/pain_narratives/ui/components/questionnaire.py
git add -p src/pain_narratives/ui/
git commit -m "feat: forward-port UI updates (terminology, evaluation display, questionnaire)"
```

### 2.2 The ACM analysis models module

```bash
cp ../pain-narratives-app/src/pain_narratives/db/models_acm_202512.py src/pain_narratives/db/
git add src/pain_narratives/db/models_acm_202512.py
git commit -m "feat: add ACM 202512 analysis schema models"
```

This module declares a separate schema `pain_narratives_acm_202512` and is **read-mostly** (the notebooks query it). If those tables already exist in your prod DB, nothing to do. If they don't (i.e. you only have them on a different machine), see §6.4.

### 2.3 Drifted scripts (private is ahead)

Thirteen scripts have drifted in addition to the new ones. Forward-port them with one commit:

```bash
# Top-level scripts
for f in debug_translation.py deploy_ec2.sh deploy_ec2_fixed.sh fix_css_error.sh \
         manage_users.py register_user.py register_user_batch.py run_app.py user_demo.py; do
  cp "../pain-narratives-app/scripts/$f" "scripts/$f"
done

# Setup subfolder
cp ../pain-narratives-app/scripts/setup/complete_setup.py    scripts/setup/
cp ../pain-narratives-app/scripts/setup/init_database.py     scripts/setup/
cp ../pain-narratives-app/scripts/setup/init_uv_env.ps1      scripts/setup/

# Dev subfolder (the existing build_docs.py)
cp ../pain-narratives-app/scripts/dev/build_docs.py          scripts/dev/

git add -p scripts/
git commit -m "feat: forward-port drifted scripts (deploy, user mgmt, setup, dev tools)"
```

Quick sanity scan before committing — `deploy_ec2*.sh` and `.streamlit/config.toml` are the two places where the EC2 hostname leaked into the private repo. Confirm the deploy scripts don't hard-code credentials:

```bash
grep -E "ec2-|amazonaws|password|api_key|sk-" scripts/deploy_ec2*.sh scripts/fix_css_error.sh
```

If the hostname appears, replace it with an environment variable or a placeholder (`$DEPLOY_HOST`) before committing.

### 2.4 Drifted documentation and config

```bash
cp ../pain-narratives-app/docs/EDIT_EXPERIMENT_GROUPS_GUIDE.md docs/
cp ../pain-narratives-app/docs/PROMPTS_MIGRATION_SUMMARY.md docs/
cp ../pain-narratives-app/docs/TRANSLATION_MODEL_CONFIG.md docs/
cp ../pain-narratives-app/docs/conf.py docs/
git add docs/
git commit -m "docs: forward-port doc updates from private"
```

### 2.5 README — manual merge required

`pain-narratives-app/README.md` is 938 lines, public is 997 lines. The public version added Docker, LICENSE, contributor onboarding, and citation. The private version evolved terminology and a few sections. **Do a 3-way merge**:

```bash
# In the public repo working tree
diff -u README.md ../pain-narratives-app/README.md | less
# Apply only the private-side changes that don't conflict with the public-side scaffolding.
```

Suggested sections to forward-port from private: "Terminology", "Language handling", any updated screenshots in section 2 (image references should keep public's `images/` filenames).

```bash
git add README.md
git commit -m "docs: merge terminology and language updates into public README"
```

### 2.6 Makefile — manual merge required

Public Makefile already has `run-notebooks`, `run-notebooks-safe`, `list-notebooks`, `consolidate-tables`, `publication`, `docs`, `docs-serve`, `experiments`, `run-script`. **These reference scripts that don't exist in public yet — fix in §4.** From private's Makefile, forward-port: kernel-name handling and any small target tweaks.

```bash
git add Makefile
git commit -m "build: align Makefile with private repo improvements"
```

### 2.7 `.gitignore` — take the union

Private's gitignore is the standard "GitHub's Python" template (verbose, comprehensive). Public's is shorter and project-specific. Take **public's project-specific entries** + **private's standard Python ignores**. Add `.DS_Store`, `notebooks_new/outputs/` (if not already), and `.streamlit/config.toml` (so future operator-specific configs don't leak).

```bash
git add .gitignore
git commit -m "chore: tighten .gitignore (Python boilerplate + operator configs)"
```

### 2.8 `pyproject.toml` — review the 2-line diff

Likely the project name or kernel display name. Reconcile by hand, prefer public's published name.

```bash
git add pyproject.toml
git commit -m "build: reconcile pyproject metadata"
```

### 2.9 Trivial drift — skip or take public's

`example.yaml`: keep public's placeholder version. `.github/copilot-instructions.md`: keep public's `temperature=1.0, max_tokens=8000`. No commit needed unless something obvious is missing.

---

## 3 — Migrate the notebooks (with PII / path scrub)

### 3.1 Clear outputs and copy over

The private notebooks contain printouts of paths like `/home/gferreir/mines/pain-narratives-app/...` (about 100 occurrences across all 6 notebooks). No API keys, passwords, or PII were found — just local filesystem strings in printed cell outputs. **Clearing outputs removes all of them in one shot.**

```bash
cd ~/mines/pain-narratives-app-public
mkdir -p notebooks
# Strip outputs as we copy
for nb in ../pain-narratives-app/notebooks_new/*.ipynb; do
  uv run jupyter nbconvert --clear-output --to notebook \
    --output-dir=notebooks "$nb"
done
```

(Renaming `notebooks_new/` → `notebooks/` is the natural choice in public; the Makefile target `run-notebooks` already expects this convention.)

### 3.2 Update output directory references

The notebooks write to `notebooks_new/outputs/...`. Either:

- (a) Keep them in `notebooks/` and change the path inside the notebooks once via search/replace, **or**
- (b) Add a constant at the top of each notebook (`OUTPUT_DIR = Path("./outputs")`) and gitignore `notebooks/outputs/`.

(b) is cleaner and matches the `Makefile` target `publication: run-notebooks consolidate-tables`.

```bash
git add notebooks/ .gitignore
git commit -m "feat: migrate analysis notebooks (cleared outputs, generic paths)"
```

### 3.3 Smoke-test one notebook end-to-end

Pick the cheapest one — `02_patient_demographics_for_publication.ipynb` — and run it against your existing DB to confirm imports, model references, and DB connectivity are intact:

```bash
uv run jupyter nbconvert --to notebook --execute \
  notebooks/02_patient_demographics_for_publication.ipynb \
  --output notebooks/_smoke_test_02.ipynb
```

If it succeeds, delete the smoke output and proceed.

---

## 4 — Move the orchestration scripts (and remove the dangling Makefile references)

### 4.1 Move publication / batch / token scripts

```bash
cp ../pain-narratives-app/scripts/run_batch_evaluation.py scripts/
cp ../pain-narratives-app/scripts/consolidate_publication_tables.py scripts/
cp ../pain-narratives-app/scripts/run_all_notebooks.sh scripts/
cp ../pain-narratives-app/scripts/tokens_count.py scripts/
chmod +x scripts/run_all_notebooks.sh
git add scripts/
git commit -m "feat: add publication pipeline scripts (batch eval, notebook runner, token counter)"
```

After this commit, the public Makefile targets `experiments`, `run-notebooks`, `consolidate-tables`, `publication` should all resolve.

### 4.2 Move dev/translation utility scripts to `scripts/dev/`

The 7 `test_*.py` files in private's `scripts/` are not pytest tests — they are CLI utilities. Putting them in `scripts/dev/` keeps the top-level `scripts/` clean.

```bash
mkdir -p scripts/dev
for f in test_gpt5_compatibility.py \
         test_translation_comprehensive.py test_translation_config.py test_translation_service.py \
         test_multilingual_display.py test_multilingual_functionality.py; do
  cp "../pain-narratives-app/scripts/$f" "scripts/dev/$f"
done
git add scripts/dev/
git commit -m "chore: move translation/multilingual diagnostics to scripts/dev/"
```

### 4.3 Move the SQL dev/debug queries

```bash
mkdir -p sql
cp ../pain-narratives-app/sql/*.sql sql/
# Drop temp.sql which is a 5-line scratchpad
rm -f sql/temp.sql
git add sql/
git commit -m "chore: import SQL dev/debug queries from private repo"
```

### 4.4 Add a sanitized `.streamlit/config.toml.example`

```bash
mkdir -p .streamlit
cp ../pain-narratives-app/.streamlit/config.toml .streamlit/config.toml.example
# Edit .streamlit/config.toml.example: replace the EC2 hostname with "your-server.example.com"
# Make sure .streamlit/config.toml itself is gitignored (done in §2.6)
git add .streamlit/config.toml.example
git commit -m "feat: add Streamlit config template (gitignore live config)"
```

---

## 5 — Database compatibility: apply the dedup migration cleanly

Your prod DB is at alembic head **`1a2b3c4d5e6f`** (drop_legacy_columns_from_narratives) — that's the highest revision in the private repo. The public repo has one extra: **`0000000dedup`**, which adds three additive columns to `narratives`:

- `narrative_hash` (SHA256, length 64)
- `word_count` (int)
- `char_count` (int)

This is **safe**: it adds columns, never drops, and the down_revision points cleanly at `1a2b3c4d5e6f`.

### 5.1 Verify the head before upgrade

```bash
cd ~/mines/pain-narratives-app-public
uv run alembic current        # expect 1a2b3c4d5e6f
uv run alembic heads          # expect 0000000dedup
uv run alembic history --verbose | head -40
```

### 5.2 Apply the migration in a transaction (Postgres supports DDL transactions)

```bash
uv run alembic upgrade head
uv run alembic current        # should now show 0000000dedup
```

### 5.3 Backfill the new columns (optional, only if notebooks expect non-null values)

```sql
-- run via psql or a one-off script
UPDATE pain_narratives_app.narratives
SET narrative_hash = encode(digest(narrative_text, 'sha256'), 'hex'),
    word_count     = array_length(regexp_split_to_array(narrative_text, '\s+'), 1),
    char_count     = char_length(narrative_text)
WHERE narrative_hash IS NULL;
```

### 5.4 ACM analysis schema (`pain_narratives_acm_202512`)

The models in `models_acm_202512.py` are not under alembic — they declare `__table_args__ = {"schema": "pain_narratives_acm_202512"}`. If your prod DB already has these tables (they were populated for the published analyses), there's nothing to do.

If you want them under alembic going forward, generate a single autogen revision **after** importing the model module in `alembic/env.py`:

```bash
uv run alembic revision --autogenerate -m "Add ACM 202512 analysis schema"
# Review the generated migration carefully — it should only CREATE TABLE in the new schema, never DROP anything in pain_narratives_app
uv run alembic upgrade head     # only on a non-prod DB first; verify tables match
```

If on prod the tables already exist exactly as the autogen migration would create them, run `alembic stamp <new_rev>` instead of `upgrade` to mark it as applied without running the DDL.

---

## 6 — Verification

### 6.1 Unit + integration tests

```bash
make check              # format + lint + typecheck
make test               # full pytest, including tests/test_integration.py
```

Expected: all pass. The drifted tests in `tests/` are the same set in both repos; they should run cleanly against the merged code.

### 6.2 Run the app locally against the production DB (read-only sanity)

```bash
make app
# Verify: language toggle works, terminology updated, evaluation display renders,
# questionnaire feedback loads, expert UI loads.
```

### 6.3 Run one notebook end-to-end (from §3.3 if not already)

### 6.4 Run the batch evaluation script in dry-run mode

```bash
uv run python scripts/run_batch_evaluation.py --input data/narratives.xlsx --dry-run
```

This exercises the OpenAI client wiring, the new prompts, settings, and DB connection — without spending tokens.

### 6.5 Build the docs

```bash
make docs
```

---

## 7 — Land the merge

```bash
git push -u origin chore/consolidate-from-private
# Open a PR → review → squash-merge or rebase-merge into main
```

**Suggested PR description tag:** "Closes the private→public migration. Forward-ports 107 commits of application work from the private repo. DB requires `alembic upgrade head` to apply revision `0000000dedup`."

---

## 8 — Archive the private repo

Once `main` of the public repo is green and deployed:

```bash
cd ~/mines/pain-narratives-app
git tag archived-final && git push --tags
# On GitHub: Settings → Danger Zone → Archive this repository
```

Add a stub `README.md` on top of `main` pointing to the public repo:

```bash
git checkout -b archive
cat > README.md <<'EOF'
# pain-narratives-app (archived)

Active development moved to https://github.com/gregorio-ferreira/pain-narratives-app-public on 2026-05.
This repository is preserved read-only for historical reference and the Software Impacts
publication snapshot.
EOF
git add README.md
git commit -m "chore: archive notice — moved to pain-narratives-app-public"
git push origin archive
# Then on GitHub set this branch as default, or just archive the repo.
```

---

## 9 — New workflow (so you never have to copy code between two repos again)

Once the public repo is the source of truth:

1. **All feature work** happens on `pain-narratives-app-public`, on feature branches off `main`.
2. **Unpublished / sensitive content** (paper drafts, raw patient data, expert names) lives **outside any git repo** — keep them in a folder gitignored by the public repo (e.g. `~/research/private-data/` or `pain-narratives-app-public/data/` which is already gitignored).
3. **Future papers**: the analysis notebook for a new paper goes in `notebooks/` from day one. The PDF / LaTeX of the paper itself stays in your private folder; only a citation goes into the public README.
4. **DB migrations**: every schema change goes through alembic on a feature branch, never edited directly. New ACM / publication schemas get their own SQLModel module under `src/pain_narratives/db/`.
5. **Secrets / operator config**: `config.yaml` and `.streamlit/config.toml` are gitignored; commit only the `*.example` versions. Keep your real EC2 hostname and DB credentials out of the repo.

---

## 10 — Risk register & rollback

| Risk | Likelihood | Mitigation |
|---|---|---|
| Alembic upgrade fails | low | DB backup in §1.1; the migration is purely additive; `alembic downgrade -1` reverses it cleanly |
| Drifted alembic migrations confuse alembic | low | Same revision IDs, alembic only checks IDs not body. Verify with `alembic current` after upgrade |
| ACM schema models out of sync with prod tables | medium | §5.4 — autogen and review before applying; use `stamp` on prod if tables already match |
| Notebook outputs leak local paths | low | Cleared in §3.1 via `nbconvert --clear-output` |
| Streamlit EC2 hostname leaked to public history | n/a | `.streamlit/config.toml` was never committed to public; only the `*.example` will be |
| README merge introduces broken image refs | medium | Public images live under `images/`, private references would have used different paths — manually verify image URLs render |
| Lost commits during forward-port | low | Tag both repos in §1.3 before any change; the working branch is reviewable as a single PR |

**Hard rollback** (worst case): `git reset --hard pre-consolidation-public` on the public repo + `pg_restore` from §1.1.

---

## Quick checklist (printable)

- [ ] §1.1 DB backup taken
- [ ] §1.2 Alembic head recorded
- [ ] §1.3 Both repos tagged
- [ ] §1.4 `chore/consolidate-from-private` branch created
- [ ] §2 Source/docs/config drift forward-ported (7 commits)
- [ ] §3 Notebooks migrated, outputs cleared, smoke test passes
- [ ] §4 Scripts moved, sanitized Streamlit example added
- [ ] §5 `alembic upgrade head` applied; ACM schema status confirmed
- [ ] §6 `make check`, `make test`, app smoke, batch dry-run all green
- [ ] §7 PR opened and merged
- [ ] §8 Private repo tagged + archived; stub README pointing to public
- [ ] §9 Workflow change communicated to your research group
