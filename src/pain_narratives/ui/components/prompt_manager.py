"""Components for managing evaluation prompts."""

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, cast

import pandas as pd
import streamlit as st

from pain_narratives.config.prompts import (
    get_base_prompt,
    get_default_dimensions,
    get_default_prompt,
    get_prompt_library,
    get_system_role,
)
from pain_narratives.ui.utils.localization import get_translator

# Default prompt components loaded from YAML configuration
# These are loaded from src/pain_narratives/config/default_prompts.yaml
DEFAULT_SYSTEM_ROLE = get_system_role()
DEFAULT_BASE_PROMPT = get_base_prompt()
DEFAULT_PROMPT = get_default_prompt()


def dimensions_editor_no_form(
    state_key: str = "current_dimensions_alt",
    show_preview: bool = False,
    auto_save_to_db: bool = False,
    experiment_group_id: Optional[int] = None,
    user_id: Optional[int] = None,
) -> Tuple[List[Dict[str, Any]], bool, bool]:
    """Display the dimensions editor without form."""
    from pain_narratives.ui.utils.localization import get_translator

    t = get_translator(st.session_state.get("language", "en"))

    if state_key not in st.session_state:
        # Load default dimensions from YAML configuration
        st.session_state[state_key] = get_default_dimensions()

    dims = st.session_state[state_key]

    # Ensure backward compatibility: add active field if missing
    for dim in dims:
        if "active" not in dim:
            dim["active"] = True

    # Filter to only show active dimensions
    active_dims = [dim for dim in dims if dim.get("active", True)]

    # Ensure all active dims have a unique uuid
    seen = set()
    for dim in active_dims:
        uid = dim.get("uuid")
        if not uid or uid in seen:
            # Generate truly unique UUID with timestamp
            uid = f"{int(datetime.now().timestamp() * 1000000)}_{str(uuid.uuid4())}"
            dim["uuid"] = uid
        seen.add(uid)

    # Headers: Replace 'Acciones' with 'Seleccionar para eliminar' (localized)
    cols = st.columns([2, 4, 1, 1, 1])
    with cols[0]:
        st.markdown(t("ui_text.dimension_name_title"))
    with cols[1]:
        st.markdown(t("ui_text.definition_explanation_title"))
    with cols[2]:
        st.markdown(t("ui_text.lowest_score_title"))
    with cols[3]:
        st.markdown(t("ui_text.highest_score_title"))
    with cols[4]:
        st.markdown(t("ui_text.select_for_removal_label"))

    invalid_range = False
    invalid_fields = False

    # Initialize selection state in session_state if not exists - use list instead of set
    selection_key = f"{state_key}_selected_for_removal"
    if selection_key not in st.session_state:
        st.session_state[selection_key] = []

    # Get current selections as a list
    current_selections = st.session_state[selection_key].copy()

    for i, dim in enumerate(active_dims):
        c1, c2, c3, c4, c5 = st.columns([2, 4, 1, 1, 1])

        dim["name"] = c1.text_input(
            "Dimension Name",
            value=dim.get("name", ""),
            key=f"{state_key}_dim_name_{dim['uuid']}",
            label_visibility="collapsed",
        )
        if not dim["name"].strip():
            invalid_fields = True
            c1.warning("Required")

        dim["definition"] = c2.text_input(
            "Definition",
            value=dim.get("definition", ""),
            key=f"{state_key}_dim_def_{dim['uuid']}",
            label_visibility="collapsed",
        )
        if not dim["definition"].strip():
            invalid_fields = True
            c2.warning("Required")

        min_val = int(dim.get("min", "0"))
        max_val = int(dim.get("max", "10"))

        min_input = c3.number_input(
            "Lowest Score",
            min_value=-1000,
            max_value=1000,
            value=min_val,
            step=1,
            key=f"{state_key}_dim_min_{dim['uuid']}",
            label_visibility="collapsed",
        )

        max_input = c4.number_input(
            "Highest Score",
            min_value=-1000,
            max_value=1000,
            value=max_val,
            step=1,
            key=f"{state_key}_dim_max_{dim['uuid']}",
            label_visibility="collapsed",
        )

        dim["min"] = str(min_input)
        dim["max"] = str(max_input)

        if max_input <= min_input:
            invalid_range = True
            c4.warning("Highest Score must be greater than Lowest Score")

        # Selection checkbox for removal - only show checkbox, no label, for compactness
        dim_uuid = dim["uuid"]
        is_selected = c5.checkbox(
            label=" ",  # Non-empty label for accessibility
            value=dim_uuid in current_selections,
            key=f"{state_key}_select_dim_{dim_uuid}",
            help=t("ui_text.remove_dimension_help").format(dimension_name=dim["name"] or f"Dimension {i+1}"),
            label_visibility="collapsed",
        )

        # Update selections based on checkbox state
        if is_selected and dim_uuid not in current_selections:
            current_selections.append(dim_uuid)
        elif not is_selected and dim_uuid in current_selections:
            current_selections.remove(dim_uuid)

    # Update session state with current selections
    st.session_state[selection_key] = current_selections

    # Add spacing and action buttons
    st.markdown("")

    # Row for action buttons
    col1, col2 = st.columns([1, 1])

    with col1:
        # Add dimension button
        if st.button(t("ui_text.add_dimension_button"), key=f"add_dim_button_{state_key}"):
            timestamp = int(datetime.now().timestamp() * 1000000)
            new_uuid = f"{timestamp}_new_{str(uuid.uuid4())}"
            dims.append({"name": "", "definition": "", "min": "0", "max": "10", "uuid": new_uuid, "active": True})
            st.session_state[state_key] = dims
            st.rerun()

    with col2:
        # Get list of selected dimension UUIDs
        selected_uuids = st.session_state[selection_key]

        if selected_uuids:
            # Count how many dimensions are selected
            selected_count = len(selected_uuids)

            # Check if we're in confirmation mode
            confirm_key = f"confirm_removal_{state_key}"
            in_confirmation = st.session_state.get(confirm_key, False)

            if in_confirmation:
                # Show confirmation message and buttons
                st.warning(t("ui_text.confirm_remove_dimensions").format(count=selected_count))

                col2a, col2b = st.columns(2)
                with col2a:
                    if st.button("✅ Confirm", key=f"confirm_yes_{state_key}", type="primary"):
                        # Perform soft deletion by marking dimensions as inactive
                        for dim in dims:
                            if dim["uuid"] in selected_uuids:
                                dim["active"] = False

                        # Update session state with modified dimensions
                        st.session_state[state_key] = dims

                        # Save to database if auto-save is enabled
                        if auto_save_to_db and experiment_group_id and user_id:
                            try:
                                db_manager = st.session_state.get("db_manager")
                                if db_manager:
                                    success = db_manager.update_experiment_group(
                                        group_id=experiment_group_id, user_id=user_id, dimensions=dims
                                    )
                                    if success:
                                        st.success(t("ui_text.dimensions_removed_and_saved_success"))
                                    else:
                                        st.error(t("ui_text.dimensions_save_failed"))
                                else:
                                    st.warning(t("ui_text.dimensions_removed_no_db"))
                            except Exception as e:
                                st.error(f"{t('ui_text.dimensions_save_error')}: {str(e)}")
                        else:
                            st.success(t("ui_text.dimensions_removed_success"))

                        st.session_state[selection_key] = []  # Clear selections
                        st.session_state[confirm_key] = False  # Clear confirmation state
                        st.rerun()

                with col2b:
                    if st.button("❌ Cancel", key=f"confirm_no_{state_key}"):
                        st.session_state[confirm_key] = False
                        st.rerun()
            else:
                # Normal remove button
                button_text = f"{t('ui_text.remove_selected_dimensions_button')} ({selected_count})"
                if st.button(button_text, key=f"remove_selected_button_{state_key}", type="secondary"):
                    st.session_state[confirm_key] = True
                    st.rerun()
        else:
            # Show disabled button when nothing is selected
            st.button(
                t("ui_text.remove_selected_dimensions_button"),
                key=f"remove_selected_disabled_{state_key}",
                disabled=True,
                help=t("ui_text.no_dimensions_selected_warning"),
            )

    # Always update session state with current dimensions to ensure latest values
    st.session_state[state_key] = dims

    # Show preview if requested
    if show_preview:
        st.markdown("---")
        st.markdown(t("ui_text.generated_prompt_preview"))
        generated_prompt = generate_prompt_from_dimensions(dims)
        st.code(generated_prompt, language="text")

        # Character/token count
        char_count = len(generated_prompt)
        token_estimate = char_count // 4

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Characters", char_count)
        with col2:
            st.metric("Estimated Tokens", token_estimate)

    return dims, invalid_range, invalid_fields


def generate_prompt_from_dimensions(
    dims: list[dict],
    system_role: Optional[str] = DEFAULT_SYSTEM_ROLE,
    base_prompt: Optional[str] = DEFAULT_BASE_PROMPT,
) -> str:
    """Generate a full prompt from dimensions and optional prompt pieces."""

    # Filter to only use active dimensions
    active_dims = [dim for dim in dims if dim.get("active", True)]

    # Dimensions definition section
    dimension_lines = [
        "Please analyze the following narrative and provide scores for these dimensions as specified:",
        "",
    ]

    for idx, dim in enumerate(active_dims, 1):
        dimension_lines.append(
            f"{idx}. **{dim['name']}**: {dim['definition']} (Score range: {dim['min']}-{dim['max']})"
        )

    # Base instructions
    effective_base = base_prompt if base_prompt else ""

    # JSON structure definition
    json_structure = ["Please respond in JSON format with the following structure:", "{{"]

    for dim in active_dims:
        field_name = dim["name"].lower().replace(" ", "_").replace("-", "_")
        json_structure.append(f'    "{field_name}": <score>,')
        json_structure.append(
            f'    "{field_name}_explanation": "<explanation in English for the {dim["name"].lower()}">",'
        )

    json_structure.extend(['    "reasoning": "<brief explanation of your overall scoring>"', "}}"])

    # Narrative placeholder
    narrative_placeholder = "Patient narrative:\n{narrative}"

    # Combine all parts
    parts = []
    if system_role:
        parts.append(system_role)
    parts.append("\n".join(dimension_lines))
    if effective_base:
        parts.append(effective_base)
    parts.append("\n".join(json_structure))
    parts.append(narrative_placeholder)

    full_prompt = "\n\n".join(parts)

    return full_prompt


class PromptManager:
    """Manager for evaluation prompts."""

    def __init__(self) -> None:
        """Initialize the prompt manager."""
        if "saved_prompts" not in st.session_state:
            st.session_state.saved_prompts = self._get_default_prompts()
        if "prompt_history" not in st.session_state:
            st.session_state.prompt_history = []
        if "current_prompt" not in st.session_state:
            st.session_state.current_prompt = DEFAULT_PROMPT

    def _get_default_prompts(self) -> Dict[str, Dict[str, Any]]:
        """Get default prompt templates from YAML configuration."""
        return get_prompt_library()

    def display_prompt_library(self) -> Optional[str]:
        """Display the prompt library and return selected prompt."""
        t = get_translator(st.session_state.get("language", "en"))
        st.subheader(t("ui_text.prompt_library_header"))

        if not st.session_state.saved_prompts:
            st.info(t("ui_text.no_saved_prompts_info"))
            return None

        # Filter by category
        categories = set(prompt["category"] for prompt in st.session_state.saved_prompts.values())
        selected_category = st.selectbox(t("ui_text.filter_by_category_label"), ["All"] + sorted(categories))

        # Display prompts
        filtered_prompts = {}
        for key, prompt in st.session_state.saved_prompts.items():
            if selected_category == "All" or prompt["category"] == selected_category:
                filtered_prompts[key] = prompt

        if not filtered_prompts:
            st.info(t("ui_text.no_prompts_in_category_info"))
            return None

        selected_prompt_key = st.selectbox(
            "Select a prompt:",
            options=list(filtered_prompts.keys()),
            format_func=lambda x: (f"{filtered_prompts[x]['name']} - {filtered_prompts[x]['description']}"),
        )

        if selected_prompt_key:
            prompt = filtered_prompts[selected_prompt_key]

            col1, col2, col3 = st.columns([2, 1, 1])

            with col1:
                st.write(f"**Description:** {prompt['description']}")
                st.write(f"**Category:** {prompt['category']}")
                st.write(f"**Created:** {prompt['created'][:10]}")

            with col2:
                if st.button(t("ui_text.use_this_prompt_button")):
                    return cast(str, prompt["template"])

            with col3:
                if st.button(t("ui_text.delete_prompt_button"), type="secondary"):
                    if st.session_state.get("confirm_delete"):
                        del st.session_state.saved_prompts[selected_prompt_key]
                        st.success(t("ui_text.prompt_deleted_success"))
                        # Let Streamlit's natural rerun handle the update
                    else:
                        st.session_state.confirm_delete = True
                        st.warning(t("ui_text.confirm_deletion_warning"))

            # Preview
            with st.expander("Preview Prompt"):
                st.code(prompt["template"], language="text")

        return None

    def save_prompt_dialog(self, current_prompt: str) -> None:
        """Display dialog for saving current prompt."""
        t = get_translator(st.session_state.get("language", "en"))
        st.subheader(t("ui_text.save_current_prompt_header"))

        with st.form("save_prompt_form"):
            col1, col2 = st.columns(2)

            with col1:
                prompt_name = st.text_input(
                    t("ui_text.prompt_name_label"), placeholder=t("ui_text.custom_evaluation_placeholder")
                )
                prompt_description = st.text_area(
                    t("ui_text.description_label_short"),
                    placeholder=t("ui_text.prompt_purpose_placeholder"),
                )

            with col2:
                prompt_category = st.selectbox(
                    "Category",
                    ["general", "chronic_pain", "research", "clinical", "custom"],
                    help=t("ui_text.category_organization_help"),
                )

                custom_category = st.text_input(t("ui_text.custom_category_label"))

            submitted = st.form_submit_button("Save Prompt")

            if submitted:
                if not prompt_name:
                    st.error(t("ui_text.provide_name_error"))
                    return

                if not prompt_description:
                    st.error(t("ui_text.provide_description_error"))
                    return

                # Use custom category if provided
                final_category = custom_category if prompt_category == "custom" and custom_category else prompt_category

                # Create unique key
                prompt_key = f"{prompt_name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

                # Save prompt
                st.session_state.saved_prompts[prompt_key] = {
                    "name": prompt_name,
                    "description": prompt_description,
                    "template": current_prompt,
                    "created": datetime.now().isoformat(),
                    "category": final_category,
                }

                st.success(t("ui_text.prompt_saved_success").format(prompt_name=prompt_name))

    def display_prompt_editor(self, current_prompt: str) -> str:
        """Display advanced prompt editor."""
        t = get_translator(st.session_state.get("language", "en"))
        st.subheader(t("ui_text.advanced_prompt_editor_header"))

        # Tabs for different editing modes
        tab1, tab2, tab3 = st.tabs(["Edit", "Variables", "Validation"])

        with tab1:
            # Main editor
            edited_prompt = st.text_area(
                "Prompt Template:",
                value=current_prompt,
                height=400,
                help=t("ui_text.narrative_placeholder_help"),
            )

            # Quick actions
            col1, col2, col3 = st.columns(3)

            with col1:
                if st.button(t("ui_text.add_json_structure_button")):
                    json_template = """
{
    "dimension1": <score>,
    "dimension2": <score>,
    "reasoning": "<explanation>"
}"""
                    if "{" not in edited_prompt:
                        edited_prompt += "\n\nPlease respond in JSON format:" + json_template

            with col2:
                if st.button(t("ui_text.add_scale_definition_button")):
                    scale_def = (
                        "\n\nScoring Scale:\n1-2: Very Low\n3-4: Low\n5-6: Moderate\n" "7-8: High\n9-10: Very High"
                    )
                    edited_prompt += scale_def

            with col3:
                if st.button(t("ui_text.add_medical_context_button")):
                    context = (
                        "\n\nContext: You are evaluating narratives from patients with chronic pain conditions. "
                        "Consider both the medical and psychosocial aspects of the patient's experience."
                    )
                    edited_prompt = context + "\n\n" + edited_prompt

        with tab2:
            st.subheader(t("ui_text.available_variables_header"))
            st.markdown(
                """
            **Available placeholders:**
            - `{narrative}` - The patient narrative text

            **Planned variables (not yet implemented):**
            - `{patient_age}` - Patient age
            - `{condition}` - Primary diagnosis
            - `{duration}` - Pain duration
            """
            )

            # Variable validation
            if "{narrative}" not in edited_prompt:
                st.error(t("ui_text.placeholder_required_error"))

        with tab3:
            st.subheader(t("ui_text.prompt_validation_header"))

            # Basic validation
            issues = []

            if len(edited_prompt) < 50:
                issues.append("Prompt seems very short")

            if len(edited_prompt) > 4000:
                issues.append("Prompt is quite long - may be expensive")

            if "{narrative}" not in edited_prompt:
                issues.append("Missing {narrative} placeholder")

            if "json" not in edited_prompt.lower():
                issues.append("Consider requesting JSON output for easier parsing")

            if not any(char.isdigit() for char in edited_prompt):
                issues.append("Consider specifying a scoring scale (e.g., 1-10)")

            if issues:
                st.warning(t("ui_text.potential_issues_warning"))
                for issue in issues:
                    st.write(f"• {issue}")
            else:
                st.success(t("ui_text.prompt_looks_good"))

            # Character/token count
            char_count = len(edited_prompt)
            token_estimate = char_count // 4

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Characters", char_count)
            with col2:
                st.metric("Estimated Tokens", token_estimate)

        return edited_prompt

    def export_prompts(self) -> str:
        """Export all saved prompts as JSON."""
        return json.dumps(st.session_state.saved_prompts, indent=2, default=str)

    def import_prompts(self, uploaded_file: Any) -> bool:
        """Import prompts from uploaded JSON file."""
        t = get_translator(st.session_state.get("language", "en"))
        try:
            content = uploaded_file.read()
            imported_prompts = json.loads(content)

            # Validate structure
            for key, prompt in imported_prompts.items():
                required_fields = ["name", "description", "template", "category"]
                if not all(field in prompt for field in required_fields):
                    st.error(f"Invalid prompt structure in {key}")
                    return False

            # Merge with existing prompts
            st.session_state.saved_prompts.update(imported_prompts)
            st.success(f"Successfully imported {len(imported_prompts)} prompts!")
            return True

        except json.JSONDecodeError:
            st.error(t("ui_text.invalid_json_file_error"))
            return False
        except Exception as e:
            st.error(f"Import failed: {str(e)}")
            return False

    def display_prompt_analytics(self) -> None:
        """Display analytics about prompt usage."""
        t = get_translator(st.session_state.get("language", "en"))
        st.subheader(t("ui_text.prompt_analytics_header"))

        if not st.session_state.prompt_history:
            st.info(t("ui_text.no_prompt_history_info"))
            return

        # Usage statistics
        history_df = pd.DataFrame(st.session_state.prompt_history)

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Total Uses", len(history_df))

        with col2:
            unique_prompts = history_df["prompt_name"].nunique()
            st.metric("Unique Prompts", unique_prompts)

        with col3:
            if "timestamp" in history_df.columns:
                recent_uses = len(
                    history_df[history_df["timestamp"] > datetime.now().replace(hour=0, minute=0, second=0)]
                )
                st.metric("Uses Today", recent_uses)

        # Most used prompts
        if "prompt_name" in history_df.columns:
            prompt_counts = history_df["prompt_name"].value_counts()
            st.subheader(t("ui_text.most_used_prompts_header"))
            st.bar_chart(prompt_counts.head(10))

    def log_prompt_usage(self, prompt_name: str, prompt_content: str) -> None:
        """Log prompt usage for analytics."""
        st.session_state.prompt_history.append(
            {
                "prompt_name": prompt_name,
                "prompt_length": len(prompt_content),
                "timestamp": datetime.now().isoformat(),
                "character_count": len(prompt_content),
            }
        )


def get_current_prompt() -> str:
    """Get the current prompt string. Uses Evaluation group prompt if available."""
    # Check if we have a current prompt in session state
    current_prompt = st.session_state.get("current_prompt")
    if current_prompt:
        return current_prompt

    # Check if we have an Evaluation group selected with dimensions
    selected_dimensions = st.session_state.get("selected_group_dimensions")
    if selected_dimensions:
        # Generate prompt from Evaluation group data
        group_system_role = st.session_state.get("selected_group_system_role")
        group_base_prompt = st.session_state.get("selected_group_base_prompt")

        group_prompt = generate_prompt_from_dimensions(selected_dimensions, group_system_role, group_base_prompt)
        # Store it in session state for future use
        st.session_state["current_prompt"] = group_prompt
        return group_prompt

    # Fall back to default prompt
    return DEFAULT_PROMPT


def set_current_prompt(prompt: str) -> None:
    """Set the current prompt in session state."""
    st.session_state["current_prompt"] = prompt


def reset_prompt_to_default() -> None:
    """Reset the prompt in session state to the default prompt."""
    st.session_state["current_prompt"] = DEFAULT_PROMPT


def prompt_customization_ui(
    show_preview: bool = True,
    button_label: str | None = "Save as Current Prompt",
    update_session: bool = True,
    state_key: str = "custom_dimensions",
) -> str:
    """Display the prompt customization UI in Streamlit."""
    t = get_translator(st.session_state.get("language", "en"))
    st.header(t("ui_text.prompt_customization_header"))

    # Initialize session state for dimensions using YAML defaults
    if state_key not in st.session_state:
        st.session_state[state_key] = get_default_dimensions()

    st.markdown(t("ui_text.define_dimensions_header"))
    dims = st.session_state[state_key]

    # Ensure all dims have a uuid
    for dim in dims:
        if "uuid" not in dim:
            dim["uuid"] = str(uuid.uuid4())

    with st.form("dimensions_form"):
        cols = st.columns([2, 4, 1, 1, 1])
        with cols[0]:
            st.markdown("**Dimension Name**")
        with cols[1]:
            st.markdown("**Definition/Explanation**")
        with cols[2]:
            st.markdown("**Lowest Score**")
        with cols[3]:
            st.markdown("**Highest Score**")
        with cols[4]:
            st.markdown("")

        remove_idx = None
        invalid_range = False
        for i, dim in enumerate(dims):
            c1, c2, c3, c4, c5 = st.columns([2, 4, 1, 1, 1])
            dim["name"] = c1.text_input(
                "Dimension Name",
                value=dim.get("name", ""),
                key=f"{state_key}_dim_name_{dim['uuid']}",
                label_visibility="collapsed",
            )
            dim["definition"] = c2.text_input(
                "Definition",
                value=dim.get("definition", ""),
                key=f"{state_key}_dim_def_{dim['uuid']}",
                label_visibility="collapsed",
            )
            min_val = int(dim.get("min", "0"))
            max_val = int(dim.get("max", "10"))
            min_input = c3.number_input(
                "Lowest Score",
                min_value=-1000,
                max_value=1000,
                value=min_val,
                step=1,
                key=f"{state_key}_dim_min_{dim['uuid']}",
                label_visibility="collapsed",
            )
            max_input = c4.number_input(
                "Highest Score",
                min_value=-1000,
                max_value=1000,
                value=max_val,
                step=1,
                key=f"{state_key}_dim_max_{dim['uuid']}",
                label_visibility="collapsed",
            )
            dim["min"] = str(min_input)
            dim["max"] = str(max_input)
            if max_input <= min_input:
                invalid_range = True
                c4.warning("Highest Score must be greater than Lowest Score")
            # Use form_submit_button for remove (no key param allowed)
            if c5.form_submit_button(f"Remove {dim['name'] or i}"):
                remove_idx = i
        if remove_idx is not None:
            dims.pop(remove_idx)

        add_clicked = st.form_submit_button("Add Dimension")
        main_clicked = False
        if button_label:
            main_clicked = st.form_submit_button(button_label, disabled=invalid_range)

        # Generate prompt from dimensions using YAML defaults
        prompt_lines = []
        
        # Use system role from YAML config
        system_role_lines = DEFAULT_SYSTEM_ROLE.split('\n')
        prompt_lines.extend(system_role_lines)
        prompt_lines.append("")
        
        prompt_lines.append("Please analyze the following narrative and provide scores for these dimensions as specified:")
        prompt_lines.append("")
        
        for idx, dim in enumerate(dims, 1):
            prompt_lines.append(
                f"{idx}. **{dim['name']}**: {dim['definition']} (Score range: {dim['min']}-{dim['max']})"
            )
        
        # Use base prompt from YAML config
        prompt_lines.append("")
        base_prompt_lines = DEFAULT_BASE_PROMPT.split('\n')
        prompt_lines.extend(base_prompt_lines)
        prompt_lines.append("")
        prompt_lines.append("Please respond in JSON format with the following structure:")
        prompt_lines.append("{{")
        for dim in dims:
            field_name = dim["name"].lower().replace(" ", "_")
            prompt_lines.append(f'    "{field_name}": <score>,')
            if "severity" in field_name.lower() or "disability" in field_name.lower():
                prompt_lines.append(
                    f'    "{field_name}_explanation": "<explanation in English for the {dim["name"].lower()}>",'
                )
        prompt_lines.append('    "reasoning": "<brief explanation of your overall scoring>"')
        prompt_lines.append("}}")
        prompt_lines.append("")
        prompt_lines.append("Patient narrative:\n{narrative}")
        generated_prompt = "\n".join(prompt_lines)

        if show_preview:
            st.markdown(t("ui_text.prompt_preview_header"))
            st.code(generated_prompt, language="markdown")

        if add_clicked:
            timestamp = int(datetime.now().timestamp() * 1000000)
            new_uuid = f"{timestamp}_new_{str(uuid.uuid4())}"
            dims.append({"name": "", "definition": "", "min": "0", "max": "10", "uuid": new_uuid})
            st.session_state[state_key] = dims
            # Let Streamlit's natural rerun handle the update

        if main_clicked:
            if update_session:
                st.session_state["current_prompt"] = generated_prompt
            st.success(
                t("ui_text.prompt_saved_session_success") if update_session else t("ui_text.dimensions_updated_success")
            )

    return generated_prompt
