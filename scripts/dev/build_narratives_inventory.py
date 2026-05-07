"""
Build a per-narrative inventory CSV with size metadata and provenance flags.

The CSV is the source of truth for `docs/revision/NARRATIVES_INVENTORY.md`. It
records, for every non-empty narrative in `pain_narratives_app.narratives`:

- char / word counts (already populated by the dedup migration)
- token counts under `o200k_base` (gpt-5 / gpt-4o) and `cl100k_base` (gpt-3.5 / gpt-4)
- whether the narrative was used in the published GPT-5 ACM batch (groups 38, 39, 40)
- whether it has human assessment / questionnaire feedback

The narrative text itself is never written to the CSV — only its hash and counts —
so the file is safe to commit alongside the markdown doc.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import tiktoken
from sqlalchemy import create_engine, text

from pain_narratives.config.settings import get_settings

# Group ids that constitute the published GPT-5 ACM Publication baseline:
# Run 2 (38), Run 3 (39), Run 4 (40). 152 narratives × 3 repetitions.
ACM_BATCH_GROUP_IDS = (38, 39, 40)
OUTPUT_PATH = Path("docs/revision/narratives_inventory.csv")


def main() -> None:
    settings = get_settings()
    engine = create_engine(settings.database_url)

    query = text(
        """
        WITH acm_runs AS (
            SELECT narrative_id, COUNT(*) AS acm_repetitions
            FROM pain_narratives_app.experiments_list
            WHERE experiments_group_id = ANY(:acm_groups)
            GROUP BY narrative_id
        ),
        assessment AS (
            SELECT narrative_id,
                   COUNT(DISTINCT user_id) AS assessment_evaluators,
                   COUNT(*)                AS assessment_rows
            FROM pain_narratives_app.assessment_feedback
            GROUP BY narrative_id
        ),
        questionnaire AS (
            SELECT narrative_id,
                   COUNT(DISTINCT user_id) AS questionnaire_evaluators,
                   COUNT(*)                AS questionnaire_rows
            FROM pain_narratives_app.questionnaire_feedback
            GROUP BY narrative_id
        )
        SELECT n.narrative_id,
               n.narrative_hash,
               n.char_count,
               n.word_count,
               n.narrative                                      AS narrative_text,
               COALESCE(a.acm_repetitions, 0)                   AS acm_repetitions,
               COALESCE(asm.assessment_evaluators, 0)           AS assessment_evaluators,
               COALESCE(asm.assessment_rows, 0)                 AS assessment_rows,
               COALESCE(q.questionnaire_evaluators, 0)          AS questionnaire_evaluators,
               COALESCE(q.questionnaire_rows, 0)                AS questionnaire_rows
        FROM pain_narratives_app.narratives n
        LEFT JOIN acm_runs       a   ON a.narrative_id   = n.narrative_id
        LEFT JOIN assessment     asm ON asm.narrative_id = n.narrative_id
        LEFT JOIN questionnaire  q   ON q.narrative_id   = n.narrative_id
        WHERE n.char_count > 0
        ORDER BY n.narrative_id
        """
    )

    df = pd.read_sql(query, engine, params={"acm_groups": list(ACM_BATCH_GROUP_IDS)})

    enc_o200k = tiktoken.get_encoding("o200k_base")
    enc_cl100k = tiktoken.get_encoding("cl100k_base")
    df["tokens_o200k"] = df["narrative_text"].map(lambda t: len(enc_o200k.encode(t)))
    df["tokens_cl100k"] = df["narrative_text"].map(lambda t: len(enc_cl100k.encode(t)))

    # Per-narrative-id flags (the row I'm currently looking at).
    df["in_acm_baseline"] = df["acm_repetitions"] > 0
    df["has_human_assessment"] = df["assessment_rows"] > 0
    df["has_human_questionnaire"] = df["questionnaire_rows"] > 0
    df["has_any_human_validation"] = df["has_human_assessment"] | df["has_human_questionnaire"]

    # Per-content-hash aggregates: useful because the same narrative content
    # often appears under several narrative_ids (one per batch run / per evaluator).
    # The published GPT-5 batch and the human evaluations use *different* narrative_ids
    # of the *same* content; without these aggregates the by-id intersection looks empty
    # even though 39 narratives by content have both synthetic and human evaluations.
    by_hash = df.groupby("narrative_hash").agg(
        hash_in_acm=("in_acm_baseline", "any"),
        hash_has_assessment=("has_human_assessment", "any"),
        hash_has_questionnaire=("has_human_questionnaire", "any"),
        hash_total_rows=("narrative_id", "count"),
    )
    by_hash["hash_has_any_human"] = by_hash["hash_has_assessment"] | by_hash["hash_has_questionnaire"]
    by_hash["hash_human_comparable"] = by_hash["hash_in_acm"] & by_hash["hash_has_any_human"]
    df = df.join(by_hash, on="narrative_hash")

    out = df[
        [
            "narrative_id",
            "narrative_hash",
            "char_count",
            "word_count",
            "tokens_o200k",
            "tokens_cl100k",
            # per narrative_id
            "in_acm_baseline",
            "acm_repetitions",
            "has_human_assessment",
            "assessment_evaluators",
            "has_human_questionnaire",
            "questionnaire_evaluators",
            "has_any_human_validation",
            # per content (hash) — same value for every row sharing the hash
            "hash_total_rows",
            "hash_in_acm",
            "hash_has_assessment",
            "hash_has_questionnaire",
            "hash_has_any_human",
            "hash_human_comparable",
        ]
    ].copy()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT_PATH, index=False)

    n_rows = len(out)
    n_unique = out["narrative_hash"].nunique()
    print(f"Wrote {OUTPUT_PATH}: {n_rows} non-empty rows ({n_unique} unique by hash)")

    # Per-narrative-id (rows) summary
    print("\nPer narrative_id:")
    print(f"  in ACM baseline (rows):             {int(out['in_acm_baseline'].sum())}")
    print(f"  with assessment_feedback:           {int(out['has_human_assessment'].sum())}")
    print(f"  with questionnaire_feedback:        {int(out['has_human_questionnaire'].sum())}")
    print(f"  with any human validation:          {int(out['has_any_human_validation'].sum())}")

    # Per content (hash) summary
    by_hash = out.drop_duplicates("narrative_hash")
    print("\nPer content (hash):")
    print(f"  unique narratives:                  {len(by_hash)}")
    print(f"  hash in ACM baseline:               {int(by_hash['hash_in_acm'].sum())}")
    print(f"  hash has any human validation:      {int(by_hash['hash_has_any_human'].sum())}")
    print(f"  hash human-comparable (ACM ∩ human):{int(by_hash['hash_human_comparable'].sum())}")

    print("\nToken-count summary (o200k_base, gpt-5 / gpt-4o):")
    for label, subset in (
        ("all rows",            out),
        ("ACM baseline only",   out[out["in_acm_baseline"]]),
        ("human-comparable",    out[out["hash_human_comparable"] & out["in_acm_baseline"]]),
    ):
        desc = subset["tokens_o200k"].describe()
        print(f"  {label:<22} n={int(desc['count']):3d}  min={int(desc['min']):4d}  median={int(desc['50%']):4d}  mean={desc['mean']:6.1f}  max={int(desc['max']):5d}")


if __name__ == "__main__":
    main()
