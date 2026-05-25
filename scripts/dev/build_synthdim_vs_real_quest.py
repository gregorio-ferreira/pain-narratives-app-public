"""Standalone analysis: synthetic LLM dimension scores vs real patient questionnaire totals.

Produces two CSV tables + two PDF figures:

- T10e_synthdim_vs_real_quest.csv
    Per (model, dimension, real_questionnaire): Spearman rho with percentile-bootstrap
    95% CI, raw p, BH-FDR-corrected p, significance marker. 10 cells per model x 3 models = 30 rows.

- T10f_synthdim_realvalidity_cross_model.csv
    Cross-model paired bootstrap on rho_real anchored on GPT-5. Answers
    "is GPT-5's synthetic-dimension prediction of real questionnaires significantly
    different from R1's / Sonnet's?". 10 cells x 2 non-anchor models = 20 rows.

- 08_fig4_synthdim_vs_real_heatmap.pdf
    2x5 heatmap per model on rho_real (one panel per model).

- 08_fig5_synthdim_vs_real_forest.pdf
    Forest plot of rho_real with 95% CI per (model, dimension, questionnaire).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from statsmodels.stats.multitest import multipletests
import matplotlib.pyplot as plt
import seaborn as sns

REPO = Path(__file__).resolve().parents[2]
from pain_narratives.analysis import revision_data_layer as dl

OUT_DIR = REPO / "notebooks" / "outputs" / "revision"
FIG_DIR = OUT_DIR / "figures"
OUT_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR.mkdir(parents=True, exist_ok=True)

MODELS = ["gpt-5", "deepseek-r1", "claude-sonnet-4-5-thinking"]
ANCHOR = "gpt-5"
DIMS = ["severidad_score", "discapacidad_score"]
REAL_QUESTS = [
    "pcs_total",
    "bpi_total_mean",
    "bpi_interference_mean",
    "bpi_intensity_mean",
    "tsk_total",
]
BOOT_ITERS = 2000
CROSS_BOOT_ITERS = 5000
RNG_SEED = 42

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

real = dl.load_processed("real_152.parquet")
real = real[["narrative_hash"] + REAL_QUESTS].copy()

synth_agg: dict[str, pd.DataFrame] = {}
for tag in MODELS:
    slug = tag.replace("-", "_")
    df = dl.load_processed(f"synth_{slug}.parquet")
    synth_agg[tag] = df.groupby("narrative_hash", as_index=False)[DIMS].mean()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def spearman_boot_ci(x, y, n_boot=BOOT_ITERS, seed=RNG_SEED):
    rng = np.random.default_rng(seed)
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    mask = ~(np.isnan(x) | np.isnan(y))
    x, y = x[mask], y[mask]
    n = len(x)
    if n < 4:
        return {"rho": np.nan, "p_raw": np.nan, "ci_lo": np.nan, "ci_hi": np.nan, "n": n}
    rho, p = spearmanr(x, y)
    rx = pd.Series(x).rank(method="average").to_numpy()
    ry = pd.Series(y).rank(method="average").to_numpy()
    idx = rng.integers(0, n, size=(n_boot, n))
    rxb = rx[idx]
    ryb = ry[idx]
    rxb = rxb - rxb.mean(axis=1, keepdims=True)
    ryb = ryb - ryb.mean(axis=1, keepdims=True)
    num = (rxb * ryb).sum(axis=1)
    den = np.sqrt((rxb ** 2).sum(axis=1) * (ryb ** 2).sum(axis=1))
    boots = np.where(den > 0, num / den, np.nan)
    lo, hi = np.nanpercentile(boots, [2.5, 97.5])
    return {"rho": float(rho), "p_raw": float(p),
            "ci_lo": float(lo), "ci_hi": float(hi), "n": int(n)}


def sig_mark(p):
    if pd.isna(p):
        return ""
    if p < 0.001:
        return "***"
    if p < 0.01:
        return "**"
    if p < 0.05:
        return "*"
    return ""


def paired_bootstrap(df_a, df_b, x_var, y_var, n_boot=CROSS_BOOT_ITERS, seed=RNG_SEED):
    rng = np.random.default_rng(seed)
    merged = (df_a[["narrative_hash", x_var, y_var]]
              .merge(df_b[["narrative_hash", x_var, y_var]],
                     on="narrative_hash", suffixes=("_a", "_b"))
              .dropna())
    n = len(merged)
    if n < 4:
        return {"delta_rho": np.nan, "ci_lo": np.nan, "ci_hi": np.nan,
                "p_bootstrap": np.nan, "n": n}
    xa = merged[f"{x_var}_a"].to_numpy()
    ya = merged[f"{y_var}_a"].to_numpy()
    xb = merged[f"{x_var}_b"].to_numpy()
    yb = merged[f"{y_var}_b"].to_numpy()
    deltas = np.empty(n_boot)
    for i in range(n_boot):
        idx = rng.integers(0, n, n)
        ra, _ = spearmanr(xa[idx], ya[idx])
        rb, _ = spearmanr(xb[idx], yb[idx])
        deltas[i] = ra - rb
    mean = float(np.nanmean(deltas))
    lo, hi = np.nanpercentile(deltas, [2.5, 97.5])
    p = 2.0 * min((deltas > 0).mean(), (deltas < 0).mean())
    return {"delta_rho": mean, "ci_lo": float(lo), "ci_hi": float(hi),
            "p_bootstrap": float(p), "n": int(n)}


# ---------------------------------------------------------------------------
# Table 10e — per model, all dim x real-questionnaire cells
# ---------------------------------------------------------------------------

rows = []
for tag in MODELS:
    merged = synth_agg[tag].merge(real, on="narrative_hash", how="inner")
    for d in DIMS:
        for q in REAL_QUESTS:
            res = spearman_boot_ci(merged[d], merged[q])
            rows.append({"model": tag, "dimension": d, "real_questionnaire": q, **res})

t10e = pd.DataFrame(rows)
# BH-FDR per model
for tag in MODELS:
    mask = t10e["model"] == tag
    p_raw = t10e.loc[mask, "p_raw"].fillna(1.0).to_numpy()
    _, p_fdr, _, _ = multipletests(p_raw, method="fdr_bh")
    t10e.loc[mask, "p_fdr"] = p_fdr
t10e["signif"] = t10e["p_fdr"].map(sig_mark)
t10e = t10e[["model", "dimension", "real_questionnaire", "n",
             "rho", "p_raw", "p_fdr", "ci_lo", "ci_hi", "signif"]]
t10e.to_csv(OUT_DIR / "08_table10e_synthdim_vs_real_quest.csv", index=False)
print("Wrote T10e: 30 rows")
print(t10e.round(3).to_string(index=False))
print()

# ---------------------------------------------------------------------------
# Table 10f — cross-model paired bootstrap on rho_real
# ---------------------------------------------------------------------------

anchor_merged = synth_agg[ANCHOR].merge(real, on="narrative_hash", how="inner")
cross_rows = []
for other in MODELS:
    if other == ANCHOR:
        continue
    other_merged = synth_agg[other].merge(real, on="narrative_hash", how="inner")
    for d in DIMS:
        for q in REAL_QUESTS:
            res = paired_bootstrap(other_merged, anchor_merged, d, q)
            cross_rows.append({
                "model_a": other, "model_b": ANCHOR,
                "dimension": d, "real_questionnaire": q,
                **res,
            })
t10f = pd.DataFrame(cross_rows)
t10f.to_csv(OUT_DIR / "08_table10f_synthdim_realvalidity_cross_model.csv", index=False)
print("Wrote T10f: 20 rows (model_a vs GPT-5)")
print(t10f.round(3).to_string(index=False))
print()

# ---------------------------------------------------------------------------
# Mean per-model rho_real summary
# ---------------------------------------------------------------------------

summary = (t10e.groupby("model")["rho"]
           .agg(mean_rho="mean", median_rho="median",
                min_rho="min", max_rho="max", n_cells="count")
           .round(3))
print("Per-model mean rho_real summary:")
print(summary.to_string())
print()

# ---------------------------------------------------------------------------
# Figure 4: heatmap grid (one panel per model)
# ---------------------------------------------------------------------------

fig, axes = plt.subplots(1, len(MODELS), figsize=(6.5 * len(MODELS), 4),
                         sharey=True, squeeze=False)
for ax, tag in zip(axes[0], MODELS):
    pivot = (t10e.query("model == @tag")
             .pivot(index="dimension", columns="real_questionnaire", values="rho"))
    pivot = pivot[REAL_QUESTS]
    sns.heatmap(pivot, ax=ax, annot=True, fmt=".2f", cmap="RdBu_r",
                center=0, vmin=-1, vmax=1, cbar=(ax is axes[0][-1]),
                square=False, linewidths=0.3)
    ax.set_title(tag)
    ax.set_ylabel("")
    ax.set_xlabel("")
    ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha="right")
fig.suptitle("Synthetic dimensions vs real patient questionnaires (Spearman rho)")
fig.tight_layout()
fig.savefig(FIG_DIR / "08_fig4_synthdim_vs_real_heatmap.pdf", bbox_inches="tight")
plt.close(fig)
print("Saved 08_fig4_synthdim_vs_real_heatmap.pdf")

# ---------------------------------------------------------------------------
# Figure 5: forest plot
# ---------------------------------------------------------------------------

n_cells = len(DIMS) * len(REAL_QUESTS)
fig, ax = plt.subplots(figsize=(8, 8))
y_pos = []
labels = []
vals = []
err_lo = []
err_hi = []
colors_map = {"gpt-5": "#1f77b4",
              "deepseek-r1": "#ff7f0e",
              "claude-sonnet-4-5-thinking": "#2ca02c"}
row = 0
for d in DIMS:
    for q in REAL_QUESTS:
        for tag in MODELS:
            sub = t10e.query("model == @tag and dimension == @d and real_questionnaire == @q").iloc[0]
            y_pos.append(row)
            labels.append(f"{tag} | {d.replace('_score','')} x {q}")
            vals.append(sub["rho"])
            err_lo.append(sub["rho"] - sub["ci_lo"])
            err_hi.append(sub["ci_hi"] - sub["rho"])
            row += 1
        row += 0.6  # spacer between cells

vals = np.asarray(vals)
errs = np.vstack([err_lo, err_hi])
colors_seq = []
for i, label in enumerate(labels):
    for tag, c in colors_map.items():
        if label.startswith(tag):
            colors_seq.append(c)
            break

ax.errorbar(vals, y_pos, xerr=errs, fmt="o", capsize=2, markersize=4,
            ecolor="gray", elinewidth=0.8,
            markerfacecolor="white", markeredgewidth=1.2)
# Re-draw points with per-model colour
for x, y, c in zip(vals, y_pos, colors_seq):
    ax.plot(x, y, "o", color=c, markersize=5)
ax.axvline(0, color="black", linewidth=0.5)
ax.set_yticks(y_pos)
ax.set_yticklabels(labels, fontsize=7)
ax.set_xlabel("Spearman rho (synthetic dimension vs real questionnaire)")
ax.set_title("Synthetic dimensions predicting real patient questionnaires (95% CI)")
ax.invert_yaxis()
# Legend
from matplotlib.lines import Line2D
handles = [Line2D([0], [0], marker="o", color="w", markerfacecolor=c, label=m, markersize=6)
           for m, c in colors_map.items()]
ax.legend(handles=handles, loc="lower right", fontsize=8)
fig.tight_layout()
fig.savefig(FIG_DIR / "08_fig5_synthdim_vs_real_forest.pdf", bbox_inches="tight")
plt.close(fig)
print("Saved 08_fig5_synthdim_vs_real_forest.pdf")
