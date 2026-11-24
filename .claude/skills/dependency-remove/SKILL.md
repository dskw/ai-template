---
name: dependency-remove
description: Removes one structural dependency from the dependencies file after a refactor, when the reviewer agrees that it has no value any more. Use it from plan-close in the close of a refactor plan only.
---
# dependency-remove

The format and the rules of the file are in `docs/DOCS_CONVENTIONS.md`, section Dependencies file.
An agent task holds the goal and its sources, with no implementation step and no test instruction. The rules are in `docs/DOCS_CONVENTIONS.md`, section Agent tasks.

## Procedure
1. Work in the main repository, after the merge of the refactor plan. Stop when the plan in close is no refactor plan.
2. Find the `Plan merged:` commit of the plan with `git log`.
3. Start the `reviewer` agent with the scope document review. Give it the row of the dependency and the diff of the merge commit.
4. The reviewer agrees when the trigger cannot occur any more, or when the action happens without work of a step. It names the code that shows this.
5. After an agreement, run `python -m tools.dependency remove <id> "<reason>"`. The reason has max 12 words.
6. After a refusal, keep the row. Add the reason of the reviewer as a `Nit` problem of the plan with `python -m tools.step_close add-problem`. Then write the answer `closed intentional <reason>` with `python -m tools.step_close answer-problem`.

## Rules
- A changed dependency is a removal and an add: run `dependency-add` for the new row.
- The row for a further instance of something that exists belongs to the setup. Never remove it.
