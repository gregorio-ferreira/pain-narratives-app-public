"""Components for displaying evaluation results."""

from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from pain_narratives.ui.utils import get_translator


def display_score_metrics(
    result: Dict[str, Any],
    columns: int = 2,
    score_ranges: Optional[Dict[str, tuple]] = None,
) -> None:
    """Display evaluation scores as metrics cards with multilingual support.

    Args:
        result: Evaluation result dictionary (already in user's language)
        columns: Number of columns for metrics display
        score_ranges: Optional dict mapping dimension keys to (min, max) tuples
    """
    t = get_translator(st.session_state.get("language", "en"))

    # Handle multilingual result structure
    evaluation_result = result
    if isinstance(result, dict) and any(key in ["en", "es", "fr", "de"] for key in result.keys()):
        from pain_narratives.core.translation_service import TranslationService

        translation_service = TranslationService()
        current_language = st.session_state.get("language", "en")
        evaluation_result = translation_service.get_available_translation(result, current_language)

    score_keys = [
        k for k in evaluation_result.keys() if k != "reasoning" and isinstance(evaluation_result[k], (int, float))
    ]

    if not score_keys:
        st.warning(t("evaluation.no_numeric_scores"))
        return

    cols = st.columns(columns)

    for i, key in enumerate(score_keys):
        col = cols[i % columns]
        with col:
            display_name = key.replace("_", " ").title()
            score = evaluation_result[key]
            # Get min/max for this dimension
            min_score, max_score = (1, 10)
            if score_ranges and key in score_ranges:
                min_score, max_score = score_ranges[key]
            # Color coding based on score (optional: you may want to adjust logic for custom ranges)
            if score >= max_score * 0.8:
                help_text = "High"
            elif score >= max_score * 0.6:
                help_text = "Moderate"
            elif score >= max_score * 0.4:
                help_text = "Low-Moderate"
            else:
                help_text = "Low"

            st.metric(
                label=display_name,
                value=f"{score}/{max_score}",
                help=f"{help_text} score ({score}/{min_score}-{max_score})",
            )


def display_evaluation_comparison(evaluations: List[Dict[str, Any]]) -> None:
    """Display comparison of multiple evaluations.

    Args:
        evaluations: List of evaluation results
    """
    t = get_translator(st.session_state.get("language", "en"))

    if len(evaluations) < 2:
        st.info(t("display.comparison_info"))
        return

    # Prepare data for comparison
    comparison_data = []
    for i, eval_result in enumerate(evaluations):
        if "result" in eval_result and isinstance(eval_result["result"], dict):
            row = {
                "Evaluation": f"Eval {i + 1}",
                "Model": eval_result.get("model", "Unknown"),
                "Temperature": eval_result.get("temperature", 0),
                "Timestamp": eval_result.get("timestamp", ""),
            }

            # Add scores
            for key, value in eval_result["result"].items():
                if key != "reasoning" and isinstance(value, (int, float)):
                    row[key.replace("_", " ").title()] = value

            comparison_data.append(row)

    if not comparison_data:
        st.warning(t("display.no_comparison_data"))
        return

    df = pd.DataFrame(comparison_data)

    # Display table
    st.subheader(t("display.evaluation_comparison"))
    st.dataframe(df, use_container_width=True)

    # Create radar chart for score comparison
    score_columns = [col for col in df.columns if col not in ["Evaluation", "Model", "Temperature", "Timestamp"]]

    if score_columns:
        create_radar_chart(df, score_columns)


def create_radar_chart(df: "pd.DataFrame", score_columns: List[str]) -> None:
    """Create radar chart for score comparison.

    Args:
        df: DataFrame with evaluation data
        score_columns: List of score column names
    """
    fig = go.Figure()

    for idx, row in df.iterrows():
        values = [row[col] for col in score_columns]
        # Close the polygon by repeating the first value
        values.append(values[0])
        categories = score_columns + [score_columns[0]]

        fig.add_trace(
            go.Scatterpolar(
                r=values,
                theta=categories,
                fill="toself",
                name=f"{row['Evaluation']} ({row['Model']})",
                line=dict(width=2),
            )
        )

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 10])),
        showlegend=True,
        title="Score Comparison Radar Chart",
        height=500,
    )

    st.plotly_chart(fig, use_container_width=True)


def display_batch_results_summary(results: List[Dict[str, Any]]) -> None:
    """Display summary of batch evaluation results.

    Args:
        results: List of batch evaluation results
    """
    t = get_translator(st.session_state.get("language", "en"))

    if not results:
        st.info(t("display.no_batch_results"))
        return

    # Calculate summary statistics
    total_evaluations = len(results)
    successful_evaluations = len([r for r in results if "error" not in r.get("evaluation", {})])
    error_rate = (total_evaluations - successful_evaluations) / total_evaluations * 100

    # Display summary metrics
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total Evaluations", total_evaluations)

    with col2:
        st.metric("Successful", successful_evaluations)

    with col3:
        st.metric("Error Rate", f"{error_rate:.1f}%")

    # Extract scores for analysis
    score_data = []
    for result in results:
        if "error" not in result.get("evaluation", {}):
            eval_result = result["evaluation"]
            row = {
                "ID": result.get("id", ""),
                "Category": result.get("category", "Unknown"),
            }

            for key, value in eval_result.items():
                if key != "reasoning" and isinstance(value, (int, float)):
                    row[key.replace("_", " ").title()] = value

            score_data.append(row)

    if score_data:
        df = pd.DataFrame(score_data)

        # Display score distributions
        st.subheader("Score Distributions")

        score_columns = [col for col in df.columns if col not in ["ID", "Category"]]

        if score_columns:
            # Box plots for score distributions
            fig = go.Figure()

            for col in score_columns:
                fig.add_trace(go.Box(y=df[col], name=col, boxpoints="outliers"))

            fig.update_layout(
                title="Score Distribution by Dimension",
                yaxis_title="Score (1-10)",
                height=400,
            )

            st.plotly_chart(fig, use_container_width=True)

            # Category-wise analysis if categories are available
            if "Category" in df.columns and df["Category"].nunique() > 1:
                st.subheader("Scores by Category")

                # Calculate mean scores by category
                category_means = df.groupby("Category")[score_columns].mean()

                fig = px.bar(
                    category_means.reset_index().melt(id_vars="Category"),
                    x="Category",
                    y="value",
                    color="variable",
                    title="Average Scores by Category",
                    labels={"value": "Average Score", "variable": "Dimension"},
                )

                st.plotly_chart(fig, use_container_width=True)


def display_evaluation_details(
    evaluation: Dict[str, Any], expanded: bool = False, score_ranges: Optional[Dict[str, tuple]] = None
) -> None:
    """Display detailed view of a single evaluation.

    Args:
        evaluation: Single evaluation result
        expanded: Whether to show expanded view by default
        score_ranges: Optional dict mapping dimension keys to (min, max) tuples
    """
    t = get_translator(st.session_state.get("language", "en"))

    with st.expander(t("evaluation.details_header"), expanded=expanded):
        # Basic info
        col1, col2 = st.columns(2)

        with col1:
            st.subheader(t("evaluation.configuration_header"))
            # Try to get max_tokens from evaluation, fallback to config if missing
            max_tokens = evaluation.get("max_tokens")
            if max_tokens is None:
                # Try to get from config if available in session state
                try:
                    from pain_narratives.config.settings import get_settings
                    max_tokens = get_settings().model_config.default_max_tokens
                except Exception:
                    max_tokens = "N/A"
            st.json(
                {
                    t("evaluation.model_label"): evaluation.get("model", t("common.unknown")),
                    t("evaluation.temperature_label"): evaluation.get("temperature", 0),
                    t("evaluation.timestamp_label"): evaluation.get("timestamp", ""),
                    t("evaluation.max_tokens_label"): max_tokens,
                }
            )

        with col2:
            st.subheader(t("evaluation.input_narrative_header"))
            narrative = evaluation.get("narrative", t("evaluation.no_narrative_available"))
            st.text_area(t("evaluation.narrative_text_label"), value=narrative, height=150, disabled=True, label_visibility="collapsed")

        # Evaluation result
        if "result" in evaluation:
            st.subheader(t("evaluation.result_header"))
            result = evaluation["result"]

            # Get result in user's preferred language if it's a multilingual structure
            if isinstance(result, dict) and any(key in ["en", "es", "fr", "de"] for key in result.keys()):
                from pain_narratives.core.translation_service import TranslationService

                translation_service = TranslationService()
                current_language = st.session_state.get("language", "en")
                result = translation_service.get_available_translation(result, current_language)

            # Display scores
            display_score_metrics(result, columns=3, score_ranges=score_ranges)

            # Display reasoning
            if "reasoning" in result:
                st.subheader(t("evaluation.reasoning_header"))
                st.write(result["reasoning"])

            # Display model reasoning for questionnaires
            if "model_reasoning" in result:
                st.subheader(t("evaluation.model_reasoning_header"))
                st.write(result["model_reasoning"])

            explanation_keys = [k for k in result.keys() if k.endswith("_explanation")]
            if explanation_keys:
                st.subheader(t("evaluation.explanations_header"))
                for key in explanation_keys:
                    st.write(f"**{key.replace('_', ' ').title()}:** {result[key]}")

        # Raw response
        if "raw_response" in evaluation:
            with st.expander(t("evaluation.raw_response_header")):
                st.json(evaluation["raw_response"])


def create_prompt_preview(prompt_template: str, sample_narrative: Optional[str] = None) -> None:
    """Create a preview of how the prompt will look with a sample narrative.    Args:
    prompt_template: The prompt template with placeholders
    sample_narrative: Sample narrative to use for preview
    """
    if sample_narrative is None:
        sample_narrative = (
            "I've been experiencing constant pain in my joints for several months. "
            "The pain is particularly severe in the mornings and affects my ability to perform daily tasks."
        )

    st.subheader("Prompt Preview")

    try:
        formatted_prompt = prompt_template.format(narrative=sample_narrative)

        st.markdown("**How your prompt will appear to the model:**")
        st.code(formatted_prompt, language="text")

        # Character count
        char_count = len(formatted_prompt)
        token_estimate = char_count // 4  # Rough estimate

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Characters", char_count)
        with col2:
            st.metric("Estimated Tokens", token_estimate)

        if token_estimate > 3000:
            st.warning("⚠️ Prompt might be quite long. Consider shortening for cost efficiency.")

    except KeyError as e:
        st.error(f"❌ Missing placeholder in prompt: {e}")
    except Exception as e:
        st.error(f"❌ Error formatting prompt: {e}")


def display_cost_estimate(
    num_narratives: int,
    model: str,
    avg_prompt_tokens: int = 500,
    avg_response_tokens: int = 200,
) -> None:
    """Display estimated costs for evaluation.

    Args:
        num_narratives: Number of narratives to evaluate
        model: Model name
        avg_prompt_tokens: Average prompt tokens
        avg_response_tokens: Average response tokens
    """
    # Rough cost estimates (as of 2024 - should be updated)
    # See: https://openai.com/pricing for current pricing
    cost_per_1k_tokens = {
        "gpt-4o": {"input": 0.0025, "output": 0.01},
        "gpt-5-mini": {"input": 0.00015, "output": 0.0006},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    }

    if model in cost_per_1k_tokens:
        costs = cost_per_1k_tokens[model]

        total_input_tokens = num_narratives * avg_prompt_tokens
        total_output_tokens = num_narratives * avg_response_tokens

        input_cost = (total_input_tokens / 1000) * costs["input"]
        output_cost = (total_output_tokens / 1000) * costs["output"]
        total_cost = input_cost + output_cost

        st.subheader("💰 Cost Estimate")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Input Cost", f"${input_cost:.4f}")

        with col2:
            st.metric("Output Cost", f"${output_cost:.4f}")

        with col3:
            st.metric("Total Cost", f"${total_cost:.4f}")

        st.caption("*Estimates based on current OpenAI pricing. Actual costs may vary.*")
    else:
        st.info("Cost estimate not available for this model.")
