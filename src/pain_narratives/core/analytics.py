"""Analytics and evaluation functions for pain narratives."""

import json
import logging
from typing import Any, Dict, Literal, Optional

import pandas as pd
from sklearn.metrics import cohen_kappa_score, mean_squared_error

from .openai_client import remove_unicode_chars


def convert_string_to_json(input_string: str) -> Optional[Dict[str, Any]]:
    """Convert a JSON string to a Python dictionary.

    Args:
        input_string: JSON string to convert

    Returns:
        Dictionary if conversion successful, None otherwise
    """
    try:
        result = json.loads(input_string)
        if isinstance(result, dict):
            return result
        return None
    except json.JSONDecodeError as e:
        logging.error(f"JSON decode error: {e}")
        return None


def parse_answers(
    db_conn: Any,
    narrative_id: int,
    experiment_id: int,
    response: Dict[str, Any],
    schema: str = "pain_narratives",
) -> bool:
    """Parse AI model response and save to database.

    Args:
        db_conn: Database connection
        narrative_id: ID of the narrative
        experiment_id: ID of the experiment
        response: Model response dictionary
        schema: Database schema name

    Returns:
        True if parsing successful, False otherwise
    """
    response = remove_unicode_chars(response)
    try:
        message_content = response["choices"][0]["message"]["content"]
        json_eval = convert_string_to_json(message_content)

        if json_eval:
            exp_df = pd.DataFrame(json_eval, index=[0])
            exp_df.insert(0, "narrative_id", narrative_id)
            exp_df.insert(0, "experiment_id", experiment_id)

            exp_df.to_sql(
                "model_responses",
                db_conn,
                schema=schema,
                if_exists="append",
                index=False,
            )

            return True
        else:
            logging.error("Error parsing JSON: %s", message_content)
            return False
    except (KeyError, IndexError) as e:
        logging.error(f"Error accessing response content: {e}")
        return False
    except Exception as e:
        logging.exception(f"Unexpected error: {e}")
        return False


def calculate_mse(values_original: pd.Series, values_new: pd.Series) -> float:
    """Calculate the Mean Squared Error between two series of annotations."""
    mse = mean_squared_error(values_original, values_new)
    return float(mse)


def calculate_kappa(
    values_original: pd.Series,
    values_new: pd.Series,
    weights: Optional[Literal["linear", "quadratic"]] = None,
) -> float:
    """Calculate Cohen's Kappa between two series of annotations."""
    return float(cohen_kappa_score(values_original, values_new, weights=weights))


def calculate_rmse(values_original: pd.Series, values_new: pd.Series) -> float:
    """Calculate the Root Mean Squared Error between two series of annotations."""
    rmse = mean_squared_error(values_original, values_new, squared=False)
    return float(rmse)


def calculate_mean_absolute_error(values_original: pd.Series, values_new: pd.Series) -> float:
    """Calculate Mean Absolute Error between two series.

    Args:
        values_original: Original values
        values_new: New values

    Returns:
        MAE value
    """
    mae = abs(values_original - values_new).mean()
    return float(mae)


def evaluate_agreement_metrics(
    expert1_scores: pd.Series, expert2_scores: pd.Series, model_scores: pd.Series
) -> Dict[str, float]:
    """Calculate comprehensive agreement metrics between experts and model.

    Args:
        expert1_scores: First expert's scores
        expert2_scores: Second expert's scores
        model_scores: AI model's scores

    Returns:
        Dictionary containing various agreement metrics
    """
    metrics = {}

    # Inter-expert agreement
    metrics["expert_kappa"] = calculate_kappa(expert1_scores, expert2_scores, weights="quadratic")
    metrics["expert_rmse"] = calculate_rmse(expert1_scores, expert2_scores)
    metrics["expert_mae"] = calculate_mean_absolute_error(expert1_scores, expert2_scores)

    # Expert 1 vs Model
    metrics["expert1_model_kappa"] = calculate_kappa(expert1_scores, model_scores, weights="quadratic")
    metrics["expert1_model_rmse"] = calculate_rmse(expert1_scores, model_scores)
    metrics["expert1_model_mae"] = calculate_mean_absolute_error(expert1_scores, model_scores)

    # Expert 2 vs Model
    metrics["expert2_model_kappa"] = calculate_kappa(expert2_scores, model_scores, weights="quadratic")
    metrics["expert2_model_rmse"] = calculate_rmse(expert2_scores, model_scores)
    metrics["expert2_model_mae"] = calculate_mean_absolute_error(expert2_scores, model_scores)

    # Average Expert vs Model
    expert_avg = (expert1_scores + expert2_scores) / 2
    metrics["avg_expert_model_kappa"] = calculate_kappa(
        expert_avg.round().astype(int),
        model_scores.round().astype(int),
        weights="quadratic",
    )
    metrics["avg_expert_model_rmse"] = calculate_rmse(expert_avg, model_scores)
    metrics["avg_expert_model_mae"] = calculate_mean_absolute_error(expert_avg, model_scores)

    return metrics


def calculate_correlation_metrics(values1: pd.Series, values2: pd.Series) -> Dict[str, float]:
    """Calculate correlation metrics between two series.

    Args:
        values1: First series
        values2: Second series

    Returns:
        Dictionary with Pearson and Spearman correlations
    """
    return {
        "pearson_correlation": values1.corr(values2, method="pearson"),
        "spearman_correlation": values1.corr(values2, method="spearman"),
    }


def get_default_system_prompt() -> str:
    """
    Get the default system prompt for pain narrative evaluation.
    
    This function now loads the prompt from YAML configuration instead of
    being hardcoded, making it easier to maintain and update.
    """
    from pain_narratives.config.prompts import get_default_prompt
    
    return get_default_prompt()
