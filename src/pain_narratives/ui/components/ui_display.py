"""UI display components for pain narratives Streamlit app."""

from typing import Any, Callable, Dict, List, Optional

import pandas as pd
import streamlit as st


def display_evaluation_results(result: Dict[str, Any], dimension_labels: Optional[Dict[str, str]] = None) -> None:
    """
    Display the evaluation results in a Streamlit app with multilingual support.

    Args:
        result: The evaluation result dictionary.
        dimension_labels: Optional mapping of dimension keys to display labels.
    """
    st.subheader("🎯 Latest Evaluation Results")

    # Get evaluation result in user's preferred language
    evaluation_result = result.get("result", {})

    # Check if this is a multilingual result structure
    if isinstance(evaluation_result, dict) and any(key in ["en", "es", "fr", "de"] for key in evaluation_result.keys()):
        from pain_narratives.core.translation_service import TranslationService

        translation_service = TranslationService()
        current_language = st.session_state.get("language", "en")
        evaluation_result = translation_service.get_available_translation(evaluation_result, current_language)

    if isinstance(evaluation_result, dict) and "error" not in evaluation_result:
        col1, col2 = st.columns([2, 1])
        with col1:
            scores = {k: v for k, v in evaluation_result.items() if k != "reasoning" and isinstance(v, (int, float))}
            if scores:
                for dimension, score in scores.items():
                    st.metric(dimension.replace("_", " ").title(), f"{score}/10")
        with col2:
            if "reasoning" in evaluation_result:
                st.text_area(
                    "Reasoning",
                    evaluation_result["reasoning"],
                    height=150,
                    disabled=True,
                )
        # Show full model response as JSON
        with st.expander("🔍 Full Model Response", expanded=False):
            st.json(result["result"])
    elif isinstance(result["result"], list):
        st.write(f"Consistency test with {len(result['result'])} evaluations")
    with st.expander("📋 Evaluation Details"):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.write(f"**Model:** {result['model']}")
        with col2:
            st.write(f"**Temperature:** {result['temperature']}")
        with col3:
            st.write(f"**Timestamp:** {result['timestamp'][:19]}")


def display_batch_results(results: List[Dict[str, Any]], dimension_labels: Optional[Dict[str, str]] = None) -> None:
    """
    Display batch evaluation results in a Streamlit app.

    Args:
        results: List of evaluation result dictionaries.
        dimension_labels: Optional mapping of dimension keys to display labels.
    """
    st.subheader("📊 Batch Results Summary")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Processed", len(results))
    with col2:
        st.metric(
            "Successful",
            sum(1 for result in results if "error" not in result.get("evaluation", {})),
        )
    with col3:
        st.metric(
            "Errors",
            sum(1 for result in results if "error" in result.get("evaluation", {})),
        )
    with col4:
        success_rate = (
            (sum(1 for result in results if "error" not in result.get("evaluation", {})) / len(results)) * 100
            if results
            else 0
        )
        st.metric("Success Rate", f"{success_rate:.1f}%")
    if results:
        st.subheader("📋 Detailed Results")
        table_data = []
        for result in results:
            row = {
                "ID": result.get("id", ""),
                "Category": result.get("category", "Unknown"),
                "Status": "Error" if "error" in result.get("evaluation", {}) else "Success",
                "Timestamp": result.get("timestamp", "")[:19],
            }
            if "evaluation" in result and "error" not in result["evaluation"]:
                eval_result = result["evaluation"]
                scores = []
                for key, value in eval_result.items():
                    if key != "reasoning" and isinstance(value, (int, float)):
                        row[key] = float(value)
                        scores.append(float(value))
                if scores:
                    row["Average Score"] = round(sum(scores) / len(scores), 1)
            else:
                row["Error"] = result.get("evaluation", {}).get("error", "")[:50]
            table_data.append(row)
        results_df = pd.DataFrame(table_data)
        st.dataframe(results_df, use_container_width=True)
        csv = results_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Results CSV",
            data=csv,
            file_name=f"batch_results_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
        )


def display_custom_ui(custom_func: Callable[[], None]) -> None:
    """
    Display a custom UI component in the Streamlit app.

    Args:
        custom_func: A function that renders custom Streamlit UI elements.
    """
    custom_func()
