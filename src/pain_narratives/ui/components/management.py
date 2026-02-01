"""
Management UI component for Evaluation groups and user administration.
"""

from typing import Any, Dict

import pandas as pd
import streamlit as st
from sqlmodel import select

from pain_narratives.core.database import DatabaseManager
from pain_narratives.core.questionnaire_prompts import (
    DEFAULT_QUESTIONNAIRE_PROMPTS,
    get_questionnaire_prompts_for_group,
    initialize_default_prompts_for_group,
    update_questionnaire_prompt,
)
from pain_narratives.db.models_sqlmodel import ExperimentGroup, User
from pain_narratives.ui.utils import get_translator

from .prompt_manager import (
    DEFAULT_BASE_PROMPT,
    DEFAULT_SYSTEM_ROLE,
    dimensions_editor_no_form,
    generate_prompt_from_dimensions,
)


def _display_experiment_group_details(
    db_manager: DatabaseManager, group: ExperimentGroup, is_admin: bool = False
) -> None:
    """Display Evaluation group details in a consolidated, visually appealing format."""
    t = get_translator(st.session_state.language)

    # Main header with group name and ID
    if not is_admin:  # Only show header for non-admin (admin already shows it)
        st.markdown(f"**🧪 {group.description or 'Unnamed Group'}** (ID: {group.experiments_group_id})")

    # Create a clean card-like layout
    with st.container():
        # Basic information section
        st.markdown(f"### {t('management.basic_information')}")

        info_col1, info_col2, info_col3 = st.columns(3)

        with info_col1:
            st.metric(t("management.group_id"), group.experiments_group_id)
            status = t("management.status_concluded") if group.concluded else t("management.status_active")
            st.write(f"**Status:** {status}")

        with info_col2:
            st.write(f"**{t('management.created_label')}:** {group.created.strftime('%Y-%m-%d %H:%M:%S')}")
            # Get owner information
            with db_manager.get_session() as session:
                owner = session.exec(select(User).where(User.id == group.owner_id)).first()
                st.write(f"**{t('management.owner_label')}:** {owner.username if owner else 'Unknown'}")

        with info_col3:
            st.write("**Description:**")
            st.write(group.description or t("management.no_description"))

        st.divider()

        # AI Configuration section
        st.markdown(f"### {t('management.ai_configuration')}")

        config_col1, config_col2 = st.columns(2)

        with config_col1:
            st.markdown(f"**{t('management.system_role_content')}:**")
            if group.system_role:
                if is_admin:
                    # For admin, use expanders since they're not nested
                    with st.expander(t("management.view_system_role"), expanded=True):
                        st.text_area(
                            "",
                            value=group.system_role,
                            height=120,
                            disabled=True,
                            key=f"sys_role_{group.experiments_group_id}",
                        )
                else:
                    # For regular users, display directly to avoid nested expanders
                    st.text_area(
                        t("management.system_role_content"),
                        value=group.system_role,
                        height=120,
                        disabled=True,
                        key=f"sys_role_{group.experiments_group_id}",
                    )
            else:
                st.write(t("management.no_system_role"))

        with config_col2:
            st.markdown(f"**{t('management.base_prompt_content')}:**")
            if group.base_prompt:
                if is_admin:
                    # For admin, use expanders since they're not nested
                    with st.expander(t("management.view_base_prompt"), expanded=True):
                        st.text_area(
                            "",
                            value=group.base_prompt,
                            height=120,
                            disabled=True,
                            key=f"base_prompt_{group.experiments_group_id}",
                        )
                else:
                    # For regular users, display directly to avoid nested expanders
                    st.text_area(
                        t("management.base_prompt_content"),
                        value=group.base_prompt,
                        height=120,
                        disabled=True,
                        key=f"base_prompt_{group.experiments_group_id}",
                    )
            else:
                st.write(t("management.no_base_prompt"))

        st.divider()

        # Evaluation dimensions section
        st.markdown(f"### {t('management.evaluation_dimensions')}")

        if group.dimensions:
            # Display dimensions in a more structured way
            if is_admin:
                # For admin, use expanders since they're not nested
                for i, dim in enumerate(group.dimensions, 1):
                    with st.expander(f"📏 Dimension {i}: {dim.get('name', 'Unnamed')}", expanded=True):
                        dim_col1, dim_col2 = st.columns([2, 1])
                        with dim_col1:
                            st.write("**Definition:**")
                            st.write(dim.get("definition", "No definition provided"))
                        with dim_col2:
                            st.metric("Score Range", f"{dim.get('min', 0)} - {dim.get('max', 10)}")
            else:
                # For regular users, display directly to avoid nested expanders
                for i, dim in enumerate(group.dimensions, 1):
                    st.markdown(f"**📏 Dimension {i}: {dim.get('name', 'Unnamed')}**")
                    dim_col1, dim_col2 = st.columns([2, 1])
                    with dim_col1:
                        st.write("**Definition:**")
                        st.write(dim.get("definition", "No definition provided"))
                    with dim_col2:
                        st.metric("Score Range", f"{dim.get('min', 0)} - {dim.get('max', 10)}")
                    if i < len(group.dimensions):  # Add spacing between dimensions except for the last one
                        st.markdown("---")
        else:
            st.write(t("management.no_dimensions"))

        st.divider()

        # Generated prompt section
        st.markdown(f"### {t('management.generated_prompt')}")

        # Generate the prompt for this group
        if group.dimensions:
            group_prompt = generate_prompt_from_dimensions(group.dimensions, group.system_role, group.base_prompt)
        else:
            # Use default prompt if no dimensions
            from .prompt_manager import DEFAULT_PROMPT

            group_prompt = DEFAULT_PROMPT

        # Show prompt preview with expansion option
        preview_length = 300
        if len(group_prompt) > preview_length:
            st.text_area(
                "Prompt Preview",
                value=group_prompt[:preview_length] + "...",
                height=100,
                disabled=True,
                key=f"prompt_preview_{group.experiments_group_id}",
            )

            # Use a button instead of checkbox for cleaner UI
            if st.button(
                t("ui_text.show_complete_prompt_button"), key=f"show_full_prompt_{group.experiments_group_id}"
            ):
                st.text_area(
                    "Complete Generated Prompt",
                    value=group_prompt,
                    height=400,
                    disabled=True,
                    key=f"full_prompt_{group.experiments_group_id}",
                )
        else:
            st.text_area(
                "Generated Prompt",
                value=group_prompt,
                height=200,
                disabled=True,
                key=f"prompt_display_{group.experiments_group_id}",
            )


def experiment_group_management_ui(db_manager: DatabaseManager, user_info: Dict[str, Any]) -> None:
    """Display Evaluation group management interface."""
    t = get_translator(st.session_state.language)
    st.header(t("management.experiment_group_management"))

    user_id = user_info["id"]
    is_admin = user_info["is_admin"]

    # Get user's Evaluation groups or all groups if admin
    with db_manager.get_session() as session:
        if is_admin:
            groups = list(session.exec(select(ExperimentGroup)).all())
            st.info(t("ui_text.admin_see_all_groups_info"))
        else:
            # Get groups where user is owner OR assigned to the group
            from pain_narratives.db.models_sqlmodel import ExperimentGroupUser

            # First, get groups where user is the owner
            owned_groups = session.exec(select(ExperimentGroup).where(ExperimentGroup.owner_id == user_id)).all()

            # Then, get groups where user is assigned via ExperimentGroupUser table
            assigned_groups = session.exec(
                select(ExperimentGroup).join(ExperimentGroupUser).where(ExperimentGroupUser.user_id == user_id)
            ).all()

            # Combine and deduplicate groups by ID
            all_groups = list(owned_groups) + list(assigned_groups)
            seen_ids = set()
            groups = []
            for group in all_groups:
                if group.experiments_group_id not in seen_ids:
                    groups.append(group)
                    seen_ids.add(group.experiments_group_id)

    # Display existing groups
    if groups:
        if is_admin:
            selected_id = st.session_state.get("selected_experiment_group_id")
            selected_group = next((g for g in groups if g.experiments_group_id == selected_id), None)
            if selected_group:
                _display_experiment_group_details(db_manager, selected_group, is_admin=True)
            else:
                st.info(t("management.select_group_info"))
        else:
            # For regular users, also use the same selection logic as admin
            selected_id = st.session_state.get("selected_experiment_group_id")
            selected_group = next((g for g in groups if g.experiments_group_id == selected_id), None)
            if selected_group:
                _display_experiment_group_details(db_manager, selected_group, is_admin=False)
            else:
                st.info(t("management.select_group_info"))
    else:
        if is_admin:
            st.info(t("management.no_groups_admin"))
        else:
            st.info(t("management.no_groups_user"))

    if is_admin:
        # Create new Evaluation group section
        st.subheader(t("management.create_new_group"))

        st.info(t("management.create_tip"))

        with st.expander(t("management.about_templates"), expanded=False):
            st.markdown(t("management.templates_description"))

        st.info(t("management.required_fields"))

        t = get_translator(st.session_state.language)

        description = st.text_input(
            t("management.description_label"),
            placeholder=t("ui_text.study_description_placeholder"),
            help=t("management.description_help"),
        )

        use_defaults = st.checkbox(
            t("ui_text.use_default_templates_label"),
            value=True,
            help=t("ui_text.expert_prompts_help"),
        )

        system_role = st.text_area(
            t("management.system_role_label"),
            value=DEFAULT_SYSTEM_ROLE if use_defaults else "",
            placeholder=t("ui_text.system_role_placeholder"),
            help=t("ui_text.ai_role_help"),
            height=100,
        )

        base_prompt = st.text_area(
            t("management.base_prompt_label"),
            value=DEFAULT_BASE_PROMPT if use_defaults else "",
            placeholder=t("ui_text.base_prompt_placeholder"),
            help=t("ui_text.prompt_template_help"),
            height=150,
        )

        # Dimensions editor
        dims, invalid_range, invalid_fields = dimensions_editor_no_form(state_key="new_group_dimensions")

        # Show prompt preview using the returned dims directly
        st.markdown(t("ui_text.generated_prompt_preview_header"))

        prompt_content_hash = hash(
            str([(d.get("name", ""), d.get("definition", ""), d.get("min", ""), d.get("max", "")) for d in dims])
            + (system_role or "")
            + (base_prompt or "")
        )

        full_prompt = generate_prompt_from_dimensions(dims, system_role, base_prompt)

        st.text_area(
            t("management.generated_prompt"),
            value=full_prompt,
            height=300,
            disabled=False,
            key=f"prompt_display_{prompt_content_hash}",
        )

        if st.checkbox(t("ui_text.show_debug_info_label"), key="debug_dims"):
            st.json(
                {
                    f"Dimension {i+1}": {
                        "name": d.get("name", ""),
                        "min": d.get("min", ""),
                        "max": d.get("max", ""),
                    }
                    for i, d in enumerate(dims)
                }
            )

        with db_manager.get_session() as session:
            all_users = list(session.exec(select(User)).all())
        user_map = {u.username: u.id for u in all_users if not u.is_admin or u.id == user_id}
        assign_to = st.multiselect(t("ui_text.grant_access_users_label"), options=list(user_map.keys()))

        has_errors = invalid_range or invalid_fields
        submit_button = st.button(t("management.create_group_button"), disabled=has_errors)

        if submit_button:
            # Validation
            validation_errors = []

            if not description.strip():
                validation_errors.append("Description is required")

            # Use the dims returned from dimensions_editor_no_form instead of re-fetching from session state
            # This ensures we're validating against the most current state
            current_dims = dims  # dims is already returned from dimensions_editor_no_form above
            for i, dim in enumerate(current_dims):
                if not dim.get("name", "").strip():
                    validation_errors.append(f"Dimension {i+1} name is required")
                if not dim.get("definition", "").strip():
                    validation_errors.append(f"Dimension {i+1} definition is required")
                try:
                    if int(dim.get("max", "0")) <= int(dim.get("min", "0")):
                        validation_errors.append(f"Dimension {i+1} highest score must be greater than lowest score")
                except ValueError:
                    validation_errors.append(f"Dimension {i+1} scores must be numeric")

            if validation_errors:
                st.error(t("ui_text.fix_issues_error"))
                for error in validation_errors:
                    st.write(f"• {error}")
            else:
                try:
                    # Use current_dims (the validated dimensions) instead of re-fetching from session state
                    group = db_manager.create_experiment_group(
                        owner_id=user_id,
                        description=description.strip(),
                        system_role=system_role.strip() if system_role.strip() else None,
                        base_prompt=base_prompt.strip() if base_prompt.strip() else None,
                        dimensions=current_dims,
                    )

                    # Assign group to selected users
                    if group.experiments_group_id and assign_to:
                        for uname in assign_to:
                            user_id_to_assign = user_map.get(uname)
                            if user_id_to_assign:
                                db_manager.assign_group_to_user(group.experiments_group_id, user_id_to_assign)

                    st.success(f"✅ Evaluation group created successfully! ID: {group.experiments_group_id}")

                    # Clear cached Evaluation groups in session state
                    keys_to_remove = [
                        key
                        for key in st.session_state.keys()
                        if isinstance(key, str) and key.startswith("experiment_groups_")
                    ]
                    for key in keys_to_remove:
                        del st.session_state[key]

                    # Note: Cache clearing is sufficient, no need to rerun the entire page
                except (ValueError, RuntimeError, KeyError) as e:
                    st.error(f"❌ Failed to create Evaluation group: {str(e)}")
                except Exception as e:  # pylint: disable=broad-except
                    st.error(f"❌ Unexpected error creating Evaluation group: {str(e)}")


def user_administration_ui(db_manager: DatabaseManager, user_info: Dict[str, Any]) -> None:
    """Display user administration interface (admin only)."""
    t = get_translator(st.session_state.get("language", "en"))
    if not user_info["is_admin"]:
        st.warning(t("ui_text.admin_privileges_required_warning"))
        return

    st.header(t("ui_text.user_administration_header"))

    # Create new user section
    with st.expander(t("ui_text.create_new_user_header"), expanded=False):
        with st.form("create_user_form"):
            col1, col2, col3 = st.columns([2, 2, 1])

            with col1:
                new_username = st.text_input(t("ui_text.username_input_label"), key="new_user_username")

            with col2:
                new_password = st.text_input(
                    t("ui_text.password_input_label"), type="password", key="new_user_password"
                )

            with col3:
                is_admin = st.checkbox(t("ui_text.make_admin_checkbox"), key="new_user_admin")

            submit_button = st.form_submit_button(t("ui_text.create_user_button"))

            if submit_button:
                # Validate inputs
                if not new_username:
                    st.error(t("ui_text.username_required_error"))
                elif not new_password:
                    st.error(t("ui_text.password_required_error"))
                elif len(new_password) < 3:
                    st.error(t("ui_text.password_min_length_error"))
                else:
                    try:
                        db_manager.create_user(new_username, new_password, is_admin)
                        st.success(t("ui_text.user_created_success").format(username=new_username))
                        st.rerun()
                    except Exception as e:
                        st.error(t("ui_text.user_creation_failed").format(error=str(e)))

    # Get all users
    with db_manager.get_session() as session:
        users = list(session.exec(select(User)).all())

    if not users:
        st.info(t("ui_text.no_users_found_info"))
        return

    # Display users table
    st.subheader(t("ui_text.all_users_subheader"))

    user_data = []
    for user in users:
        # Get Evaluation group IDs for each user
        group_ids = db_manager.get_user_experiment_groups(user.id)
        group_ids_str = ", ".join(map(str, group_ids)) if group_ids else "-"

        user_data.append(
            {
                "ID": user.id,
                t("ui_text.username_label").replace("**", "").replace(":", ""): user.username,
                "Admin": "✅ Yes" if user.is_admin else "❌ No",
                t("ui_text.experiment_groups_column"): group_ids_str,
                "_user_obj": user,  # Hidden column for internal use
            }
        )

    # Create DataFrame for better display
    df = pd.DataFrame(user_data)
    display_df = df.drop(columns=["_user_obj"])

    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # User actions section
    st.subheader(t("ui_text.user_actions_header"))

    # Select user to manage
    user_options = {f"{u.username} (ID: {u.id})": u for u in users}
    selected_user_key = st.selectbox(
        t("ui_text.edit_user_header").format(username=""),
        options=list(user_options.keys()),
        key="selected_user_for_action",
    )

    if selected_user_key:
        selected_user = user_options[selected_user_key]

        col1, col2, col3 = st.columns(3)

        # Toggle admin status
        with col1:
            current_admin_status = "Admin" if selected_user.is_admin else "Regular User"
            new_admin_status = "Regular User" if selected_user.is_admin else "Admin"

            if st.button(
                f"{t('ui_text.toggle_admin_button')} ({current_admin_status} → {new_admin_status})",
                key="toggle_admin_btn",
                use_container_width=True,
            ):
                try:
                    db_manager.update_user_admin_status(selected_user.id, not selected_user.is_admin)
                    st.success(t("ui_text.admin_status_updated").format(username=selected_user.username))
                    st.rerun()
                except Exception as e:
                    st.error(t("ui_text.admin_update_failed").format(error=str(e)))

        # Reset password
        with col2:
            with st.popover(t("ui_text.reset_password_button"), use_container_width=True):
                new_pwd = st.text_input(t("ui_text.new_password_label"), type="password", key="reset_pwd_input")
                if st.button(t("ui_text.reset_password_button"), key="confirm_reset_pwd"):
                    if not new_pwd:
                        st.error(t("ui_text.password_required_error"))
                    elif len(new_pwd) < 3:
                        st.error(t("ui_text.password_min_length_error"))
                    else:
                        try:
                            db_manager.reset_user_password(selected_user.id, new_pwd)
                            st.success(t("ui_text.password_reset_success").format(username=selected_user.username))
                            st.rerun()
                        except Exception as e:
                            st.error(t("ui_text.password_reset_failed").format(error=str(e)))

        # Delete user
        with col3:
            if selected_user.id == user_info["id"]:
                st.button(
                    t("ui_text.delete_user_button"),
                    disabled=True,
                    key="delete_user_disabled",
                    use_container_width=True,
                    help=t("ui_text.cannot_delete_self"),
                )
            else:
                with st.popover(t("ui_text.delete_user_button"), use_container_width=True):
                    st.warning(t("ui_text.confirm_delete_user").format(username=selected_user.username))
                    if st.button("⚠️ Confirm Delete", key="confirm_delete_user", type="primary"):
                        try:
                            db_manager.delete_user(selected_user.id)
                            st.success(t("ui_text.user_deleted_success").format(username=selected_user.username))
                            st.rerun()
                        except Exception as e:
                            st.error(t("ui_text.user_delete_failed").format(error=str(e)))

    # Edit Experiment Groups section
    st.divider()
    st.subheader(t("ui_text.edit_experiment_groups_header"))
    
    if selected_user_key:
        selected_user = user_options[selected_user_key]
        
        # Get all available experiment groups
        all_groups = db_manager.get_all_experiment_groups()
        
        if not all_groups:
            st.warning(t("ui_text.no_groups_available"))
        else:
            # Display available groups for reference
            with st.expander(t("ui_text.available_groups_label"), expanded=False):
                group_info = []
                for group in all_groups:
                    group_info.append({
                        "ID": group.experiments_group_id,
                        "Description": group.description or "No description",
                        "Owner": group.owner_id,
                        "Status": "✅ Concluded" if group.concluded else "🔄 Active"
                    })
                st.dataframe(pd.DataFrame(group_info), use_container_width=True, hide_index=True)
            
            # Get current groups for the user
            current_groups = db_manager.get_user_experiment_groups(selected_user.id)
            current_groups_str = ", ".join(map(str, current_groups)) if current_groups else "None"
            
            st.info(f"**{t('ui_text.current_groups_label')}:** {current_groups_str}")
            
            # Input for new group IDs
            with st.form("edit_groups_form"):
                new_groups_str = st.text_input(
                    t("ui_text.enter_group_ids_label"),
                    value=", ".join(map(str, current_groups)) if current_groups else "",
                    help=t("ui_text.enter_group_ids_help")
                )
                
                col1, col2 = st.columns([1, 3])
                with col1:
                    submit_groups = st.form_submit_button(t("ui_text.save_groups_button"), use_container_width=True)
                
                if submit_groups:
                    try:
                        # Parse the input
                        if not new_groups_str.strip():
                            # Empty input means remove all groups
                            new_group_ids = []
                        else:
                            # Parse comma-separated integers
                            new_group_ids = []
                            for part in new_groups_str.split(","):
                                part = part.strip()
                                if part:
                                    try:
                                        group_id = int(part)
                                        new_group_ids.append(group_id)
                                    except ValueError:
                                        st.error(t("ui_text.invalid_group_ids_error"))
                                        st.stop()
                        
                        # Validate and update
                        db_manager.update_user_experiment_groups(selected_user.id, new_group_ids)
                        st.success(t("ui_text.groups_updated_success").format(username=selected_user.username))
                        st.rerun()
                        
                    except ValueError as e:
                        # Handle group not found error
                        error_msg = str(e)
                        if "does not exist" in error_msg:
                            # Extract group ID from error message
                            import re
                            match = re.search(r'ID (\d+)', error_msg)
                            if match:
                                group_id = match.group(1)
                                st.error(t("ui_text.group_not_found_error").format(group_id=group_id))
                            else:
                                st.error(t("ui_text.groups_update_failed").format(error=error_msg))
                        else:
                            st.error(t("ui_text.groups_update_failed").format(error=error_msg))
                    except Exception as e:
                        st.error(t("ui_text.groups_update_failed").format(error=str(e)))

    # Quick actions section (command line reference)
    st.divider()
    st.subheader(t("ui_text.quick_actions_header"))
    st.info(t("ui_text.command_line_scripts_info"))

    col1, col2 = st.columns(2)

    with col1:
        st.write("**User Management Scripts**")
        st.code(
            """
# List all users
uv run python scripts/manage_users.py list

# Show user details
uv run python scripts/manage_users.py show username

# Grant admin privileges
uv run python scripts/manage_users.py make-admin username

# Reset password
uv run python scripts/manage_users.py reset-password username newpass
        """
        )

    with col2:
        st.write("**User Registration Scripts**")
        st.code(
            """
# Interactive registration
uv run python scripts/register_user.py

# Batch registration
uv run python scripts/register_user_batch.py username password

# Admin user creation
uv run python scripts/register_user_batch.py admin_user pass --admin

# Import from CSV
uv run python scripts/manage_users.py import-csv users.csv
        """
        )

    st.info(t("ui_text.command_line_scripts_info"))


def management_tab_ui(db_manager: DatabaseManager, user_info: Dict[str, Any]) -> None:
    """Main management tab interface."""
    t = get_translator(st.session_state.language)
    st.header(t("management.header"))
    st.write(t("management.description"))

    # Sub-tabs for different management areas
    if user_info["is_admin"]:
        mgmt_tab1, mgmt_tab2, mgmt_tab3, mgmt_tab4 = st.tabs(
            [
                t("management.evaluation_groups_tab"),
                t("management.user_administration_tab"),
                t("management.questionnaire_prompts_tab"),
                t("management.system_info_tab"),
            ]
        )
    else:
        mgmt_tab1, mgmt_tab4 = st.tabs([t("management.evaluation_groups_tab"), t("management.system_info_tab")])
        mgmt_tab2 = None
        mgmt_tab3 = None

    with mgmt_tab1:
        experiment_group_management_ui(db_manager, user_info)

    if mgmt_tab2 and user_info["is_admin"]:
        with mgmt_tab2:
            user_administration_ui(db_manager, user_info)

    if mgmt_tab3 and user_info["is_admin"]:
        with mgmt_tab3:
            questionnaire_prompts_management_ui(db_manager, user_info)

    with mgmt_tab4:
        system_info_ui(db_manager, user_info)


def system_info_ui(db_manager: DatabaseManager, user_info: Dict[str, Any]) -> None:
    """Display system information."""
    t = get_translator(st.session_state.language)
    st.header(t("management.system_info_header"))

    # Database statistics
    with db_manager.get_session() as session:
        user_count = len(list(session.exec(select(User)).all()))
        group_count = len(list(session.exec(select(ExperimentGroup)).all()))

        if user_info["is_admin"]:
            user_groups = group_count
        else:
            user_groups = len(
                list(session.exec(select(ExperimentGroup).where(ExperimentGroup.owner_id == user_info["id"])).all())
            )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(t("management.total_users_metric"), user_count)

    with col2:
        st.metric(t("management.total_groups_metric"), group_count)

    with col3:
        if user_info["is_admin"]:
            st.metric(t("ui_text.your_access_metric"), t("ui_text.all_groups_admin"))
        else:
            st.metric(t("ui_text.your_groups_metric"), user_groups)

    # User info
    st.subheader(t("ui_text.your_account_header"))

    col1, col2 = st.columns(2)

    with col1:
        st.write(t("ui_text.username_label"), user_info["username"])
        st.write(t("ui_text.user_id_label"), user_info["id"])
        st.write(
            t("ui_text.account_type_label"),
            t("ui_text.admin_type") if user_info["is_admin"] else t("ui_text.regular_user_type"),
        )

    with col2:
        st.write(t("ui_text.permissions_label"))
        if user_info["is_admin"]:
            st.write(t("ui_text.access_all_groups_perm"))
            st.write(t("ui_text.manage_users_perm"))
            st.write(t("ui_text.system_admin_perm"))
        else:
            st.write(t("ui_text.create_groups_perm"))
            st.write(t("ui_text.run_evaluations_perm"))
            st.write(t("ui_text.manage_data_perm"))

    # Database connection info
    st.subheader(t("ui_text.database_connection_header"))
    st.write(t("ui_text.schema_label"), db_manager.schema)
    st.write(t("ui_text.status_label"), t("ui_text.connected_status"))

    # Documentation links
    st.subheader(t("ui_text.documentation_header"))
    st.write("- [User Management Guide](scripts/USER_MANAGEMENT.md)")
    st.write("- [Database Models](src/pain_narratives/db/models_sqlmodel.py)")
    st.write("- [Configuration Guide](README.md#configuration)")


def questionnaire_prompts_management_ui(db_manager: DatabaseManager, user_info: Dict[str, Any]) -> None:
    """UI for managing questionnaire prompts for experiment groups."""
    t = get_translator(st.session_state.language)
    st.header(t("management.questionnaire_prompts_header"))
    st.write(t("management.questionnaire_prompts_description"))

    # Special note about not editing inside brackets
    lang = st.session_state.get("language", "en")
    if lang == "es":
        st.info("⚠️ No edite nada que esté dentro de llaves '{}' (brackets).", icon="⚠️")
    else:
        st.info("⚠️ Do not edit anything that is inside brackets '{}' (curly braces).", icon="⚠️")

    # Use the Evaluation group selected in the sidebar (single source of truth)
    selected_group_id = st.session_state.get("selected_experiment_group_id")

    # If no group selected in sidebar, prompt the user and exit
    if not selected_group_id:
        st.info(t("management.select_group_info"))
        return

    # Validate group exists (in case session state is stale)
    with db_manager.get_session() as session:
        group_exists = session.exec(
            select(ExperimentGroup).where(ExperimentGroup.experiments_group_id == selected_group_id)
        ).first()

    if not group_exists:
        st.warning(t("management.no_experiment_groups"))
        return

    # Initialize prompts button
    if st.button(t("management.initialize_default_prompts")):
        if initialize_default_prompts_for_group(db_manager, selected_group_id):
            st.success(t("management.prompts_initialized"))
            st.rerun()
        else:
            st.error(t("management.prompts_initialization_failed"))

    # Get existing prompts for the selected group
    existing_prompts = get_questionnaire_prompts_for_group(db_manager, selected_group_id)

    st.subheader(t("management.current_prompts"))

    # Display and edit prompts for each questionnaire type
    questionnaire_types = ["PCS", "BPI-IS", "TSK-11SV"]

    for q_type in questionnaire_types:
        with st.expander(f"{q_type} {t('management.questionnaire_prompts')}"):
            # Get current prompts or defaults
            current_system_role = existing_prompts.get(q_type, {}).get(
                "system_role", DEFAULT_QUESTIONNAIRE_PROMPTS[q_type]["system_role"]
            )
            current_instructions = existing_prompts.get(q_type, {}).get(
                "instructions", DEFAULT_QUESTIONNAIRE_PROMPTS[q_type]["instructions"]
            )  # System role editor
            st.write(f"**{t('management.system_role')}:**")
            new_system_role = st.text_area(
                f"{q_type} System Role",
                value=current_system_role,
                height=100,
                key=f"system_role_{q_type}_{selected_group_id}",
                label_visibility="collapsed",
            )

            # Instructions editor
            st.write(f"**{t('management.instructions')}:**")
            new_instructions = st.text_area(
                f"{q_type} Instructions",
                value=current_instructions,
                height=200,
                key=f"instructions_{q_type}_{selected_group_id}",
                label_visibility="collapsed",
            )

            # Save button
            if st.button(f"{t('management.save_prompts')} - {q_type}", key=f"save_{q_type}_{selected_group_id}"):
                if update_questionnaire_prompt(
                    db_manager, selected_group_id, q_type, new_system_role, new_instructions
                ):
                    st.success(f"{q_type} {t('management.prompts_updated')}")
                    st.rerun()
                else:
                    st.error(f"{q_type} {t('management.prompts_update_failed')}")

            # Reset to default button
            if st.button(f"{t('management.reset_to_default')} - {q_type}", key=f"reset_{q_type}_{selected_group_id}"):
                default_system_role = DEFAULT_QUESTIONNAIRE_PROMPTS[q_type]["system_role"]
                default_instructions = DEFAULT_QUESTIONNAIRE_PROMPTS[q_type]["instructions"]

                if update_questionnaire_prompt(
                    db_manager, selected_group_id, q_type, default_system_role, default_instructions
                ):
                    st.success(f"{q_type} {t('management.prompts_reset')}")
                    st.rerun()
                else:
                    st.error(f"{q_type} {t('management.prompts_reset_failed')}")
