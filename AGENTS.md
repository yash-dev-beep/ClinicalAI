# Project Workflow Guidelines: Ralph Loop, CodeRabbit & GSD

This project integrates three complementary workflows: **GSD (Get Shit Done)**, **Ralph Wiggum Loop**, and **CodeRabbit**. Follow these operating principles:

---

## 1. Spec-Driven Planning & Execution (GSD)
- **Planning & Roadmaps**: Use GSD workflows located in `.agent/workflows/` (or `.agents/skills/gsd/workflows/`) for multi-step feature additions and roadmap planning (`/gsd-new-project`, `/gsd-plan`, `/gsd-execute`).
- **Autonomous Delivery**: For end-to-end task execution with strict verification gates, trigger `/gsd-super`.
- **Anti-Hallucination & Research**: Never guess APIs or library functions. Use `/gsd-no-halluc` or verify via `search_web` and `read_url_content` with clear confidence attribution before proposing solutions.
- **Project Memory**: Capture significant architectural decisions and pivots in `.planning/memory/` using `/gsd-commit-memory`.
- **Atomic Commits**: Group work into atomic, single-intent commits per task.

---

## 2. Iterative Autonomous TDD (Ralph Loop)
- **Continuous Refactoring & Test Loops**: Use `ralph-loop` when iterative test-driven development or hard backpressure is required.
- **Deterministic Backpressure**: Always supply `--test-cmd "<cmd>"` (e.g., `pytest` or `python test_ui.py`) and a clear `--completion-promise '<TEXT>'`.
- **Safe Bounds**: Keep `--max-iterations` bounded (default: 10, typically 5-10 in chat sessions) to avoid unbounded token consumption.
- **Discipline**: Work on exactly ONE priority item per turn in `.ralph/fix_plan.md`. Never weaken or remove tests to make a build pass.

---

## 3. Automated Code Review & Quality Gates (CodeRabbit)
- **Pre-Completion Review**: Before finalizing features or closing milestones, run a CodeRabbit CLI review (`code-review` or invoke the `code-reviewer` subagent).
- **Security & Lint Standards**: Inspect potential security vulnerabilities, type mismatches, and edge cases highlighted by CodeRabbit.
- **Autofix Validation**: When applying reviewer feedback (`autofix`), review each diff individually before applying.
