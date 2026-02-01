"""Analytics logic for pain narratives Streamlit app."""

from typing import Any, Dict, List, TypedDict, Union

import pandas as pd
import streamlit as st


class EvaluationResult(TypedDict, total=False):
    reasoning: str
    # Add your actual dimension names and types here, e.g.:
    # pain_intensity: float
    # empathy: float
    # ...
    # For now, allow any str: float for dimensions


def calculate_consistency_metrics(evaluations: List[Dict[str, Union[str, float, int]]]) -> Dict[str, float]:
    """Calculate consistency metrics across multiple evaluations."""
    if len(evaluations) < 2:
        return {"avg_std": 0.0, "max_diff": 0.0, "dimensions_analyzed": 0.0}
    score_data: Dict[str, List[float]] = {}
    for eval_result in evaluations:
        for key, value in eval_result.items():
            if key != "reasoning" and isinstance(value, (int, float)):
                if key not in score_data:
                    score_data[key] = []
                score_data[key].append(float(value))
    if not score_data:
        return {"avg_std": 0.0, "max_diff": 0.0, "dimensions_analyzed": 0.0}
    std_devs: List[float] = []
    max_diffs: List[float] = []
    for dimension, scores in score_data.items():
        if len(scores) > 1:
            std_dev: float = float(pd.Series(scores).std())
            max_diff: float = max(scores) - min(scores)
            std_devs.append(std_dev)
            max_diffs.append(max_diff)
    return {
        "avg_std": sum(std_devs) / len(std_devs) if std_devs else 0.0,
        "max_diff": max(max_diffs) if max_diffs else 0.0,
        "dimensions_analyzed": float(len(score_data)),
    }


def display_consistency_metrics(evaluations: List[Dict[str, Union[str, float, int]]]) -> None:
    """Display consistency metrics for multiple evaluations."""
    st.subheader("🎯 Consistency Analysis")
    if len(evaluations) < 2:
        st.warning("Need at least 2 evaluations for consistency analysis.")
        return
    metrics: Dict[str, float] = calculate_consistency_metrics(evaluations)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Average Std Dev", f"{metrics['avg_std']:.2f}")
    with col2:
        st.metric("Max Difference", f"{metrics['max_diff']:.1f}")
    with col3:
        st.metric("Dimensions Analyzed", int(metrics["dimensions_analyzed"]))
    with st.expander("📊 Detailed Consistency Results"):
        df_data: List[Dict[str, Any]] = []
        for i, eval_result in enumerate(evaluations):
            row: Dict[str, Any] = {"Evaluation": i + 1}
            for key, value in eval_result.items():
                if key != "reasoning" and isinstance(value, (int, float)):
                    row[key] = float(value)
            df_data.append(row)
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True)
