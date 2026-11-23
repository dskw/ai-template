---
name: step-run
description: Implements the next step of the plan of this worktree with code, evidence, review, answers and the step gate. Use it in the worktree of a plan for the step that the status prints, also for a fix step.
---
# step-run

The rules are in `docs/DOCS_CONVENTIONS.md`, section Step execution, and in the code and test conventions. The main session orchestrates: it runs the tools of the step state, starts the agents and reads their reports, not the code.
Change the directory to the worktree of the plan right before each agent start, unless an agent of another plan runs. Name the worktree in the task of the agent. Name the dependency sources too: the path that `python -m tools.project source` prints, unless it prints `none`.
Before each command with `--answer`, ask the user in the chat and wait for the answer. A request for a change is not its approval. Run that command alone, with no second command.

## Procedure
1. Run `python -m tools.progress status` in the worktree of the plan. Take the step that it prints.
2. Run `python -m tools.step_close start <step>` before the first write to a source or test file. The pre-commit check rejects code of a step that has not started.
3. Read the step row in `plan.md`. Name the design sections of its feature and the rows of `docs/DEPENDENCIES.md` that its `Dependencies` cell names.
4. Start the `implementor` agent with the plan folder, the step id, the design sections, the dependency rows and the task. Name `docs/MEMORY.md` in the task. It implements the step, runs the verification and the tests whose files it changes, and commits.
5. Read its report. Answer each open question with the user when the report names one.
6. Run `review-step` with the notes of the report.
7. Start the `implementor` agent with the problem rows for the fixes. It commits each fix and answers each problem with `python -m tools.step_close answer-problem`.
8. When the round posted an `Important` problem, run `review-step` for the next round, up to round 3.
9. When a protected path changed, ask the user, and run `python -m tools.approve <plan> <step> --answer <yes|no>`.
10. Run `python -m tools.step_close close <step>`. Fix each item that the gate names and run it again.

## Several plans in one session
1. Start max one agent that writes per worktree at a time. Its first write binds it to that worktree, and the write hook refuses its writes into another worktree.
2. Never change the directory of the session while an agent runs. Start the agent of another plan from the current directory, and name its worktree in the task.
3. Run each state tool of a plan in a sub shell with the worktree as its directory, for example `(cd <worktree> && python -m tools.step_close close <step>)`.
4. The hooks judge a write of an agent against the root of its path. When the hook input names no agent, the directory of the session stays the root. Parallel plans then need one session per worktree.

## Research step
A step with the verification `COMMAND research_check passes` is a research step. Run `python -m tools.step_close start <step>`, then the skill `research-run` with its section Research step of a plan. No implementor agent runs, and the step changes no source file and no test file. Then continue at step 9 of the procedure.

## Fix plan step
The implementor writes the regression test first when the acceptance of the bug is a test. It runs the test with the options `--step` and `--fails` on the code without the fix, and with `--step` after the fix. The evidence shows the failing run before the passing run, and the step gate refuses the close without it.
A bug can sit in the test, so the old test passes on correct code. Then tell the implementor to use a mutation run as the failing run. The mutation breaks the behavior that the test guards. The implementor writes the mutation as a patch into the folder `tmp/` of the plan and runs `python -m tools.test <name> --step <step> --mutation <patch>`. The tool applies the patch, runs the test and takes the patch back. The implementor names the patch in its report. Each further bug of a shared cause gets its failing run the same way.

## Failed test
Never run a failed test again by hand to make a gate pass. The test tool runs it three more times alone. `fails in n of 4 runs` names a cause in the timeline or the order of the test: fix that cause.

## Agent that waits
An agent can report that it waits for its own build or test run. Then read the logs of that run in the folder `tmp/logs/` of the plan folder and the evidence file of the step. When the run finished, send the agent a message with the result and tell it to go on. When no run is active, tell it to run the command again in the foreground.

## Test that the plan did not name
When a report names a test that the verification of the plan does not hold, ask the user. After the approval, run `python -m tools.step_close add-check "TEST <name> passes" --answer yes`.

## Work outside the step
The implementor implements no need that the step text does not cover. It adds a row with the next id to `extensions.md` of the plan, with `Decision` and `Detail` empty.
A worktree holds no write to a shared file of the milestone. A fact for the memory becomes a row of `extensions.md` with the prefix `Memory:`, a setup finding one with the prefix `Setup:`. The plan close saves them in the main repository.
A report or a review can name a row of `docs/DEPENDENCIES.md` whose trigger the step meets and that its `Dependencies` cell does not name. Run `python -m tools.step_close set-dependencies <step> "<ids>"` with each id that the step meets. It adds the validation of each row that is a check to the verification of the plan.

## Important problem open after round 3
1. Show the user each open problem, also a non-breaking one, with its trigger and its fix. Ask for a new approach or an acceptance with a reason.
2. For an acceptance, run `python -m tools.step_close unblock <step> --answer "<reason of the user>"` and close the step. The plan close reports each accepted problem as a bug.
3. For a new approach, run `python -m tools.step_close revert <step>`. The revert keeps the commits outside the step.
4. When the user approved a new step text, run `python -m tools.step_close set-text <step> "<text>" --answer yes`. It takes each step that is not complete.
5. When the new approach needs a refactor first, add the refactor feature in the main repository with `python -m tools.progress add-feature`, then run `python -m tools.plan_close sync` in the worktree. After the approval of the user, run `python -m tools.step_close insert-refactor <feature> "<text>" "<verification>" --answer yes`. The refactor step stands before the open steps and runs first.
6. Continue at step 4 of the procedure with the task of a new attempt and the open problems.
7. When the second attempt fails, run `python -m tools.step_close block <step>`. Show the user the open problems and ask how to continue.
8. Run `python -m tools.step_close unblock <step> --answer "<answer of the user>"`. Continue as the user decided.

## Manual verification
1. The implementor puts a package into `docs/plans/<plan>/tmp/manual-check/` and nowhere else. It holds the built application with each file that it needs, one start script per part and a readme of max 20 lines. A start script has the file type of `[start_script]` in `tools/project.toml` for the platform. A milestone check package goes into the milestone package folder of `docs/DOCS_CONVENTIONS.md`.
2. The readme names what to start, what to check and what the user tells the agent.
3. The implementor starts each script once from its full path and fixes the package when a script fails.
4. Run `python -m tools.step_close close <step>` first. It accepts an earlier pass of the same check while no product file changed since. When it asks, ask the user to run the check, and pass the answer with `python -m tools.step_close close <step> --answer <yes|no>`. Never pass an earlier answer of the user on to a later gate. The tool decides whether an earlier pass still holds.
5. When the user delegated the check to the agent, run the check yourself and add `--by agent`.
6. When the user answers with tuning requests, pass `--answer no`. Start the implementor with the requests in the same step; it applies them and rebuilds the package. Ask again. Repeat until the user answers yes.
7. When the user asks for a new way, follow the section Important problem open after round 3.
