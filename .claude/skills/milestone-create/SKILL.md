---
name: milestone-create
description: Writes a milestone file with goal, features, acceptance checks and out of scope list from the design documents and the user request. Use it when no milestone is open, or for the new milestone of a premature close.
---
# milestone-create

The format and the rules of a milestone file are in `docs/DOCS_CONVENTIONS.md`, section Milestone file.

## Procedure
1. Run `python -m tools.progress status`. Stop when the project is not initialized.
2. Choose a short name in lower case with hyphens.
3. Run `python -m tools.milestone_create start <name>`. It creates the milestone branch and the draft file.
4. For the new milestone of a premature close, run `python -m tools.milestone_create start <name> --migrate`.
5. Read `docs/design/`, `docs/DEPENDENCIES.md` and the user request.
6. Write the `Goal`, the feature rows and the `Out of scope` list into the draft file.
7. A feature row has the next id, the feature text, the type and one acceptance check. `Plans` stays empty. `State` is `open`.
   A feature that another feature needs stands above it in the table. The text of the dependent feature names it.
8. Ask the user for each acceptance that `docs/design/` does not give. A feature without acceptance does not pass.
9. Tell the user each feature that meets a trigger of the section Research of `plan-create`, as `needs research`.
10. Write a bug row for each open bug that this milestone takes over. Give each row a new id.
11. Start the `reviewer` agent with the effort `medium`, the scope document review and the path of the draft file.
12. Fix each problem in the draft file. When the review posted an `Important` problem, run a second review of the answers and the changed lines only, up to three reviews.
13. Run `python -m tools.milestone_create commit`. Fix each item that it names and run it again.
14. Run `idea-remove` for each idea of the ideas file that the milestone plans, with the milestone id as reason.
15. When the design gives the milestone a system that later work must respect, run `dependency-add` for it with the milestone id as source.
16. When a feature adds one more instance of a type, name it to the user. A feature of the type `refactor` comes first when the instance would repeat knowledge of the type outside its own places.
   A feature that another feature needs gives a dependency row only when the rules of the section Dependencies file hold.

## Scope change of an open milestone
After the creation commit, change the goal with `python -m tools.progress set-goal "<text>"`. Change the out of scope list with `python -m tools.progress out-of-scope add "<item>"` or `out-of-scope remove "<item>"`. Run them only on a user decision.

## Milestone for bugs only
When the user reports a bug and no milestone is open, write a milestone with an empty feature table and the bug rows. The goal text is in `docs/DOCS_CONVENTIONS.md`, section Bugs.

## Premature close
The draft starts with the migrated features in id order, then the features that the user adds. The migrated bugs come first in the `Bugs` table. Write the new feature id into the `Feature` column of each migrated bug. Do not run step 13. `milestone-close` opens the new milestone.
