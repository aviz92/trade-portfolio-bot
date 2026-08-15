# Claude Code — Slash Commands Reference

> **Tip:** Type `/` in any session to see all available commands. Type `/` + letters to filter.

---

## 🗂️ Context Management

### `/compact [instructions]`
Compresses the current conversation into a summary, allowing you to continue without hitting context limits.
Pass optional instructions to control what's preserved:
```
/compact Focus on the authentication implementation and database schema decisions
```
**Rule of thumb:** Use `/compact` when context usage exceeds 80%, and `/clear` when switching tasks.

### `/clear`
Wipes the conversation history clean. Use when you want a fresh start or when context gets too cluttered.

### `/context`
Visualizes your current context usage — messages, file contents, tool outputs — and shows how close you are to the limit.

---

## 💬 Side Questions — `/btw` ⭐

Introduced in Claude Code 2.1.72 (March 2026).

Lets you ask a quick question **without adding it to the conversation history**. Claude spawns a temporary ephemeral agent in read-only mode — no tools, no persistence, the exchange is discarded after you close it.

**Why it matters:** Consistent use of `/btw` can reduce total token consumption by up to 50% in sessions with frequent mid-task questions.

**Heuristic:**
- Is this *advancing* the primary task? → Main thread
- Is this a *supporting* question or context addition? → `/btw`

```
/btw What does the calculate_metrics function return in this context?
```

> `/btw` is the inverse of a subagent: it **sees** your full conversation but has **no tools**.
> A subagent has full tools but starts with an empty context.

---

## 🛠️ Code Quality

### `/diff`
Shows exactly what Claude changed — equivalent to `git diff --staged` but more convenient.
**Pair with `/rewind`:** if `/diff` reveals something you don't like, rewind and try a different approach.

### `/rewind` (also `Esc Esc`)
Rolls back the conversation to a previous point.
Key feature: **selective rollback** — "Rewind code only" reverts all file changes while keeping the conversation history intact.
> Try an aggressive refactoring → discuss results → decide it didn't work → revert only the code, keep the diagnostic conversation.

### `/simplify`
Runs a three-agent review pipeline checking for:
- Architectural issues
- Duplicate logic
- Performance inefficiencies

Designed as a **quality gate before PRs**, not during active development.

---

## 📊 Session Info

### `/cost`
Shows detailed token usage statistics and estimated costs for the current session.

### `/status`
Shows version info and connectivity status. Useful for troubleshooting.

### `/model`
Switch the active model mid-session (e.g. Opus ↔ Sonnet based on task complexity).

### `/usage`
Shows your current usage against your subscription plan limits.

---

## ⚙️ Built-in Skills (bundled)

Unlike slash commands (fixed-logic), skills are **prompt-based** — they can spawn subagents and orchestrate multi-step workflows.

| Skill | What it does |
|-------|-------------|
| `/batch` | Large-scale changes across multiple files in parallel, with auto PR creation |
| `/loop` | Performs actions on a recurring interval |
| `/debug` | Structured debugging workflow |
| `/effort [low/medium/high/max]` | Controls how deeply Claude thinks (and how many tokens it spends) |
| `/review` | Code review (deprecated in favor of `/simplify`) |

---

## 🎯 Workflow & Planning

### `/plan` (also `Shift+Tab`)
Puts Claude in **read-only mode** — it can analyze your codebase but can't make changes.
All proposed modifications are presented as plans requiring explicit approval.
> Use for production-critical files, database migrations, or any task where you want to understand scope before committing.

### `/memory`
Opens your `CLAUDE.md` files for editing. Update persistent project-level instructions.

### `/init`
Creates a `CLAUDE.md` file for the current project with instructions for consistent Claude behavior.

### `/resume`
Browse and resume previous sessions interactively.

### `! <shell command>` (bash prefix)
Run shell commands directly with full conversation context. The output becomes part of the conversation.
```
! git status
! pytest tests/ -x
! cat src/config.py
```

---

## 🔌 MCP Commands

MCP servers can expose their own prompts as commands, discovered dynamically in the format:
```
/mcp__<server>__<prompt>
```
Example: `/mcp__github__create-pr`

---

## 🔑 Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+F` (×2) | Kill all background agents instantly |
| `Shift+Tab` | Cycle: normal → auto-accept → plan mode |
| `Esc Esc` | Rewind last action |
| `Tab` | Toggle extended thinking |
| `Option+T` / `Alt+T` | Extended thinking toggle |
| `Option+P` / `Alt+P` | Model picker |
| `Ctrl+G` | Open external editor |
| `Ctrl+C` (×2) | End session |

---

## 🔧 Custom Commands / Skills

Store reusable prompts as markdown files:

| Location | Scope |
|----------|-------|
| `.claude/skills/<name>/SKILL.md` | Project-level (shared with team) |
| `~/.claude/skills/<name>/SKILL.md` | Personal (all projects) |

Minimal example — `.claude/skills/run-tests/SKILL.md`:
```yaml
---
name: run-tests
description: Run the pytest suite with coverage
allowed-tools: Bash(pytest:*)
---
Run: pytest $ARGUMENTS --cov --tb=short
```
Invoked as: `/run-tests tests/unit/`

> **Legacy path** `.claude/commands/*.md` still works but skills are the recommended approach going forward.

---

## 🧠 Strategy Summary

| Situation | Command |
|-----------|---------|
| Approaching context limit | `/compact` |
| Switching to a new task | `/clear` |
| Quick question mid-task | `/btw` |
| Before committing code | `/diff` + `/simplify` |
| Something went wrong | `/rewind` |
| Risky change on prod files | `/plan` first |
| Tracking token spend | `/cost` |
| Need a faster/cheaper response | `/effort low` |
| Long running session, check fuel gauge | `/context` |
