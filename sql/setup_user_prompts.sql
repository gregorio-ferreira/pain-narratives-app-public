-- =====================================================
-- Pain Narratives App - User Prompt Persistence Solution
-- =====================================================

-- 1. Create a table to store user-specific prompts
-- =====================================================
CREATE TABLE IF NOT EXISTS pain_narratives_app.user_prompts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES pain_narratives_app.users(id) ON DELETE CASCADE,
    prompt_name VARCHAR(255) NOT NULL,
    prompt_description TEXT,
    prompt_template TEXT NOT NULL,
    category VARCHAR(100) DEFAULT 'custom',
    is_current BOOLEAN DEFAULT FALSE, -- Mark as user's current active prompt
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, prompt_name) -- User can't have duplicate prompt names
);

-- 2. Add index for faster lookups
-- =====================================================
CREATE INDEX IF NOT EXISTS idx_user_prompts_user_id ON pain_narratives_app.user_prompts(user_id);
CREATE INDEX IF NOT EXISTS idx_user_prompts_current ON pain_narratives_app.user_prompts(user_id, is_current) WHERE is_current = true;

-- 3. Add trigger to ensure only one prompt per user is marked as current
-- =====================================================
CREATE OR REPLACE FUNCTION pain_narratives_app.ensure_single_current_prompt()
RETURNS TRIGGER AS $$
BEGIN
    -- If setting a prompt as current, unset all others for this user
    IF NEW.is_current = TRUE THEN
        UPDATE pain_narratives_app.user_prompts 
        SET is_current = FALSE 
        WHERE user_id = NEW.user_id AND id != NEW.id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_ensure_single_current_prompt ON pain_narratives_app.user_prompts;
CREATE TRIGGER trigger_ensure_single_current_prompt
    BEFORE INSERT OR UPDATE ON pain_narratives_app.user_prompts
    FOR EACH ROW
    EXECUTE FUNCTION pain_narratives_app.ensure_single_current_prompt();

-- 4. Optional: Insert default prompts for existing users
-- =====================================================
-- This will give all existing users a default current prompt
INSERT INTO pain_narratives_app.user_prompts (user_id, prompt_name, prompt_description, prompt_template, category, is_current)
SELECT 
    u.id,
    'Default Pain Assessment',
    'Standard pain narrative evaluation prompt',
    'You are a medical expert evaluating pain narratives from fibromyalgia patients. Please analyze the following narrative and provide scores for these dimensions on a scale of 1-10:

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
    'general',
    true
FROM pain_narratives_app.users u
WHERE NOT EXISTS (
    SELECT 1 FROM pain_narratives_app.user_prompts up 
    WHERE up.user_id = u.id
);

-- 5. Verification queries
-- =====================================================

-- Check if table was created successfully
SELECT EXISTS (
    SELECT FROM information_schema.tables 
    WHERE table_schema = 'pain_narratives_app' 
    AND table_name = 'user_prompts'
) as table_exists;

-- Check user prompts
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
ORDER BY u.username, up.created_at DESC;
