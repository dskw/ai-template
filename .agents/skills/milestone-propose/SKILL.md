---
name: milestone-propose
description: Proposes the next milestone from the done features, the design documents and the ideas file. Use it when the user asks for suggestions for the next milestone.
---
# milestone-propose

The rules of a milestone are in `docs/DOCS_CONVENTIONS.md`, section Milestone file. The ideas file is in the section Ideas file.

## Procedure
1. Run `python -m tools.progress status`. Stop when a milestone is open and the user did not ask for a later one.
2. Read the archived milestones and the open milestone: the done features, the dropped features with their reasons and the out of scope lists.
3. Read the design documents and the ideas file.
4. List the mechanics that the code has now, from the done features, not from the design alone.
5. Write two or three proposals. Each proposal has a goal of one or two sentences, three to six features and the ideas that it takes in by id. Each feature builds on a done feature or mechanic and names it.
6. Keep each proposal small: one connected result that the user can see and play.
7. Name the design gaps that a proposal needs to close before planning.
8. Show the proposals to the user and ask which one to plan.
9. When the user chooses a proposal, run `milestone-create` with it. Pass the idea ids of the proposal.

## Rules
- Never write a milestone file in this skill.
