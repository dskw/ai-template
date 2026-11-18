---
name: project-update
description: Changes one or more project bindings after the first run, for example a new language, a different formatter, a pipeline or an MCP server. Use it only when no plan is active.
---
# project-update

The procedure and the formats are in `docs/DOCS_CONVENTIONS.md`, section Project init and update.

## Procedure
1. Run `python -m tools.progress status`. Stop when a plan is active.
2. Ask the user which binding changes. A binding is a question of `project-init`, the test report or the test support folder.
3. Ask one question per changed binding. Show the current value as the first option.
4. Follow the question rules of `project-init`.
5. For an MCP server, state in one line what it gives the agent and which step type uses it.
6. Prepare the writes of the changed bindings only. The list of binding files is in `project-init`.
7. Show the user a summary of all writes. Ask for one confirmation: confirm, change an answer, or stop.
8. After the confirmation, write the files.
9. Run `python -m tools.project update`. Fix each item that it names and run it again.
