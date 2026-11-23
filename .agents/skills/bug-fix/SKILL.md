---
name: bug-fix
description: Verifies each fixed bug of a fix plan at plan close and records the verified bugs. Use it from plan-close before the plan review.
---
# bug-fix

The rules are in `docs/DOCS_CONVENTIONS.md`, sections Bugs and Plan close.
Before each command with `--answer`, ask the user in the chat and wait for the answer. A request for a change is not its approval. Run that command alone, with no second command.

## Procedure
1. Read the bug ids from the field `bugs` of the active plan.
2. For a bug with a manual check, run `python -m tools.plan_close check <bug>`. When it asks, ask the user and run it again with `--answer <yes|no>`. Never pass an earlier answer of the user on to a later gate. The tool decides whether an earlier pass still holds.
3. Run `python -m tools.plan_close verify-bug <bug>` for each bug.
4. Report each bug that the tool did not verify, with the reason that the tool prints.

## Rules
- This skill verifies only. It writes nothing to the milestone file.
- The tool checks that the acceptance passes now.
- For a regression test, the tool checks that the evidence shows a failing run before a passing run.
- A bug that the tool did not verify stays in the `Bugs` table after the plan close.
