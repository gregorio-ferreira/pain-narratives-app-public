"""Streamlit component for collecting assessment feedback from experts."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

import streamlit as st

from pain_narratives.ui.utils.localization import get_translator

__all__ = ["render_assessment_feedback_form"]

LIKERT_OPTIONS: List[tuple[str, str]] = [
    ("Strongly Disagree", "strongly_disagree"),
    ("Disagree", "disagree"),
    ("Somewhat Disagree", "somewhat_disagree"),
    ("Neither Agree Nor Disagree", "neither_agree_nor_disagree"),
    ("Somewhat Agree", "somewhat_agree"),
    ("Agree", "agree"),
    ("Strongly Agree", "strongly_agree"),
]

_VALUE_TO_INDEX = {value: idx for idx, (value, _) in enumerate(LIKERT_OPTIONS)}


def _format_option(value: str) -> str:
    t = get_translator(st.session_state.get("language", "en"))
    key = dict(LIKERT_OPTIONS)[value]
    return t(f"assessment_feedback.options.{key}")


def _option_index(current: Optional[str]) -> int:
    if current is None:
        return 3  # Default to "Neither Agree Nor Disagree"
    return _VALUE_TO_INDEX.get(current, 3)


def _dimension_streamlit_key(dimension: Dict[str, Any], experiment_id: int, suffix: str) -> str:
    base = dimension.get("uuid") or re.sub(r"[^0-9a-zA-Z_]+", "_", str(dimension.get("name", "")).strip().lower())
    if not base:
        base = "dimension"
    return f"feedback_{experiment_id}_{base}_{suffix}"


def render_assessment_feedback_form(evaluation: Dict[str, Any], dimensions: Optional[List[Dict[str, Any]]] = None) -> None:
    """Render dimension-based feedback form beneath the assessment results."""
    if not evaluation:
        return

    t = get_translator(st.session_state.get("language", "en"))
    db_manager = st.session_state.get("db_manager")
    user = st.session_state.get("user")

    if not db_manager or not user:
        st.info(t("assessment_feedback.no_database_warning"))
        return

    experiment_id = evaluation.get("experiment_id")
    group_id = (
        evaluation.get("experiment_group_id")
        or evaluation.get("experiments_group_id")
        or st.session_state.get("selected_experiment_group_id")
    )

    if experiment_id is None or group_id is None:
        st.info(t("assessment_feedback.no_experiment_info"))
        return

    # Check for recently completed feedback in session state
    feedback_completion_key = f"assessment_feedback_completed_{experiment_id}_{user.get('id')}"
    recently_completed = st.session_state.get(feedback_completion_key, False)

    # Get active dimensions to provide feedback for
    active_dimensions = []
    if dimensions:
        seen_names = set()
        for dim in dimensions:
            if not dim.get("active", True):
                continue
            name = str(dim.get("name", "")).strip()
            if not name or name in seen_names:
                continue
            seen_names.add(name)
            active_dimensions.append(dim)

    if not active_dimensions:
        st.info("No dimensions available for feedback.")
        return

    st.subheader(t("assessment_feedback.header"))
    st.write(t("assessment_feedback.instructions"))

    # Check database for existing feedback
    existing = db_manager.get_assessment_feedback(experiment_id, user.get("id")) if db_manager else None
    feedback_already_exists = existing is not None or recently_completed
    
    if feedback_already_exists:
        st.success(t("assessment_feedback.feedback_completed"))
        st.caption(t("assessment_feedback.already_submitted_info"))
        
        # Show existing feedback in read-only mode
        if existing and existing.dimension_feedback:
            st.write("**" + t("assessment_feedback.header") + " - " + t("assessment_feedback.dimension_group_header").format(dimension="Summary") + "**")
            
            for dim_name, dim_values in existing.dimension_feedback.items():
                if isinstance(dim_values, dict):
                    st.write(f"**{dim_name}:**")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.info(f"Score: {dim_values.get('score_alignment', 'N/A')}")
                    with col2:
                        st.info(f"Explanation: {dim_values.get('explanation_alignment', 'N/A')}")
                    with col3:
                        st.info(f"Usage: {dim_values.get('usage_intent', 'N/A')}")
        else:
            # Recently completed case - show session state data
            recent_data = st.session_state.get(f"recent_assessment_feedback_{experiment_id}_{user.get('id')}", {})
            if recent_data:
                st.write("**" + t("assessment_feedback.header") + " - Summary**")
                for dim_name, dim_values in recent_data.items():
                    if isinstance(dim_values, dict):
                        st.write(f"**{dim_name}:**")
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.info(f"Score: {dim_values.get('score_alignment', 'N/A')}")
                        with col2:
                            st.info(f"Explanation: {dim_values.get('explanation_alignment', 'N/A')}")
                        with col3:
                            st.info(f"Usage: {dim_values.get('usage_intent', 'N/A')}")
        
        return  # Exit early if feedback already exists

    likert_values = [value for value, _ in LIKERT_OPTIONS]
    label_map = {value: _format_option(value) for value in likert_values}
    placeholder = t("assessment_feedback.select_placeholder")

    def select_question(
        label_key: str,
        default_value: Optional[str],
        key: str,
        *,
        dimension_name: str,
    ) -> Optional[str]:
        """Render a selectbox question for a dimension."""
        label_text = t(label_key).format(dimension=dimension_name)

        kwargs: Dict[str, Any] = {
            "label": label_text,
            "options": likert_values,
            "format_func": lambda value: label_map[value],
            "key": key,
            "placeholder": placeholder,
        }

        index = _option_index(default_value)
        kwargs["index"] = index
        return st.selectbox(**kwargs)

    # Get existing dimension feedback defaults
    dimension_defaults: Dict[str, Dict[str, Optional[str]]] = {}
    if existing and existing.dimension_feedback:
        for name, values in existing.dimension_feedback.items():
            if isinstance(values, dict):
                dimension_defaults[name] = {
                    "score": values.get("score_alignment"),
                    "explanation": values.get("explanation_alignment"),
                    "usage": values.get("usage_intent"),
                }

    with st.form(f"assessment_feedback_form_{experiment_id}"):
        dimension_responses: Dict[str, Dict[str, Optional[str]]] = {}
        
        # Create feedback sections organized by dimension
        for dim in active_dimensions:
            name = str(dim.get("name", "")).strip()
            defaults = dimension_defaults.get(name, {})
            
            # Create a visual group for each dimension
            st.markdown(f"### {t('assessment_feedback.dimension_group_header').format(dimension=name)}")
            
            with st.container():
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    score_key = _dimension_streamlit_key(dim, experiment_id, "score")
                    score_alignment = select_question(
                        "assessment_feedback.dimension_score_question",
                        defaults.get("score"),
                        score_key,
                        dimension_name=name,
                    )
                
                with col2:
                    explanation_key = _dimension_streamlit_key(dim, experiment_id, "explanation")
                    explanation_alignment = select_question(
                        "assessment_feedback.dimension_explanation_question",
                        defaults.get("explanation"),
                        explanation_key,
                        dimension_name=name,
                    )
                
                with col3:
                    usage_key = _dimension_streamlit_key(dim, experiment_id, "usage")
                    usage_intent = select_question(
                        "assessment_feedback.dimension_usage_question",
                        defaults.get("usage"),
                        usage_key,
                        dimension_name=name,
                    )

                dimension_responses[name] = {
                    "score_alignment": score_alignment,
                    "explanation_alignment": explanation_alignment,
                    "usage_intent": usage_intent,
                }
            
            st.markdown("---")  # Visual separator between dimensions

        submitted = st.form_submit_button(t("assessment_feedback.submit_button"))

    if not submitted:
        return

    # Check for missing responses
    missing_responses = []
    for dim_name, dim_values in dimension_responses.items():
        for question_type, response in dim_values.items():
            if response is None:
                missing_responses.append(f"{dim_name} - {question_type}")

    if missing_responses:
        st.warning(t("assessment_feedback.incomplete_warning"))
        return

    # Prepare payload - keep backward compatibility with existing DB schema
    # Set dimension-only feedback in dimension_feedback JSON field
    # Leave intensity/disability fields as empty strings for backward compatibility
    payload = {
        "experiment_id": experiment_id,
        "experiments_group_id": group_id,
        "user_id": user["id"],
        "narrative_id": evaluation.get("narrative_id") or st.session_state.get("current_narrative_id"),
        "intensity_score_alignment": "",  # No longer used but required by schema
        "intensity_explanation_alignment": "",  # No longer used but required by schema
        "intensity_usage_intent": "",  # No longer used but required by schema
        "disability_score_alignment": "",  # No longer used but required by schema
        "disability_explanation_alignment": "",  # No longer used but required by schema
        "disability_usage_intent": "",  # No longer used but required by schema
        "dimension_feedback": dimension_responses,
    }

    try:
        db_manager.save_assessment_feedback(payload)
        
        # Mark feedback as completed in session state
        st.session_state[feedback_completion_key] = True
        
        # Store recent feedback data for display
        recent_feedback_key = f"recent_assessment_feedback_{experiment_id}_{user.get('id')}"
        st.session_state[recent_feedback_key] = dimension_responses
        
        st.success(t("assessment_feedback.save_success"))
        st.rerun()  # Force re-run to show completion status
        
    except Exception as exc:  # noqa: BLE001 generic user feedback
        st.error(t("assessment_feedback.save_error").format(error=str(exc)))
