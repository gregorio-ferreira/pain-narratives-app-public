"""Database operations and connection management."""

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import create_engine, func
from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from pain_narratives.config.prompts import get_base_prompt as yaml_get_base_prompt
from pain_narratives.config.prompts import get_default_dimensions as yaml_get_default_dimensions
from pain_narratives.config.prompts import get_questionnaire_prompts as yaml_get_questionnaire_prompts
from pain_narratives.config.prompts import get_system_role as yaml_get_system_role
from pain_narratives.config.settings import get_settings
from pain_narratives.db.base import SCHEMA_NAME
from pain_narratives.db.models_sqlmodel import (
    AssessmentFeedback,
    EvaluationResult,
    ExperimentGroup,
    ExperimentGroupUser,
    ExperimentList,
    Narrative,
    Questionnaire,
    QuestionnaireFeedback,
    QuestionnairePrompt,
    RequestResponse,
    User,
    UserPrompt,
)


class DatabaseManager:
    """Database connection and operations manager using SQLModel."""

    def __init__(self, engine: Optional[Engine] = None):
        """Initialize the database manager."""
        self._engine: Optional[Engine] = engine

    @property
    def engine(self) -> Engine:
        """Get or create database engine."""
        if self._engine is None:
            self._engine = self._create_engine()
        return self._engine

    def get_session(self) -> Session:
        """Create a new SQLModel Session."""
        return Session(self.engine)

    @property
    def schema(self) -> str:
        """Get the database schema name."""
        return SCHEMA_NAME

    def _create_engine(self) -> Engine:
        """Create a new database engine using settings."""
        settings = get_settings()
        try:
            engine = create_engine(settings.database_url, echo=False)
            # Test connection
            with engine.connect():
                pass
            return engine
        except Exception as e:
            raise ConnectionError(f"Could not establish database connection: {e}") from e

    # User authentication methods
    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate a user by verifying username and hashed password."""
        with self.get_session() as session:
            user = session.exec(select(User).where(User.username == username)).first()
            if user:
                hashed_input = hashlib.sha256(password.encode()).hexdigest()
                if hashed_input == user.hashed_password:
                    return {
                        "id": user.id,
                        "username": user.username,
                        "is_admin": user.is_admin,
                        "preferred_language": user.preferred_language,
                    }
        return None

    def create_user(self, username: str, password: str, is_admin: bool = False) -> User:
        """Create a new user."""
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        user = User(username=username, hashed_password=hashed_password, is_admin=is_admin)
        with self.get_session() as session:
            session.add(user)
            session.commit()
            session.refresh(user)
        return user

    def is_user_admin(self, user_id: int) -> bool:
        """Check if a user has admin privileges."""
        with self.get_session() as session:
            user = session.exec(select(User).where(User.id == user_id)).first()
            return bool(user and user.is_admin)

    def update_user_language(self, user_id: int, language: str) -> bool:
        """Update a user's preferred language."""
        with self.get_session() as session:
            user = session.exec(select(User).where(User.id == user_id)).first()
            if user:
                user.preferred_language = language
                session.add(user)
                session.commit()
                return True
            return False

    def update_user_admin_status(self, user_id: int, is_admin: bool) -> bool:
        """Update a user's admin status."""
        with self.get_session() as session:
            user = session.exec(select(User).where(User.id == user_id)).first()
            if user:
                user.is_admin = is_admin
                session.add(user)
                session.commit()
                return True
            return False

    def reset_user_password(self, user_id: int, new_password: str) -> bool:
        """Reset a user's password."""
        hashed_password = hashlib.sha256(new_password.encode()).hexdigest()
        with self.get_session() as session:
            user = session.exec(select(User).where(User.id == user_id)).first()
            if user:
                user.hashed_password = hashed_password
                session.add(user)
                session.commit()
                return True
            return False

    def delete_user(self, user_id: int) -> bool:
        """Delete a user (admin only operation)."""
        with self.get_session() as session:
            user = session.exec(select(User).where(User.id == user_id)).first()
            if user:
                session.delete(user)
                session.commit()
                return True
            return False

    def get_user_experiment_groups(self, user_id: int) -> List[int]:
        """Get list of experiment group IDs that a user belongs to."""
        with self.get_session() as session:
            links = session.exec(select(ExperimentGroupUser).where(ExperimentGroupUser.user_id == user_id)).all()
            return [link.experiments_group_id for link in links]

    def update_user_experiment_groups(self, user_id: int, group_ids: List[int]) -> bool:
        """Update the experiment groups assigned to a user.
        
        Args:
            user_id: The ID of the user to update
            group_ids: List of experiment group IDs to assign to the user
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            ValueError: If any group_id doesn't exist in the database
        """
        with self.get_session() as session:
            # Validate that all group IDs exist
            for group_id in group_ids:
                group = session.exec(
                    select(ExperimentGroup).where(ExperimentGroup.experiments_group_id == group_id)
                ).first()
                if not group:
                    raise ValueError(f"Experiment group with ID {group_id} does not exist")
            
            # Delete all existing assignments for this user
            existing_links = session.exec(
                select(ExperimentGroupUser).where(ExperimentGroupUser.user_id == user_id)
            ).all()
            for link in existing_links:
                session.delete(link)
            
            # Create new assignments
            for group_id in group_ids:
                new_link = ExperimentGroupUser(
                    experiments_group_id=group_id,
                    user_id=user_id
                )
                session.add(new_link)
            
            session.commit()
            return True

    def get_all_experiment_groups(self) -> List[ExperimentGroup]:
        """Get all experiment groups in the database.
        
        Returns:
            List of all ExperimentGroup objects
        """
        with self.get_session() as session:
            return list(session.exec(select(ExperimentGroup)).all())

    # Experiment group methods
    def get_experiment_groups_for_user(self, user_id: Optional[int], is_admin: bool) -> List[ExperimentGroup]:
        """Retrieve experiment groups accessible by a user or all if admin."""
        with self.get_session() as session:
            if is_admin:
                return list(session.exec(select(ExperimentGroup)))
            links = session.exec(select(ExperimentGroupUser).where(ExperimentGroupUser.user_id == user_id)).all()
            group_ids = [link.experiments_group_id for link in links]
            if not group_ids:
                return []
            group_query = select(ExperimentGroup).where(ExperimentGroup.experiments_group_id.in_(group_ids))
            return list(session.exec(group_query))

    def create_experiment_group(
        self,
        owner_id: int,
        description: str,
        system_role: Optional[str] = None,
        base_prompt: Optional[str] = None,
        dimensions: Optional[List[Dict[str, Any]]] = None,
    ) -> ExperimentGroup:
        """Create a new experiment group. Only admins can create groups."""

        if not self.is_user_admin(owner_id):
            raise PermissionError("Only admin users can create experiment groups")
        group = ExperimentGroup(
            owner_id=owner_id,
            description=description,
            system_role=system_role,
            base_prompt=base_prompt,
            dimensions=dimensions,
        )
        with self.get_session() as session:
            session.add(group)
            session.commit()
            session.refresh(group)
        return group

    def update_experiment_group(
        self,
        group_id: int,
        user_id: int,
        description: Optional[str] = None,
        system_role: Optional[str] = None,
        base_prompt: Optional[str] = None,
        dimensions: Optional[List[Dict[str, Any]]] = None,
        concluded: Optional[bool] = None,
    ) -> bool:
        """Update an experiment group. Allows admins, owners, and assigned users to update."""
        with self.get_session() as session:
            group = session.exec(
                select(ExperimentGroup).where(ExperimentGroup.experiments_group_id == group_id)
            ).first()

            if not group:
                return False

            # Check permissions: admin, owner, or assigned user
            if not self.can_user_edit_experiment_group(user_id, group_id):
                raise PermissionError("You don't have permission to update this experiment group")

            # Update fields if provided
            if description is not None:
                group.description = description
            if system_role is not None:
                group.system_role = system_role
            if base_prompt is not None:
                group.base_prompt = base_prompt
            if dimensions is not None:
                group.dimensions = dimensions
            if concluded is not None:
                group.concluded = concluded

            session.commit()
            return True

    # Experiment methods
    def create_experiment(self, experiment_data: Dict[str, Any]) -> ExperimentList:
        """Create a new experiment."""
        experiment = ExperimentList(**experiment_data)
        with self.get_session() as session:
            session.add(experiment)
            session.commit()
            session.refresh(experiment)
        return experiment

    def register_new_experiment(self, experiment_data: Dict[str, Any]) -> int:
        """Register a new experiment and return its ID."""
        experiment = self.create_experiment(experiment_data)
        return experiment.experiment_id if experiment.experiment_id is not None else -1

    def register_new_experiments_group(
        self,
        description: str,
        system_role: Optional[str] = None,
        base_prompt: Optional[str] = None,
        owner_id: int = 1,
        dimensions: Optional[List[Dict[str, Any]]] = None,
    ) -> int:
        """Register a new experiment group and return its ID."""

        if not self.is_user_admin(owner_id):
            raise PermissionError("Only admin users can create experiment groups")

        # Resolve YAML defaults when parameters are not provided
        resolved_system_role = system_role or yaml_get_system_role()
        resolved_base_prompt = base_prompt or yaml_get_base_prompt()
        resolved_dimensions = dimensions or yaml_get_default_dimensions()

        group = self.create_experiment_group(
            owner_id=owner_id,
            description=description,
            system_role=resolved_system_role,
            base_prompt=resolved_base_prompt,
            dimensions=resolved_dimensions,
        )

        group_id = group.experiments_group_id or -1

        # Initialize questionnaire prompts for this group from YAML defaults (idempotent)
        if group_id != -1:
            try:
                yaml_prompts = yaml_get_questionnaire_prompts()
                with self.get_session() as session:
                    for q_type, prompts in yaml_prompts.items():
                        existing = session.exec(
                            select(QuestionnairePrompt).where(
                                QuestionnairePrompt.experiments_group_id == group_id,
                                QuestionnairePrompt.questionnaire_type == q_type,
                            )
                        ).first()
                        if not existing:
                            session.add(
                                QuestionnairePrompt(
                                    experiments_group_id=group_id,
                                    questionnaire_type=q_type,
                                    system_role=prompts["system_role"],
                                    instructions=prompts["instructions"],
                                    created_at=datetime.now(timezone.utc),
                                    updated_at=datetime.now(timezone.utc),
                                )
                            )
                    session.commit()
            except Exception:
                # Best-effort only; do not block group creation if initialization fails
                pass

        return group_id

    def update_experiment_status(self, experiment_id: int, **kwargs) -> None:
        """Update experiment status fields."""
        with self.get_session() as session:
            experiment = session.exec(
                select(ExperimentList).where(ExperimentList.experiment_id == experiment_id)
            ).first()
            if experiment:
                for key, value in kwargs.items():
                    if hasattr(experiment, key):
                        setattr(experiment, key, value)
                session.commit()

    # Narrative methods
    def create_narrative(self, narrative_data: Dict[str, Any]) -> int:
        """Create a new narrative and return its ID."""
        with self.get_session() as session:
            max_id = session.exec(select(func.max(Narrative.narrative_id))).first() or 0
            next_id = max_id + 1

            narrative = Narrative(
                narrative_id=next_id,
                narrative=narrative_data.get("narrative"),
                owner_id=narrative_data["owner_id"],
            )
            session.add(narrative)
            session.commit()
            session.refresh(narrative)
            return int(narrative.narrative_id)

    def get_narratives(self) -> List[Narrative]:
        """Get all narratives from the database."""
        with self.get_session() as session:
            return list(session.exec(select(Narrative)))

    def get_narrative_by_id(self, narrative_id: int) -> Optional[Narrative]:
        """Get a specific narrative by ID."""
        with self.get_session() as session:
            return session.exec(select(Narrative).where(Narrative.narrative_id == narrative_id)).first()

    def get_narratives_by_owner(self, owner_id: int) -> List[Narrative]:
        """Return all narratives created by a specific user."""
        with self.get_session() as session:
            return list(session.exec(select(Narrative).where(Narrative.owner_id == owner_id)))

    def get_last_narrative_for_group(self, group_id: int) -> Optional[Narrative]:
        """Return the most recent narrative used in a given experiment group."""
        with self.get_session() as session:
            exp = session.exec(
                select(ExperimentList)
                .where(ExperimentList.experiments_group_id == group_id)
                .order_by(ExperimentList.experiment_id.desc())
            ).first()
            if not exp or exp.narrative_id is None:
                return None
            return session.exec(select(Narrative).where(Narrative.narrative_id == exp.narrative_id)).first()

    def save_questionnaire_result(self, questionnaire_data: Dict[str, Any]) -> int:
        """Save a questionnaire run and return its ID."""
        questionnaire = Questionnaire(**questionnaire_data)
        with self.get_session() as session:
            session.add(questionnaire)
            session.commit()
            session.refresh(questionnaire)
            return int(questionnaire.id) if questionnaire.id is not None else -1

    def save_evaluation_result(self, result_data: Dict[str, Any]) -> int:
        """Persist a processed evaluation result and return its ID."""
        evaluation = EvaluationResult(**result_data)
        with self.get_session() as session:
            session.add(evaluation)
            session.commit()
            session.refresh(evaluation)
            return int(evaluation.id) if evaluation.id is not None else -1

    # Assessment feedback
    def get_assessment_feedback(
        self, experiment_id: int, user_id: Optional[int] = None
    ) -> Optional[AssessmentFeedback]:
        """Return assessment feedback for a given experiment and user."""
        with self.get_session() as session:
            query = select(AssessmentFeedback).where(AssessmentFeedback.experiment_id == experiment_id)
            if user_id is not None:
                query = query.where(AssessmentFeedback.user_id == user_id)
            return session.exec(query).first()

    def save_assessment_feedback(self, feedback_data: Dict[str, Any]) -> int:
        """Insert or update feedback about an assessment result."""
        with self.get_session() as session:
            existing = session.exec(
                select(AssessmentFeedback).where(AssessmentFeedback.experiment_id == feedback_data["experiment_id"])
            ).first()

            if existing:
                for key, value in feedback_data.items():
                    if key in {"id", "created"}:
                        continue
                    setattr(existing, key, value)
                session.add(existing)
                session.commit()
                session.refresh(existing)
                return int(existing.id) if existing.id is not None else -1

            feedback = AssessmentFeedback(**feedback_data)
            session.add(feedback)
            session.commit()
            session.refresh(feedback)
            return int(feedback.id) if feedback.id is not None else -1

    # Questionnaire feedback
    def get_questionnaire_feedback(
        self, questionnaire_id: int, user_id: Optional[int] = None
    ) -> Optional[QuestionnaireFeedback]:
        """Return questionnaire feedback for a given questionnaire and user."""
        with self.get_session() as session:
            query = select(QuestionnaireFeedback).where(QuestionnaireFeedback.questionnaire_id == questionnaire_id)
            if user_id is not None:
                query = query.where(QuestionnaireFeedback.user_id == user_id)
            return session.exec(query).first()

    def save_questionnaire_feedback(self, feedback_data: Dict[str, Any]) -> int:
        """Insert or update feedback about a questionnaire result."""
        with self.get_session() as session:
            existing = session.exec(
                select(QuestionnaireFeedback).where(
                    QuestionnaireFeedback.questionnaire_id == feedback_data["questionnaire_id"],
                    QuestionnaireFeedback.user_id == feedback_data["user_id"],
                )
            ).first()

            if existing:
                for key, value in feedback_data.items():
                    if key in {"id", "created"}:
                        continue
                    setattr(existing, key, value)
                session.add(existing)
                session.commit()
                session.refresh(existing)
                return int(existing.id) if existing.id is not None else -1

            feedback = QuestionnaireFeedback(**feedback_data)
            session.add(feedback)
            session.commit()
            session.refresh(feedback)
            return int(feedback.id) if feedback.id is not None else -1

    # Request/Response logging
    def save_request_response(self, experiment_id: int, request_json: Dict, response_json: Dict) -> RequestResponse:
        """Save request and response data."""
        req_resp = RequestResponse(experiment_id=experiment_id, request_json=request_json, response_json=response_json)
        with self.get_session() as session:
            session.add(req_resp)
            session.commit()
            session.refresh(req_resp)
        return req_resp

    # User prompt persistence methods
    def save_user_prompt(
        self,
        user_id: int,
        prompt_name: str,
        prompt_template: str,
        prompt_description: Optional[str] = None,
        category: str = "custom",
        is_current: bool = False,
    ) -> int:
        """Save a user prompt to the database."""
        with self.get_session() as session:
            # Check if prompt name already exists for this user
            existing = session.exec(
                select(UserPrompt).where(UserPrompt.user_id == user_id, UserPrompt.prompt_name == prompt_name)
            ).first()

            if existing:
                # Update existing prompt
                existing.prompt_template = prompt_template
                existing.prompt_description = prompt_description
                existing.category = category
                existing.is_current = is_current
                existing.updated_at = datetime.now(timezone.utc)
                prompt_id = int(existing.id) if existing.id is not None else -1
            else:
                # Create new prompt
                new_prompt = UserPrompt(
                    user_id=user_id,
                    prompt_name=prompt_name,
                    prompt_description=prompt_description,
                    prompt_template=prompt_template,
                    category=category,
                    is_current=is_current,
                )
                session.add(new_prompt)
                session.flush()  # To get the ID
                prompt_id = int(new_prompt.id) if new_prompt.id is not None else -1

            # If setting as current, unset all other prompts for this user
            if is_current:
                others = session.exec(
                    select(UserPrompt).where(UserPrompt.user_id == user_id, UserPrompt.id != prompt_id)
                ).all()
                for other in others:
                    other.is_current = False

            session.commit()
            return prompt_id

    def get_user_current_prompt(self, user_id: int) -> Optional[str]:
        """Get the current prompt for a user."""
        with self.get_session() as session:
            current_prompt = session.exec(
                select(UserPrompt).where(
                    UserPrompt.user_id == user_id,
                    UserPrompt.is_current.is_(True),
                )
            ).first()

            return current_prompt.prompt_template if current_prompt else None

    def get_user_prompts(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all prompts for a user."""
        with self.get_session() as session:
            prompts = list(session.exec(select(UserPrompt).where(UserPrompt.user_id == user_id)))
            # Sort in Python to avoid column access issues
            prompts.sort(key=lambda p: p.created_at, reverse=True)

            return [
                {
                    "id": prompt.id,
                    "name": prompt.prompt_name,
                    "description": prompt.prompt_description,
                    "template": prompt.prompt_template,
                    "category": prompt.category,
                    "is_current": prompt.is_current,
                    "created": prompt.created_at.isoformat() if prompt.created_at else None,
                }
                for prompt in prompts
            ]

    def set_user_current_prompt(self, user_id: int, prompt_id: int) -> bool:
        """Set a prompt as the current prompt for a user."""
        with self.get_session() as session:
            # Load all prompts for user and toggle is_current flags
            prompts = session.exec(select(UserPrompt).where(UserPrompt.user_id == user_id)).all()
            found = False
            for p in prompts:
                if p.id == prompt_id:
                    p.is_current = True
                    found = True
                else:
                    p.is_current = False
            session.commit()
            return found

    def delete_user_prompt(self, user_id: int, prompt_id: int) -> bool:
        """Delete a user prompt."""
        with self.get_session() as session:
            prompt = session.exec(
                select(UserPrompt).where(UserPrompt.user_id == user_id, UserPrompt.id == prompt_id)
            ).first()
            if not prompt:
                return False
            session.delete(prompt)
            session.commit()
            return True

    def assign_group_to_user(self, group_id: int, user_id: int) -> bool:
        """Assign a user to an experiment group."""
        try:
            with self.get_session() as session:
                # Check if assignment already exists
                existing = session.exec(
                    select(ExperimentGroupUser).where(
                        ExperimentGroupUser.experiments_group_id == group_id, ExperimentGroupUser.user_id == user_id
                    )
                ).first()

                if existing:
                    return True  # Already assigned

                # Create new assignment
                assignment = ExperimentGroupUser(experiments_group_id=group_id, user_id=user_id)
                session.add(assignment)
                session.commit()
                return True
        except Exception:
            return False

    def is_user_in_experiment_group(self, user_id: int, group_id: int) -> bool:
        """Check if a user is assigned to an experiment group."""
        with self.get_session() as session:
            assignment = session.exec(
                select(ExperimentGroupUser).where(
                    ExperimentGroupUser.experiments_group_id == group_id, ExperimentGroupUser.user_id == user_id
                )
            ).first()
            return assignment is not None

    def get_experiments_by_group(self, group_id: int) -> List[ExperimentList]:
        """Return all experiments for a given experiment group."""
        with self.get_session() as session:
            return list(session.exec(select(ExperimentList).where(ExperimentList.experiments_group_id == group_id)))

    def get_questionnaires_by_group(self, group_id: int) -> List[Questionnaire]:
        """Return all questionnaires for a given experiment group."""
        with self.get_session() as session:
            return list(session.exec(select(Questionnaire).where(Questionnaire.experiments_group_id == group_id)))

    def get_evaluation_results_by_group(self, group_id: int) -> List[EvaluationResult]:
        """Return all evaluation results for a given experiment group."""
        with self.get_session() as session:
            return list(session.exec(select(EvaluationResult).where(EvaluationResult.experiments_group_id == group_id)))

    def can_user_edit_experiment_group(self, user_id: int, group_id: int) -> bool:
        """Check if a user can edit an experiment group. Allows admins, owners, and assigned users."""
        with self.get_session() as session:
            # Get the experiment group
            group = session.exec(
                select(ExperimentGroup).where(ExperimentGroup.experiments_group_id == group_id)
            ).first()

            if not group:
                return False

            # Check if user is admin
            if self.is_user_admin(user_id):
                return True

            # Check if user is owner
            if group.owner_id == user_id:
                return True

            # Check if user is assigned to this experiment group
            assignment = session.exec(
                select(ExperimentGroupUser).where(
                    ExperimentGroupUser.experiments_group_id == group_id, ExperimentGroupUser.user_id == user_id
                )
            ).first()

            return assignment is not None

    def get_batch_results_summary(self, group_id: int) -> Dict[str, Any]:
        """
        Get a comprehensive summary of batch processing results for an experiment group.
        
        This method retrieves all dimension evaluations, questionnaire results, and 
        computed scores for post-processing analysis. Designed for use with batch
        processing results and analysis notebooks.
        
        Args:
            group_id: The experiment group ID to retrieve results for
            
        Returns:
            Dictionary containing:
            - 'group_info': ExperimentGroup metadata
            - 'narratives': List of narrative data with all evaluation results
            - 'summary_stats': Aggregate statistics
        """
        with self.get_session() as session:
            # Get group info
            group = session.exec(
                select(ExperimentGroup).where(ExperimentGroup.experiments_group_id == group_id)
            ).first()
            
            if not group:
                return {"error": f"Group {group_id} not found"}
            
            # Get all experiments for this group
            experiments = session.exec(
                select(ExperimentList).where(ExperimentList.experiments_group_id == group_id)
            ).all()
            
            # Get all evaluation results
            eval_results = session.exec(
                select(EvaluationResult).where(EvaluationResult.experiments_group_id == group_id)
            ).all()
            
            # Get all questionnaires
            questionnaires = session.exec(
                select(Questionnaire).where(Questionnaire.experiments_group_id == group_id)
            ).all()
            
            # Build narrative-centric results
            narratives_data = []
            narrative_ids = set(exp.narrative_id for exp in experiments if exp.narrative_id)
            
            for narrative_id in narrative_ids:
                narrative = session.exec(
                    select(Narrative).where(Narrative.narrative_id == narrative_id)
                ).first()
                
                if not narrative:
                    continue
                
                # Get experiment for this narrative
                exp = next(
                    (e for e in experiments if e.narrative_id == narrative_id),
                    None
                )
                
                # Get evaluation results for this narrative
                narrative_evals = [
                    er for er in eval_results if er.narrative_id == narrative_id
                ]
                
                # Extract dimension results
                dim_result = next(
                    (er.result_json for er in narrative_evals if er.result_type == "dimensions"),
                    None
                )
                
                # Get questionnaire results
                pcs_result = next(
                    (er.result_json for er in narrative_evals if er.result_type == "PCS"),
                    None
                )
                bpi_is_result = next(
                    (er.result_json for er in narrative_evals if er.result_type == "BPI-IS"),
                    None
                )
                tsk_result = next(
                    (er.result_json for er in narrative_evals if er.result_type == "TSK-11SV"),
                    None
                )
                
                narratives_data.append({
                    "narrative_id": narrative_id,
                    "narrative_text": narrative.narrative,
                    "experiment_id": exp.experiment_id if exp else None,
                    "succeeded": exp.succeeded if exp else False,
                    "dimension_result": dim_result,
                    "pcs_result": pcs_result,
                    "bpi_is_result": bpi_is_result,
                    "tsk_11sv_result": tsk_result,
                })
            
            # Calculate summary statistics
            total_narratives = len(narratives_data)
            successful_dims = sum(1 for n in narratives_data if n["dimension_result"] and "error" not in n["dimension_result"])
            successful_pcs = sum(1 for n in narratives_data if n["pcs_result"])
            successful_bpi_is = sum(1 for n in narratives_data if n["bpi_is_result"])
            successful_tsk = sum(1 for n in narratives_data if n["tsk_11sv_result"])
            
            return {
                "group_info": {
                    "group_id": group_id,
                    "description": group.description,
                    "created": group.created.isoformat() if group.created else None,
                    "concluded": group.concluded,
                    "owner_id": group.owner_id,
                },
                "narratives": narratives_data,
                "summary_stats": {
                    "total_narratives": total_narratives,
                    "successful_dimensions": successful_dims,
                    "successful_pcs": successful_pcs,
                    "successful_bpi_is": successful_bpi_is,
                    "successful_tsk_11sv": successful_tsk,
                },
            }


# Singleton database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_database_manager() -> DatabaseManager:
    """Get the singleton database manager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager
