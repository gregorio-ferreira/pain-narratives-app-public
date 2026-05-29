"""Data layer for multi-model revision analyses.

Primary source: the ``ai_narratives_original`` PostgreSQL schema (created by
the alembic migration ``2026051500ai_narratives`` and populated by the scripts
under ``scripts/migrate/``). Run those once to fill the schema, then every
``load_*`` function in this module is just a SQL query against it.

Legacy helpers (Excel-based) are kept below the schema-readers for historical
reproduction of the publication paper outputs. The legacy parsers
(_parse_dimensions/pcs/bpi/tsk and MODEL_CONFIGS) remain because the migration
scripts reuse them when reading the raw ``pain_narratives_app.evaluation_results``
rows; downstream analysis code should use the new schema readers.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd
from sqlalchemy import text

from pain_narratives.core.database import DatabaseManager

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# File locations for private analysis inputs. The data directory is ignored by
# git; keep workbooks there or pass them in via a private local workflow.
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DATA_DIR_TRACKED = _REPO_ROOT / "docs" / "revision" / "data"
PROCESSED_DIR = _DATA_DIR_TRACKED / "processed"


def _find(name: str) -> Path:
    p = _DATA_DIR_TRACKED / name
    if p.exists():
        return p
    raise FileNotFoundError(
        f"{name} not found in {_DATA_DIR_TRACKED}. Private workbook inputs are not tracked."
    )


EXCEL_PUB = lambda: _find("20251201_publication_tables.xlsx")  # noqa: E731
EXCEL_EXPERT = lambda: _find("Expert_Evaluated_Narratives_Data.xlsx")  # noqa: E731


# ---------------------------------------------------------------------------
# Per-model batch config. Adding a new model is one entry here.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ModelConfig:
    tag: str
    group_ids: tuple[int, ...]
    # GPT-5 has its synthetic data pre-aggregated in the publication Excel,
    # so we read from Excel rather than re-parsing the DB.
    source: str = "db"  # "db" or "publication_excel"


MODEL_CONFIGS: dict[str, ModelConfig] = {
    # GPT-5: parsed from DB so cross-model comparisons stay apples-to-apples.
    # The Excel aggregate (Data_PCS/BPI/TSK) is also written separately for paper reproduction.
    "gpt-5": ModelConfig(tag="gpt-5", group_ids=(35, 36, 38, 39), source="db"),
    "deepseek-r1": ModelConfig(tag="deepseek-r1", group_ids=(45, 46, 47), source="db"),
    "claude-sonnet-4-5-thinking": ModelConfig(
        # Predicted next group_ids for Runs 3 (49) and 4 (50). Adjust here if the
        # overnight orchestrator's batch script lands on different group ids.
        tag="claude-sonnet-4-5-thinking", group_ids=(48, 49, 50), source="db"
    ),
}

# GPT-5 batch groups 35 and 36 are the two halves of Run 1 (145 + 7 = 152).
# This map collapses them so all models share a "1..N" run space.
_GPT5_GROUP_TO_RUN = {35: 1, 36: 1, 38: 2, 39: 3, 40: 4}


# ---------------------------------------------------------------------------
# Primary schema: ai_narratives_original
# Use these for all new analyses; everything below is legacy / paper-reproduction.
# ---------------------------------------------------------------------------

SCHEMA = "ai_narratives_original"


def load_real_from_schema(db: DatabaseManager | None = None) -> pd.DataFrame:
    """Real patient ground truth from the schema (152 narratives).

    One row per narrative_hash with: participant_id, narrative_hash, all real PCS / BPI / TSK
    items and totals + the four BPI subscale aggregates. Demographics are *not* joined here
    (use ``load_demographics_from_schema``).
    """
    db = db or DatabaseManager()
    with db.engine.connect() as conn:
        return pd.read_sql(text(f"""
            SELECT n.narrative_id AS participant_id, n.narrative_hash, n.word_count,
                   p.pcs_total, p.pcs_rumination, p.pcs_magnification, p.pcs_helplessness,
                   p.pcs_01, p.pcs_02, p.pcs_03, p.pcs_04, p.pcs_05, p.pcs_06, p.pcs_07,
                   p.pcs_08, p.pcs_09, p.pcs_10, p.pcs_11, p.pcs_12, p.pcs_13,
                   b.bpi_total_mean, b.bpi_interference_mean, b.bpi_intensity_mean,
                   b.bpiq11, b.bpiq12, b.bpiq13, b.bpiq14, b.bpiq15, b.bpiq16, b.bpiq17,
                   b.bpiq28, b.bpiq39, b.bpiq410, b.bpiq511,
                   t.tsk_total,
                   t.tsk_01, t.tsk_02, t.tsk_03, t.tsk_04, t.tsk_05, t.tsk_06,
                   t.tsk_07, t.tsk_08, t.tsk_09, t.tsk_10, t.tsk_11
            FROM {SCHEMA}.narratives n
            JOIN {SCHEMA}.real_patient_pcs p ON p.participant_id = n.narrative_id
            JOIN {SCHEMA}.real_patient_bpi b ON b.participant_id = n.narrative_id
            JOIN {SCHEMA}.real_patient_tsk t ON t.participant_id = n.narrative_id
            ORDER BY n.narrative_id
        """), conn)


def load_demographics_from_schema(db: DatabaseManager | None = None) -> pd.DataFrame:
    db = db or DatabaseManager()
    with db.engine.connect() as conn:
        return pd.read_sql(text(
            f"SELECT * FROM {SCHEMA}.real_patient_demographics ORDER BY participant_id"
        ), conn)


def load_synth_from_schema(
    model_tag: str | None = None, db: DatabaseManager | None = None
) -> pd.DataFrame:
    """LLM synthetic results joined across the four llm_* tables.

    Long format: one row per (participant_id, model, run_number). All four PK
    columns plus the dimension scores, all PCS/BPI/TSK items + scores, and
    narrative_hash. When ``model_tag`` is None, returns rows for every model.
    """
    db = db or DatabaseManager()
    where = "WHERE d.model = :model" if model_tag else ""
    params = {"model": model_tag} if model_tag else {}
    with db.engine.connect() as conn:
        return pd.read_sql(text(f"""
            SELECT d.participant_id, d.model, d.run_number,
                   d.experiment_id, d.experiments_group_id,
                   d.severidad_score, d.severidad_explicacion,
                   d.discapacidad_score, d.discapacidad_explicacion,
                   p.pcs_total, p.pcs_rumination, p.pcs_magnification, p.pcs_helplessness,
                   p.pcs_01, p.pcs_02, p.pcs_03, p.pcs_04, p.pcs_05, p.pcs_06, p.pcs_07,
                   p.pcs_08, p.pcs_09, p.pcs_10, p.pcs_11, p.pcs_12, p.pcs_13,
                   b.bpi_total, b.bpi_total_mean,
                   b.bpi_interference_avg, b.bpi_intensity_avg,
                   b.bpi_interference_total, b.bpi_intensity_total,
                   b.bpiq11, b.bpiq12, b.bpiq13, b.bpiq14, b.bpiq15, b.bpiq16, b.bpiq17,
                   b.bpiq28, b.bpiq39, b.bpiq410, b.bpiq511,
                   t.tsk_total,
                   t.tsk_01, t.tsk_02, t.tsk_03, t.tsk_04, t.tsk_05, t.tsk_06,
                   t.tsk_07, t.tsk_08, t.tsk_09, t.tsk_10, t.tsk_11,
                   n.narrative_hash
            FROM {SCHEMA}.llm_dimension_evaluation d
            LEFT JOIN {SCHEMA}.llm_pcs_results p
              ON p.participant_id = d.participant_id AND p.model = d.model AND p.run_number = d.run_number
            LEFT JOIN {SCHEMA}.llm_bpi_results b
              ON b.participant_id = d.participant_id AND b.model = d.model AND b.run_number = d.run_number
            LEFT JOIN {SCHEMA}.llm_tsk_results t
              ON t.participant_id = d.participant_id AND t.model = d.model AND t.run_number = d.run_number
            LEFT JOIN {SCHEMA}.narratives n ON n.narrative_id = d.participant_id
            {where}
            ORDER BY d.model, d.run_number, d.participant_id
        """), conn, params=params)


def load_expert_dimension_from_schema(db: DatabaseManager | None = None) -> pd.DataFrame:
    db = db or DatabaseManager()
    with db.engine.connect() as conn:
        return pd.read_sql(text(
            f"SELECT * FROM {SCHEMA}.expert_dimension_evaluation"
        ), conn)


def load_expert_questionnaire_from_schema(db: DatabaseManager | None = None) -> pd.DataFrame:
    db = db or DatabaseManager()
    with db.engine.connect() as conn:
        return pd.read_sql(text(
            f"SELECT * FROM {SCHEMA}.expert_questionnaire_feedback"
        ), conn)


def available_models(db: DatabaseManager | None = None) -> list[str]:
    """Models that currently have data in the schema."""
    db = db or DatabaseManager()
    with db.engine.connect() as conn:
        rows = conn.execute(text(
            f"SELECT DISTINCT model FROM {SCHEMA}.llm_dimension_evaluation ORDER BY model"
        )).fetchall()
    return [m for (m,) in rows]


# ---------------------------------------------------------------------------
# Legacy bridge tables (paper-reproduction only)
# ---------------------------------------------------------------------------


def load_mapping() -> pd.DataFrame:
    """152 rows: excel_id, db_narrative_id, narrative_hash."""
    return pd.read_excel(EXCEL_PUB(), sheet_name="Map_ExcelToDB")


def load_db_narrative_hashes(db: DatabaseManager | None = None) -> pd.DataFrame:
    """narrative_id -> narrative_hash from pain_narratives_app.narratives.

    Each narrative_text can appear under multiple narrative_id values (one per
    upload/batch). This table is the universal hash bridge.
    """
    db = db or DatabaseManager()
    with db.engine.connect() as conn:
        return pd.read_sql(
            text("SELECT narrative_id, narrative_hash FROM pain_narratives_app.narratives"),
            conn,
        )


def load_data_matched() -> pd.DataFrame:
    """37 rows bridging the expert-evaluated subset to batch_narrative_id."""
    df = pd.read_excel(EXCEL_PUB(), sheet_name="Data_Matched")
    df["narrative_text_strip"] = df["narrative_text"].str.strip()
    return df


def load_expert_to_db_bridge() -> pd.DataFrame:
    """expert participant_id -> batch (db) narrative_id, for the 37 matched."""
    nar = pd.read_excel(EXCEL_EXPERT(), sheet_name="Narratives")
    nar = nar[["participant_id", "narrative_text"]].copy()
    nar["narrative_text_strip"] = nar["narrative_text"].str.strip()
    matched = load_data_matched()
    return nar.merge(matched[["narrative_text_strip", "batch_narrative_id"]],
                     on="narrative_text_strip", how="inner")[
        ["participant_id", "batch_narrative_id"]
    ].rename(columns={"participant_id": "expert_participant_id"})


# ---------------------------------------------------------------------------
# Real ground truth
# ---------------------------------------------------------------------------


def load_real_152() -> pd.DataFrame:
    """152 narratives with real patient PCS/BPI/TSK totals + items + narrative_hash + db_narrative_id.

    Source: Data_RealQuest (157 rows) joined with Map_ExcelToDB on narrative_hash.
    The 5 dropped rows are real patients whose narratives were not used in the LLM batch.
    """
    rq = pd.read_excel(EXCEL_PUB(), sheet_name="Data_RealQuest")
    mapping = load_mapping()
    df = rq.merge(mapping, on="narrative_hash", how="inner").rename(
        columns={"ID": "expert_participant_id"}
    )

    pcs_items = [f"PCS_{i}" for i in range(1, 14)]
    df["pcs_total"] = df[pcs_items].sum(axis=1)

    # BPI: total_mean uses interference (BPI_IS_1..7 minus item 4) + intensity (BPI_PI_1..4).
    # Match the publication's bpi_total_mean by averaging available items on a 0-10 scale.
    bpi_int_cols = [f"BPI_IS_{i}" for i in (1, 2, 3, 5, 6, 7)]
    bpi_intensity_cols = [f"BPI_PI_{i}" for i in (1, 2, 3, 4)]
    df["bpi_interference_mean"] = df[bpi_int_cols].mean(axis=1)
    df["bpi_intensity_mean"] = df[bpi_intensity_cols].mean(axis=1)
    df["bpi_total_mean"] = df[bpi_int_cols + bpi_intensity_cols].mean(axis=1)

    tsk_items = [f"TSK_{i}" for i in range(1, 12)]
    df["tsk_total"] = df[tsk_items].sum(axis=1)

    keep = (
        ["expert_participant_id", "excel_id", "db_narrative_id", "narrative_hash",
         "pcs_total", "bpi_total_mean", "bpi_interference_mean", "bpi_intensity_mean",
         "tsk_total"]
        + pcs_items
        + bpi_int_cols
        + bpi_intensity_cols
        + tsk_items
    )
    return df[keep].copy()


def load_real_41() -> pd.DataFrame:
    """41-narrative expert-evaluated subset with full item-level real scores.

    From Real_Scores_AllItems. Adds batch_narrative_id when the expert participant
    bridges to the publication Excel (37 of 41 do).
    """
    df = pd.read_excel(EXCEL_EXPERT(), sheet_name="Real_Scores_AllItems")
    bridge = load_expert_to_db_bridge()
    df = df.merge(bridge, left_on="participant_id",
                  right_on="expert_participant_id", how="left")
    return df


# ---------------------------------------------------------------------------
# GPT-5 synthetic (read pre-aggregated from the publication Excel)
# ---------------------------------------------------------------------------


def load_gpt5_synth_aggregated() -> pd.DataFrame:
    """One row per narrative_hash with GPT-5 aggregated PCS/BPI/TSK + dimension scores.

    Data_PCS / Data_BPI / Data_TSK each have 152 rows and represent GPT-5 results
    averaged across runs. Their ``narrative_id`` is the DB narrative_id from the
    GPT-5 batch upload; the universal join key is ``narrative_hash`` (looked up
    via pain_narratives_app.narratives).
    """
    pcs = pd.read_excel(EXCEL_PUB(), sheet_name="Data_PCS")
    bpi = pd.read_excel(EXCEL_PUB(), sheet_name="Data_BPI")
    tsk = pd.read_excel(EXCEL_PUB(), sheet_name="Data_TSK")

    bpi = bpi.rename(columns={"bpi_interference_mean": "bpi_interference_avg",
                              "bpi_intensity_mean": "bpi_intensity_avg"})

    # Each Data_* sheet already carries narrative_hash; join on (narrative_id, narrative_hash).
    df = (pcs.merge(bpi, on=["narrative_id", "narrative_hash"])
              .merge(tsk, on=["narrative_id", "narrative_hash"]))
    df["model"] = "gpt-5"
    return df


def load_gpt5_synth_runs_41() -> pd.DataFrame:
    """Per-run GPT-5 synthetic results for the 41 expert-evaluated narratives.

    Long format: one row per (expert_participant_id, run_number, questionnaire).
    Returned columns: participant_id, run_number, pcs_total, bpi_total_mean,
    bpi_interference_avg, bpi_intensity_avg, tsk_total.
    """
    pcs = pd.read_excel(EXCEL_EXPERT(), sheet_name="Synth_PCS_AllRuns")
    bpi = pd.read_excel(EXCEL_EXPERT(), sheet_name="Synth_BPI_AllRuns")
    tsk = pd.read_excel(EXCEL_EXPERT(), sheet_name="Synth_TSK_AllRuns")
    bpi = bpi.rename(columns={"bpi_interference_mean": "bpi_interference_avg",
                              "bpi_intensity_mean": "bpi_intensity_avg"})
    keep_pcs = ["participant_id", "run_number", "pcs_total"]
    keep_bpi = ["participant_id", "run_number", "bpi_total_mean",
                "bpi_interference_avg", "bpi_intensity_avg"]
    keep_tsk = ["participant_id", "run_number", "tsk_total"]
    df = (pcs[keep_pcs]
              .merge(bpi[keep_bpi], on=["participant_id", "run_number"])
              .merge(tsk[keep_tsk], on=["participant_id", "run_number"]))
    df["model"] = "gpt-5"
    return df.rename(columns={"participant_id": "expert_participant_id"})


# ---------------------------------------------------------------------------
# Synthetic from DB (DeepSeek-R1, Sonnet 4.5)
# ---------------------------------------------------------------------------


def _coerce_dim_value(v):
    """Pull a numeric score out of any of the three observed schemas.

    GPT-5:        {'Severidad del dolor': {'score': 8, 'explicacion': '...'}}
    R1 / Sonnet:  {'severidad_del_dolor': 8}
    Older:        {'severidad': {'puntuacion': 8, 'explicacion': '...'}}
    """
    if v is None:
        return None, None
    if isinstance(v, dict):
        score = v.get("score")
        if score is None:
            score = v.get("puntuacion")
        return score, v.get("explicacion")
    return v, None  # bare numeric


def _parse_dimensions(rj) -> dict:
    obj = rj if isinstance(rj, dict) else json.loads(rj)
    sev_raw = (obj.get("severidad_del_dolor")
               or obj.get("Severidad del dolor")
               or obj.get("severidad"))
    dis_raw = obj.get("discapacidad") or obj.get("Discapacidad")
    sev_score, sev_exp = _coerce_dim_value(sev_raw)
    dis_score, dis_exp = _coerce_dim_value(dis_raw)
    return {
        "severidad_score": sev_score,
        "severidad_explicacion": sev_exp,
        "discapacidad_score": dis_score,
        "discapacidad_explicacion": dis_exp,
    }


def _parse_pcs(rj) -> dict:
    obj = rj if isinstance(rj, dict) else json.loads(rj)
    raw = obj.get("raw_data", {}) or {}
    scores = raw.get("scores", {}) or {}
    sub = obj.get("subscales", {}) or {}
    data = {
        "pcs_total": obj.get("total_score"),
        "pcs_rumination": sub.get("rumination"),
        "pcs_magnification": sub.get("magnification"),
        "pcs_helplessness": sub.get("helplessness"),
    }
    for i in range(1, 14):
        # Scores keyed as "1".."13" in the simplified_v1 schema.
        data[f"pcs_{i:02d}"] = scores.get(str(i))
    return data


_BPI_ITEM_ORDER = [
    "bpiq11", "bpiq12", "bpiq13", "bpiq15", "bpiq16", "bpiq17",
    "bpiq28", "bpiq39", "bpiq410", "bpiq511",
]


def _parse_bpi(rj) -> dict:
    obj = rj if isinstance(rj, dict) else json.loads(rj)
    raw = obj.get("raw_data", {}) or {}
    responses = raw.get("responses", []) or []
    sub = obj.get("subscales", {}) or {}
    total = obj.get("total_score")
    data = {
        "bpi_total": total,
        "bpi_total_mean": total / 10.0 if total is not None else None,
        "bpi_interference_avg": sub.get("interference_avg"),
        "bpi_intensity_avg": sub.get("intensity_avg"),
        "bpi_interference_total": sub.get("interference_total"),
        "bpi_intensity_total": sub.get("intensity_total"),
    }
    for idx, key in enumerate(_BPI_ITEM_ORDER):
        if idx < len(responses):
            data[key] = responses[idx].get("value") if isinstance(responses[idx], dict) else None
    return data


def _parse_tsk(rj) -> dict:
    obj = rj if isinstance(rj, dict) else json.loads(rj)
    raw = obj.get("raw_data", {}) or {}
    responses = raw.get("responses", []) or []
    data = {"tsk_total": obj.get("total_score")}
    for i in range(1, 12):
        if i - 1 < len(responses):
            v = responses[i - 1].get("value") if isinstance(responses[i - 1], dict) else None
            data[f"tsk_{i:02d}"] = v
    return data


_RESULT_PARSERS = {
    "dimensions": _parse_dimensions,
    "PCS": _parse_pcs,
    "BPI-IS": _parse_bpi,
    "TSK-11SV": _parse_tsk,
}


def load_synth_from_db(
    model_tag: str,
    group_ids: Iterable[int],
    db: DatabaseManager | None = None,
) -> pd.DataFrame:
    """Tidy long-format DataFrame for one model: one row per experiment.

    Output columns: experiment_id, experiments_group_id, run_number, narrative_id,
    narrative_hash, model, pcs_total, pcs_*, bpi_*, tsk_*, severidad_score,
    discapacidad_score.

    `run_number` is derived from the order of `group_ids` (first group = run 1).
    """
    db = db or DatabaseManager()
    group_ids = list(group_ids)
    # GPT-5 uses a specific run mapping that collapses retries; everything else
    # numbers runs by the order group_ids was supplied.
    if model_tag == "gpt-5":
        group_to_run = {gid: _GPT5_GROUP_TO_RUN.get(gid, i + 1)
                        for i, gid in enumerate(group_ids)}
    else:
        group_to_run = {gid: i + 1 for i, gid in enumerate(group_ids)}

    with db.engine.connect() as conn:
        exp = pd.read_sql(
            text(
                """
                SELECT experiment_id, experiments_group_id, narrative_id, succeeded
                FROM pain_narratives_app.experiments_list
                WHERE experiments_group_id = ANY(:gids)
                  AND succeeded = TRUE
                """
            ),
            conn,
            params={"gids": group_ids},
        )
        evals = pd.read_sql(
            text(
                """
                SELECT experiment_id, experiments_group_id, result_type, result_json
                FROM pain_narratives_app.evaluation_results
                WHERE experiments_group_id = ANY(:gids)
                """
            ),
            conn,
            params={"gids": group_ids},
        )

    if exp.empty:
        logger.warning("No succeeded experiments for groups %s", group_ids)
        return pd.DataFrame()

    rows: dict[int, dict] = {}
    for _, r in exp.iterrows():
        rows[r.experiment_id] = {
            "experiment_id": r.experiment_id,
            "experiments_group_id": r.experiments_group_id,
            "run_number": group_to_run[r.experiments_group_id],
            "narrative_id": r.narrative_id,
            "model": model_tag,
        }

    for _, e in evals.iterrows():
        if e.experiment_id not in rows:
            continue
        parser = _RESULT_PARSERS.get(e.result_type)
        if parser is None:
            continue
        rows[e.experiment_id].update(parser(e.result_json))

    out = pd.DataFrame(rows.values())
    hashes = load_db_narrative_hashes(db)
    out = out.merge(hashes, on="narrative_id", how="left")
    return out


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def write_parquet(df: pd.DataFrame, name: str) -> Path:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out = PROCESSED_DIR / name
    df.to_parquet(out, index=False)
    return out


def load_processed(name: str) -> pd.DataFrame:
    return pd.read_parquet(PROCESSED_DIR / name)
