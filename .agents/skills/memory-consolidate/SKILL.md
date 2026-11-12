---
name: memory-consolidate
description: Reviews memory entries, then confirms, rewrites, merges or deletes them. Use it at each plan close before the plan review, and when the memory lint reports the index over its limit.
---
# memory-consolidate

The limits are in `docs/DOCS_CONVENTIONS.md`, section Local memory.

## Procedure
1. Run `python -m tools.memory_lint --strict`. It lists each stale entry.
2. Review each entry whose `source` is the closing plan and each stale entry.
3. Decide for each entry: confirm, rewrite or delete.
4. Delete an entry that the code or a conventions file now shows.
5. Merge entries that overlap into one entry.
6. Remove narrative from an entry. Keep the fact.
7. For a confirmed or rewritten entry, set `modified` to the date of today.
8. When the index is over its limit, merge or delete entries until it fits.
9. Run `python -m tools.memory_index`.
10. Run `python -m tools.memory_lint --strict`. Fix each item that it names.
