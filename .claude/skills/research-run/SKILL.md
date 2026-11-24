---
name: research-run
description: Answers one open question with a research file through the researcher agent, a document review and a commit. Use it when plan-create or a research step needs a fact that nobody verified, or when the user asks for research.
---
# research-run

The frame of a research file is in `docs/DOCS_CONVENTIONS.md`, section Research file. The main session orchestrates: it runs the tool, starts the agents and reads their reports.
An agent task holds the goal and its sources, with no implementation step and no test instruction. The rules are in `docs/DOCS_CONVENTIONS.md`, section Agent tasks.

## Procedure
1. Write the question as one sentence. Name the feature or the decision that needs the answer.
2. Search `docs/research/` for a file that answers the question. When one exists and its facts still hold, report it and stop.
3. Choose a short name in lower case with hyphens. Run `python -m tools.research start <name>`. It prints the path of the file.
4. Start the `researcher` agent with the question, the path of the file, the design sections and the code paths that the question touches. Name the dependency sources: the path that `python -m tools.project source` prints, unless it prints `none`. Name `docs/MEMORY.md` in the task.
5. Read its report, not its sources.
6. Start the `reviewer` agent with the effort `medium`, the scope document review and the path of the file. Name the question.
7. When the review posted a problem, start the `researcher` agent with the problems. Run a further review only after an `Important` problem. Follow the section Document review of `docs/DOCS_CONVENTIONS.md`: count the rounds, stop a round that does not converge, and run the short check after the last round.
8. Run `python -m tools.research commit <id>` only when the short check confirmed each fix of an `Important` problem.
9. Tell the user the recommendation and the open points. When a fact contradicts a design document, ask the user how the design changes.

## Research step of a plan
1. The question is the text of the step. Run the procedure in the worktree of the plan after `python -m tools.step_close start <step>`.
2. The document review of step 6 is the review of the step. Run `python -m tools.step_close review <step>` before it. Write its problems into the problems file as `review-step` does.
3. After the commit, compare the recommendation with each open step of the same feature.
4. When a step no longer fits, show the user the old and the new step text. Ask in the chat and wait for the answer; a request for a change is not its approval. After the approval, run `python -m tools.step_close set-text <step> "<text>" --answer yes` alone.
5. When the recommendation needs a new step or a different verification, stop and ask the user for a replan.

## Spike
Use a spike for a question about a change of existing code, when only running code can show the answer.
1. Run `python -m tools.research spike <id>`. It prints the spike worktree.
2. Start the `implementor` agent in the spike worktree with the core of the change as its task. It builds the core, runs the whole suite with `python -m tools.test` and reports each failure with its cause. It commits only on the spike branch.
3. Start the `researcher` agent with the report. It writes each failure and its cause into the research file and marks these facts as `run`.
4. Run `python -m tools.research spike-end <id>`. It deletes the spike worktree and its branch.

## Rules
- Research is input only. Never change a design document, a source file or a test file in this skill.
- One research file answers one question. A second question gets its own file.
