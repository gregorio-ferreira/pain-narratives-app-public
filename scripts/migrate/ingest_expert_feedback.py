"""Populate the expert feedback tables in ``ai_narratives_original``.

Sources:
- ``pain_narratives_app.assessment_feedback``  -> ``expert_dimension_evaluation``
- ``pain_narratives_app.questionnaire_feedback`` -> ``expert_questionnaire_feedback``

We carry the Likert agreement ratings (text) for the two core dimensions
(Severidad, Discapacidad) and stash the JSON ``dimension_feedback`` blob (which
holds the extended dimensions like Depression, Trustworthiness, etc.) into a
single ``extended_dimensions`` JSON column.

The bridge to the target schema's narratives table is via SHA-256 of the source
narrative's stripped text — same trick as ``ingest_llm_from_db.py``.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import text

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

from pain_narratives.core.database import DatabaseManager  # noqa: E402

SCHEMA = "ai_narratives_original"


def _hash_to_participant_map(db: DatabaseManager) -> dict[str, int]:
    with db.engine.connect() as conn:
        rows = conn.execute(
            text(f"SELECT narrative_hash, narrative_id FROM {SCHEMA}.narratives")
        ).fetchall()
    return {h: nid for h, nid in rows}


def _source_narrative_id_to_target_pid(db: DatabaseManager) -> dict[int, int]:
    pid_by_hash = _hash_to_participant_map(db)
    with db.engine.connect() as conn:
        rows = conn.execute(
            text("SELECT narrative_id, narrative FROM pain_narratives_app.narratives "
                 "WHERE narrative IS NOT NULL")
        ).fetchall()
    out: dict[int, int] = {}
    for nid, narr in rows:
        h = hashlib.sha256(narr.strip().encode("utf-8")).hexdigest()
        pid = pid_by_hash.get(h)
        if pid is not None:
            out[nid] = pid
    return out


def _ingest_dimensions(db: DatabaseManager, pid_lookup: dict[int, int]) -> int:
    with db.engine.connect() as conn:
        src = pd.read_sql(text(
            "SELECT id, experiment_id, experiments_group_id, user_id, narrative_id, "
            "intensity_score_alignment, intensity_explanation_alignment, intensity_usage_intent, "
            "disability_score_alignment, disability_explanation_alignment, disability_usage_intent, "
            "dimension_feedback "
            "FROM pain_narratives_app.assessment_feedback"
        ), conn)

    src["participant_id"] = src["narrative_id"].map(pid_lookup)
    n_drop = src["participant_id"].isna().sum()
    if n_drop:
        print(f"  assessment_feedback: dropped {n_drop}/{len(src)} rows (narrative not in target)")
    src = src.dropna(subset=["participant_id"]).copy()
    src["participant_id"] = src["participant_id"].astype(int)

    # The source's `intensity_*` columns map to our `severidad_*` columns
    # (the original column naming used "intensity" for severity Likert ratings).
    out = pd.DataFrame({
        "experiment_id": src["experiment_id"],
        "participant_id": src["participant_id"].astype(float),
        "narrative_id": src["narrative_id"],
        "narrative_hash": None,
        "experiments_group_id": src["experiments_group_id"],
        "user_id": src["user_id"],
        "word_count": None,
        "severidad_score_alignment": src["intensity_score_alignment"],
        "severidad_explanation_alignment": src["intensity_explanation_alignment"],
        "severidad_usage_intent": src["intensity_usage_intent"],
        "discapacidad_score_alignment": src["disability_score_alignment"],
        "discapacidad_explanation_alignment": src["disability_explanation_alignment"],
        "discapacidad_usage_intent": src["disability_usage_intent"],
        "extended_dimensions": src["dimension_feedback"].apply(
            lambda v: json.dumps(v) if isinstance(v, dict) else v
        ),
    })
    out.to_sql("expert_dimension_evaluation", db.engine, schema=SCHEMA,
               if_exists="append", index=False, method="multi")
    return len(out)


def _ingest_questionnaire(db: DatabaseManager, pid_lookup: dict[int, int]) -> int:
    with db.engine.connect() as conn:
        src = pd.read_sql(text(
            "SELECT id, experiment_id, experiments_group_id, user_id, narrative_id, "
            "questionnaire_id, questionnaire_name, authenticity_rating, reasoning_adequacy_rating "
            "FROM pain_narratives_app.questionnaire_feedback"
        ), conn)

    src["participant_id"] = src["narrative_id"].map(pid_lookup)
    n_drop = src["participant_id"].isna().sum()
    if n_drop:
        print(f"  questionnaire_feedback: dropped {n_drop}/{len(src)} rows")
    src = src.dropna(subset=["participant_id"]).copy()
    src["participant_id"] = src["participant_id"].astype(int)

    out = pd.DataFrame({
        "questionnaire_id": src["questionnaire_id"],
        "participant_id": src["participant_id"].astype(float),
        "narrative_id": src["narrative_id"],
        "narrative_hash": None,
        "experiments_group_id": src["experiments_group_id"],
        "user_id": src["user_id"],
        "questionnaire_name": src["questionnaire_name"],
        "authenticity_rating": src["authenticity_rating"],
        "reasoning_adequacy_rating": src["reasoning_adequacy_rating"],
        "word_count": None,
    })
    # Drop duplicate questionnaire_id (PK) rows defensively
    out = out.drop_duplicates(subset=["questionnaire_id"], keep="last")
    out.to_sql("expert_questionnaire_feedback", db.engine, schema=SCHEMA,
               if_exists="append", index=False, method="multi")
    return len(out)


def main() -> int:
    db = DatabaseManager()
    print("Building source narrative_id -> target participant_id map...")
    pid_lookup = _source_narrative_id_to_target_pid(db)
    print(f"  bridged {len(pid_lookup)} source narrative_ids to target participants")

    with db.engine.begin() as conn:
        for table in ("expert_dimension_evaluation", "expert_questionnaire_feedback"):
            conn.execute(text(f"TRUNCATE TABLE {SCHEMA}.{table} CASCADE"))

    print("\nIngesting assessment_feedback -> expert_dimension_evaluation")
    n_dim = _ingest_dimensions(db, pid_lookup)
    print(f"  inserted {n_dim} rows")

    print("\nIngesting questionnaire_feedback -> expert_questionnaire_feedback")
    n_q = _ingest_questionnaire(db, pid_lookup)
    print(f"  inserted {n_q} rows")

    print("\nVerifying:")
    with db.engine.connect() as conn:
        for table in ("expert_dimension_evaluation", "expert_questionnaire_feedback"):
            n = conn.execute(text(f"SELECT COUNT(*) FROM {SCHEMA}.{table}")).scalar()
            print(f"  {table}: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
