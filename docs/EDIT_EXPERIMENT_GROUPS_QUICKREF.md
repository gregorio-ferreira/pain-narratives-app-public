# Quick Reference: Edit Experiment Groups

## 🚀 Quick Access

**Management Tab** → **User Administration** → **Edit Experiment Groups**

---

## ⚡ Quick Actions

### Assign Groups

```
1. Select user from dropdown
2. Enter group IDs: "1, 3, 5"
3. Click "💾 Save Groups"
```

### Remove All Groups

```
1. Select user from dropdown
2. Clear input field (leave empty)
3. Click "💾 Save Groups"
```

### View Available Groups

```
1. Expand "📋 Available Groups"
2. Note the IDs you need
3. Use those IDs in the input field
```

---

## ✅ Valid Input Examples

| Input      | Meaning                   |
| ---------- | ------------------------- |
| `1, 3, 5`  | Assign groups 1, 3, and 5 |
| `12`       | Assign group 12 only      |
| `2, 4`     | Assign groups 2 and 4     |
| `` (empty) | Remove all groups         |

---

## ❌ Common Errors

| Input        | Error                        | Fix                    |
| ------------ | ---------------------------- | ---------------------- |
| `1; 3; 5`    | Invalid format (semicolons)  | Use commas: `1, 3, 5`  |
| `1, abc, 5`  | Invalid format (non-numeric) | Use only numbers       |
| `1, 99999`   | Group 99999 doesn't exist    | Check available groups |
| Extra spaces | None - automatically trimmed | No action needed       |

---

## 🔍 Where to Find Information

### Current User Groups

Look at "Experiment Groups" column in user table

### Available Groups

Click "📋 Available Groups" to expand full list

### Current Groups for Selected User

See "Current Groups: X, Y, Z" info box

---

## 💡 Pro Tips

✅ **Check available groups first** before assigning  
✅ **Use commas to separate** multiple group IDs  
✅ **Verify in user table** after saving  
✅ **Empty input is valid** to remove all groups

❌ **Don't use semicolons** - use commas  
❌ **Don't guess group IDs** - check available groups  
❌ **Don't forget to save** - click the button!

---

## 🌍 Language Support

Switch language in sidebar:

- 🇬🇧 English
- 🇪🇸 Spanish (Español)

---

## 📞 Need Help?

See full guides:

- **Technical:** `docs/EDIT_EXPERIMENT_GROUPS_FEATURE.md`
- **Visual Guide:** `docs/EDIT_EXPERIMENT_GROUPS_GUIDE.md`
- **Summary:** `docs/EDIT_EXPERIMENT_GROUPS_SUMMARY.md`
