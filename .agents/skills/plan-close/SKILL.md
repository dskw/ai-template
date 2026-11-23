---
name: plan-close
description: Closes a plan in two parts. In the worktree it runs the sync, the wiki update and the plan review. In the main repository it runs the merge, the bug reports, memory consolidation, tuning, extension decisions, bug verification and the plan gate. Use it when the status prints that no step is open.
---
# plan-close

The rules are in `docs/DOCS_CONVENTIONS.md`, sections Plan close, Tuning and Gates.
Before each command with `--answer`, ask the user in the chat and wait for the answer. A request for a change is not its approval. Run that command alone, with no second command.

## Part 1: in the worktree of the plan
1. Run `python -m tools.progress status`. Continue only when it prints that no step is open.
2. Run `python -m tools.plan_close sync`. For a conflict, resolve the files, run `git add` and run the command again.
3. Start the `implementor` agent with the plan folder and the task to compare the changes of the plan with the pages in `docs/wiki/`. It reads the page map of the overview first and updates each page that the changes make wrong or incomplete. A change goes into the section of the page form that fits it. A new system gets a new page, a row in the page map and a line in the sidebar. A changed tuning value changes its table. The agent commits.
4. Run `review-plan` when the plan changed a source or a test file. A plan without such a change needs no plan review.
5. Tell the user that the plan is ready for the merge in the main repository.

## Part 2: in the main repository
1. Run `python -m tools.plan_close merge <plan>`. It runs the checks and the tests of the plan on the merged tree.
2. When the merge names a failure, go back to the worktree. A failing test goes into the task of `review-plan`, and a fix step carries the fix. Then run step 1 again.
3. Run `bug-report` for each `Pre-existing` problem without an answer, with the plan id and the problem id as source. Write the answer with `python -m tools.step_close answer-problem <problem> "bug <id>"`.
4. Run `bug-report` for each problem whose answer of the user accepts it. These are the `accept` choice of a blocked plan and each accepted problem of a step.
5. Run `memory-consolidate`. Run `memory-save` for each row of `extensions.md` with the prefix `Memory:`. Add a finding to `docs/ai-setup-adjustments.md` for each row with the prefix `Setup:`.
6. Run `python -m tools.plan_close tuning`. Decide for each line that starts with `tune` whether a rule change helps. Prepare the change when it does. For a `tune topic` line of a system of the project, run `dependency-add`. For a topic that came back, also weigh a research on its cause, with a refactor feature as its possible result.
7. Show the user each entry of `extensions.md` without decision and each prepared tuning change. State for each entry whether it names the cause of an open bug or of a problem that came back. Ask for the decisions.
8. Write each decision into `extensions.md`. A saved `Memory:` or `Setup:` row gets the decision `dropped` with the place as reason. Run `python -m tools.progress add-feature` for each approved entry. Use the type `refactor` for the decision `refactor`. Run `idea-add` with the source `agent` for each entry that fits no planned milestone. When the new feature conflicts with an item of `Out of scope`, run `python -m tools.progress out-of-scope remove "<item>"` in the same turn.
9. Apply the tuning changes that the user agreed to.
10. Run `python -m tools.plan_close check`. It accepts an earlier pass of a manual check while no product file changed since. Never pass an earlier answer of the user on to a later gate. The tool decides whether an earlier pass still holds. For a manual check, prepare the package of the section Manual verification of `step-run` in `docs/plans/<plan>/tmp/manual-check/`. Ask the user and pass the answer as the tool prints. A `MANUAL` line of the plan verification is a manual check too, also when each feature has a test as acceptance. The plan gate refuses the close without its passed record.
11. For a fix plan, run `bug-fix`. For a refactor plan, run `dependency-remove` for each dependency whose trigger the refactor removed.
12. Commit the writes of the steps before.
13. When a protected path changed, ask the user and run `python -m tools.approve <plan> close --answer <yes|no>`.
14. Ask the user to close the manual check package. Run `python -m tools.plan_close`. Fix each item that the gate names.
15. Name each problem that became a bug in the report to the user.

## Several plans in one session
Follow the section Several plans in one session of `step-run`. Run the tools of part 1 in a sub shell with the worktree of the plan as its directory. Run the tools of part 2 in a sub shell with the main repository as its directory. The wiki agent of part 1 is the one agent that writes in the worktree.

## Rules
- When the agent recommends no tuning change, it applies none and does not mention tuning to the user.
- One plan is in close at a time. Finish part 2 of a plan before the merge of the next plan.
- No write of part 2 changes a source file or a test file. The plan gate refuses such a change.
- A failing acceptance check does not stop the close. The feature stays `in progress` and needs one more plan.
- The plan close writes no version. The milestone close writes the version and the changelog entry.
- Add a feature of an approved extension with the type and the milestone that the user gives.
