"""
SQLModel models for pain_narratives_app schema (full migration).
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, Relationship, SQLModel

SCHEMA_NAME = "pain_narratives_app"


class Narrative(SQLModel, table=True):
    __tablename__ = "narratives"  # type: ignore
    __table_args__ = {"schema": SCHEMA_NAME}

    narrative_id: int = Field(primary_key=True)
    narrative: Optional[str] = None
    owner_id: int = Field(foreign_key=f"{SCHEMA_NAME}.users.id")

    # Deduplication fields (added via migration add_narrative_deduplication.py)
    narrative_hash: Optional[str] = Field(default=None, max_length=64)
    word_count: Optional[int] = Field(default=None)
    char_count: Optional[int] = Field(default=None)

    experiments: List["ExperimentList"] = Relationship(back_populates="narrative")
    owner: Optional["User"] = Relationship(back_populates="narratives")
    evaluation_results: List["EvaluationResult"] = Relationship(back_populates="narrative")
    feedback_entries: List["AssessmentFeedback"] = Relationship(back_populates="narrative")
    questionnaire_feedback_entries: List["QuestionnaireFeedback"] = Relationship(back_populates="narrative")


class ExperimentGroup(SQLModel, table=True):
    __tablename__ = "experiments_groups"  # type: ignore
    __table_args__ = {"schema": SCHEMA_NAME}

    experiments_group_id: Optional[int] = Field(default=None, primary_key=True)
    created: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)
    description: Optional[str] = None
    system_role: Optional[str] = None
    base_prompt: Optional[str] = None
    dimensions: Optional[List[Dict[str, Any]]] = Field(default=None, sa_column=Column(JSON))
    concluded: bool = Field(default=False, nullable=False)
    processed: bool = Field(default=False, nullable=False)
    owner_id: int = Field(foreign_key=f"{SCHEMA_NAME}.users.id")

    owner: Optional["User"] = Relationship(back_populates="experiments_groups")
    experiments: List["ExperimentList"] = Relationship(back_populates="group")
    users: List["ExperimentGroupUser"] = Relationship(back_populates="group")
    questionnaires: List["Questionnaire"] = Relationship(back_populates="group")
    evaluation_results: List["EvaluationResult"] = Relationship(back_populates="group")
    questionnaire_prompts: List["QuestionnairePrompt"] = Relationship(back_populates="group")
    feedback_entries: List["AssessmentFeedback"] = Relationship(back_populates="group")
    questionnaire_feedback_entries: List["QuestionnaireFeedback"] = Relationship(back_populates="group")


class ExperimentList(SQLModel, table=True):
    __tablename__ = "experiments_list"  # type: ignore
    __table_args__ = {"schema": SCHEMA_NAME}

    experiment_id: Optional[int] = Field(default=None, primary_key=True)
    experiments_group_id: Optional[int] = Field(foreign_key=f"{SCHEMA_NAME}.experiments_groups.experiments_group_id")
    user_id: int = Field(foreign_key=f"{SCHEMA_NAME}.users.id")
    repeated: Optional[int] = None
    created: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)
    language_instructions: Optional[str] = None
    model_provider: Optional[str] = None
    model: Optional[str] = None
    with_context: Optional[bool] = None
    narrative_id: Optional[int] = Field(foreign_key=f"{SCHEMA_NAME}.narratives.narrative_id")
    succeeded: bool = Field(default=False, nullable=False)
    parsed_answers: bool = Field(default=False, nullable=False)
    calculated_metrics: bool = Field(default=False, nullable=False)
    extra_description: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    repo_sha: str
    exp_type: str = Field(default="aut", nullable=False)

    group: Optional["ExperimentGroup"] = Relationship(back_populates="experiments")
    narrative: Optional["Narrative"] = Relationship(back_populates="experiments")
    request_responses: List["RequestResponse"] = Relationship(back_populates="experiment")
    questionnaires: List["Questionnaire"] = Relationship(back_populates="experiment")
    user: Optional["User"] = Relationship(back_populates="experiments")
    evaluation_results: List["EvaluationResult"] = Relationship(back_populates="experiment")
    feedback_entries: List["AssessmentFeedback"] = Relationship(back_populates="experiment")
    questionnaire_feedback_entries: List["QuestionnaireFeedback"] = Relationship(back_populates="experiment")


class RequestResponse(SQLModel, table=True):
    __tablename__ = "request_response"  # type: ignore
    __table_args__ = {"schema": SCHEMA_NAME}

    id: Optional[int] = Field(default=None, primary_key=True)
    created: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)
    experiment_id: Optional[int] = Field(foreign_key=f"{SCHEMA_NAME}.experiments_list.experiment_id")
    request_json: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    response_json: Optional[dict] = Field(default=None, sa_column=Column(JSON))

    experiment: Optional["ExperimentList"] = Relationship(back_populates="request_responses")


class ExperimentGroupUser(SQLModel, table=True):
    __tablename__ = "experiment_group_users"  # type: ignore
    __table_args__ = {"schema": SCHEMA_NAME}

    id: Optional[int] = Field(default=None, primary_key=True)
    experiments_group_id: int = Field(foreign_key=f"{SCHEMA_NAME}.experiments_groups.experiments_group_id")
    user_id: int = Field(foreign_key=f"{SCHEMA_NAME}.users.id")

    group: Optional["ExperimentGroup"] = Relationship(back_populates="users")
    user: Optional["User"] = Relationship(back_populates="experiment_group_links")


class User(SQLModel, table=True):
    __tablename__ = "users"  # type: ignore
    __table_args__ = {"schema": SCHEMA_NAME}

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, nullable=False, max_length=255)
    hashed_password: str = Field(nullable=False, max_length=255)
    is_admin: bool = Field(default=False, nullable=False)
    preferred_language: str = Field(default="en", nullable=False, max_length=10)

    experiments_groups: List["ExperimentGroup"] = Relationship(back_populates="owner")
    prompts: List["UserPrompt"] = Relationship(back_populates="user")
    experiment_group_links: List["ExperimentGroupUser"] = Relationship(back_populates="user")
    narratives: List["Narrative"] = Relationship(back_populates="owner")
    experiments: List["ExperimentList"] = Relationship(back_populates="user")
    questionnaires: List["Questionnaire"] = Relationship(back_populates="user")
    evaluation_results: List["EvaluationResult"] = Relationship(back_populates="user")
    feedback_entries: List["AssessmentFeedback"] = Relationship(back_populates="user")
    questionnaire_feedback_entries: List["QuestionnaireFeedback"] = Relationship(back_populates="user")


class UserPrompt(SQLModel, table=True):
    # DEPRECATED: This model/table is currently not used by the Streamlit UI and has 0 rows in production.
    # It is retained for backward compatibility with CLI scripts/tests and potential future per-user prompts.
    # If fully removing in the future, also remove related DatabaseManager methods and tests/test_user_prompt_current.py.
    __tablename__ = "user_prompts"  # type: ignore
    __table_args__ = {"schema": SCHEMA_NAME}

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key=f"{SCHEMA_NAME}.users.id")
    prompt_name: str = Field(nullable=False, max_length=255)
    prompt_description: Optional[str] = None
    prompt_template: str = Field(nullable=False)
    category: str = Field(default="custom", nullable=False, max_length=100)
    is_current: bool = Field(default=False, nullable=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)

    user: Optional[User] = Relationship(back_populates="prompts")


class QuestionnairePrompt(SQLModel, table=True):
    """Store custom questionnaire prompts and system roles for experiment groups."""
    
    __tablename__ = "questionnaire_prompts"  # type: ignore
    __table_args__ = {"schema": SCHEMA_NAME}

    id: Optional[int] = Field(default=None, primary_key=True)
    experiments_group_id: int = Field(foreign_key=f"{SCHEMA_NAME}.experiments_groups.experiments_group_id")
    questionnaire_type: str = Field(nullable=False, max_length=50)  # 'PCS', 'BPI-IS', 'TSK-11SV'
    system_role: str = Field(nullable=False)
    instructions: str = Field(nullable=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)

    group: Optional[ExperimentGroup] = Relationship()


class Questionnaire(SQLModel, table=True):
    """Store questionnaire runs associated with experiments."""

    __tablename__ = "questionnaires"  # type: ignore
    __table_args__ = {"schema": SCHEMA_NAME}

    id: Optional[int] = Field(default=None, primary_key=True)
    experiment_id: Optional[int] = Field(foreign_key=f"{SCHEMA_NAME}.experiments_list.experiment_id")
    experiments_group_id: int = Field(foreign_key=f"{SCHEMA_NAME}.experiments_groups.experiments_group_id")
    narrative_id: int = Field(foreign_key=f"{SCHEMA_NAME}.narratives.narrative_id")
    user_id: int = Field(foreign_key=f"{SCHEMA_NAME}.users.id")
    questionnaire_name: str
    prompt: str
    created: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)
    result_json: Optional[dict] = Field(default=None, sa_column=Column(JSON))

    experiment: Optional[ExperimentList] = Relationship(back_populates="questionnaires")
    group: Optional[ExperimentGroup] = Relationship(back_populates="questionnaires")
    narrative: Optional[Narrative] = Relationship()
    user: Optional[User] = Relationship(back_populates="questionnaires")
    evaluation_results: List["EvaluationResult"] = Relationship(back_populates="questionnaire")
    feedback_entries: List["QuestionnaireFeedback"] = Relationship(back_populates="questionnaire")


class EvaluationResult(SQLModel, table=True):
    """Persist processed results from evaluations and questionnaires."""

    __tablename__ = "evaluation_results"  # type: ignore
    __table_args__ = {"schema": SCHEMA_NAME}

    id: Optional[int] = Field(default=None, primary_key=True)
    experiment_id: Optional[int] = Field(foreign_key=f"{SCHEMA_NAME}.experiments_list.experiment_id")
    questionnaire_id: Optional[int] = Field(foreign_key=f"{SCHEMA_NAME}.questionnaires.id")
    experiments_group_id: int = Field(foreign_key=f"{SCHEMA_NAME}.experiments_groups.experiments_group_id")
    narrative_id: int = Field(foreign_key=f"{SCHEMA_NAME}.narratives.narrative_id")
    user_id: int = Field(foreign_key=f"{SCHEMA_NAME}.users.id")
    result_type: str = Field(max_length=50)
    result_json: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    created: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)

    experiment: Optional[ExperimentList] = Relationship(back_populates="evaluation_results")
    questionnaire: Optional[Questionnaire] = Relationship(back_populates="evaluation_results")
    group: Optional[ExperimentGroup] = Relationship(back_populates="evaluation_results")
    narrative: Optional[Narrative] = Relationship(back_populates="evaluation_results")
    user: Optional[User] = Relationship(back_populates="evaluation_results")


class AssessmentFeedback(SQLModel, table=True):
    """Store clinician feedback about assessment scores and explanations."""

    __tablename__ = "assessment_feedback"  # type: ignore
    __table_args__ = {"schema": SCHEMA_NAME}

    id: Optional[int] = Field(default=None, primary_key=True)
    experiment_id: int = Field(foreign_key=f"{SCHEMA_NAME}.experiments_list.experiment_id")
    experiments_group_id: int = Field(foreign_key=f"{SCHEMA_NAME}.experiments_groups.experiments_group_id")
    user_id: int = Field(foreign_key=f"{SCHEMA_NAME}.users.id")
    narrative_id: Optional[int] = Field(default=None, foreign_key=f"{SCHEMA_NAME}.narratives.narrative_id")
    intensity_score_alignment: str = Field(max_length=64)
    intensity_explanation_alignment: str = Field(max_length=64)
    intensity_usage_intent: str = Field(max_length=64)
    disability_score_alignment: str = Field(max_length=64)
    disability_explanation_alignment: str = Field(max_length=64)
    disability_usage_intent: str = Field(max_length=64)
    dimension_feedback: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    created: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)

    experiment: Optional[ExperimentList] = Relationship(back_populates="feedback_entries")
    group: Optional[ExperimentGroup] = Relationship(back_populates="feedback_entries")
    user: Optional[User] = Relationship(back_populates="feedback_entries")
    narrative: Optional[Narrative] = Relationship(back_populates="feedback_entries")


class QuestionnaireFeedback(SQLModel, table=True):
    """Store expert feedback about questionnaire results and reasoning."""

    __tablename__ = "questionnaire_feedback"  # type: ignore
    __table_args__ = {"schema": SCHEMA_NAME}

    id: Optional[int] = Field(default=None, primary_key=True)
    questionnaire_id: int = Field(foreign_key=f"{SCHEMA_NAME}.questionnaires.id")
    experiment_id: Optional[int] = Field(default=None, foreign_key=f"{SCHEMA_NAME}.experiments_list.experiment_id")
    experiments_group_id: int = Field(foreign_key=f"{SCHEMA_NAME}.experiments_groups.experiments_group_id")
    user_id: int = Field(foreign_key=f"{SCHEMA_NAME}.users.id")
    narrative_id: Optional[int] = Field(default=None, foreign_key=f"{SCHEMA_NAME}.narratives.narrative_id")
    questionnaire_name: str = Field(max_length=100)  # PCS, BPI-IS, TSK-11SV, etc.
    authenticity_rating: str = Field(max_length=64)  # Could questionnaire be answered by narrative author?
    reasoning_adequacy_rating: str = Field(max_length=64)  # Does model reasoning justify answers?
    created: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)

    questionnaire: Optional[Questionnaire] = Relationship(back_populates="feedback_entries")
    experiment: Optional[ExperimentList] = Relationship(back_populates="questionnaire_feedback_entries")
    group: Optional[ExperimentGroup] = Relationship(back_populates="questionnaire_feedback_entries")
    user: Optional[User] = Relationship(back_populates="questionnaire_feedback_entries")
    narrative: Optional[Narrative] = Relationship(back_populates="questionnaire_feedback_entries")
