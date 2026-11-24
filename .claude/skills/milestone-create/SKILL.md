---
name: milestone-create
description: Writes a milestone file with goal, features, acceptance checks and out of scope list from the design documents and the user request. Opens it when no milestone is open, else keeps it as a draft for later. Use it for a new milestone, for a change of a draft, or for the new milestone of a premature close.
---
# milestone-create

The format and the rules of a milestone file are in `docs/DOCS_CONVENTIONS.md`, section Milestone file.
An agent task holds the goal and its sources, with no implementation step and no test instruction. The rules are in `docs/DOCS_CONVENTIONS.md`, section Agent tasks.

## Procedure
1. Run `python -m tools.progress status`. Stop when the project is not initialized.
2. Choose a short name in lower case with hyphens.
3. Run `python -m tools.milestone_create draft <name>`. It writes the draft file with the next milestone id and creates no branch.
4. A draft can stand beside the open milestone and beside other drafts. A feature of the draft can build on a feature of the open milestone or of an earlier draft. Its text names that feature with the milestone id.
5. Read `docs/design/`, `docs/DEPENDENCIES.md` and the user request.
6. Write the `Goal`, the feature rows and the `Out of scope` list into the draft file.
7. A feature row has the next id, the feature text, the type and one acceptance check. `Plans` stays empty. `State` is `open`.
   A feature that another feature needs stands above it in the table. The text of the dependent feature names it.
8. Ask the user for each acceptance that `docs/design/` does not give. A feature without acceptance does not pass.
9. Tell the user each feature that meets a trigger of the section Research of `plan-create`, as `needs research`.
10. Write a bug row for each open bug that this milestone takes over. Give each row a new id.
11. Start the `reviewer` agent with the effort `medium`, the scope document review and the path of the draft file.
12. Fix each problem in the draft file. When the review posted an `Important` problem, run a further review of the answers and the changed lines only, up to three reviews. Follow the section Document review of `docs/DOCS_CONVENTIONS.md`.
13. Run `python -m tools.milestone_create commit <id>`. Fix each item that it names and run it again.
    When no milestone is open and no earlier draft waits, run `python -m tools.milestone_create open <id>`. It creates the milestone branch and opens the milestone.
    Else stop after the commit and tell the user that the draft waits for the close of the open milestone.
14. Run `idea-remove` for each idea of the ideas file that the milestone plans, with the milestone id as reason.
15. When the design gives the milestone a system that later work must respect, run `dependency-add` for it with the milestone id as source.
16. When a feature adds one more instance of a type, name it to the user. A feature of the type `refactor` comes first when the instance would repeat knowledge of the type outside its own places.
   A feature that another feature needs gives a dependency row only when the rules of the section Dependencies file hold.

## Change of a draft
A draft stays editable until it opens. Use this section when the user changes a feature, the goal or the out of scope list of a draft.
1. Edit the draft file. Keep the feature ids in table order, and correct each feature text that names a changed id.
2. Run the document review of step 11 for the changed lines only, then step 12.
3. Run `python -m tools.milestone_create commit <id>`. Only this command commits a draft.
4. Run `python -m tools.milestone_create remove <id>` when the user drops the draft. Run `idea-add` for each feature that the user wants to keep as an idea.

## Scope change of an open milestone
After the creation commit, change the goal with `python -m tools.progress set-goal "<text>"`. Change the out of scope list with `python -m tools.progress out-of-scope add "<item>"` or `out-of-scope remove "<item>"`. Run them only on a user decision.

## Milestone for bugs only
When the user reports a bug and no milestone is open, write a milestone with an empty feature table and the bug rows. The goal text is in `docs/DOCS_CONVENTIONS.md`, section Bugs. Open it in step 13, also when a draft waits. The bugs come before the drafts.

## Premature close
Ask the user whether the migrated features go into the first draft or into a new draft. For the first draft, follow the section Change of a draft.
The draft starts with the migrated features in id order, then its other features. The migrated bugs come first in the `Bugs` table. Write the new feature id into the `Feature` column of each migrated bug. In step 13, run only the commit command. `milestone-close` opens the draft.
