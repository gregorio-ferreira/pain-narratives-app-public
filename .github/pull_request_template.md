## Summary

One to three sentences on what this PR does and why.

## What changed

- ...
- ...

## Test plan

- [ ] `make check` passes (format, lint, typecheck)
- [ ] `make test` passes (or note which pre-existing failures remain)
- [ ] Manual smoke test of the affected code paths
- [ ] Database migration applied to a staging DB (if applicable)

## Schema / migration impact

If this PR touches `src/pain_narratives/db/` or adds an alembic revision,
describe:

- The new head revision id
- Whether the migration is additive (preferred) or destructive
- Rollback plan if anything goes wrong

## Risk

What's the worst that could happen? What did you do to prevent it?

## Screenshots / artifacts

If this PR changes the UI or generates output, include screenshots or sample
output. Redact PII.
