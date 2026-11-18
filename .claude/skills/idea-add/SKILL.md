---
name: idea-add
description: Records an idea for a feature of a later milestone in the ideas file. Use it when the user or the agent has an idea that fits neither the open milestone nor a planned one.
---
# idea-add

The ideas file and its rules are in `docs/DOCS_CONVENTIONS.md`, section Ideas file.

## Procedure
1. Write the idea as one sentence of max 25 words that names what the user sees.
2. Set the source: `user` when the user has the idea, `agent` when the agent has it.
3. Run `python -m tools.ideas add "<idea>" <user|agent>`. It takes the next id and commits the file.

## Rules
- Never save an idea as a memory.
- An idea that extends an existing idea changes its text with `idea-edit`. It gets no new row.
- An idea that fits the open milestone becomes a feature or an extension, not an idea.
