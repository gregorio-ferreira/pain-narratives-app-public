# User Management

Admin-only UI for managing accounts and experiment-group access. Available at
**Application Management → User Administration** after logging in as an admin.

The UI layer lives in
[`src/pain_narratives/ui/components/management.py`](../src/pain_narratives/ui/components/management.py).
The corresponding database methods are on `DatabaseManager` in
[`src/pain_narratives/core/database.py`](../src/pain_narratives/core/database.py).
All copy is localized in `en.yml` and `es.yml` under
[`src/pain_narratives/locales/`](../src/pain_narratives/locales/).

## User account actions

| Action | Method | Notes |
|---|---|---|
| Create user | `DatabaseManager.create_user(username, password, is_admin)` | Min password length 3. Username unique. Hashed with SHA-256. |
| Toggle admin | `update_user_admin_status(user_id, is_admin)` | Button label shows current → new status. |
| Reset password | `reset_user_password(user_id, new_password)` | Popover input; same validation as creation. |
| Delete user | `delete_user(user_id)` | Confirmation popover. The currently logged-in user cannot delete themselves. |

The user table displays each user's ID, username, admin flag, and the comma-
separated list of experiment groups they have access to.

## Experiment-group assignment

Users are linked to experiment groups through the `experiment_group_users`
junction table. The UI section **Edit Experiment Groups** accepts a
comma-separated list of group IDs:

| Input | Effect |
|---|---|
| `1, 3, 5` | Replace assignments with groups 1, 3, 5. |
| `12` | Assign only to group 12. |
| `` (empty) | Remove all group assignments. |
| `1; 3; 5` | Error: invalid format (use commas). |
| `1, abc, 5` | Error: invalid format (integers only). |
| `1, 99999` | Error: group 99999 does not exist. |

Database method:

```python
DatabaseManager.update_user_experiment_groups(user_id: int, group_ids: list[int]) -> bool
```

Behaviour: validates every group ID exists, deletes the existing
`ExperimentGroupUser` rows for that user, inserts the new ones in a single
transaction, and raises `ValueError` if any ID is unknown. The available-groups
panel is populated by `get_all_experiment_groups()`.

## CLI alternatives

For batch or scripted operations:

```bash
# List / inspect
uv run python scripts/manage_users.py list
uv run python scripts/manage_users.py show <username>

# Grant or revoke admin rights
uv run python scripts/manage_users.py make-admin <username>

# Register users
uv run python scripts/register_user.py                          # interactive
uv run python scripts/register_user_batch.py <user> <password>  # one-shot
uv run python scripts/manage_users.py import-csv <path>         # bulk
```

## Tests

```bash
uv run pytest tests/test_edit_experiment_groups.py
```

Covers valid assignment, empty input (revoke all), and invalid group IDs.

## Security notes

- All UI actions check `is_admin` at page load and refuse otherwise.
- All database operations go through SQLModel parameterized queries.
- Operations are wrapped in transactions; failures roll back cleanly.
- The "cannot delete self" guard is enforced in the UI; the underlying
  `delete_user` method does not refuse, so do not call it without that check.
