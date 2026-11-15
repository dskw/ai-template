---
name: step-run
description: Implements the next step of the active plan with code, evidence, review, answers and the step gate. Use it for the step that the status prints, also for a fix step.
---
# step-run

The rules are in `docs/DOCS_CONVENTIONS.md`, section Step execution, and in the code and test conventions.

## Procedure
1. Run `python -m tools.progress status`. Take the step that it prints.
2. Run `python -m tools.step_close start <step>` before the first write to a source or test file. The pre-commit check rejects code of a step that has not started.
3. Read the step row in `plan.md`, the design documents for its feature and the code that it touches.
4. Implement the step. Follow `docs/CODE_CONVENTIONS.md` and `docs/TEST_CONVENTIONS.md`.
5. Run the verification of the step with `python -m tools.test <name> --step <step>`. Add `--command` for a `COMMAND` check. Run each test that covers the changed code with `python -m tools.test <name>`, under the rules of `docs/TEST_CONVENTIONS.md`, section Test runs. Not the whole suite.
6. Commit the work with a message of your own.
7. Run `review-step` with notes of max 10 lines on why the change has this form.
8. Answer each problem in `problems.md`. For a fix, commit it and write `fixed <commit>`.
9. When the round posted an `Important` problem, commit and run `review-step` for the next round, up to round 3.
10. When a protected path changed, commit, ask the user, and run `python -m tools.approve <plan> <step> --answer <yes|no>`.
11. Run `python -m tools.step_close close <step>`. Fix each item that the gate names and run it again.

## Fix plan step
1. Write the regression test first when the acceptance of the bug is a test.
2. Run it with `python -m tools.test <name> --step <step>` on the code without the fix. The run must fail.
3. Fix the code. Run the same command one more time. The run must pass.

## Work outside the step
Do not implement a need that the step text does not cover. Add a row with the next id to `extensions.md` of the plan. Leave `Decision` and `Detail` empty.

## Important problem open after round 3
1. Show the user the open problems. Ask for a new approach or an acceptance with a reason.
2. For an acceptance, run `python -m tools.step_close unblock <step> "<reason of the user>"` and close the step.
3. For a new approach, commit and run `python -m tools.step_close revert <step>`. The revert keeps the commits outside the step, so commit an unrelated write, as a memory or a setup finding, in its own commit.
4. Implement the step one more time with a different approach. Continue at step 4 of the procedure.
5. When the second attempt fails, run `python -m tools.step_close block <step>`. Show the user the open problems and ask how to continue.
6. Run `python -m tools.step_close unblock <step> "<answer of the user>"`. Continue as the user decided.

## Manual verification
1. Put a package into `docs/plans/<plan>/tmp/manual-check/` and nowhere else. It holds the built application with each file that it needs, one start script per part, and a readme of max 20 lines. A milestone check package goes into the milestone package folder of `docs/DOCS_CONVENTIONS.md`.
2. The readme names what to start, what to check and what the user tells the agent.
3. Start each script once from its full path. Fix the package when a script fails.
4. Ask the user to run the check. Pass the answer with `python -m tools.step_close close <step> --answer <yes|no>`.
5. When the user delegated the check to the agent, run the check yourself and add `--by agent`.
6. When the user answers with tuning requests, pass `--answer no`. Apply the requests in the same step, rebuild the package and ask again. Repeat until the user answers yes.
7. When the user asks for a new way, follow the section Important problem open after round 3.
