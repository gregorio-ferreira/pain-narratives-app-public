"""Streamlit component for collecting questionnaire feedback from experts."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import streamlit as st

from pain_narratives.ui.utils.localization import get_translator

__all__ = ["render_questionnaire_feedback_form"]

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
    return t(f"questionnaire_feedback.options.{key}")


def _option_index(current: Optional[str]) -> int:
    if current is None:
        return 3  # Default to "Neither Agree Nor Disagree"
    return _VALUE_TO_INDEX.get(current, 3)


def render_questionnaire_feedback_form(
    questionnaire_result: Dict[str, Any],
    questionnaire_name: str,
    experiment_id: Optional[int],
    group_id: int,
    narrative_id: Optional[int] = None,
) -> None:
    """Render feedback form beneath questionnaire results."""
    if not questionnaire_result:
        return

    t = get_translator(st.session_state.get("language", "en"))
    db_manager = st.session_state.get("db_manager")
    user = st.session_state.get("user")

    if not db_manager or not user:
        st.info(t("questionnaire_feedback.no_database_warning"))
        return

    questionnaire_id = questionnaire_result.get("id")
    if questionnaire_id is None:
        st.info(t("questionnaire_feedback.no_questionnaire_info"))
        return

    st.subheader(t("questionnaire_feedback.header"))
    st.write(t("questionnaire_feedback.instructions"))

    # Check for recently completed feedback in session state
    feedback_completion_key = f"questionnaire_feedback_completed_{questionnaire_id}_{user.get('id')}"
    recently_completed = st.session_state.get(feedback_completion_key, False)

    # Check database for existing feedback
    existing = db_manager.get_questionnaire_feedback(questionnaire_id, user.get("id"))
    feedback_already_exists = existing is not None or recently_completed
    
    if feedback_already_exists:
        st.success(t("questionnaire_feedback.feedback_completed"))
        st.caption(t("questionnaire_feedback.already_submitted_info"))
        
        # Show existing feedback in read-only mode (prefer database data over session state)
        if existing:
            st.write("**" + t("questionnaire_feedback.authenticity_question") + "**")
            st.info(existing.authenticity_rating)
            
            st.write("**" + t("questionnaire_feedback.reasoning_question") + "**")
            st.info(existing.reasoning_adequacy_rating)
        else:
            # Recently completed case - show session state data
            recent_data = st.session_state.get(f"recent_feedback_{questionnaire_id}_{user.get('id')}", {})
            if recent_data:
                st.write("**" + t("questionnaire_feedback.authenticity_question") + "**")
                st.info(recent_data.get("authenticity_rating", "N/A"))
                
                st.write("**" + t("questionnaire_feedback.reasoning_question") + "**")
                st.info(recent_data.get("reasoning_adequacy_rating", "N/A"))
        
        return  # Exit early if feedback already exists

    likert_values = [value for value, _ in LIKERT_OPTIONS]
    label_map = {value: _format_option(value) for value in likert_values}
    placeholder = t("questionnaire_feedback.select_placeholder")

    def select_question(
        label_key: str,
        default_value: Optional[str],
        key: str,
    ) -> Optional[str]:
        """Render a selectbox question."""
        label_text = t(label_key)

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

    # Render form only if no existing feedback
    with st.form(f"questionnaire_feedback_form_{questionnaire_id}"):
        st.markdown("#### " + t("questionnaire_feedback.expert_instructions"))
        
        authenticity_rating = select_question(
            "questionnaire_feedback.authenticity_question",
            None,  # Always start fresh
            f"authenticity_{questionnaire_id}",
        )
        
        reasoning_rating = select_question(
            "questionnaire_feedback.reasoning_question",
            None,  # Always start fresh
            f"reasoning_{questionnaire_id}",
        )

        submitted = st.form_submit_button(t("questionnaire_feedback.submit_button"))

    if not submitted:
        return

    # Check for missing responses
    if authenticity_rating is None or reasoning_rating is None:
        st.warning(t("questionnaire_feedback.incomplete_warning"))
        return

    # Prepare payload
    payload = {
        "questionnaire_id": questionnaire_id,
        "experiment_id": experiment_id,
        "experiments_group_id": group_id,
        "user_id": user["id"],
        "narrative_id": narrative_id,
        "questionnaire_name": questionnaire_name,
        "authenticity_rating": authenticity_rating,
        "reasoning_adequacy_rating": reasoning_rating,
    }

    try:
        db_manager.save_questionnaire_feedback(payload)
        
        # Mark feedback as completed in session state
        st.session_state[feedback_completion_key] = True
        
        # Store recent feedback data for display
        recent_feedback_key = f"recent_feedback_{questionnaire_id}_{user.get('id')}"
        st.session_state[recent_feedback_key] = {
            "authenticity_rating": authenticity_rating,
            "reasoning_adequacy_rating": reasoning_rating,
        }
        
        st.success(t("questionnaire_feedback.save_success"))
        st.rerun()  # Force re-run to show completion status
        
    except Exception as exc:  # noqa: BLE001 generic user feedback
        st.error(t("questionnaire_feedback.save_error").format(error=str(exc)))
