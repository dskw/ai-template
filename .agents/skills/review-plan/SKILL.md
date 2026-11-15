---
name: review-plan
description: Runs the reviewer agent on the whole plan, adds fix steps for open Important problems and records the review pass. Use it from plan-close after the commit of every other write of the close.
---
# review-plan

The rules are in `docs/DOCS_CONVENTIONS.md`, section Plan close. The problem format is in `docs/REVIEW.md`.

## Procedure
1. Run `python -m tools.plan_close reviewed`. It prints the review round.
2. Start the `reviewer` agent in a fresh context with the scope plan review.
3. Give it the plan folder, the notes of the implementor and the round. In a later round, add the problem rows of the round before with their answers.
4. Write one row per posted problem into the `Problems` table with `plan` in the `Step` column. Run `python -m tools.check` with the path of the problems file and fix each sentence that it names.
5. In a later round, write the result of the reviewer into the `Check` cell of each problem of the round before.
6. For each `Pre-existing` problem, run `bug-report` with the plan id and the problem id as source. Write `bug <id>` as its answer.
7. Start the `implementor` agent with the plan folder and the problem rows. It answers each problem and commits each fix.
8. When the round posted an `Important` problem, start again at step 1 for the next round, up to round 3.
9. When an `Important` problem is open after round 3, follow the section Fix step.
10. Commit all changes except `problems.md`. Run `python -m tools.plan_close review-passed`.

## Fix step
1. Find the step that the location of the problem belongs to.
2. Run `python -m tools.step_close add-fix <problem> <step>`.
3. Run `step-run` for the fix step.
4. Start again at step 1 of the procedure.
5. When the tool refuses the fix step, or the fix step has the state `blocked`, follow the section Blocked plan.

## Blocked plan
1. Run `python -m tools.plan_close block`.
2. Show the user the open problems. Ask for one of the three choices: `accept`, `drop` or `replan`.
3. For `accept`, run `python -m tools.plan_close unblock accept "<reason of the user>"`. Then run `bug-report` for each accepted problem.
4. For `drop`, run `python -m tools.plan_close unblock drop <id> "<reason of the user>"`.
5. For `replan`, run `python -m tools.plan_close unblock replan <id>`.
6. Continue at step 10 of the procedure.
