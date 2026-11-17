---
name: plan-create
description: Writes a plan folder with steps and verification for open features, for a list of bugs or for a refactor, then creates the worktree of the plan. Use it in the main repository when a feature or a bug has no active plan.
---
# plan-create

The format and the rules of a plan file are in `docs/DOCS_CONVENTIONS.md`, sections Plan file, Bugs and Dependencies file.

## Procedure
1. Run `python -m tools.progress status` in the main repository. Stop when no milestone is open, or when each open feature and each bug has an active plan.
2. Choose the ids of the plan under the rules of the section Ids.
3. Choose a short name in lower case with hyphens.
4. Run `python -m tools.plan_create start <feature|fix|refactor> <name>`. It creates the draft folder.
5. Read the milestone file, `docs/design/`, `docs/DEPENDENCIES.md` and the code that the ids touch.
6. Check each id against the section Research. Run `research-run` first when the cut of the steps depends on the answer.
7. Write the ids into the field `features` or `bugs` of `plan.md`.
8. Read `docs/TEST_CONVENTIONS.md`. Write the step rows. Each step names its id, a text and one verification check. The steps of one feature share the test of that feature.
9. Cut each step as one increment that the user can see. The verification must pass after that step alone.
10. Compare each step with the `Trigger` column of the dependencies file. Write the id of each row that the step meets into its `Dependencies` cell, or `none`.
11. When a step adds one more instance of a type, check it against the row `DEP-01`. When the instance would repeat knowledge of the type in another place, stop and tell the user that a refactor comes first.
12. Write the checks of the plan into the `Verification` section, one check per list line. List the checks of the steps and the validation of each named dependency that is a check. Add each test that covers the code that the plan changes.
13. A fix plan needs no document review: continue at step 15. Run `python -m tools.plan_create reviewed`. Start the `reviewer` agent with the effort `medium`, the scope document review and the path of `plan.md`. Name `docs/TEST_CONVENTIONS.md` and `docs/DEPENDENCIES.md` as further rule sources.
14. Fix each problem in the draft. When the review posted an `Important` problem, run step 13 again for the answers and the changed lines only, up to three reviews.
15. Run `python -m tools.plan_create commit`. Fix each item that it names and run it again. It creates the branch and the worktree of the plan and prints the folder.
16. Tell the user the folder of the worktree. A session that works in that folder runs the steps of the plan.

## Ids
- Feature plan: take the features with the state `open` or `in progress` that no active plan holds, in id order, unless the user names different features. A feature of the type `refactor` that they need can join the plan. Its steps come first.
- Refactor plan: take features of the type `refactor` only.
- Refactor step: each verification is an existing test of the code that the step changes. A step that adds the first instance of the structure of its feature verifies with the new test of the feature acceptance.
- Plans that run at the same time change different parts of the code. Tell the user when a new plan changes the same files as an active plan.
- Fix plan on user request: take the bug ids that the user names. Do not pick bugs yourself.
- Bugfix phase: take all open bugs that no active plan holds. Tell the user the list before you write the plan, so the user can drop bugs first.
- A plan can implement one part of a feature when the feature is too large for one plan.

## Research
An id needs research when one of these triggers holds:
- It depends on a behavior of a library, a platform or a tool that the code does not use yet.
- It has two or more approaches, and the choice changes the cut of the steps.
- Nobody knows whether its acceptance check can pass.

When the cut of the steps depends on the answer, run `research-run` before you write the steps. Write the steps from its recommendation and name the research id in the step text.
When only the detail of the id depends on the answer, write a research step as its first step. The step text is the question. Its verification is `COMMAND research_check passes` and its `Dependencies` cell is `none`.
A research file that answers the question already replaces both.

## Open problems of an earlier plan
Search the archived plans of each id for problems with the answer `user replan`. Write each of them into the step text of the step that solves it.

## New binding
When the plan needs a new binding, for example a named command for a check, run `project-update` before step 4 or after step 15. The project tool commits only its binding files, and the draft stays out of its commit.

## Fix plan steps
Each bug has one step. The verification of the step is the acceptance check of the bug.
