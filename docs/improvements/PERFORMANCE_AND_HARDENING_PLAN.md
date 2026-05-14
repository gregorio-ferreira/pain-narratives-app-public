# Performance & Hardening Plan

This document captures four independent improvement tracks for the
`pain-narratives-app-public` codebase, identified during the post-migration
review on 2026-05-14. Each section is self-contained: it describes the
**current behavior**, the **problem** (with concrete file paths and line
numbers), the **proposed fix**, an **implementation sketch**, **validation
steps**, and the **expected payoff vs. risk**.

The tracks are ordered by expected return on effort for this codebase. None
of them depend on each other; pick them up in whichever order suits your time.

| # | Track | Estimated effort | Risk |
|---|---|---|---|
| 1 | Database connection lifecycle (pooling + pre-ping) | ~1 hour | Low |
| 2 | systemd hardening (limits, journal, restart policy) | ~30 min | Low |
| 3 | Streamlit caching and session reuse | ~3 hours | Medium |
| 4 | Batch runner parallelism | ~1 day | Medium-high |

---

## Track 1: Database connection lifecycle

### Current behavior

[src/pain_narratives/core/database.py:56-66](../../src/pain_narratives/core/database.py#L56-L66) creates the SQLAlchemy engine with
all defaults:

```python
engine = create_engine(settings.database_url, echo=False)
```

`DatabaseManager.get_session()` ([database.py:47-49](../../src/pain_narratives/core/database.py#L47-L49)) opens a new
`sqlmodel.Session` per call. There are ~55 `get_session()` call sites across
the codebase.

### Problem

For a Streamlit app talking to an RDS Postgres across regions, this leaves
two important defaults wrong:

1. **No `pool_pre_ping=True`.** When a TCP connection in the pool has been
   idle longer than RDS's `idle_in_transaction_session_timeout` (or a NAT /
   firewall idle reaper between AZs), the next query raises
   `OperationalError: server closed the connection unexpectedly`. Users see
   this as random "DB error" toasts after the app has been idle for a while.
2. **No `pool_recycle`.** Connections are kept indefinitely. Same failure
   mode as above, just rarer.
3. **Pool size defaults to 5 + 10 overflow.** Fine for single-user dev, but
   when several experimenters open the app concurrently and trigger batch
   evaluations, sessions can be held long enough to block UI requests.

The current `_create_engine` also does a one-shot
`with engine.connect(): pass` at construction time. That is a connectivity
smoke test, not a health check — it does nothing for sessions opened minutes
or hours later.

### Proposed fix

Configure the engine explicitly in `_create_engine`:

```python
engine = create_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,      # cheap SELECT 1 before checkout; eliminates stale conns
    pool_recycle=1800,       # recycle conns older than 30 min
    pool_size=10,            # keep 10 hot conns
    max_overflow=20,         # allow short spikes
    pool_timeout=30,         # fail fast if pool is exhausted
)
```

If you want to be extra careful around long-running Streamlit sessions, you
can also pass `connect_args={"keepalives": 1, "keepalives_idle": 60}` so the
OS-level TCP keepalive kicks in before AWS's NAT/firewall drops the socket.

### Implementation sketch

1. Edit [src/pain_narratives/core/database.py:60](../../src/pain_narratives/core/database.py#L60) — replace the one-line
   `create_engine(...)` call with the multi-argument form above.
2. Keep the existing connectivity smoke test (`with engine.connect()`) — it
   still catches "DB completely unreachable" at boot.
3. Optional: lift the four pool numbers into `BedrockConfig`-style constants
   or the `app:` block in `config.yaml` if you want per-environment overrides.
   Not required.

### Validation

- Unit tests still pass: `uv run pytest tests/`
- Smoke-test from a Python shell:
  ```python
  from pain_narratives.core.database import DatabaseManager
  dm = DatabaseManager()
  with dm.get_session() as s:
      s.execute("SELECT 1")
  ```
- Manual: open the Streamlit app, leave it idle for 30+ minutes, then trigger
  a DB-backed action. Before the fix this can drop a stale-connection error;
  after the fix it should succeed transparently.
- (Optional) enable SQLAlchemy pool logging once to confirm pre-ping is
  firing: `logging.getLogger("sqlalchemy.pool").setLevel(logging.DEBUG)`.

### Payoff vs. risk

**Payoff:** eliminates the most common transient DB error class. Adds modest
headroom for concurrent users.
**Risk:** very low. `pool_pre_ping` adds one cheap roundtrip per session
checkout; with sub-millisecond latency to RDS this is invisible. Pool size
changes are bounded and revertible.

---

## Track 2: systemd hardening

### Current behavior

The live unit at `/etc/systemd/system/pain-narratives.service` (mirrored by
[deploy/pain-narratives.service](../../deploy/pain-narratives.service) as a
template):

```ini
[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/pain-narratives-app-public
Environment="PATH=/home/ubuntu/.local/bin:..."
Environment="STREAMLIT_SERVER_ENABLE_STATIC_SERVING=true"
Environment="STREAMLIT_SERVER_ENABLE_CORS=false"
Environment="STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=true"
ExecStart=/home/ubuntu/.local/bin/uv run streamlit run scripts/run_app.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
```

### Problem

1. **No resource limits.** If a Streamlit worker leaks memory (uploaded
   PDFs, large pandas frames, runaway translation cache), it can consume all
   RAM on the EC2 and cause OOM-kills of unrelated processes (sshd,
   journald).
2. **`Restart=always` with no rate limit.** A pathological bug that
   crashes immediately on startup will restart the process every 10s
   forever, filling the journal and burning CPU.
3. **No journal rate-limit.** Streamlit + the Bedrock retry loop can log
   verbose tracebacks; with `Restart=always` a crash loop fills `/var/log`
   quickly.
4. **No filesystem hardening.** The unit could deny writes outside the app
   directory cheaply; it doesn't, so a code-execution bug has the full FS to
   play with.
5. **No `EnvironmentFile=` separation.** Secrets/config still live in the
   on-disk `config.yaml`, but a per-host `.env`-style override would let you
   keep tunables (port, region) outside the service unit.

### Proposed fix

A hardened unit looks like:

```ini
[Unit]
Description=Pain Narratives Streamlit App
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=<APP_USER>
Group=<APP_GROUP>
WorkingDirectory=<APP_ROOT>

# --- limits ---
MemoryMax=2G
MemoryHigh=1500M
CPUQuota=200%           # at most 2 cores
TasksMax=256
LimitNOFILE=4096

# --- hardening ---
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
PrivateTmp=true
ReadWritePaths=<APP_ROOT>/logs <APP_ROOT>/checkpoints <APP_ROOT>/data

# --- restart policy ---
Restart=on-failure
RestartSec=10
StartLimitIntervalSec=300
StartLimitBurst=5        # 5 crash-restarts in 5 min → give up

# --- environment ---
Environment="PATH=<UV_BIN_DIR>:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="STREAMLIT_SERVER_ENABLE_STATIC_SERVING=true"
Environment="STREAMLIT_SERVER_ENABLE_CORS=false"
Environment="STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=true"
EnvironmentFile=-/etc/pain-narratives.env

ExecStart=<UV_BIN_DIR>/uv run streamlit run scripts/run_app.py

# --- logging ---
StandardOutput=journal
StandardError=journal
SyslogIdentifier=pain-narratives
LogRateLimitIntervalSec=10
LogRateLimitBurst=200

[Install]
WantedBy=multi-user.target
```

Key choices, with the reasoning:

- `MemoryHigh` is a soft throttle (kernel slows the process); `MemoryMax`
  is the hard limit. Together they let the kernel apply pressure before
  outright killing the process.
- `Restart=on-failure` instead of `always` means a clean shutdown
  (`systemctl stop`) does not get clobbered by a restart.
- `StartLimitBurst=5` over 5 minutes prevents crash-loop log explosions.
- `ProtectSystem=strict` makes `/usr`, `/boot`, `/etc` read-only for the
  service; `ReadWritePaths` re-enables write access only to the directories
  the app actually needs.
- `EnvironmentFile=-/etc/pain-narratives.env` with leading `-` makes the
  file optional. Use it for per-host overrides like
  `STREAMLIT_SERVER_PORT=8501`.

### Implementation sketch

1. Update the runtime unit:
   ```bash
   sudo cp /etc/systemd/system/pain-narratives.service \
           /etc/systemd/system/pain-narratives.service.bak.$(date +%F)
   sudo $EDITOR /etc/systemd/system/pain-narratives.service
   # paste the hardened block above, replacing <APP_USER>/<APP_ROOT>/<UV_BIN_DIR>
   sudo systemctl daemon-reload
   sudo systemctl restart pain-narratives
   ```
2. Also update the in-repo template
   [deploy/pain-narratives.service](../../deploy/pain-narratives.service) so
   future deploys get the hardened version.
3. (Optional) Create `/etc/pain-narratives.env` with `0600` perms for any
   per-host tunables you want outside the unit file.

### Validation

- `systemctl status pain-narratives` shows `active (running)` and the
  expected `Tasks` / `Memory` lines.
- `systemd-analyze security pain-narratives` reports an improved exposure
  score (target: below 5.0).
- Stress-test: `stress-ng --vm 1 --vm-bytes 3G --timeout 30s` from inside
  the unit's process group (or simulate via a heavy upload) — the service
  should be killed by `MemoryMax=2G` rather than the box OOM-killing
  unrelated processes.
- Crash-loop test: introduce a deliberate boot-time error, watch
  `systemctl status` show `failed` after 5 restarts within 5 minutes
  instead of restarting forever.

### Payoff vs. risk

**Payoff:** the EC2 stays healthy even when the app misbehaves; logs stay
readable; reduces blast radius of a code-execution bug.
**Risk:** low if the read-write paths and PATH are correct. The main failure
mode is forgetting to add a directory to `ReadWritePaths` and getting EROFS
on first write — easily diagnosed in the journal.

---

## Track 3: Streamlit caching and session reuse

### Current behavior

[src/pain_narratives/ui/app.py](../../src/pain_narratives/ui/app.py) holds long-lived objects in
`st.session_state`:

- [app.py:443](../../src/pain_narratives/ui/app.py#L443): `st.session_state.openai_client = OpenAIClient(api_key=api_key)`
- [app.py:449](../../src/pain_narratives/ui/app.py#L449): `st.session_state.db_manager = DatabaseManager()`

`session_state` is per-browser-session, so every new user spins up their own
`DatabaseManager` (with its own SQLAlchemy engine and connection pool) and
its own `OpenAIClient`. The translator
([src/pain_narratives/ui/utils/localization.py](../../src/pain_narratives/ui/utils/localization.py)) has Streamlit caching, but
the cache key includes language and is **cleared globally** when language
changes ([localization.py:51-53](../../src/pain_narratives/ui/utils/localization.py#L51-L53)).

### Problem

1. **N engines for N users.** SQLAlchemy engines are designed to be shared
   across threads; creating one per session multiplies open connections and
   defeats pooling. With ~10 concurrent users you can quickly approach RDS's
   `max_connections` limit.
2. **`st.cache_data.clear()` is a sledgehammer.** Changing language wipes
   every cached function output app-wide (narrative loads, prompt fetches,
   anything decorated with `@st.cache_data`). Subsequent UI clicks then
   re-run those expensive functions for no gain.
3. **Localization YAML re-parsed on every script rerun** in the
   `use_cache=False` path ([localization.py:33-39](../../src/pain_narratives/ui/utils/localization.py#L33-L39)). The
   `_language_cache` dict fixes this but it's a process-global mutable; safe
   in Streamlit's single-process model, brittle if you ever move to multi-
   worker.
4. **No `@st.cache_resource` anywhere.** That decorator is purpose-built
   for exactly the shared-singleton case (engines, clients).

### Proposed fix

Introduce two module-level cached factories and call them everywhere the
current code uses `st.session_state.openai_client` / `db_manager`:

```python
# src/pain_narratives/ui/utils/resources.py  (new file)
import streamlit as st
from pain_narratives.core.database import DatabaseManager
from pain_narratives.core.openai_client import OpenAIClient


@st.cache_resource(show_spinner=False)
def get_db_manager() -> DatabaseManager:
    """One engine + pool shared across all browser sessions."""
    return DatabaseManager()


@st.cache_resource(show_spinner=False)
def get_openai_client(api_key: str | None = None) -> OpenAIClient:
    """One OpenAIClient per (api_key) key; default key = env."""
    return OpenAIClient(api_key=api_key) if api_key else OpenAIClient()
```

`@st.cache_resource` returns the **same object** to every session. Per-user
state (auth user, evaluation history, current narrative) stays in
`session_state`. Per-app shared state (engine, client) moves into
`cache_resource`.

For localization, replace the global `st.cache_data.clear()` with a
targeted invalidation:

```python
# instead of: st.cache_data.clear()
_load_language_data_cached.clear()    # only clears this function's cache
```

`@st.cache_data` functions expose a `.clear()` method on themselves.

### Implementation sketch

1. Create `src/pain_narratives/ui/utils/resources.py` with the two factories
   above.
2. Replace assignments to `st.session_state.openai_client` /
   `st.session_state.db_manager` in
   [app.py:430-455](../../src/pain_narratives/ui/app.py#L430-L455) with reads from `get_openai_client(...)` and
   `get_db_manager()`.
3. Audit the rest of `app.py` and `ui/components/*.py` for any code that
   reads `st.session_state.db_manager` / `openai_client` — most will be
   compatible if you keep `session_state` populated by calling the factory
   on each rerun.
4. In [localization.py:51](../../src/pain_narratives/ui/utils/localization.py#L51), replace `st.cache_data.clear()` with
   `_load_language_data_cached.clear()`.
5. Delete the global `_language_cache` dict and the `use_cache=False` path —
   `@st.cache_data` already handles concurrent reads safely.

### Validation

- `uv run pytest tests/` — anything that imports the UI modules should
  still pass.
- Open the app in two browser windows simultaneously, log in as different
  users, watch `pg_stat_activity` on the DB:
  ```sql
  SELECT count(*) FROM pg_stat_activity WHERE application_name LIKE '%pain%';
  ```
  Before: one connection set per session. After: one connection set total.
- Switch language mid-session and confirm narrative-load functions are not
  re-evaluated (add a `logger.info(...)` inside one of them as a temporary
  probe).

### Payoff vs. risk

**Payoff:** scales the app to many more concurrent users on the same RDS
budget. Removes a noticeable lag spike on first interaction with each tab.
Eliminates the language-change cache-stampede.
**Risk:** medium. The session-state references are read all over the UI
layer; missing one means a stale reference. Mitigated by keeping
`session_state` populated as a *cached pointer* (assign on each rerun)
rather than removing it entirely.

---

## Track 4: Batch runner parallelism

### Current behavior

[src/pain_narratives/batch/processor.py:810](../../src/pain_narratives/batch/processor.py#L810) and
[processor.py:1067](../../src/pain_narratives/batch/processor.py#L1067) loop over narratives sequentially with a
`time.sleep(delay_between_calls)` (default 1.0s,
[processor.py:97](../../src/pain_narratives/batch/processor.py#L97)) between every sub-call. Per narrative the runner
does 4 LLM calls (dimensions + PCS + BPI-IS + TSK-11SV), each blocking on
Bedrock latency.

The `SIMPLIFIED_EXPERIMENT_PLAN.md` budgets ~3 hours per model for 152
narratives × 3 reps. Wall time is dominated by `Bedrock.Converse` latency
(seconds per call), not by Python work.

### Problem

The CPU sits idle waiting for HTTP responses. Bedrock supports concurrent
requests well below provider quotas; we are leaving substantial throughput
on the table. At 3 hours × 2 models × 3 reps that's 18 wall-clock hours
where 4-8x would be achievable.

### Proposed fix

Add an **opt-in** parallel mode that processes K narratives concurrently
using a bounded thread pool. Keep the existing sequential code path as the
default so the published baseline reproduces exactly.

Two-level parallelism is **not** worth it here:

- Across narratives: yes — they are independent.
- Within a narrative (4 sub-calls): no — the questionnaires share retry
  state and consecutive-failure counters, and parallelising them
  complicates the auth-error-halts-batch invariant.

Recommended approach: `concurrent.futures.ThreadPoolExecutor` with
`max_workers=4`. Threads are appropriate because the work is I/O-bound on
boto3 (which releases the GIL during socket reads).

### Implementation sketch

1. Add a new field to `BatchConfig`
   ([processor.py:80-123](../../src/pain_narratives/batch/processor.py#L80-L123)):
   ```python
   max_workers: int = 1   # 1 = sequential (default), N>1 = parallel
   ```
2. Add a CLI flag in
   [scripts/run_batch_evaluation.py](../../scripts/run_batch_evaluation.py): `--max-workers 4`
   (default 1).
3. Extract the per-narrative work into a single function
   `_process_one(idx, row, group_id, user_id) -> tuple[idx, NarrativeEvaluationResult]`.
   It must be thread-safe; verify by inspection that:
   - `self.db_manager.get_session()` opens a new session per call (it does
     — see [database.py:47](../../src/pain_narratives/core/database.py#L47)); SQLAlchemy engines + connection pools are
     thread-safe.
   - `self.openai_client` / `_bedrock_client` are used only for their
     thread-safe boto3/HTTP calls — they are.
   - `self.progress` is mutated under a `threading.Lock`.
   - The shared `consecutive_failures` counter and checkpoint writes are
     guarded by the same lock.
4. Replace the `for idx, row in narratives_df.iterrows()` block with:
   ```python
   from concurrent.futures import ThreadPoolExecutor, as_completed
   lock = threading.Lock()
   with ThreadPoolExecutor(max_workers=self.config.max_workers) as ex:
       futures = {ex.submit(self._process_one, idx, row, group_id, user_id): idx
                  for idx, row in narratives_df.iterrows()}
       for fut in as_completed(futures):
           with lock:
               # update progress, consecutive_failures, checkpoint
               ...
   ```
5. Critical invariant: a `BedrockAuthError` from any worker must cancel the
   remaining futures and halt the batch. Use a `threading.Event` to signal,
   and check it inside `_process_one` before each sub-call. Calling
   `ex.shutdown(wait=False, cancel_futures=True)` on auth failure is the
   cleanest path.

### Validation

- Smoke test with a 5-narrative pilot at `--max-workers 4`. Confirm:
  - 5 rows land in `experiments_list` with the new group ID.
  - All 5 have `succeeded=true`.
  - `evaluation_results` has exactly 4 rows per experiment.
  - Wall time is ~1/4 of the sequential pilot.
- Auth-failure drill: revoke the AWS profile mid-run; confirm the batch
  stops within seconds and the checkpoint is written.
- Reproducibility check: rerun with `--max-workers 1` and compare results
  to a known-good baseline run — they should match (modulo LLM
  non-determinism).
- Throttling drill: at `--max-workers 8`, watch for Bedrock
  `ThrottlingException`. If they appear, drop `max_workers` or add a token
  bucket. The default of 4 should be safe for current quotas; verify in
  the Bedrock console (Service Quotas → `On-demand model inference
  requests per minute`).

### Payoff vs. risk

**Payoff:** roughly 3-4x wall-time reduction at `max_workers=4`. ~3 hours
per model → ~45 min. For 6 runs total (2 models × 3 reps), that's saving
~12 hours of clock time on this rebuttal alone, and more on every future
sweep.
**Risk:** medium-high. The auth-error-halts-batch and consecutive-failure
tripwire invariants are easy to break under concurrency. Mitigations:
keep `max_workers=1` as the default so the published baseline is
unaffected, gate the new path behind the CLI flag, and add an integration
test that simulates a mid-batch auth failure.

---

## Decision criteria (which tracks to do, in what order)

For this codebase, my recommended sequence is:

1. **Track 1 (DB pooling)** — cheapest fix, addresses a real failure class
   you are likely to hit unpredictably. Do this first.
2. **Track 2 (systemd hardening)** — defensive; do it before the next
   incident, not after.
3. **Track 4 (batch parallelism)** — biggest single time-saver if you
   expect more sweeps; skip if the rebuttal is the last big batch this
   project will run.
4. **Track 3 (Streamlit caching)** — only if you actually see concurrent-
   user pain or notice the language-switch lag. The current code works
   fine for single-user dev.

Each track has its own validation checklist above; do not collapse them
into one PR. Sequential, reversible commits make the rollback story simple
if any one fix misbehaves in production.
