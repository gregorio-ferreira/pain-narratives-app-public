"""Utility functions for managing questionnaire prompts for experiment groups."""

from datetime import datetime
from typing import Dict, Optional

from sqlmodel import select

from pain_narratives.config.prompts import (
    get_questionnaire_prompts as get_yaml_questionnaire_prompts,
)
from pain_narratives.core.database import DatabaseManager
from pain_narratives.db.models_sqlmodel import ExperimentGroup, QuestionnairePrompt

# Load default prompt configurations from YAML
# These are loaded from src/pain_narratives/config/default_prompts.yaml
DEFAULT_QUESTIONNAIRE_PROMPTS = get_yaml_questionnaire_prompts()


def get_questionnaire_prompts_for_group(
    db_manager: DatabaseManager,
    experiment_group_id: int
) -> Dict[str, Dict[str, str]]:
    """
    Get all questionnaire prompts for a specific experiment group.

    Args:
        db_manager: DatabaseManager instance
        experiment_group_id: ID of the experiment group

    Returns:
        Dict mapping questionnaire types to their prompts (system_role, instructions)
    """
    with db_manager.get_session() as session:
        stmt = select(QuestionnairePrompt).where(
            QuestionnairePrompt.experiments_group_id == experiment_group_id
        )
        results = session.exec(stmt).all()

        prompts = {}
        for prompt in results:
            prompts[prompt.questionnaire_type] = {
                "system_role": prompt.system_role,
                "instructions": prompt.instructions
            }

        return prompts


def initialize_default_prompts_for_group(
    db_manager: DatabaseManager,
    experiment_group_id: int
) -> bool:
    """
    Initialize default prompts for all questionnaire types for an experiment group.

    Args:
        db_manager: DatabaseManager instance
        experiment_group_id: ID of the experiment group

    Returns:
        True if successful, False otherwise
    """
    try:
        with db_manager.get_session() as session:
            # Check if experiment group exists
            group_stmt = select(ExperimentGroup).where(ExperimentGroup.experiments_group_id == experiment_group_id)
            group = session.exec(group_stmt).first()
            if not group:
                return False

            # Create default prompts for each questionnaire type
            for q_type, default_prompts in DEFAULT_QUESTIONNAIRE_PROMPTS.items():
                # Check if prompt already exists
                existing_stmt = select(QuestionnairePrompt).where(
                    QuestionnairePrompt.experiments_group_id == experiment_group_id,
                    QuestionnairePrompt.questionnaire_type == q_type
                )
                existing = session.exec(existing_stmt).first()

                if not existing:
                    new_prompt = QuestionnairePrompt(
                        experiments_group_id=experiment_group_id,
                        questionnaire_type=q_type,
                        system_role=default_prompts["system_role"],
                        instructions=default_prompts["instructions"],
                        created_at=datetime.now(),
                        updated_at=datetime.now()
                    )
                    session.add(new_prompt)

            session.commit()
            return True

    except Exception:
        return False


def update_questionnaire_prompt(
    db_manager: DatabaseManager,
    experiment_group_id: int,
    questionnaire_type: str,
    system_role: Optional[str] = None,
    instructions: Optional[str] = None
) -> bool:
    """
    Update a specific questionnaire prompt for an experiment group.

    Args:
        db_manager: DatabaseManager instance
        experiment_group_id: ID of the experiment group
        questionnaire_type: Type of questionnaire (PCS, BPI-IS, TSK-11SV)
        system_role: New system role prompt (optional)
        instructions: New instructions prompt (optional)

    Returns:
        True if successful, False otherwise
    """
    if not system_role and not instructions:
        return False

    try:
        with db_manager.get_session() as session:
            stmt = select(QuestionnairePrompt).where(
                QuestionnairePrompt.experiments_group_id == experiment_group_id,
                QuestionnairePrompt.questionnaire_type == questionnaire_type
            )
            prompt = session.exec(stmt).first()

            if not prompt:
                # Create new prompt if it doesn't exist
                prompt = QuestionnairePrompt(
                    experiments_group_id=experiment_group_id,
                    questionnaire_type=questionnaire_type,
                    system_role=system_role or DEFAULT_QUESTIONNAIRE_PROMPTS[questionnaire_type]["system_role"],
                    instructions=instructions or DEFAULT_QUESTIONNAIRE_PROMPTS[questionnaire_type]["instructions"],
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                session.add(prompt)
            else:
                # Update existing prompt
                if system_role:
                    prompt.system_role = system_role
                if instructions:
                    prompt.instructions = instructions
                prompt.updated_at = datetime.now()

            session.commit()
            return True

    except Exception:
        return False
