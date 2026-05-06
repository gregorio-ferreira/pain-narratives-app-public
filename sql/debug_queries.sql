-- =====================================================
-- Pain Narratives App - Database Debugging Queries
-- =====================================================
-- Run these queries in pgAdmin to debug experiments and user data

-- 1. Check all users and their details
-- =====================================================
SELECT 
    id,
    username,
    is_admin,
    (SELECT COUNT(*) FROM pain_narratives_app.experiments_groups WHERE owner_id = u.id) as owned_experiment_groups
FROM pain_narratives_app.users u
ORDER BY id;

-- 2. Check all experiment groups with owner information
-- =====================================================
SELECT 
    eg.experiments_group_id,
    eg.description,
    eg.system_role,
    LEFT(eg.base_prompt, 100) || '...' as base_prompt_preview,
    eg.created,
    eg.concluded,
    eg.processed,
    u.username as owner_username,
    u.is_admin as owner_is_admin,
    (SELECT COUNT(*) FROM pain_narratives_app.experiments_list WHERE experiments_group_id = eg.experiments_group_id) as experiments_count
FROM pain_narratives_app.experiments_groups eg
JOIN pain_narratives_app.users u ON eg.owner_id = u.id
ORDER BY eg.created DESC;

-- 3. Check all narratives created
-- =====================================================
SELECT 
    narrative_id,
    LEFT(narrative, 100) || '...' as narrative_preview,
    seve_rube,
    seve_pat,
    disca_rube,
    disca_pat,
    (SELECT COUNT(*) FROM pain_narratives_app.experiments_list WHERE narrative_id = n.narrative_id) as experiments_count
FROM pain_narratives_app.narratives n
ORDER BY narrative_id;

-- 4. Check all experiments with full details
-- =====================================================
SELECT 
    el.experiment_id,
    el.experiments_group_id,
    el.repeated,
    el.created,
    el.language_instructions,
    el.model_provider,
    el.model,
    el.with_context,
    el.narrative_id,
    el.succeeded,
    el.parsed_answers,
    el.calculated_metrics,
    el.extra_description,
    el.repo_sha,
    el.exp_type,
    eg.description as group_description,
    u.username as group_owner,
    LEFT(n.narrative, 50) || '...' as narrative_preview
FROM pain_narratives_app.experiments_list el
JOIN pain_narratives_app.experiments_groups eg ON el.experiments_group_id = eg.experiments_group_id
JOIN pain_narratives_app.users u ON eg.owner_id = u.id
LEFT JOIN pain_narratives_app.narratives n ON el.narrative_id = n.narrative_id
ORDER BY el.created DESC;

-- 5. Check all request/response data
-- =====================================================
SELECT 
    rr.id,
    rr.created,
    rr.experiment_id,
    el.model,
    el.model_provider,
    u.username as experiment_owner,
    rr.request_json->>'model' as request_model,
    rr.response_json->>'model' as response_model,
    rr.response_json->'usage' as token_usage,
    LENGTH(rr.request_json::text) as request_size_chars,
    LENGTH(rr.response_json::text) as response_size_chars
FROM pain_narratives_app.request_response rr
JOIN pain_narratives_app.experiments_list el ON rr.experiment_id = el.experiment_id
JOIN pain_narratives_app.experiments_groups eg ON el.experiments_group_id = eg.experiments_group_id
JOIN pain_narratives_app.users u ON eg.owner_id = u.id
ORDER BY rr.created DESC;

-- 6. Check model responses (evaluation results)
-- =====================================================
SELECT 
    mr.narrative_id,
    mr.experiment_id,
    mr.severity_score,
    mr.disability_score,
    LEFT(mr.severity_explanation, 100) || '...' as severity_explanation_preview,
    LEFT(mr.disability_explanation, 100) || '...' as disability_explanation_preview,
    el.model,
    el.created as experiment_created,
    u.username as experiment_owner
FROM pain_narratives_app.model_responses mr
JOIN pain_narratives_app.experiments_list el ON mr.experiment_id = el.experiment_id
JOIN pain_narratives_app.experiments_groups eg ON el.experiments_group_id = eg.experiments_group_id
JOIN pain_narratives_app.users u ON eg.owner_id = u.id
ORDER BY el.created DESC;

-- 7. User activity summary
-- =====================================================
SELECT 
    u.username,
    u.is_admin,
    COUNT(DISTINCT eg.experiments_group_id) as experiment_groups_created,
    COUNT(DISTINCT el.experiment_id) as total_experiments,
    COUNT(DISTINCT el.narrative_id) as unique_narratives_evaluated,
    MAX(el.created) as last_experiment_date,
    COUNT(DISTINCT el.model) as different_models_used
FROM pain_narratives_app.users u
LEFT JOIN pain_narratives_app.experiments_groups eg ON u.id = eg.owner_id
LEFT JOIN pain_narratives_app.experiments_list el ON eg.experiments_group_id = el.experiments_group_id
GROUP BY u.id, u.username, u.is_admin
ORDER BY total_experiments DESC;

-- 8. Recent experiment activity (last 24 hours)
-- =====================================================
SELECT 
    el.experiment_id,
    el.created,
    u.username,
    el.model,
    el.exp_type,
    LEFT(n.narrative, 80) || '...' as narrative_preview,
    CASE 
        WHEN rr.id IS NOT NULL THEN 'Has Request/Response'
        ELSE 'No Request/Response'
    END as has_openai_data
FROM pain_narratives_app.experiments_list el
JOIN pain_narratives_app.experiments_groups eg ON el.experiments_group_id = eg.experiments_group_id
JOIN pain_narratives_app.users u ON eg.owner_id = u.id
LEFT JOIN pain_narratives_app.narratives n ON el.narrative_id = n.narrative_id
LEFT JOIN pain_narratives_app.request_response rr ON el.experiment_id = rr.experiment_id
WHERE el.created >= NOW() - INTERVAL '24 hours'
ORDER BY el.created DESC;

-- 9. Prompt persistence check - Look for saved prompts in experiment groups
-- =====================================================
SELECT 
    eg.experiments_group_id,
    eg.description,
    u.username as owner,
    LEFT(eg.base_prompt, 200) || '...' as base_prompt_preview,
    eg.created,
    COUNT(el.experiment_id) as experiments_using_this_prompt
FROM pain_narratives_app.experiments_groups eg
JOIN pain_narratives_app.users u ON eg.owner_id = u.id
LEFT JOIN pain_narratives_app.experiments_list el ON eg.experiments_group_id = el.experiments_group_id
WHERE eg.base_prompt IS NOT NULL AND eg.base_prompt != ''
GROUP BY eg.experiments_group_id, eg.description, u.username, eg.base_prompt, eg.created
ORDER BY eg.created DESC;

-- 10. Check for any JSON data in extra_description that might contain prompt info
-- =====================================================
SELECT 
    el.experiment_id,
    el.created,
    u.username,
    el.extra_description,
    LEFT(n.narrative, 50) || '...' as narrative_preview
FROM pain_narratives_app.experiments_list el
JOIN pain_narratives_app.experiments_groups eg ON el.experiments_group_id = eg.experiments_group_id
JOIN pain_narratives_app.users u ON eg.owner_id = u.id
LEFT JOIN pain_narratives_app.narratives n ON el.narrative_id = n.narrative_id
WHERE el.extra_description IS NOT NULL
ORDER BY el.created DESC;
