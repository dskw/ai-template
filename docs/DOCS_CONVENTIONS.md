# Docs conventions

Each rule has an id. A review problem names the id.

## Writing rules
The writing rules follow ASD-STE100, Simplified Technical English.

| ID | Rule |
|---|---|
| D001 | A sentence has max 25 words. |
| D002 | Do not use a word or phrase of the blocklist in `tools/vale/styles/Project/Blocklist.yml`. |
| D003 | Write in active voice. |
| D004 | Write one instruction per sentence. |
| D005 | Use one word for one meaning. Do not use synonyms, idioms or figures of speech. |
| D006 | Use the technical names of the project: class names, tool names and protocol names. |
| D007 | A code identifier follows the naming rules of its language, not these rules. |
| D008 | A document shows a procedure with a Mermaid diagram. A diagram shows one procedure with its decision points. |
| D009 | A conventions file states rules only. Each rule has an id. |
| D010 | Research in `docs/research/` is input only. Text copied from it must pass the lint. The section Research file holds its frame. |

`python -m tools.docs_lint` runs Vale with the style in `tools/vale/styles/Project/`. Passive voice is a warning. The other checks fail. The lint does not check the text inside a code block. It fails when a Mermaid block does not parse.

## Lint exclusions
The docs lint covers `docs/**`, `AGENTS.md`, `.agents/**` and `CHANGELOG.md`. It excludes these paths.

| Path |
|---|
| docs/design/** |
| docs/research/** |
| docs/plans/**/evidence/** |
| docs/plans/**/tmp/** |
| docs/milestones/tmp/** |
| docs/wiki/assets/** |
| docs/wiki/index.html |

## Project structure
```
/AGENTS.md                                     (agent instructions for every provider)
/CLAUDE.md, /.claude/, /.codex/, /.kilo/       (generated provider files)
/.mcp.json, /kilo.jsonc                        (generated provider files)
/.agents/skills/[NAME]/SKILL.md                (skills, the source for every provider)
/.agents/agents/[NAME].md                      (agent definitions)
/.agents/hooks.yaml                            (hook definitions)
/.agents/mcp.yaml                              (approved MCP servers)
/.agents/.generated/manifest.json              (list and source hash of the generated files)
/tools/                                        (Python package with every tool)
/tools/project.toml                            (project bindings, written by project-init)
/.worktrees/[PLAN ID]/                         (worktree of an active plan, not committed)
/docs/CODE_CONVENTIONS.md                      (how to write code)
/docs/TEST_CONVENTIONS.md                      (how to test)
/docs/DOCS_CONVENTIONS.md                      (how to plan, record and write, and the AI setup)
/docs/REVIEW.md                                (reviewer instructions)
/docs/ai-setup-adjustments.md                  (findings about the AI setup and the instructions to apply them)
/docs/DEPENDENCIES.md                          (structural dependencies of the project, written by tools.dependency)
/docs/MEMORY.md                                (memory index, generated)
/docs/LICENSES.md                              (outside items with a license outside the free list)
/docs/IDEAS.md                                 (ideas for later milestones)
/docs/memories/MEM-[NAME].md                   (one memory per file)
/docs/design/                                  (design documents of the user)
/docs/design/PROJECT.md                        (product, platforms and stack)
/docs/research/R[NNN]-[NAME].md                (one research file per question, input only)
/docs/research/tmp/                            (experiments of a research outside a plan, ignored by git)
/docs/milestones/PROGRESS.md                   (one row per milestone, generated)
/docs/milestones/M[NNN]-[NAME].md              (one milestone)
/docs/milestones/archive/                      (closed milestones)
/docs/plans/M[NNN]-P[NNN]-[NAME]/plan.md       (one plan)
/docs/plans/M[NNN]-P[NNN]-[NAME]/progress.md   (one row per step)
/docs/plans/M[NNN]-P[NNN]-[NAME]/extensions.md (work found during the plan that is not in the plan)
/docs/plans/M[NNN]-P[NNN]-[NAME]/problems.md   (review problems, answers and records)
/docs/plans/M[NNN]-P[NNN]-[NAME]/evidence/     (raw output per step, written by tools.test)
/docs/plans/M[NNN]-P[NNN]-[NAME]/tmp/          (temporary files of the plan, the manual check package, deleted at plan close)
/docs/plans/M[NNN]-P[NNN]-[NAME]/tmp/logs/     (logs of the test tool in the worktree of the plan)
/docs/plans/M[NNN]-P[NNN]-[NAME]/tmp/research/ (experiments of a research of the plan)
/docs/milestones/tmp/                          (the manual check package of the milestone close, deleted at that close)
/docs/milestones/tmp/logs/                     (logs of the test tool outside a plan and of the timing tool, deleted at the milestone close)
/docs/plans/archive/                           (closed plans)
/docs/wiki/                                    (developer wiki, project content only)
/docs/wiki/README.md                           (overview of the product with the page map)
/docs/wiki/_sidebar.md                         (navigation: each page once under its group)
/docs/wiki/[GROUP]/[PAGE].md                   (one page; the groups are start, architecture, systems, working and those of the project)
/docs/wiki/assets/                             (generated bundle with the dark theme; no page lives here)
/CHANGELOG.md                                  (versions, written by tools.milestone_close)
/DEPLOYMENT.md                                 (deployed version and compatible paths, written by the user)
```

## File formats
| ID | Rule |
|---|---|
| D100 | A file uses three shapes only: frontmatter for fields, a table for items, a record line for an event. |
| D101 | A record line is a list item of the form `<type> <ids> <date>`. Only a tool writes a record line, also each line of a `Records` section. |
| D102 | A field has one meaning and one writer. |
| D103 | The tool that reads a file validates it and names the wrong line. |

## Lifecycle
```mermaid
flowchart TD
    init[project-init] --> milestone[milestone-create]
    milestone --> plan[plan-create]
    plan --> step[step-run for the next step]
    step --> more{Open step?}
    more -->|yes| step
    more -->|no| close[plan-close]
    close --> open{Open feature or bug?}
    open -->|yes| plan
    open -->|no| finish[milestone-close]
    finish --> milestone
```

| ID | Rule |
|---|---|
| D200 | A milestone is a set of features that give the user one usable result. |
| D201 | A feature is one behavior that the user can see or measure. |
| D202 | A bug is one behavior that differs from the design or from a feature acceptance. |
| D203 | A plan implements features, or one part of a feature, or a list of bugs, or a refactor. |
| D204 | One milestone is open at a time. More than one plan can be active. A feature or a bug belongs to max one active plan. |
| D205 | Any number of milestones can have the status `draft`. A draft holds a later milestone. It has no branch and no plan, and it takes no bug report. |
| D206 | A draft gets the next free milestone id. The drafts open in the order of their ids. Only the user changes this order. |
| D207 | Each active plan has the branch `plan/<plan id>` and the worktree `.worktrees/<plan id>/`. `python -m tools.plan_create commit` creates both. |
| D208 | The main repository holds the milestone branch. The milestone skills, the plan creation and the plan close run there, one at a time. |
| D209 | Each step, its reviews and the plan review run in the worktree of the plan. One agent writes in one worktree. One session can run the agents of several plans. |
| D210 | Only a session in the main repository writes the shared files. They are the milestone files, `PROGRESS.md`, the ideas file, the memory, the adjustments document and the dependencies file. |
| D211 | A need of a step for a shared file waits for the plan close. It goes to `extensions.md`: a new need as it is, a fact for the memory with the prefix `Memory:`, a setup finding with the prefix `Setup:`. |
| D212 | Each stage has a skill. The skill calls the tools. A tool makes each state change. Do not call a tool to skip the procedure of its skill. |
| D213 | Start only the step that `python -m tools.progress status` prints in the worktree of the plan. |

## Milestone file
```
---
id: M003
name: route-planning
status: open
created: 2026-11-08
closed:
---
# M003 Route planning

## Goal
The user can draw a route on the map, save it and load it again.

## Features
| ID | Feature | Type | Acceptance | Plans | State |
|---|---|---|---|---|---|
| F01 | Draw a route by clicking waypoints | new | TEST route_draw passes | M003-P001 | done |
| F02 | Save a route to a file | new | TEST route_save passes | M003-P002 | in progress |
| F03 | Check the route file by hand | update | MANUAL route_file_check | | open |

## Bugs
| ID | Bug | Feature | Source | Acceptance | Cause |
|---|---|---|---|---|---|
| B01 | Save fails for routes with one waypoint | F02 | user | TEST bug_route_save_single passes | user The length check divides by the count of segments |
| B02 | Deleted waypoint still drawn until reload | M002-F04 | M003-P002 N07 | TEST bug_route_delete_redraw passes | |

## Out of scope
- Route optimization

## Records
- feature dropped F04 old: open new: dropped The user wants no export 2026-11-12
```

| ID | Rule |
|---|---|
| D300 | `status` is `draft`, `open` or `closed`. |
| D301 | `python -m tools.milestone_create draft <name>` writes a draft, `commit <id>` validates and commits it, `open <id>` opens it when no milestone is open, and `remove <id>` deletes it. |
| D302 | `Goal` has one to three sentences. It names the user result, not the implementation. |
| D303 | A feature text has max 12 words. `Type` is `new`, `update` or `refactor`. A refactor changes the structure of the code and no behavior. It can add a structure for a later instance and change each caller of a moved structure. |
| D304 | A feature that another feature needs stands above it in the table. The text of the dependent feature names its id. |
| D305 | An acceptance is one check: `TEST <name> passes`, `COMMAND <name> passes` or `MANUAL <name>`. |
| D306 | The user runs a `MANUAL` check, or delegates it to the agent for one step or one plan. A tool records the answer and its source. |
| D307 | The record of a manual check names the check and the commit that the user checked. A later gate with the same check accepts a pass while no product file changed since that commit. |
| D308 | A product file is each file outside `docs/` and the setup, except a Markdown file. After a change of one, the gate asks again and names the changed files. |
| D309 | Never pass an earlier answer of the user on to a later gate. The tool decides whether an earlier pass still holds. |
| D310 | A manual check package of a step or a plan goes into `docs/plans/<plan>/tmp/manual-check/`, one of the milestone close into `docs/milestones/tmp/manual-check/`. A close fails while a package is in use. |
| D311 | `python -m tools.progress` writes `Plans` and `State`. `State` is `open`, `in progress`, `done`, `dropped` or `migrated`. Each state other than `open` stands in bold. |
| D312 | A feature is `done` when an archived plan lists it in `done` and no active plan references it. |
| D313 | After the document review, only the user adds, changes or deletes a feature. The user changes the `Goal` and the `Out of scope` list of the open milestone through `python -m tools.progress set-goal` and `out-of-scope`. |
| D314 | A need found during a plan goes to `extensions.md`. It becomes a feature only with user approval. |
| D315 | Only the user drops a feature. Ask with the reason. The dropped row keeps its acceptance. Its record `feature dropped` holds the old state and the reason. |
| D316 | The section `Records` of a milestone file is optional. It holds the records `feature dropped`, `bug dropped` and `milestone reviewed`. Only a tool writes it. |
| D317 | `Out of scope` lists what the milestone does not deliver. Do not implement an item of this list. |
| D318 | A milestone with zero features and one or more bugs is valid. |

```mermaid
stateDiagram-v2
    state "in progress" as progress
    [*] --> open
    open --> progress: plan_create commit
    progress --> done: plan_close, acceptance passes
    progress --> progress: plan_close, acceptance fails
    open --> dropped: progress drop-feature
    progress --> dropped: progress drop-feature
    open --> migrated: milestone_close migrate
    progress --> migrated: milestone_close migrate
    done --> [*]
```

## Bugs
```mermaid
flowchart TD
    user[The user reports a bug] --> report[bug-report]
    review[A review posts a Pre-existing problem] --> report
    accept[The user accepts a problem of a blocked plan] --> report
    report --> test{Can a test show the bug?}
    test -->|yes| name[Acceptance: name of the regression test]
    test -->|no| manual[Acceptance: manual check]
    name --> add[python -m tools.progress add-bug]
    manual --> add
    add --> wait[The bug waits for a fix plan]
    wait --> fix[plan-create with type fix]
    fix --> run[step-run: test first, then the fix]
    run --> verify[bug-fix at plan close]
    verify --> removed[plan_close removes the row]
```

| ID | Rule |
|---|---|
| D400 | The `Bugs` table lists open bugs only. A tool removes a fixed or dropped bug. |
| D401 | A bug text has max 12 words. It names what the user sees, never a fix. |
| D402 | `Cause` is empty, `user <cause>` or `<research id> <cause>`, with max 20 words. The prefix names the source of the cause. |
| D403 | `Feature` is empty, a feature id of the milestone, or `M001-F03` for a feature of a different milestone. |
| D404 | `Source` is `user`, or the plan id and the problem id of the review. |
| D405 | A bug without acceptance is not added. Ask the user when you cannot derive it. |
| D406 | A bug of a closed milestone goes to the open milestone. When no milestone is open, create one with the goal `Fix the open bugs of version <version>`. |
| D407 | A bug reported during a plan does not change that plan. It waits for a fix plan. |
| D408 | The user chooses the bugs of a fix plan. In the bugfix phase the plan takes all open bugs. Tell the user the bug list before you write the plan of a bugfix phase. |
| D409 | Only the user drops a bug. The reason has max 12 words. It is the value of `--answer`. |
| D410 | A problem in a `done` feature is a bug. A feature plan never references a `done` feature. |

## PROGRESS.md
```
| Milestone | Features | Done | Bugs | Status |
|---|---|---|---|---|
| M001 map-view | 5 | 5 | 0 | closed |
| M003 route-planning | 5 | 1 | 2 | open |
| M004 offline-maps | 3 | 0 | 0 | draft |
```

| ID | Rule |
|---|---|
| D500 | The table is the only content of the file. `python -m tools.progress` writes it. |
| D501 | Dropped and migrated features count in `Features` and not in `Done`. |
| D502 | A draft stands in the table from its first commit on. |

## Plan file
```
---
id: M003-P002
milestone: M003
type: feature
features: [F02, F04]
done: [F04]
status: in progress
closed:
---
# M003-P002 Save and delete

## Steps
| Step | Feature | Text | Verification | Dependencies |
|---|---|---|---|---|
| S01 | F02 | Save the route from the route menu in the format of the design | TEST route_save passes | DEP-02 |
| S02 | F04 | Remove a waypoint on right click | TEST route_delete passes | none |

## Fix steps
| Step | Feature | Problem | Text | Verification |
|---|---|---|---|---|
| S03-fix | F02 | N07 | Return before the division when points is empty | TEST route_save passes |

## Verification
- TEST route_save passes
- TEST route_delete passes
```

| ID | Rule |
|---|---|
| D600 | `type` is `feature`, `fix` or `refactor`. A fix plan holds its bug ids in the field `bugs`, not `features`. |
| D601 | A refactor plan holds features of the type `refactor` only. A feature plan can hold a feature of the type `refactor`, and its steps stand before the steps of the other features. |
| D602 | A step of a feature of the type `refactor` is a refactor step. Its checks are existing tests of the changed code. |
| D603 | A refactor step that adds the first instance of a structure has the new test of the feature acceptance as a further check. |
| D604 | A refactor step adds no instance, so the row `DEP-01` does not apply to it. |
| D605 | `Dependencies` holds the id of each row of `docs/DEPENDENCIES.md` whose trigger the step meets, or `none`. The tools refuse an empty cell. |
| D606 | The `Verification` section of the plan lists the validation of each dependency that a step names, when it is a check. |
| D607 | `python -m tools.step_close set-dependencies` writes the `Dependencies` cell of a step of the running plan, also of a complete step. It adds the validation of each named row that is a check to the `Verification` section. A cell that drops a named row needs `--answer`. |
| D608 | `status` is `draft`, `in progress`, `blocked` or `closed`. |
| D609 | A plan references ids of its own milestone only. |
| D610 | `python -m tools.plan_close` writes `done`: the ids whose acceptance check passed at plan close. |
| D611 | The archive holds files with content only. `plan_close` removes `extensions.md`, `problems.md` and `evidence/` from the plan folder when they hold nothing beyond their template. |
| D612 | A step names the feature id or the bug id that it serves. |
| D613 | A step text has max 20 words. The verification is one check in the form of an acceptance. |
| D614 | The verification passes after that step alone. Cut a step as one increment that the user can see. |
| D615 | In a fix plan each bug has one step. The verification is the acceptance of the bug. |
| D616 | A fix plan with a bug without a cause starts with a diagnosis. It is a research step with the question `What causes these bugs, and which bugs share a cause?`. The diagnosis names per bug the cause and the section of the design or of a research that the fix follows. The session then writes the fix steps with `set-text` and the user key. |
| D617 | Bugs with one cause share one fix. The first step of the group fixes the cause. Each further step adds its regression test, with a mutation run as its failing run. |
| D618 | `plan-create` searches the ideas file and the research files for the topics of the bugs of a fix plan. The step of a bug names each match. |
| D619 | Only `python -m tools.step_close add-fix` writes the `Fix steps` table. |
| D620 | When a feature has problems with the answer `user replan` in an archived plan, write them into the step texts. |
| D621 | A step with the verification `COMMAND research_check passes` is a research step. Its text is the question. It is the first step of its feature. |
| D622 | A research step adds a research file and changes no source file and no test file. The step gate refuses such a change. |
| D623 | `python -m tools.step_close set-text` writes the new text of a step that is not complete, after the approval of the user. Its record keeps the old and the new text. |

```mermaid
stateDiagram-v2
    state "in progress" as progress
    [*] --> draft: plan_create start
    draft --> progress: plan_create commit
    progress --> blocked: step_close block, plan_close block
    blocked --> progress: step_close unblock, plan_close unblock
    progress --> closed: plan_close
    closed --> [*]
```

## Plan progress file
```
| Step | Feature | State | Evidence | Round |
|---|---|---|---|---|
| S01 | F02 | complete | evidence/S01-test.txt | 1 |
| S02 | F04 | blocked | evidence/S02-test.txt | 2 |
```

| ID | Rule |
|---|---|
| D700 | `State` is `open`, `in progress`, `complete` or `blocked`. `python -m tools.step_close` writes it. Each state other than `open` stands in bold. |
| D701 | `Evidence` names the file that holds the raw output of the step. |
| D702 | `Round` is the review round in which the step got its state `complete` or `blocked`. |

```mermaid
stateDiagram-v2
    state "in progress" as progress
    [*] --> open
    open --> progress: step_close start
    progress --> complete: step_close close
    progress --> progress: step_close revert
    progress --> blocked: step_close block
    blocked --> progress: step_close unblock
    complete --> [*]
```

## Extensions file
```
| ID | Extension | Decision | Detail |
|---|---|---|---|
| E01 | Export a route as GPX | feature | M003 |
| E02 | Undo for the waypoint delete | dropped | Not necessary for the first version |
| E03 | Zoom to the route after load | | |
```

| ID | Rule |
|---|---|
| D800 | Each entry gets one decision of the user before the plan closes: `feature`, `refactor` or `dropped`. `feature` and `refactor` hold the milestone id in `Detail`. `dropped` holds a reason of max 12 words. |
| D801 | `refactor` is the decision for a structural extension. It becomes a feature of the type `refactor`, which a refactor plan or the plan of the next instance implements first. |
| D802 | Add an approved entry with `python -m tools.progress add-feature`. |

## Problems file
```
## Problems
| ID | Step | Round | Severity | Rule | Topic | Location | Trigger | Class | Fix | Answer | Check |
|---|---|---|---|---|---|---|---|---|---|---|---|
| N01 | S01 | 1 | Important | C002 | empty input | src/route/draw.py:88 | A route with zero points | Every caller of draw() | Return when points is empty | fixed 3f2a91c | confirmed |
| N02 | S01 | 1 | Nit | C005 | helper | src/route/save.py:12 | The helper has one caller | save.py only | Move the helper inline | closed intentional The design names the helper | confirmed |
| N03 | plan | 1 | Pre-existing | C002 | zoom limit | src/map/view.py:40 | Zoom below zero | view.py only | Clamp the zoom | bug B03 | |

## Records
- step started S01 3f2a91c0d1e2 2026-11-10
- step reviewed S01 2026-11-10
- approved S01 77aa01b2c3d4 2026-11-10
- review passed 9c1d22e3f4a5 2026-11-11
```

| ID | Rule |
|---|---|
| D900 | The review skill adds each problem row with `python -m tools.step_close add-problem`. `Step` is a step id, or `plan` for a plan review problem. |
| D901 | Only a tool writes the problems file. The problem commands validate each value, name the broken rule and commit at once. The add command appends a row, and the answer and check commands each change one cell. No command changes or drops a posted row. |
| D902 | The implementor writes `Answer` with `python -m tools.step_close answer-problem`: `fixed <commit>` or `closed <category> <reason>`. A problem with the answer `fix <step>` takes no further answer. |
| D903 | The categories are `wrong`, `intentional` and `prevented`. `wrong`: the trigger does not exist. `intentional`: name the design or the convention. `prevented`: name the place that prevents the trigger. |
| D904 | In a later round the review skill writes `Check` with `python -m tools.step_close check-problem` for each problem of the round before: `confirmed` or `re-raised <trigger>`. A re-raised problem that a new row of the same step carries gets `carried <id>`. |
| D905 | A gate treats a problem with `carried <id>` as closed when the row with that id has an answer and the check `confirmed`. |
| D906 | The answer of a `Pre-existing` problem is `bug <id>`. The plan close runs `bug-report` for it in the main repository and writes the answer with `answer-problem`. |
| D907 | `Topic` holds one or two words for the subject of the failure. A problem with the subject of an earlier problem takes its topic. |
| D908 | The implementor decides before each fix if the trigger exists and if the design wants the behavior. It closes the problem with its category when not. |
| D909 | A tool writes the answers `reverted`, `user <text>` and `fix <step>`. |

| Record | Writer |
|---|---|
| `step started <step> <hash>` | `step_close start` |
| `step reviewed <step>` | `step_close review` |
| `step reverted <step>` | `step_close revert` |
| `step blocked <step> <problems>` | `step_close block` |
| `step unblocked <step> old: <answers> new: <answer>` | `step_close unblock` |
| `text changed <step> old: <text> new: <text>` | `step_close set-text` |
| `dependencies removed <step> old: <ids> new: <ids>` | `step_close set-dependencies` |
| `fix added <step> <problem>` | `step_close add-fix` |
| `approved <step or close> <hash>`, `rejected <step or close> <hash>` | `approve` |
| `manual passed <id> <check> <hash>`, `manual failed <id> <check> <hash>` | `step_close close`, `plan_close check` |
| `plan manual passed <check> <hash>`, `plan manual failed <check> <hash>` | `plan_close check` |
| `milestone manual passed <feature> <check> <hash>`, `milestone manual failed <feature> <check> <hash>` | `milestone_close check` |
| `bug verified <bug>` | `plan_close verify-bug` |
| `bug verified withdrawn <bug>` | `plan_close unblock`, `progress drop-bug` |
| `tuning done` | `plan_close tuning` |
| `plan reviewed` | `plan_close reviewed` |
| `document reviewed` | `plan_create reviewed` |
| `review passed <hash>` | `plan_close review-passed` |
| `plan blocked <problems>` | `plan_close block` |
| `plan unblocked <choice> <id> old: <answers> new: <answer>` | `plan_close unblock` |

## Step execution
```mermaid
sequenceDiagram
    participant I as Implementor
    participant T as Tools
    participant R as Reviewer
    I->>T: step_close start
    I->>I: implement the step
    I->>T: test with --step
    T-->>I: evidence file
    loop max 3 rounds, a further round only after an Important problem
        I->>T: step_close review
        I->>R: diff, plan diff, evidence, notes
        R-->>I: problems
        I->>I: answer each problem
    end
    alt Important problem open after the last round
        I->>T: step_close revert, then one new attempt
        I->>T: step_close block after the second attempt
    else all problems answered
        I->>T: approve, when a protected path changed
        I->>T: step_close close
        T-->>I: step gate, then the commit
    end
```

| ID | Rule |
|---|---|
| D1000 | Prove a step with output. `python -m tools.test` writes the evidence, not the agent. |
| D1001 | Each step has a review. The reviewer runs in a fresh context. |
| D1002 | Give the reviewer notes of max 10 lines on why the change has this form. |
| D1003 | Answer each problem. A step has max 3 review rounds. A further round runs only when the round before posted an `Important` problem. |
| D1004 | A later round reviews the new diff and the answers of the round before. A `Nit` of the last round needs no check. |
| D1005 | An `Important` problem that round 3 posts gets one short check of its fix. An `Important` problem that round 3 or the short check re-raises is open. Revert the step and use a different approach. |
| D1006 | A step has one new attempt. After the second attempt fails, block the step and ask the user. The user can also accept the open problem of a step in progress: `step_close unblock` writes the decision of `--answer`, and the step goes on. |
| D1007 | No other step starts while a step has the state `blocked`. |
| D1008 | The agent commits during a step as often as necessary, with a message of its own. A tool commits each of its own state writes at once. |
| D1009 | A delegated agent first compares its directory with the worktree of its task, then reads the memory index. It follows each memory of the types user and feedback like the main session. |
| D1010 | A memory of the types user and feedback adds its conditions to each skill step that it touches. A skill step never overrides such a memory. |
| D1011 | Tuning requests of a manual check belong to the step of the check, also when they touch an earlier step of the feature. |
| D1012 | The `implementor` agent writes the code and the documents of a step in a fresh context. The main session runs the tools and reads the reports. |
| D1013 | In a research step the `researcher` agent takes the place of the implementor. The document review of the research file is the review of the step. |
| D1014 | A step revert keeps the commits outside the step: memories, setup findings, milestone files and other plans. It names each kept commit. |
| D1015 | A bug that sits in a test has a mutation run as its failing run. The mutation breaks the behavior that the test guards, and no commit holds it. `python -m tools.test <name> --mutation <patch> --step <step>` is the only way of a mutation run. It needs a clean work tree, applies the patch, runs the test as a run that must fail and takes the patch back. |
| D1016 | Start the step before the first write to a source or test folder. The pre-commit check rejects such a change while a plan is active and no step is in progress. |

## Plan close
```mermaid
flowchart TD
    sync[Worktree: plan_close sync] --> wiki[Wiki update, committed]
    wiki --> review[review-plan]
    review --> important{Important problem open after the last round?}
    important -->|no| passed[plan_close review-passed]
    important -->|yes| existing{Fix step for this rule exists?}
    existing -->|no| fix[step_close add-fix, then step-run]
    fix --> review
    existing -->|yes| block[plan_close block, ask the user]
    block --> choice[accept, drop or replan]
    choice --> passed
    passed --> merge[Main repository: plan_close merge]
    merge --> green{Checks and tests pass on the merged tree?}
    green -->|no| review
    green -->|yes| writes[Agent writes of the close, committed]
    writes --> approve[approve close, when a protected path changed]
    approve --> close[plan_close]
    close --> gate{Plan gate}
    gate -->|fail| writes
    gate -->|pass| done[Archive, remove the worktree and the branch]
```

| ID | Rule |
|---|---|
| D1100 | The agent writes of the close run in the main repository. They are: memory consolidation, tuning, extension decisions, the bug reports of the plan, bug verification and dependency proposals. |
| D1101 | Run `python -m tools.plan_close check` after the merge. It records the manual acceptance checks. |
| D1102 | The plan review is the last change of the worktree. It follows the sync and the wiki update. A plan that changed no source or test file needs no plan review. |
| D1103 | `python -m tools.plan_close sync` merges the milestone branch into the plan branch. After a merge with a conflict the plan needs a plan review of that state. |
| D1104 | `python -m tools.plan_close merge <plan>` tags the plan branch as `closed/<plan id>` and makes the commit `Plan merged:` with a squash. One plan is in close at a time. |
| D1105 | The milestone tables and `PROGRESS.md` belong to the main repository. In a worktree, the progress check skips them. The plan merge rewrites them on the merged tree and stages them before its checks. |
| D1106 | The writes of the close after the merge change no source file and no test file. The plan gate refuses such a change. |
| D1107 | Round 1 of the plan review starts with a run of each `COMMAND` check of the `Verification` section in the worktree. A test that fails there or at the plan merge goes into the task of the plan review. The review posts it as an `Important` problem, and a fix step carries the fix. |
| D1108 | A failing acceptance check does not block the plan close. An acceptance command without a binding is a failing check. The feature stays `in progress`. |
| D1109 | The plan review has max 3 rounds, a further round only after an `Important` problem, and the short check of D1005. An `Important` problem open after that gets a fix step. |
| D1110 | A fix step runs under the step rules. The plan review runs again after it. |
| D1111 | Each rule id gets max one fix step per plan close. After that, block the plan and ask the user. |
| D1112 | The user chooses `accept`, `drop` or `replan` for a blocked plan. `accept`: the tool closes the problem with the reason of the user. Run `bug-report` for it. `drop`: the tool drops the feature or the bug. The plan closes without that id in `done`. `replan`: the feature stays `in progress` or the bug stays in the table. The next plan reads the open problems. |

## Tuning
| ID | Rule |
|---|---|
| D1200 | The implementor owns the tuning. Run `python -m tools.plan_close tuning` in the main repository after the merge. |
| D1201 | A topic with an `Important` problem in this plan and in an earlier plan has three answers. Add one row to the failure patterns of `REVIEW.md`, propose a dependency, or run a research on the cause. A refactor feature is a possible result of that research. |
| D1202 | A rule id closed as `wrong` or `intentional` twice and confirmed: remove the pattern from `REVIEW.md`, or add the intent to a conventions file. |
| D1203 | A rule id fixed three times: add a lint rule or a convention rule. |
| D1204 | A bug with the source `user` in a `done` feature: add one line to the failure patterns of `REVIEW.md`. |
| D1205 | Show the tuning changes to the user with the extension decisions. Apply them after the user agrees. |
| D1206 | The tuning adds a line to `REVIEW.md`, a conventions file or the blocklist. It never changes a skill or an agent definition. |

## Milestone close
| ID | Rule |
|---|---|
| D1300 | Before the acceptance checks and the final manual check, the milestone review checks the sum of the plans against the design. `python -m tools.milestone_close reviewed` records it. An `Important` problem of the milestone review becomes a bug or a refactor feature of the milestone. The review also runs on user request. |
| D1301 | `python -m tools.milestone_close check` runs each acceptance check of the feature table. |
| D1302 | `python -m tools.milestone_close` applies the gate, writes the version, archives the file, merges the branch with a squash, tags it as `milestone/<id>` and deletes it. |
| D1303 | The user can close a milestone early. Close the active plan first. |
| D1304 | For a premature close, the migrated features go into the first draft or into a new draft. The user chooses. The draft starts with the migrated features in id order and the migrated bugs, with new ids. |
| D1305 | `python -m tools.milestone_close migrate <new id>` closes the old milestone and opens the committed draft. |
| D1306 | A migrated feature keeps nothing from its old plans. The new milestone tracks it from the state `open`. |
| D1307 | After a close, `milestone-close` offers the first draft. Before the draft opens, check it against the closed milestone and run a document review of the changes. |

## Gates
A gate runs its checks itself. A gate failure names the missing item.

| Gate | Tool | Conditions |
|---|---|---|
| Step | `step_close close` | The milestone tables hold the id of the step. A review exists. Each problem has an answer. No `Important` problem is open. An approval covers the protected paths. The verification, `tools.check` and each test file that the step changed pass. The evidence file exists. A research step added a research file and changed no source or test file. |
| Plan merge | `plan_close merge` | The worktree is clean. The plan branch holds the tip of the milestone branch. Each step is complete. Each problem has an answer. When the plan changed product code against the milestone branch, its newest own commit is the `Review passed:` commit. Only a sync without a conflict follows it. On the merged tree, `tools.check`, the checks of the `Verification` section and each test file that the plan changed pass. |
| Plan | `plan_close` | The work tree is clean. No source or test file changed after the `Plan merged:` commit. Each step is complete. Each problem has an answer. The tuning ran. Each extension has a decision. An approval covers the protected paths of the close. The memory lint, `tools.progress`, `tools.licenses` and `tools.check` pass. |
| Milestone | `milestone_close` | A milestone review record exists. Each feature is `done` or `dropped`. The `Bugs` table is empty. Each plan is in `archive/`. Each acceptance check of a `done` feature passes. `tools.progress`, `tools.licenses` and the whole suite pass. |

| ID | Rule |
|---|---|
| D1400 | A step of a dropped feature or a dropped bug is not necessary for a gate. |
| D1401 | A premature close accepts open features. The tool sets them to `migrated`. |
| D1402 | The reviewer result never replaces a user approval. |

## Approval records and write protection
| ID | Rule |
|---|---|
| D1500 | The protected paths are in `docs/REVIEW.md`. |
| D1501 | A step that changes a protected path needs `python -m tools.approve <plan> <step>` before the step gate. A plan close that changes a protected path after the merge needs `python -m tools.approve <plan> close` before the plan gate. |
| D1502 | Commit before the approval. The record holds the `HEAD` hash. A later change to a protected path invalidates it. |
| D1503 | Ask the user in the chat first, and wait for the answer. A request for a change is not its approval. Then pass the answer with `--answer`. Never answer for the user. A delegated manual check gets `--by agent`. |
| D1504 | A command that changes or loosens a decision of the user takes `--answer`. The permission rule on `--answer` is the user key. It stays as it is, in each permission mode. |
| D1505 | A state of a step blocks one command only: a complete step takes no new text. An `unblock` and a drop take the reason of the user as the value of `--answer`. |
| D1506 | The bash guard refuses a command that holds `--answer` and a second command, also in the main session. Only a leading `cd <folder> &&` may stand before it. |
| D1507 | Where the provider has a permission rule for it, the provider asks the user before each command that holds `--answer`. It asks too before a command that names the variable of a tool commit. The same holds for a command that imports a module of the tools into a line of code. The user can approve such a command for a repair by hand. |
| D1508 | A milestone file and a plan file are editable while `status` is `draft`. `python -m tools.milestone_create commit <id>` makes each commit of a milestone draft. |
| D1509 | After the creation commit, each write to a milestone file, `plan.md`, `progress.md` and `PROGRESS.md` goes through a tool. A tool commits its write at once: to such a file, an evidence file, the problems file, the ideas file and the dependencies file. The commit check refuses each other commit that holds one. A tool that refuses a work tree names each changed file and the tool that writes it. |
| D1510 | Never delete, rename or move a milestone file, a plan folder or an archive entry by hand. |
| D1511 | Never edit a generated file. Edit the source and run the generator. |
| D1512 | Write only inside the repository. A temporary file goes into `docs/plans/<plan>/tmp/`, `docs/research/tmp/` or `docs/milestones/tmp/`. |
| D1513 | Outside the repository, the pre-write hook allows only the user folder of the provider. The bash guard refuses a command of an agent that names a path outside the repository. |
| D1514 | The bash guard allows the folders of `toolchain_folders` and `dependency_source` in `tools/project.toml`. It does not check the main session. |
| D1515 | An agent reads a dependency only in the folder that `python -m tools.project source` prints, never in a folder of the user account. It never asks for a permission to read outside the repository. |
| D1516 | The pre-write hook and the bash guard judge the work of an agent against the root of its path. The root is the main repository or the worktree that holds the path. The first write of an agent binds it to its root. Work without an agent keeps the root of the session. |

## Commits
The tools make these commits. The agent never makes them by hand.

| Commit message | Tool |
|---|---|
| `Project initialized`, `Project updated` | `project init`, `project update` |
| `Milestone drafted: M004`, `Milestone draft removed: M004` | `milestone_create commit`, `milestone_create remove` |
| `Milestone created: M003` | `milestone_create open`, `milestone_close migrate` |
| `Plan created: M003-P002` | `plan_create commit` |
| `Step started: M003-P002 S01`, `Step reviewed:`, `Step blocked:`, `Step unblocked:`, `Fix step added:` | `step_close start`, `review`, `block`, `unblock`, `add-fix` |
| `Problem added: M003-P002 N01`, `Problem answered:`, `Problem checked:` | `step_close add-problem`, `answer-problem`, `check-problem` |
| `Evidence: M003-P002 S01` | `test --step` |
| `Approval recorded: M003-P002 S01` | `approve` |
| `Step closed: M003-P002 S01` | `step_close close` |
| `Feature added: M003 F06`, `Feature dropped: M003 F06 <reason>` | `progress add-feature`, `progress drop-feature` |
| `Dependency added: DEP-02`, `Dependency changed: DEP-02`, `Dependency removed: DEP-02 M003-P002` | `dependency add`, `dependency change`, `dependency remove` |
| `Bug reported: M003 B01` | `progress add-bug` |
| `Bug fixed: M003 B01` | `plan_close` |
| `Bug dropped: M003 B02 <reason>` | `progress drop-bug` |
| `Idea added: IDEA001` | `ideas add` |
| `Ideas removed: IDEA001 IDEA002 <reason>` | `ideas remove` |
| `Milestone updated: M003` | `progress set-goal`, `progress out-of-scope` |
| `Plan synced: M003-P002`, `Plan synced with conflicts: M003-P002` | `plan_close sync` |
| `Plan blocked: M003-P002`, `Plan unblocked: M003-P002` | `plan_close block`, `plan_close unblock` |
| `Plan reviewed: M003-P002`, `Tuning done:`, `Manual check recorded: M003-P002`, `Bug verified: M003-P002 B01` | `plan_close reviewed`, `tuning`, `check`, `verify-bug` |
| `Review passed: M003-P002` | `plan_close review-passed` |
| `Plan merged: M003-P002` | `plan_close merge`, as the squash commit on the milestone branch |
| `Milestone reviewed: M003` | `milestone_close reviewed` |
| `Manual check recorded: M003-P002 S01` | `step_close close`, for a failed manual check |
| `Manual check recorded: M003 F01` | `milestone_close check` |
| `Plan closed: M003-P002` | `plan_close` |
| `Version: 1.12.0` | `milestone_close`, on the milestone branch |
| `Milestone closed: M003 1.12.0` | `milestone_close`, on the milestone branch and as the squash commit on the main branch |

| ID | Rule |
|---|---|
| D1600 | No tool pushes, pulls or fetches. The user pushes. |
| D1601 | The main branch holds the closed milestones. Its name is `main_branch` in `tools/project.toml`. It gets one commit per milestone: `Milestone closed: M003 1.12.0`, the goal and the done, dropped and migrated features. |
| D1602 | Each milestone has one branch, for example `milestone/M003-route-planning`. Each commit of the milestone is on it. |
| D1603 | Each plan has one branch from the milestone branch, for example `plan/M003-P002`. The milestone branch gets the commits `Plan merged:` and `Plan closed:` per plan. |
| D1604 | The tag `closed/<plan id>` keeps the commits of a plan branch, the tag `milestone/<id>` those of a milestone branch. The user pushes the tags. |
| D1605 | A tool stops on the wrong branch, on a detached `HEAD`, or during an open merge or rebase. |
| D1606 | Resolve a merge conflict of the milestone close, run `git add`, then run the tool again. |
| D1607 | The commits of the milestone branch stay on that branch until the tool deletes it. A tool reads the history of the main branch for no state. |
| D1608 | Each active plan has one worktree, and the plan close removes it. Do not create a different worktree unless the user asks. |

## Versions and deployment
```
# v1.12.0 - 2026-10-28 18:42:10
- New feature: User permission system added
- Update: Route save dialog shows the file name before saving

# v1.11.25 - 2026-09-01 12:14:00
- Bugfix: User names with non-ASCII characters fail registration
```

| ID | Rule |
|---|---|
| D1700 | `python -m tools.milestone_close` writes `CHANGELOG.md` with one entry per milestone: the `New feature` lines, then the `Update` lines, then the `Bugfix` lines. Do not log a change by hand. |
| D1701 | A milestone with a done feature gives a minor version. A milestone with fixed bugs only gives a patch version. A milestone with nothing done gives no version. A plan close gives no version. The user decides a major version. |
| D1702 | The first version counts from `start_version` in `tools/project.toml`. |
| D1703 | Legacy support and migration are necessary only for an entry of `DEPLOYMENT.md`. |
| D1704 | The user writes `DEPLOYMENT.md` at each deployment. Ask the user when a change conflicts with an entry. |

```
---
version: 1.12.0
---
# Deployment

## Compatible
| Path | What must stay compatible |
|---|---|
| src/storage/schema.sql | Saved routes of version 1.x load without change |
```

## Ideas file
`docs/IDEAS.md` holds the ideas for features of later milestones that no milestone plans yet.

| ID | Rule |
|---|---|
| D1800 | The table has the columns `ID`, `Time`, `Source` and `Idea`. Only `python -m tools.ideas` writes it. |
| D1801 | `ID` is `IDEA` and a number of three digits, for example `IDEA001`. An id is never used twice, also after its row was removed. |
| D1802 | `Time` is the local date and time in the form `2026-11-14 15:30`. `Source` is `user` or `agent`. |
| D1803 | `Idea` has max 100 words and names what the user sees. It can hold more than one sentence. |
| D1804 | A milestone that plans an idea removes its row with the milestone id as reason. |
| D1805 | `python -m tools.ideas edit` writes the new text of an idea. The id, the time and the source stay. |

## Licenses file
`docs/LICENSES.md` lists each outside item of the project whose license is not on the free list of `tools/project.toml`.

```
| Item | Source | License | Author | Attribution | Condition |
|---|---|---|---|---|---|
| map-tiles | https://example.org/map-tiles | CC-BY-4.0 | Example Maps | Map data by Example Maps | |
```

| ID | Rule |
|---|---|
| D1900 | An outside item is a library, an asset or a code pattern that the project did not make. `Item` is its name in the manifest, or its path. |
| D1901 | A row exists only for an item with a license outside the free list: an attribution, a copyleft, a paid license or another condition. |
| D1902 | `Attribution` holds the text that the license asks for. `Condition` holds each other condition of the license or of the terms. |
| D1903 | An asset that the project builds itself needs no row. Each source of its data needs a license check: a generator model, a texture, a font or a reference image. |
| D1904 | The terms of a model or a tool can set a condition beyond the license name. An example is a free license that ends above a limit of revenue or users. A source with such a condition counts as outside the free list. Its row holds the condition. |
| D1905 | `python -m tools.licenses` reads the license of each dependency of the manifests. It lists each dependency with a license outside the free list that has no row. |
| D1906 | The plan gate and the milestone gate run the license tool. An item that it lists gets its row, or the user removes the item. |

## Research file
A research file answers one question before the work on a feature. The skill `research-run` writes it through the `researcher` agent.

| ID | Rule |
|---|---|
| D2000 | The file has the name `R[NNN]-[NAME].md`. Its first line is the title with the id and the subject. One line under the title holds the date and the scope of the research. |
| D2001 | The file marks each fact as `run` when an experiment or a spike showed it, or as `read` when only a source states it. It marks each statement that the research did not verify as not verified. |
| D2002 | A research on a change of existing code can run a spike. `python -m tools.research spike <id>` creates the branch `spike/<id>` and its worktree, and `spike-end <id>` deletes both. In a spike, the `implementor` agent builds the core of the change and runs the whole suite. The research file lists each failure with its cause. No commit of a spike reaches the milestone branch. |
| D2003 | A step that rests on a fact that the research marks as `read` says so in its text. |
| D2004 | The file ends with a recommendation or the lessons for the project, then the section `Sources`. Each part between that frame has the shape that fits the subject. No rule prescribes a further section. |
| D2005 | `python -m tools.research check` fails only when the title, the line with date and scope or the section `Sources` is missing or empty. |
| D2006 | A recommendation that changes the design goes to the user. Only the user changes a design document. |
| D2007 | A feature needs research when a trigger of the section Research of the skill `plan-create` holds. |
| D2008 | The researcher starts max 4 sub agents per research, each on the cheapest model class, and only for searches that read. |

## Document review
A document review checks a milestone file, a plan file, a research file or a dependency row.

| ID | Rule |
|---|---|
| D2100 | Count the new `Important` problems of each round. A round converges when it posts fewer than half of the round before. When a round does not converge, stop the review by reading. Run a spike on the open question, or cut the scope of the document. |
| D2101 | A document with unchecked fixes of `Important` problems is not committed. One short check of these fixes runs after the last round. It confirms or re-raises them and posts nothing new. |

## Dependencies file
`docs/DEPENDENCIES.md` holds the structural dependencies of the project.

```
## Dependencies
| ID | Trigger | Action | Validation |
|---|---|---|---|
| DEP-01 | A step adds one more instance of a type that the project already has, such as a data file, a message or a handler. | Add only the own places of the instance. When it repeats knowledge of the type in another place, stop and record a structural extension. | The reviewer names each place outside the instance that repeats knowledge of the type as Shotgun Surgery, or states that there is none. |
| DEP-02 | A step adds state of a running session | Carry it through each restart path | TEST session_restart passes |

## Records
- added DEP-01 template 2026-11-08
- added DEP-02 M003 2026-11-10
- changed DEP-01 user 2026-11-12
```

| ID | Rule |
|---|---|
| D2200 | An id is `DEP-` and a number of two digits, from `DEP-01` on. An id is never used again, also after the removal of its row. |
| D2201 | A dependency names a system of the project, not a detail of the code. |
| D2202 | A miss of the dependency breaks something that the tests of the step do not cover. |
| D2203 | A row is not allowed when a conventions rule or one test can express it. |
| D2204 | The file holds max 9 rows. A further row needs a removal first. |
| D2205 | `Validation` is a check that a tool or the reviewer can run. |
| D2206 | `Trigger` names the kinds of change that meet the row, not only the kinds of state that it guards. |
| D2207 | Only `python -m tools.dependency` writes the file. Each add, change and removal writes one record line with the source or the reason. |
| D2208 | `python -m tools.dependency change` writes new cells into a row on a decision of the user. The row keeps its id. |
| D2209 | `dependency-add` proposes a row at two times only: at the milestone creation from the design, and at the plan close for a topic that came back. The user decides. |
| D2210 | `dependency-remove` removes a row only in the close of a refactor plan, and only when the reviewer agrees that the row has no value any more. |
| D2211 | The row `DEP-01` belongs to the setup. Each other row belongs to the project. |
| D2212 | A type is a group of things that the project already has and that share one structure. |
| D2213 | Knowledge of a type is a fact that holds for each instance, such as where its files lie or how a program loads it. |
| D2214 | The own places of an instance are its code, its data, its tests and its registration. A registration names the instance where the project lists the instances of its type. |
| D2215 | The reviewer names a place by its unit: a function, a method, a data structure, a constant, or a file without such units. |

## Local memory
```
---
type: feedback
source: M003-P002
modified: 2026-11-06
---
# Use pnpm, not npm
npm install rewrites the lockfile and breaks CI.
```
Index line: `- [feedback] MEM-use-pnpm: Use pnpm, not npm`

| ID | Rule |
|---|---|
| D2300 | `type` is `user`, `feedback`, `project` or `reference`. `source` is a plan id or `user`. |
| D2301 | The title is the index summary. It has max 12 words. |
| D2302 | An entry has max 15 body lines, one fact and ASCII characters only. |
| D2303 | The index has max 100 lines. `python -m tools.memory_index` writes it. |
| D2304 | `memory-save` sets `modified` on each write or confirmation. |
| D2305 | An entry is stale when `modified` is before the `closed` date of the fifth most recent archived plan. |
| D2306 | `memory-consolidate` runs at each plan close and when the index is over its limit. |
| D2307 | The memory feature of each provider stays off. |

## Developer wiki
| ID | Rule |
|---|---|
| D2400 | The wiki describes the product: architecture, subsystems, data, and the build, run and debug procedures. The wiki holds nothing about the AI setup: no agent, skill, hook, provider, gate, plan, memory or tool. |
| D2401 | A page of a system or of the architecture starts with one Mermaid diagram. The text follows it. |
| D2402 | The wiki has four default groups, each in its own folder: `start/`, `architecture/`, `systems/` and `working/`. |
| D2403 | `start/` holds `setup.md` and `repository-tour.md`. `architecture/` holds `overview.md` and one page per further subject of the architecture. `systems/` holds one page per system of the product. `working/` holds `build-and-run.md`, `testing.md` and one page per recurring task. |
| D2404 | A project adds groups for its domain, for example for its content and for its tuning values. No group uses the folder `assets/`. |
| D2405 | A system page has these sections in this order: `What it does`, `How it works`, `Where the code is`, `How to change or extend it`, `Gotchas`. |
| D2406 | `Where the code is` is a table of roles and paths. Each row names in one sentence the decision that its module hides (C011). `How to change or extend it` has one task per paragraph, with its steps. |
| D2407 | `README.md` is the overview: what the product does, its parts, its principles, its core words and the page map. The page map is a table with one row per page and what the page holds. It is the specification of the wiki of the project. |
| D2408 | `_sidebar.md` lists each page once under its group. Its paths start at the root of the wiki, with `/`. |
| D2409 | A value that a developer tunes stands in a table with its name in the code and its file. |
| D2410 | A change goes to the page that the page map names. A new system gets a new page, a row in the page map and a line in the sidebar. |
| D2411 | The wiki uses the dark theme `theme.css` of the tools. A project changes the look through the variables of that file. |
| D2412 | A wiki page uses relative links. |
| D2413 | Agents keep the wiki up to date. Never use the wiki as a source for a decision. |
| D2414 | `python -m tools.build_wiki_bundle` writes `docs/wiki/index.html` and `docs/wiki/assets/`. `python -m tools.build_wiki_bundle check` fails for a page outside the sidebar or the page map. It fails too for a system page without a section of its form, and for a link that names no page. |

Open `docs/wiki/index.html` in a browser, or run `python -m http.server 8000 --directory docs/wiki`.

## Agent tasks
| ID | Rule |
|---|---|
| D2500 | An agent task holds the goal and its sources: the step or the problem, the worktree, the design sections and the research files. It can hold the dependency rows, the decisions of the user and facts from earlier reports or from the output of a tool. A value that the user decided or the design states is a source too. |
| D2501 | An agent task holds no implementation step and no test instruction. These are the files to change, a value that no source states, the tests to write or run, test bounds and mutation runs. |
| D2502 | The agent derives the work from the sources and the conventions. An exception needs an explicit request of the user for that task. |

## Skills, agent definitions and AGENTS.md
| ID | Rule |
|---|---|
| D2600 | Read the whole file before a change. |
| D2601 | Adjust before you extend. Change the sentence, step or rule that covers the subject. Add a sentence only when no existing sentence covers the subject. |
| D2602 | Remove what the change makes obsolete in the same edit. Two statements on one subject never stay. |
| D2603 | The file describes the procedure as it is now. It holds no past decision and no reason for a past change. Never append a note, an exception, a reminder or a history line. |
| D2604 | A skill or an agent definition holds no project content: no milestone, plan, bug or problem id, no date, no version, no product term. |
| D2605 | A fact about the project lives in `docs/design/`, `tools/project.toml`, a memory or a conventions file. The skill names that place. A skill names no mode, tool or argument of the project. |
| D2606 | An agent prompt states the role, the input, the procedure and the output. It does not prescribe a decision that the agent can make. |
| D2607 | `AGENTS.md` holds the sections Project, Conventions, Status, Skills, Memory and Language. A rule longer than one line moves to a conventions file. |

## Source schema
| File | Fields |
|---|---|
| `.agents/skills/[NAME]/SKILL.md` | Frontmatter: `name` equal to the folder name, `description`. |
| `.agents/agents/[NAME].md` | Frontmatter: `name` equal to the file name, `description`, `model`, `tools`, optional `bash_allow`, optional `edit_allow`. The body is the prompt. |
| `.agents/hooks.yaml` | List of entries: `event`, `matcher`, `command`, `timeout` in seconds. |
| `.agents/mcp.yaml` | List of entries: `name`, `command` or `url`, optional `args`, optional `env`, `used_for`. |

| ID | Rule |
|---|---|
| D2700 | `model` is `fast`, `balanced` or `strong`. `tools` is a subset of `read edit write bash grep glob web agent`. The tool `agent` lets the agent start sub agents. `bash_allow` is a list of command prefixes. `edit_allow` is a list of globs. |
| D2701 | `event` is `session_start`, `pre_tool_use` or `post_tool_use`. A command has the form `python -m tools.<name>`. `matcher` is one string, or one string per provider with the keys `claude`, `codex` and `kilo`. |
| D2702 | `env` holds names of environment variables, never a value. A `url` entry has max one name, the bearer token. `used_for` has max 12 words. |

```yaml
- name: docs-lookup
  command: npx
  args: ["-y", "docs-lookup-server"]
  env: [DOCS_API_KEY]
  used_for: Framework documentation lookup in implementation steps
```

## Provider generation
`.agents/` and `AGENTS.md` are the source. `python -m tools.provider` generates the files of Claude Code, Codex and Kilo. Commit the generated files.

| | Claude Code | Codex | Kilo |
|---|---|---|---|
| Instructions | `CLAUDE.md` with `@AGENTS.md` | `AGENTS.md` | `AGENTS.md` |
| Skills | copy in `.claude/skills/` | `.agents/skills/` | `.agents/skills/` |
| Agents | `.claude/agents/*.md` | `.codex/agents/*.toml` | `.kilo/agents/*.md` |
| Hooks | `.claude/settings.json` | `.codex/hooks.json` | `.kilo/plugin/setup-hooks.ts` |
| MCP servers | `.mcp.json` | `.codex/config.toml` | `kilo.jsonc` |
| Model class | `haiku`, `sonnet`, `opus` | reasoning effort `low`, `medium`, `high` | the model of the session |
| Tool limits of an agent | `tools` list, project hook `agent_guard` with `agent_type` | stated in the prompt only | `permission` map |

| ID | Rule |
|---|---|
| D2800 | Run `python -m tools.provider` after a change to `.agents/` or `AGENTS.md` outside an agent session. `python -m tools.provider check` fails when the source changed after the last generation. |
| D2801 | Change an MCP server through `project-update` only. |
| D2802 | A provider change takes effect in the next session. Kilo needs `/reload`. |

Provider facts, checked against the provider documentation in November 2026. The machines of the checks had Claude Code 2.1.201 and 2.1.322. They had no Codex and no Kilo.

| Subject | Result |
|---|---|
| Claude Code: agent hook in the frontmatter | Not reliable. It fired in a headless session of 2.1.201. It did not fire in the VS Code extension of 2.1.322. The guard runs as a project hook. |
| Claude Code: hook input in a subagent | `agent_type` and `agent_id` since 2.1.290. A project hook runs inside each subagent. |
| Claude Code: environment variable in `.mcp.json` | `${NAME}` in `command`, `args`, `env`, `url` and `headers`. |
| Claude Code: provider memory | `autoMemoryEnabled: false` in `.claude/settings.json`. |
| Claude Code: question tool | `AskUserQuestion`, one to four questions, two to four options, multiple select. |
| Claude Code: ask rule | `permissions.ask` in `.claude/settings.json` with `Bash(* --answer *)`, one rule for the variable of a tool commit and three rules for an import of the tools. It asks in each permission mode and for a command inside a compound command. |
| Claude Code: prompt for `cd` with `git` | Not verified. A built-in check is the likely cause: it asks in each permission mode for one command line with `cd` and `git`. An agent in a worktree runs `git -C <worktree>`. |
| Codex and Kilo: ask rule | Not generated. The rule D1503 is the only protection there. |
| Codex: agent sandbox | An agent file cannot set `sandbox_mode`. An agent inherits the sandbox of the session. |
| Codex: hooks | `[features] hooks`, on by default. The trust of the project and `/hooks` are necessary. |
| Codex: hooks on Windows | Not verified. |
| Codex: provider memory | `[features] memories`, off by default. |
| Codex: question tool | `request_user_input` works in plan mode only. Ask in text. |
| Kilo: provider memory | Off by default. No configuration key exists. |
| Kilo: Claude Code compatibility | No configuration key exists. It is a setting of the VS Code extension. Keep it off. |
| Kilo: session start | No plugin event adds text to a new session. The `AGENTS.md` instruction applies. |
| Kilo: plugin dependencies | The plugin has none. Kilo installs its own plugin package at startup. |
| Kilo: question tool | Not verified. Ask in text when the session has no question tool. |
| Each provider: an agent that starts sub agents | Not verified. The tool `agent` maps to `Agent` in Claude Code and to the permission `task` in Kilo. The prompt of the agent holds the fallback. |

## Bootstrap
`python -m tools.setup` runs once per machine and per copy of the repository.
The tools need Python 3.11 or later and Git, for a project in any language. The Mermaid check of the wiki needs Node.js.

| Step | Effect |
|---|---|
| 1 | Creates the Git repository with the branch `main` when the folder has none. |
| 2 | Installs the Python packages of `tools/requirements.txt`. This includes Vale. |
| 3 | Installs the Git pre-commit hook that runs `python -m tools.check`. |
| 4 | Sets `PYTHONUTF8=1` for the user on Windows. |
| 5 | Runs `git add --renormalize .` when `.gitattributes` changed. |
| 6 | Runs `python -m tools.build_wiki_bundle` and `python -m tools.provider`. |

## Project init and update
```mermaid
flowchart TD
    setup[python -m tools.setup] --> design{Documents in docs/design/?}
    design -->|yes| derive[Derive the answers]
    design -->|no| ask[Ask the user for the source]
    ask -->|describe now| questions[Ask the questions]
    ask -->|add documents first| stop[Stop]
    derive --> questions
    questions --> summary[Show all writes]
    summary --> confirm{User confirms?}
    confirm -->|change| questions
    confirm -->|yes| write[Write the bindings]
    write --> tool[python -m tools.project init]
    tool --> commit[Commit: Project initialized]
```

| ID | Rule |
|---|---|
| D2900 | The project has its bindings when `python -m tools.project check` passes. |
| D2901 | `project-init` never decides an answer. A question without answer stops it. |
| D2902 | The user confirmation of the summary is the approval for the protected paths that the skill writes. |
| D2903 | `project-update` runs only when no plan is active. It writes the changed bindings only. |

The example binds a Python project.

```toml
product_terms = ["Route Planner", "waypoint"]
start_version = "0.0.0"
main_branch = "main"
ci = "none"
test_suite = "pytest"
test_command = "pytest -n auto {names}"
test_report = "build/junit.xml"
test_run_limit = 1800
test_support = "tests/support"
dependency_source = ".venv/Lib/site-packages"

[[language]]
name = "python"
extensions = [".py"]
source = ["src"]
tests = ["tests"]
format = "ruff format --check {files}"
lint = "ruff check {files}"
comments = "python scripts/comment_check.py {files}"

[commands]
build = "python -m build"

[start_script]
windows = "bat"
linux = "sh"

[licenses]
commercial = true
paid = false
held = ["Example Font Pro"]
free = ["MIT", "Apache-2.0"]
dependencies = "python scripts/dependency_licenses.py"
```

| ID | Rule |
|---|---|
| D2904 | `ci` is `none` or the path of the pipeline file. The pipeline runs `python -m tools.check` and `python -m tools.test`. |
| D2905 | `test_command` runs the test `{name}`, or each test of `{names}` in one call of the runner. It must fail when no test has a given name. The test commands run the tests in parallel, with the option of the runner. |
| D2906 | `test_report` is optional. It names the report file in the JUnit XML format that the runner writes. `python -m tools.test` reads the counts and the failed tests from it. A run that must fail needs it. |
| D2907 | A bound folder exists: each source folder, each test folder and the test support folder. A project without a file of its languages is exempt. |
| D2908 | `[commands]` holds each command of a `COMMAND <name> passes` check. A project with a second test runner binds it as an entry of `[commands]`. |
| D2909 | `format` and `lint` are check commands. They do not change a file. |
| D2910 | `{files}` is optional. The tool replaces it with one changed file, or with the source and test folders. |
| D2911 | Each command is a command line of the stack of the project, for example `cargo test {name}` or `cargo clippy`. |
| D2912 | `dependency_source` is optional. It names the folder with the source of the installed dependencies. `python -m tools.project source` prints its absolute path in the main repository, also in a worktree. |
| D2913 | `comments` is optional. It is a check command that refuses each comment without a tool reason. `python -m tools.check` runs it with `format` and `lint`. |
| D2914 | `test_run_limit` is the time limit of one test run in seconds. The per-test timeout lives in the configuration of the test runner. |
| D2915 | `test_binaries` is optional. It lists the globs of the test executables. Before a run, `python -m tools.test` ends each process of such an executable that still runs. |
| D2916 | `[start_script]` is optional. It maps each platform to the file type of a start script of a manual check package, for example `windows = "bat"`. A start script passes its arguments to the program. |
| D2917 | `toolchain_folders` is optional. It lists the folders of the tool chain outside the repository that a command of an agent names. |
| D2919 | `[licenses]` holds the license answers of the user. `commercial` says whether the product is commercial. `paid` says whether paid libraries and assets are allowed. `held` lists what the project already holds a license for. |
| D2920 | `free` lists the free licenses. Such a license allows commercial and open source use and asks for no attribution in the product. |
| D2921 | `dependencies` is optional. It is a command that prints one line per dependency of the manifests: the name, a tab and the license expression. |

## Tool reference
Each tool runs as `python -m tools.<name>`. A tool without arguments prints its usage when it needs arguments.

| Tool | Commands | Purpose |
|---|---|---|
| `setup` | | Bootstrap. |
| `provider` | none, `check` | Generates the provider files. Checks that they are current. |
| `check` | none, `<files>`, `--format-only`, `--staged` | Runs lint, format, encoding, docs lint, memory lint, provider, wiki and progress checks. `--format-only` skips the lint. `--staged`, the commit hook, lints the staged documents only and refuses a tool file in a commit that no tool makes. |
| `pre_write`, `post_write` | | Hook entries. Block a protected write. Run the generator and the checks for a changed file. Run the hook of the main repository or of the worktree that holds the path of a write of an agent. Refuse a write of an agent outside its first root. |
| `timing` | `start`, `end`, `report [<log>]` | Hook entries that log the duration of each tool call of a session in `docs/milestones/tmp/logs/` of the main repository. The report prints the time per tool and the slowest calls. |
| `agent_guard` | `<bash or edit>` | Hook entry. Reads the agent from `agent_type` of the hook input. Checks a call against `bash_allow` and `edit_allow` of the root of its path. A leading `cd <root> &&` names that root, and so does the `git -C <root>` of a git command. Refuses a command of an agent that names a path outside the repository. It reads an absolute path in quotes as one token, also with a space. Refuses a command with `--answer` and a second command, also of the main session. |
| `project` | `init`, `update`, `check`, `source` | Validates the bindings and commits them. Prints the absolute path of the dependency sources. |
| `progress` | none, `check`, `status`, `add-feature`, `drop-feature <feature> --answer`, `set-goal`, `out-of-scope <add or remove>`, `add-bug`, `fix-bug`, `drop-bug <bug> --answer` | Writes `PROGRESS.md` and the feature tables. Prints the next step in a worktree, and the active plans and the drafts in the main repository. Writes features, bugs, the goal and the out of scope list in the main repository. |
| `milestone_create` | `draft <name>`, `commit <id>`, `open <id>`, `remove <id>` | Writes a draft file. Validates and commits a draft. Opens a draft with its branch. Removes a draft. |
| `plan_create` | `start <feature, fix or refactor> <name>`, `reviewed`, `commit`, `worktree <plan>` | Creates the draft folder. Records a document review. Validates and commits the plan, then creates its branch and its worktree. |
| `review_yield` | none | Counts the reviews of the archived plans per kind and round, their problems, the plans per topic and the bugs fixed later. |
| `step_close` | `start`, `review`, `close [--answer] [--by agent]`, `revert`, `block`, `add-fix`, `set-text <step> "<text>" --answer`, `unblock <step> --answer`, `set-dependencies <step> "<ids>" [--answer]`, `add-problem <step or plan> <round> <severity> <rule> "<topic>" "<location>" "<trigger>" "<class>" "<fix>"`, `answer-problem <problem> "<answer>"`, `check-problem <problem> "<check>"` | Makes each state change of a step, in the worktree of the plan. Writes the new text and the dependencies of a step. Adds, answers and checks the problems of the plan, also of the plan in close in the main repository. |
| `plan_close` | In the worktree: `sync`, `reviewed`, `review-passed`, `block`, `unblock <accept, drop <id> or replan <id>> --answer`. In the main repository: `merge <plan>`, `tuning`, `check`, `verify-bug`, none | Makes each state change of the plan close. `reviewed` runs each `COMMAND` check of the plan verification in round 1 and prints each failure. |
| `milestone_close` | none, `reviewed`, `check`, `migrate <id>` | Closes, merges or migrates a milestone. `reviewed` records the milestone review. `migrate` opens the draft with the given id. |
| `approve` | `<plan> <step or close>` | Writes an approval record of the user. |
| `test` | none, `<name or check line> [...]`, `--contains`, `--fails`, `--mutation <patch>`, `--step <step>` | Runs the suite, the named tests in one call of the runner, or the command of a check line. Names each test that ran and each failed test, and runs a failed test three more times alone. Writes the full output to the evidence or to a log. The log lies in `tmp/logs/` of the plan folder in a plan worktree, else in `docs/milestones/tmp/logs/`. Ends a run after `test_run_limit` with its process tree, and ends leftover test processes before a run. |
| `dependency` | `add "<trigger>" "<action>" "<validation>" "<source>"`, `change <id> "<trigger>" "<action>" "<validation>" "<source>"`, `remove <id> "<reason>"` | Adds a row with the next id to `docs/DEPENDENCIES.md`, changes the cells of a row and removes one in the close of a refactor plan. Commits the file. |
| `memory_index`, `memory_lint` | none, `show`, `--strict` | Writes and checks the memory index and the entries. |
| `licenses` | none | Checks the license of each dependency of the manifests against the free list. Lists each dependency outside the list without a row in `docs/LICENSES.md`. |
| `ideas` | `add "<idea>" <user or agent>`, `edit <id> "<idea>"`, `remove <id> [<id> ...] "<reason>"` | Adds an idea with the next id, changes the text of an idea and removes ideas from `docs/IDEAS.md`. Commits the file. |
| `research` | `start <name>`, `check [<id> ...]`, `commit <id>`, `spike <id>`, `spike-end <id>` | Starts a research file with the next id. Checks the frame of the research files. Commits one file. Creates and deletes the branch and the worktree of a spike. |
| `check_encoding`, `fix_encoding` | none, `<files>` | Checks and repairs the encoding. |
| `docs_lint` | none, `<files>` | Runs Vale and the project content check. |
| `build_wiki_bundle` | none, `check` | Writes and checks the offline wiki bundle. |

## User involvement
| ID | Rule |
|---|---|
| D3000 | Ask the user for: an answer of `project-init` or `project-update`, and the MCP server list. Ask the user for: an acceptance that the design does not give, a manual check, and a decision that the design does not give. Ask the user for: an approval of a protected path, a blocked step, a blocked plan, and the tuning changes. Ask the user for: an extension decision, a dropped feature or bug, the bug list of a bugfix phase, and each new dependency. Ask the user for: a premature close with the new goal, a major version, and a conflict with `DEPLOYMENT.md`. |
| D3001 | Everything else runs without the user. |
