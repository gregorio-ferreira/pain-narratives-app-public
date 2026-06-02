"""Assemble the comprehensive multi-model deliverable package.

Bundles every multi-model analysis produced from `ai_narratives_original`:
- The publication-style tables (T1, T2, T3, T3b, T5, T7, T11) from notebook 06
- The rebuttal cross-model tables (Tables 7, 8, 9) from notebook 07
- The dimension x questionnaire tables (Tables 10a-f) from notebook 08 + T10e/f scripts
- All figures from notebooks 07 and 08
- A single Excel with an Index sheet and Headline numbers

Output:
    docs/multimodel/package/
    ├── 00_README.md, 01_executive_summary.md, 02_methodology.md,
    │   03_results_walkthrough.md, 04_caveats.md  (written separately)
    ├── AINarratives_Multimodel_Complete.xlsx
    ├── tables/   (raw CSVs)
    └── figures/  (PDFs)
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
NB_OUT = REPO / "notebooks" / "outputs"
REV_OUT = NB_OUT / "revision"
PKG = REPO / "docs" / "multimodel" / "package"
WORKBOOK = PKG / "AINarratives_Multimodel_Complete.xlsx"


# (Sheet name, CSV file relative to NB_OUT or REV_OUT, description)
SHEETS: list[tuple[str, Path | None, str]] = [
    ("Index", None,
     "This sheet. Map of every other table + one-line description."),
    ("Headline_numbers", None,
     "Top-line summary numbers across all models and analyses."),
    # Publication-style tables (from notebook 06)
    ("T1_Sample_Characteristics", None,
     "Patient demographics (N=152)."),
    ("T2_Dimension_Descriptives", None,
     "Per-model mean / SD / range for LLM dimension scores (Severidad, Discapacidad)."),
    ("T2b_Dim_InterModel_Agreement", None,
     "Pairwise MAE / RMSE between models on the two dimension scores (per-narrative mean across runs)."),
    ("T3_Questionnaire_Descriptives", None,
     "Real + per-model synthetic means / SDs for PCS / BPI / TSK."),
    ("T3b_Real_vs_Synth_Agreement", None,
     "Per-model MAE / RMSE / Pearson r / Spearman rho vs real."),
    ("T5_Cronbach_Alpha", None,
     "Long format: real + per-model synthetic (mean+/-SD across runs) alpha. Includes BPI total + subscales."),
    ("T5b_Cronbach_Alpha_Compact", None,
     "Compact format: one row per scale (PCS, BPI total, BPI interference, BPI intensity, TSK). One column group per model with mean and SD side-by-side."),
    ("T7_LLM_Consistency", None,
     "Within-model SD across runs per participant."),
    ("T11_Dim_vs_Real_Quest", None,
     "LLM dimension scores correlated with real patient questionnaires."),
    # Rebuttal cross-model tables (from notebook 07)
    ("R7_Per_Model_Agreement", REV_OUT / "07_table7_per_model_agreement.csv",
     "Rebuttal Table 7: per-model agreement vs real (Pearson + Spearman + Fisher 95% CI)."),
    ("R8_Inter_Model", REV_OUT / "07_table8_inter_model_agreement.csv",
     "Rebuttal Table 8: pairwise inter-model agreement (MAE, Pearson, ICC)."),
    ("R9_Stat_vs_Anchor", REV_OUT / "07_table9_stat_comparison_vs_anchor.csv",
     "Rebuttal Table 9: Wilcoxon + paired bootstrap |err| delta vs GPT-5."),
    # Dimension x questionnaire (from notebook 08 + T10e/f)
    ("R10a_DimQuest_Sim_Real", REV_OUT / "08_table10a_per_model_correlations.csv",
     "2x5 dim x quest correlations per model: rho_sim (LLM vs LLM) + rho_real (LLM vs real)."),
    ("R10b_Cross_Model_Delta", REV_OUT / "08_table10b_cross_model_delta.csv",
     "Cross-model paired-bootstrap delta_rho_sim vs GPT-5."),
    ("R10c_QxQ_vs_Real", REV_OUT / "08_table10c_quest_vs_real.csv",
     "Per-model questionnaire inter-correlations vs the real-data reference."),
    ("R10d_Q_Inter_Corr", REV_OUT / "08_table10d_quest_inter.csv",
     "Questionnaire inter-correlations: 3 models + real, side-by-side."),
    ("R10e_SynthDim_vs_RealQ", REV_OUT / "08_table10e_synthdim_vs_real_quest.csv",
     "Focused: synthetic dimension vs real patient questionnaire (Spearman + boot CI + FDR)."),
    ("R10f_SynthDim_RealVal_X", REV_OUT / "08_table10f_synthdim_realvalidity_cross_model.csv",
     "Cross-model paired bootstrap on rho_real (T10e). External-validity comparison."),
]


def headline_numbers() -> pd.DataFrame:
    """Pull the most rebuttal-/paper-relevant numbers from the underlying CSVs."""
    t3b = pd.read_csv(NB_OUT / "05_real_vs_synthetic_all.csv")
    t5 = pd.read_csv(NB_OUT / "05_cronbach_alpha.csv")
    r9 = pd.read_csv(REV_OUT / "07_table9_stat_comparison_vs_anchor.csv")
    r10e = pd.read_csv(REV_OUT / "08_table10e_synthdim_vs_real_quest.csv")

    rows = [
        {"metric": "Schema source", "value": "ai_narratives_original"},
        {"metric": "Patients (N)", "value": "152"},
        {"metric": "Models analysed", "value": "GPT-5, DeepSeek-R1, Claude Sonnet 4.5 (extended thinking)"},
        {"metric": "Runs per model", "value": "3"},
    ]

    for m in sorted(t3b["model"].unique()):
        sub = t3b[(t3b["model"] == m) & t3b["questionnaire"].isin(["pcs_total", "bpi_total_mean", "tsk_total"])]
        pcs = sub.query("questionnaire == 'pcs_total'")["pearson_r"].iloc[0]
        bpi = sub.query("questionnaire == 'bpi_total_mean'")["pearson_r"].iloc[0]
        tsk = sub.query("questionnaire == 'tsk_total'")["pearson_r"].iloc[0]
        rows.append({"metric": f"Pearson r vs real ({m}): PCS / BPI / TSK",
                     "value": f"{pcs:.3f} / {bpi:.3f} / {tsk:.3f}"})

    real_row = t5.query("source == 'real'").iloc[0]
    rows.append({"metric": "Cronbach alpha (real): PCS / BPI_int / BPI_inten / TSK",
                 "value": f"{real_row['pcs_alpha']:.3f} / {real_row['bpi_interference_alpha']:.3f} / "
                          f"{real_row['bpi_intensity_alpha']:.3f} / {real_row['tsk_alpha']:.3f}"})
    for m in sorted(t5.query("source == 'synthetic_mean'")["model"].unique()):
        r = t5.query("source == 'synthetic_mean' and model == @m").iloc[0]
        rows.append({"metric": f"Cronbach alpha (synth {m}, mean across 3 runs)",
                     "value": f"PCS={r['pcs_alpha']:.3f}  BPI_int={r['bpi_interference_alpha']:.3f}  "
                              f"BPI_inten={r['bpi_intensity_alpha']:.3f}  TSK={r['tsk_alpha']:.3f}"})

    for _, r in r9.iterrows():
        rows.append({
            "metric": f"Wilcoxon: GPT-5 vs {r['other']} ({r['questionnaire']})",
            "value": f"p = {r['wilcoxon_p']:.4f}  Δ|err| = {r['mean_delta_abs_err']:+.3f}",
        })

    mean_rho_real = r10e.groupby("model")["rho"].mean().round(3).sort_values(ascending=False)
    rows.append({"metric": "Mean rho (synth dim vs real questionnaire, T10e)",
                 "value": ", ".join(f"{m}={v:.3f}" for m, v in mean_rho_real.items())})

    return pd.DataFrame(rows)


def main() -> None:
    PKG.mkdir(parents=True, exist_ok=True)
    (PKG / "tables").mkdir(parents=True, exist_ok=True)
    (PKG / "figures").mkdir(parents=True, exist_ok=True)

    # Copy publication-style CSVs from notebook 05/06 outputs
    for fname in ("05_real_vs_synthetic_all.csv", "05_cronbach_alpha.csv",
                  "05_llm_consistency.csv", "05_dim_vs_real_quest.csv"):
        src = NB_OUT / fname
        if src.exists():
            shutil.copy2(src, PKG / "tables" / fname)
            print(f"  csv (pub) -> {fname}")

    # Copy rebuttal CSVs
    for sheet_name, csv_path, _ in SHEETS:
        if csv_path is None or not csv_path.exists():
            continue
        shutil.copy2(csv_path, PKG / "tables" / csv_path.name)
        print(f"  csv (rev) -> {csv_path.name}")

    # Copy figures
    fig_src = REV_OUT / "figures"
    if fig_src.exists():
        for fig in sorted(fig_src.glob("*.pdf")):
            shutil.copy2(fig, PKG / "figures" / fig.name)
            print(f"  fig       -> {fig.name}")

    # Build the consolidated workbook.
    # Source: AINarratives_Multimodel_Consolidated.xlsx (from notebook 06) -> base sheets.
    # Plus rebuttal CSVs read in as additional sheets.
    consolidated = NB_OUT / "AINarratives_Multimodel_Consolidated.xlsx"
    base_sheets = pd.read_excel(consolidated, sheet_name=None)

    with pd.ExcelWriter(WORKBOOK, engine="openpyxl") as writer:
        index_rows = [{"Sheet": name, "Description": desc}
                      for name, _, desc in SHEETS]
        pd.DataFrame(index_rows).to_excel(writer, sheet_name="Index", index=False)
        headline_numbers().to_excel(writer, sheet_name="Headline_numbers", index=False)

        for sheet_name, csv_path, _ in SHEETS:
            if sheet_name in ("Index", "Headline_numbers"):
                continue
            if csv_path is None:
                # Read from the existing consolidated workbook
                base_name = sheet_name  # same names already in the consolidated file
                if base_name in base_sheets:
                    base_sheets[base_name].to_excel(writer, sheet_name=sheet_name[:31], index=False)
                    print(f"  xlsx pub  -> {sheet_name}  ({len(base_sheets[base_name])} rows)")
            else:
                df = pd.read_csv(csv_path)
                df.to_excel(writer, sheet_name=sheet_name[:31], index=False)
                print(f"  xlsx rev  -> {sheet_name}  ({len(df)} rows)")

    print(f"\nWrote {WORKBOOK}")


if __name__ == "__main__":
    main()
