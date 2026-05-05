"""
SQLModel models for pain_narratives_acm_202512 schema.

This module defines the data models for the ACM 202512 publication schema,
containing real patient data, expert evaluations, and LLM synthetic data.

Tables:
- Real patient data: demographics, PCS, BPI, TSK, and master data
- Expert users and their feedback: dimension evaluation, questionnaire feedback
- LLM synthetic results: dimension evaluation, PCS, BPI, TSK
"""

from typing import Optional

from sqlmodel import Field, SQLModel

SCHEMA_NAME = "pain_narratives_acm_202512"


# =============================================================================
# Real Patient Data Tables
# =============================================================================


class RealPatientDemographics(SQLModel, table=True):
    """Demographics and narrative data for real chronic pain patients."""

    __tablename__ = "real_patient_demographics"  # type: ignore
    __table_args__ = {"schema": SCHEMA_NAME}

    participant_id: int = Field(primary_key=True)
    narrative_hash: Optional[str] = Field(default=None, max_length=64)
    narrative_text: Optional[str] = None
    word_count: Optional[int] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    marital_status: Optional[str] = None
    education_level: Optional[str] = None
    country_residence: Optional[str] = None
    country_birth: Optional[str] = None
    employment_status: Optional[str] = None
    years_with_pain: Optional[str] = None
    years_since_diagnosis: Optional[str] = None
    pain_cause_primary: Optional[str] = None
    pain_location_zones: Optional[str] = None


class RealPatientPCS(SQLModel, table=True):
    """Pain Catastrophizing Scale (PCS) responses from real patients.

    PCS measures catastrophic thinking about pain across 13 items,
    with subscales for rumination, magnification, and helplessness.
    """

    __tablename__ = "real_patient_pcs"  # type: ignore
    __table_args__ = {"schema": SCHEMA_NAME}

    participant_id: int = Field(primary_key=True)
    # Individual items (0-4 scale)
    pcs_01: Optional[int] = None
    pcs_02: Optional[int] = None
    pcs_03: Optional[int] = None
    pcs_04: Optional[int] = None
    pcs_05: Optional[int] = None
    pcs_06: Optional[int] = None
    pcs_07: Optional[int] = None
    pcs_08: Optional[int] = None
    pcs_09: Optional[int] = None
    pcs_10: Optional[int] = None
    pcs_11: Optional[int] = None
    pcs_12: Optional[int] = None
    pcs_13: Optional[int] = None
    # Subscales and total
    pcs_total: Optional[int] = None  # Sum of all items (0-52)
    pcs_rumination: Optional[int] = None  # Items 8, 9, 10, 11
    pcs_magnification: Optional[int] = None  # Items 6, 7, 13
    pcs_helplessness: Optional[int] = None  # Items 1, 2, 3, 4, 5, 12


class RealPatientBPI(SQLModel, table=True):
    """Brief Pain Inventory - Interference Scale (BPI-IS) responses from real patients.

    BPI measures pain intensity and interference with daily activities.
    """

    __tablename__ = "real_patient_bpi"  # type: ignore
    __table_args__ = {"schema": SCHEMA_NAME}

    participant_id: int = Field(primary_key=True)
    # Individual items (0-10 scale)
    # Intensity items (Q1.1-Q1.7): current, worst, least, average pain + relief
    bpiq11: Optional[int] = None
    bpiq12: Optional[int] = None
    bpiq13: Optional[int] = None
    bpiq14: Optional[int] = None
    bpiq15: Optional[int] = None
    bpiq16: Optional[int] = None
    bpiq17: Optional[int] = None
    # Interference items (Q2.8-Q5.11): activity, mood, walking, work, etc.
    bpiq28: Optional[int] = None
    bpiq39: Optional[int] = None
    bpiq410: Optional[int] = None
    bpiq511: Optional[int] = None
    # Subscale means
    bpi_interference_mean: Optional[float] = None
    bpi_intensity_mean: Optional[float] = None
    bpi_total_mean: Optional[float] = None


class RealPatientTSK(SQLModel, table=True):
    """Tampa Scale for Kinesiophobia (TSK-11SV) responses from real patients.

    TSK measures fear of movement and (re)injury in chronic pain patients.
    """

    __tablename__ = "real_patient_tsk"  # type: ignore
    __table_args__ = {"schema": SCHEMA_NAME}

    participant_id: int = Field(primary_key=True)
    # Individual items (1-4 scale)
    tsk_01: Optional[int] = None
    tsk_02: Optional[int] = None
    tsk_03: Optional[int] = None
    tsk_04: Optional[int] = None
    tsk_05: Optional[int] = None
    tsk_06: Optional[int] = None
    tsk_07: Optional[int] = None
    tsk_08: Optional[int] = None
    tsk_09: Optional[int] = None
    tsk_10: Optional[int] = None
    tsk_11: Optional[int] = None
    # Total score
    tsk_total: Optional[int] = None  # Sum of all items (11-44)


class RealPatientMasterData(SQLModel, table=True):
    """Consolidated master data combining demographics and all questionnaire responses.

    This denormalized view contains all patient data in a single table for
    convenient analysis and export.
    """

    __tablename__ = "real_patient_master_data"  # type: ignore
    __table_args__ = {"schema": SCHEMA_NAME}

    participant_id: int = Field(primary_key=True)
    # Demographics
    narrative_text: Optional[str] = None
    narrative_hash: Optional[str] = Field(default=None, max_length=64)
    word_count: Optional[int] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    marital_status: Optional[str] = None
    education_level: Optional[str] = None
    country_residence: Optional[str] = None
    country_birth: Optional[str] = None
    employment_status: Optional[str] = None
    years_with_pain: Optional[str] = None
    years_since_diagnosis: Optional[str] = None
    pain_cause_primary: Optional[str] = None
    pain_location_zones: Optional[str] = None
    # PCS items and subscales
    pcs_01: Optional[int] = None
    pcs_02: Optional[int] = None
    pcs_03: Optional[int] = None
    pcs_04: Optional[int] = None
    pcs_05: Optional[int] = None
    pcs_06: Optional[int] = None
    pcs_07: Optional[int] = None
    pcs_08: Optional[int] = None
    pcs_09: Optional[int] = None
    pcs_10: Optional[int] = None
    pcs_11: Optional[int] = None
    pcs_12: Optional[int] = None
    pcs_13: Optional[int] = None
    # BPI items
    bpiq11: Optional[int] = None
    bpiq12: Optional[int] = None
    bpiq13: Optional[int] = None
    bpiq14: Optional[int] = None
    bpiq15: Optional[int] = None
    bpiq16: Optional[int] = None
    bpiq17: Optional[int] = None
    bpiq28: Optional[int] = None
    bpiq39: Optional[int] = None
    bpiq410: Optional[int] = None
    bpiq511: Optional[int] = None
    # TSK items
    tsk_01: Optional[int] = None
    tsk_02: Optional[int] = None
    tsk_03: Optional[int] = None
    tsk_04: Optional[int] = None
    tsk_05: Optional[int] = None
    tsk_06: Optional[int] = None
    tsk_07: Optional[int] = None
    tsk_08: Optional[int] = None
    tsk_09: Optional[int] = None
    tsk_10: Optional[int] = None
    tsk_11: Optional[int] = None
    # Computed scores
    pcs_total: Optional[int] = None
    pcs_rumination: Optional[int] = None
    pcs_magnification: Optional[int] = None
    pcs_helplessness: Optional[int] = None
    bpi_interference_mean: Optional[float] = None
    bpi_intensity_mean: Optional[float] = None
    bpi_total_mean: Optional[float] = None
    tsk_total: Optional[int] = None


# =============================================================================
# Expert User and Feedback Tables
# =============================================================================


class ExpertUser(SQLModel, table=True):
    """Expert users (clinicians/researchers) who provide feedback on assessments."""

    __tablename__ = "expert_users"  # type: ignore
    __table_args__ = {"schema": SCHEMA_NAME}

    user_id: int = Field(primary_key=True)
    username: Optional[str] = None
    is_admin: Optional[bool] = Field(default=False)
    preferred_language: Optional[str] = None
    evaluation_completed: Optional[bool] = Field(default=False)
    # Assigned narratives for evaluation
    assigned_narrative_01: Optional[int] = None
    assigned_narrative_02: Optional[int] = None
    assigned_narrative_03: Optional[float] = None  # Float due to possible NaN handling
    assigned_narrative_hash_01: Optional[str] = None
    assigned_narrative_hash_02: Optional[str] = None
    assigned_narrative_hash_03: Optional[str] = None


class ExpertDimensionEvaluation(SQLModel, table=True):
    """Expert feedback on LLM dimension evaluation (severity, disability, etc.).

    Contains alignment ratings for each dimension's score, explanation, and usage intent.
    """

    __tablename__ = "expert_dimension_evaluation"  # type: ignore
    __table_args__ = {"schema": SCHEMA_NAME}

    # Identifiers
    participant_id: Optional[float] = None  # Float due to pandas handling
    narrative_id: Optional[int] = None
    narrative_hash: Optional[str] = None
    experiments_group_id: Optional[int] = None
    experiment_id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = None
    word_count: Optional[int] = None

    # Core dimensions: Severidad (severity), Discapacidad (disability)
    severidad_score_alignment: Optional[str] = None
    severidad_explanation_alignment: Optional[str] = None
    severidad_usage_intent: Optional[str] = None
    discapacidad_score_alignment: Optional[str] = None
    discapacidad_explanation_alignment: Optional[str] = None
    discapacidad_usage_intent: Optional[str] = None

    # Extended dimensions
    catastrofizacion_score_alignment: Optional[str] = Field(
        default=None, sa_column_kwargs={"name": "catastrofización_score_alignment"}
    )
    catastrofizacion_explanation_alignment: Optional[str] = Field(
        default=None, sa_column_kwargs={"name": "catastrofización_explanation_alignment"}
    )
    catastrofizacion_usage_intent: Optional[str] = Field(
        default=None, sa_column_kwargs={"name": "catastrofización_usage_intent"}
    )
    flexibilidad_score_alignment: Optional[str] = None
    flexibilidad_explanation_alignment: Optional[str] = None
    flexibilidad_usage_intent: Optional[str] = None
    estigma_percibido_score_alignment: Optional[str] = None
    estigma_percibido_explanation_alignment: Optional[str] = None
    estigma_percibido_usage_intent: Optional[str] = None
    injusticia_percibida_score_alignment: Optional[str] = None
    injusticia_percibida_explanation_alignment: Optional[str] = None
    injusticia_percibida_usage_intent: Optional[str] = None
    fatiga_score_alignment: Optional[str] = None
    fatiga_explanation_alignment: Optional[str] = None
    fatiga_usage_intent: Optional[str] = None
    estado_de_animo_score_alignment: Optional[str] = Field(
        default=None, sa_column_kwargs={"name": "estado_de_ánimo_score_alignment"}
    )
    estado_de_animo_explanation_alignment: Optional[str] = Field(
        default=None, sa_column_kwargs={"name": "estado_de_ánimo_explanation_alignment"}
    )
    estado_de_animo_usage_intent: Optional[str] = Field(
        default=None, sa_column_kwargs={"name": "estado_de_ánimo_usage_intent"}
    )
    riesgo_de_suicidio_score_alignment: Optional[str] = None
    riesgo_de_suicidio_explanation_alignment: Optional[str] = None
    riesgo_de_suicidio_usage_intent: Optional[str] = None
    apoyo_sanitario_percibido_score_alignment: Optional[str] = None
    apoyo_sanitario_percibido_explanation_alignment: Optional[str] = None
    apoyo_sanitario_percibido_usage_intent: Optional[str] = None
    apoyo_social_score_alignment: Optional[str] = None
    apoyo_social_explanation_alignment: Optional[str] = None
    apoyo_social_usage_intent: Optional[str] = None
    control_farmacologico_deldel_dolor_score_alignment: Optional[str] = Field(
        default=None, sa_column_kwargs={"name": "control_farmacológico_deldel_dolor_score_alignment"}
    )
    control_farmacologico_deldel_dolor_explanation_alignment: Optional[str] = Field(
        default=None, sa_column_kwargs={"name": "control_farmacológico_deldel_dolor_explanation_alignment"}
    )
    control_farmacologico_deldel_dolor_usage_intent: Optional[str] = Field(
        default=None, sa_column_kwargs={"name": "control_farmacológico_deldel_dolor_usage_intent"}
    )
    visibilidad_score_alignment: Optional[str] = None
    visibilidad_explanation_alignment: Optional[str] = None
    visibilidad_usage_intent: Optional[str] = None
    impacto_en_salud_mental_score_alignment: Optional[str] = None
    impacto_en_salud_mental_explanation_alignment: Optional[str] = None
    impacto_en_salud_mental_usage_intent: Optional[str] = None
    temporalidad_score_alignment: Optional[str] = None
    temporalidad_explanation_alignment: Optional[str] = None
    temporalidad_usage_intent: Optional[str] = None
    alteracion_de_la_vida_social_score_alignment: Optional[str] = Field(
        default=None, sa_column_kwargs={"name": "alteración_de_la_vida_social_score_alignment"}
    )
    alteracion_de_la_vida_social_explanation_alignment: Optional[str] = Field(
        default=None, sa_column_kwargs={"name": "alteración_de_la_vida_social_explanation_alignment"}
    )
    alteracion_de_la_vida_social_usage_intent: Optional[str] = Field(
        default=None, sa_column_kwargs={"name": "alteración_de_la_vida_social_usage_intent"}
    )
    depresion_score_alignment: Optional[str] = Field(
        default=None, sa_column_kwargs={"name": "depresión_score_alignment"}
    )
    depresion_explanation_alignment: Optional[str] = Field(
        default=None, sa_column_kwargs={"name": "depresión_explanation_alignment"}
    )
    depresion_usage_intent: Optional[str] = Field(default=None, sa_column_kwargs={"name": "depresión_usage_intent"})
    pensamientos_autoliticos_score_alignment: Optional[str] = Field(
        default=None, sa_column_kwargs={"name": "pensamientos_autolíticos_score_alignment"}
    )
    pensamientos_autoliticos_explanation_alignment: Optional[str] = Field(
        default=None, sa_column_kwargs={"name": "pensamientos_autolíticos_explanation_alignment"}
    )
    pensamientos_autoliticos_usage_intent: Optional[str] = Field(
        default=None, sa_column_kwargs={"name": "pensamientos_autolíticos_usage_intent"}
    )
    etiologia_score_alignment: Optional[str] = None
    etiologia_explanation_alignment: Optional[str] = None
    etiologia_usage_intent: Optional[str] = None
    congruencia_clinica_score_alignment: Optional[str] = Field(
        default=None, sa_column_kwargs={"name": "congruencia_clínica_score_alignment"}
    )
    congruencia_clinica_explanation_alignment: Optional[str] = Field(
        default=None, sa_column_kwargs={"name": "congruencia_clínica_explanation_alignment"}
    )
    congruencia_clinica_usage_intent: Optional[str] = Field(
        default=None, sa_column_kwargs={"name": "congruencia_clínica_usage_intent"}
    )
    sintomatologia_depresiva_score_alignment: Optional[str] = Field(
        default=None, sa_column_kwargs={"name": "sintomatología_depresiva_score_alignment"}
    )
    sintomatologia_depresiva_explanation_alignment: Optional[str] = Field(
        default=None, sa_column_kwargs={"name": "sintomatología_depresiva_explanation_alignment"}
    )
    sintomatologia_depresiva_usage_intent: Optional[str] = Field(
        default=None, sa_column_kwargs={"name": "sintomatología_depresiva_usage_intent"}
    )


class ExpertQuestionnaireFeedback(SQLModel, table=True):
    """Expert feedback on LLM questionnaire results (PCS, BPI, TSK)."""

    __tablename__ = "expert_questionnaire_feedback"  # type: ignore
    __table_args__ = {"schema": SCHEMA_NAME}

    # Identifiers
    participant_id: Optional[float] = None  # Float due to pandas handling
    narrative_id: Optional[int] = None
    narrative_hash: Optional[str] = None
    experiments_group_id: Optional[int] = None
    user_id: Optional[int] = None
    questionnaire_id: Optional[int] = Field(default=None, primary_key=True)
    questionnaire_name: Optional[str] = None
    # Feedback ratings
    authenticity_rating: Optional[str] = None
    reasoning_adequacy_rating: Optional[str] = None
    word_count: Optional[int] = None


# =============================================================================
# LLM Synthetic Data Tables
# =============================================================================


class LLMDimensionEvaluation(SQLModel, table=True):
    """LLM-generated dimension evaluation scores (severity and disability)."""

    __tablename__ = "llm_dimension_evaluation"  # type: ignore
    __table_args__ = {"schema": SCHEMA_NAME}

    participant_id: int = Field(primary_key=True)
    experiment_id: Optional[int] = None
    experiments_group_id: Optional[int] = None
    run_number: Optional[int] = None
    model: Optional[str] = None
    # Dimension scores and explanations
    severidad_score: Optional[float] = None
    severidad_explicacion: Optional[str] = None
    discapacidad_score: Optional[float] = None
    discapacidad_explicacion: Optional[str] = None


class LLMPCSResults(SQLModel, table=True):
    """LLM-generated Pain Catastrophizing Scale (PCS) results.

    LLM impersonates the patient to complete the questionnaire.
    """

    __tablename__ = "llm_pcs_results"  # type: ignore
    __table_args__ = {"schema": SCHEMA_NAME}

    participant_id: int = Field(primary_key=True)
    experiment_id: Optional[int] = None
    experiments_group_id: Optional[int] = None
    run_number: Optional[int] = None
    model: Optional[str] = None
    # PCS scores
    pcs_total: Optional[int] = None
    pcs_rumination: Optional[int] = None
    pcs_magnification: Optional[int] = None
    pcs_helplessness: Optional[int] = None
    # Individual items
    pcs_01: Optional[int] = None
    pcs_02: Optional[int] = None
    pcs_03: Optional[int] = None
    pcs_04: Optional[int] = None
    pcs_05: Optional[int] = None
    pcs_06: Optional[int] = None
    pcs_07: Optional[int] = None
    pcs_08: Optional[int] = None
    pcs_09: Optional[int] = None
    pcs_10: Optional[int] = None
    pcs_11: Optional[int] = None
    pcs_12: Optional[int] = None
    pcs_13: Optional[int] = None
    # Persona context
    persona_name: Optional[str] = None
    persona_traits: Optional[str] = None
    model_reasoning: Optional[str] = None


class LLMBPIResults(SQLModel, table=True):
    """LLM-generated Brief Pain Inventory (BPI-IS) results.

    LLM impersonates the patient to complete the questionnaire.
    """

    __tablename__ = "llm_bpi_results"  # type: ignore
    __table_args__ = {"schema": SCHEMA_NAME}

    participant_id: int = Field(primary_key=True)
    experiment_id: Optional[int] = None
    experiments_group_id: Optional[int] = None
    run_number: Optional[int] = None
    model: Optional[str] = None
    # BPI scores
    bpi_total: Optional[int] = None
    bpi_total_mean: Optional[float] = None  # Mean of all items (0-10 scale, matches real data)
    bpi_interference_avg: Optional[float] = None
    bpi_intensity_avg: Optional[float] = None
    bpi_interference_total: Optional[int] = None
    bpi_intensity_total: Optional[int] = None
    # Individual items
    bpiq11: Optional[int] = None
    bpiq12: Optional[int] = None
    bpiq13: Optional[int] = None
    bpiq14: Optional[str] = None  # String in actual data
    bpiq15: Optional[int] = None
    bpiq16: Optional[int] = None
    bpiq17: Optional[int] = None
    bpiq28: Optional[int] = None
    bpiq39: Optional[int] = None
    bpiq410: Optional[int] = None
    bpiq511: Optional[int] = None
    # Persona context
    persona_name: Optional[str] = None
    persona_traits: Optional[str] = None
    model_reasoning: Optional[str] = None


class LLMTSKResults(SQLModel, table=True):
    """LLM-generated Tampa Scale for Kinesiophobia (TSK-11SV) results.

    LLM impersonates the patient to complete the questionnaire.
    """

    __tablename__ = "llm_tsk_results"  # type: ignore
    __table_args__ = {"schema": SCHEMA_NAME}

    participant_id: int = Field(primary_key=True)
    experiment_id: Optional[int] = None
    experiments_group_id: Optional[int] = None
    run_number: Optional[int] = None
    model: Optional[str] = None
    # TSK total score
    tsk_total: Optional[int] = None
    # Individual items (stored as strings in actual data)
    tsk_01: Optional[str] = None
    tsk_02: Optional[str] = None
    tsk_03: Optional[str] = None
    tsk_04: Optional[str] = None
    tsk_05: Optional[str] = None
    tsk_06: Optional[str] = None
    tsk_07: Optional[str] = None
    tsk_08: Optional[str] = None
    tsk_09: Optional[str] = None
    tsk_10: Optional[str] = None
    tsk_11: Optional[str] = None
    # Persona context
    persona_name: Optional[str] = None
    persona_traits: Optional[str] = None
    model_reasoning: Optional[str] = None


# =============================================================================
# System Usability Scale (SUS) Table
# =============================================================================


class SUSUsabilityResults(SQLModel, table=True):
    """System Usability Scale (SUS) responses from expert users.

    SUS is a 10-item questionnaire measuring system usability on a 5-point
    Likert scale. Final scores range 0-100.

    Scoring:
    - Odd items (q1,3,5,7,9): score = response - 1
    - Even items (q2,4,6,8,10): score = 5 - response
    - Total = sum of adjusted scores × 2.5

    Benchmarks:
    - <50: F (Poor)
    - 50-62: D (Marginal)
    - 62-68: C (Average)
    - 68-80: B (Good)
    - 80-90: A (Excellent)
    - >90: A+ (Best Imaginable)
    """

    __tablename__ = "sus_usability_results"  # type: ignore
    __table_args__ = {"schema": SCHEMA_NAME}

    sus_id: Optional[int] = Field(default=None, primary_key=True)
    email: Optional[str] = None
    username: Optional[str] = None
    profession: Optional[str] = None
    age: Optional[int] = None
    # SUS items (1-5 Likert scale)
    q1: Optional[int] = None  # I think I would like to use this system frequently
    q2: Optional[int] = None  # I found the system unnecessarily complex
    q3: Optional[int] = None  # I thought the system was easy to use
    q4: Optional[int] = None  # I would need support from a technical person
    q5: Optional[int] = None  # I found the functions well integrated
    q6: Optional[int] = None  # I thought there was too much inconsistency
    q7: Optional[int] = None  # I imagine most people would learn quickly
    q8: Optional[int] = None  # I found the system very cumbersome to use
    q9: Optional[int] = None  # I felt very confident using the system
    q10: Optional[int] = None  # I needed to learn a lot before using
    # Computed score
    sus_score: Optional[float] = None  # Final SUS score (0-100)
    completed_date: Optional[str] = None
