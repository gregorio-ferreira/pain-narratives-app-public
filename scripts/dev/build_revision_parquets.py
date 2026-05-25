"""Materialise the revision analysis data layer to Parquet.

Writes the following under ``docs/revision/data/processed/``:
- real_152.parquet           - 152 real patients (the subset used for LLM experiments)
- real_41.parquet            - 41 expert-evaluated real-patient subset
- synth_gpt5_aggregated.parquet  - GPT-5 per-narrative aggregate from publication Excel
- synth_gpt5_runs_41.parquet     - GPT-5 per-run for the 41-narrative expert subset
- synth_<model>.parquet      - one Parquet per non-GPT-5 model

Also prints a quick sanity comparison of GPT-5 vs real_152 (MAE / Pearson r)
so we have an immediate read on whether the data layer is internally consistent
with the published findings.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from pain_narratives.analysis import revision_data_layer as dl


def main() -> None:
    print("=" * 80)
    print("Building revision analysis Parquet outputs")
    print("=" * 80)
    dl.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    real_152 = dl.load_real_152()
    p = dl.write_parquet(real_152, "real_152.parquet")
    print(f"  real_152                 -> {p}  ({len(real_152)} rows)")

    real_41 = dl.load_real_41()
    p = dl.write_parquet(real_41, "real_41.parquet")
    print(f"  real_41                  -> {p}  ({len(real_41)} rows)")

    # Excel aggregate (paper-reproduction reference; not used in the cross-model loops).
    gpt5_excel = dl.load_gpt5_synth_aggregated()
    p = dl.write_parquet(gpt5_excel, "synth_gpt5_excel_agg.parquet")
    print(f"  synth_gpt5_excel_agg     -> {p}  ({len(gpt5_excel)} rows)")

    gpt5_runs41 = dl.load_gpt5_synth_runs_41()
    p = dl.write_parquet(gpt5_runs41, "synth_gpt5_runs_41.parquet")
    print(f"  synth_gpt5_runs_41       -> {p}  ({len(gpt5_runs41)} rows)")

    # Every model — including GPT-5 — gets the same DB-parsed long-format Parquet
    # so downstream notebooks can compare them on equal footing.
    for tag, cfg in dl.MODEL_CONFIGS.items():
        if cfg.source != "db":
            continue
        df = dl.load_synth_from_db(tag, cfg.group_ids)
        if df.empty:
            print(f"  synth_{tag}: <no data>")
            continue
        slug = tag.replace("-", "_")
        out = dl.write_parquet(df, f"synth_{slug}.parquet")
        print(f"  synth_{tag:<28} -> {out}  ({len(df)} rows, "
              f"runs={sorted(df['run_number'].unique().tolist())})")

    # Reproducibility check: aggregate each model across its runs, then compare
    # per-narrative against real_152. Reports MAE/RMSE/Pearson r/Spearman ρ.
    print()
    print("=" * 80)
    print("Per-model aggregate vs real_152 (mean across runs)")
    print("=" * 80)
    for tag, cfg in dl.MODEL_CONFIGS.items():
        try:
            df = dl.load_processed(f"synth_{tag.replace('-', '_')}.parquet")
        except FileNotFoundError:
            continue
        agg = df.groupby("narrative_hash", as_index=False)[
            ["pcs_total", "bpi_total_mean", "tsk_total"]
        ].mean()
        print(f"\n  {tag} (n_runs={df['run_number'].nunique()}, n_hashes={len(agg)})")
        for q in ("pcs_total", "bpi_total_mean", "tsk_total"):
            merged = real_152[["narrative_hash", q]].merge(
                agg[["narrative_hash", q]], on="narrative_hash",
                suffixes=("_real", "_synth"),
            )
            r = merged[f"{q}_real"].astype(float).to_numpy()
            s = merged[f"{q}_synth"].astype(float).to_numpy()
            mask = ~(np.isnan(r) | np.isnan(s))
            r, s = r[mask], s[mask]
            mae = float(np.mean(np.abs(r - s)))
            rmse = float(np.sqrt(np.mean((r - s) ** 2)))
            pr, _ = stats.pearsonr(r, s)
            sp, _ = stats.spearmanr(r, s)
            print(f"    {q:<18} n={len(r):3d}  MAE={mae:6.3f}  RMSE={rmse:6.3f}  "
                  f"Pearson={pr:6.3f}  Spearman={sp:6.3f}")


if __name__ == "__main__":
    main()
