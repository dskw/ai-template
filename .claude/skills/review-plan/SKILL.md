---
name: review-plan
description: Runs the reviewer agent on the whole plan in its worktree, adds fix steps for open Important problems and records the review pass. Use it from plan-close after the sync and the wiki update.
---
# review-plan

The rules are in `docs/DOCS_CONVENTIONS.md`, section Plan close. The problem format is in `docs/REVIEW.md`.
Before each command with `--answer`, ask the user in the chat and wait for the answer. A request for a change is not its approval. Run that command alone, with no second command.
An agent task holds the goal and its sources, with no implementation step and no test instruction. The rules are in `docs/DOCS_CONVENTIONS.md`, section Agent tasks.

## Procedure
1. Run `python -m tools.plan_close reviewed` in the worktree of the plan. It prints the review round. In round 1 it first runs each `COMMAND` check of the plan verification and prints each failing test.
2. Start the `reviewer` agent in a fresh context with the scope plan review.
3. Give it the plan folder, the notes of the implementor and the round. Name each test that failed in that run or at the plan merge. Name the dependency sources: the path that `python -m tools.project source` prints, unless it prints `none`. In a later round, add the problem rows of the round before with their answers.
4. Add one row per posted problem with `python -m tools.step_close add-problem plan <round> <severity> <rule> "<topic>" "<location>" "<trigger>" "<class>" "<fix>"`. When the tool names a broken rule, correct that value and run it again.
5. In a later round, write the result of the reviewer for each problem of the round before with `python -m tools.step_close check-problem <problem> "<check>"`.
6. Leave the answer of a `Pre-existing` problem empty. The plan close reports it as a bug.
7. Start the `implementor` agent with the plan folder and the problem rows. It answers each problem and commits each fix.
8. When the round posted an `Important` problem, start again at step 1 for the next round, up to round 3.
9. When round 3 posted an `Important` problem, run the short check after its fix: the reviewer confirms or re-raises each fix and posts nothing new. Write each result with `check-problem`. When an `Important` problem is still open, follow the section Open problem.
10. Commit all changes. Run `python -m tools.plan_close review-passed`.

## Open problem
1. Show the user each open problem, also a non-breaking one, with its trigger and its fix. Ask for a fix step or an acceptance with a reason.
2. For an acceptance, follow the section Blocked plan with the choice `accept`.
3. For a fix step, follow the section Fix step.

## Fix step
1. Find the step that the location of the problem belongs to.
2. Run `python -m tools.step_close add-fix <problem> <step>`.
3. Run `step-run` for the fix step.
4. Start again at step 1 of the procedure.
5. When the tool refuses the fix step, or the fix step has the state `blocked`, follow the section Blocked plan.

## Blocked plan
1. Run `python -m tools.plan_close block`.
2. Show the user the open problems. Ask for one of the three choices: `accept`, `drop` or `replan`.
3. For `accept`, run `python -m tools.plan_close unblock accept --answer "<reason of the user>"`. The plan close reports each accepted problem as a bug.
4. For `drop`, run `python -m tools.plan_close unblock drop <id> --answer "<reason of the user>"`. The plan merge writes the drop to the milestone.
5. For `replan`, run `python -m tools.plan_close unblock replan <id> --answer "<reason of the user>"`.
6. Continue at step 10 of the procedure.
