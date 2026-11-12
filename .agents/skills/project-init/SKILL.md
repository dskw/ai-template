---
name: project-init
description: Binds the setup to one project. Asks for the product, the platforms, the stack, the tools, the pipeline and the MCP servers, then writes and commits the project bindings. Use it once, before the first milestone.
---
# project-init

The procedure and the formats are in `docs/DOCS_CONVENTIONS.md`, section Project init and update.

## Start
1. Run `python -m tools.setup`. It is safe to run again.
2. Run `python -m tools.project check`. When it passes, stop and tell the user to use `project-update`.
3. Read each document in `docs/design/`.
4. When `docs/design/` holds no document, ask question 1. When the user adds documents first, stop.

## Question rules
- Use the question tool of the harness when the session has one. If not, ask in text with numbered options.
- A question has two to four options. The user can always type a different answer.
- Show a value that you derived from `docs/design/` as the first option, marked as derived. Do not ask for it again.
- A question that allows more than one answer is a multiple select question.
- Ask one question at a time and max three in one turn.
- Never decide an answer. Stop when a question has no answer.

## Questions
| # | Question | Form | Options |
|---|---|---|---|
| 1 | Where does the project information come from? | single choice | I describe it now. I add documents to `docs/design/` first. |
| 2 | What is the product? | free text, one to three sentences | The derived text to confirm, or a new text. |
| 3 | Which target platforms? | multiple select | The derived platforms. The common platforms for the product type. |
| 4 | Which programming languages and frameworks? | multiple select | The derived stack. The common stacks for the platforms. |
| 5 | Which formatter, linter and test runner per language? | single choice per language | The standard tool of the language. One alternative. |
| 6 | Is the product deployed? | single choice | Not deployed. Deployed, the user writes `DEPLOYMENT.md` now. |
| 7 | Does the project have a CI pipeline? | single choice | None, the project lives on the local machine. A pipeline on the host that the user names. |
| 8 | Which MCP servers? | multiple select | The suggested servers. None. |
| 9 | Where is the source of the installed dependencies? | single choice | The derived folder of the stack. None. |

Ask question 1 only when `docs/design/` holds no document.

## MCP servers
1. Derive candidates from the platforms, the languages, the frameworks and the external systems in the answers and in `docs/design/`.
2. Examples are a database, a browser for UI checks, a device bridge, a documentation lookup and an issue tracker.
3. For each candidate, state in one line what it gives the agent and which step type uses it.
4. Suggest no server without a use in this project. `none` is a valid answer.
5. The user approves entries, removes entries and adds servers.

## Writes
Prepare these writes. Do not write a file before the confirmation.
1. `docs/design/PROJECT.md` with the answers as given, when the user described the project in the session.
2. The `Project` section of `AGENTS.md`: one to three sentences on the product and a link to `docs/design/`.
3. The `Languages` table of `docs/CODE_CONVENTIONS.md`: one row per language, with the naming rules.
4. The `Test runner` table of `docs/TEST_CONVENTIONS.md`.
5. `tools/project.toml` in the format of `docs/DOCS_CONVENTIONS.md`, with the command lines of the chosen tools and `dependency_source` when the user named a folder.
6. Use the start version of the example in `docs/DOCS_CONVENTIONS.md` unless the user answered that the product is in deployment.
7. Set `main_branch` to the output of `git branch --show-current`.
8. The pipeline file that runs `python -m tools.check` and `python -m tools.test`, only when the user named a pipeline.
9. The rows of the Non-ASCII allowlist in `docs/CODE_CONVENTIONS.md` that the stack needs, for example localization files.
10. `.agents/mcp.yaml` with the approved servers. Write names of environment variables, never a value.

## Confirmation
1. Show the user a summary of all writes.
2. Ask for one confirmation: confirm, change an answer, or stop.
3. After the confirmation, write the files.
4. Run `python -m tools.project init`. Fix each item that it names and run it again.
5. Tell the user to approve the MCP servers and the hooks when the provider asks.
