---
name: project-init
description: Binds the setup to one project. Asks for the product, the platforms, the stack, the tools, the pipeline, the licenses and the MCP servers, then writes and commits the project bindings. Use it once, before the first milestone.
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
| 4 | Which file type has a start script on each platform? | single choice per platform | The common type, for example `bat` on Windows and `sh` on Linux. |
| 5 | Which programming languages and frameworks? | multiple select | The derived stack. The common stacks for the platforms. |
| 6 | Which formatter, linter, comment check and test runner per language? | single choice per language | The standard tool of the language. One alternative. A comment check is a command that refuses each comment without a tool reason. |
| 7 | Which time limits end a hung test and a hung test run? | single choice | 5 minutes per test and 30 minutes per run. Limits that the user names. |
| 8 | Is the product deployed? | single choice | Not deployed. Deployed, the user writes `DEPLOYMENT.md` now. |
| 9 | Does the project have a CI pipeline? | single choice | None, the project lives on the local machine. A pipeline on the host that the user names. |
| 10 | Which MCP servers? | multiple select | The suggested servers. None. |
| 11 | Where is the source of the installed dependencies? | single choice | The derived folder of the stack. None. |
| 12 | Which groups of its domain does the wiki need? | multiple select | The derived groups, for example content and tuning values. None. |
| 13 | Is the product commercial? | single choice | Commercial. Not commercial. Not decided, which counts as commercial. |
| 14 | Are paid libraries and paid assets allowed? | single choice | Not allowed. Allowed. |
| 15 | What does the project already hold a license for? | free text | Nothing. The items that the user names. |
| 16 | Which licenses are free? | single choice | The common licenses that allow commercial and open source use and ask for no attribution in the product. A list that the user names. |

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
5. `tools/project.toml` in the format of `docs/DOCS_CONVENTIONS.md`, with the command lines of the chosen tools, `comments` per language with a comment check, `test_run_limit`, `[start_script]` and `dependency_source` when the user named a folder. Add `[licenses]` with the answers of questions 13 to 16, and its command `dependencies` when the stack has a manifest. Add `test_binaries` when the test runner builds its own test executables.
6. The per-test timeout in the configuration of the test runner.
7. Use the start version of the example in `docs/DOCS_CONVENTIONS.md` unless the user answered that the product is in deployment.
8. Set `main_branch` to the output of `git branch --show-current`.
9. The pipeline file that runs `python -m tools.check` and `python -m tools.test`, only when the user named a pipeline.
10. The rows of the Non-ASCII allowlist in `docs/CODE_CONVENTIONS.md` that the stack needs, for example localization files.
11. `.agents/mcp.yaml` with the approved servers. Write names of environment variables, never a value.
12. The overview `docs/wiki/README.md` in the form of the wiki rules, with the product, its parts and the page map.
    The page map has one row per page of the default groups and one row per planned page of each group of question 12.
13. `docs/LICENSES.md` with the table of the section Licenses file and no row.
14. One page per row of the page map with its headings, and `docs/wiki/_sidebar.md` with each page under its group.

## Confirmation
1. Show the user a summary of all writes.
2. Ask for one confirmation: confirm, change an answer, or stop.
3. After the confirmation, write the files.
4. Run `python -m tools.project init`. Fix each item that it names and run it again.
5. Tell the user to approve the MCP servers and the hooks when the provider asks.
