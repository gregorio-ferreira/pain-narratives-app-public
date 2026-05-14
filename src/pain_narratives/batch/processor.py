"""
Batch processor for pain narrative evaluation.

This module provides the BatchProcessor class that handles batch processing
of pain narratives, including dimension evaluation and questionnaires.
All results are stored in the existing database schema.
"""

import json
import logging
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import pandas as pd

from pain_narratives.config.prompts import (
    get_base_prompt,
    get_default_dimensions,
    get_narrative_evaluation_config_v,
    get_questionnaire_prompt,
    get_system_role,
)
from pain_narratives.core.bedrock_client import (
    BedrockAuthError,
    BedrockClient,
    BedrockModelError,
    BedrockOpenAIAdapter,
    BedrockTransientError,
)
from pain_narratives.core.database import DatabaseManager
from pain_narratives.core.openai_client import OpenAIClient
from pain_narratives.core.questionnaire_runner import (
    QuestionnaireResult,
    calculate_bpi_is_subscales,
    calculate_bpi_is_total_score,
    calculate_pcs_subscales,
    calculate_pcs_total_score,
    calculate_tsk_11sv_total_score,
    run_questionnaire,
)

logger = logging.getLogger(__name__)


def get_git_sha() -> str:
    """Get current git commit SHA."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


@dataclass
class NarrativeEvaluationResult:
    """Container for a single narrative's evaluation results."""

    narrative_id: int
    narrative_text: str
    experiment_id: Optional[int] = None

    # Dimension evaluation
    dimension_success: bool = False
    dimension_result: Dict[str, Any] = field(default_factory=dict)
    dimension_error: Optional[str] = None

    # Questionnaire results
    pcs_result: Optional[QuestionnaireResult] = None
    bpi_is_result: Optional[QuestionnaireResult] = None
    tsk_11sv_result: Optional[QuestionnaireResult] = None

    # Questionnaire IDs in database
    pcs_questionnaire_id: Optional[int] = None
    bpi_is_questionnaire_id: Optional[int] = None
    tsk_11sv_questionnaire_id: Optional[int] = None


@dataclass
class BatchConfig:
    """Configuration for batch processing."""

    model: str = "gpt-5-mini"
    temperature: float = 0.0
    max_tokens: int = 8000

    # Rate limiting
    delay_between_calls: float = 1.0  # Seconds between API calls
    max_retries: int = 3
    retry_delay: float = 5.0  # Seconds to wait before retry

    # Processing options
    include_dimensions: bool = True
    include_pcs: bool = True
    include_bpi_is: bool = True
    include_tsk_11sv: bool = True

    # Checkpointing
    checkpoint_file: Optional[str] = None
    checkpoint_interval: int = 10  # Save checkpoint every N narratives

    # Provider / prompt-version selection (revision experiments)
    model_provider: str = "openai"  # "openai" or "bedrock_anthropic" or "bedrock_deepseek"
    prompt_version: str = "original"  # "original" or "simplified_v1"

    # Bedrock-only options
    thinking_enabled: bool = False
    thinking_budget_tokens: int = 8000
    bedrock_region: Optional[str] = None
    bedrock_profile: Optional[str] = None

    # Safety net — abort batch after N consecutive narrative-level failures
    # (likely indicates auth expiry, quota exhaustion, or a programming bug)
    consecutive_failure_threshold: int = 5


@dataclass
class BatchProgress:
    """Track batch processing progress."""

    total: int = 0
    processed: int = 0
    successful: int = 0
    failed: int = 0
    current_narrative_id: Optional[int] = None
    start_time: Optional[datetime] = None

    @property
    def elapsed_seconds(self) -> float:
        if self.start_time is None:
            return 0
        return (datetime.now(timezone.utc) - self.start_time).total_seconds()

    @property
    def avg_time_per_narrative(self) -> float:
        if self.processed == 0:
            return 0
        return self.elapsed_seconds / self.processed

    @property
    def estimated_remaining_seconds(self) -> float:
        remaining = self.total - self.processed
        return remaining * self.avg_time_per_narrative


class BatchProcessor:
    """
    Batch processor for pain narratives.

    Processes multiple narratives through dimension evaluation and questionnaires,
    storing all results in the existing database schema.
    """

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        openai_client: Optional[OpenAIClient] = None,
        config: Optional[BatchConfig] = None,
    ):
        """Initialize the batch processor.

        When `config.model_provider` is `"openai"`, the OpenAI client is used
        as before. When it starts with `"bedrock"`, a `BedrockClient` is
        constructed and wrapped in `BedrockOpenAIAdapter` so call sites can
        pass `self.openai_client` to `run_questionnaire(llm_client=...)`
        regardless of provider.
        """
        self.db_manager = db_manager or DatabaseManager()
        self.config = config or BatchConfig()

        # The attribute remains named `openai_client` for compatibility with
        # the rest of the codebase; it is the LLM adapter regardless of provider.
        if self.config.model_provider.startswith("bedrock"):
            self._bedrock_client = BedrockClient(
                region=self.config.bedrock_region,
                profile_name=self.config.bedrock_profile,
            )
            force_temp = self.config.temperature if not self.config.thinking_enabled else None
            self.openai_client = BedrockOpenAIAdapter(  # type: ignore[assignment]
                self._bedrock_client,
                thinking_enabled=self.config.thinking_enabled,
                thinking_budget_tokens=self.config.thinking_budget_tokens,
                force_temperature=force_temp,
            )
        else:
            self._bedrock_client = None
            self.openai_client = openai_client or OpenAIClient()

        self.progress = BatchProgress()
        self._checkpoint_data: Dict[str, Any] = {}
        self._progress_callback: Optional[Callable[[BatchProgress], None]] = None

    def preflight(self, min_remaining_hours: float = 2.0) -> None:
        """Run pre-batch sanity checks. Raises a typed error on failure so the
        runner can present a clear message before any expensive work starts.

        - Bedrock: validates that the bearer token is not expired and has at
          least `min_remaining_hours` of usable time left.
        - OpenAI: no-op (the OpenAI SDK validates per-call).
        """
        if self._bedrock_client is not None:
            from datetime import timedelta

            info = self._bedrock_client.check_credentials(min_remaining=timedelta(hours=min_remaining_hours))
            if info.expires_at:
                remaining = info.time_remaining()
                logger.info(
                    "Bedrock pre-flight OK: %s credentials valid until %s (%s remaining)",
                    info.auth_method,
                    info.expires_at.isoformat(),
                    remaining,
                )
            else:
                principal = f" principal={info.principal_arn}" if info.principal_arn else ""
                profile = f" profile={info.profile_name}" if info.profile_name else ""
                logger.info(
                    "Bedrock pre-flight OK: %s credentials%s%s (no local expiry)",
                    info.auth_method,
                    profile,
                    principal,
                )

    def set_progress_callback(self, callback: Callable[[BatchProgress], None]) -> None:
        """Set a callback function for progress updates."""
        self._progress_callback = callback

    def _notify_progress(self) -> None:
        """Notify progress callback if set."""
        if self._progress_callback:
            self._progress_callback(self.progress)

    def load_narratives_from_excel(
        self,
        file_path: str,
        narrative_column: str = "narrative",
        id_column: Optional[str] = None,
        sheet_name: str | int = 0,
        filter_column: Optional[str] = None,
        filter_value: Optional[Any] = None,
    ) -> pd.DataFrame:
        """
        Load narratives from an Excel file.

        Args:
            file_path: Path to the Excel file
            narrative_column: Name of the column containing narratives
            id_column: Optional column for existing narrative IDs
            sheet_name: Sheet name or index to read
            filter_column: Optional column name to filter by
            filter_value: Value to filter for in filter_column

        Returns:
            DataFrame with narratives
        """
        logger.info(f"Loading narratives from: {file_path}")

        df = pd.read_excel(file_path, sheet_name=sheet_name)

        if narrative_column not in df.columns:
            raise ValueError(f"Column '{narrative_column}' not found. Available: {list(df.columns)}")

        # Apply filter if specified
        initial_count = len(df)
        if filter_column is not None and filter_value is not None:
            if filter_column not in df.columns:
                raise ValueError(f"Filter column '{filter_column}' not found. Available: {list(df.columns)}")
            df = df[df[filter_column] == filter_value]
            logger.info(f"Filtered by {filter_column}={filter_value}: {initial_count} -> {len(df)} rows")

        # Filter out empty narratives
        df = df[df[narrative_column].notna() & (df[narrative_column].str.strip() != "")]

        logger.info(f"Loaded {len(df)} narratives from Excel")
        return df

    def estimate_batch_cost(
        self,
        num_narratives: int,
        avg_narrative_tokens: int = 500,
    ) -> Dict[str, Any]:
        """
        Estimate API costs for a batch run.

        Args:
            num_narratives: Number of narratives to process
            avg_narrative_tokens: Estimated average tokens per narrative

        Returns:
            Dict with cost estimates
        """
        # Count API calls per narrative
        calls_per_narrative = 0
        if self.config.include_dimensions:
            calls_per_narrative += 1
        if self.config.include_pcs:
            calls_per_narrative += 1
        if self.config.include_bpi_is:
            calls_per_narrative += 1
        if self.config.include_tsk_11sv:
            calls_per_narrative += 1

        total_calls = num_narratives * calls_per_narrative

        # Estimate tokens (rough estimates for gpt-5-mini)
        input_tokens_per_call = avg_narrative_tokens + 2000  # narrative + prompt
        output_tokens_per_call = 1500  # JSON response + reasoning

        total_input_tokens = total_calls * input_tokens_per_call
        total_output_tokens = total_calls * output_tokens_per_call

        # gpt-5-mini pricing (as of late 2024, approximate)
        input_cost_per_1m = 0.15  # $0.15 per 1M input tokens
        output_cost_per_1m = 0.60  # $0.60 per 1M output tokens

        input_cost = (total_input_tokens / 1_000_000) * input_cost_per_1m
        output_cost = (total_output_tokens / 1_000_000) * output_cost_per_1m
        total_cost = input_cost + output_cost

        # Time estimate
        time_per_call = self.config.delay_between_calls + 2  # delay + processing
        total_time_seconds = total_calls * time_per_call

        return {
            "num_narratives": num_narratives,
            "calls_per_narrative": calls_per_narrative,
            "total_api_calls": total_calls,
            "estimated_input_tokens": total_input_tokens,
            "estimated_output_tokens": total_output_tokens,
            "estimated_cost_usd": round(total_cost, 2),
            "estimated_time_minutes": round(total_time_seconds / 60, 1),
        }

    def create_experiment_group(
        self,
        user_id: int,
        description: str,
    ) -> int:
        """
        Create a new experiment group for the batch.

        Args:
            user_id: Owner user ID (batch user)
            description: Description for the experiment group

        Returns:
            Experiment group ID
        """
        group_id = self.db_manager.register_new_experiments_group(
            description=description,
            system_role=get_system_role(),
            base_prompt=get_base_prompt(),
            owner_id=user_id,
            dimensions=get_default_dimensions(),
        )

        logger.info(f"Created experiment group: {group_id}")
        return group_id

    def create_narrative_record(
        self,
        narrative_text: str,
        owner_id: int,
    ) -> int:
        """
        Create a narrative record in the database.

        Args:
            narrative_text: The pain narrative text
            owner_id: Owner user ID

        Returns:
            Narrative ID
        """
        narrative_id = self.db_manager.create_narrative(
            {
                "narrative": narrative_text,
                "owner_id": owner_id,
            }
        )

        logger.debug(f"Created narrative: {narrative_id}")
        return narrative_id

    def _run_dimension_evaluation(
        self,
        narrative_text: str,
        experiment_id: int,
    ) -> tuple[Dict[str, Any], int]:
        """Run dimension evaluation. Returns (parsed_result, reasoning_tokens).
        Versioned via `self.config.prompt_version`."""
        ne_cfg = get_narrative_evaluation_config_v(self.config.prompt_version)
        system_role = ne_cfg.get("system_role", "").strip() or get_system_role()
        base_prompt = ne_cfg.get("base_prompt", "").strip() or get_base_prompt()
        dimensions = ne_cfg.get("dimensions", []) or get_default_dimensions()

        # Build the full prompt
        dimension_descriptions = []
        for dim in dimensions:
            if dim.get("active", True):
                dimension_descriptions.append(
                    f"- **{dim['name']}**: {dim['definition']} (Score range: {dim['min']}-{dim['max']})"
                )

        # Output instruction depends on prompt version: original asks for
        # scores+explanations; simplified asks for scores only.
        if self.config.prompt_version == "simplified_v1":
            output_instruction = (
                "Output a JSON object with the dimension snake_case names as keys "
                "and the integer score as values. Do not include any other fields, "
                "explanations, or commentary."
            )
        else:
            output_instruction = "Please respond in JSON format with scores and explanations for each dimension."

        full_prompt = f"""{base_prompt}

Please analyze the following narrative and provide scores for these dimensions as specified:

{chr(10).join(dimension_descriptions)}

{output_instruction}

Patient narrative:
{narrative_text}
"""

        messages = [
            {"role": "system", "content": system_role},
            {"role": "user", "content": full_prompt},
        ]

        # Retry dimensions on transient errors; auth/model errors raise immediately.
        response = self._call_llm_with_retry(
            lambda: self.openai_client.create_completion(
                messages=messages,
                model=self.config.model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                response_format="json_object",
            ),
            label="dimensions",
        )

        # Save request/response
        self.db_manager.save_request_response(
            experiment_id=experiment_id,
            request_json={"messages": messages, "model": self.config.model},
            response_json=response,
        )

        # Parse response
        content = response.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        reasoning_tokens = int(response.get("reasoning_tokens") or 0)

        if content:
            try:
                # Clean JSON
                if content.startswith("```json"):
                    content = content[7:]
                if content.startswith("```"):
                    content = content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()

                return json.loads(content), reasoning_tokens
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse dimension response: {e}")
                return {"error": str(e), "raw_content": content[:500]}, reasoning_tokens

        return {"error": "Empty response"}, reasoning_tokens

    def _call_llm_with_retry(self, fn: Callable[[], Any], *, label: str) -> Any:
        """Call an LLM completion `fn` with retry on transient Bedrock errors.

        BedrockAuthError raises immediately so the runner can halt the batch.
        BedrockModelError raises immediately (programming bug, not transient).
        Generic exceptions are treated as transient up to `max_retries`.
        """
        delay = self.config.retry_delay
        last_exc: Optional[Exception] = None
        for attempt in range(1, self.config.max_retries + 1):
            try:
                return fn()
            except BedrockAuthError:
                raise  # halt batch immediately — caller will save checkpoint
            except BedrockModelError as e:
                logger.error("[%s] model rejected request (not retried): %s", label, e)
                raise
            except (BedrockTransientError, Exception) as e:  # noqa: BLE001
                last_exc = e
                logger.warning(
                    "[%s] attempt %d/%d failed: %s",
                    label,
                    attempt,
                    self.config.max_retries,
                    e,
                )
                if attempt < self.config.max_retries:
                    time.sleep(delay)
                    delay *= 2
        assert last_exc is not None
        raise last_exc

    def _run_questionnaire_with_retry(
        self,
        narrative_text: str,
        questionnaire_type: str,
    ) -> QuestionnaireResult:
        """Run a questionnaire with retry logic, using the configured prompt
        version. `BedrockAuthError` propagates out of `run_questionnaire` so the
        batch halts immediately; transient/parse failures retry."""
        prompts = get_questionnaire_prompt(questionnaire_type, version=self.config.prompt_version)

        result: Optional[QuestionnaireResult] = None
        for attempt in range(1, self.config.max_retries + 1):
            result = run_questionnaire(
                narrative=narrative_text,
                questionnaire_type=questionnaire_type,
                llm_client=self.openai_client,
                model=self.config.model,
                temperature=self.config.temperature,
                system_role=prompts.get("system_role"),
                instructions=prompts.get("instructions"),
                max_tokens=self.config.max_tokens,
            )
            if result.success:
                return result
            logger.warning(
                "%s attempt %d/%d failed: %s",
                questionnaire_type,
                attempt,
                self.config.max_retries,
                result.error,
            )
            if attempt < self.config.max_retries:
                time.sleep(self.config.retry_delay * (2 ** (attempt - 1)))

        assert result is not None
        return result

    def _save_questionnaire_result(
        self,
        result: QuestionnaireResult,
        questionnaire_type: str,
        experiment_id: int,
        group_id: int,
        narrative_id: int,
        user_id: int,
    ) -> Optional[int]:
        """
        Save questionnaire result to database.

        Returns:
            Questionnaire ID if successful, None otherwise
        """
        if not result.success:
            return None

        # Build prompt string for storage
        prompt_str = "\n".join([f"{msg['role']}: {msg['content'][:200]}..." for msg in result.messages])

        questionnaire_id = self.db_manager.save_questionnaire_result(
            {
                "experiment_id": experiment_id,
                "experiments_group_id": group_id,
                "narrative_id": narrative_id,
                "user_id": user_id,
                "questionnaire_name": questionnaire_type,
                "prompt": prompt_str,
                "result_json": result.data,
            }
        )

        # Calculate scores for evaluation result
        scores_data: Dict[str, Any] = {"raw_data": result.data}

        if questionnaire_type == "PCS":
            scores_data["total_score"] = calculate_pcs_total_score(result)
            scores_data["subscales"] = calculate_pcs_subscales(result)
        elif questionnaire_type == "BPI-IS":
            scores_data["total_score"] = calculate_bpi_is_total_score(result)
            scores_data["subscales"] = calculate_bpi_is_subscales(result)
        elif questionnaire_type == "TSK-11SV":
            scores_data["total_score"] = calculate_tsk_11sv_total_score(result)

        # Save evaluation result
        self.db_manager.save_evaluation_result(
            {
                "experiment_id": experiment_id,
                "questionnaire_id": questionnaire_id,
                "experiments_group_id": group_id,
                "narrative_id": narrative_id,
                "user_id": user_id,
                "result_type": questionnaire_type,
                "result_json": scores_data,
            }
        )

        return questionnaire_id

    def process_single_narrative(
        self,
        narrative_text: str,
        narrative_id: int,
        experiment_id: int,
        group_id: int,
        user_id: int,
    ) -> NarrativeEvaluationResult:
        """
        Process a single narrative through all evaluations.

        Args:
            narrative_text: The pain narrative text
            narrative_id: Database narrative ID
            experiment_id: Database experiment ID
            group_id: Experiment group ID
            user_id: User ID for ownership

        Returns:
            NarrativeEvaluationResult with all results
        """
        result = NarrativeEvaluationResult(
            narrative_id=narrative_id,
            narrative_text=narrative_text,
            experiment_id=experiment_id,
        )

        total_reasoning_tokens = 0

        # 1. Dimension evaluation
        if self.config.include_dimensions:
            try:
                dim_result, dim_reasoning_tokens = self._run_dimension_evaluation(narrative_text, experiment_id)
                total_reasoning_tokens += dim_reasoning_tokens
                result.dimension_success = "error" not in dim_result
                result.dimension_result = dim_result

                # Save dimension evaluation result
                self.db_manager.save_evaluation_result(
                    {
                        "experiment_id": experiment_id,
                        "experiments_group_id": group_id,
                        "narrative_id": narrative_id,
                        "user_id": user_id,
                        "result_type": "dimensions",
                        "result_json": dim_result,
                    }
                )

                # Update experiment status
                self.db_manager.update_experiment_status(
                    experiment_id,
                    succeeded=result.dimension_success,
                    parsed_answers=result.dimension_success,
                )

            except BedrockAuthError:
                # Halt the batch — refreshing credentials is the only recourse.
                raise
            except Exception as e:
                result.dimension_error = str(e)
                logger.error(f"Dimension evaluation failed: {e}")

            time.sleep(self.config.delay_between_calls)

        # 2. PCS questionnaire
        if self.config.include_pcs:
            result.pcs_result = self._run_questionnaire_with_retry(narrative_text, "PCS")
            total_reasoning_tokens += int((result.pcs_result.raw_response or {}).get("reasoning_tokens") or 0)
            result.pcs_questionnaire_id = self._save_questionnaire_result(
                result.pcs_result, "PCS", experiment_id, group_id, narrative_id, user_id
            )
            time.sleep(self.config.delay_between_calls)

        # 3. BPI-IS questionnaire
        if self.config.include_bpi_is:
            result.bpi_is_result = self._run_questionnaire_with_retry(narrative_text, "BPI-IS")
            total_reasoning_tokens += int((result.bpi_is_result.raw_response or {}).get("reasoning_tokens") or 0)
            result.bpi_is_questionnaire_id = self._save_questionnaire_result(
                result.bpi_is_result, "BPI-IS", experiment_id, group_id, narrative_id, user_id
            )
            time.sleep(self.config.delay_between_calls)

        # 4. TSK-11SV questionnaire
        if self.config.include_tsk_11sv:
            result.tsk_11sv_result = self._run_questionnaire_with_retry(narrative_text, "TSK-11SV")
            total_reasoning_tokens += int((result.tsk_11sv_result.raw_response or {}).get("reasoning_tokens") or 0)
            result.tsk_11sv_questionnaire_id = self._save_questionnaire_result(
                result.tsk_11sv_result, "TSK-11SV", experiment_id, group_id, narrative_id, user_id
            )
            time.sleep(self.config.delay_between_calls)

        # Persist aggregate reasoning-token count for cost reconstruction.
        if total_reasoning_tokens > 0:
            self.db_manager.update_experiment_status(experiment_id, reasoning_tokens=total_reasoning_tokens)

        return result

    def _save_checkpoint(self, processed_ids: List[int], group_id: int) -> None:
        """Save checkpoint to file."""
        if not self.config.checkpoint_file:
            return

        checkpoint_path = Path(self.config.checkpoint_file)
        checkpoint_data = {
            "processed_ids": processed_ids,
            "group_id": group_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "progress": {
                "total": self.progress.total,
                "processed": self.progress.processed,
                "successful": self.progress.successful,
                "failed": self.progress.failed,
            },
        }

        checkpoint_path.write_text(json.dumps(checkpoint_data, indent=2))
        logger.debug(f"Saved checkpoint: {len(processed_ids)} processed")

    def _load_checkpoint(self) -> Dict[str, Any]:
        """Load checkpoint from file."""
        if not self.config.checkpoint_file:
            return {}

        checkpoint_path = Path(self.config.checkpoint_file)
        if not checkpoint_path.exists():
            return {}

        try:
            return json.loads(checkpoint_path.read_text())
        except Exception as e:
            logger.warning(f"Failed to load checkpoint: {e}")
            return {}

    def run_batch(
        self,
        narratives_df: pd.DataFrame,
        user_id: int,
        group_description: str,
        narrative_column: str = "narrative",
        resume: bool = False,
    ) -> List[NarrativeEvaluationResult]:
        """
        Run batch processing on a DataFrame of narratives.

        Args:
            narratives_df: DataFrame with narrative text
            user_id: User ID for ownership (batch user)
            group_description: Description for the experiment group
            narrative_column: Column name containing narrative text
            resume: Whether to resume from checkpoint

        Returns:
            List of NarrativeEvaluationResult
        """
        results: List[NarrativeEvaluationResult] = []
        processed_ids: List[int] = []
        consecutive_failures = 0

        # Pre-flight: credentials, model access. Raises with a clear message
        # before any DB rows are created.
        self.preflight()

        # Load checkpoint if resuming
        checkpoint = self._load_checkpoint() if resume else {}

        if checkpoint and resume:
            processed_ids = checkpoint.get("processed_ids", [])
            group_id = checkpoint.get("group_id")
            logger.info(f"Resuming from checkpoint: {len(processed_ids)} already processed")
        else:
            # Create new experiment group
            group_id = self.create_experiment_group(user_id, group_description)

        # Initialize progress
        self.progress = BatchProgress(
            total=len(narratives_df),
            processed=len(processed_ids),
            successful=0,
            failed=0,
            start_time=datetime.now(timezone.utc),
        )

        git_sha = get_git_sha()

        try:
            for idx, row in narratives_df.iterrows():
                narrative_text = row[narrative_column]

                # Skip if already processed (resume mode)
                if idx in processed_ids:
                    continue

                self.progress.current_narrative_id = idx
                self._notify_progress()

                try:
                    # Create narrative record
                    narrative_id = self.create_narrative_record(narrative_text, user_id)

                    # Create experiment record
                    experiment_id = self.db_manager.register_new_experiment(
                        {
                            "experiments_group_id": group_id,
                            "user_id": user_id,
                            "narrative_id": narrative_id,
                            "model_provider": self.config.model_provider,
                            "model": self.config.model,
                            "exp_type": "batch",
                            "repo_sha": git_sha,
                            "succeeded": False,
                            "parsed_answers": False,
                            "calculated_metrics": False,
                            "prompt_version": self.config.prompt_version,
                        }
                    )

                    # Process narrative
                    result = self.process_single_narrative(
                        narrative_text=narrative_text,
                        narrative_id=narrative_id,
                        experiment_id=experiment_id,
                        group_id=group_id,
                        user_id=user_id,
                    )

                    results.append(result)
                    processed_ids.append(idx)

                    # Update progress and consecutive-failure counter
                    self.progress.processed += 1
                    succeeded = result.dimension_success or (result.pcs_result and result.pcs_result.success)
                    if succeeded:
                        self.progress.successful += 1
                        consecutive_failures = 0
                    else:
                        self.progress.failed += 1
                        consecutive_failures += 1

                    self._notify_progress()

                    # Save checkpoint periodically
                    if self.progress.processed % self.config.checkpoint_interval == 0:
                        self._save_checkpoint(processed_ids, group_id)

                    logger.info(
                        f"Processed {self.progress.processed}/{self.progress.total}: "
                        f"narrative_id={narrative_id}, experiment_id={experiment_id}"
                    )

                    # Tripwire: bail if too many consecutive narratives have failed.
                    if consecutive_failures >= self.config.consecutive_failure_threshold:
                        logger.error(
                            "Aborting batch: %d consecutive failures (threshold=%d). "
                            "Inspect the log for the root cause; re-run with --resume after fixing.",
                            consecutive_failures,
                            self.config.consecutive_failure_threshold,
                        )
                        raise RuntimeError(f"Aborting after {consecutive_failures} consecutive narrative failures")

                except BedrockAuthError as e:
                    logger.error(
                        "Bedrock auth failure mid-batch: %s. Save state and stop; "
                        "refresh the bearer token in config.yaml and re-run with --resume.",
                        e,
                    )
                    raise  # propagate after the finally-block saves the checkpoint
                except Exception as e:
                    logger.error(f"Failed to process narrative at index {idx}: {e}")
                    self.progress.processed += 1
                    self.progress.failed += 1
                    consecutive_failures += 1
                    processed_ids.append(idx)
                    self._notify_progress()
        finally:
            # Always save final checkpoint, even on abort
            self._save_checkpoint(processed_ids, group_id)

        # Mark group as concluded
        self.db_manager.update_experiment_group(
            group_id=group_id,
            user_id=user_id,
            concluded=True,
        )

        logger.info(
            f"Batch complete: {self.progress.successful} successful, "
            f"{self.progress.failed} failed out of {self.progress.total}"
        )

        return results

    def load_narratives_from_group(
        self,
        experiment_group_id: int,
    ) -> List[Dict[str, Any]]:
        """
        Load existing narratives from a previous experiment group.

        This allows reusing narratives from a previous run instead of creating
        new narrative records each time.

        Args:
            experiment_group_id: The experiment group ID to load narratives from

        Returns:
            List of dicts with 'narrative_id' and 'narrative_text' keys
        """
        from sqlmodel import select

        from pain_narratives.db.models_sqlmodel import ExperimentList, Narrative

        narratives = []

        with self.db_manager.get_session() as session:
            # Get all experiments from the group with their narratives
            experiments = session.exec(
                select(ExperimentList, Narrative)
                .join(Narrative, ExperimentList.narrative_id == Narrative.narrative_id)
                .where(ExperimentList.experiments_group_id == experiment_group_id)
                .order_by(ExperimentList.experiment_id)
            ).all()

            for exp, narr in experiments:
                narratives.append(
                    {
                        "narrative_id": narr.narrative_id,
                        "narrative_text": narr.narrative,
                    }
                )

        logger.info(f"Loaded {len(narratives)} narratives from experiment group {experiment_group_id}")
        return narratives

    def load_narratives_from_multiple_groups(
        self,
        experiment_group_ids: List[int],
    ) -> List[Dict[str, Any]]:
        """
        Load unique narratives from multiple experiment groups.

        Useful when the first run was split across multiple groups (e.g., groups 35 and 36).
        Deduplicates by narrative_id.

        Args:
            experiment_group_ids: List of experiment group IDs to load from

        Returns:
            List of dicts with 'narrative_id' and 'narrative_text' keys
        """
        from sqlmodel import select

        from pain_narratives.db.models_sqlmodel import ExperimentList, Narrative

        seen_narrative_ids = set()
        narratives = []

        with self.db_manager.get_session() as session:
            for group_id in experiment_group_ids:
                experiments = session.exec(
                    select(ExperimentList, Narrative)
                    .join(Narrative, ExperimentList.narrative_id == Narrative.narrative_id)
                    .where(ExperimentList.experiments_group_id == group_id)
                    .order_by(ExperimentList.experiment_id)
                ).all()

                for exp, narr in experiments:
                    if narr.narrative_id not in seen_narrative_ids:
                        seen_narrative_ids.add(narr.narrative_id)
                        narratives.append(
                            {
                                "narrative_id": narr.narrative_id,
                                "narrative_text": narr.narrative,
                            }
                        )

        logger.info(f"Loaded {len(narratives)} unique narratives from groups {experiment_group_ids}")
        return narratives

    def run_batch_with_existing_narratives(
        self,
        narratives: List[Dict[str, Any]],
        user_id: int,
        group_description: str,
        run_number: int,
        resume: bool = False,
    ) -> List[NarrativeEvaluationResult]:
        """
        Run batch processing using existing narrative records.

        This method reuses existing narrative_ids instead of creating new narrative
        records for each run. This is more efficient for running multiple repetitions
        of the same evaluation.

        Args:
            narratives: List of dicts with 'narrative_id' and 'narrative_text' keys
            user_id: User ID for ownership (batch user)
            group_description: Description for the experiment group
            run_number: Run number to store in the 'repeated' column (e.g., 2, 3, ..., 10)
            resume: Whether to resume from checkpoint

        Returns:
            List of NarrativeEvaluationResult
        """
        results: List[NarrativeEvaluationResult] = []
        processed_ids: List[int] = []
        consecutive_failures = 0

        # Pre-flight: credentials, model access. Halts before any DB writes.
        self.preflight()

        # Load checkpoint if resuming
        checkpoint = self._load_checkpoint() if resume else {}

        if checkpoint and resume:
            processed_ids = checkpoint.get("processed_ids", [])
            group_id = checkpoint.get("group_id")
            logger.info(f"Resuming from checkpoint: {len(processed_ids)} already processed")
        else:
            # Create new experiment group
            group_id = self.create_experiment_group(user_id, group_description)

        # Initialize progress
        self.progress = BatchProgress(
            total=len(narratives),
            processed=len(processed_ids),
            successful=0,
            failed=0,
            start_time=datetime.now(timezone.utc),
        )

        git_sha = get_git_sha()

        logger.info(f"Starting batch with {len(narratives)} existing narratives, run_number={run_number}")
        logger.info(
            "Using provider=%s model=%s prompt_version=%s thinking=%s",
            self.config.model_provider,
            self.config.model,
            self.config.prompt_version,
            self.config.thinking_enabled,
        )

        try:
            for idx, narr_data in enumerate(narratives):
                narrative_id = narr_data["narrative_id"]
                narrative_text = narr_data["narrative_text"]

                # Skip if already processed (resume mode)
                if narrative_id in processed_ids:
                    continue

                self.progress.current_narrative_id = narrative_id
                self._notify_progress()

                try:
                    # Create experiment record (reusing existing narrative_id).
                    # The 'repeated' field tracks the run number; prompt_version
                    # records which prompt set this row used.
                    experiment_id = self.db_manager.register_new_experiment(
                        {
                            "experiments_group_id": group_id,
                            "user_id": user_id,
                            "narrative_id": narrative_id,
                            "model_provider": self.config.model_provider,
                            "model": self.config.model,
                            "exp_type": "batch_repetition",
                            "repo_sha": git_sha,
                            "repeated": run_number,
                            "succeeded": False,
                            "parsed_answers": False,
                            "calculated_metrics": False,
                            "prompt_version": self.config.prompt_version,
                        }
                    )

                    # Process narrative
                    result = self.process_single_narrative(
                        narrative_text=narrative_text,
                        narrative_id=narrative_id,
                        experiment_id=experiment_id,
                        group_id=group_id,
                        user_id=user_id,
                    )

                    results.append(result)
                    processed_ids.append(narrative_id)

                    # Update progress + tripwire counter
                    self.progress.processed += 1
                    succeeded = result.dimension_success or (result.pcs_result and result.pcs_result.success)
                    if succeeded:
                        self.progress.successful += 1
                        consecutive_failures = 0
                    else:
                        self.progress.failed += 1
                        consecutive_failures += 1

                    self._notify_progress()

                    # Save checkpoint periodically
                    if self.progress.processed % self.config.checkpoint_interval == 0:
                        self._save_checkpoint(processed_ids, group_id)

                    logger.info(
                        f"Processed {self.progress.processed}/{self.progress.total}: "
                        f"narrative_id={narrative_id}, experiment_id={experiment_id}, run={run_number}"
                    )

                    if consecutive_failures >= self.config.consecutive_failure_threshold:
                        logger.error(
                            "Aborting batch: %d consecutive failures (threshold=%d). "
                            "Re-run with --resume after diagnosing the root cause.",
                            consecutive_failures,
                            self.config.consecutive_failure_threshold,
                        )
                        raise RuntimeError(f"Aborting after {consecutive_failures} consecutive narrative failures")

                except BedrockAuthError as e:
                    logger.error(
                        "Bedrock auth failure mid-batch: %s. Refresh the bearer "
                        "token in config.yaml and re-run with --resume.",
                        e,
                    )
                    raise
                except Exception as e:
                    logger.error(f"Failed to process narrative_id={narrative_id}: {e}")
                    self.progress.processed += 1
                    self.progress.failed += 1
                    consecutive_failures += 1
                    processed_ids.append(narrative_id)
                    self._notify_progress()
        finally:
            self._save_checkpoint(processed_ids, group_id)

        # Mark group as concluded
        self.db_manager.update_experiment_group(
            group_id=group_id,
            user_id=user_id,
            concluded=True,
        )

        logger.info(
            f"Batch run {run_number} complete: {self.progress.successful} successful, "
            f"{self.progress.failed} failed out of {self.progress.total}"
        )

        return results

    def run_single_test(
        self,
        narrative_text: str,
        user_id: int,
        group_description: str = "Single Test Evaluation",
    ) -> NarrativeEvaluationResult:
        """
        Run a single narrative as a test (creates its own group).

        Args:
            narrative_text: The narrative to evaluate
            user_id: User ID for ownership
            group_description: Description for the test group

        Returns:
            NarrativeEvaluationResult
        """
        # Create experiment group
        group_id = self.create_experiment_group(user_id, group_description)

        # Create narrative
        narrative_id = self.create_narrative_record(narrative_text, user_id)

        # Create experiment
        experiment_id = self.db_manager.register_new_experiment(
            {
                "experiments_group_id": group_id,
                "user_id": user_id,
                "narrative_id": narrative_id,
                "model_provider": "openai",
                "model": self.config.model,
                "exp_type": "batch_test",
                "repo_sha": get_git_sha(),
                "succeeded": False,
                "parsed_answers": False,
                "calculated_metrics": False,
            }
        )

        # Process
        result = self.process_single_narrative(
            narrative_text=narrative_text,
            narrative_id=narrative_id,
            experiment_id=experiment_id,
            group_id=group_id,
            user_id=user_id,
        )

        return result
