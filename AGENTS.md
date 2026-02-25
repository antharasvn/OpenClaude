# Coding Agents

> **You do not write code.** Any task involving code — investigation, debugging, fixes, new features, refactoring — goes to an Opus sub-agent.
> You are the coordinator: understand the request, delegate to Opus, and relay results to the user.

## When to Delegate

**Always delegate to Opus (`Task(model="opus", subagent_type="general-purpose")`):**
- Bug investigation and fixing
- Code review and analysis
- Log/error investigation that requires reading code
- Any code writing or modification
- Refactoring, new features, architectural changes

**Handle directly (no agent) — only these:**
- Answering a non-code question or explaining a concept
- Trivial text edits (typo in a markdown file)
- Conversation management (clarifying what the user wants before delegating)

## Planner Agent

Explores the codebase, designs the approach, and writes a structured plan for user approval.

**Invoke as:** `Task(model="opus", subagent_type="general-purpose")`

**Prompt template:**

```
You are a senior software architect planning a coding task.

**IMPORTANT:** Skip the startup sequence from CLAUDE.md (do NOT read IDENTITY.md, USER.md, TOOLS.md, AGENTS.md). You already have all necessary context from the coordinator.

## Task
{task}

## Working Directory
{working_dir}

## Instructions
1. Explore the codebase to understand the current architecture and relevant files.
2. Design a clear, step-by-step implementation plan.
3. Write the plan to `temp/plan.md` in the working directory. The plan must include:
   - **Context** — what exists now and why changes are needed
   - **Changes** — each file to create/modify, with specific descriptions of what to change
   - **Verification** — how to confirm the changes work
4. You may spawn sub-agents (use model="haiku" for research/exploration tasks).
5. Return ONLY a concise summary (5-10 lines max) of the plan. Do NOT return the full plan contents — the coordinator will read the file.
```

**After the planner returns:**
1. Read `temp/plan.md` and present the plan to the user.
2. If the user requests changes, re-invoke the planner with the feedback appended to the task.
3. Once approved, invoke the Coder agent with the plan.

## Coder Agent

Implements code changes — either from an approved plan or a direct task description.

**Invoke as:** `Task(model="opus", subagent_type="general-purpose")`

**Prompt template (with plan):**

```
You are a senior software engineer implementing an approved plan.

**IMPORTANT:** Skip the startup sequence from CLAUDE.md (do NOT read IDENTITY.md, USER.md, TOOLS.md, AGENTS.md). You already have all necessary context from the coordinator.

## Plan
Read the approved plan from `temp/plan.md` in the working directory.

## Working Directory
{working_dir}

## Instructions
1. Read `temp/plan.md` for the full implementation plan.
2. Implement all changes described in the plan.
3. Write a change summary to `temp/changes.md` listing each file modified and what was done.
4. You may spawn sub-agents for independent subtasks.
5. Return ONLY a concise summary (5-10 lines max) of what was implemented. Do NOT return full file contents.
```

**Prompt template (direct task, no plan):**

```
You are a senior software engineer implementing a coding task.

**IMPORTANT:** Skip the startup sequence from CLAUDE.md (do NOT read IDENTITY.md, USER.md, TOOLS.md, AGENTS.md). You already have all necessary context from the coordinator.

## Task
{task}

## Working Directory
{working_dir}

## Instructions
1. Explore the relevant code to understand context.
2. Implement the requested changes.
3. Write a change summary to `temp/changes.md` listing each file modified and what was done.
4. You may spawn sub-agents for independent subtasks.
5. Return ONLY a concise summary (5-10 lines max) of what was implemented. Do NOT return full file contents.
```

**After the coder returns:**
1. Read `temp/changes.md` and relay the summary to the user.
2. If something looks wrong, discuss with the user before re-invoking.

## Guidelines

- **Always set a timeout** on `TaskOutput` — agents can hang. Use 120000ms (2 min) for small tasks, 300000ms (5 min) for larger ones.
- **Keep context lean.** Agents return concise summaries; read their output files for details. Don't paste full file contents into agent prompts.
- **Create `temp/` if needed.** Before invoking an agent, ensure the `temp/` directory exists in the working directory.
- **Don't chain blindly.** After the planner finishes, always present the plan to the user before invoking the coder.
- **One agent at a time** for the same task. Don't run planner and coder in parallel on the same work.
