# Markdown Files Guide

This project uses several `.md` files to track progress, issues, and fixes. Here's how to use each one:

---

## 📋 Progress Tracking

### `implementation_progress.md` — **In-Progress & Pending Items**
- **Purpose**: Track work that is **currently being done** or **planned for the future**
- **When to add**: Start a new task → add it here
- **When done**: Move the item to `completed_progress.md` and remove it from this file
- **Sections**:
  - `Implemented Features & Enhancements` — completed items (for reference)
  - `In-Progress / Pending Implementation` — active work

### `completed_progress.md` — **Completed Items Archive**
- **Purpose**: Historical record of all **finished** features, fixes, and improvements
- **When to add**: Task is complete → move entry here (cut from `implementation_progress.md`)
- **Do NOT**: Add in-progress items here — this file is for history only

**Workflow**: `implementation_progress.md` → (done) → `completed_progress.md`

---

## 🐛 Issue Tracking

### `issues_tracker.md` — **Active Issues**
- **Purpose**: Log bugs, problems, and technical issues
- **When to add**: Discover a bug or problem → add it here with status
- **Statuses**: `🔴 Open`, `🟡 In Progress`, `🟢 Solved`
- **When solved**: Move to `solved_issues.md`

### `solved_issues.md` — **Resolved Issues Archive**
- **Purpose**: Record of fixed issues for future reference
- **When to add**: Issue is resolved → move from `issues_tracker.md`

---

## 📝 Planning

### `bug_fix_plan.md` — **Bug Fix Plans**
- **Purpose**: Detailed plan for fixing complex bugs
- **When to use**: Before fixing a non-trivial bug, document the approach

---

## 📊 Quick Reference

| File | Use | Status |
|------|-----|--------|
| `implementation_progress.md` | Work in progress / planned | Active |
| `completed_progress.md` | Completed work archive | Historical |
| `issues_tracker.md` | Open bugs & problems | Active |
| `solved_issues.md` | Fixed issues archive | Historical |
| `bug_fix_plan.md` | Complex bug fix plans | Per-incident |

---

## 🔄 Workflow Summary

```
1. Discover task/bug
2. Add to implementation_progress.md or issues_tracker.md
3. Work on it
4. Move to completed_progress.md or solved_issues.md when done