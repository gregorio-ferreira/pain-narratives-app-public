-- SELECT experiment_id,
--        experiments_group_id,
--        user_id,
--        repeated,
--        created,
--        language_instructions,
--        model_provider,
--        model,
--        with_context,
--        narrative_id,
--        succeeded,
--        parsed_answers,
--        calculated_metrics,
--        extra_description,
--        repo_sha,
--        exp_type

-- -- SELECT COUNT(*) AS num_experiments
-- FROM pain_narratives_app.experiments_list
-- WHERE experiments_group_id = 38 -- AND experiment_id = 531
-- ORDER BY experiment_id
-- LIMIT 1000;




-- SELECT narrative_id,
--        COUNT(*) AS num_experiments
-- FROM pain_narratives_app.experiments_list
-- WHERE experiments_group_id >= 35 -- AND experiment_id = 531
-- GROUP BY narrative_id
-- ORDER BY num_experiments



-- -- Experiments summary by run
-- SELECT 
--     COALESCE(repeated, 1) as run_number,
--     experiments_group_id,
--     COUNT(*) as num_experiments,
--     SUM(CASE WHEN succeeded THEN 1 ELSE 0 END) as succeeded
-- FROM pain_narratives_app.experiments_list
-- WHERE experiments_group_id = 38
-- GROUP BY COALESCE(repeated, 1), experiments_group_id
-- ORDER BY run_number, experiments_group_id;

-- Evaluation counts by run and type
SELECT 
    COALESCE(el.repeated, 1) as run_number,
    er.result_type,
    COUNT(*) as count
FROM pain_narratives_app.evaluation_results er
JOIN pain_narratives_app.experiments_list el ON er.experiment_id = el.experiment_id
WHERE el.experiments_group_id = 40
GROUP BY COALESCE(el.repeated, 1), er.result_type
ORDER BY run_number, er.result_type;
