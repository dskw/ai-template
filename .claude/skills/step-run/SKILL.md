---
name: step-run
description: Implements the next step of the plan of this worktree with code, evidence, review, answers and the step gate. Use it in the worktree of a plan for the step that the status prints, also for a fix step.
---
# step-run

The rules are in `docs/DOCS_CONVENTIONS.md`, section Step execution, and in the code and test conventions. The main session orchestrates: it runs the tools of the step state, starts the agents and reads their reports, not the code.

## Procedure
1. Run `python -m tools.progress status` in the worktree of the plan. Take the step that it prints.
2. Run `python -m tools.step_close start <step>` before the first write to a source or test file. The pre-commit check rejects code of a step that has not started.
3. Read the step row in `plan.md`. Name the design sections of its feature and the rows of `docs/DEPENDENCIES.md` that its `Dependencies` cell names.
4. Start the `implementor` agent with the plan folder, the step id, the design sections, the dependency rows and the task. Name `docs/MEMORY.md` in the task. It implements the step, runs the verification and the tests whose files it changes, and commits.
5. Read its report. Answer each open question with the user when the report names one.
6. Run `review-step` with the notes of the report.
7. Start the `implementor` agent with the problem rows for the fixes. It answers each problem in `problems.md` and commits each fix.
8. When the round posted an `Important` problem, run `review-step` for the next round, up to round 3.
9. When a protected path changed, ask the user, and run `python -m tools.approve <plan> <step> --answer <yes|no>`.
10. Run `python -m tools.step_close close <step>`. Fix each item that the gate names and run it again.

## Fix plan step
The implementor writes the regression test first when the acceptance of the bug is a test. It runs the test on the code without the fix and after the fix. The evidence shows the failing run before the passing run.

## Work outside the step
The implementor implements no need that the step text does not cover. It adds a row with the next id to `extensions.md` of the plan, with `Decision` and `Detail` empty.
A worktree holds no write to a shared file of the milestone. A fact for the memory becomes a row of `extensions.md` with the prefix `Memory:`, a setup finding one with the prefix `Setup:`. The plan close saves them in the main repository.

## Important problem open after round 3
1. For a non-breaking problem under `docs/REVIEW.md`, run `python -m tools.step_close unblock <step> "non-breaking, moved to the bug list"` and close the step. The plan close reports the problem as a bug.
2. For a breaking problem, show the user the open problems. Ask for a new approach or an acceptance with a reason.
3. For an acceptance, run `python -m tools.step_close unblock <step> "<reason of the user>"` and close the step.
4. For a new approach, run `python -m tools.step_close revert <step>`. The revert keeps the commits outside the step.
5. Continue at step 4 of the procedure with the task of a new attempt and the open problems.
6. When the second attempt fails, run `python -m tools.step_close block <step>`. Show the user the open problems and ask how to continue.
7. Run `python -m tools.step_close unblock <step> "<answer of the user>"`. Continue as the user decided.

## Manual verification
1. The implementor puts a package into `docs/plans/<plan>/tmp/manual-check/` and nowhere else. It holds the built application with each file that it needs, one start script per part, and a readme of max 20 lines. A milestone check package goes into the milestone package folder of `docs/DOCS_CONVENTIONS.md`.
2. The readme names what to start, what to check and what the user tells the agent.
3. The implementor starts each script once from its full path and fixes the package when a script fails.
4. Ask the user to run the check. Pass the answer with `python -m tools.step_close close <step> --answer <yes|no>`.
5. When the user delegated the check to the agent, run the check yourself and add `--by agent`.
6. When the user answers with tuning requests, pass `--answer no`. Start the implementor with the requests in the same step; it applies them and rebuilds the package. Ask again. Repeat until the user answers yes.
7. When the user asks for a new way, follow the section Important problem open after round 3.
