"""Experiment execution and management."""

import argparse
import logging
from datetime import datetime
from typing import Optional

import git
import pandas as pd

from pain_narratives.config.settings import get_settings
from pain_narratives.core.analytics import get_default_system_prompt, parse_answers
from pain_narratives.core.database import get_database_manager
from pain_narratives.core.openai_client import get_openai_client, send_to_db_request_response


class ExperimentRunner:
    """Manages and executes pain narrative evaluation experiments."""

    def __init__(self) -> None:
        """Initialize the experiment runner."""
        self.settings = get_settings()
        self.db_manager = get_database_manager()
        self.openai_client = get_openai_client()

        # Get current commit SHA for experiment tracking
        try:
            repo = git.Repo(search_parent_directories=True)
            self.repo_commit_sha = repo.head.object.hexsha
        except Exception as e:
            logging.warning(f"Could not get git commit SHA: {e}")
            self.repo_commit_sha = "unknown"

    def create_experiment_group(
        self, description: str, system_role: Optional[str] = None, base_prompt: str = ""
    ) -> int:
        """Create a new experiment group.

        Args:
            description: Description of the experiment group
            system_role: System role prompt (defaults to standard prompt)
            base_prompt: Base prompt for the experiment

        Returns:
            Experiment group ID
        """
        if system_role is None:
            system_role = get_default_system_prompt()

        return self.db_manager.register_new_experiments_group(description, system_role, base_prompt)

    def run_single_experiment(
        self,
        experiment_group_id: int,
        narrative_row: pd.Series,
        repetition_number: int = 0,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        system_prompt: Optional[str] = None,
        max_retries: int = 2,
    ) -> bool:
        """Run a single experiment on a narrative.

        Args:
            experiment_group_id: ID of the experiment group
            narrative_row: Row containing narrative data
            repetition_number: Repetition number for this experiment
            model: Model to use (defaults to settings)
            temperature: Temperature setting (defaults to settings)
            system_prompt: System prompt (defaults to standard prompt)
            max_retries: Maximum number of retries on failure

        Returns:
            True if experiment succeeded, False otherwise
        """
        model = model or self.settings.model_config.default_model
        temperature = temperature if temperature is not None else self.settings.model_config.default_temperature
        system_prompt = system_prompt or get_default_system_prompt()

        # Create experiment record
        experiment_data = {
            "experiments_group_id": experiment_group_id,
            "repeated": repetition_number,
            "language_instructions": "english",
            "model_provider": "openai",
            "model": model,
            "with_context": False,
            "narrative_id": narrative_row.narrative_id,
            "extra_description": {
                "type": "automated_experiment",
                "description": f"Automated experiment with {model} at temperature {temperature}",
            },
            "repo_sha": self.repo_commit_sha,
            "exp_type": "auto",
        }

        experiment_id = self.db_manager.register_new_experiment(experiment_data)
        logging.info(f"{datetime.now()} - experiment_id: {experiment_id}")

        # Prepare messages
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": narrative_row.narrative},
        ]

        # Run experiment with retries
        for attempt in range(max_retries + 1):
            try:
                response = self.openai_client.create_completion(messages=messages, model=model, temperature=temperature)

                # Save request/response to database
                send_to_db_request_response(
                    self.db_manager.engine,
                    response,
                    experiment_id,
                    model,
                    messages,
                    temperature,
                    self.settings.model_config.default_top_p,
                    max_tokens=self.settings.model_config.default_max_tokens,
                )

                # Parse and save answers
                parse_answers(
                    self.db_manager.engine,
                    narrative_row.narrative_id,
                    experiment_id,
                    response,
                )

                return True

            except Exception as e:
                logging.error(f"Experiment {experiment_id} failed on attempt {attempt + 1}: {e}")

        return False

    def run_batch_experiments(
        self,
        narratives: pd.DataFrame,
        models: list[str],
        temperatures: list[float],
        repetitions: int = 1,
        description_template: str = (
            "Batch experiment - model: {model}, temperature: {temperature}, repetition: {repetition}"
        ),
        system_prompt: Optional[str] = None,
    ) -> dict[str, list[int]]:
        """Run batch experiments across multiple models, temperatures, and repetitions.

        Args:
            narratives: DataFrame containing narratives to evaluate
            models: List of models to test
            temperatures: List of temperatures to test
            repetitions: Number of repetitions per configuration
            description_template: Template for experiment group descriptions
            system_prompt: System prompt to use (defaults to standard prompt)

        Returns:
            Dictionary mapping experiment configurations to group IDs
        """
        experiment_groups: dict[str, list[int]] = {}

        for model in models:
            for temperature in temperatures:
                group_desc = description_template.format(model=model, temperature=temperature, repetition=repetitions)

                group_id = self.create_experiment_group(group_desc, system_prompt)

                experiment_groups.setdefault(model, []).append(group_id)

                for rep in range(repetitions):
                    for _, row in narratives.iterrows():
                        self.run_single_experiment(
                            experiment_group_id=group_id,
                            narrative_row=row,
                            repetition_number=rep,
                            model=model,
                            temperature=temperature,
                            system_prompt=system_prompt,
                        )

        return experiment_groups

    def get_narratives(self) -> pd.DataFrame:
        """Retrieve narratives from the database.

        Returns:
            DataFrame containing narrative data
        """
        return self.db_manager.get_narratives()


def main() -> None:
    """Main entry point for running experiments."""
    parser = argparse.ArgumentParser(description="Run pain narrative experiments")
    parser.add_argument("--models", nargs="+", default=["gpt-5-mini"], help="Models to test")
    parser.add_argument(
        "--temperatures",
        nargs="+",
        type=float,
        default=[0.0],
        help="Temperatures to test",
    )
    parser.add_argument("--repetitions", type=int, default=1, help="Number of repetitions")
    parser.add_argument("--limit", type=int, help="Limit number of narratives")

    args = parser.parse_args()

    runner = ExperimentRunner()
    narratives = runner.get_narratives()
    if args.limit is not None:
        narratives = narratives.head(args.limit)

    logging.info(f"Running experiments on {len(narratives)} narratives")
    logging.info(f"Models: {args.models}")
    logging.info(f"Temperatures: {args.temperatures}")
    logging.info(f"Repetitions: {args.repetitions}")

    experiment_groups = runner.run_batch_experiments(
        narratives=narratives,
        models=args.models,
        temperatures=args.temperatures,
        repetitions=args.repetitions,
    )

    logging.info(f"Completed! Created {len(experiment_groups)} experiment groups.")


if __name__ == "__main__":
    main()
