-- =====================================================
-- Verify UserPrompt Table Creation
-- =====================================================
-- Run these queries in pgAdmin to verify the user_prompts table

-- 1. Check if the table exists
-- =====================================================
SELECT EXISTS (
    SELECT FROM information_schema.tables 
    WHERE table_schema = 'pain_narratives_app' 
    AND table_name = 'user_prompts'
) as user_prompts_table_exists;

-- 2. Check the table structure
-- =====================================================
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_schema = 'pain_narratives_app' 
AND table_name = 'user_prompts'
ORDER BY ordinal_position;

-- 3. Check constraints
-- =====================================================
SELECT 
    tc.constraint_name,
    tc.constraint_type,
    kcu.column_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu 
    ON tc.constraint_name = kcu.constraint_name
WHERE tc.table_schema = 'pain_narratives_app'
AND tc.table_name = 'user_prompts'
ORDER BY tc.constraint_type, tc.constraint_name;

-- 4. Insert a test prompt for admin user (ID 1)
-- =====================================================
INSERT INTO pain_narratives_app.user_prompts 
(user_id, prompt_name, prompt_description, prompt_template, category, is_current)
VALUES 
(
    1,
    'My Custom Pain Assessment',
    'A personalized prompt for detailed pain evaluation',
    'You are a medical expert evaluating pain narratives. Please analyze the following narrative and provide scores for these dimensions on a scale of 1-10:

1. **Pain Intensity**: How severe is the pain described? (1=minimal, 10=excruciating)
2. **Functional Impact**: How much does the pain affect daily activities? (1=no impact, 10=severe disability)
3. **Emotional Impact**: How much emotional distress is expressed? (1=none, 10=severe distress)
4. **Descriptive Quality**: How well does the narrative describe the pain experience? (1=vague, 10=very detailed)

Please respond in JSON format with the following structure:
{
    "pain_intensity": <score>,
    "functional_impact": <score>,
    "emotional_impact": <score>,
    "descriptive_quality": <score>,
    "reasoning": "<brief explanation of your scoring>"
}

Narrative to evaluate:
{narrative}',
    'custom',
    true
)
ON CONFLICT (user_id, prompt_name) DO UPDATE SET
    prompt_template = EXCLUDED.prompt_template,
    is_current = EXCLUDED.is_current,
    updated_at = CURRENT_TIMESTAMP;

-- 5. Verify the test prompt was inserted
-- =====================================================
SELECT 
    up.id,
    u.username,
    up.prompt_name,
    up.category,
    up.is_current,
    up.created_at,
    LENGTH(up.prompt_template) as template_length
FROM pain_narratives_app.user_prompts up
JOIN pain_narratives_app.users u ON up.user_id = u.id
ORDER BY up.created_at DESC;

-- 6. Test updating a prompt to current
-- =====================================================
-- This will demonstrate the unique constraint for is_current per user
INSERT INTO pain_narratives_app.user_prompts 
(user_id, prompt_name, prompt_description, prompt_template, category, is_current)
VALUES 
(
    1,
    'Alternative Assessment',
    'Another assessment approach',
    'Alternative prompt template for testing...',
    'test',
    false
);

-- Then try to set it as current (should unset the previous one)
UPDATE pain_narratives_app.user_prompts 
SET is_current = true 
WHERE user_id = 1 AND prompt_name = 'Alternative Assessment';

-- Verify only one prompt is marked as current per user
SELECT 
    u.username,
    up.prompt_name,
    up.is_current
FROM pain_narratives_app.user_prompts up
JOIN pain_narratives_app.users u ON up.user_id = u.id
WHERE up.user_id = 1
ORDER BY up.is_current DESC, up.created_at DESC;
