---
name: dependency-add
description: Adds one structural dependency of the project to the dependencies file after a review and the approval of the user. Use it from milestone-create for a system of the design, and from plan-close for a failure topic that came back.
---
# dependency-add

The format and the rules of the file are in `docs/DOCS_CONVENTIONS.md`, section Dependencies file.
An agent task holds the goal and its sources, with no implementation step and no test instruction. The rules are in `docs/DOCS_CONVENTIONS.md`, section Agent tasks.

## Procedure
1. Work in the main repository. Read `docs/DEPENDENCIES.md`.
2. Write the row as text: the trigger, the action and the validation. Each cell is one sentence.
   The trigger names the kinds of change that meet it, not only the kinds of state that the row guards. Name each kind, for example an added part, a changed part, a part of one side only or a changed restore.
3. Check the row against the rules of the section. Stop and tell the caller the reason when one rule fails:
   - The row names a system of the project, not a detail of the code.
   - A miss breaks something that the tests of a step do not cover.
   - No conventions rule and no single test can express it.
   - The file has room for the row.
4. Write the validation as a check that a tool or the reviewer can run. When it is a test, the test compares the whole state that the dependency protects.
5. Start the `reviewer` agent with the effort `medium` and the scope document review. Give it the text of the row and the section of the conventions. For a topic that came back, also give it the steps of the earlier plans that missed it. The reviewer checks that each of these steps meets the new trigger.
6. Fix each problem in the text.
7. Show the user the row and the reason for it. Ask for the approval.
8. After a yes, run `python -m tools.dependency add "<trigger>" "<action>" "<validation>" "<source>"`. The source is the milestone id or the plan id.

## Rules
- Never write the file by hand. The tool writes the row, the record line and the commit.
- Do not add a row during a step. A step names a candidate in `extensions.md`, and the plan close decides.
