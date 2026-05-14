# Performance and Hardening Backlog

Four independent improvement tracks identified during the post-migration
review (2026-05-14). None of them depend on each other; pick them up in
whichever order suits the available time.

| # | Track | Effort | Risk |
|---|---|---|---|
| 1 | Database connection lifecycle (pooling + pre-ping) | ~1 hour | Low |
| 2 | systemd hardening (limits, journal, restart policy) | ~30 min | Low |
| 3 | Streamlit caching and session reuse | ~3 hours | Medium |
| 4 | Batch runner parallelism | ~1 day | Medium-high |

Recommended sequence: 1 → 2 → 4 → 3. Tracks 1 and 2 are cheap wins that
address real failure classes. Track 4 saves the most wall time on future
sweeps. Track 3 only matters if concurrent-user pain becomes visible.

## 1. Database connection lifecycle

**Current.** [`src/pain_narratives/core/database.py`](../src/pain_narratives/core/database.py)
creates the SQLAlchemy engine with all defaults:

```python
engine = create_engine(settings.database_url, echo=False)
```

**Problem.** Three defaults bite a Streamlit app talking to RDS across
regions:

- No `pool_pre_ping=True` — TCP connections that NAT or RDS reaped come back
  as `OperationalError: server closed the connection unexpectedly`.
- No `pool_recycle` — connections are kept indefinitely. Same failure mode.
- `pool_size=5` + `max_overflow=10` is fine for solo dev but tight when
  several experimenters trigger batch evaluations concurrently.

**Fix.** Configure the engine explicitly:

```python
engine = create_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,   # cheap SELECT 1 before checkout; eliminates stale conns
    pool_recycle=1800,    # recycle conns older than 30 min
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
)
```

For long-running Streamlit sessions, optionally add
`connect_args={"keepalives": 1, "keepalives_idle": 60}` so OS-level TCP
keepalive kicks in before AWS NAT/firewall drops the socket.

**Validate.** Existing pytest suite stays green; manual idle test (open app,
leave for 30+ minutes, trigger a DB-backed action) no longer drops a stale-
connection error.

## 2. systemd hardening

Covered in detail in [`deployment.md`](deployment.md#systemd-service). The
changes against the current unit:

- Add `MemoryMax=2G`, `MemoryHigh=1500M`, `CPUQuota=200%`, `TasksMax=256`,
  `LimitNOFILE=4096`.
- `Restart=on-failure` instead of `Restart=always`.
- `StartLimitIntervalSec=300` + `StartLimitBurst=5` so a crash loop stops
  filling the journal after five restarts in five minutes.
- `NoNewPrivileges=true`, `ProtectSystem=strict`, `ProtectHome=read-only`,
  `PrivateTmp=true`, `ReadWritePaths=<APP_ROOT>/logs <APP_ROOT>/checkpoints
  <APP_ROOT>/data`.
- `LogRateLimitIntervalSec=10` + `LogRateLimitBurst=200`.
- Optional `EnvironmentFile=-/etc/pain-narratives.env` for per-host tunables.

Validate with `systemd-analyze security pain-narratives` (target exposure
score < 5.0) and a `stress-ng` test to confirm `MemoryMax` kills the service
rather than the EC2 OOM-killing unrelated processes.

## 3. Streamlit caching and session reuse

**Current.** `app.py` stores long-lived objects in `st.session_state`:

```python
st.session_state.openai_client = OpenAIClient(api_key=api_key)
st.session_state.db_manager = DatabaseManager()
```

`session_state` is per-browser-session, so every user spins up their own
`DatabaseManager` (with its own SQLAlchemy engine and pool) and its own
`OpenAIClient`. Localization in `ui/utils/localization.py` also calls
`st.cache_data.clear()` globally whenever language changes — a sledgehammer
that wipes every cached function in the app.

**Fix.** Module-level cached factories using `@st.cache_resource`:

```python
# src/pain_narratives/ui/utils/resources.py (new file)
import streamlit as st
from pain_narratives.core.database import DatabaseManager
from pain_narratives.core.openai_client import OpenAIClient


@st.cache_resource(show_spinner=False)
def get_db_manager() -> DatabaseManager:
    return DatabaseManager()


@st.cache_resource(show_spinner=False)
def get_openai_client(api_key: str | None = None) -> OpenAIClient:
    return OpenAIClient(api_key=api_key) if api_key else OpenAIClient()
```

`cache_resource` returns the same instance to every session. Per-user state
stays in `session_state`; shared singletons move to `cache_resource`.

Replace the global `st.cache_data.clear()` in
`ui/utils/localization.py` with the targeted form:

```python
_load_language_data_cached.clear()    # only this function's cache
```

**Validate.** Open the app in two browser windows as different users; check
`pg_stat_activity` to confirm one connection set is shared across them.
Switch language mid-session and confirm narrative-load functions are not
re-evaluated.

**Risk.** Medium — the session-state references are read across the UI layer;
missing one yields a stale reference. Mitigation: keep `session_state`
populated by reading from the factory on each rerun rather than removing the
attribute entirely.

## 4. Batch runner parallelism

**Current.** The batch loop in
[`src/pain_narratives/batch/processor.py`](../src/pain_narratives/batch/processor.py)
iterates over narratives sequentially with `time.sleep(delay_between_calls)`
(default 1.0 s) between sub-calls. Each narrative does 4 LLM calls
(dimensions + PCS + BPI-IS + TSK-11SV); wall time is dominated by Bedrock
latency, not Python work.

**Fix.** Add an opt-in parallel mode using `concurrent.futures.ThreadPoolExecutor`
with `max_workers=4`. Threads are appropriate because the work is I/O-bound
on boto3 (which releases the GIL during socket reads). Keep `max_workers=1`
as the default so the published baseline reproduces exactly. Across-narrative
parallelism only — do **not** parallelise the 4 sub-calls within a single
narrative; they share retry state and the consecutive-failure counter.

Implementation sketch:

1. Add `max_workers: int = 1` to `BatchConfig`.
2. Add `--max-workers 4` to [`scripts/run_batch_evaluation.py`](../scripts/run_batch_evaluation.py).
3. Extract per-narrative work into `_process_one(idx, row, group_id, user_id)`.
   It must be thread-safe: confirm `DatabaseManager.get_session()` opens a new
   session per call (it does), and that `openai_client` / `_bedrock_client`
   are used only via thread-safe boto3/HTTP calls. Mutate `progress` and the
   `consecutive_failures` counter under a `threading.Lock`.
4. Replace the `for idx, row in narratives_df.iterrows()` block with
   `ThreadPoolExecutor.submit` + `as_completed`.
5. **Critical invariant**: a `BedrockAuthError` from any worker must cancel
   the remaining futures and halt the batch. Use a `threading.Event` and
   check it before each sub-call; on auth failure call
   `executor.shutdown(wait=False, cancel_futures=True)`.

**Validate.** 5-narrative pilot at `--max-workers 4`: confirm 5 successful
rows, 4 `evaluation_results` per experiment, ~1/4 the sequential wall time.
Auth-failure drill: revoke the AWS profile mid-run, confirm the batch stops
within seconds and the checkpoint is written. Reproducibility check: rerun
with `--max-workers 1` against a known-good baseline (modulo LLM
non-determinism).

**Payoff.** Roughly 3-4× wall-time reduction at `max_workers=4`. For 6 runs
total (2 models × 3 reps), saves ~12 hours of clock time on this rebuttal
alone.

**Risk.** Medium-high. The auth-error-halts-batch and consecutive-failure
invariants are easy to break under concurrency. Mitigations: ship behind the
CLI flag, keep `max_workers=1` as the default, add an integration test that
simulates a mid-batch auth failure.
