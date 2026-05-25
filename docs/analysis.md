# Analysis Workflows

The repository includes reusable notebooks and scripts for producing research
tables and figures. Generated outputs are ignored so public commits stay small
and free of private data.

## Notebooks

Tracked notebooks live under `notebooks/`. They should be committed without
executed outputs unless an output is intentionally part of documentation.

Use:

```bash
make list-notebooks
make run-notebooks
make consolidate-tables
```

Generated files land under `notebooks/outputs/`, which is ignored.

## Revision Data Layer

`pain_narratives.analysis.revision_data_layer` provides reusable loaders for
multi-model analysis data. It can:

- Read private workbook inputs when available.
- Read model outputs from the live application database.
- Write derived Parquet files under `docs/revision/data/processed/`.

The private inputs and generated Parquet files are intentionally ignored. Public
documentation should describe how to recreate them, not commit them.

Build derived Parquets:

```bash
uv run python scripts/dev/build_revision_parquets.py
```

Run cross-model notebooks:

```bash
cd notebooks
uv run jupyter nbconvert --to notebook --execute --inplace \
  07_cross_model_comparison.ipynb \
  08_dimension_questionnaire_correlations.ipynb
```

Clear notebook outputs before committing.

## Reusable Scripts

| Script | Purpose |
|---|---|
| `scripts/dev/build_narratives_inventory.py` | Creates metadata-only narrative inventory. |
| `scripts/dev/build_revision_parquets.py` | Materializes private revision-analysis Parquets. |
| `scripts/dev/build_revision_workbook.py` | Combines generated CSV outputs into a private workbook. |
| `scripts/dev/build_synthdim_vs_real_quest.py` | Produces additional dimension-vs-questionnaire analysis outputs. |

Generated CSV/XLSX/PDF/Parquet outputs remain ignored.

## Safe Public Data

`docs/revision/narratives_inventory.csv` is tracked because it contains only
counts, hashes, token counts, and provenance flags. It contains no narrative
text.
