# Experiments and Batch Runs

AINarratives groups repeated model evaluations into experiment groups. The
Streamlit UI manages interactive workflows; `scripts/run_batch_evaluation.py`
handles long-running batch runs.

## Concepts

| Concept | Meaning |
|---|---|
| Narrative | One patient narrative row in the database. |
| Experiment group | A prompt/model configuration owned by a user. |
| Experiment row | One model evaluation for one narrative in one group. |
| Run number | Repetition index when the same narrative set is evaluated multiple times. |
| Prompt version | Versioned prompt bundle used by a batch, for example `simplified_v1`. |

## Running a Batch

Inspect options first:

```bash
uv run python scripts/run_batch_evaluation.py --help
```

Typical repeated run from existing groups:

```bash
uv run python scripts/run_batch_evaluation.py \
  --from-groups 38,39,40 \
  --run-number 1 \
  --model gpt-5-mini \
  --model-provider openai \
  --prompt-version simplified_v1 \
  --description "Revision analysis run 1" \
  --consecutive-failure-threshold 5 \
  --yes
```

For Bedrock-backed models, also pass provider, model id, region/profile, and
thinking options when applicable.

## Checkpoints and Resume

Batch checkpoints are written under `checkpoints/` and are ignored by git. They
record processed narrative IDs so interrupted batches can resume:

```bash
uv run python scripts/run_batch_evaluation.py \
  --resume \
  --checkpoint checkpoints/<checkpoint-name>.json \
  ...
```

Do not commit checkpoints. They are local run-state, not reproducibility
documentation.

## Prompt Versions

Prompt versions make repeated runs interpretable. The runner stores
`prompt_version` on `experiments_list`; analysis code should filter or group by
that value when comparing runs.

Prompt files live under `src/pain_narratives/config/`.

## Validation

After a batch, verify:

- Expected number of `experiments_list` rows.
- `succeeded = true` and `parsed_answers = true` for completed experiments.
- Four `evaluation_results` rows per experiment: dimensions, PCS, BPI-IS, and
  TSK-11SV.
- Provider-specific token/reasoning metadata is populated when expected.

Live database checks require private configuration and are skipped in normal
test runs.
