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
5. Read `docs/design/` and the user request.
6. Write the `Goal`, the feature rows and the `Out of scope` list into the draft file.
7. A feature row has the next id, the feature text, the type and one acceptance check. `Plans` stays empty. `State` is `open`.
8. Ask the user for each acceptance that `docs/design/` does not give. A feature without acceptance does not pass.
9. Write a bug row for each open bug that this milestone takes over. Give each row a new id.
10. Start the `reviewer` agent with the scope document review and the path of the draft file.
11. Fix each problem in the draft file. Run the review one more time when the first review posted a problem.
12. Run `python -m tools.milestone_create commit`. Fix each item that it names and run it again.

## Milestone for bugs only
When the user reports a bug and no milestone is open, write a milestone with an empty feature table and the bug rows. The goal text is in `docs/DOCS_CONVENTIONS.md`, section Bugs.

## Premature close
The draft starts with the migrated features in id order, then the features that the user adds. The migrated bugs come first in the `Bugs` table. Write the new feature id into the `Feature` column of each migrated bug. Do not run step 12. `milestone-close` opens the new milestone.
