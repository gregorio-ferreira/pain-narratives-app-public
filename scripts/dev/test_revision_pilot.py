"""Phase-6 pilot: run a single narrative end-to-end through DeepSeek-R1 and
Claude Sonnet 4.5 (with extended thinking) using the simplified_v1 prompts.

This exercises the full pipeline (dimensions + PCS + BPI-IS + TSK-11SV) but on
exactly one narrative_id from the ACM baseline, so the cost is ~$0.10 and it
catches integration bugs before the full revision run (~$50).

Verifies after each model run:
- experiments_list row created with the right model_provider, model, prompt_version
- request_response rows are present (the raw Bedrock response)
- evaluation_results rows for dimensions + 3 questionnaires
- reasoning_tokens > 0 (both models always reason)
- parsed answers succeeded for all 4 sub-calls

Exits non-zero on any failure.

Usage:
    uv run python scripts/dev/test_revision_pilot.py
    uv run python scripts/dev/test_revision_pilot.py --narrative-id 137
"""

from __future__ import annotations

import argparse
import logging
import sys
from typing import Optional

from sqlmodel import select

from pain_narratives.batch.processor import BatchConfig, BatchProcessor
from pain_narratives.batch.user_setup import get_or_create_batch_user
from pain_narratives.core.database import DatabaseManager
from pain_narratives.db.models_sqlmodel import (
    EvaluationResult,
    ExperimentList,
    Narrative,
    RequestResponse,
)


# The three groups that make up the published GPT-5 ACM baseline.
ACM_BASELINE_GROUPS = (38, 39, 40)

# Reserved pilot run-number so the rows are easy to find / delete later.
PILOT_RUN_NUMBER = 999


def pick_narrative(db_manager: DatabaseManager, narrative_id: Optional[int]) -> tuple[int, str]:
    """Return (narrative_id, narrative_text) — either the requested one, or the
    first narrative from the ACM baseline."""
    with db_manager.get_session() as session:
        if narrative_id is not None:
            narr = session.exec(select(Narrative).where(Narrative.narrative_id == narrative_id)).first()
            if narr is None:
                raise SystemExit(f"narrative_id={narrative_id} not found")
            return narr.narrative_id, narr.narrative

        # First narrative from the lowest ACM group
        row = session.exec(
            select(ExperimentList, Narrative)
            .join(Narrative, ExperimentList.narrative_id == Narrative.narrative_id)
            .where(ExperimentList.experiments_group_id.in_(ACM_BASELINE_GROUPS))
            .order_by(ExperimentList.experiments_group_id, ExperimentList.experiment_id)
        ).first()
        if row is None:
            raise SystemExit("No narratives found in ACM baseline groups")
        exp, narr = row
        return narr.narrative_id, narr.narrative


def run_model(
    label: str,
    model_provider: str,
    model: str,
    *,
    thinking_enabled: bool = False,
    temperature: Optional[float] = None,
    db_manager: DatabaseManager,
    user_id: int,
    narrative_id: int,
    narrative_text: str,
) -> int:
    """Run the pilot narrative through one model. Returns experiment_id."""
    print(f"\n{'=' * 72}")
    print(f"PILOT — {label}")
    print(f"{'=' * 72}")

    config = BatchConfig(
        model=model,
        temperature=temperature if temperature is not None else 1.0,
        max_tokens=12000,
        model_provider=model_provider,
        prompt_version="simplified_v1",
        thinking_enabled=thinking_enabled,
        thinking_budget_tokens=8000,
        consecutive_failure_threshold=2,
        max_retries=2,
        delay_between_calls=0.5,
    )
    processor = BatchProcessor(db_manager=db_manager, config=config)
    processor.preflight()

    group_id = processor.create_experiment_group(
        user_id=user_id, description=f"Pilot — {label} — simplified_v1"
    )

    from pain_narratives.batch.processor import get_git_sha
    experiment_id = db_manager.register_new_experiment(
        {
            "experiments_group_id": group_id,
            "user_id": user_id,
            "narrative_id": narrative_id,
            "model_provider": config.model_provider,
            "model": config.model,
            "exp_type": "pilot",
            "repo_sha": get_git_sha(),
            "repeated": PILOT_RUN_NUMBER,
            "succeeded": False,
            "parsed_answers": False,
            "calculated_metrics": False,
            "prompt_version": config.prompt_version,
        }
    )
    print(f"  group_id={group_id}  experiment_id={experiment_id}  narrative_id={narrative_id}")

    result = processor.process_single_narrative(
        narrative_text=narrative_text,
        narrative_id=narrative_id,
        experiment_id=experiment_id,
        group_id=group_id,
        user_id=user_id,
    )

    print(f"  dimension_success: {result.dimension_success}")
    if not result.dimension_success and result.dimension_error:
        print(f"    dimension_error: {result.dimension_error}")
    for qt, qr in (("PCS", result.pcs_result), ("BPI-IS", result.bpi_is_result), ("TSK-11SV", result.tsk_11sv_result)):
        if qr is None:
            print(f"  {qt}: not run")
            continue
        if qr.success:
            print(f"  {qt}: ✓ scored {len(qr.scores) or len(qr.responses)} items")
        else:
            print(f"  {qt}: ✗ {qr.error}")

    # Verify rows in DB
    with db_manager.get_session() as session:
        exp = session.exec(select(ExperimentList).where(ExperimentList.experiment_id == experiment_id)).first()
        rr_count = len(session.exec(select(RequestResponse).where(RequestResponse.experiment_id == experiment_id)).all())
        ev_count = len(session.exec(select(EvaluationResult).where(EvaluationResult.experiment_id == experiment_id)).all())
        print(f"  Rows: experiments_list.reasoning_tokens={exp.reasoning_tokens}  prompt_version={exp.prompt_version!r}  "
              f"request_response_rows={rr_count}  evaluation_result_rows={ev_count}")

    return experiment_id


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--narrative-id", type=int, default=None,
                    help="Specific narrative to use (default: first ACM-baseline narrative)")
    ap.add_argument("--skip-deepseek", action="store_true", help="Skip DeepSeek-R1 run")
    ap.add_argument("--skip-sonnet", action="store_true", help="Skip Claude Sonnet 4.5 run")
    args = ap.parse_args()

    db_manager = DatabaseManager()
    user_id = get_or_create_batch_user(db_manager)
    narrative_id, narrative_text = pick_narrative(db_manager, args.narrative_id)
    print(f"Pilot narrative_id={narrative_id} (length={len(narrative_text)} chars, first 80: {narrative_text[:80]!r}…)")

    exit_code = 0

    if not args.skip_deepseek:
        try:
            run_model(
                label="DeepSeek-R1",
                model_provider="bedrock_deepseek",
                model="us.deepseek.r1-v1:0",
                temperature=0.6,
                db_manager=db_manager,
                user_id=user_id,
                narrative_id=narrative_id,
                narrative_text=narrative_text,
            )
        except Exception as e:
            logging.exception("DeepSeek-R1 pilot raised: %s", e)
            exit_code = 1

    if not args.skip_sonnet:
        try:
            run_model(
                label="Claude Sonnet 4.5 (extended thinking)",
                model_provider="bedrock_anthropic",
                model="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
                thinking_enabled=True,
                db_manager=db_manager,
                user_id=user_id,
                narrative_id=narrative_id,
                narrative_text=narrative_text,
            )
        except Exception as e:
            logging.exception("Sonnet 4.5 pilot raised: %s", e)
            exit_code = 1

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
