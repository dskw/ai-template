---
name: plan-close
description: Closes the active plan with the test suite, memory consolidation, wiki update, tuning, extension decisions, bug verification, plan review and the plan gate. Use it when the status prints that no step is open.
---
# plan-close

The rules are in `docs/DOCS_CONVENTIONS.md`, sections Plan close, Tuning and Gates.

## Procedure
1. Run `python -m tools.progress status`. Continue only when it prints that no step is open.
2. Run `python -m tools.test`. Fix each failure first.
3. Run `memory-consolidate`.
4. Compare the changes of the plan with the pages in `docs/wiki/`. Update each page that the changes make wrong or incomplete.
5. Run `python -m tools.plan_close tuning`. Decide for each line that starts with `tune` whether a rule change helps. Prepare the change when it does.
6. Show the user each entry of `extensions.md` without decision and each prepared tuning change. Ask for the decisions.
7. Write each decision into `extensions.md`. Run `python -m tools.progress add-feature` for each approved entry. When the new feature conflicts with an item of `Out of scope`, run `python -m tools.progress out-of-scope remove "<item>"` in the same turn.
8. Apply the tuning changes that the user agreed to.
9. Run `python -m tools.plan_close check`. For a manual check, prepare the package of the section Manual verification of `step-run` in `docs/plans/<plan>/tmp/manual-check/`. Ask the user and pass the answer as the tool prints.
10. For a fix plan, run `bug-fix`.
11. Commit the writes of the steps before.
12. When a protected path changed, ask the user and run `python -m tools.approve <plan> close --answer <yes|no>`.
13. Run `review-plan`.
14. Ask the user to close the manual check package. Run `python -m tools.plan_close`. Fix each item that the gate names.
15. When the tool prints `changed after review`, run `review-plan` one more time.

## Rules
- When the agent recommends no tuning change, it applies none and does not mention tuning to the user.
- The plan review is the last agent activity before step 14. Do not change a file after it.
- A failing acceptance check does not stop the close. The feature stays `in progress` and needs one more plan.
- The plan close writes no version. The milestone close writes the version and the changelog entry.
- Add a feature of an approved extension with the type and the milestone that the user gives.
