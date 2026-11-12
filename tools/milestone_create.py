from tools import progress, project
from tools._lib import (
    MILESTONE_FILE,
    MILESTONES,
    commit,
    fail,
    git,
    main,
    milestone_branch,
    milestones,
    next_id,
    open_milestone,
    parse_check,
    rel,
    require_branch,
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
        if row["Type"] not in ("new", "update"):
            errors.append(f"{name}: {row['ID']}: Type must be new or update")
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


def start(name, migrate):
    if project.errors():
        fail("not initialized, run project-init")
    if not MILESTONE_FILE.match(f"M000-{name}.md"):
        fail("the name must have lower case letters, digits and hyphens")
    if drafts():
        fail(f"a draft milestone exists: {drafts()[0]['rel']}")
    current = open_milestone()
    milestone_id = next_id("M", [m["id"] for m in milestones()], 3)
    if migrate:
        if not current:
            fail("no milestone is open, a premature close is not possible")
    else:
        if current:
            fail(f"milestone {current['id']} is open. One milestone is open at a time")
        require_branch()
        git("checkout", "-b", f"milestone/{milestone_id}-{name}")
    path = MILESTONES / f"{milestone_id}-{name}.md"
    title = name.replace("-", " ").capitalize()
    write(path, TEMPLATE.format(id=milestone_id, name=name, date=today(), title=title))
    print(f"draft: {rel(path)}")


def create():
    found = drafts()
    if len(found) != 1:
        fail("one draft milestone file is necessary, run python -m tools.milestone_create start <name>")
    milestone = found[0]
    if open_milestone():
        fail(f"milestone {open_milestone()['id']} is open. One milestone is open at a time")
    require_branch(milestone_branch(milestone))
    errors = validate(milestone, milestones())
    if errors:
        fail("\n".join(errors))
    milestone["meta"]["status"] = "open"
    save_milestone(milestone)
    progress.regenerate()
    commit(f"Milestone created: {milestone['id']}")
    print(f"Milestone created: {milestone['id']}")


def run(args):
    if args[:1] == ["start"] and len([a for a in args[1:] if a != "--migrate"]) == 1:
        start(next(a for a in args[1:] if a != "--migrate"), "--migrate" in args)
    elif args == ["commit"]:
        create()
    else:
        fail("usage: python -m tools.milestone_create <start <name> [--migrate] | commit>")


if __name__ == "__main__":
    main(run)
