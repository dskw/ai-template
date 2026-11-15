---
name: idea-remove
description: Removes ideas from the ideas file. Use it when a milestone plans an idea, or when the user drops an idea.
---
# idea-remove

The ideas file and its rules are in `docs/DOCS_CONVENTIONS.md`, section Ideas file.

## Procedure
1. Collect the ids of the ideas to remove.
2. Set the reason: the id of the milestone that plans them, or the reason of the user.
3. Run `python -m tools.ideas remove <id> [<id> ...] "<reason>"`. It removes the rows and commits the file.
