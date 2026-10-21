---
name: gsd
description: Spec-driven development workflow system (Get Shit Done) for Antigravity. Use when the user requests spec-driven planning, GSD commands, full autonomous development (/gsd-super), phase-based project roadmaps, anti-hallucination technical research (/gsd-no-halluc), or project memory distillation.
---

# GSD (Get Shit Done) for Antigravity

A spec-driven development framework designed to eliminate context rot, prevent hallucinations, and provide structured autonomous development across AI models.

## Core Workflows & Commands

When a GSD workflow is invoked, consult the corresponding workflow guide in the `workflows/` directory:

| Command | Workflow File | Description |
| :--- | :--- | :--- |
| `/gsd-super [prompt]` | [gsd-super.md](./workflows/gsd-super.md) | **Super Mode**: Full "walk-away" autonomy from prompt/PRD to tested production code. |
| `/gsd-no-halluc [query]` | [gsd-no-halluc.md](./workflows/gsd-no-halluc.md) | **Anti-Hallucination Q&A**: Strict technical research requiring live tool verification (`search_web`/`read_url_content`) with confidence scores. |
| `/gsd-commit-memory` | [gsd-commit-memory.md](./workflows/gsd-commit-memory.md) | **Project Memory**: Distills major architectural decisions into `.planning/memory/` across conversation boundaries. |
| `/gsd-new-project` | [gsd-new-project.md](./workflows/gsd-new-project.md) | Initialize project requirements, research, and phase roadmaps in `.planning/`. |
| `/gsd-discuss [N]` | [gsd-discuss.md](./workflows/gsd-discuss.md) | Capture user preferences and decisions for Phase `N`. |
| `/gsd-plan [N]` | [gsd-plan.md](./workflows/gsd-plan.md) | Research and generate atomic XML task plans for Phase `N`. |
| `/gsd-execute [N]` | [gsd-execute.md](./workflows/gsd-execute.md) | Execute Phase `N` plans with atomic git commits and verification gates. |
| `/gsd-verify [N]` | [gsd-verify.md](./workflows/gsd-verify.md) | User acceptance testing and verification suite for Phase `N`. |
| `/gsd-quick [task]` | [gsd-quick.md](./workflows/gsd-quick.md) | Rapid ad-hoc task execution with GSD quality guarantees. |
| `/gsd-progress` | [gsd-progress.md](./workflows/gsd-progress.md) | Display current roadmap state, completed phases, and roadblocks. |
| `/gsd-help` | [gsd-help.md](./workflows/gsd-help.md) | Show full command reference and guidelines. |

## Subagent Personas

When delegating specialized phases, follow the role instructions in `agents/`:
- **Planner**: [gsd-planner.md](./agents/gsd-planner.md)
- **Executor**: [gsd-executor.md](./agents/gsd-executor.md)
- **Verifier**: [gsd-verifier.md](./agents/gsd-verifier.md)
- **Debugger**: [gsd-debugger.md](./agents/gsd-debugger.md)
- **Codebase Mapper**: [gsd-codebase-mapper.md](./agents/gsd-codebase-mapper.md)
- **Roadmapper**: [gsd-roadmapper.md](./agents/gsd-roadmapper.md)

## Protocols & Guarantees

1. **File-First Context**: Always re-read active workspace files before editing; never assume state from past conversation turns.
2. **5-Tier Verification**: Verify tasks through `Syntax -> Types -> Lint -> Tests -> Build` before declaring completion.
3. **Atomic Commits**: Group work into atomic, single-intent commits per task.
4. **Anti-Hallucination**: If an API or syntax detail is uncertain, perform research using web or local inspection tools before drafting code.
