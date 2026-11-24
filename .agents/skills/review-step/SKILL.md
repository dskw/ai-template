---
name: review-step
description: Runs the reviewer agent on the step in progress and writes the posted problems to the problems file of the plan. Use it from step-run after the step has evidence and a commit.
---
# review-step

The problem format is in `docs/REVIEW.md`. The file format is in `docs/DOCS_CONVENTIONS.md`, section Problems file.
An agent task holds the goal and its sources, with no implementation step and no test instruction. The rules are in `docs/DOCS_CONVENTIONS.md`, section Agent tasks.

## Procedure
1. Run `python -m tools.step_close review <step>`. It prints the review round.
2. Read the start commit of the step from its `step started` record in `problems.md`.
3. Start the `reviewer` agent in a fresh context with the scope step review.
4. Give it the plan folder, the step id, the start commit, the evidence file, the notes of the implementor and the round.
5. Name the design sections that the step touches, not whole documents. Name the dependency rows of the step, the test command and its duration.
6. Name the dependency sources: the path that `python -m tools.project source` prints, unless it prints `none`.
7. In a later round, give it the new diff only and the problem rows of the round before with their answers.
8. For a bug step with a mutation run, name the patch of the report. The reviewer checks that the patch breaks the guarded behavior and that the evidence shows its run with `mutation:`.
9. Add one row per posted problem with `python -m tools.step_close add-problem <step> <round> <severity> <rule> "<topic>" "<location>" "<trigger>" "<class>" "<fix>"`. The tool gives the next id, validates each cell and commits. When it names a broken rule, correct that value and run it again.
10. In a later round, write the result of the reviewer for each problem of the round before with `python -m tools.step_close check-problem <problem> "<check>"`. When the reviewer posts the trigger of a re-raised problem again as a new row, write `carried <id of the new row>` instead of `re-raised`.
11. When round 3 posted an `Important` problem, run the short check after its fix. Start the reviewer with the fixed problems only. It confirms or re-raises each fix and posts nothing new. Write each result with `check-problem`.
12. Leave the answer of a `Pre-existing` problem empty. The plan close reports it as a bug.
13. Report the count of problems to the caller.

## Rules
- Never edit the problems file. The write hook refuses it, and the tools write each row and cell.
- Do not answer a problem in this skill. The implementor answers it.
