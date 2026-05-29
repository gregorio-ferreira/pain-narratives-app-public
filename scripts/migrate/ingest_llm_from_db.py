"""Populate ``ai_narratives_original.llm_*_results`` for every model in MODEL_CONFIGS.

Idempotent: truncates each LLM table once, then inserts results for all models.

Source: ``pain_narratives_app.experiments_list`` + ``pain_narratives_app.evaluation_results``
plus ``pain_narratives_app.narratives`` for the source-side narrative_id → narrative_hash
bridge.

Target side uses ``ai_narratives_original.narratives`` (which we populated from the
Qualtrics raw export). Join key between source and target: ``narrative_hash``
(stripped SHA-256 of the narrative text), which we computed identically on both sides.

Usage::

    uv run python scripts/migrate/ingest_llm_from_db.py
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import text

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

from pain_narratives.analysis.revision_data_layer import (  # noqa: E402
    MODEL_CONFIGS,
    _parse_bpi,
    _parse_dimensions,
    _parse_pcs,
    _parse_tsk,
    _GPT5_GROUP_TO_RUN,
)
from pain_narratives.core.database import DatabaseManager  # noqa: E402

SCHEMA = "ai_narratives_original"

RESULT_PARSERS = {
    "dimensions": _parse_dimensions,
    "PCS": _parse_pcs,
    "BPI-IS": _parse_bpi,
    "TSK-11SV": _parse_tsk,
}
TARGET_TABLE = {
    "dimensions": "llm_dimension_evaluation",
    "PCS": "llm_pcs_results",
    "BPI-IS": "llm_bpi_results",
    "TSK-11SV": "llm_tsk_results",
}


def _hash_to_participant_map(db: DatabaseManager) -> dict[str, int]:
    """narrative_hash -> ai_narratives_original.narratives.narrative_id (== participant_id)."""
    with db.engine.connect() as conn:
        rows = conn.execute(
            text(f"SELECT narrative_hash, narrative_id FROM {SCHEMA}.narratives")
        ).fetchall()
    return {h: nid for h, nid in rows}


def _source_narrative_id_to_hash(db: DatabaseManager) -> dict[int, str]:
    """source narrative_id -> SHA-256(stripped source text).

    The legacy `narrative_hash` column on `pain_narratives_app.narratives` uses
    an unknown hashing scheme that does not match our SHA-256(stripped) hashes.
    We recompute on the fly from the source text so the bridge to the target
    schema works.
    """
    with db.engine.connect() as conn:
        rows = conn.execute(
            text("SELECT narrative_id, narrative FROM pain_narratives_app.narratives "
                 "WHERE narrative IS NOT NULL")
        ).fetchall()
    return {nid: hashlib.sha256(narr.strip().encode("utf-8")).hexdigest()
            for nid, narr in rows}


def _load_experiments(db: DatabaseManager, group_ids: list[int]) -> pd.DataFrame:
    with db.engine.connect() as conn:
        return pd.read_sql(
            text(
                """
                SELECT experiment_id, experiments_group_id, narrative_id
                FROM pain_narratives_app.experiments_list
                WHERE experiments_group_id = ANY(:gids)
                  AND succeeded = TRUE
                """
            ),
            conn,
            params={"gids": group_ids},
        )


def _load_evals(db: DatabaseManager, group_ids: list[int]) -> pd.DataFrame:
    with db.engine.connect() as conn:
        return pd.read_sql(
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


def _run_number_for(model_tag: str, group_id: int, ordering: dict[int, int]) -> int:
    if model_tag == "gpt-5":
        return _GPT5_GROUP_TO_RUN.get(group_id, ordering[group_id])
    return ordering[group_id]


def _build_rows_for_model(
    model_tag: str,
    group_ids: tuple[int, ...],
    db: DatabaseManager,
    src_hash_lookup: dict[int, str],
    target_pid_lookup: dict[str, int],
) -> dict[str, list[dict]]:
    """Returns {table_name: [rows]} for the four LLM tables for one model."""
    ordering = {gid: i + 1 for i, gid in enumerate(group_ids)}
    exp = _load_experiments(db, list(group_ids))
    evals = _load_evals(db, list(group_ids))

    # Per-experiment metadata: participant_id (target side) + run_number + experiments_group_id
    exp = exp.assign(
        narrative_hash=exp["narrative_id"].map(src_hash_lookup),
    )
    exp["participant_id"] = exp["narrative_hash"].map(target_pid_lookup)
    missing_pid = exp["participant_id"].isna().sum()
    if missing_pid:
        print(f"  {model_tag}: WARNING {missing_pid}/{len(exp)} experiments dropped "
              f"(narrative_hash not in target schema)")
    exp = exp.dropna(subset=["participant_id"]).copy()
    exp["participant_id"] = exp["participant_id"].astype(int)
    exp["run_number"] = exp["experiments_group_id"].map(
        lambda gid: _run_number_for(model_tag, int(gid), ordering)
    )

    # Build per-experiment shell rows for each table
    shells = {
        "llm_dimension_evaluation": [],
        "llm_pcs_results": [],
        "llm_bpi_results": [],
        "llm_tsk_results": [],
    }
    exp_meta = exp.set_index("experiment_id")[
        ["participant_id", "run_number", "experiments_group_id"]
    ].to_dict("index")

    # Group eval rows by experiment_id
    eval_by_exp: dict[int, dict[str, dict]] = {}
    for _, r in evals.iterrows():
        if r.experiment_id not in exp_meta:
            continue
        parser = RESULT_PARSERS.get(r.result_type)
        if parser is None:
            continue
        parsed = parser(r.result_json)
        eval_by_exp.setdefault(r.experiment_id, {})[r.result_type] = parsed

    seen = {tag: set() for tag in shells}  # to dedupe on (participant_id, model, run_number)
    for eid, meta in exp_meta.items():
        parsed_per_rtype = eval_by_exp.get(eid, {})
        key = (meta["participant_id"], model_tag, meta["run_number"])
        base = {
            "participant_id": meta["participant_id"],
            "model": model_tag,
            "run_number": meta["run_number"],
            "experiment_id": eid,
            "experiments_group_id": int(meta["experiments_group_id"]),
        }
        for rtype, parsed in parsed_per_rtype.items():
            table = TARGET_TABLE[rtype]
            if key in seen[table]:
                continue  # avoid duplicate PK if a stray repeat exists
            seen[table].add(key)
            shells[table].append({**base, **parsed})
    return shells


def main() -> int:
    db = DatabaseManager()
    print("Building target hash -> participant_id map...")
    target_pid = _hash_to_participant_map(db)
    print(f"  target schema has {len(target_pid)} narratives")

    print("Loading source narrative_id -> hash map...")
    src_hash = _source_narrative_id_to_hash(db)
    print(f"  source schema has {len(src_hash)} narrative_id rows")

    # Truncate target LLM tables before inserts
    with db.engine.begin() as conn:
        for table in (
            "llm_dimension_evaluation",
            "llm_pcs_results",
            "llm_bpi_results",
            "llm_tsk_results",
        ):
            conn.execute(text(f"TRUNCATE TABLE {SCHEMA}.{table} CASCADE"))

    aggregate_rows: dict[str, list[dict]] = {
        "llm_dimension_evaluation": [],
        "llm_pcs_results": [],
        "llm_bpi_results": [],
        "llm_tsk_results": [],
    }

    for tag, cfg in MODEL_CONFIGS.items():
        if cfg.source != "db":
            continue
        print(f"\nProcessing {tag} (groups {cfg.group_ids})")
        per_model = _build_rows_for_model(
            tag, cfg.group_ids, db, src_hash, target_pid
        )
        for table, rows in per_model.items():
            aggregate_rows[table].extend(rows)
            print(f"  {table}: {len(rows)} rows")

    print("\nInserting into target tables...")
    for table, rows in aggregate_rows.items():
        if not rows:
            print(f"  {table}: nothing to insert")
            continue
        df = pd.DataFrame(rows)
        # Drop any non-schema columns the parsers might emit (e.g. bpiq14 stored as None)
        df.to_sql(table, db.engine, schema=SCHEMA, if_exists="append",
                  index=False, method="multi", chunksize=200)
        print(f"  {table}: inserted {len(df)}")

    print("\nVerifying:")
    expected_per_table = 152 * 3 * 3  # 152 narratives * 3 runs * 3 models
    with db.engine.connect() as conn:
        for table in aggregate_rows:
            n = conn.execute(text(f"SELECT COUNT(*) FROM {SCHEMA}.{table}")).scalar()
            per_model = conn.execute(
                text(f"SELECT model, COUNT(*) FROM {SCHEMA}.{table} GROUP BY model ORDER BY model")
            ).fetchall()
            print(f"  {table}: total={n} (expect ~{expected_per_table})")
            for m, c in per_model:
                print(f"      {m}: {c}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
