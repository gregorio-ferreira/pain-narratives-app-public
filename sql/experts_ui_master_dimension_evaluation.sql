-- ============================================================================
-- EXPERT UI MASTER DATA - Consolidated Expert Feedback
-- ============================================================================
-- This query consolidates all expert evaluations from the UI (groups 16-32)
-- Includes: assessment feedback, questionnaire feedback, and evaluation results
--
-- IMPORTANT: The narrative_id is corrected using assessment_feedback table
-- because the UI had a bug where experiment.narrative_id wasn't always correct
-- ============================================================================

with subq as (
SELECT
    -- ========================================================================
    -- EXPERIMENT GROUP INFO
    -- ========================================================================
    grp.experiments_group_id,
    grp.description AS group_description,
    grp.dimensions AS group_dimensions,

    -- ========================================================================
    -- EXPERIMENT & USER INFO
    -- ========================================================================
    exp.experiment_id,
    exp.exp_type,
    exp.user_id,
    exp.extra_description,

    -- ========================================================================
    -- NARRATIVE INFO (with corrected narrative_id)
    -- ========================================================================
    -- Fix narrative_id: Use assessment_feedback.narrative_id for UI experiments
    -- because exp.narrative_id wasn't always stored correctly
    CASE
        WHEN exp.exp_type = 'ui' AND res.result_type = 'narrative_evaluation'
            THEN ass.narrative_id
        ELSE exp.narrative_id
    END AS narrative_id,

    -- ========================================================================
    -- ASSESSMENT FEEDBACK (Dimension Ratings by Experts)
    -- ========================================================================
    -- The actual ratings are in dimension_feedback JSON
    -- The individual columns (intensity_score_alignment, etc.) are empty in the UI data
    ass.dimension_feedback,  -- JSON with all dimension feedback



    -- ========================================================================
    -- EVALUATION RESULTS (Actual Scores and Model Outputs)
    -- ========================================================================
    -- Contains the actual evaluation scores and model-generated content

    res.result_json  -- JSON with scores, explanations, etc.

-- ============================================================================
-- TABLE JOINS
-- ============================================================================
FROM pain_narratives_app.experiments_groups AS grp

-- Get all experiments in these groups
INNER JOIN pain_narratives_app.experiments_list AS exp
    ON grp.experiments_group_id = exp.experiments_group_id


-- Get assessment feedback (expert dimension ratings)
LEFT JOIN pain_narratives_app.assessment_feedback AS ass
    ON exp.experiment_id = ass.experiment_id

-- Get evaluation results (actual scores and outputs)
LEFT JOIN pain_narratives_app.evaluation_results AS res
    ON exp.experiment_id = res.experiment_id

-- ============================================================================
-- FILTERS
-- ============================================================================
WHERE
    -- Expert UI groups (16-32)
    grp.experiments_group_id >= 16
    AND grp.experiments_group_id <= 32

    -- Only UI experiments
    AND exp.exp_type = 'ui'
    AND ass.dimension_feedback IS NOT NULL
)
SELECT
    subq.experiments_group_id,
    subq.group_description,
    subq.group_dimensions,
    subq.experiment_id,
    subq.exp_type,
    subq.user_id,
    subq.extra_description,
    subq.narrative_id,
    nar.narrative,
    nar.narrative_hash,
    nar.word_count,
    nar.char_count,
    subq.dimension_feedback,
    subq.result_json

FROM subq
LEFT JOIN pain_narratives_app.narratives nar ON subq.narrative_id = nar.narrative_id

WHERE subq.narrative_id IS NOT NULL
-- ============================================================================
-- ORDERING
-- ============================================================================
ORDER BY
    subq.experiments_group_id,
    subq.user_id,
    subq.narrative_id