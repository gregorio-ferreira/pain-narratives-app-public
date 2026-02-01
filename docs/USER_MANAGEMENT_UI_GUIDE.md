# User Management UI - Visual Guide

## Overview

The enhanced User Administration interface provides a comprehensive user management system accessible to admin users through the Application Management tab.

## Access Path

```
Login (as admin) → ⚙️ Application Management → 👥 User Administration
```

## UI Layout

### 1. Header Section

```
👥 User Administration
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 2. Create New User (Collapsible)

```
▶ ➕ Create New User
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[When expanded:]

┌─────────────────────────────────────────────────┐
│  Username        Password         [x] Make Admin│
│  [_________]     [_________]                    │
│                                                  │
│            [Create User]                         │
└─────────────────────────────────────────────────┘
```

**Features:**

- Three-column layout: Username | Password | Admin checkbox
- Form validation on submit
- Auto-refresh after successful creation
- Success/error messages with username

**Validation:**

- Username: Required
- Password: Required, minimum 3 characters
- Immediate feedback on errors

### 3. All Users Table

```
📊 All Users
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┌────┬──────────────┬────────┬─────────────────────┐
│ ID │ Username     │ Admin  │ Experiment Groups   │
├────┼──────────────┼────────┼─────────────────────┤
│ 1  │ admin        │ ✅ Yes │ 1, 3, 5, 12         │
│ 2  │ researcher01 │ ❌ No  │ 3, 5                │
│ 3  │ akamilovski  │ ❌ No  │ -                   │
│ 10 │ doctor_jane  │ ❌ No  │ 2, 7, 9             │
└────┴──────────────┴────────┴─────────────────────┘
```

**Key Changes:**

- ✨ **NEW**: Experiment Groups column shows **group IDs** (e.g., "1, 3, 5")
- Previous: Showed only count (e.g., "3")
- Empty: Shows "-" if user has no groups

### 4. User Actions Section

```
User Actions
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Select User: [researcher01 (ID: 2)     ▼]

┌──────────────────┬──────────────────┬──────────────────┐
│ 👑 Toggle Admin  │ 🔑 Reset Password│ 🗑️ Delete User  │
│ (Regular → Admin)│                  │                  │
└──────────────────┴──────────────────┴──────────────────┘
```

#### Action 1: Toggle Admin Status

```
┌─────────────────────────────────────────┐
│ 👑 Toggle Admin (Regular User → Admin) │ ← Click
└─────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────┐
│ ✅ Admin status updated for researcher01│
└─────────────────────────────────────────┘
        ↓
   [Page refreshes automatically]
```

**Features:**

- Shows current status → new status in button text
- Examples:
  - "Admin → Regular User"
  - "Regular User → Admin"
- Instant feedback
- Auto-refresh to show changes

#### Action 2: Reset Password

```
┌──────────────────┐
│ 🔑 Reset Password│ ← Click
└──────────────────┘
        ↓
┌─────────────────────────────────┐
│ New Password: [____________]    │
│                                 │
│      [🔑 Reset Password]        │
└─────────────────────────────────┘
        ↓
┌─────────────────────────────────┐
│ ✅ Password reset successfully  │
│    for researcher01             │
└─────────────────────────────────┘
```

**Features:**

- Popover interface (non-modal)
- Password input (hidden characters)
- Same validation as user creation
- Confirmation message with username

#### Action 3: Delete User

```
┌──────────────────┐
│ 🗑️ Delete User   │ ← Click
└──────────────────┘
        ↓
┌─────────────────────────────────────────────┐
│ ⚠️ Are you sure you want to delete user    │
│    'researcher01'? This action cannot be   │
│    undone.                                 │
│                                            │
│         [⚠️ Confirm Delete]                │
└─────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────┐
│ ✅ User 'researcher01' deleted successfully │
└─────────────────────────────────────────────┘
```

**Safety Features:**

- Warning message before deletion
- Requires explicit confirmation
- Cannot delete your own account (button disabled)
- Tooltip: "❌ You cannot delete your own account"

### 5. Quick Actions Reference (Bottom)

```
⚡ Quick Actions
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 Use the command-line scripts for detailed user
   management operations.

┌─────────────────────────┬─────────────────────────┐
│ User Management Scripts │ User Registration       │
│                         │ Scripts                 │
│ # List all users        │ # Interactive           │
│ uv run python           │ uv run python           │
│   scripts/manage_users  │   scripts/register_user │
│   .py list              │   .py                   │
│                         │                         │
│ # Show user details     │ # Batch registration    │
│ uv run python           │ uv run python           │
│   scripts/manage_users  │   scripts/register_user │
│   .py show username     │   _batch.py user pass   │
│                         │                         │
│ # Grant admin           │ # Import from CSV       │
│ uv run python           │ uv run python           │
│   scripts/manage_users  │   scripts/manage_users  │
│   .py make-admin user   │   .py import-csv file   │
└─────────────────────────┴─────────────────────────┘
```

## Example Workflows

### Workflow 1: Create New Research Assistant

```
1. Expand "➕ Create New User"
2. Username: "research_assistant_01"
3. Password: "TempPass123!"
4. Make Admin: [ ] (unchecked)
5. Click "Create User"
6. ✅ Success message appears
7. User appears in table with ID
8. Send credentials to new user
```

### Workflow 2: Promote User to Admin

```
1. Locate user in table: "researcher01"
2. Note current status: "❌ No"
3. Select "researcher01 (ID: 2)" from dropdown
4. Click "👑 Toggle Admin (Regular User → Admin)"
5. ✅ Status updated message
6. Page refreshes
7. Table shows: "✅ Yes" for Admin column
```

### Workflow 3: Reset Forgotten Password

```
1. User reports forgotten password
2. Admin selects user from dropdown
3. Clicks "🔑 Reset Password"
4. Enters new temporary password
5. Clicks confirm
6. ✅ Success message
7. Sends new password to user (secure channel)
```

### Workflow 4: Remove Old Account

```
1. Identify inactive user in table
2. Select user from dropdown
3. Click "🗑️ Delete User"
4. Read warning message
5. Click "⚠️ Confirm Delete"
6. ✅ Deletion confirmed
7. User removed from table
8. Page refreshes automatically
```

## Localization

All UI elements support English and Spanish:

### Language Toggle Example

```
English:
┌──────────────────────────────┐
│ ➕ Create New User           │
│ Username: [_________]        │
│ Password: [_________]        │
│ [x] Make Admin               │
│ [Create User]                │
└──────────────────────────────┘

Spanish:
┌──────────────────────────────┐
│ ➕ Crear Nuevo Usuario       │
│ Nombre de Usuario: [______] │
│ Contraseña: [_________]      │
│ [x] Hacer Administrador      │
│ [Crear Usuario]              │
└──────────────────────────────┘
```

## Error Handling

### Validation Errors

```
❌ Username is required
❌ Password is required
❌ Password must be at least 3 characters
```

### Operation Errors

```
❌ Failed to create user: username already exists
❌ Failed to delete user: database error
❌ You cannot delete your own account
```

### Success Messages

```
✅ User 'researcher01' created successfully
✅ Admin status updated for user 'researcher01'
✅ Password reset successfully for user 'researcher01'
✅ User 'researcher01' deleted successfully
```

## Technical Details

### State Management

- Uses Streamlit's `st.rerun()` for immediate UI updates
- Form state managed with unique keys
- Session state preserved across reruns

### Security

- Admin-only access (checked on page load)
- Password hashing (SHA256)
- Cannot delete own account
- Confirmation required for destructive actions

### Performance

- Single database query for user list
- Lazy loading of group memberships
- Efficient session management

## Accessibility

- Clear labels and instructions
- Color-coded status (✅/❌)
- Emoji icons for quick recognition
- Confirmation dialogs for destructive actions
- Disabled buttons with helpful tooltips

---

**Navigation**: [← Back to Documentation](../README.md) | [User Management Implementation →](USER_MANAGEMENT_UI_ENHANCEMENT.md)
