"""
Streamlit application for AINarratives evaluation.

This application provides a comprehensive interface for evaluating pain
narratives using AI models with customizable prompts and batch processing
capabilities.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

import pandas as pd
import streamlit as st
from sqlmodel import select

from pain_narratives.core.database import DatabaseManager
from pain_narratives.core.openai_client import OpenAIClient

# Direct import for questionnaire prompts to avoid circular dependency
from pain_narratives.db.models_sqlmodel import QuestionnairePrompt
from pain_narratives.ui.components.assessment_feedback import render_assessment_feedback_form
from pain_narratives.ui.components.batch_processing import run_batch_evaluation
from pain_narratives.ui.components.evaluation_display import display_evaluation_details
from pain_narratives.ui.components.evaluation_logic import NarrativeEvaluator
from pain_narratives.ui.components.management import management_tab_ui
from pain_narratives.ui.components.prompt_manager import get_current_prompt
from pain_narratives.ui.components.questionnaire import (
    BPI_IS_INSTRUCTIONS,
    BPI_IS_QUESTIONS,
    BPI_IS_SYSTEM_ROLE,
    PCS_INSTRUCTIONS,
    PCS_QUESTIONS,
    PCS_SCORE_LABELS,
    PCS_SYSTEM_ROLE,
    TSK_11SV_INSTRUCTIONS,
    TSK_11SV_QUESTIONS,
    TSK_11SV_SCALE_LABELS,
    TSK_11SV_SYSTEM_ROLE,
    calculate_bpi_is_total_score,
    calculate_pcs_total_score,
    calculate_tsk_11sv_total_score,
    count_bpi_is_scores,
    count_scores,
    count_tsk_11sv_scores,
    display_score_distribution_chart,
    run_bpi_is_questionnaire,
    run_pcs_questionnaire,
    run_tsk_11sv_questionnaire,
)
from pain_narratives.ui.components.questionnaire_feedback import render_questionnaire_feedback_form
from pain_narratives.ui.utils.localization import get_translator

# Configure comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

# Enable detailed logging for key components
logger = logging.getLogger("pain_narratives")
logger.setLevel(logging.INFO)

# Enable translation service logging
translation_logger = logging.getLogger("pain_narratives.core.translation_service")
translation_logger.setLevel(logging.INFO)

# Enable OpenAI client logging for debugging
openai_logger = logging.getLogger("pain_narratives.core.openai_client")
openai_logger.setLevel(logging.INFO)

# Enable database logging
db_logger = logging.getLogger("pain_narratives.core.database")
db_logger.setLevel(logging.INFO)

# Custom CSS for better UI
CUSTOM_CSS = """
<style>
    .main {
        padding-top: 1rem;
    }
    .stAlert {
        margin-top: 1rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #e9ecef;
        margin: 0.5rem 0;
    }
    .evaluation-result {
        background-color: #e8f5e8;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #28a745;
        margin: 1rem 0;
    }
    .error-result {
        background-color: #f8e8e8;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #dc3545;
        margin: 1rem 0;
    }
</style>
"""


class PainNarrativesApp:
    """Main application class for AINarratives Evaluation."""

    def __init__(self) -> None:
        """Initialize the application."""
        self.setup_page_config()
        self.apply_custom_css()
        self.initialize_session_state()

    def setup_page_config(self) -> None:
        """Configure Streamlit page settings."""
        # Get translator for page config - using default language without caching
        # to avoid Streamlit caching conflicts during page setup
        try:
            language = st.session_state.get("language", "en")
        except Exception:
            language = "en"

        t = get_translator(language, use_cache=False)

        st.set_page_config(
            page_title=t("app.title"),
            page_icon="🏥",
            layout="wide",
            initial_sidebar_state="expanded",
        )

    def apply_custom_css(self) -> None:
        """Apply custom CSS styles."""
        st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    def initialize_session_state(self) -> None:
        """Initialize session state variables."""
        if "openai_client" not in st.session_state:
            st.session_state.openai_client = None

        if "db_manager" not in st.session_state:
            st.session_state.db_manager = None

        if "user" not in st.session_state:
            st.session_state.user = None

        if "is_admin" not in st.session_state:
            st.session_state.is_admin = False

        if "evaluation_history" not in st.session_state:
            st.session_state.evaluation_history = []

        if "current_prompt" not in st.session_state:
            st.session_state.current_prompt = None

        if "current_experiment_id" not in st.session_state:
            st.session_state.current_experiment_id = None

        if "current_narrative_text" not in st.session_state:
            st.session_state.current_narrative_text = (
                "I woke up everydays with pain in my arms and legs.\n"
                "Over the day, I find myself better, but I am constantly tired and sad"
            )

        if "narrative_input" not in st.session_state:
            st.session_state.narrative_input = st.session_state.current_narrative_text

        if "current_narrative_id" not in st.session_state:
            st.session_state.current_narrative_id = None

        if "language" not in st.session_state:
            # Check if user is logged in and has a preferred language
            user = st.session_state.get("user")
            if user is not None and isinstance(user, dict) and "preferred_language" in user:
                st.session_state.language = user["preferred_language"]
            else:
                st.session_state.language = "en"

    def setup_sidebar(self) -> Dict[str, Any]:
        """Setup the sidebar with configuration options."""
        # Store current language before getting translator
        current_language = st.session_state.get("language", "en")
        t = get_translator(current_language)

        # Language selector with change detection
        new_language = st.sidebar.selectbox(
            t("sidebar.language_select"),
            options=["en", "es"],
            index=["en", "es"].index(current_language),
            key="language_selector",
        )

        # Detect language change and trigger rerun
        if new_language != current_language:
            st.session_state.language = new_language

            # Save language preference to database if user is logged in
            if st.session_state.user is not None and st.session_state.db_manager is not None:
                try:
                    st.session_state.db_manager.update_user_language(st.session_state.user["id"], new_language)
                    logger.info(
                        f"Updated language preference for user {st.session_state.user['username']} to {new_language}"
                    )
                except Exception as e:
                    logger.error(f"Failed to update user language preference: {e}")

            # Clear both caches when language changes
            st.cache_data.clear()
            if hasattr(st.session_state, "current_localization_language"):
                del st.session_state.current_localization_language
            st.rerun()

        # Update session state
        st.session_state.language = new_language

        st.sidebar.title(t("sidebar.login_section"))

        if st.session_state.user is None:
            # Show login form
            with st.sidebar.form("login_form"):
                st.markdown(f"**{t('sidebar.username_help')}**")
                username = st.text_input(t("sidebar.username"), key="username")
                password = st.text_input(t("sidebar.password"), type="password", key="password")
                submit_button = st.form_submit_button(t("sidebar.login_button"))

            if submit_button:
                if not username or not password:
                    st.sidebar.error(
                        t("errors.api_key_required").replace("OpenAI API key", t("auth.username_password_required"))
                    )
                    return {}

                # Initialize database manager for authentication
                if st.session_state.db_manager is None:
                    try:
                        with st.sidebar:
                            with st.spinner(t("common.loading")):
                                st.session_state.db_manager = DatabaseManager()
                    except Exception as e:
                        st.sidebar.error(f"{t('errors.database_error')}: {e}")
                        logger.error(f"Database connection error: {e}")
                        return {}

                # Authenticate user
                try:
                    with st.sidebar:
                        with st.spinner(t("auth.authenticating")):
                            user = st.session_state.db_manager.authenticate_user(username, password)

                    if user:
                        st.session_state.user = user
                        st.session_state.is_admin = user["is_admin"]
                        # Load user's preferred language
                        if "preferred_language" in user:
                            st.session_state.language = user["preferred_language"]
                            # Clear caches to refresh with user's language
                            st.cache_data.clear()
                            if hasattr(st.session_state, "current_localization_language"):
                                del st.session_state.current_localization_language
                        st.sidebar.success(t("auth.welcome_user").format(username=user["username"]))
                        logger.info("User %s logged in successfully", username)
                        st.rerun()  # Refresh the page to show authenticated state
                    else:
                        st.sidebar.error(t("auth.invalid_credentials"))
                        logger.warning("Failed login attempt for username: %s", username)
                except Exception as e:
                    st.sidebar.error(t("auth.authentication_error").format(error=str(e)))
                    logger.error("Authentication error: %s", str(e))

            with st.sidebar.expander(t("auth.need_help")):
                st.markdown(t("auth.first_time_info"))
            return {}
        else:
            # Show user info and logout
            st.sidebar.success(f"👤 **{st.session_state.user['username']}**")
            if st.session_state.is_admin:
                st.sidebar.info(t("auth.admin_access"))
            else:
                st.sidebar.info(t("auth.user_access"))

            # User actions
            with st.sidebar:
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(t("sidebar.logout_button"), use_container_width=True):
                        # Clear all session state
                        for key in list(st.session_state.keys()):
                            del st.session_state[key]
                        logger.info(f"User {st.session_state.get('user', {}).get('username', 'unknown')} logged out")
                        st.rerun()
                with col2:
                    if st.button(t("sidebar.refresh_button"), use_container_width=True):
                        st.rerun()

        st.sidebar.title(t("sidebar.header"))

        # OpenAI Configuration
        st.sidebar.subheader(t("sidebar.model_selection"))
        api_key = st.sidebar.text_input(
            t("sidebar.openai_api_key"),
            type="password",
            help=t("sidebar.api_key_help"),
            key="api_key_input",
        )

        # Non-admin users: fixed model and temperature
        # Admins: full control
        if st.session_state.is_admin:
            model = st.sidebar.selectbox(t("sidebar.model_selection"), ["gpt-4o", "gpt-5-mini", "gpt-4-turbo"], index=1)
            temperature = st.sidebar.slider(
                t("sidebar.temperature"),
                min_value=0.0,
                max_value=1.5,
                value=1.0,
                step=0.1,
                help=t("sidebar.temperature_help"),
            )
        else:
            # Non-admin users get fixed model and temperature
            model = "gpt-5"
            temperature = 1.0
            st.sidebar.selectbox(
                t("sidebar.model_selection"),
                ["gpt-5"],
                index=0,
                disabled=True,
                help=t("sidebar.model_help"),
            )
            st.sidebar.slider(
                t("sidebar.temperature"),
                min_value=0.0,
                max_value=1.5,
                value=1.0,
                step=0.1,
                disabled=True,
                help=t("sidebar.temperature_help"),
            )

        # Evaluation group Selection (database is initialized automatically)
        st.sidebar.subheader(t("sidebar.evaluation_groups"))
        experiment_group_id = None

        if st.session_state.db_manager:
            # Cache Evaluation groups in session state for better performance
            cache_key = f"experiment_groups_{st.session_state.user['id']}_{st.session_state.is_admin}"

            if cache_key not in st.session_state:
                # Load Evaluation groups for the current user
                groups = st.session_state.db_manager.get_experiment_groups_for_user(
                    st.session_state.user["id"], st.session_state.is_admin
                )
                st.session_state[cache_key] = groups
            else:
                groups = st.session_state[cache_key]

            if groups:
                group_options = [
                    (g.experiments_group_id, f"{g.experiments_group_id} - {g.description}") for g in groups
                ]
                selected_group = st.sidebar.selectbox(
                    t("sidebar.select_group"),
                    options=group_options,
                    format_func=lambda x: x[1],
                    help=t("sidebar.select_group_help"),
                )
                experiment_group_id = selected_group[0]
                selected = next((g for g in groups if g.experiments_group_id == experiment_group_id), None)
                if selected:
                    # Store the selected Evaluation group ID in session state
                    st.session_state.selected_experiment_group_id = experiment_group_id
                    st.session_state.selected_group_system_role = selected.system_role
                    st.session_state.selected_group_base_prompt = selected.base_prompt

                    dims = selected.dimensions or []
                    # Ensure each dimension has a unique uuid
                    seen = set()
                    for dim in dims:
                        uid = dim.get("uuid")
                        if not uid or uid in seen:
                            uid = str(uuid.uuid4())
                            dim["uuid"] = uid
                        seen.add(uid)

                    st.session_state.selected_group_dimensions = dims
                    # Initialize dimensions from group when switching
                    st.session_state.custom_dimensions = list(st.session_state.selected_group_dimensions)
            else:
                st.sidebar.warning(t("sidebar.no_groups_warning"))
                st.sidebar.info(t("sidebar.create_group_info"))
                experiment_group_id = None
                # Clear selected Evaluation group from session state
                st.session_state.selected_experiment_group_id = None

            # Add a manual refresh button for Evaluation groups (as backup)
            if st.sidebar.button(t("sidebar.refresh_groups_button"), help=t("sidebar.refresh_groups_help")):
                # Clear the cache and reload
                if cache_key in st.session_state:
                    del st.session_state[cache_key]
                st.rerun()

            # Small helper info
            if groups:
                st.sidebar.caption(t("sidebar.groups_count").format(count=len(groups)))
        else:
            # Clear selected Evaluation group when no database connection
            st.session_state.selected_experiment_group_id = None

        # Automatically initialize connections if needed
        if st.session_state.openai_client is None:
            self.initialize_connections(api_key, True)

        return {
            "model": model,
            "temperature": temperature,
            "use_database": True,
            "experiment_group_id": experiment_group_id,
        }

    def initialize_connections(self, api_key: str, use_database: bool) -> None:
        """Initialize OpenAI and database connections."""
        t = get_translator(st.session_state.get("language", "en"))
        try:
            logger.info(
                "Initializing connections - API Key provided: %s, Use DB: %s",
                bool(api_key),
                use_database,
            )

            # Initialize OpenAI client
            if api_key:
                logger.info("Using provided API key")
                st.session_state.openai_client = OpenAIClient(api_key=api_key)
            else:
                logger.info("Using environment API key")
                st.session_state.openai_client = OpenAIClient()  # Initialize database if requested
            if use_database:
                logger.info("Initializing database connection")
                st.session_state.db_manager = DatabaseManager()
                logger.info(
                    "Database connection initialized: %s",
                    bool(st.session_state.db_manager),
                )

            st.sidebar.success(t("common.connections_initialized"))

        except Exception as e:
            logger.error("Connection initialization failed: %s", str(e), exc_info=True)
            st.sidebar.error(t("common.connection_failed").format(error=str(e)))

    def narrative_dimensions_tab(self) -> None:
        """Tab for editing the pain narrative and evaluation dimensions."""
        t = get_translator(st.session_state.language)
        st.header(t("narrative_dimensions.header"))

        if st.session_state.user is None:
            st.error(t("auth.login_required"))
            return

        is_admin = st.session_state.is_admin

        st.subheader(t("narrative_dimensions.narrative_input"))

        db_manager = st.session_state.db_manager
        user_id = st.session_state.user["id"] if st.session_state.user else None

        # Check if user has selected an Evaluation group
        experiment_group_id = st.session_state.get("selected_experiment_group_id")

        if not experiment_group_id:
            st.warning(t("narrative_dimensions.no_group_selected"))
            st.info(t("narrative_dimensions.get_started_info"))
            return

        # Show selected Evaluation group info
        st.success(t("narrative_dimensions.selected_group").format(group_id=experiment_group_id))

        # Load last narrative for the group if this is the first time loading this group
        if db_manager and st.session_state.get("last_loaded_group_id") != experiment_group_id:
            try:
                last_narr = db_manager.get_last_narrative_for_group(experiment_group_id)
                if last_narr and "narrative_input" not in st.session_state:
                    # Only set if narrative_input hasn't been initialized yet
                    st.session_state.narrative_input = last_narr.narrative or ""
                    st.session_state.current_narrative_text = st.session_state.narrative_input
                    st.session_state.current_narrative_id = last_narr.narrative_id
            except Exception as e:
                logger.error("Failed to load last narrative for group: %s", e)
            st.session_state.last_loaded_group_id = experiment_group_id

        new_narrative_option = t("narrative_dimensions.new_narrative")
        narrative_options = [new_narrative_option]
        narratives_map = {}
        if db_manager and user_id is not None:
            try:
                user_narratives = db_manager.get_narratives_by_owner(user_id)
                for n in user_narratives:
                    label = f"{n.narrative_id} - {str(n.narrative)[:40]}"
                    narrative_options.append(label)
                    narratives_map[label] = n
            except Exception as e:
                logger.error("Failed to load narratives: %s", e)

        selected_option = st.selectbox(
            t("narrative_dimensions.load_existing_narrative"),
            options=narrative_options,
        )

        if selected_option != new_narrative_option and selected_option in narratives_map:
            selected_narrative = narratives_map[selected_option]
            if st.session_state.get("current_narrative_id") != selected_narrative.narrative_id:
                st.session_state.current_narrative_id = selected_narrative.narrative_id
                st.session_state.narrative_input = selected_narrative.narrative or ""
                st.session_state.current_narrative_text = st.session_state.narrative_input

        uploaded_file = st.file_uploader(
            t("narrative_dimensions.upload_narrative_file"),
            type=["pdf", "docx", "txt"],
        )

        if uploaded_file is not None:
            try:
                from pain_narratives.utils import file_to_markdown

                uploaded_file.seek(0)
                markdown_text = file_to_markdown(uploaded_file, uploaded_file.name)
                st.session_state.narrative_input = markdown_text.strip()
                st.session_state.current_narrative_text = st.session_state.narrative_input
            except Exception as e:
                st.error(f"Failed to process file: {e}")

        # Preserve any edits the user makes to the narrative across reruns
        if st.session_state.get("narrative_input") != st.session_state.get("current_narrative_text"):
            st.session_state.current_narrative_text = st.session_state.narrative_input

        st.text_area(
            t("narrative_dimensions.enter_modify_narrative"),
            key="narrative_input",
            height=200,
        )
        st.session_state.current_narrative_text = st.session_state.narrative_input

        if st.button(t("narrative_dimensions.save_narrative_button"), type="primary"):
            if db_manager and user_id is not None:
                try:
                    narrative_id = db_manager.create_narrative(
                        {"narrative": st.session_state.narrative_input, "owner_id": user_id}
                    )
                    st.session_state.current_narrative_id = narrative_id
                    st.success(t("narrative_dimensions.narrative_saved").format(narrative_id=narrative_id))
                except Exception as e:
                    st.error(t("narrative_dimensions.failed_save_narrative").format(error=str(e)))

        if is_admin:
            st.info(t("narrative_dimensions.admin_mode_info"))
            st.markdown("---")

        # Show current dimensions from the Evaluation group
        current_dims = st.session_state.get("selected_group_dimensions", [])
        if not current_dims:
            # Initialize with default dimensions if none exist in the Evaluation group
            current_dims = [
                {
                    "name": "Severity Score",
                    "definition": "The perceived intensity of pain and overall suffering",
                    "min": "0",
                    "max": "10",
                    "uuid": str(uuid.uuid4()),
                },
                {
                    "name": "Disability Score",
                    "definition": (
                        "The extent to which fibromyalgia hinders patients' " "usual activities and quality of life"
                    ),
                    "min": "0",
                    "max": "10",
                    "uuid": str(uuid.uuid4()),
                },
            ]
            st.session_state.selected_group_dimensions = current_dims

        st.markdown(t("ui_text.customize_evaluation_dimensions"))
        st.info(t("ui_text.modify_dimensions_info"))

        # Import the dimensions editor function that doesn't use forms
        from pain_narratives.ui.components.prompt_manager import dimensions_editor_no_form

        # Show preview only for admins
        dims, invalid_range, invalid_fields = dimensions_editor_no_form(
            state_key="selected_group_dimensions",
            show_preview=is_admin,
            auto_save_to_db=True,
            experiment_group_id=st.session_state.get("selected_experiment_group_id"),
            user_id=st.session_state.user["id"] if st.session_state.user else None,
        )

        # Update button
        has_errors = invalid_range or invalid_fields
        if st.button(t("ui_text.dimensions_ready_button"), disabled=has_errors, type="primary"):
            if has_errors:
                st.error(t("ui_text.fix_dimension_ranges"))
            else:
                # Update the session state with the new dimensions
                st.session_state.selected_group_dimensions = dims

                # Get the group info from session state
                group_system_role = st.session_state.get("selected_group_system_role")
                group_base_prompt = st.session_state.get("selected_group_base_prompt")

                # Import function for generating prompt
                from pain_narratives.ui.components.prompt_manager import generate_prompt_from_dimensions

                # Generate the updated prompt using the group's system and base prompts
                generated_prompt = generate_prompt_from_dimensions(
                    dims,
                    group_system_role,
                    group_base_prompt,
                )
                st.session_state.current_prompt = generated_prompt

                # Update the Evaluation group in the database if we have all necessary info
                experiment_group_id = st.session_state.get("selected_experiment_group_id")
                if experiment_group_id and st.session_state.db_manager and st.session_state.user:
                    try:
                        success = st.session_state.db_manager.update_experiment_group(
                            group_id=experiment_group_id, user_id=st.session_state.user["id"], dimensions=dims
                        )
                        if success:
                            st.success(t("ui_text.dimensions_updated_success"))
                        else:
                            st.warning(t("ui_text.database_update_failed_local_saved"))
                    except PermissionError:
                        st.error(t("ui_text.no_permission_update"))
                    except Exception as e:
                        st.error(t("ui_text.error_updating_group").format(error=str(e)))
                        st.warning(t("ui_text.changes_saved_locally"))
                else:
                    st.success(t("ui_text.dimensions_updated_success"))

    def pain_assessment_tab(self, config: Dict[str, Any]) -> None:
        """Tab for evaluating the current pain narrative."""
        t = get_translator(st.session_state.language)
        st.header(t("pain_assessment.header"))

        # Check if Evaluation group is selected
        if config.get("experiment_group_id") is None:
            st.warning(t("pain_assessment.no_group_selected"))
            st.info(t("pain_assessment.evaluation_group_required"))
            return

        if st.session_state.openai_client is None:
            st.info(t("pain_assessment.setup_instructions"))
            return

        st.subheader(t("pain_assessment.current_narrative"))
        narrative_text = st.session_state.get("current_narrative_text", "")
        if not narrative_text:
            st.warning(t("pain_assessment.narrative_required"))
            return
        st.text_area(t("pain_assessment.pain_narrative_label"), value=narrative_text, height=200, disabled=True)

        # Set max_tokens from config and fix num_evaluations to 1 (single evaluation)
        from pain_narratives.config.settings import get_settings

        max_tokens = get_settings().model_config.default_max_tokens

        evaluate_button = st.button(
            t("pain_assessment.evaluate_button"),
            type="primary",
            disabled=not narrative_text,
            key="pain_assessment_evaluate"
        )
        rerun_button = st.button(
            t("pain_assessment.rerun_button"),
            disabled=not narrative_text,
            key="pain_assessment_rerun"
        )
        # Only run evaluation if button is pressed and stay on this tab
        if evaluate_button or rerun_button:
            self.evaluate_single_narrative(
                narrative_text,
                config,
                max_tokens,
                new_experiment=rerun_button,
            )
            # Do NOT trigger any rerun or tab switch here; result will be shown below
        # Show latest evaluation result below the input
        if st.session_state.evaluation_history:
            latest_result = st.session_state.evaluation_history[-1]
            # Build score_ranges from custom_dimensions if available
            score_ranges = None
            if "custom_dimensions" in st.session_state:
                dims = st.session_state["custom_dimensions"]
                score_ranges = {
                    d["name"].lower().replace(" ", "_"): (int(d["min"]), int(d["max"]))
                    for d in dims
                    if d.get("name") and d.get("min") and d.get("max")
                }

            display_evaluation_details(latest_result, expanded=True, score_ranges=score_ranges)

            feedback_dimensions = (
                st.session_state.get("selected_group_dimensions")
                or st.session_state.get("custom_dimensions")
                or []
            )
            render_assessment_feedback_form(latest_result, feedback_dimensions)

    def evaluate_single_narrative(
        self,
        narrative_text: str,
        config: Dict[str, Any],
        max_tokens: int,
        new_experiment: bool = False,
    ) -> None:
        """Evaluate a single narrative."""
        t = get_translator(st.session_state.language)
        logger.info("Starting single narrative evaluation")
        logger.info("Model: %s, Temperature: %s", config["model"], config["temperature"])

        try:
            with st.spinner(t("welcome.evaluating_narrative_spinner")):
                logger.info("Getting current prompt")
                current_prompt = get_current_prompt()
                logger.info(
                    "Prompt retrieved, length: %s",
                    len(current_prompt) if current_prompt else 0,
                )

                logger.info("Calling NarrativeEvaluator.evaluate_single_narrative")
                result = NarrativeEvaluator.evaluate_single_narrative(
                    narrative_text=narrative_text,
                    prompt=current_prompt,
                    openai_client=st.session_state.openai_client,
                    config=config,
                    max_tokens=max_tokens,
                )

                logger.info(
                    "Evaluation completed with result keys: %s",
                    list(result.keys()) if result else None,
                )

                # Debug: Immediately check session state after evaluation
                print(f"DEBUG: Session state keys immediately after evaluation: {list(st.session_state.keys())}")
                print(f"DEBUG: last_openai_response exists: {'last_openai_response' in st.session_state}")
                if "last_openai_response" in st.session_state:
                    print(f"DEBUG: last_openai_response type: {type(st.session_state.last_openai_response)}")
                    print(f"DEBUG: last_openai_response is None: {st.session_state.last_openai_response is None}")

                # Attach experiment_group_id to result for DB save
                result["experiment_group_id"] = config.get("experiment_group_id", 1)

                # Debug: Check if OpenAI response was stored correctly
                logger.info("Checking for OpenAI response in session state")
                if hasattr(st.session_state, "last_openai_response"):
                    logger.info("last_openai_response found in session state")
                    openai_response = st.session_state.last_openai_response
                    logger.info(
                        "OpenAI response keys: %s",
                        list(openai_response.keys()) if openai_response else "None",
                    )
                    logger.info("OpenAI response type: %s", type(openai_response))
                else:
                    logger.warning("last_openai_response NOT found in session state")

                st.session_state.evaluation_history.append(result)

                logger.info(
                    "Use database: %s, DB manager exists: %s",
                    config["use_database"],
                    bool(st.session_state.db_manager),
                )

                experiment_id = None
                if config["use_database"] and st.session_state.db_manager:
                    logger.info("Saving to database")
                    experiment_id = self.save_to_database(result, new_experiment=new_experiment)
                    result["experiment_id"] = experiment_id

                t = get_translator(st.session_state.language)
                st.success(t("ui_text.evaluation_completed_success"))

        except Exception as e:
            logger.error("Evaluation failed: %s", str(e), exc_info=True)
            st.error(f"❌ Evaluation failed: {str(e)}")

    def evaluate_multiple_narratives(
        self,
        narrative_text: str,
        config: Dict[str, Any],
        max_tokens: int,
        num_evaluations: int,
    ) -> None:
        """Evaluate a narrative multiple times for consistency testing."""
        t = get_translator(st.session_state.language)
        try:
            with st.spinner(t("welcome.evaluating_multiple_consistency_spinner")):
                evaluations = NarrativeEvaluator.evaluate_multiple_narratives(
                    narrative_text=narrative_text,
                    prompt=get_current_prompt(),
                    openai_client=st.session_state.openai_client,
                    config=config,
                    max_tokens=max_tokens,
                    num_evaluations=num_evaluations,
                )
                evaluation_result = {
                    "narrative": narrative_text,
                    "result": evaluations,
                    "model": config["model"],
                    "temperature": config["temperature"],
                    "timestamp": datetime.now().isoformat(),
                    "consistency_test": True,
                }
                st.session_state.evaluation_history.append(evaluation_result)
        except Exception as e:
            st.error(f"❌ Consistency evaluation failed: {str(e)}")

    def batch_evaluation_tab(self, config: Dict[str, Any]) -> None:
        """Tab for batch evaluation of multiple narratives."""
        t = get_translator(st.session_state.language)
        st.header(t("ui_text.batch_evaluation_header"))

        if st.session_state.openai_client is None:
            st.info(
                """
                ℹ️ **Setup Required**

                To use batch evaluation, please configure your OpenAI connection:

                1. Enter your OpenAI API key in the sidebar (or ensure it's set in your environment)
                2. Select your preferred model and temperature settings
                3. Click **"Initialize Connections"** to enable batch processing

                **Batch Processing Features:**
                - Upload CSV files with multiple pain narratives
                - Process hundreds of narratives efficiently
                - Built-in rate limiting to respect API limits
                - Export results to CSV for analysis
                - Optional database storage for long-term tracking
                """
            )
            return

        st.subheader(t("ui_text.upload_data_header"))

        uploaded_file = st.file_uploader(
            "Upload CSV file with narratives",
            type=["csv"],
            help=t("ui_text.csv_format_help"),
        )

        if uploaded_file is not None:
            try:
                df = pd.read_csv(uploaded_file)

                # Validate structure
                required_columns = ["narrative"]
                if not all(col in df.columns for col in required_columns):
                    st.error(f"CSV must contain columns: {required_columns}")
                    return

                st.success(f"✅ Loaded {len(df)} narratives")
                st.dataframe(df.head(), use_container_width=True)

                # Batch processing settings
                col1, col2, col3 = st.columns(3)

                with col1:
                    max_narratives = st.number_input(
                        "Max narratives to process",
                        min_value=1,
                        max_value=len(df),
                        value=min(10, len(df)),
                    )

                with col2:
                    delay_seconds = st.number_input(
                        "Delay between requests (seconds)",
                        min_value=0.1,
                        max_value=10.0,
                        value=1.0,
                        step=0.1,
                    )

                with col3:
                    save_results = st.checkbox(
                        "Save to database",
                        value=False,
                        disabled=st.session_state.db_manager is None,
                    )

                # Process button
                if st.button(t("ui_text.start_batch_processing_button"), type="primary"):
                    result_tuple = run_batch_evaluation(
                        df.head(max_narratives),
                        config,
                        delay_seconds,
                        save_results,
                        st.session_state.openai_client,
                        st.session_state.db_manager,
                        st.session_state.current_prompt,
                    )
                    batch_results, success_count, error_count = result_tuple

            except Exception as e:
                st.error(f"Error loading file: {str(e)}")

        else:
            # Sample data option
            st.info(t("ui_text.upload_csv_sample_info"))

            if st.button(t("ui_text.use_sample_data_button")):
                sample_df = self.create_sample_data()
                st.dataframe(sample_df, use_container_width=True)

                if st.button(t("ui_text.process_sample_data_button")):
                    result_tuple = run_batch_evaluation(
                        sample_df,
                        config,
                        1.0,
                        False,
                        st.session_state.openai_client,
                        st.session_state.db_manager,
                        st.session_state.current_prompt,
                    )
                    batch_results, success_count, error_count = result_tuple

    def create_sample_data(self) -> pd.DataFrame:
        """Create sample data for testing."""
        return pd.DataFrame(
            {
                "id": [1, 2, 3],
                "narrative": [
                    "Sufro de dolor constante en las articulaciones, especialmente por la mañana.",
                    "El dolor es variable, algunos días puedo trabajar pero otros apenas puedo moverme.",
                    "A pesar del dolor, sigo haciendo ejercicio y trabajando normalmente.",
                ],
                "category": ["High", "Medium", "Low"],
            }
        )

    def analytics_tab(self) -> None:
        """Tab for analytics and insights."""
        t = get_translator(st.session_state.language)
        st.header(t("analytics.header"))

        group_id = st.session_state.get("selected_experiment_group_id")
        db_manager = st.session_state.db_manager
        if group_id and db_manager:
            experiments = db_manager.get_experiments_by_group(group_id)
            questionnaires = db_manager.get_questionnaires_by_group(group_id)
            saved_results = db_manager.get_evaluation_results_by_group(group_id)
            st.subheader(t("analytics.group_summary").format(group_id=group_id))
            gcol1, gcol2 = st.columns(2)
            gcol1.metric(t("analytics.experiments_metric"), len(experiments))
            gcol2.metric(t("analytics.questionnaires_metric"), len(questionnaires))

            if saved_results:
                st.markdown("---")
                st.subheader(t("analytics.stored_results_header"))

                from pain_narratives.core.translation_service import TranslationService

                translation_service = TranslationService(st.session_state.openai_client)
                current_language = st.session_state.get("language", "en")

                table_data = []
                for r in saved_results:
                    row = {
                        "ID": r.id,
                        "Type": r.result_type,
                        "User": r.user_id,
                        "Experiment": r.experiment_id,
                        "Questionnaire": r.questionnaire_id,
                        "Created": r.created.isoformat() if r.created else "",
                    }

                    # Extract evaluation result in user's language
                    if isinstance(r.result_json, dict):
                        # Get result in user's preferred language
                        evaluation_result = translation_service.get_available_translation(
                            r.result_json, current_language
                        )
                        
                        # Log which language is being used
                        available_languages = list(r.result_json.keys()) if r.result_json else []
                        if current_language in available_languages:
                            logger.info(f"Using {current_language} translation for result {r.id}")
                        elif "en" in available_languages:
                            logger.info(f"Using English fallback for result {r.id} (requested: {current_language})")
                        else:
                            logger.warning(f"No suitable translation found for result {r.id}")

                        # Add translated content to the row
                        for k, v in evaluation_result.items():
                            if k not in row and not k.endswith("_explanation"):
                                row[k] = v

                    table_data.append(row)
                df = pd.DataFrame(table_data)
                st.dataframe(df, use_container_width=True)

        if not st.session_state.evaluation_history:
            st.info(t("analytics.no_evaluation_history"))
            return

        # Convert history to DataFrame for analysis
        eval_df = pd.DataFrame(st.session_state.evaluation_history)

        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(t("analytics.total_evaluations"), len(eval_df))

        with col2:
            unique_models = eval_df["model"].nunique()
            st.metric(t("analytics.models_used"), unique_models)

        with col3:
            avg_temp = eval_df["temperature"].mean()
            st.metric(t("analytics.avg_temperature"), f"{avg_temp:.2f}")

        with col4:
            recent_count = len(
                [
                    e
                    for e in st.session_state.evaluation_history
                    if pd.to_datetime(e["timestamp"]) > pd.Timestamp.now() - pd.Timedelta(hours=24)
                ]
            )
            st.metric(t("analytics.last_24h"), recent_count)

        # Detailed analysis
        if len(eval_df) > 1:
            st.subheader(t("analytics.evaluation_trends"))

            # Extract scores over time
            score_data = []
            for _, row in eval_df.iterrows():
                if isinstance(row["result"], dict) and "error" not in row["result"]:
                    for key, value in row["result"].items():
                        if key != "reasoning" and isinstance(value, (int, float)):
                            score_data.append(
                                {
                                    "timestamp": row["timestamp"],
                                    "dimension": key,
                                    "score": value,
                                    "model": row["model"],
                                }
                            )
                elif isinstance(row["result"], list):  # Multiple evaluations
                    for eval_result in row["result"]:
                        if isinstance(eval_result, dict):
                            for key, value in eval_result.items():
                                if key != "reasoning" and isinstance(value, (int, float)):
                                    score_data.append(
                                        {
                                            "timestamp": row["timestamp"],
                                            "dimension": key,
                                            "score": value,
                                            "model": row["model"],
                                        }
                                    )

            if score_data:
                scores_df = pd.DataFrame(score_data)

                # Score distribution by dimension
                st.subheader(t("analytics.score_distributions"))
                dimension_stats = scores_df.groupby("dimension")["score"].agg(["mean", "std", "min", "max"]).round(2)
                st.dataframe(dimension_stats, use_container_width=True)

                # Simple visualization
                dimension_means = scores_df.groupby("dimension")["score"].mean()
                st.bar_chart(dimension_means)

    def questionnaires_tab(self, config: Dict[str, Any]) -> None:
        """Tab for running questionnaires based on the last evaluated narrative."""
        t = get_translator(st.session_state.language)
        st.header(t("questionnaires.header"))

        if st.session_state.openai_client is None:
            st.info(t("questionnaires.description"))
            return

        # Multiple questionnaires available
        questionnaire_options = {
            "PCS. Escala de catastrofización del dolor": "PCS",
            "BPI-IS. Brief Pain Inventory - Interference Scale": "BPI-IS",
            "TSK-11SV. Tampa Scale of Kinesiophobia (Short Version)": "TSK-11SV"
        }
        
        # Get narrative text first
        narrative_text = st.session_state.get("current_narrative_text", "")
        if not narrative_text:
            st.warning(t("questionnaires.narrative_required"))
            return
        
        # Display narrative
        st.text_area(
            t("questionnaires.pain_narrative_label"),
            value=narrative_text,
            height=150,
            disabled=True,
            key="questionnaire_narrative_display"
        )
        
        # Questionnaire selection using session state for persistence
        st.subheader(t("questionnaires.select_questionnaires"))
        
        # Initialize questionnaire selections in session state
        if "selected_questionnaire_ids" not in st.session_state:
            st.session_state.selected_questionnaire_ids = []
        
        # Use session state to track checkbox states
        selected_questionnaires = []
        selected_questionnaire_ids = []
        
        # Create checkboxes with session state tracking
        for q_display_name, q_id in questionnaire_options.items():
            # Use session state key for each checkbox
            checkbox_key = f"questionnaire_selected_{q_id}"
            
            # Initialize checkbox state if not exists
            if checkbox_key not in st.session_state:
                st.session_state[checkbox_key] = False
            
            # Create checkbox with session state value
            is_selected = st.checkbox(
                q_display_name,
                value=st.session_state[checkbox_key],
                key=checkbox_key
            )
            
            if is_selected:
                selected_questionnaires.append(q_display_name)
                selected_questionnaire_ids.append(q_id)
        
        # Update session state with current selections
        st.session_state.selected_questionnaire_ids = selected_questionnaire_ids
        
        # Show selection summary
        if selected_questionnaires:
            st.write(f"**{t('questionnaires.selected_questionnaires_label')}** ({len(selected_questionnaires)})")
            for q_name in selected_questionnaires:
                st.write(f"• {q_name}")
        else:
            st.info(t("questionnaires.select_at_least_one"))
        
        # Action buttons
        col1, col2, col3 = st.columns(3)
        with col1:
            run_btn = st.button(
                t("questionnaires.run_questionnaires_button"),
                type="primary",
                disabled=not selected_questionnaires,
                key="questionnaire_run_btn"
            )
        with col2:
            rerun_btn = st.button(
                t("questionnaires.rerun_button"),
                disabled=not selected_questionnaires,
                key="questionnaire_rerun_btn"
            )
        with col3:
            clear_btn = st.button(
                t("questionnaires.clear_results_button"),
                disabled="questionnaire_results" not in st.session_state or not st.session_state.questionnaire_results,
                key="questionnaire_clear_btn"
            )
        
        # Handle clear results button
        if clear_btn:
            if "questionnaire_results" in st.session_state:
                del st.session_state.questionnaire_results
            st.rerun()
        
        if run_btn or rerun_btn:
            # Initialize results storage in session state
            if "questionnaire_results" not in st.session_state or rerun_btn:
                st.session_state.questionnaire_results = {}
            all_results = st.session_state.questionnaire_results
            
            # Run questionnaires sequentially
            for i, questionnaire_id in enumerate(selected_questionnaire_ids):
                questionnaire_name = selected_questionnaires[i]
                
                with st.spinner(f"{t('questionnaires.contacting_model')} - {questionnaire_name}"):
                    # Get custom prompts for this experiment group if available
                    experiment_group_id = st.session_state.get("selected_experiment_group_id")
                    custom_system_role = None
                    custom_instructions = None
                    
                    if experiment_group_id and st.session_state.db_manager:
                        try:
                            # Direct database query to get custom prompts for this experiment group
                            with st.session_state.db_manager.get_session() as session:
                                stmt = select(QuestionnairePrompt).where(
                                    QuestionnairePrompt.experiments_group_id == experiment_group_id
                                )
                                results = session.exec(stmt).all()

                                custom_prompts = {}
                                for prompt in results:
                                    custom_prompts[prompt.questionnaire_type] = {
                                        "system_role": prompt.system_role,
                                        "instructions": prompt.instructions
                                    }

                                if questionnaire_id in custom_prompts:
                                    custom_system_role = custom_prompts[questionnaire_id].get("system_role")
                                    custom_instructions = custom_prompts[questionnaire_id].get("instructions")
                        except Exception as e:
                            logger.warning(f"Failed to load custom prompts, using defaults: {e}")
                    
                    # Run the appropriate questionnaire
                    result = None
                    if questionnaire_id == "PCS":
                        result = run_pcs_questionnaire(
                            narrative=narrative_text,
                            openai_client=st.session_state.openai_client,
                            model=config["model"],
                            temperature=config["temperature"],
                            pcs_system_role=custom_system_role or PCS_SYSTEM_ROLE,
                            pcs_instructions=custom_instructions or PCS_INSTRUCTIONS,
                        )
                        result["prompt"] = custom_instructions or PCS_INSTRUCTIONS
                    elif questionnaire_id == "BPI-IS":
                        result = run_bpi_is_questionnaire(
                            narrative=narrative_text,
                            openai_client=st.session_state.openai_client,
                            model=config["model"],
                            temperature=config["temperature"],
                            bpi_system_role=custom_system_role or BPI_IS_SYSTEM_ROLE,
                            bpi_instructions=custom_instructions or BPI_IS_INSTRUCTIONS,
                        )
                        result["prompt"] = custom_instructions or BPI_IS_INSTRUCTIONS
                    elif questionnaire_id == "TSK-11SV":
                        result = run_tsk_11sv_questionnaire(
                            narrative=narrative_text,
                            openai_client=st.session_state.openai_client,
                            model=config["model"],
                            temperature=config["temperature"],
                            tsk_system_role=custom_system_role or TSK_11SV_SYSTEM_ROLE,
                            tsk_instructions=custom_instructions or TSK_11SV_INSTRUCTIONS,
                        )
                        result["prompt"] = custom_instructions or TSK_11SV_INSTRUCTIONS
                    
                    if result:
                        # Save to database if enabled
                        if config["use_database"] and st.session_state.db_manager:
                            db_id = self.save_questionnaire_to_db(
                                questionnaire_result=result,
                                narrative_text=narrative_text,
                                questionnaire_name=questionnaire_id,
                                config=config,
                                new_experiment=rerun_btn,
                            )
                            # Add the database ID to the result for feedback component
                            if db_id:
                                result["id"] = db_id
                        
                        all_results[questionnaire_id] = {
                            "result": result,
                            "display_name": questionnaire_name
                        }
                    else:
                        st.error(f"{t('questionnaires.no_result_error')} - {questionnaire_name}")

        # Display results from session state (persists across reruns)
        if "questionnaire_results" in st.session_state and st.session_state.questionnaire_results:
            st.divider()
            st.subheader(t("questionnaires.results_summary"))
            
            for questionnaire_id, data in st.session_state.questionnaire_results.items():
                result = data["result"]
                display_name = data["display_name"]
                
                # Create collapsible section for each questionnaire
                with st.expander(f"📋 {display_name}", expanded=len(st.session_state.questionnaire_results) == 1):
                    if questionnaire_id == "PCS":
                        self._display_pcs_results(result, t)
                    elif questionnaire_id == "BPI-IS":
                        self._display_bpi_is_results(result, t)
                    elif questionnaire_id == "TSK-11SV":
                        self._display_tsk_11sv_results(result, t)

    def _display_pcs_results(self, result: Dict[str, Any], t: Any) -> None:
        """Display PCS questionnaire results."""
        scores = result.get("scores", {})
        reasoning = result.get("model_reasoning", "")
        persona = result.get("persona", {})

        st.subheader(t("questionnaires.results_header"))
        
        # Display persona information
        if persona:
            st.info(f"**Persona**: {persona.get('name', 'Unknown')} - {persona.get('traits', 'No traits')}")

        st.subheader(t("questionnaires.scores_header"))
        if scores:
            # Create detailed table with question numbers, question text, and scores
            table_data = []
            for question_num, score in sorted(scores.items(), key=lambda x: int(x[0])):
                question_text = PCS_QUESTIONS.get(int(question_num), f"Question {question_num}")
                score_int = int(score)
                score_label = PCS_SCORE_LABELS.get(score_int, f"Invalid score: {score}")
                table_data.append(
                    {
                        t("questionnaires.question_column"): f"Q{question_num}",
                        t("questionnaires.question_text_column"): question_text,
                        t("questionnaires.score_column"): score_int,
                        t("questionnaires.scale_column"): score_label,
                    }
                )

            score_df = pd.DataFrame(table_data)
            st.dataframe(score_df, hide_index=True, use_container_width=True)

            # Calculate and display total score
            total_score = calculate_pcs_total_score(result)
            st.metric(
                label=t("questionnaires.total_score_label"),
                value=f"{total_score}",
                help=t("questionnaires.total_score_help"),
            )

            counts = count_scores(scores)
            display_score_distribution_chart(counts, "PCS", t)
        else:
            st.warning(t("questionnaires.no_scores_warning"))

        if reasoning:
            st.subheader(t("questionnaires.model_reasoning_header"))
            st.write(reasoning)

        # Add feedback component for PCS questionnaire
        st.markdown("---")
        render_questionnaire_feedback_form(
            questionnaire_result=result,
            questionnaire_name="PCS",
            experiment_id=None,  # Questionnaires don't belong to experiments
            group_id=st.session_state.get("selected_experiment_group_id", 0),
            narrative_id=st.session_state.get("current_narrative_id"),
        )

    def _display_bpi_is_results(self, result: Dict[str, Any], t: Any) -> None:
        """Display BPI-IS questionnaire results."""
        responses = result.get("responses", [])
        persona = result.get("persona", {})

        st.subheader(t("questionnaires.results_header"))
        
        # Display persona information
        if persona:
            st.info(f"**Persona**: {persona.get('name', 'Unknown')} - {persona.get('traits', 'No traits')}")

        if responses:
            # Create detailed table
            table_data = []
            for response in responses:
                code = response.get("code", "")
                value = response.get("value", 0)
                question_text = BPI_IS_QUESTIONS.get(code, f"Question {code}")
                
                # Determine scale type for labels
                if code in ["BPI_Q1_1", "BPI_Q1_2", "BPI_Q1_3", "BPI_Q1_5", "BPI_Q1_6", "BPI_Q1_7"]:
                    scale_type = "interference"
                else:
                    scale_type = "intensity"
                
                table_data.append({
                    t("questionnaires.question_column"): code,
                    t("questionnaires.question_text_column"): question_text,
                    t("questionnaires.score_column"): value,
                    t("questionnaires.scale_type_column"): scale_type.title(),
                })

            score_df = pd.DataFrame(table_data)
            st.dataframe(score_df, hide_index=True, use_container_width=True)

            # Calculate and display summary metrics
            interference_scores = [r["value"] for r in responses if r["code"] in ["BPI_Q1_1", "BPI_Q1_2", "BPI_Q1_3", "BPI_Q1_5", "BPI_Q1_6", "BPI_Q1_7"]]
            intensity_scores = [r["value"] for r in responses if r["code"] in ["BPI_Q2_8", "BPI_Q3_9", "BPI_Q4_10", "BPI_Q5_11"]]
            total_score = calculate_bpi_is_total_score(result)
            
            # Display total score prominently
            st.metric(
                label=t("questionnaires.total_score_label"),
                value=f"{total_score}",
                help=t("questionnaires.bpi_total_help"),
            )
            
            # Display subscale averages
            col1, col2 = st.columns(2)
            with col1:
                st.metric(
                    label=t("questionnaires.interference_average"),
                    value=f"{sum(interference_scores) / len(interference_scores):.1f}" if interference_scores else "N/A",
                    help=t("questionnaires.interference_help"),
                )
            with col2:
                st.metric(
                    label=t("questionnaires.intensity_average"),
                    value=f"{sum(intensity_scores) / len(intensity_scores):.1f}" if intensity_scores else "N/A",
                    help=t("questionnaires.intensity_help"),
                )

            # Score distribution
            counts = count_bpi_is_scores(responses)
            display_score_distribution_chart(counts, "BPI-IS", t)
        else:
            st.warning(t("questionnaires.no_scores_warning"))

        # Display model reasoning
        reasoning = result.get("model_reasoning", "")
        if reasoning:
            st.subheader(t("questionnaires.model_reasoning_header"))
            st.write(reasoning)

        # Add feedback component for BPI-IS questionnaire
        st.markdown("---")
        render_questionnaire_feedback_form(
            questionnaire_result=result,
            questionnaire_name="BPI-IS",
            experiment_id=None,  # Questionnaires don't belong to experiments
            group_id=st.session_state.get("selected_experiment_group_id", 0),
            narrative_id=st.session_state.get("current_narrative_id"),
        )

    def _display_tsk_11sv_results(self, result: Dict[str, Any], t: Any) -> None:
        """Display TSK-11SV questionnaire results."""
        responses = result.get("responses", [])
        persona = result.get("persona", {})

        st.subheader(t("questionnaires.results_header"))
        
        # Display persona information
        if persona:
            st.info(f"**Persona**: {persona.get('name', 'Unknown')} - {persona.get('traits', 'No traits')}")

        if responses:
            # Create detailed table
            table_data = []
            for response in responses:
                code = response.get("code", "")
                value = response.get("value", 1)
                question_text = TSK_11SV_QUESTIONS.get(code, f"Question {code}")
                scale_label = TSK_11SV_SCALE_LABELS.get(value, f"Invalid score: {value}")
                
                table_data.append({
                    t("questionnaires.question_column"): code,
                    t("questionnaires.question_text_column"): question_text,
                    t("questionnaires.score_column"): value,
                    t("questionnaires.scale_column"): scale_label,
                })

            score_df = pd.DataFrame(table_data)
            st.dataframe(score_df, hide_index=True, use_container_width=True)

            # Calculate and display total score
            total_score = calculate_tsk_11sv_total_score(result)
            average_score = total_score / len(responses) if responses else 0
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric(
                    label=t("questionnaires.total_score_label"),
                    value=f"{total_score}",
                    help=t("questionnaires.tsk_total_help"),
                )
            with col2:
                st.metric(
                    label=t("questionnaires.average_score_label"),
                    value=f"{average_score:.1f}",
                    help=t("questionnaires.tsk_average_help"),
                )

            # Score distribution
            counts = count_tsk_11sv_scores(responses)
            display_score_distribution_chart(counts, "TSK-11SV", t)
        else:
            st.warning(t("questionnaires.no_scores_warning"))

        # Display model reasoning
        reasoning = result.get("model_reasoning", "")
        if reasoning:
            st.subheader(t("questionnaires.model_reasoning_header"))
            st.write(reasoning)

        # Add feedback component for TSK-11SV questionnaire
        st.markdown("---")
        render_questionnaire_feedback_form(
            questionnaire_result=result,
            questionnaire_name="TSK-11SV",
            experiment_id=None,  # Questionnaires don't belong to experiments
            group_id=st.session_state.get("selected_experiment_group_id", 0),
            narrative_id=st.session_state.get("current_narrative_id"),
        )

    def management_tab(self) -> None:
        """Tab for application management including Evaluation groups and user administration."""
        t = get_translator(st.session_state.get("language", "en"))
        if st.session_state.user is None:
            st.error(t("ui_text.login_required_management"))
            return

        try:
            db_manager = DatabaseManager()
            user_info = st.session_state.user  # Use the existing user session state
            management_tab_ui(db_manager, user_info)
        except Exception as e:
            st.error(f"❌ Error loading management interface: {str(e)}")
            logger.error(f"Management tab error: {e}")

    def help_tab(self) -> None:
        """Tab for help and documentation."""
        t = get_translator(st.session_state.language)
        st.header(t("help.header"))

        # Platform overview
        st.markdown(f"**{t('welcome.tagline')}**")
        st.write(t("welcome.description"))

        # About the platform
        st.subheader(t("welcome.about_platform_title"))
        st.write(t("welcome.about_platform_description"))

        # Key capabilities
        st.subheader(t("welcome.key_capabilities_title"))
        st.markdown(t("welcome.capability_management"))
        st.markdown(t("welcome.capability_evaluation"))
        st.markdown(t("welcome.capability_spanish"))
        st.markdown(t("welcome.capability_batch"))
        st.markdown(t("welcome.capability_analytics"))
        st.markdown(t("welcome.capability_help"))

        # Quick start guide
        st.subheader(t("welcome.quick_start_title"))
        st.markdown(t("welcome.quick_start_step1"))
        st.markdown(t("welcome.quick_start_step2"))
        st.markdown(t("welcome.quick_start_step3"))
        st.markdown(t("welcome.quick_start_step4"))

        # Need help section
        st.subheader(t("welcome.need_help_title"))
        st.markdown(t("welcome.need_help_item1"))
        st.markdown(t("welcome.need_help_item2"))
        st.markdown(t("welcome.need_help_item3"))

        # For administrators
        if st.session_state.user and st.session_state.is_admin:
            st.subheader(t("welcome.for_administrators_title"))
            st.markdown(t("welcome.for_administrators_description"))

        # Getting started
        st.subheader(t("welcome.getting_started_title"))
        st.markdown(t("welcome.getting_started_description"))

        # Footer
        st.markdown("---")
        st.caption(t("footer.version"))
        st.caption(t("footer.built_with"))
        st.caption(t("footer.tagline_footer"))

    def run(self) -> None:
        """Main application entry point."""
        # Set up configuration
        config = self.setup_sidebar()

        # Main content area
        t = get_translator(st.session_state.language)

        # Check if user is logged in to determine which tabs to show
        if st.session_state.user is None:
            # Show limited tabs for non-authenticated users
            tab_options = [
                t("tabs.narrative_dimensions"),
                t("tabs.help"),
            ]
            
            # Initialize or validate active tab for limited options
            if "active_tab" not in st.session_state or st.session_state.active_tab not in tab_options:
                st.session_state.active_tab = tab_options[0]
            
            # Get current index safely
            try:
                current_index = tab_options.index(st.session_state.active_tab)
            except ValueError:
                current_index = 0
                st.session_state.active_tab = tab_options[0]
            
            # Tab selector with persistence
            selected_tab = st.radio(
                "🗂️ Navigation",
                options=tab_options,
                index=current_index,
                key="tab_selector_limited",
                horizontal=True
            )
            
            # Update session state only if tab changed
            if selected_tab != st.session_state.active_tab:
                st.session_state.active_tab = selected_tab
                st.rerun()
            
            # Display content based on selected tab
            if selected_tab == t("tabs.narrative_dimensions"):
                self.narrative_dimensions_tab()
            elif selected_tab == t("tabs.help"):
                self.help_tab()
        else:
            # Show all tabs for authenticated users
            tab_options = [
                t("tabs.narrative_dimensions"),
                t("tabs.pain_assessment"),
                t("tabs.questionnaires"),
                t("tabs.analytics"),
                t("tabs.management"),
                t("tabs.help"),
            ]
            
            # Initialize or validate active tab for full options
            if "active_tab" not in st.session_state or st.session_state.active_tab not in tab_options:
                st.session_state.active_tab = tab_options[0]
            
            # Get current index safely
            try:
                current_index = tab_options.index(st.session_state.active_tab)
            except ValueError:
                current_index = 0
                st.session_state.active_tab = tab_options[0]
            
            # Tab selector with persistence
            selected_tab = st.radio(
                "🗂️ Navigation",
                options=tab_options,
                index=current_index,
                key="tab_selector_full",
                horizontal=True
            )
            
            # Update session state only if tab changed
            if selected_tab != st.session_state.active_tab:
                st.session_state.active_tab = selected_tab
                st.rerun()
            
            # Display content based on selected tab
            if selected_tab == t("tabs.narrative_dimensions"):
                self.narrative_dimensions_tab()
            elif selected_tab == t("tabs.pain_assessment"):
                self.pain_assessment_tab(config)
            elif selected_tab == t("tabs.questionnaires"):
                self.questionnaires_tab(config)
            elif selected_tab == t("tabs.analytics"):
                self.analytics_tab()
            elif selected_tab == t("tabs.management"):
                self.management_tab()
            elif selected_tab == t("tabs.help"):
                self.help_tab()

    def save_to_database(self, result: Dict[str, Any], new_experiment: bool = False) -> int:
        """Save evaluation result to database with multilingual support."""
        from pain_narratives.core.translation_service import TranslationService

        try:
            db_manager = st.session_state.db_manager
            if not db_manager:
                raise ValueError("Database manager not available")

            # Get user_id from session state
            user_id = st.session_state.user["id"] if st.session_state.user else None
            if user_id is None:
                raise ValueError("User ID not available")

            # Create experiment record
            experiment_data = {
                "experiments_group_id": result.get("experiment_group_id", 1),
                "user_id": user_id,  # Add the missing user_id
                "repeated": 0,
                "language_instructions": "english",
                "model_provider": "openai",
                "model": result.get("model", "gpt-5"),
                "with_context": False,
                "narrative_id": 1,  # Default for UI evaluations
                "extra_description": {
                    "type": "ui_evaluation",
                    "timestamp": result.get("timestamp"),
                },
                "repo_sha": "",
                "exp_type": "ui",
            }

            experiment_id = db_manager.register_new_experiment(experiment_data)

            # Prepare multilingual result JSON
            current_language = st.session_state.get("language", "en")

            # Structure the result data for multilingual storage
            multilingual_result = {"en": result.get("result", {})}

            # If user is using a different language, translate the result
            if current_language != "en" and result.get("result"):
                logger.info(f"User language is {current_language}, translating evaluation result")
                
                # Get translator for user messages
                t = get_translator(st.session_state.language)
                
                # Show translation progress to user
                translation_progress = st.empty()
                translation_progress.info(t("ui_text.translating_result").format(language=current_language.upper()))
                
                translation_service = TranslationService(st.session_state.openai_client)

                try:
                    translated_result = translation_service.translate_evaluation_result(
                        result["result"], current_language
                    )
                    multilingual_result[current_language] = translated_result
                    logger.info(f"Successfully added {current_language} translation to result")
                    
                    # Update user with success message
                    translation_progress.success(t("ui_text.translation_completed_success").format(language=current_language.upper()))
                    
                except Exception as translation_error:
                    logger.warning(f"Translation failed: {translation_error}")
                    translation_progress.warning(t("ui_text.translation_failed_english_only").format(error=str(translation_error)))
                    # Continue without translation

            # Save evaluation result to evaluation_results table
            evaluation_result_data = {
                "experiment_id": experiment_id,
                "experiments_group_id": result.get("experiment_group_id", 1),
                "narrative_id": 1,  # Default for UI evaluations
                "user_id": user_id,
                "result_type": "narrative_evaluation",
                "result_json": multilingual_result,
            }

            evaluation_result_id = db_manager.save_evaluation_result(evaluation_result_data)
            logger.info(f"Saved evaluation result with ID: {evaluation_result_id}")

            # Update the evaluation result in session state with multilingual version
            if st.session_state.evaluation_history:
                # Update the most recent evaluation result with multilingual structure
                latest_eval = st.session_state.evaluation_history[-1]
                if latest_eval.get("result") == result.get("result"):  # Match by content
                    # Replace the result with multilingual version
                    latest_eval["result"] = multilingual_result
                    logger.info("Updated session state evaluation_history with multilingual result")

            return experiment_id

        except Exception as e:
            logger.error(f"Failed to save to database: {e}")
            raise

    def save_questionnaire_to_db(
        self,
        questionnaire_result: Dict[str, Any],
        narrative_text: str,
        questionnaire_name: str,
        config: Dict[str, Any],
        new_experiment: bool = False,
    ) -> Optional[int]:
        """Save questionnaire result to database and return the database ID."""
        try:
            db_manager = st.session_state.db_manager
            if not db_manager:
                raise ValueError("Database manager not available")

            # Calculate total score based on questionnaire type
            total_score = None
            if questionnaire_name == "PCS" and "scores" in questionnaire_result:
                total_score = calculate_pcs_total_score(questionnaire_result)
            elif questionnaire_name == "BPI-IS" and "responses" in questionnaire_result:
                total_score = calculate_bpi_is_total_score(questionnaire_result)
            elif questionnaire_name == "TSK-11SV" and "responses" in questionnaire_result:
                total_score = calculate_tsk_11sv_total_score(questionnaire_result)

            # Add total score to result_json if calculated
            result_json = questionnaire_result.copy()
            if total_score is not None:
                result_json["total_score"] = total_score

            # Get required database fields
            experiments_group_id = st.session_state.get("selected_experiment_group_id")
            narrative_id = st.session_state.get("current_narrative_id")
            user_id = st.session_state.user["id"] if st.session_state.user else None

            # Check if all required fields are available
            if not all([experiments_group_id, narrative_id, user_id]):
                missing_fields = []
                if not experiments_group_id:
                    missing_fields.append("experiments_group_id")
                if not narrative_id:
                    missing_fields.append("narrative_id")
                if not user_id:
                    missing_fields.append("user_id")
                
                logger.warning(f"Cannot save questionnaire to database: missing required fields: {missing_fields}")
                st.warning(f"Questionnaire results cannot be saved to database. Missing: {', '.join(missing_fields)}")
                
                if total_score is not None:
                    logger.info(f"Calculated total score: {total_score} (not saved to database)")
                return None

            # Prepare questionnaire data for database
            questionnaire_data = {
                "experiments_group_id": experiments_group_id,
                "narrative_id": narrative_id,
                "user_id": user_id,
                "questionnaire_name": questionnaire_name,
                "prompt": questionnaire_result.get("prompt", ""),
                "result_json": result_json,
            }

            # Save questionnaire result
            questionnaire_id = db_manager.save_questionnaire_result(questionnaire_data)
            logger.info(f"Saved questionnaire {questionnaire_name} to database with ID: {questionnaire_id}")
            
            # Save request/response to request_response table if available in session state
            if hasattr(st.session_state, "last_openai_response") and hasattr(st.session_state, "last_prompt_messages"):
                try:
                    openai_response = st.session_state.last_openai_response
                    prompt_messages = st.session_state.last_prompt_messages
                    
                    if openai_response and prompt_messages:
                        # Create a minimal experiment entry for the questionnaire
                        experiment_data = {
                            "experiments_group_id": experiments_group_id,
                            "user_id": user_id,
                            "repeated": 0,
                            "language_instructions": "spanish",  # Questionnaires are in Spanish
                            "model_provider": "openai",
                            "model": openai_response.get("model", "gpt-5"),
                            "with_context": False,
                            "narrative_id": narrative_id,
                            "extra_description": {
                                "type": "questionnaire",
                                "questionnaire_name": questionnaire_name,
                                "questionnaire_id": questionnaire_id,
                            },
                            "repo_sha": "",
                            "exp_type": "questionnaire",
                        }
                        
                        experiment_id = db_manager.register_new_experiment(experiment_data)
                        
                        # Prepare request JSON
                        request_json = {
                            "model": openai_response.get("model", "gpt-5"),
                            "messages": prompt_messages,
                            "temperature": 1.0,
                            "top_p": 1.0,
                        }
                        
                        # Save request/response
                        db_manager.save_request_response(experiment_id, request_json, openai_response)
                        logger.info(f"Saved request/response for questionnaire {questionnaire_name} with experiment_id: {experiment_id}")
                except Exception as req_resp_error:
                    logger.warning(f"Failed to save request/response for questionnaire: {req_resp_error}")
                    # Don't fail the whole save if just request/response fails
            
            if total_score is not None:
                logger.info(f"Calculated total score: {total_score}")

            return questionnaire_id

        except Exception as e:
            logger.error(f"Failed to save questionnaire to database: {e}")
            raise


def main() -> None:
    """Main entry point for the application."""
    app = PainNarrativesApp()
    app.run()


if __name__ == "__main__":
    main()
