# Revision Experiments Plan — ACM HEALTH-2026-0160

**Context.** The reviewers ask for evidence that the AINarratives results are not specific to GPT-5 (R1 #1, R2 #7), that the temperature configuration claim is supported empirically (R1 #2), that prompt sensitivity is reported (R1 #3, R2 #7), and that the codebase is fully reproducible (R3 #1). This plan extends the public repo with multi-provider model support (Bedrock + OpenAI), adds prompt-variant tracking, and defines an experiment matrix that addresses these reviewer concerns in one revision pass.

**Decisions captured (your answers):**

1. Temperature grid: `[0.0, 0.4, 0.8, 1.0]` for all Bedrock models; the asymmetric `1.5` cell runs only on `gpt-4o`.
2. GPT-5 stays as the original baseline at its API-pinned `temperature=1.0` (one data point on the OpenAI side). Temperature sensitivity is studied on Bedrock + `gpt-4o`.
3. Three prompt variants in this revision: `original`, `reworded`, `stricter_grounding`.
4. Branch will be cut **after** the consolidation PR merges to `main`. Until then, this is a planning document.

**Scope this plan does not cover** (acknowledged but for separate work): privacy implications of cloud LLM use (R1 #4), narrative-length lower bound (R1 #5), figure regeneration, expert evaluation re-run, ethical considerations section (R3 #4). Those are paper-text and analysis tasks downstream of the experiments described here.

---

## 1 — Reviewer concern → revision response

| Reviewer | Concern | This plan's response |
|---|---|---|
| R1 #1 | Only GPT-5 evaluated | Add Claude Opus 4.1, Claude Sonnet 4.5, Amazon Nova Pro via Bedrock |
| R1 #2 | Temperature claim unevaluated | Sweep `[0.0, 0.4, 0.8, 1.0]` on all Bedrock models + `[0.0, 0.4, 0.8, 1.0, 1.5]` on `gpt-4o`; report stability metrics |
| R1 #3 | Prompt sensitivity not discussed | Run 3 prompt variants per cell; report variance attributable to prompts vs. models vs. temperature |
| R2 #7 | Broader range of LLM settings | Same experimental matrix, framed in revised paper as "model × temperature × prompt" sensitivity study |
| R3 #1 | Reproducibility / code link | Public repo as the primary artifact, full prompts in `prompts/`, exact request/response logged in `request_response` table per call, model registry with exact `api_id` strings and release dates |

---

## 2 — Model registry (what to evaluate, with capabilities and defaults)

The registry is the central source of truth. Every experiment must resolve a `ModelSpec` from this dict; nothing in the runner should hard-code a model id or temperature.

### 2.1 Models in scope for the revision

| Friendly id | Provider | Bedrock / API id | Release | Why included |
|---|---|---|---|---|
| `gpt-5` | openai | `gpt-5` | 2025-08-07 | Original paper baseline. Pinned at temp=1.0 by the API. |
| `gpt-4o` | openai | `gpt-4o` | 2024-05-13 | Carries the temperature sensitivity study on the OpenAI side; supports temp range [0, 2] so includes the 1.5 cell. |
| `claude-opus-4-1` | bedrock_anthropic | `anthropic.claude-opus-4-1-20250805-v1:0` | 2025-08-05 | Frontier commercial comparator; released two days before GPT-5 (closest temporal match). |
| `claude-sonnet-4-5` | bedrock_anthropic | `anthropic.claude-sonnet-4-5-20250929-v1:0` | 2025-09-29 | Production-grade Claude comparator. |
| `nova-pro` | bedrock_amazon | `amazon.nova-pro-v1:0` | 2024-12-03 | AWS-native commercial baseline; ensures comparison isn't OpenAI-vs-Anthropic only. |
| *(optional)* `llama-4-maverick` | bedrock_meta | `meta.llama4-maverick-17b-instruct-v1:0` | 2025-04 | Open-weight comparator. Defer unless cost budget allows. |

### 2.2 Inference parameters per model

These are the values the registry will pin during the sweep. Where AWS doesn't publish a single "default" value crisply, we simply choose a deterministic value and hold it constant across all models so temperature is the only variable. Max-tokens is sized for the worst-case dimension+questionnaire JSON response.

| Model | Temp default | Temp valid range | Sweep grid (this study) | top_p (held fixed) | top_k (held fixed) | max_tokens | Notes / caveats |
|---|---|---|---|---|---|---|---|
| `gpt-5` | 1.0 (API-fixed) | parameter rejected | `[1.0]` | 1.0 | n/a | 8000 | Reasoning model — `temperature` is not accepted; do not pass it. Use `reasoning_effort` if needed (default is fine). |
| `gpt-4o` | 1.0 | [0.0, 2.0] | `[0.0, 0.4, 0.8, 1.0, 1.5]` | 1.0 | n/a | 4096 | Supports `response_format=json_object`, `logprobs`, `seed` for reproducibility. |
| `claude-opus-4-1` | 1.0 | [0.0, 1.0] | `[0.0, 0.4, 0.8, 1.0]` | 0.999 | 250 | 4096 | Anthropic guidance: do not vary `temperature` and `top_p` simultaneously. We hold `top_p` fixed at 0.999. |
| `claude-sonnet-4-5` | 1.0 | [0.0, 1.0] | `[0.0, 0.4, 0.8, 1.0]` | 0.999 | 250 | 4096 | Same as Opus. |
| `nova-pro` | 0.7 (commonly cited) | (0.0, 1.0] | `[0.0, 0.4, 0.8, 1.0]` | 0.9 | 50 | 4096 | Bedrock docs note `temperature > 0`; we use a small epsilon (e.g. `1e-5`) for the "0.0" cell, or skip the 0.0 cell on Nova and call out the asymmetry. |
| `llama-4-maverick` | 0.5 (commonly cited) | [0.0, 1.0] | `[0.0, 0.4, 0.8, 1.0]` | 0.9 | n/a | 4096 | Bedrock Converse API supports `additionalModelRequestFields` for any provider extras. |

> **Methodological note on "default" values.** The intention of this study is not to compare each model at *its* default — that would conflate model and configuration choice. Instead we hold every parameter except `temperature` and `prompt` fixed at deterministic, study-declared values, so the only variables are model, temperature, and prompt. The registry records both each model's *API default* (for transparency) and the *study fixed value* (the one actually used).

### 2.3 Prompt variants

Three variants live as ordinary YAML files under `src/pain_narratives/config/prompts/` and are loaded by `prompt_id`:

| `prompt_id` | Description | Source |
|---|---|---|
| `original` | Verbatim from the published paper. | Frozen as-is. |
| `reworded` | Same instructions, paraphrased. Word-level changes, no semantic shift. | Manual. |
| `stricter_grounding` | Adds explicit instructions: "answer only what the narrative supports", "if information is missing for a dimension, mark it as unknown". | Manual. |

Each prompt file has a header block with `prompt_id`, `version`, `language`, `description`, and a SHA256 `prompt_hash` (computed by a pre-commit hook so the value is always current). Every experiment record stores the `prompt_id` and `prompt_hash` so a frozen audit trail exists even if the prompt file changes later.

---

## 3 — Architecture changes

The current code is OpenAI-specific (`OpenAIClient` is concrete; `model_provider="openai"` is hard-coded in 6 call sites; no model registry). The refactor introduces a thin abstraction without rewriting the world.

### 3.1 New modules

```
src/pain_narratives/core/
  llm_client.py           NEW — Protocol for all providers
  openai_client.py        EXISTING — refactored to satisfy Protocol
  bedrock_client.py       NEW — uses bedrock-runtime Converse API
  model_registry.py       NEW — ModelSpec dataclass + REGISTRY dict
src/pain_narratives/config/
  prompts/                NEW — prompt YAML files
    original.yaml
    reworded.yaml
    stricter_grounding.yaml
  prompt_loader.py        NEW — load + hash + validate prompts
src/pain_narratives/experiments/
  matrix.py               NEW — generates the (model × temp × prompt) cells
  runner.py               EXISTING — accepts ModelSpec instead of model_str
src/pain_narratives/batch/
  processor.py            EXISTING — same change as runner
```

### 3.2 `LLMClient` protocol (single uniform interface)

```python
# src/pain_narratives/core/llm_client.py
from typing import Protocol, Sequence
from dataclasses import dataclass

@dataclass
class GenerationParams:
    temperature: float | None       # None means "do not pass to API"
    top_p: float
    top_k: int | None
    max_tokens: int
    seed: int | None = None         # OpenAI only; ignored elsewhere
    response_format_json: bool = False

@dataclass
class CompletionResult:
    text: str                       # primary content
    raw_response: dict              # whole API response, persisted
    request_payload: dict           # the exact payload sent, persisted
    usage: dict                     # input/output tokens
    finish_reason: str

class LLMClient(Protocol):
    def create_completion(
        self,
        messages: Sequence[dict[str, str]],
        spec: "ModelSpec",
        params: GenerationParams,
    ) -> CompletionResult: ...
```

Both `OpenAIClient` and `BedrockClient` implement this. The runner asks the registry "give me a client that can serve this `ModelSpec`" and gets the right concrete instance back via a factory:

```python
# src/pain_narratives/core/llm_client.py
def get_client_for(spec: ModelSpec) -> LLMClient:
    if spec.provider == "openai":
        return get_openai_client()
    if spec.provider.startswith("bedrock_"):
        return get_bedrock_client()
    raise ValueError(f"Unknown provider {spec.provider}")
```

### 3.3 `BedrockClient` design (uses Converse API)

The Bedrock **Converse API** (`bedrock-runtime.converse(...)`) is the right integration point. It exposes a uniform message format across Claude, Nova, Llama, and Mistral, and supports `additionalModelRequestFields` for provider-specific extras (e.g., `top_k` on Claude). One client, four providers.

```python
# src/pain_narratives/core/bedrock_client.py
import boto3

class BedrockClient:
    def __init__(self, region: str):
        self._client = boto3.client("bedrock-runtime", region_name=region)

    def create_completion(self, messages, spec, params):
        inference_config = {
            "maxTokens": params.max_tokens,
            "topP": params.top_p,
        }
        if params.temperature is not None:
            inference_config["temperature"] = params.temperature

        # Provider-specific extras
        additional_fields = {}
        if spec.provider == "bedrock_anthropic" and params.top_k is not None:
            additional_fields["top_k"] = params.top_k
        if spec.provider == "bedrock_amazon":
            additional_fields["inferenceConfig"] = {"top_k": params.top_k}
        # (Llama / Mistral don't expose top_k via Converse extras.)

        # Convert OpenAI-style {role, content} list into Bedrock format
        system_msgs = [m["content"] for m in messages if m["role"] == "system"]
        user_assistant = [
            {"role": m["role"], "content": [{"text": m["content"]}]}
            for m in messages if m["role"] != "system"
        ]

        response = self._client.converse(
            modelId=spec.api_id,
            messages=user_assistant,
            system=[{"text": s} for s in system_msgs] if system_msgs else None,
            inferenceConfig=inference_config,
            additionalModelRequestFields=additional_fields or None,
        )
        return CompletionResult(
            text=response["output"]["message"]["content"][0]["text"],
            raw_response=response,
            request_payload={
                "modelId": spec.api_id,
                "messages": user_assistant,
                "system": system_msgs,
                "inferenceConfig": inference_config,
                "additionalModelRequestFields": additional_fields,
            },
            usage={
                "input_tokens": response["usage"]["inputTokens"],
                "output_tokens": response["usage"]["outputTokens"],
            },
            finish_reason=response["stopReason"],
        )
```

### 3.4 `model_registry.py` (the dict the user asked for)

```python
# src/pain_narratives/core/model_registry.py
from dataclasses import dataclass, field
from typing import Literal, Sequence

ProviderName = Literal[
    "openai",
    "bedrock_anthropic",
    "bedrock_amazon",
    "bedrock_meta",
    "bedrock_mistral",
]

@dataclass(frozen=True)
class ModelSpec:
    # Identity
    id: str
    provider: ProviderName
    api_id: str
    release_date: str

    # Capabilities
    supports_temperature: bool = True
    supports_top_p: bool = True
    supports_top_k: bool = False
    supports_response_format_json: bool = False
    supports_seed: bool = False
    supports_logprobs: bool = False

    # Defaults the API itself uses (informational only — for transparency)
    api_default_temperature: float | None = 1.0

    # Values this STUDY pins for non-swept parameters
    study_top_p: float = 1.0
    study_top_k: int | None = None
    study_max_tokens: int = 4096

    # Valid range checks
    temperature_range: tuple[float, float] = (0.0, 1.0)

    # The grid this study sweeps
    sweep_temperatures: Sequence[float] = field(default_factory=lambda: [0.0, 0.4, 0.8, 1.0])

    notes: str = ""

REGISTRY: dict[str, ModelSpec] = {
    "gpt-5": ModelSpec(
        id="gpt-5",
        provider="openai",
        api_id="gpt-5",
        release_date="2025-08-07",
        supports_temperature=False,
        api_default_temperature=1.0,
        study_top_p=1.0,
        study_max_tokens=8000,
        sweep_temperatures=[1.0],          # single point
        notes="Reasoning model. The OpenAI API rejects the temperature parameter; do not pass it.",
    ),
    "gpt-4o": ModelSpec(
        id="gpt-4o",
        provider="openai",
        api_id="gpt-4o",
        release_date="2024-05-13",
        supports_response_format_json=True,
        supports_seed=True,
        supports_logprobs=True,
        api_default_temperature=1.0,
        study_top_p=1.0,
        study_max_tokens=4096,
        temperature_range=(0.0, 2.0),
        sweep_temperatures=[0.0, 0.4, 0.8, 1.0, 1.5],
        notes="Carries the temperature-sensitivity study on the OpenAI side, including temp=1.5.",
    ),
    "claude-opus-4-1": ModelSpec(
        id="claude-opus-4-1",
        provider="bedrock_anthropic",
        api_id="anthropic.claude-opus-4-1-20250805-v1:0",
        release_date="2025-08-05",
        supports_top_k=True,
        api_default_temperature=1.0,
        study_top_p=0.999,
        study_top_k=250,
        study_max_tokens=4096,
        temperature_range=(0.0, 1.0),
        sweep_temperatures=[0.0, 0.4, 0.8, 1.0],
    ),
    "claude-sonnet-4-5": ModelSpec(
        id="claude-sonnet-4-5",
        provider="bedrock_anthropic",
        api_id="anthropic.claude-sonnet-4-5-20250929-v1:0",
        release_date="2025-09-29",
        supports_top_k=True,
        api_default_temperature=1.0,
        study_top_p=0.999,
        study_top_k=250,
        study_max_tokens=4096,
        temperature_range=(0.0, 1.0),
        sweep_temperatures=[0.0, 0.4, 0.8, 1.0],
    ),
    "nova-pro": ModelSpec(
        id="nova-pro",
        provider="bedrock_amazon",
        api_id="amazon.nova-pro-v1:0",
        release_date="2024-12-03",
        supports_top_k=True,
        api_default_temperature=0.7,
        study_top_p=0.9,
        study_top_k=50,
        study_max_tokens=4096,
        temperature_range=(0.00001, 1.0),     # Bedrock requires temp > 0
        sweep_temperatures=[0.00001, 0.4, 0.8, 1.0],
        notes="Nova requires temperature > 0; the '0.0' cell uses 1e-5 as a near-zero proxy.",
    ),
}

# Models referenced by the revision matrix; defined once so the runner can iterate.
REVISION_MODELS = ["gpt-5", "gpt-4o", "claude-opus-4-1", "claude-sonnet-4-5", "nova-pro"]
```

### 3.5 Where the `BedrockConfig` already exists

`src/pain_narratives/config/settings.py` already defines `BedrockConfig` with `aws_access_key`, `aws_secret_key`, `aws_region`. The integration just needs `boto3` to read it; **no schema change to `config.yaml.example`** is needed beyond uncommenting the existing `bedrock:` block. (Recommendation: prefer IAM roles / `~/.aws/credentials` over inlining keys in `config.yaml`. The settings class can fall back to whatever `boto3.client(...)` finds in the standard credential chain.)

### 3.6 `experiments/matrix.py` — generates the cells

```python
# src/pain_narratives/experiments/matrix.py
from dataclasses import dataclass
from itertools import product
from .model_registry import REGISTRY, REVISION_MODELS

@dataclass
class ExperimentCell:
    model_id: str
    temperature: float
    prompt_id: str
    repetition: int

def generate_cells(
    model_ids: list[str] = None,
    prompt_ids: list[str] = None,
    repetitions: int = 1,
) -> list[ExperimentCell]:
    model_ids = model_ids or REVISION_MODELS
    prompt_ids = prompt_ids or ["original", "reworded", "stricter_grounding"]
    cells: list[ExperimentCell] = []
    for mid, pid, rep in product(model_ids, prompt_ids, range(repetitions)):
        spec = REGISTRY[mid]
        for temp in spec.sweep_temperatures:
            cells.append(ExperimentCell(mid, temp, pid, rep))
    return cells
```

This makes the matrix generator the single thing to test, and lets you say in the paper exactly how many cells exist by calling `len(generate_cells())`.

---

## 4 — Database additions

The current schema stores temperature inside `request_response.request_json`. That works but makes per-temperature analytics painful (you'd be JSON-extracting on every query). For a clean revision, add three first-class columns on `experiments_list`:

```sql
ALTER TABLE pain_narratives_app.experiments_list
  ADD COLUMN temperature       DOUBLE PRECISION,
  ADD COLUMN prompt_id         VARCHAR(64),
  ADD COLUMN prompt_hash       VARCHAR(64);
```

And one alembic migration:

```python
# new revision: add_revision_experiment_columns
# down_revision: 0000000dedup
op.add_column('experiments_list', sa.Column('temperature', sa.Float(), nullable=True), schema=SCHEMA)
op.add_column('experiments_list', sa.Column('prompt_id', sa.String(64), nullable=True), schema=SCHEMA)
op.add_column('experiments_list', sa.Column('prompt_hash', sa.String(64), nullable=True), schema=SCHEMA)
```

`SQLModel` companion update in `models_sqlmodel.py`:

```python
class ExperimentList(SQLModel, table=True):
    # ...
    temperature: Optional[float] = None
    prompt_id: Optional[str] = Field(default=None, max_length=64)
    prompt_hash: Optional[str] = Field(default=None, max_length=64)
```

Six call sites currently pass `"model_provider": "openai"` literally. Each becomes `spec.provider`. The runner also writes `temperature`, `prompt_id`, `prompt_hash` into the `experiments_list` row — these are populated by the matrix cell, so the link `cell → experiment row → request_response` is bidirectional.

The `extra_description` JSON column stays useful for free-form tags ("rebuttal-2026", "prompt-sensitivity", etc.) but the indexed columns above are the ones used for analytics.

---

## 5 — Experimental matrix size and cost

### 5.1 Matrix size

Per narrative, one repetition:

| Model | Temps | Prompts | Cells |
|---|---|---|---|
| `gpt-5` | 1 | 3 | 3 |
| `gpt-4o` | 5 | 3 | 15 |
| `claude-opus-4-1` | 4 | 3 | 12 |
| `claude-sonnet-4-5` | 4 | 3 | 12 |
| `nova-pro` | 4 | 3 | 12 |
| **Total per narrative** | | | **54** |

For 152 narratives × 1 repetition: **8,208 calls**. With 3 repetitions for stability (recommended): **24,624 calls**. Each "call" produces dimensions evaluation + 3 questionnaires (PCS / BPI / TSK), so multiply API hits accordingly if those are separate calls in your code (check `core/questionnaire_runner.py`).

### 5.2 Token budget per call

Approximate per-call token usage in the existing experiments (from the published paper's figures and your token-count script):

| Component | Input tokens | Output tokens |
|---|---|---|
| System prompt + dimensions | ~1,200 | — |
| Narrative | ~350 (median) | — |
| Dimension evaluation output | — | ~600 |
| Persona generation | ~1,500 | ~400 |
| Questionnaire (×3: PCS, BPI, TSK) | ~2,000 each | ~300 each |
| **Total per narrative pass** | **~10,500 input** | **~2,400 output** |

### 5.3 Cost per model (May 2026 published prices, USD per 1M tokens)

| Model | Input $/1M | Output $/1M | Cost / narrative pass | Cost / 152 narratives × 1 rep |
|---|---|---|---|---|
| `gpt-5` | $1.25 | $10.00 | ~$0.04 | ~$6 |
| `gpt-4o` | $2.50 | $10.00 | ~$0.05 | ~$8 |
| `claude-opus-4-1` | $15.00 | $75.00 | ~$0.34 | ~$52 |
| `claude-sonnet-4-5` | $3.00 | $15.00 | ~$0.07 | ~$11 |
| `nova-pro` | $0.80 | $3.20 | ~$0.02 | ~$3 |

> Prices change. Check the current AWS Bedrock pricing page and OpenAI pricing page before you actually run.

**Full matrix cost estimate** for 1 repetition (152 narratives):

```
gpt-5:               1 cell  ×  $6  = $6
gpt-4o:              5 cells ×  $8  = $40
claude-opus-4-1:     4 cells ×  $52 = $208
claude-sonnet-4-5:   4 cells ×  $11 = $44
nova-pro:            4 cells ×  $3  = $12
× 3 prompt variants  ×3              = (already factored)
Subtotal             1 rep            ~$310
× 3 repetitions                     ~$930
```

**~$900–1,000** for the full matrix at 3 repetitions. **Claude Opus 4.1 is ~70% of the bill.** If budget is tight, drop Opus to `claude-sonnet-4-5` only and the bill falls below $300.

### 5.4 Runtime estimate

At ~3 seconds median per Bedrock call and ~8 seconds for OpenAI reasoning calls, with sequential execution: ~24,000 calls × ~5 sec = ~33 hours. With 5 parallel workers: ~7 hours. Plan for **one weekend** to run the full matrix end-to-end. Use `scripts/run_batch_evaluation.py` with `--resume` so a transient failure doesn't lose progress (the existing checkpoint logic is already there).

---

## 6 — Implementation phases

Ordered to ship in small, reviewable PRs.

### Phase 1 — Dependencies and config (½ day)

1. `uv add boto3` and `uv add botocore`. Verify `pyproject.toml` and `uv.lock` updated.
2. Confirm `BedrockConfig` in `settings.py` reads `bedrock:` block from `config.yaml`. Add a `bedrock` section to `config.yaml.example`.
3. Document IAM role / credentials chain in `docs/revision/AWS_BEDROCK_SETUP.md` (region, model access, AssumeRole, etc.).
4. **Pre-flight**: in the AWS console, request access for each Bedrock model in your chosen region (us-east-1 is most common — Frankfurt eu-central-1 has some models but not all).

### Phase 2 — Model registry + LLMClient protocol (1 day)

1. Create `src/pain_narratives/core/model_registry.py` exactly as in §3.4.
2. Create `src/pain_narratives/core/llm_client.py` with the Protocol and `GenerationParams` / `CompletionResult` dataclasses.
3. Refactor `src/pain_narratives/core/openai_client.py` so its `create_completion` matches the Protocol (signature + return type).
4. Add unit tests: `tests/test_model_registry.py` (validates every entry's ranges, sweep grids in range, no duplicate ids), `tests/test_llm_client_protocol.py` (mock both clients return well-formed `CompletionResult`).

### Phase 3 — BedrockClient (1–2 days)

1. Create `src/pain_narratives/core/bedrock_client.py` (Converse API).
2. Integration tests against AWS staging account: one call per model in the registry, asserting `CompletionResult.text` is non-empty and `usage` parses. Mark these tests `@pytest.mark.integration` and skip in CI.
3. Add a `scripts/dev/test_bedrock_smoke.py` CLI: `python scripts/dev/test_bedrock_smoke.py --model claude-opus-4-1 --temperature 0.4` to exercise the end-to-end path during development.

### Phase 4 — Prompt registry (½ day)

1. Create `src/pain_narratives/config/prompts/{original,reworded,stricter_grounding}.yaml` with header (id, version, language, description, hash) + body (system_role + base_prompt + dimensions).
2. Create `src/pain_narratives/config/prompt_loader.py`: load, validate, and compute SHA256 over the body.
3. Pre-commit hook to refresh `prompt_hash` on save.

### Phase 5 — DB schema + runner refactor (1 day)

1. Add alembic migration `add_revision_experiment_columns` per §4.
2. Update `ExperimentList` SQLModel with `temperature`, `prompt_id`, `prompt_hash`.
3. Refactor `ExperimentRunner.run_single_experiment` to take a `ModelSpec` and `PromptVariant` instead of a model string.
4. Refactor `BatchProcessor` similarly.
5. Replace all 6 hard-coded `"model_provider": "openai"` literals with `spec.provider`.

### Phase 6 — Matrix generator + CLI (½ day)

1. Create `src/pain_narratives/experiments/matrix.py` per §3.6.
2. Update `scripts/run_batch_evaluation.py` so `--models`, `--prompts`, `--temperatures` are optional; if omitted, the full revision matrix runs. Add `--matrix revision` shorthand for the published configuration.
3. Update `Makefile`: add `revision-experiments-dry-run` and `revision-experiments-run` targets.

### Phase 7 — End-to-end smoke + small pilot (1 day)

1. Run a **3-narrative pilot** through the full matrix on a non-prod DB: `--limit 3 --matrix revision`.
2. Verify: each cell produces `(experiments_list_row, request_response_row, evaluation_results_row)` with correct `model_provider`, `model`, `temperature`, `prompt_id`, `prompt_hash`. Manually inspect 1 row per provider.
3. Pull token / cost numbers from the smoke run; sanity-check against §5.3 estimates.

### Phase 8 — Full run (over a weekend)

1. `make revision-experiments-run REPETITIONS=3` against prod DB.
2. Monitor via `sql/batch_progress.sql`. Resume on failure.
3. Generate consolidated outputs via the existing `make publication` pipeline (the publication notebooks already iterate over all repetitions of a `experiments_group_id`).

### Phase 9 — Analysis notebooks (separate effort, parallel)

A new notebook `notebooks/07_revision_model_temperature_prompt_analysis.ipynb` produces:

- Pearson r and RMSE per (model, temperature, prompt) cell vs. real responses.
- ANOVA decomposition: variance attributable to model vs. temperature vs. prompt vs. residual. (Directly responds to R1 #2 and R1 #3.)
- Pairwise post-hoc model comparison (Tukey HSD) at temp=1.0, prompt=original.
- Stability score per model: standard deviation of repeated runs at fixed (temp, prompt).

Out of scope for this implementation plan; flagged so the data shape stays consistent with what that notebook will need.

---

## 7 — Risk register

| Risk | Likelihood | Mitigation |
|---|---|---|
| Bedrock model access not granted in target region | medium | Phase 1 pre-flight — request access *before* writing any code. |
| Nova rejects `temperature=0.0` | high | Registry ships with `1e-5` proxy; document the asymmetry in the paper. |
| GPT-5 API changes — temp parameter newly accepted or rejected | low | `supports_temperature=False` is a feature-flag; flip and re-run if it changes. |
| Bedrock rate limits during full run | medium | Converse API calls are subject to per-account TPM. Use exponential backoff in `BedrockClient`; the existing batch processor already retries. |
| Cost overrun on Opus 4.1 | medium | Drop Opus to Sonnet only if pilot exceeds $80 for 3 narratives (well above the §5.3 estimate). |
| Prompt hash drift breaks audit trail | low | Pre-commit hook + tests asserting hash matches body. |
| Mid-experiment alembic migration on prod | low | Apply migration as part of the consolidation merge so it's already there before experiments run. |

---

## 8 — Reviewer response framing (proposed text)

> **R1 #1, R2 #7 — model breadth:** "We agree that the original evaluation was limited to a single GPT-5 configuration. In this revision we extend the evaluation to four additional commercially available large language models, accessed through Amazon Bedrock and OpenAI. We selected models available at the time of the original GPT-5 experiments (August 2025) to preserve temporal comparability: Claude Opus 4.1 (released 2025-08-05), Claude Sonnet 4.5 (2025-09-29), Amazon Nova Pro (2024-12-03), and gpt-4o (2024-05-13). The full model registry — including exact API identifiers, release dates, and inference parameters — is published in the public code repository. The original GPT-5 baseline is retained."
>
> **R1 #2, R2 #7 — temperature:** "Each model except GPT-5 was evaluated at four temperature settings (0.0, 0.4, 0.8, 1.0); gpt-4o was additionally evaluated at 1.5 because the OpenAI API admits values up to 2.0. GPT-5 was retained at the API-fixed default because the OpenAI API rejects the temperature parameter for reasoning models. Table N reports stability metrics across temperature; Figure M decomposes prediction variance attributable to model, temperature, and prompt via ANOVA."
>
> **R1 #3 — prompt sensitivity:** "We evaluate each (model, temperature) cell under three prompt variants: the original published prompt (verbatim), a minimally reworded version with no semantic change, and a stricter grounding variant that explicitly instructs the model to refuse inferences not supported by the narrative. Variance attributable to prompt choice is reported alongside model and temperature variance."
>
> **R3 #1 — reproducibility:** "All prompt templates are versioned YAML files in `src/pain_narratives/config/prompts/`, hashed via SHA256 with the hash recorded on every experiment row. Each LLM request and response is persisted in full in the `request_response` table. The exact code commit (`repo_sha`) is recorded per experiment. The model registry pins exact API identifiers and release dates so a third party can reproduce the matrix verbatim."

---

## 9 — Hand-off checklist for Claude Code

When the consolidation PR is merged and you open Claude Code on this branch:

- [ ] Confirm AWS Bedrock model access requested in the target region for all 4 Bedrock models
- [ ] Phase 1 — `uv add boto3 botocore`, update `config.yaml.example`, write `docs/revision/AWS_BEDROCK_SETUP.md`
- [ ] Phase 2 — implement `model_registry.py`, `llm_client.py`, refactor `openai_client.py` to Protocol
- [ ] Phase 3 — implement `bedrock_client.py`, integration test suite, smoke CLI
- [ ] Phase 4 — author 3 prompt variants, prompt loader, pre-commit hash hook
- [ ] Phase 5 — alembic migration, SQLModel update, runner / batch processor refactor
- [ ] Phase 6 — matrix generator, CLI flags, Makefile targets
- [ ] Phase 7 — 3-narrative pilot on staging DB, verify all rows + provenance
- [ ] Phase 8 — full run with 3 repetitions, monitor via `sql/batch_progress.sql`
- [ ] Open PR per phase or a single squashed PR — your call; phases 1-4 are independent of each other and can land in parallel; 5-8 must serialize.

**Time estimate:** 6–8 working days for an experienced developer (Phases 1–7), then weekend wall-clock for Phase 8. Phase 9 (analysis notebook) is a separate ~3-day effort.
