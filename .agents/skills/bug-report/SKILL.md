---
name: bug-report
description: Adds a bug to the open milestone with text, feature, source and acceptance. Use it in the main repository when the user reports a bug, when a plan close finds a pre-existing problem, or when the user accepts a problem of a plan.
---
# bug-report

The rules of a bug row are in `docs/DOCS_CONVENTIONS.md`, section Bugs.

## Procedure
1. Work in the main repository. Run `python -m tools.progress status`. When no milestone is open, run `milestone-create` for a milestone with bugs only.
2. Write the bug text. It names what the user sees. Never write a fix into the bug text.
3. Find the feature that the bug belongs to in the milestone files. Leave the feature empty when no feature matches.
4. Set the source: `user`, or the plan id and the problem id of the review.
5. Set the cause with its source: `user <cause>` when the user names it, `<research id> <cause>` when a research file names it. Leave it empty when nobody knows the cause.
6. Decide if a test can show the bug.
7. When a test can show it, the acceptance is `TEST <name> passes` with the name of the regression test. Do not write the test now.
8. When no test can show it, the acceptance is a manual check from `docs/design/` or from the user.
9. Ask the user for the acceptance when you cannot derive it.
10. Run `python -m tools.progress add-bug "<text>" "<feature>" "<source>" "<acceptance>" "<cause>"`.

## Rules
- A bug report during a plan does not change that plan.
- In the worktree of a plan, a bug of the user waits: tell the user to report it in the main repository.
- No review runs for a bug row. The tool validates it.
