# Agent instructions

## Project
Not initialized. Run the `project-init` skill. The design documents are in `docs/design/`.

## Conventions
- `docs/CODE_CONVENTIONS.md`: read it before you write or review code.
- `docs/TEST_CONVENTIONS.md`: read it before you write, change or review a test.
- `docs/DOCS_CONVENTIONS.md`: read it before you write a document, run a skill or change the setup.
- `docs/REVIEW.md`: read it before you review a change or change a protected path.
- `docs/ai-setup-adjustments.md`: add a finding when the AI setup causes a problem. Keep it independent of the project.

## Status
Run `python -m tools.progress status` at session start when no hook injected its output. Continue with the step it prints. Never start a different step. When it prints `bugfix phase`, start a fix plan with `plan-create`.

## Skills
- `project-init`: binds the setup to the project. Use it once, before the first milestone.
- `project-update`: changes a project binding. Use it for a new language, tool, pipeline or MCP server.
- `milestone-propose`: proposes the next milestone. Use it when the user asks for suggestions.
- `milestone-create`: writes a milestone. Use it when no milestone is open.
- `plan-create`: writes a plan for open features or for bugs. Use it when no plan is active.
- `step-run`: implements the step that the status prints.
- `review-step`: reviews the step in progress. `step-run` calls it.
- `plan-close`: closes the active plan when no step is open.
- `review-plan`: reviews the whole plan. `plan-close` calls it.
- `bug-report`: adds a bug to the open milestone.
- `bug-fix`: verifies the fixed bugs of a fix plan. `plan-close` calls it.
- `milestone-close`: closes the open milestone, or closes it early on user request.
- `idea-add`: records an idea for a later milestone.
- `idea-remove`: removes planned or dropped ideas. `milestone-create` calls it.
- `memory-save`: creates or updates a memory.
- `memory-consolidate`: reviews, merges and deletes memories. `plan-close` calls it.

## Memory
- Read `docs/MEMORY.md` at session start when no hook injected it. Open an entry file only when its index line is relevant to the task.
- Save a memory when the user corrects you, confirms an approach that is not obvious, or makes a decision that the code does not show.
- Save a memory when you find an environment fact that a later session must find again without it.
- Never save progress, status, architecture, file paths, bug fixes, a rule of the conventions or a fact that the code shows.
- A memory is a hint to verify, not a fact. When the code contradicts it, correct or delete it in the same turn.
- Write memory files through `memory-save` only. Never edit `docs/MEMORY.md` by hand.
- Never save an idea for a feature as a memory. Use `idea-add`.

## Language
Every text follows the writing rules of `docs/DOCS_CONVENTIONS.md`.
