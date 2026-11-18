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
5. Name the design sections that the step touches, not whole documents. Name the dependency rows of the step, the test command and its duration.
6. Name the dependency sources: the path that `python -m tools.project source` prints, unless it prints `none`.
7. In a later round, give it the new diff only and the problem rows of the round before with their answers.
8. Write one row per posted problem into the `Problems` table. Use the next free problem id.
9. Fill `Step`, `Round`, `Severity`, `Rule`, `Topic`, `Location`, `Trigger`, `Class` and `Fix`. Leave `Answer` and `Check` empty. Run `python -m tools.check` with the path of the problems file and fix each sentence that it names.
10. In a later round, write the result of the reviewer into the `Check` cell of each problem of the round before.
11. Leave the answer of a `Pre-existing` problem empty. The plan close reports it as a bug.
12. Report the count of problems to the caller.

## Rules
- Do not change a problem that the reviewer posted. Do not drop one.
- Do not answer a problem in this skill. The implementor answers it.
