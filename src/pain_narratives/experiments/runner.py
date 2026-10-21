"""Compatibility CLI backed by the maintained batch processor."""

import argparse

from pain_narratives.batch.processor import BatchConfig, BatchProcessor
from pain_narratives.core.database import DatabaseManager


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate existing narratives using the maintained batch pipeline")
    parser.add_argument("--user-id", type=int, required=True, help="Explicit administrator/automation owner ID")
    parser.add_argument("--models", nargs="+", default=["gpt-5-mini"])
    parser.add_argument("--temperatures", type=float, nargs="+", default=[1.0])
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    if args.repetitions < 1 or (args.limit is not None and args.limit < 1):
        parser.error("repetitions and limit must be positive")
    db = DatabaseManager()
    if not db.is_user_admin(args.user_id):
        parser.error("The owner must be an administrator/automation identity")
    records = db.get_narratives()
    narratives = [{"narrative_id": n.narrative_id, "narrative_text": n.narrative} for n in records if n.narrative]
    if args.limit:
        narratives = narratives[: args.limit]
    for model in args.models:
        for temperature in args.temperatures:
            processor = BatchProcessor(config=BatchConfig(model=model, temperature=temperature), db_manager=db)
            for repetition in range(1, args.repetitions + 1):
                processor.run_batch_with_existing_narratives(
                    narratives=narratives,
                    user_id=args.user_id,
                    group_description=f"Experiment: {model}, repetition {repetition}",
                    run_number=repetition,
                )


if __name__ == "__main__":
    main()
