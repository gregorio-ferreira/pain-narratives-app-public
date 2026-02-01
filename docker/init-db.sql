-- Pain Narratives Database Initialization Script
-- This script runs automatically when the PostgreSQL container starts for the first time

-- Create the application schema
CREATE SCHEMA IF NOT EXISTS pain_narratives_app;

-- Grant permissions (the tables will be created by Alembic migrations)
GRANT ALL PRIVILEGES ON SCHEMA pain_narratives_app TO pain_narratives;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA pain_narratives_app TO pain_narratives;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA pain_narratives_app TO pain_narratives;

-- Set default schema for the user
ALTER USER pain_narratives SET search_path TO pain_narratives_app, public;

-- Add comment for documentation
COMMENT ON SCHEMA pain_narratives_app IS 'Schema for Pain Narratives AI Assessment Application';
