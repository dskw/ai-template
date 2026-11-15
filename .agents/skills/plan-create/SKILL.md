---
name: plan-create
description: Writes a plan folder with steps and verification for one or more open features, or a fix plan for a list of bugs. Use it when a milestone is open and no plan is active.
---
# plan-create

The format and the rules of a plan file are in `docs/DOCS_CONVENTIONS.md`, sections Plan file and Bugs.

## Procedure
1. Run `python -m tools.progress status`. Stop when a plan is active or when no milestone is open.
2. Choose the ids of the plan under the rules of the section Ids.
3. Choose a short name in lower case with hyphens.
4. Run `python -m tools.plan_create start <feature|fix> <name>`. It creates the draft folder.
5. Read the milestone file, `docs/design/` and the code that the ids touch.
6. Write the ids into the field `features` or `bugs` of `plan.md`.
7. Read `docs/TEST_CONVENTIONS.md`. Write the step rows. Each step names its id, a text and one verification check. The steps of one feature share the test of that feature.
8. Cut each step as one increment that the user can see. The verification must pass after that step alone.
9. Write the checks of the plan into the `Verification` section, one check per list line.
10. A fix plan needs no document review: continue at step 12. Run `python -m tools.plan_create reviewed`. Start the `reviewer` agent with the effort `medium`, the scope document review and the path of `plan.md`. Name `docs/TEST_CONVENTIONS.md` as the second rule source for the verification column.
11. Fix each problem in the draft. When the review posted an `Important` problem, run step 10 again for the answers and the changed lines only, up to three reviews.
12. Run `python -m tools.plan_create commit`. Fix each item that it names and run it again.

## Ids
- Feature plan: take the features with the state `open` or `in progress` in id order, unless the user names different features.
- Fix plan on user request: take the bug ids that the user names. Do not pick bugs yourself.
- Bugfix phase: take all open bugs. Tell the user the list before you write the plan, so the user can drop bugs first.
- A plan can implement one part of a feature when the feature is too large for one plan.

## Open problems of an earlier plan
Search the archived plans of each id for problems with the answer `user replan`. Write each of them into the step text of the step that solves it.

## Fix plan steps
Each bug has one step. The verification of the step is the acceptance check of the bug.
