"""Populate the ``ai_narratives_original`` schema's real-patient tables from the
Qualtrics raw export ``data/Data_real_sample.xlsx``.

Idempotent: truncates the four real-patient tables + the canonical narratives
table on every run, then inserts the 152 valid rows.

Usage::

    uv run python scripts/migrate/ingest_real_from_xlsx.py

Run after the alembic migration ``2026051500ai_narratives`` has created the
schema. The script asserts row counts at the end so a bad run halts loudly.
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import text

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

from pain_narratives.core.database import DatabaseManager  # noqa: E402

RAW_XLSX = REPO / "data" / "Data_real_sample.xlsx"
SCHEMA = "ai_narratives_original"

# Likert mapping helpers (see scripts/dev/preview_data_real_sample_cleanup.py)
PCS_LIKERT_RE = re.compile(r"^\s*(\d)")
TSK_LIKERT_MAP = {
    "totalmente en desacuerdo": 1,
    "en desacuerdo": 2,
    "de acuerdo": 3,
    "totalmente de acuerdo": 4,
}


def parse_pcs_likert(value):
    if pd.isna(value):
        return None
    m = PCS_LIKERT_RE.match(str(value))
    return int(m.group(1)) if m else None


def parse_tsk_likert(value):
    if pd.isna(value):
        return None
    return TSK_LIKERT_MAP.get(str(value).strip().lower())


def parse_int(value):
    if pd.isna(value):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_years(value):
    """Parse a Spanish year string like '23 años' to an integer.

    Handles 'Menos de un año' (< 1 year) as 0 and falls back to None for
    anything we cannot parse cleanly.
    """
    if pd.isna(value):
        return None
    s = str(value).strip().lower()
    if "menos" in s and "año" in s:
        return 0
    m = re.search(r"\d+", s)
    return int(m.group(0)) if m else None


# Source column -> canonical item-column mappings
PCS_ITEM_MAP = {
    "Q2_1": "pcs_01", "Q2_2": "pcs_02", "Q2_3": "pcs_03",
    "Q2_4": "pcs_04", "Q2_5": "pcs_05",
    "Q3_1": "pcs_06", "Q3_2": "pcs_07", "Q3_3": "pcs_08", "Q3_4": "pcs_09",
    "Q4_1": "pcs_10", "Q4_2": "pcs_11", "Q4_3": "pcs_12", "Q4_4": "pcs_13",
}
BPI_ITEM_MAP = {
    # Qualtrics BPI_1..BPI_7 are the interference 7 items (Q1.1..Q1.7).
    # BPI_8..BPI_11 are the four severity/intensity items (worst, least, avg, now).
    "BPI_1": "bpiq11", "BPI_2": "bpiq12", "BPI_3": "bpiq13", "BPI_4": "bpiq14",
    "BPI_5": "bpiq15", "BPI_6": "bpiq16", "BPI_7": "bpiq17",
    "BPI_8": "bpiq28", "BPI_9": "bpiq39", "BPI_10": "bpiq410", "BPI_11": "bpiq511",
}
TSK_ITEM_MAP = {
    "Q2_1.1": "tsk_01", "Q2_2.1": "tsk_02", "Q2_3.1": "tsk_03",
    "Q2_4.1": "tsk_04", "Q2_5.1": "tsk_05",
    "Q3_1.1": "tsk_06", "Q3_2.1": "tsk_07", "Q3_3.1": "tsk_08", "Q3_4.1": "tsk_09",
    "Q3_5": "tsk_10", "Q3_6": "tsk_11",
}

# PCS subscale item indices (1-based)
PCS_RUMINATION = [8, 9, 10, 11]
PCS_MAGNIFICATION = [6, 7, 13]
PCS_HELPLESSNESS = [1, 2, 3, 4, 5, 12]

# BPI groups (column suffixes after renaming)
BPI_INTERFERENCE = ["bpiq11", "bpiq12", "bpiq13", "bpiq14", "bpiq15", "bpiq16", "bpiq17"]
BPI_INTENSITY = ["bpiq28", "bpiq39", "bpiq410", "bpiq511"]


# ---------------------------------------------------------------------------
# Cleaning
# ---------------------------------------------------------------------------


def load_clean() -> pd.DataFrame:
    raw = pd.read_excel(RAW_XLSX)
    raw = raw.iloc[1:].reset_index(drop=True)
    raw = raw.rename(columns={
        "Unnamed: 0": "valid",
        "Unnamed: 1": "response_id",
        "Q2": "narrative_text",
    })
    raw["valid"] = pd.to_numeric(raw["valid"], errors="coerce").fillna(0).astype(int)
    df = raw.loc[raw["valid"] == 1].copy()
    df["narrative_text"] = df["narrative_text"].astype(str)
    df["narrative_hash"] = df["narrative_text"].apply(
        lambda s: hashlib.sha256(s.strip().encode("utf-8")).hexdigest()
    )
    df["word_count"] = df["narrative_text"].str.split().str.len()
    return df.reset_index(drop=True)


def build_narratives(df: pd.DataFrame) -> pd.DataFrame:
    """Frame for the ``narratives`` table — narrative_id is assigned 1..N here."""
    out = df[["narrative_hash", "narrative_text", "word_count", "response_id"]].copy()
    out.insert(0, "narrative_id", range(1, len(out) + 1))
    return out


def build_demographics(df: pd.DataFrame, narratives: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame({
        "participant_id": narratives["narrative_id"].to_numpy(),
        "narrative_hash": df["narrative_hash"].to_numpy(),
        "narrative_text": df["narrative_text"].to_numpy(),
        "word_count": df["word_count"].to_numpy(),
        "age": df["Edad"].apply(parse_int),
        "gender": df["Genero"],
        "marital_status": df["Estado_civil"],
        "education_level": df["Estudios"],
        "country_residence": df["Residencia_pais"],
        "country_birth": df["Nacimiento_pais"],
        "employment_status": df["Empleo"],
        # Keep years as raw strings to match the original schema convention,
        # but also expose a parsed integer column for downstream convenience.
        "years_with_pain": df["Años_dolor"].astype(str),
        "years_since_diagnosis": df["Años_diagnostico"].astype(str),
        "pain_cause_primary": df["Causa_dolor"],
        "pain_location_zones": df["Zonas_dolor"],
    })
    return out


def build_pcs(df: pd.DataFrame, narratives: pd.DataFrame) -> pd.DataFrame:
    items = df[list(PCS_ITEM_MAP.keys())].map(parse_pcs_likert)
    items.columns = list(PCS_ITEM_MAP.values())
    items.insert(0, "participant_id", narratives["narrative_id"].to_numpy())
    items["pcs_total"] = items[[f"pcs_{i:02d}" for i in range(1, 14)]].sum(axis=1, skipna=False)
    items["pcs_rumination"] = items[[f"pcs_{i:02d}" for i in PCS_RUMINATION]].sum(axis=1, skipna=False)
    items["pcs_magnification"] = items[[f"pcs_{i:02d}" for i in PCS_MAGNIFICATION]].sum(axis=1, skipna=False)
    items["pcs_helplessness"] = items[[f"pcs_{i:02d}" for i in PCS_HELPLESSNESS]].sum(axis=1, skipna=False)
    return items


def build_bpi(df: pd.DataFrame, narratives: pd.DataFrame) -> pd.DataFrame:
    items = df[list(BPI_ITEM_MAP.keys())].apply(pd.to_numeric, errors="coerce")
    items.columns = list(BPI_ITEM_MAP.values())
    items.insert(0, "participant_id", narratives["narrative_id"].to_numpy())
    items["bpi_interference_mean"] = items[BPI_INTERFERENCE].mean(axis=1)
    items["bpi_intensity_mean"] = items[BPI_INTENSITY].mean(axis=1)
    items["bpi_total_mean"] = items[BPI_INTERFERENCE + BPI_INTENSITY].mean(axis=1)
    return items


def build_tsk(df: pd.DataFrame, narratives: pd.DataFrame) -> pd.DataFrame:
    items = df[list(TSK_ITEM_MAP.keys())].map(parse_tsk_likert)
    items.columns = list(TSK_ITEM_MAP.values())
    items.insert(0, "participant_id", narratives["narrative_id"].to_numpy())
    items["tsk_total"] = items[[f"tsk_{i:02d}" for i in range(1, 12)]].sum(axis=1, skipna=False)
    return items


# ---------------------------------------------------------------------------
# DB writes
# ---------------------------------------------------------------------------


def truncate_and_load(db: DatabaseManager, frames: dict[str, pd.DataFrame]) -> None:
    """Truncate tables then bulk-insert dataframes."""
    with db.engine.begin() as conn:
        # Drop in reverse dependency order: real_patient_* depend on narratives in the
        # logical sense (same participant_id), although there's no FK constraint.
        for table in ("real_patient_pcs", "real_patient_bpi", "real_patient_tsk",
                      "real_patient_demographics", "narratives"):
            conn.execute(text(f"TRUNCATE TABLE {SCHEMA}.{table} CASCADE"))
    for table, df in frames.items():
        df.to_sql(table, db.engine, schema=SCHEMA, if_exists="append", index=False, method="multi")


def verify_counts(db: DatabaseManager) -> None:
    with db.engine.connect() as conn:
        for table, expected in (
            ("narratives", 152),
            ("real_patient_demographics", 152),
            ("real_patient_pcs", 152),
            ("real_patient_bpi", 152),
            ("real_patient_tsk", 152),
        ):
            n = conn.execute(text(f"SELECT COUNT(*) FROM {SCHEMA}.{table}")).scalar()
            status = "OK" if n == expected else "FAIL"
            print(f"  {status:<4} {SCHEMA}.{table}: {n} (expected {expected})")
            assert n == expected, f"{table} has {n} rows, expected {expected}"


def main() -> int:
    if not RAW_XLSX.exists():
        print(f"ERROR: {RAW_XLSX} not found", file=sys.stderr)
        return 1
    print(f"Reading {RAW_XLSX}")
    df = load_clean()
    print(f"  valid rows: {len(df)}")

    narratives = build_narratives(df)
    frames = {
        "narratives": narratives,
        "real_patient_demographics": build_demographics(df, narratives),
        "real_patient_pcs": build_pcs(df, narratives),
        "real_patient_bpi": build_bpi(df, narratives),
        "real_patient_tsk": build_tsk(df, narratives),
    }

    for table, frame in frames.items():
        print(f"  built {table}: shape={frame.shape}, columns={list(frame.columns)[:6]}...")

    db = DatabaseManager()
    print(f"\nTruncating and inserting into {SCHEMA}.* ...")
    truncate_and_load(db, frames)

    print("\nVerifying row counts:")
    verify_counts(db)
    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
