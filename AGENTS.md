# Coding Agents

## When to Delegate vs Handle Directly

**Handle directly (no agent needed):**
- Explaining a concept or answering a question
- Analyzing code to answer a question (no files will change)
- Clarifying what the user wants
- Trivial text edits (typo fix in a non-code file)

**Always delegate to Opus:**
- Any code writing or modification (even small fixes)
- Bug investigation that leads to a fix
- Code review with suggested changes
- New features, refactoring, architectural changes
- Log/error investigation where files will be changed

When in doubt: if files will change → delegate.

---

## Invoking Agents

**Model:** `Task(model="opus", subagent_type="general-purpose")`

Before invoking any agent:
1. Ensure `temp/` directory exists in the workspace
2. Generate a progress filename using the current timestamp:
   ```python
   from datetime import datetime
   progress_file = f"progress-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
   # e.g. progress-20260320-143025.md
   ```
   Pass this exact filename string into the agent prompt template.
3. After the agent returns: read `temp/{progress_file}`, write daily log to memory

---

## Planner Agent

Explores the codebase, designs the approach, writes a plan for user approval.

**Invoke as:** `Task(model="opus", subagent_type="general-purpose")`

**Prompt template:**
```
[SUBAGENT] You are a senior software architect planning a coding task.

## Task
{task}

## Working Directory
{working_dir}

## Progress file
Write your progress summary to: temp/{progress_file}
Format: what you explored, the plan you designed, any blockers found.

## Instructions
1. Explore the relevant codebase.
2. Design a clear, step-by-step implementation plan.
3. Write the plan to `temp/plan.md`.
   Include: Context, Changes (each file + what changes), Verification steps.
4. Write your progress summary to temp/{progress_file}.
5. Return a concise summary (5-10 lines) of the plan. Do NOT return full file contents.
```

**After planner returns:**
1. Read `temp/plan.md` and present the plan to the user.
2. Read `temp/{progress_file}` and write a daily log entry to memory.
3. If the user requests changes, re-invoke with feedback appended.
4. Once approved, invoke the Coder agent.

---

## Coder Agent

Implements code changes from an approved plan or direct task description.

**Invoke as:** `Task(model="opus", subagent_type="general-purpose")`

**Prompt template (with plan):**
```
[SUBAGENT] You are a senior software engineer implementing an approved plan.

## Plan
Read the approved plan from `temp/plan.md`.

## Working Directory
{working_dir}

## Progress file
Write your progress summary to: temp/{progress_file}
Format: files changed, what was done, any problems encountered.

## Instructions
1. Read `temp/plan.md` for the full implementation plan.
2. Implement all changes.
3. Write a change summary to `temp/changes.md` (files modified + what changed).
4. Write your progress summary to temp/{progress_file}.
5. Return a concise summary (5-10 lines). Do NOT return full file contents.
```

**Prompt template (direct task, no plan):**
```
[SUBAGENT] You are a senior software engineer implementing a coding task.

## Task
{task}

## Working Directory
{working_dir}

## Progress file
Write your progress summary to: temp/{progress_file}
Format: files changed, what was done, any problems encountered.

## Instructions
1. Explore relevant code for context.
2. Implement the requested changes.
3. Write a change summary to `temp/changes.md`.
4. Write your progress summary to temp/{progress_file}.
5. Return a concise summary (5-10 lines). Do NOT return full file contents.
```

**After coder returns:**
1. Read `temp/changes.md` and relay summary to the user.
2. Read `temp/{progress_file}` and write a daily log entry to
   `memory/t{TID}/{date}/coding-{timestamp}.md`.
3. If something looks wrong, discuss with the user before re-invoking.

---

## Guidelines

- **Always set a timeout** on `TaskOutput` — 120s for small tasks, 300s for larger ones.
- **Keep context lean.** Agents return concise summaries — read their output files for details.
- **One agent at a time** for the same task. Don't run planner and coder in parallel.
- **Don't chain blindly.** Always present the plan to the user before invoking the coder.
- **Progress files are disposable.** Delete them after writing the daily log (or leave for debugging).
