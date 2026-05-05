with subq as (
SELECT qfb.experiments_group_id,
       qfb.user_id,
       qfb.narrative_id,
       qfb.questionnaire_id,
       que.questionnaire_name,
       qfb.authenticity_rating,
       qfb.reasoning_adequacy_rating,
       que.result_json
FROM pain_narratives_app.questionnaire_feedback AS qfb
LEFT JOIN pain_narratives_app.questionnaires AS que ON qfb.questionnaire_id = que.id
WHERE qfb.experiments_group_id >= 16
    AND qfb.experiments_group_id <= 32
)
SELECT
    subq.experiments_group_id,
    subq.user_id,
    subq.narrative_id,
    nar.narrative,
    nar.narrative_hash,
    nar.word_count,
    nar.char_count,
    subq.questionnaire_id,
    subq.questionnaire_name,
    subq.authenticity_rating,
    subq.reasoning_adequacy_rating,
    subq.result_json

FROM subq
LEFT JOIN pain_narratives_app.narratives nar ON subq.narrative_id = nar.narrative_id

WHERE subq.narrative_id IS NOT NULL

ORDER BY
    subq.experiments_group_id,
    subq.user_id,
    subq.narrative_id;