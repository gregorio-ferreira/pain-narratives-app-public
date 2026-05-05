#!/usr/bin/env python3
"""
Batch Evaluation Runner for Pain Narratives.

This script processes pain narratives from an Excel file, running:
- Dimension evaluation (pain severity, disability)
- PCS questionnaire (Pain Catastrophizing Scale)
- BPI-IS questionnaire (Brief Pain Inventory)
- TSK-11SV questionnaire (Tampa Scale of Kinesiophobia)

All results are stored in the existing database schema for analysis.

Usage:
    # Dry run to estimate costs
    uv run python scripts/run_batch_evaluation.py --input data/narratives.xlsx --dry-run

    # Test with a single narrative
    uv run python scripts/run_batch_evaluation.py --input data/narratives.xlsx --test-single

    # Full batch processing (creates new narratives)
    uv run python scripts/run_batch_evaluation.py --input data/narratives.xlsx --description "Batch Nov 2025"

    # Resume from checkpoint
    uv run python scripts/run_batch_evaluation.py --input data/narratives.xlsx --resume

    # Run batch repetition using existing narratives from groups 35,36 (run 1)
    # This reuses the same narrative_ids and stores run_number in 'repeated' column
    uv run python scripts/run_batch_evaluation.py \\
        --from-groups 35,36 \\
        --run-number 2 \\
        --model gpt-5 \\
        --description "Batch Run 2 - ACM Publication" \\
        --yes
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add src to path if needed
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from pain_narratives.batch.processor import BatchConfig, BatchProcessor, BatchProgress
from pain_narratives.batch.user_setup import get_or_create_batch_user
from pain_narratives.core.database import DatabaseManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


def print_progress(progress: BatchProgress) -> None:
    """Print progress to console."""
    elapsed = progress.elapsed_seconds
    remaining = progress.estimated_remaining_seconds

    elapsed_str = f"{elapsed/60:.1f}min" if elapsed > 60 else f"{elapsed:.0f}s"
    remaining_str = f"{remaining/60:.1f}min" if remaining > 60 else f"{remaining:.0f}s"

    print(
        f"\r[{progress.processed}/{progress.total}] "
        f"✓ {progress.successful} ✗ {progress.failed} | "
        f"Elapsed: {elapsed_str} | Remaining: ~{remaining_str}    ",
        end="",
        flush=True,
    )


def run_dry_run(processor: BatchProcessor, narratives_df, args: argparse.Namespace) -> None:
    """Run dry-run mode to estimate costs without processing."""
    print("\n" + "=" * 70)
    print("DRY RUN - Cost and Time Estimation")
    print("=" * 70)

    num_narratives = len(narratives_df)
    estimate = processor.estimate_batch_cost(num_narratives)

    print(f"\nNarratives to process: {estimate['num_narratives']}")
    print(f"\nEvaluations enabled:")
    print(f"  - Dimensions: {'✓' if processor.config.include_dimensions else '✗'}")
    print(f"  - PCS: {'✓' if processor.config.include_pcs else '✗'}")
    print(f"  - BPI-IS: {'✓' if processor.config.include_bpi_is else '✗'}")
    print(f"  - TSK-11SV: {'✓' if processor.config.include_tsk_11sv else '✗'}")

    print(f"\nAPI Calls:")
    print(f"  - Per narrative: {estimate['calls_per_narrative']}")
    print(f"  - Total: {estimate['total_api_calls']}")

    print(f"\nToken Estimates:")
    print(f"  - Input tokens: ~{estimate['estimated_input_tokens']:,}")
    print(f"  - Output tokens: ~{estimate['estimated_output_tokens']:,}")

    print(f"\nCost & Time Estimates:")
    print(f"  - Estimated cost: ${estimate['estimated_cost_usd']:.2f} USD")
    print(f"  - Estimated time: {estimate['estimated_time_minutes']:.1f} minutes")

    print(f"\nModel: {processor.config.model}")
    print(f"Temperature: {processor.config.temperature}")
    print(f"Delay between calls: {processor.config.delay_between_calls}s")

    # Show sample narratives
    print(f"\nSample narratives (first 3):")
    for i, (_, row) in enumerate(narratives_df.head(3).iterrows()):
        narrative = row[args.narrative_column]
        preview = narrative[:150] + "..." if len(narrative) > 150 else narrative
        print(f"  {i+1}. {preview}")

    print("\n" + "=" * 70)
    print("To proceed with actual processing, remove --dry-run flag")
    print("=" * 70 + "\n")


def run_test_single(processor: BatchProcessor, narratives_df, user_id: int, args: argparse.Namespace) -> None:
    """Run a single narrative test."""
    print("\n" + "=" * 70)
    print("SINGLE NARRATIVE TEST")
    print("=" * 70)

    # Get first narrative
    first_row = narratives_df.iloc[0]
    narrative_text = first_row[args.narrative_column]

    print(f"\nNarrative preview:")
    print(f"  {narrative_text[:300]}...")
    print(f"\nProcessing with {processor.config.model}...")
    print("This will create a test experiment group in the database.\n")

    # Run single test
    result = processor.run_single_test(
        narrative_text=narrative_text,
        user_id=user_id,
        group_description=f"Single Test - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
    )

    # Print results
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)

    print(f"\nNarrative ID: {result.narrative_id}")
    print(f"Experiment ID: {result.experiment_id}")

    # Dimension results
    if processor.config.include_dimensions:
        print(f"\n--- Dimension Evaluation ---")
        print(f"Success: {'✓' if result.dimension_success else '✗'}")
        if result.dimension_success:
            dim_result = result.dimension_result
            # Try to print key dimension scores
            for key in ["severidad_del_dolor", "discapacidad", "pain_severity", "disability"]:
                if key in dim_result:
                    print(f"  {key}: {dim_result[key]}")
        if result.dimension_error:
            print(f"Error: {result.dimension_error}")

    # PCS results
    if processor.config.include_pcs and result.pcs_result:
        print(f"\n--- PCS Questionnaire ---")
        print(f"Success: {'✓' if result.pcs_result.success else '✗'}")
        if result.pcs_result.success:
            from pain_narratives.core.questionnaire_runner import calculate_pcs_total_score

            total = calculate_pcs_total_score(result.pcs_result)
            print(f"Total Score: {total} (range 0-52)")
            print(f"Questionnaire ID: {result.pcs_questionnaire_id}")
        if result.pcs_result.error:
            print(f"Error: {result.pcs_result.error}")

    # BPI-IS results
    if processor.config.include_bpi_is and result.bpi_is_result:
        print(f"\n--- BPI-IS Questionnaire ---")
        print(f"Success: {'✓' if result.bpi_is_result.success else '✗'}")
        if result.bpi_is_result.success:
            from pain_narratives.core.questionnaire_runner import calculate_bpi_is_subscales

            subscales = calculate_bpi_is_subscales(result.bpi_is_result)
            print(f"Interference Average: {subscales['interference_avg']}")
            print(f"Intensity Average: {subscales['intensity_avg']}")
            print(f"Questionnaire ID: {result.bpi_is_questionnaire_id}")
        if result.bpi_is_result.error:
            print(f"Error: {result.bpi_is_result.error}")

    # TSK-11SV results
    if processor.config.include_tsk_11sv and result.tsk_11sv_result:
        print(f"\n--- TSK-11SV Questionnaire ---")
        print(f"Success: {'✓' if result.tsk_11sv_result.success else '✗'}")
        if result.tsk_11sv_result.success:
            from pain_narratives.core.questionnaire_runner import calculate_tsk_11sv_total_score

            total = calculate_tsk_11sv_total_score(result.tsk_11sv_result)
            print(f"Total Score: {total} (range 11-44)")
            print(f"Questionnaire ID: {result.tsk_11sv_questionnaire_id}")
        if result.tsk_11sv_result.error:
            print(f"Error: {result.tsk_11sv_result.error}")

    print("\n" + "=" * 70)
    print("Test complete! Check the database for full results.")
    print("=" * 70 + "\n")


def run_batch_repetition(processor: BatchProcessor, user_id: int, args: argparse.Namespace) -> None:
    """Run batch repetition using existing narratives."""
    print("\n" + "=" * 70)
    print(f"BATCH REPETITION - Run {args.run_number}")
    print("=" * 70)

    # Parse group IDs
    group_ids = [int(g.strip()) for g in args.from_groups.split(",")]
    print(f"\nLoading narratives from experiment groups: {group_ids}")

    # Load existing narratives
    narratives = processor.load_narratives_from_multiple_groups(group_ids)
    num_narratives = len(narratives)

    if num_narratives == 0:
        print("ERROR: No narratives found in the specified groups.")
        return

    estimate = processor.estimate_batch_cost(num_narratives)

    print(f"\nNarratives loaded: {num_narratives}")
    print(f"Estimated cost: ${estimate['estimated_cost_usd']:.2f} USD")
    print(f"Estimated time: {estimate['estimated_time_minutes']:.1f} minutes")
    print(f"Model: {processor.config.model}")
    print(f"Run number: {args.run_number}")
    print(f"Description: {args.description}")

    if not args.yes:
        response = input("\nProceed? [y/N]: ").strip().lower()
        if response != "y":
            print("Aborted.")
            return

    print("\nStarting batch repetition...")
    print("-" * 70)

    # Set progress callback
    processor.set_progress_callback(print_progress)

    # Run batch with existing narratives
    results = processor.run_batch_with_existing_narratives(
        narratives=narratives,
        user_id=user_id,
        group_description=args.description,
        run_number=args.run_number,
        resume=args.resume,
    )

    # Print final summary
    print("\n\n" + "=" * 70)
    print(f"BATCH REPETITION RUN {args.run_number} COMPLETE")
    print("=" * 70)

    successful = sum(1 for r in results if r.dimension_success or (r.pcs_result and r.pcs_result.success))
    failed = len(results) - successful

    print(f"\nTotal processed: {len(results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")

    if results:
        # Get group ID from first result
        first_exp_id = results[0].experiment_id
        if first_exp_id:
            with processor.db_manager.get_session() as session:
                from sqlmodel import select

                from pain_narratives.db.models_sqlmodel import ExperimentList

                exp = session.exec(select(ExperimentList).where(ExperimentList.experiment_id == first_exp_id)).first()
                if exp:
                    print(f"\nExperiment Group ID: {exp.experiments_group_id}")
                    print(f"Run Number (repeated): {exp.repeated}")
                    print("\nUse this group ID for extraction in notebook 04.")

    print("\n" + "=" * 70 + "\n")


def run_full_batch(processor: BatchProcessor, narratives_df, user_id: int, args: argparse.Namespace) -> None:
    """Run full batch processing."""
    print("\n" + "=" * 70)
    print("BATCH PROCESSING")
    print("=" * 70)

    num_narratives = len(narratives_df)
    estimate = processor.estimate_batch_cost(num_narratives)

    print(f"\nNarratives: {num_narratives}")
    print(f"Estimated cost: ${estimate['estimated_cost_usd']:.2f} USD")
    print(f"Estimated time: {estimate['estimated_time_minutes']:.1f} minutes")
    print(f"Model: {processor.config.model}")
    print(f"Description: {args.description}")

    if not args.yes:
        response = input("\nProceed? [y/N]: ").strip().lower()
        if response != "y":
            print("Aborted.")
            return

    print("\nStarting batch processing...")
    print("-" * 70)

    # Set progress callback
    processor.set_progress_callback(print_progress)

    # Run batch
    results = processor.run_batch(
        narratives_df=narratives_df,
        user_id=user_id,
        group_description=args.description,
        narrative_column=args.narrative_column,
        resume=args.resume,
    )

    # Print final summary
    print("\n\n" + "=" * 70)
    print("BATCH COMPLETE")
    print("=" * 70)

    successful = sum(1 for r in results if r.dimension_success or (r.pcs_result and r.pcs_result.success))
    failed = len(results) - successful

    print(f"\nTotal processed: {len(results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")

    if results:
        # Get group ID from first result
        first_exp_id = results[0].experiment_id
        if first_exp_id:
            with processor.db_manager.get_session() as session:
                from sqlmodel import select

                from pain_narratives.db.models_sqlmodel import ExperimentList

                exp = session.exec(select(ExperimentList).where(ExperimentList.experiment_id == first_exp_id)).first()
                if exp:
                    print(f"\nExperiment Group ID: {exp.experiments_group_id}")
                    print("\nTo analyze results, use this group ID in your notebooks.")

    print("\n" + "=" * 70 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Batch process pain narratives for LLM evaluation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Input options
    parser.add_argument(
        "--input",
        "-i",
        help="Path to Excel file with narratives (not required when using --from-groups)",
    )
    parser.add_argument(
        "--narrative-column",
        "-c",
        default="narrative",
        help="Column name containing narrative text (default: narrative)",
    )
    parser.add_argument(
        "--sheet",
        default=0,
        help="Sheet name or index (default: 0)",
    )
    parser.add_argument(
        "--filter-column",
        help="Column name to filter narratives by (e.g., 'Valid')",
    )
    parser.add_argument(
        "--filter-value",
        type=int,
        help="Value to filter for in filter-column (e.g., 1)",
    )

    # Mode options
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Estimate costs without processing",
    )
    parser.add_argument(
        "--test-single",
        action="store_true",
        help="Test with first narrative only",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from checkpoint",
    )

    # Repetition mode options (for running multiple identical runs)
    parser.add_argument(
        "--run-number",
        type=int,
        help="Run number for batch repetitions (stored in 'repeated' column). "
        "Use with --from-groups to reuse existing narratives.",
    )
    parser.add_argument(
        "--from-groups",
        type=str,
        help="Comma-separated experiment group IDs to load narratives from "
        "(e.g., '35,36' for narratives from run 1). "
        "Reuses existing narrative_ids instead of creating new ones.",
    )

    # Batch options
    parser.add_argument(
        "--description",
        "-d",
        default=f"Batch Processing - {datetime.now().strftime('%Y-%m-%d')}",
        help="Description for the experiment group",
    )
    parser.add_argument(
        "--batch-user",
        default="batch_processor",
        help="Username for batch processing (default: batch_processor)",
    )

    # Processing options
    parser.add_argument(
        "--model",
        default="gpt-5-mini",
        help="OpenAI model to use (default: gpt-5-mini)",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Temperature for generation (default: 0.0)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay between API calls in seconds (default: 1.0)",
    )
    parser.add_argument(
        "--checkpoint",
        help="Path to checkpoint file for resume capability",
    )

    # Evaluation toggles
    parser.add_argument(
        "--skip-dimensions",
        action="store_true",
        help="Skip dimension evaluation",
    )
    parser.add_argument(
        "--skip-pcs",
        action="store_true",
        help="Skip PCS questionnaire",
    )
    parser.add_argument(
        "--skip-bpi-is",
        action="store_true",
        help="Skip BPI-IS questionnaire",
    )
    parser.add_argument(
        "--skip-tsk",
        action="store_true",
        help="Skip TSK-11SV questionnaire",
    )

    # Other options
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip confirmation prompt",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Set log level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Validate arguments for repetition mode
    if args.run_number is not None and not args.from_groups:
        logger.error("--run-number requires --from-groups to specify source narratives")
        sys.exit(1)
    if args.from_groups and args.run_number is None:
        logger.error("--from-groups requires --run-number to specify the run number")
        sys.exit(1)
    if not args.from_groups and not args.input:
        logger.error("--input is required when not using --from-groups")
        sys.exit(1)

    # Create configuration
    config = BatchConfig(
        model=args.model,
        temperature=args.temperature,
        delay_between_calls=args.delay,
        include_dimensions=not args.skip_dimensions,
        include_pcs=not args.skip_pcs,
        include_bpi_is=not args.skip_bpi_is,
        include_tsk_11sv=not args.skip_tsk,
        checkpoint_file=args.checkpoint,
    )

    # Initialize components
    logger.info("Initializing batch processor...")
    db_manager = DatabaseManager()
    processor = BatchProcessor(db_manager=db_manager, config=config)

    # Repetition mode: load narratives from existing experiment groups
    if args.from_groups:
        logger.info(f"Running batch repetition mode (run {args.run_number})")
        user_id = get_or_create_batch_user(db_manager, username=args.batch_user)
        logger.info(f"Using batch user ID: {user_id}")
        run_batch_repetition(processor, user_id, args)
        return

    # Standard mode: load narratives from Excel file
    # Validate input file
    input_path = Path(args.input)
    if not input_path.exists():
        logger.error(f"Input file not found: {args.input}")
        sys.exit(1)

    # Load narratives from Excel
    logger.info(f"Loading narratives from: {args.input}")
    try:
        narratives_df = processor.load_narratives_from_excel(
            file_path=args.input,
            narrative_column=args.narrative_column,
            sheet_name=args.sheet if isinstance(args.sheet, int) else args.sheet,
            filter_column=args.filter_column,
            filter_value=args.filter_value,
        )
    except Exception as e:
        logger.error(f"Failed to load Excel file: {e}")
        sys.exit(1)

    logger.info(f"Loaded {len(narratives_df)} narratives")

    # Get or create batch user
    if not args.dry_run:
        user_id = get_or_create_batch_user(db_manager, username=args.batch_user)
        logger.info(f"Using batch user ID: {user_id}")
    else:
        user_id = None

    # Run appropriate mode
    if args.dry_run:
        run_dry_run(processor, narratives_df, args)
    elif args.test_single:
        run_test_single(processor, narratives_df, user_id, args)
    else:
        run_full_batch(processor, narratives_df, user_id, args)


if __name__ == "__main__":
    main()
