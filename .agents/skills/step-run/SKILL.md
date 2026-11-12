---
name: step-run
description: Implements the next step of the active plan with code, evidence, review, answers and the step gate. Use it for the step that the status prints, also for a fix step.
---
# step-run

The rules are in `docs/DOCS_CONVENTIONS.md`, section Step execution, and in the code and test conventions.

## Procedure
1. Run `python -m tools.progress status`. Take the step that it prints.
2. Run `python -m tools.step_close start <step>`.
3. Read the step row in `plan.md`, the design documents for its feature and the code that it touches.
4. Implement the step. Follow `docs/CODE_CONVENTIONS.md` and `docs/TEST_CONVENTIONS.md`.
5. Run the verification of the step with `python -m tools.test <name> --step <step>`. Add `--command` for a `COMMAND` check.
6. Commit the work with a message of your own.
7. Run `review-step` with notes of max 10 lines on why the change has this form.
8. Answer each problem in `problems.md`. For a fix, commit it and write `fixed <commit>`.
9. When round 1 posted a problem, commit and run `review-step` one more time.
10. When a protected path changed, commit, ask the user, and run `python -m tools.approve <plan> <step> --answer <yes|no>`.
11. Run `python -m tools.step_close close <step>`. Fix each item that the gate names and run it again.

## Fix plan step
1. Write the regression test first when the acceptance of the bug is a test.
2. Run it with `python -m tools.test <name> --step <step>` on the code without the fix. The run must fail.
3. Fix the code. Run the same command one more time. The run must pass.

## Work outside the step
Do not implement a need that the step text does not cover. Add a row with the next id to `extensions.md` of the plan. Leave `Decision` and `Detail` empty.

## Important problem open after round 2
1. Commit. Run `python -m tools.step_close revert <step>`.
2. Implement the step one more time with a different approach. Continue at step 4 of the procedure.
3. When the second attempt fails, run `python -m tools.step_close block <step>`.
4. Show the user the open problems and ask how to continue.
5. Run `python -m tools.step_close unblock <step> "<answer of the user>"`. Continue as the user decided.

## Manual verification
For a `MANUAL` check, ask the user to run the check. Pass the answer with `python -m tools.step_close close <step> --answer <yes|no>`.
