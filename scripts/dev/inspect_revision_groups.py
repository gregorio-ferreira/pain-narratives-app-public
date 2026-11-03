"""
Read-only provenance check of the experiment groups used in the revision analyses.

Answers, without writing anything to the database:

1. Per experiment group: model, prompt_version, number of experiments and
   narratives, and whether the stored results contain `persona`,
   `model_reasoning` and dimension explanations.
2. For a set of narrative ids (default: the five shortest in the ACM baseline),
   which groups evaluated them and whether persona / explanations are available.
3. The history of questionnaire prompts (distinct system_role + instructions per
   questionnaire, by group), as evidence of how the prompts evolved.

Narrative text and model outputs are never printed, only counts, flags and hashes.

Usage:
    uv run python scripts/dev/inspect_revision_groups.py
    uv run python scripts/dev/inspect_revision_groups.py --min-group 30 --max-group 55 \
        --narrative-ids 246,216,247,274,207
"""

from __future__ import annotations

import argparse

import pandas as pd
from sqlalchemy import create_engine, event, text

from pain_narratives.config.settings import get_settings

DEFAULT_NARRATIVE_IDS = "246,216,247,274,207"

GROUPS_QUERY = text("""
    WITH exp AS (
        SELECT el.experiment_id, el.experiments_group_id, el.narrative_id,
               el.succeeded, el.prompt_version
        FROM pain_narratives_app.experiments_list el
        WHERE el.experiments_group_id BETWEEN :gmin AND :gmax
    ),
    models AS (
        SELECT e.experiments_group_id,
               string_agg(DISTINCT rr.request_json ->> 'model', ', ') AS models
        FROM exp e
        JOIN pain_narratives_app.request_response rr ON rr.experiment_id = e.experiment_id
        GROUP BY e.experiments_group_id
    ),
    res AS (
        SELECT er.experiments_group_id,
               COUNT(*) FILTER (WHERE er.result_type <> 'dimensions')                    AS quest_results,
               COUNT(*) FILTER (WHERE er.result_type <> 'dimensions'
                                AND er.result_json::text LIKE '%"persona"%')             AS with_persona,
               COUNT(*) FILTER (WHERE er.result_type <> 'dimensions'
                                AND er.result_json::text LIKE '%model_reasoning%')       AS with_reasoning,
               COUNT(*) FILTER (WHERE er.result_type = 'dimensions')                     AS dim_results,
               COUNT(*) FILTER (WHERE er.result_type = 'dimensions'
                                AND (er.result_json::text ILIKE '%explanation%'
                                     OR er.result_json::text ILIKE '%explicaci%'))       AS dim_with_expl
        FROM pain_narratives_app.evaluation_results er
        WHERE er.experiments_group_id BETWEEN :gmin AND :gmax
        GROUP BY er.experiments_group_id
    )
    SELECT g.experiments_group_id                                   AS grp,
           g.created::date                                          AS created,
           LEFT(COALESCE(g.description, ''), 60)                    AS description,
           m.models,
           string_agg(DISTINCT COALESCE(e.prompt_version, '<null>'), ', ') AS prompt_version,
           COUNT(e.experiment_id)                                   AS n_exp,
           COUNT(e.experiment_id) FILTER (WHERE e.succeeded)        AS n_ok,
           COUNT(DISTINCT e.narrative_id)                           AS n_narr,
           MAX(r.quest_results)                                     AS quest_res,
           MAX(r.with_persona)                                      AS persona,
           MAX(r.with_reasoning)                                    AS reasoning,
           MAX(r.dim_results)                                       AS dim_res,
           MAX(r.dim_with_expl)                                     AS dim_expl
    FROM pain_narratives_app.experiments_groups g
    JOIN exp e         ON e.experiments_group_id = g.experiments_group_id
    LEFT JOIN models m ON m.experiments_group_id = g.experiments_group_id
    LEFT JOIN res r    ON r.experiments_group_id = g.experiments_group_id
    GROUP BY g.experiments_group_id, g.created, g.description, m.models
    ORDER BY g.experiments_group_id
    """)

NARRATIVES_QUERY = text("""
    SELECT el.narrative_id,
           n.word_count,
           el.experiments_group_id                                   AS grp,
           COALESCE(el.prompt_version, '<null>')                     AS prompt_version,
           COUNT(DISTINCT el.experiment_id)                          AS n_exp,
           COUNT(er.id) FILTER (WHERE er.result_json::text LIKE '%"persona"%')  AS persona,
           COUNT(er.id) FILTER (WHERE er.result_json::text LIKE '%model_reasoning%') AS reasoning,
           COUNT(er.id) FILTER (WHERE er.result_type = 'dimensions'
                                AND (er.result_json::text ILIKE '%explanation%'
                                     OR er.result_json::text ILIKE '%explicaci%')) AS dim_expl
    FROM pain_narratives_app.experiments_list el
    JOIN pain_narratives_app.narratives n ON n.narrative_id = el.narrative_id
    LEFT JOIN pain_narratives_app.evaluation_results er ON er.experiment_id = el.experiment_id
    WHERE el.narrative_id = ANY(:nids) AND el.succeeded
    GROUP BY el.narrative_id, n.word_count, el.experiments_group_id, el.prompt_version
    ORDER BY n.word_count, el.narrative_id, el.experiments_group_id
    """)

PROMPT_HISTORY_QUERY = text("""
    SELECT questionnaire_type,
           LEFT(md5(system_role || '||' || instructions), 8)        AS prompt_hash,
           LENGTH(system_role) + LENGTH(instructions)                AS prompt_chars,
           (position('"persona"' in instructions) > 0)                AS asks_persona,
           MIN(created_at)::date                                     AS first_seen,
           MAX(created_at)::date                                     AS last_seen,
           string_agg(DISTINCT experiments_group_id::text, ',')      AS groups
    FROM pain_narratives_app.questionnaire_prompts
    GROUP BY questionnaire_type, prompt_hash, prompt_chars, asks_persona
    ORDER BY questionnaire_type, first_seen
    """)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--min-group", type=int, default=30)
    parser.add_argument("--max-group", type=int, default=60)
    parser.add_argument("--narrative-ids", default=DEFAULT_NARRATIVE_IDS)
    parser.add_argument("--connect-timeout", type=int, default=10)
    args = parser.parse_args()

    engine = create_engine(
        get_settings().database_url,
        connect_args={"connect_timeout": args.connect_timeout},
    )

    @event.listens_for(engine, "connect")
    def _read_only(dbapi_conn, _record):  # type: ignore[no-untyped-def]
        with dbapi_conn.cursor() as cur:
            cur.execute("SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY")
            cur.execute("SET statement_timeout = '120s'")

    nids = [int(x) for x in args.narrative_ids.split(",") if x.strip()]
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
    pd.set_option("display.max_colwidth", 60)

    with engine.connect() as conn:
        groups = pd.read_sql(GROUPS_QUERY, conn, params={"gmin": args.min_group, "gmax": args.max_group})
        narratives = pd.read_sql(NARRATIVES_QUERY, conn, params={"nids": nids})
        prompts = pd.read_sql(PROMPT_HISTORY_QUERY, conn)

    print(f"\n=== 1. Experiment groups {args.min_group}-{args.max_group} ===")
    print(groups.to_string(index=False))
    print(f"\n=== 2. Coverage of narratives {nids} ===")
    print(narratives.to_string(index=False))
    print("\n=== 3. Questionnaire prompt history (distinct prompt texts) ===")
    print(prompts.to_string(index=False))


if __name__ == "__main__":
    main()
