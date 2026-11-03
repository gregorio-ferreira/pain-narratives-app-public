-- Operator-reviewed template; never run with the application's runtime credentials.
-- Provision app_role separately with LOGIN, no superuser/role/database creation,
-- and a password supplied privately. It must not own the schema/tables.
-- Usage: psql 'service=operator' -v app_role=app_runtime -v owner_role=schema_owner \
--          -v database=application_database -f sql/runtime_role.example.sql
\set ON_ERROR_STOP on
BEGIN;
GRANT CONNECT ON DATABASE :"database" TO :"app_role";
GRANT USAGE ON SCHEMA pain_narratives_app TO :"app_role";
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA pain_narratives_app TO :"app_role";
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA pain_narratives_app TO :"app_role";
ALTER DEFAULT PRIVILEGES FOR ROLE :"owner_role" IN SCHEMA pain_narratives_app
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO :"app_role";
ALTER DEFAULT PRIVILEGES FOR ROLE :"owner_role" IN SCHEMA pain_narratives_app
    GRANT USAGE, SELECT ON SEQUENCES TO :"app_role";
REVOKE CREATE ON SCHEMA pain_narratives_app FROM :"app_role";
COMMIT;
-- Review inherited/PUBLIC privileges and role memberships separately. A GRANT
-- template cannot remove privileges inherited from another role or schema owner.
