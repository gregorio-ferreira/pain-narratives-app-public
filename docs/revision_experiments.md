# Revision Experiments — ACM HEALTH-2026-0160

Active execution plan for the rebuttal experiments. Two new reasoning models
(DeepSeek-R1, Claude Sonnet 4.5 with extended thinking) evaluated on the
152-narrative ACM baseline at three repetitions each, using simplified
answer-only prompts. The original GPT-5 baseline (groups 38, 39, 40) is **not**
rerun.

## Decision summary

The first plan envisaged an 8-model × 4-temperature × 3-prompt sweep. After
two rounds of team review the scope was reduced to the two reasoning models
above. Rationale:

- The strongest reviewer concern (R1#1) is whether the GPT-5 results
  generalise. GPT-5, DeepSeek-R1, and Claude Sonnet 4.5 (with thinking) are
  three reasoning models from three vendors — the strongest "not GPT-5-specific"
  claim available on Bedrock.
- Temperature is not a tunable parameter for these models (GPT-5 rejects it,
  Claude with thinking rejects non-default values, DeepSeek recommends 0.6).
  The rebuttal frames each model as running at its provider-specified
  operating point.
- Prompt sensitivity is explicitly out of scope; we use one simplified prompt
  set (`simplified_v1`) and disclose the limitation.
- Expected spend: ~$45 (plan for ~$70; worst plausible ~$110). Wall time:
  ~3 hours per model sequentially, ~1.5 hours in parallel.

| Dimension | Value |
|---|---|
| Models | DeepSeek-R1 (Bedrock) + Claude Sonnet 4.5 with extended thinking (Bedrock); GPT-5 baseline already in DB |
| Temperature | Vendor-pinned: GPT-5 = 1.0 (API-fixed), R1 = 0.6 (recommended), Sonnet+thinking = default only |
| Prompts | One simplified set (`simplified_v1`), structured answers only |
| Repetitions | 3 per new model |
| Narratives | 152 (groups 38, 39, 40) |
| Total calls | ~4,560 (152 × 5 sub-calls × 3 reps × 2 models) |

## Reviewer concern → response

| Reviewer | Concern | Addressed? | How |
|---|---|---|---|
| R1#1 | Only GPT-5 evaluated | Yes | DeepSeek-R1 + Claude Sonnet 4.5 with thinking; three vendors, three reasoning models. |
| R1#2 | Temperature claim unevaluated | Partially | All three models are pinned by their provider; rebuttal frames this directly. |
| R1#3 | Prompt sensitivity | Not addressed | Acknowledged as a limitation; offered as future work. |
| R2#5 | Mixed quantitative vs experts | Yes | Two new models' agreement with humans computed on the 40-narrative subset; 3 reps support stability claims. |
| R2#7 | Broader range of LLM settings | Partially | Two additional models from two additional vendors. Reasoning-model parameters are vendor-determined. |
| R3#1 | Reproducibility | Yes | Public repo; exact model IDs; simplified prompts versioned at [`src/pain_narratives/config/simplified_v1_prompts.yaml`](../src/pain_narratives/config/simplified_v1_prompts.yaml); full request/response logged in DB. |

## The simplified prompt

Because the rebuttal does not use human evaluators to score LLM explanations,
the LLM no longer needs to produce them. The simplified prompt strips
explanation / reasoning text from every sub-call and returns only structured
answer values. The persona generation step is unchanged because the persona
text is structurally required as input to the questionnaire steps.

System prompt (one paragraph):

> *"You are a clinical assistant analysing a chronic-pain narrative. Return
> only the structured fields in the response schema. Do not include
> explanations, justifications, or commentary outside the schema. If a value
> cannot be determined from the narrative, return `null`."*

The prompt is versioned as `simplified_v1` in
[`src/pain_narratives/config/simplified_v1_prompts.yaml`](../src/pain_narratives/config/simplified_v1_prompts.yaml).

## Cost model

Per-1M-token Bedrock pricing (May 2026):

| Model | Input $/1M | Output $/1M |
|---|---:|---:|
| `deepseek-r1` | $1.35 | $5.40 |
| `claude-sonnet-4-5` | $3.00 | $15.00 |

Output token counts include the reasoning / thinking trace, which both
vendors bill as output.

| Model | Input | Output (visible + trace) | Per-pass | 152 × 3 reps |
|---|---:|---:|---:|---:|
| `deepseek-r1` | ~10,500 | ~2,000 | $0.025 | ~$11 |
| `claude-sonnet-4-5` (thinking, 8K budget) | ~10,500 | ~3,000 | $0.077 | ~$35 |
| **Total** | | | | **~$46** |

| Output trace assumption | R1 total | Sonnet total | Combined |
|---|---:|---:|---:|
| Conservative | $10 | $25 | $35 |
| **Mid (estimate)** | $11 | $35 | $46 |
| High | $16 | $50 | $66 |
| Worst plausible | $26 | $80 | $106 |

## Database schema

`experiments_list` has two columns added by alembic head `2026051100rev`:

- `prompt_version` — set to `simplified_v1` for revision experiments; existing
  GPT-5 baseline rows can be backfilled with `'original'`.
- `reasoning_tokens` — aggregate chain-of-thought token count per experiment.

Both are nullable and additive; the existing app keeps working unchanged.

## Running the experiments

All commands assume `cd /opt/pain-narratives-app-public` and a working
Bedrock auth setup (see [`deployment.md`](deployment.md)).

### 1. Re-confirm scope

```bash
PGPASSWORD=<pw> psql -h <rds> -U aid4s -d ai-for-society -p 5432 \
  -c "SELECT COUNT(DISTINCT narrative_id) FROM pain_narratives_app.experiments_list
       WHERE experiments_group_id IN (38, 39, 40);"
# expect: 152
```

### 2. Pilot (1 narrative × 2 models, ~$0.10)

```bash
uv run python scripts/dev/test_revision_pilot.py
```

Confirms `parse_answers` handles the two-block reasoning + answer response,
`request_response.response_json` contains both traces, the new columns
populate correctly, and (for Sonnet) the request omits `temperature`, `top_p`,
`top_k` when thinking is enabled.

### 3. Full runs, in `tmux`

DeepSeek-R1 — repeat for runs 2, 3, 4:

```bash
tmux new -s deepseek-r1
mkdir -p logs
uv run python scripts/run_batch_evaluation.py \
  --from-groups 38,39,40 \
  --run-number 2 \
  --model us.deepseek.r1-v1:0 \
  --model-provider bedrock_deepseek \
  --prompt-version simplified_v1 \
  --temperature 0.6 \
  --bedrock-profile mfa \
  --bedrock-region us-east-1 \
  --description "Revision Run 2 — DeepSeek-R1 simplified_v1" \
  --consecutive-failure-threshold 5 \
  --yes 2>&1 | tee logs/r1-run2.log
# Ctrl-b d to detach; tmux attach -t deepseek-r1 to resume.
```

Claude Sonnet 4.5 with thinking — note the model id and the omitted
`--temperature`:

```bash
uv run python scripts/run_batch_evaluation.py \
  --from-groups 38,39,40 \
  --run-number 2 \
  --model us.anthropic.claude-sonnet-4-5-20250929-v1:0 \
  --model-provider bedrock_anthropic \
  --thinking-enabled \
  --thinking-budget-tokens 8000 \
  --prompt-version simplified_v1 \
  --bedrock-profile mfa \
  --bedrock-region us-east-1 \
  --description "Revision Run 2 — Sonnet 4.5 thinking" \
  --consecutive-failure-threshold 5 \
  --yes 2>&1 | tee logs/sonnet-run2.log
```

Monitor:

```bash
# From your laptop
ssh -t ec2-user@<host> "tail -f /opt/pain-narratives-app-public/logs/r1-run2.log"

# Or via SQL — count completed experiments in the current run group
psql ... -c "SELECT COUNT(*) FROM pain_narratives_app.experiments_list
              WHERE experiments_group_id = <new-group-id>;"
```

### 4. What "good" looks like

Per run:

- 152 rows in `experiments_list` with the new `experiments_group_id`
- `succeeded = true` and `parsed_answers = true` on each
- `reasoning_tokens > 0`
- Four `evaluation_results` rows per experiment with `result_type ∈
  {dimensions, PCS, BPI-IS, TSK-11SV}`

If `succeeded = false` on more than ~5% of rows, stop and inspect — likely
either a JSON-parse error against the simplified schema or rate-limit warnings.

## Hardening already baked into the runner

- **Pre-flight** refuses to start the batch if the Bedrock bearer token has
  less than two hours remaining. No-op with IAM-role auth.
- **Per-call retries** with exponential backoff for transient Bedrock errors
  (503, throttling, server-side). Auth and model-validation errors raise
  immediately so the batch halts cleanly.
- **Consecutive-failure tripwire** (default 5) aborts the batch with a clear
  log line on a contiguous run of narrative failures — a useful signal that
  something systemic is wrong.
- **Per-run checkpoints** auto-named at `checkpoints/<model>-<description>.json`
  so different runs don't collide. `--resume` picks up exactly where the last
  save was.
- **`reasoning_tokens`** is recorded per experiment, so the post-hoc cost
  reconstruction in the analysis notebook is exact.

## Acceptance criteria

- [ ] All three R1 repetitions complete with 152/152 successful narratives.
- [ ] All three Sonnet-with-thinking repetitions complete with 152/152.
- [ ] `experiments_list` shows 6 new groups (3 × R1 + 3 × Sonnet), each with
      152 rows, `reasoning_tokens > 0`, `prompt_version = 'simplified_v1'`.

## Analysis notebook

A new notebook `notebooks/07_reasoning_models_revision.ipynb` covers:

1. Pairwise comparison (MAE, Pearson r, RMSE) between GPT-5, R1, and Sonnet
   4.5 with thinking across all 152 narratives, per dimension and per
   questionnaire.
2. Each model's agreement with the human ground truth on the 40-narrative
   subset.
3. Per-model stability across the 3 repetitions (ICC, per-cell stdev).
4. Cost reconstruction from `reasoning_tokens × $/1M`.
5. Cross-model agreement: do reasoning models agree with each other more than
   with humans?
6. Tables and figures for the rebuttal text.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `AccessDeniedException: Bearer Token has expired` mid-run | 12h short-term Bedrock key expired | Refresh `config.yaml`; rerun with `--resume`. Move to instance-profile auth to eliminate. |
| `AccessDeniedException: You don't have access to the model with the specified model ID` | Model access not granted in `us-east-1` | AWS Console → Bedrock → Model access → request access. Anthropic can take longer than other vendors. |
| `ValidationException: temperature may only be set to 1 when thinking is enabled` | `--temperature` and `--thinking-enabled` passed together | Drop `--temperature` for the Sonnet-with-thinking run. |
| Sonnet thinking budget exhausted | `budget_tokens=8000` too small for some narratives | Raise to 16000; monitor `finish_reason` for `length`. |
| Rate-limit errors on Sonnet | Thinking-mode TPM quota is separate from non-thinking | Reduce `--max-workers` or pause briefly between repetitions. |
| Alembic head is not `2026051100rev` | Schema drift | `uv run alembic upgrade head`. Do not downgrade past `260d578db51b` / `47f5ef239b72` / `bad99e59d04b` — see [`architecture.md`](architecture.md#alembic-state). |
