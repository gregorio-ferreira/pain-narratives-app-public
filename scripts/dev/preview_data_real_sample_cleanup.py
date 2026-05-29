"""Read-only preview: clean Data_real_sample.xlsx the way the migration will.

Run this before the migration to confirm the resulting 152 narratives, the
SHA-256 hashes, and the parsed PCS/BPI/TSK item columns all look right.
Nothing is written to the DB or to disk.
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

import pandas as pd

# PCS Likert labels begin with the numeric value: "0.No, nunca", "1.Sí, alguna vez", ...
PCS_LIKERT_RE = re.compile(r"^\s*(\d)")
# TSK uses a 4-level agreement scale (no leading digit).
TSK_LIKERT_MAP = {
    "totalmente en desacuerdo": 1,
    "en desacuerdo": 2,
    "de acuerdo": 3,
    "totalmente de acuerdo": 4,
}


def parse_pcs_likert(value):
    """Extract the integer from labels like '1.Sí, alguna vez'."""
    if pd.isna(value):
        return None
    m = PCS_LIKERT_RE.match(str(value))
    return int(m.group(1)) if m else None


def parse_tsk_likert(value):
    if pd.isna(value):
        return None
    key = str(value).strip().lower()
    return TSK_LIKERT_MAP.get(key)

REPO = Path(__file__).resolve().parents[2]
RAW_XLSX = REPO / "data" / "Data_real_sample.xlsx"


# Qualtrics column -> canonical column mappings.
# Discovered by inspecting the descriptor row in Data_real_sample.xlsx.
PCS_ITEM_MAP = {
    "Q2_1": "pcs_01", "Q2_2": "pcs_02", "Q2_3": "pcs_03",
    "Q2_4": "pcs_04", "Q2_5": "pcs_05",
    "Q3_1": "pcs_06", "Q3_2": "pcs_07", "Q3_3": "pcs_08", "Q3_4": "pcs_09",
    "Q4_1": "pcs_10", "Q4_2": "pcs_11", "Q4_3": "pcs_12", "Q4_4": "pcs_13",
}
BPI_ITEM_MAP = {f"BPI_{i}": f"bpi_{i:02d}" for i in range(1, 12)}
TSK_ITEM_MAP = {
    "Q2_1.1": "tsk_01", "Q2_2.1": "tsk_02", "Q2_3.1": "tsk_03",
    "Q2_4.1": "tsk_04", "Q2_5.1": "tsk_05",
    "Q3_1.1": "tsk_06", "Q3_2.1": "tsk_07", "Q3_3.1": "tsk_08", "Q3_4.1": "tsk_09",
    "Q3_5": "tsk_10", "Q3_6": "tsk_11",
}

DEMOGRAPHIC_MAP = {
    "Edad": "age",
    "Genero": "gender",
    "Estado_civil": "marital_status",
    "Estudios": "education_level",
    "Residencia_pais": "country_residence",
    "Nacimiento_pais": "country_birth",
    "Empleo": "employment_status",
    "Empleo_11_TEXT": "employment_other",
    "Años_dolor": "years_with_pain",
    "Años_diagnostico": "years_since_diagnosis",
    "Causa_dolor": "pain_cause_primary",
    "Causa_dolor_9_TEXT": "pain_cause_other",
    "Zonas_dolor": "pain_location_zones",
}


def section(title: str) -> None:
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


def main() -> int:
    if not RAW_XLSX.exists():
        print(f"ERROR: {RAW_XLSX} not found", file=sys.stderr)
        return 1

    section(f"Loading {RAW_XLSX.name}")
    raw = pd.read_excel(RAW_XLSX)
    print(f"  raw shape: {raw.shape}")

    # Drop the Qualtrics descriptor row.
    raw = raw.iloc[1:].reset_index(drop=True)
    raw = raw.rename(columns={
        "Unnamed: 0": "valid",
        "Unnamed: 1": "response_id",
        "Q2": "narrative_text",
    })
    raw["valid"] = pd.to_numeric(raw["valid"], errors="coerce").fillna(0).astype(int)
    print(f"  after dropping descriptor: {raw.shape}")
    print(f"  valid==1: {(raw['valid'] == 1).sum()}  valid==0: {(raw['valid'] == 0).sum()}")

    df = raw.loc[raw["valid"] == 1].copy()

    section("narrative_hash + word_count")
    df["narrative_text"] = df["narrative_text"].astype(str)
    df["narrative_hash"] = df["narrative_text"].apply(
        lambda s: hashlib.sha256(s.strip().encode("utf-8")).hexdigest()
    )
    df["word_count"] = df["narrative_text"].str.split().str.len()
    print(f"  rows: {len(df)}")
    print(f"  unique hashes: {df['narrative_hash'].nunique()} (expect 152)")
    print(f"  word_count: min={df['word_count'].min()} max={df['word_count'].max()} "
          f"mean={df['word_count'].mean():.1f}")
    print()
    print("  sample narratives:")
    for _, r in df.head(3).iterrows():
        print(f"    hash={r['narrative_hash'][:16]}...  words={r['word_count']}  "
              f"text={r['narrative_text'][:60]!r}")

    section("Item parsing")
    for label, src_map, parser in (
        ("PCS", PCS_ITEM_MAP, parse_pcs_likert),
        ("BPI", BPI_ITEM_MAP, None),  # BPI items are already 0-10 integers
        ("TSK", TSK_ITEM_MAP, parse_tsk_likert),
    ):
        missing = [k for k in src_map if k not in df.columns]
        if missing:
            print(f"  *** {label} MISSING source columns: {missing}")
            continue
        if parser is None:
            items = df[list(src_map.keys())].apply(pd.to_numeric, errors="coerce")
        else:
            items = df[list(src_map.keys())].map(parser)
        items.columns = list(src_map.values())
        present = items.notna().mean(axis=1).mean()
        total = items.sum(axis=1, skipna=False)
        print(f"  {label}: {len(src_map)} items, mean fill rate {present*100:.1f}%, "
              f"total range [{total.min()}, {total.max()}] mean {total.mean():.2f}")

    section("Demographics presence")
    for src, dst in DEMOGRAPHIC_MAP.items():
        if src not in df.columns:
            print(f"  MISSING: {src} -> {dst}")
            continue
        non_null = df[src].notna().sum()
        print(f"  {src:<22} -> {dst:<22}  non_null={non_null}/{len(df)}")

    section("Hash uniqueness vs publication Excel (info only)")
    try:
        pub = pd.read_excel(
            REPO / "docs" / "revision" / "data" / "20251201_publication_tables.xlsx",
            sheet_name="Data_RealQuest",
        )
        pub_texts = set(pub["narrative"].astype(str))
        overlap = df["narrative_text"].isin(pub_texts).sum()
        print(f"  text-level overlap with Data_RealQuest: {overlap}/{len(df)}")
        if overlap == len(df):
            print("  -> All 152 narratives are present in the publication Excel by text match.")
    except FileNotFoundError:
        print("  publication Excel not found (acceptable; this is informational only)")

    section("SUMMARY")
    ok = len(df) == 152 and df["narrative_hash"].nunique() == 152
    print(f"  {'OK' if ok else 'FAIL'}: 152 valid narratives with 152 unique hashes")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
