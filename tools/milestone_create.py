from tools import progress, project
from tools._lib import (
    FEATURE_TYPES,
    MILESTONE_FILE,
    MILESTONES,
    commit,
    fail,
    git,
    git_ok,
    load_project,
    main,
    milestone_branch,
    milestones,
    next_id,
    open_milestone,
    parse_check,
    rel,
    require_branch,
    require_main,
    save_milestone,
    today,
    words,
    write,
)

TEMPLATE = """---
id: {id}
name: {name}
status: draft
created: {date}
closed:
---
# {id} {title}

## Goal

## Features
| ID | Feature | Type | Acceptance | Plans | State |
|---|---|---|---|---|---|

## Bugs
| ID | Bug | Feature | Source | Acceptance |
|---|---|---|---|---|

## Out of scope
"""


def section(text, heading):
    lines = text.split("\n")
    if f"## {heading}" not in lines:
        return None
    body = []
    for line in lines[lines.index(f"## {heading}") + 1 :]:
        if line.startswith("## "):
            break
        body.append(line)
    return "\n".join(body).strip()


def validate(milestone, all_milestones):
    errors = []
    name = milestone["rel"]
    if not section(milestone["text"], "Goal"):
        errors.append(f"{name}: the Goal section is empty")
    if section(milestone["text"], "Out of scope") is None:
        errors.append(f"{name}: the section '## Out of scope' is missing")
    if not milestone["features"] and not milestone["bugs"]:
        errors.append(f"{name}: a milestone needs one feature or one bug")
    for number, row in enumerate(milestone["features"], 1):
        if row["ID"] != f"F{number:02d}":
            errors.append(f"{name}: feature row {number} must have the id F{number:02d}")
        if not 1 <= words(row["Feature"]) <= 12:
            errors.append(f"{name}: {row['ID']}: the feature text must have 1 to 12 words")
        if row["Type"] not in FEATURE_TYPES:
            errors.append(f"{name}: {row['ID']}: Type must be new, update or refactor")
        if not parse_check(row["Acceptance"]):
            errors.append(f"{name}: {row['ID']}: the acceptance must be 'TEST <name> passes', 'COMMAND <name> passes' or 'MANUAL <name>'")
        if row["Plans"] or row["State"] != "open":
            errors.append(f"{name}: {row['ID']}: Plans must be empty and State must be open")
    for number, row in enumerate(milestone["bugs"], 1):
        if row["ID"] != f"B{number:02d}":
            errors.append(f"{name}: bug row {number} must have the id B{number:02d}")
        errors += [f"{name}: {error}" for error in progress.bug_errors(milestone, row, all_milestones)]
    return errors


def drafts():
    return [m for m in milestones() if m["meta"]["status"] == "draft" and not m["archived"]]


def find_draft(milestone_id):
    for milestone in drafts():
        if milestone["id"] == milestone_id:
            return milestone
    fail(f"{milestone_id} is no draft milestone")


def draft(name):
    if project.errors():
        fail("not initialized, run project-init")
    if not MILESTONE_FILE.match(f"M000-{name}.md"):
        fail("the name must have lower case letters, digits and hyphens")
    require_branch()
    milestone_id = next_id("M", [m["id"] for m in milestones()], 3)
    path = MILESTONES / f"{milestone_id}-{name}.md"
    title = name.replace("-", " ").capitalize()
    write(path, TEMPLATE.format(id=milestone_id, name=name, date=today(), title=title))
    print(f"draft: {rel(path)}")


def save(milestone_id):
    """Validates a draft and commits it. A draft stays editable, and each of its commits goes through this command."""
    milestone = find_draft(milestone_id)
    require_branch()
    errors = validate(milestone, milestones())
    if errors:
        fail("\n".join(errors))
    git("add", "--", milestone["rel"])
    progress.regenerate()
    if commit(f"Milestone drafted: {milestone_id}", [milestone["path"], progress.PROGRESS]):
        print(f"Milestone drafted: {milestone_id}")
    else:
        print(f"no change in the draft {milestone_id}")


def open_draft(milestone_id):
    """Opens a committed draft: creates the milestone branch from the main branch and sets the status `open`."""
    milestone = find_draft(milestone_id)
    current = open_milestone()
    if current:
        fail(f"milestone {current['id']} is open. One milestone is open at a time")
    require_branch(load_project()["main_branch"])
    if not git_ok("cat-file", "-e", f"HEAD:{milestone['rel']}") or git("status", "--porcelain", "--", milestone["rel"]):
        fail(f"the draft has changes without a commit, run python -m tools.milestone_create commit {milestone_id}")
    errors = validate(milestone, milestones())
    if errors:
        fail("\n".join(errors))
    git("checkout", "-b", milestone_branch(milestone))
    milestone["meta"]["status"] = "open"
    save_milestone(milestone)
    progress.regenerate()
    commit(f"Milestone created: {milestone_id}")
    print(f"Milestone created: {milestone_id}")


def remove(milestone_id):
    milestone = find_draft(milestone_id)
    require_branch()
    tracked = git_ok("cat-file", "-e", f"HEAD:{milestone['rel']}")
    if not tracked:
        git("rm", "-q", "--cached", "--ignore-unmatch", "--", milestone["rel"])
    milestone["path"].unlink()
    progress.regenerate()
    commit(f"Milestone draft removed: {milestone_id}", [progress.PROGRESS] + ([milestone["path"]] if tracked else []))
    print(f"Milestone draft removed: {milestone_id}")


def run(args):
    require_main()
    if args[:1] == ["draft"] and len(args) == 2:
        draft(args[1])
    elif args[:1] == ["commit"] and len(args) == 2:
        save(args[1])
    elif args[:1] == ["open"] and len(args) == 2:
        open_draft(args[1])
    elif args[:1] == ["remove"] and len(args) == 2:
        remove(args[1])
    else:
        fail("usage: python -m tools.milestone_create <draft <name> | commit <id> | open <id> | remove <id>>")


if __name__ == "__main__":
    main(run)
