# User Experiment Groups Management Feature

## Overview

This feature allows administrators to edit the experiment groups assigned to users through the web UI. Users can be assigned to multiple experiment groups, and the system validates that all assigned group IDs exist in the database.

## Implementation Date

October 14, 2025

## Components Added

### 1. Database Methods (`src/pain_narratives/core/database.py`)

#### `update_user_experiment_groups(user_id: int, group_ids: List[int]) -> bool`

Updates the experiment groups assigned to a user by replacing all existing assignments.

**Parameters:**

- `user_id`: The ID of the user to update
- `group_ids`: List of experiment group IDs to assign (can be empty to remove all assignments)

**Returns:**

- `True` if successful

**Raises:**

- `ValueError`: If any group_id doesn't exist in the database

**Behavior:**

1. Validates that all provided group IDs exist in the database
2. Deletes all existing `ExperimentGroupUser` links for the user
3. Creates new `ExperimentGroupUser` links for each group ID provided
4. Commits the transaction

**Example:**

```python
# Assign user to groups 1, 3, and 5
db_manager.update_user_experiment_groups(user_id=10, group_ids=[1, 3, 5])

# Remove all group assignments
db_manager.update_user_experiment_groups(user_id=10, group_ids=[])
```

#### `get_all_experiment_groups() -> List[ExperimentGroup]`

Returns all experiment groups in the database, used to display available groups to administrators.

**Returns:**

- List of all `ExperimentGroup` objects

### 2. UI Components (`src/pain_narratives/ui/components/management.py`)

Added a new section "Edit Experiment Groups" in the user administration UI that includes:

**Available Groups Display:**

- Expandable table showing all experiment groups with:
  - ID
  - Description
  - Owner ID
  - Status (Active/Concluded)

**Current Groups Info:**

- Displays the current experiment groups the selected user belongs to
- Format: "1, 3, 5" or "None" if no groups

**Edit Form:**

- Text input field for entering comma-separated group IDs
- Pre-populated with current group IDs
- Help text explaining the format
- Save button to apply changes

**Validation:**

- Validates that input contains only integers separated by commas
- Validates that all group IDs exist in the database
- Provides clear error messages for invalid input
- Empty input removes all group assignments

**User Feedback:**

- Success message showing username and confirmation
- Error messages for:
  - Invalid format (non-integer values)
  - Non-existent group IDs
  - Database errors

### 3. Localization Strings

Added 11 new localization keys in both English and Spanish:

**English (`src/pain_narratives/locales/en.yml`):**

```yaml
edit_experiment_groups_header: "🧪 Edit Experiment Groups"
edit_groups_button: "🧪 Edit Groups"
current_groups_label: "Current Groups"
enter_group_ids_label: "Enter Group IDs (comma-separated)"
enter_group_ids_help: "Enter experiment group IDs separated by commas (e.g., 1, 3, 5)"
save_groups_button: "💾 Save Groups"
groups_updated_success: "✅ Experiment groups updated successfully for user '{username}'"
groups_update_failed: "❌ Failed to update experiment groups: {error}"
invalid_group_ids_error: "❌ Invalid format: Please enter comma-separated integers"
group_not_found_error: "❌ Experiment group with ID {group_id} does not exist"
available_groups_label: "📋 Available Groups"
no_groups_available: "No experiment groups available"
```

**Spanish (`src/pain_narratives/locales/es.yml`):**

```yaml
edit_experiment_groups_header: "🧪 Editar Grupos de Experimento"
edit_groups_button: "🧪 Editar Grupos"
current_groups_label: "Grupos Actuales"
enter_group_ids_label: "Ingrese IDs de Grupo (separados por comas)"
enter_group_ids_help: "Ingrese los IDs de grupos de experimento separados por comas (ej. 1, 3, 5)"
save_groups_button: "💾 Guardar Grupos"
groups_updated_success: "✅ Grupos de experimento actualizados exitosamente para el usuario '{username}'"
groups_update_failed: "❌ Error al actualizar grupos de experimento: {error}"
invalid_group_ids_error: "❌ Formato inválido: Por favor ingrese enteros separados por comas"
group_not_found_error: "❌ El grupo de experimento con ID {group_id} no existe"
available_groups_label: "📋 Grupos Disponibles"
no_groups_available: "No hay grupos de experimento disponibles"
```

## User Workflow

1. **Navigate to User Administration**

   - Login as admin
   - Go to Management tab → User Administration

2. **Select User**

   - Choose a user from the dropdown in "User Actions" section

3. **View Available Groups**

   - Expand "📋 Available Groups" to see all experiment groups
   - Note the IDs you want to assign

4. **Edit Groups**

   - Scroll to "🧪 Edit Experiment Groups" section
   - Current groups are displayed
   - Enter new group IDs in the text field (comma-separated)
   - Examples:
     - `1, 3, 5` - Assign to groups 1, 3, and 5
     - `12` - Assign to group 12 only
     - `` (empty) - Remove all group assignments

5. **Save Changes**
   - Click "💾 Save Groups"
   - System validates the input
   - Success or error message is displayed
   - Page refreshes to show updated groups

## Validation Rules

1. **Format Validation:**

   - Input must be comma-separated integers or empty
   - Whitespace is automatically trimmed
   - Invalid formats show error: "Invalid format: Please enter comma-separated integers"

2. **Existence Validation:**

   - All group IDs must exist in the `experiments_groups` table
   - Non-existent IDs show error: "Experiment group with ID {id} does not exist"

3. **Empty Input:**
   - Empty input is valid and removes all group assignments
   - Useful for revoking user access to all groups

## Database Schema

### Tables Affected:

**`experiment_group_users` (junction table):**

- `id` (primary key)
- `experiments_group_id` (foreign key to `experiments_groups.experiments_group_id`)
- `user_id` (foreign key to `users.id`)

### Operations:

1. **Read:** `get_user_experiment_groups(user_id)` reads existing links
2. **Delete:** Removes all existing `ExperimentGroupUser` records for the user
3. **Create:** Creates new `ExperimentGroupUser` records for each group ID
4. **Validate:** Checks that each `experiments_group_id` exists in `experiments_groups`

## Testing

### Test Script: `tests/test_edit_experiment_groups.py`

Automated tests covering:

1. **Test 1: Valid Update**

   - Update user groups with valid IDs
   - Verify groups are correctly assigned

2. **Test 2: Remove All Groups**

   - Update with empty list
   - Verify all groups are removed

3. **Test 3: Invalid Group ID**
   - Attempt to assign non-existent group ID
   - Verify ValueError is raised with correct message

### Test Results:

```
✅ Found 15 experiment groups in database
✅ Found 33 users in database
📝 Testing with user: andreas (ID: 2)
Current groups: []

🧪 Test 1: Updating groups to [2, 4]
✅ Test 1 passed: Groups updated to [2, 4]

🧪 Test 2: Removing all groups
✅ Test 2 passed: All groups removed

🧪 Test 3: Testing with invalid group ID 99999
✅ Test 3 passed: Correctly raised ValueError: Experiment group with ID 99999 does not exist

✅ All tests completed successfully!
```

## Error Handling

### Invalid Format Error

**Trigger:** User enters non-numeric values (e.g., "1, abc, 5")
**Response:** "❌ Invalid format: Please enter comma-separated integers"

### Group Not Found Error

**Trigger:** User enters ID that doesn't exist (e.g., "1, 99999, 5")
**Response:** "❌ Experiment group with ID 99999 does not exist"

### Database Error

**Trigger:** Database connection or transaction failure
**Response:** "❌ Failed to update experiment groups: {error details}"

### No Groups Available

**Trigger:** No experiment groups exist in the database
**Response:** "No experiment groups available" (warning message)

## Security Considerations

1. **Admin-Only Access:**

   - Feature only accessible to users with `is_admin=True`
   - Non-admin users see "Admin privileges required" warning

2. **Input Validation:**

   - All input is validated before database operations
   - SQL injection prevented through SQLModel parameterized queries

3. **Transaction Integrity:**

   - All operations wrapped in database transaction
   - Changes are rolled back on error

4. **Audit Trail:**
   - All changes logged through standard application logging
   - User actions trackable through database timestamps

## Future Enhancements

Potential improvements for future versions:

1. **Multi-Select UI:**

   - Replace text input with checkbox list for better UX
   - Show group descriptions alongside IDs

2. **Bulk Operations:**

   - Update multiple users at once
   - Copy group assignments from one user to another

3. **Permission Levels:**

   - Different access levels within groups
   - Group-specific roles (viewer, editor, admin)

4. **Audit Log:**

   - Track who changed group assignments and when
   - View history of group membership changes

5. **Group Filters:**
   - Filter users by group membership
   - Search groups by various criteria

## Related Documentation

- **User Management UI Guide:** `docs/USER_MANAGEMENT_UI_GUIDE.md`
- **User Management Enhancement:** `docs/USER_MANAGEMENT_UI_ENHANCEMENT.md`
- **Database Models:** `src/pain_narratives/db/models_sqlmodel.py`
- **Management UI Components:** `src/pain_narratives/ui/components/management.py`

## Change Log

### October 14, 2025 - Initial Implementation

- Added `update_user_experiment_groups()` method to DatabaseManager
- Added `get_all_experiment_groups()` method to DatabaseManager
- Created UI section for editing experiment groups
- Added 11 localization strings (EN + ES)
- Created automated test suite
- Created comprehensive documentation
