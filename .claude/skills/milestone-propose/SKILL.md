---
name: milestone-propose
description: Proposes the next milestone from the done features, the design documents and the ideas file. Use it when the user asks for suggestions for the next milestone.
---
# milestone-propose

The rules of a milestone are in `docs/DOCS_CONVENTIONS.md`, section Milestone file. The ideas file is in the section Ideas file. The rules of a type and its instances are in the section Dependencies file.

## Procedure
1. Run `python -m tools.progress status`. When a milestone is open, propose a later milestone only on user request. It becomes a draft.
2. Read the archived milestones, the open milestone and each draft milestone. Note the done features, the dropped features with the reasons of their `feature dropped` records, the out of scope lists and the features of each draft.
3. Read the design documents and the ideas file.
4. List the mechanics that the code has now, from the done features, not from the design alone.
5. Write two or three proposals. Each proposal has a goal of one or two sentences, three to six features and the ideas that it takes in by id. Each feature builds on a done feature or mechanic, or on a feature of the open milestone or of a draft, and names it. No proposal repeats a feature of a draft.
6. For each feature of a proposal, name the structure that it needs, such as a module, an interface or a data path. Check it against the code.
   A missing structure is due when a feature adds the third instance of a type. Count the instances in the code and in the proposal.
   It is due too when a feature adds an instance that repeats knowledge of the type outside its own places.
   Without either case, the feature uses the code as it is. When no feature needs a structure, propose none.
7. A due structure becomes one feature of the type `refactor`, also when it adds the first instance of the structure.
   It has its own plan when 2 or more features of the proposal need it, or when it needs its own check as acceptance. Else the plan of the one feature that needs it holds it, with its steps first.
   This enabling feature stands before the first feature that needs it and counts in the features of the proposal. Its acceptance is a check that keeps the structure.
8. Keep each proposal small: one connected result that the user can see and play. A proposal never holds only enabling features.
9. Name the design gaps that a proposal needs to close before planning. Mark a gap as `needs research` when it meets a trigger of the section Research of `plan-create`.
10. Show the proposals to the user and ask which one to plan.
11. When the user chooses a proposal, run `milestone-create` with it. Pass the idea ids of the proposal.
12. When the user also keeps a second proposal as the follow-up, run `milestone-create` for it after the first one. It stays a draft.

## Rules
- Never write a milestone file in this skill.
