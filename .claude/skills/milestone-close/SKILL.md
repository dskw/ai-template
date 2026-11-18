---
name: milestone-close
description: Runs the acceptance checks of the open milestone and closes it, or closes it early and moves the open features and bugs to a new milestone. Use it when the status prints that the milestone has no open feature and no bug, or when the user asks for a premature close.
---
# milestone-close

The rules are in `docs/DOCS_CONVENTIONS.md`, sections Milestone close and Gates.

## Procedure
1. Run `python -m tools.progress status`. Stop when a plan is active.
2. Run `python -m tools.test`, the whole suite. For each failure, run `bug-report`, stop the close and create a fix plan with `plan-create`.
3. Run `python -m tools.milestone_close check`.
4. For a manual check, put the package of the section Manual verification of `step-run` into the milestone package folder of `docs/DOCS_CONVENTIONS.md`. Ask the user and pass the answer as the tool prints.
5. Ask the user to close the package. Run `python -m tools.milestone_close`. It writes the version and the changelog entry from the done features and the fixed bugs. Fix each item that the gate names and run it again.
6. When the tool lists files with a merge conflict, resolve them and run `git add`.
7. Run `python -m tools.check` and `python -m tools.test`. Then run `python -m tools.milestone_close` one more time.
8. When the status prints a draft milestone, follow the section Next draft.

## Next draft
1. Take the draft with the lowest id. Ask the user whether to open it now, or which other draft to open.
2. Check the draft against the closed milestone. Look for a feature that the closed milestone already delivered, dropped or changed. Look for an acceptance that no longer fits and for an out of scope item that is done now. Show the user each difference and the change that you propose.
3. Change the draft with the section Change of a draft of `milestone-create`. Its document review covers the changed lines. Without a change, run no review.
4. Run `python -m tools.milestone_create open <id>`.

## Premature close
1. Use this procedure only when the user asks to close the milestone early.
2. Close the active plan first with `plan-close`.
3. Ask the user for the goal of the new milestone and for the features to add.
4. Ask the user whether the open features and bugs go into the first draft or into a new milestone before the drafts.
   Run `milestone-create` for that milestone as a premature close. It writes or changes the draft, runs the document review and commits the draft.
5. Run `python -m tools.milestone_close migrate <id of the new milestone>`.
6. On a merge conflict, follow steps 5 and 6 of the procedure with the migrate command.
