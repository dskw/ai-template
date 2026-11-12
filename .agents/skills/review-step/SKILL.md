---
name: review-step
description: Runs the reviewer agent on the step in progress and writes the posted problems to the problems file of the plan. Use it from step-run after the step has evidence and a commit.
---
# review-step

The problem format is in `docs/REVIEW.md`. The file format is in `docs/DOCS_CONVENTIONS.md`, section Problems file.

## Procedure
1. Run `python -m tools.step_close review <step>`. It prints the review round.
2. Read the start commit of the step from its `step started` record in `problems.md`.
3. Start the `reviewer` agent in a fresh context with the scope step review.
4. Give it the plan folder, the step id, the start commit, the evidence file, the notes of the implementor and the round.
5. Name the design sections that the step touches, not whole documents. Name the test command and its duration.
6. Name the folder `dependency_source` of `tools/project.toml` when the binding exists.
7. In round 2, give it the new diff only and the problem rows of round 1 with their answers.
8. Write one row per posted problem into the `Problems` table. Use the next free problem id.
9. Fill `Step`, `Round`, `Severity`, `Rule`, `Location`, `Trigger`, `Class` and `Fix`. Leave `Answer` and `Check` empty.
10. In round 2, write the result of the reviewer into the `Check` cell of each round 1 problem.
11. For each `Pre-existing` problem, run `bug-report` with the plan id and the problem id as source. Write `bug <id>` as its answer.
12. Report the count of problems to the caller.

## Rules
- Do not change a problem that the reviewer posted. Do not drop one.
- Do not answer a problem in this skill. The implementor answers it.
