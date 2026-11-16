---
name: memory-save
description: Creates or updates one memory entry and rebuilds the memory index. Use it when the user corrects the agent, confirms an approach that is not obvious, makes a decision that the code does not show, or when the agent finds an environment fact.
---
# memory-save

The entry format and the limits are in `docs/DOCS_CONVENTIONS.md`, section Local memory. The rules on what to save are in `AGENTS.md`.

## Procedure
1. In the worktree of a plan, do not write the entry. Add the fact as a row with the prefix `Memory:` to `extensions.md` of the plan and stop. The plan close saves it.
2. Set the type of the fact: `user`, `feedback`, `project` or `reference`.
3. Reject the fact when the code shows it or when a conventions file states it.
4. Reject progress, status, architecture, file paths and bug fixes.
5. Search `docs/MEMORY.md` for an entry on the same subject. Update that entry. Do not add a duplicate.
6. Write the entry file in `docs/memories/` with the name pattern `MEM-[NAME].md`.
7. Set `source` to the id of the plan that gave the fact, or to `user`.
8. Set `modified` to the date of today.
9. Write the title as the index summary. Write one fact in the body.
10. Run `python -m tools.memory_index`.
11. Run `python -m tools.memory_lint`. Fix each item that it names.

## Confirm an entry
To confirm an entry without a change of its text, set `modified` to the date of today and run steps 10 and 11.
