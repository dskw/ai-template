---
name: idea-edit
description: Changes the text of an idea in the ideas file and keeps its id. Use it when the user or the agent extends or corrects an existing idea.
---
# idea-edit

The ideas file and its rules are in `docs/DOCS_CONVENTIONS.md`, section Ideas file.

## Procedure
1. Find the id of the idea in the ideas file.
2. Write the new text in max 100 words. Name what the user sees. Keep the part of the old text that still holds.
3. Run `python -m tools.ideas edit <id> "<idea>"`. It keeps the id, the time and the source and commits the file.

## Rules
- An idea that fits the open milestone becomes a feature or an extension, not a changed idea.
- A second idea on a different subject gets its own row through `idea-add`.
