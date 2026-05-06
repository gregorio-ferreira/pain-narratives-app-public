# Visual Guide: Editing User Experiment Groups

## Quick Start

This guide shows you how to manage which experiment groups a user can access.

---

## Step-by-Step Instructions

### 1. Access User Administration

**Login as Admin → Management Tab → User Administration**

```
┌─────────────────────────────────────────────┐
│  🏥 AINarratives - Management               │
├─────────────────────────────────────────────┤
│  Tabs: [Evaluation groups] [User Admin] ✓  │
└─────────────────────────────────────────────┘
```

---

### 2. View All Users

The user table shows each user's current experiment groups:

```
┌────────────────────────────────────────────────────────────┐
│  📊 All Users                                               │
├────┬───────────┬─────────┬────────────────────────────────┤
│ ID │ Username  │ Admin   │ Experiment Groups              │
├────┼───────────┼─────────┼────────────────────────────────┤
│ 2  │ andreas   │ ❌ No   │ 1, 3, 5                        │
│ 10 │ maria     │ ✅ Yes  │ 2, 4                           │
│ 15 │ john      │ ❌ No   │ -                              │
└────┴───────────┴─────────┴────────────────────────────────┘
```

**What you see:**

- **ID:** User's database ID
- **Username:** Login name
- **Admin:** Whether user has admin privileges
- **Experiment Groups:** Comma-separated list of group IDs (or "-" if none)

---

### 3. Select a User to Edit

```
┌─────────────────────────────────────────────┐
│  User Actions                                │
├─────────────────────────────────────────────┤
│  ✏️ Edit User:                              │
│  [Select user ▼]                            │
│  › andreas (ID: 2)                    ◄─── Click to select
│    maria (ID: 10)                           │
│    john (ID: 15)                            │
└─────────────────────────────────────────────┘
```

---

### 4. View Available Experiment Groups

Scroll down to the "Edit Experiment Groups" section and expand the available groups list:

```
┌─────────────────────────────────────────────────────────────┐
│  🧪 Edit Experiment Groups                                   │
├─────────────────────────────────────────────────────────────┤
│  📋 Available Groups                           [Expand ▼]   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ ID │ Description           │ Owner │ Status          │  │
│  ├────┼──────────────────────┼───────┼─────────────────┤  │
│  │ 1  │ Chronic Pain Study   │ 5     │ 🔄 Active       │  │
│  │ 2  │ Pain Assessment 2024 │ 3     │ 🔄 Active       │  │
│  │ 3  │ Clinical Trial       │ 5     │ ✅ Concluded    │  │
│  │ 4  │ Research Project     │ 7     │ 🔄 Active       │  │
│  │ 5  │ Validation Study     │ 3     │ 🔄 Active       │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**Note the IDs** of groups you want to assign to the user.

---

### 5. Current Groups Display

See which groups the user currently belongs to:

```
┌─────────────────────────────────────────────┐
│  ℹ️ Current Groups: 1, 3, 5                 │
└─────────────────────────────────────────────┘
```

---

### 6. Edit Group Assignments

Enter the new group IDs in the form:

```
┌─────────────────────────────────────────────────────────────┐
│  Enter Group IDs (comma-separated)                           │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 2, 4, 5                                               │  │
│  └───────────────────────────────────────────────────────┘  │
│  💡 Enter experiment group IDs separated by commas          │
│     (e.g., 1, 3, 5)                                         │
│                                                              │
│  [💾 Save Groups]                                           │
└─────────────────────────────────────────────────────────────┘
```

**Examples:**

| Input      | Result                            |
| ---------- | --------------------------------- |
| `1, 3, 5`  | Assign user to groups 1, 3, and 5 |
| `2, 4`     | Assign user to groups 2 and 4     |
| `12`       | Assign user to group 12 only      |
| `` (empty) | Remove all group assignments      |

---

### 7. Save and Verify

After clicking "💾 Save Groups":

**✅ Success:**

```
┌─────────────────────────────────────────────────────────────┐
│  ✅ Experiment groups updated successfully for user         │
│     'andreas'                                               │
└─────────────────────────────────────────────────────────────┘
```

The page automatically refreshes, and you'll see:

- Updated groups in the user table
- Updated "Current Groups" display

---

## Common Use Cases

### Use Case 1: Grant Access to Multiple Groups

**Scenario:** New researcher needs access to 3 different studies

```
1. Select user: "maria (ID: 10)"
2. View available groups
3. Enter: "1, 3, 7"
4. Click "💾 Save Groups"
5. Result: Maria can now access groups 1, 3, and 7
```

---

### Use Case 2: Revoke All Access

**Scenario:** User leaving project, remove all group access

```
1. Select user: "john (ID: 15)"
2. Current groups: "2, 4, 6"
3. Enter: "" (leave field empty)
4. Click "💾 Save Groups"
5. Result: John has no group access (shows "-" in table)
```

---

### Use Case 3: Transfer to Different Group

**Scenario:** Move user from study A to study B

```
1. Select user: "andreas (ID: 2)"
2. Current groups: "5"
3. Enter: "8"
4. Click "💾 Save Groups"
5. Result: Andreas moved from group 5 to group 8
```

---

## Error Messages

### Invalid Format

**Input:** `1, abc, 5` or `1; 3; 5`

```
┌─────────────────────────────────────────────┐
│  ❌ Invalid format: Please enter            │
│     comma-separated integers                │
└─────────────────────────────────────────────┘
```

**Fix:** Use only numbers separated by commas: `1, 3, 5`

---

### Group Not Found

**Input:** `1, 99999, 5` (where 99999 doesn't exist)

```
┌─────────────────────────────────────────────┐
│  ❌ Experiment group with ID 99999          │
│     does not exist                          │
└─────────────────────────────────────────────┘
```

**Fix:** Check available groups and use valid IDs only

---

### No Groups Available

**When:** Database has no experiment groups yet

```
┌─────────────────────────────────────────────┐
│  ⚠️ No experiment groups available          │
└─────────────────────────────────────────────┘
```

**Fix:** Create experiment groups first (Evaluation groups tab)

---

## Tips & Best Practices

### ✅ Do's

- **Check available groups** before editing
- **Use commas** to separate multiple IDs
- **Verify changes** in the user table after saving
- **Document assignments** for audit purposes
- **Test access** by logging in as the user

### ❌ Don'ts

- Don't use semicolons (`;`) - use commas (`,`)
- Don't enter non-existent group IDs
- Don't forget to save changes
- Don't assign users to concluded groups unless necessary

---

## Keyboard Shortcuts

| Action            | Shortcut               |
| ----------------- | ---------------------- |
| Navigate to field | `Tab`                  |
| Submit form       | `Enter`                |
| Clear field       | `Ctrl+A` then `Delete` |

---

## Workflow Diagram

```
┌─────────────────┐
│ Login as Admin  │
└────────┬────────┘
         │
         ▼
┌─────────────────────┐
│ Go to User Admin    │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│ Select User         │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│ View Available      │
│ Groups              │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│ Enter Group IDs     │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│ Click Save          │
└────────┬────────────┘
         │
         ▼
    ┌────┴────┐
    │ Valid?  │
    └────┬────┘
         │
    ┌────┴────┐
    │  Yes    │  No  ──┐
    │         │        │
    ▼         ▼        │
┌────────┐ ┌─────────┐│
│Success!│ │Error Msg││
└────────┘ └─────────┘│
    │         │        │
    └─────────┴────────┘
         │
         ▼
┌─────────────────────┐
│ Page Refreshes      │
└─────────────────────┘
```

---

## Language Support

This feature is fully localized in:

- 🇬🇧 **English**
- 🇪🇸 **Spanish (Español)**

Switch languages in the sidebar to see translated UI elements.

---

## Need Help?

**Common Questions:**

**Q: Can I assign a user to groups they don't own?**  
A: Yes, users can be assigned to any group regardless of ownership.

**Q: What happens to existing evaluations if I remove group access?**  
A: Historical data remains intact. The user just can't create new evaluations in that group.

**Q: Can regular users edit their own groups?**  
A: No, only administrators can modify group assignments.

**Q: How do I see which users belong to a specific group?**  
A: Filter the user table and look at the "Experiment Groups" column.

---

## Related Features

- **Create User:** User Administration → Create New User
- **Toggle Admin:** User Actions → Toggle Admin button
- **Reset Password:** User Actions → Reset Password button
- **Delete User:** User Actions → Delete User button
- **Create Groups:** Evaluation groups tab → Create New Evaluation group

---

## Version Information

- **Feature Added:** October 14, 2025
- **Version:** 1.0
- **Tested With:** PostgreSQL database, 33 users, 15 experiment groups
