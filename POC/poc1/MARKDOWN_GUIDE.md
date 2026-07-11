# Markdown Files Guide

This project uses several `.md` files to track progress, issues, and fixes. Here's how to use each one:

---

## 💡 Important: Keep It Simple

> **All markdown files in this project (except `README.md`) are primarily for the AI developer agent.**
> - Do **NOT** over-engineer them with excessive formatting, elaborate tables, or verbose explanations.
> - Keep content **concise, factual, and actionable**.
> - `README.md` is the only file meant for human readers — it should be polished and comprehensive.
> - You (the human) may read these files, but you rely on the AI to interpret and act on them.

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

## 🧪 Testing

### `UNIT_INTEGRATION_TESTING_GUID.md` — **Unit & Integration Testing Guide**
- **Purpose**: Reference guide for writing and running unit and integration tests
- **When to use**: As a reference for test standards, frameworks, and execution commands
- **Covers**: Unit testing (isolated component tests), integration testing (cross-component tests), test environment setup, pytest usage

## 📝 Planning

### `bug_fix_plan.md` — **Bug Fix Plans**
- **Purpose**: Detailed plan for fixing complex bugs
- **When to use**: Before fixing a non-trivial bug, document the approach

---

## 📋 Log Files

### `LMStudioLogs.log` — **LM Studio Application Logs**
- **Purpose**: Contains logs copied from LM Studio's internal logging system
- **How to populate**: Copy logs from LM Studio's application logs and paste them into this file manually
- **Time validation**: The file's update time should be within or after the dates found in `terminal.log`. This ensures the LM Studio logs correspond to the same session or timeframe as the application's terminal logs
- **Use case**: Debugging language model interactions, API calls, and LM Studio-specific issues

### `terminal.log` — **Terminal Application Logs**
- **Purpose**: Contains terminal logs captured after running the application
- **When generated**: Created when running the app from the terminal (e.g., `python app.py` or `python src/main.py`)
- **Use case**: Captures application startup messages, runtime errors, console output, and general application behavior

---

## 📊 Quick Reference

| File | Use | Status |
|------|-----|--------|
| `implementation_progress.md` | Work in progress / planned | Active |
| `completed_progress.md` | Completed work archive | Historical |
| `issues_tracker.md` | Open bugs & problems | Active |
| `solved_issues.md` | Fixed issues archive | Historical |
| `bug_fix_plan.md` | Complex bug fix plans | Per-incident |
| `UNIT_INTEGRATION_TESTING_GUID.md` | Unit & integration testing reference | Reference |
| `LMStudioLogs.log` | LM Studio application logs (copy from LM Studio) | Reference |
| `terminal.log` | Terminal output logs (from running the app) | Reference |

---

## 🔄 Workflow Summary

```
1. Discover task/bug
2. Add to implementation_progress.md or issues_tracker.md
3. Work on it
4. Move to completed_progress.md or solved_issues.md when done
5. Write tests following UNIT_INTEGRATION_TESTING_GUID.md
