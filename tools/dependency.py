"""Keeps the dependencies file: adds a structural dependency with the next id and removes one after a refactor."""

import re

from tools._lib import (
    DEPENDENCY_HEADER,
    DOCS,
    active_plans,
    commit,
    fail,
    main,
    merged,
    read,
    read_table,
    require_branch,
    require_main,
    today,
    words,
    write,
    write_table,
)

FILE = DOCS / "DEPENDENCIES.md"
NAME = "docs/DEPENDENCIES.md"
MAX_ROWS = 9
RECORD = re.compile(r"^- (added|removed) (DEP-\d{2}) (.+) (\d{4}-\d{2}-\d{2})$")
TEMPLATE = """# Dependencies

The structural dependencies of the project. A step names each row whose trigger it meets.

## Dependencies
| ID | Trigger | Action | Validation |
|---|---|---|---|

## Records
"""


def load():
    text = read(FILE) if FILE.exists() else TEMPLATE
    lines = text.split("\n")
    if "## Records" not in lines:
        fail(f"{NAME}: section '## Records' is missing")
    records = [line for line in lines[lines.index("## Records") + 1 :] if line.strip()]
    for line in records:
        if not RECORD.match(line):
            fail(f"{NAME}: not a record line of the form - <added|removed> <id> <source or reason> <date>: {line}")
    return text, read_table(text, "Dependencies", DEPENDENCY_HEADER, NAME), records


def save(text, rows, record):
    text = write_table(text, "Dependencies", DEPENDENCY_HEADER, rows, NAME)
    write(FILE, text.rstrip("\n") + "\n" + record + "\n")


def cell(text, name, limit):
    if not 1 <= words(text) <= limit:
        fail(f"the {name} must have 1 to {limit} words")
    if "|" in text or "\n" in text:
        fail(f"the {name} must be one line without '|'")
    return text.strip()


def add(trigger, action, validation, source):
    text, rows, records = load()
    if len(rows) >= MAX_ROWS:
        fail(f"the file holds the maximum of {MAX_ROWS} dependencies. Remove one after a refactor first")
    # an id is never used again, so the records of removed rows count too
    used = [int(row["ID"][4:]) for row in rows] + [int(RECORD.match(line).group(2)[4:]) for line in records]
    row = {
        "ID": f"DEP-{max(used, default=0) + 1:02d}",
        "Trigger": cell(trigger, "trigger", 25),
        "Action": cell(action, "action", 25),
        "Validation": cell(validation, "validation", 25),
    }
    source = cell(source, "source", 12)
    save(text, rows + [row], f"- added {row['ID']} {source} {today()}")
    commit(f"Dependency added: {row['ID']}", [FILE])
    print(f"added {row['ID']}")


def remove(dependency_id, reason):
    text, rows, _ = load()
    kept = [row for row in rows if row["ID"] != dependency_id]
    if len(kept) == len(rows):
        fail(f"{dependency_id} is not in {NAME}")
    closing = [plan for plan in active_plans() if merged(plan["id"]) and plan["meta"]["type"] == "refactor"]
    if not closing:
        fail("a dependency leaves the file only in the close of a refactor plan, after its merge")
    reason = cell(reason, "reason", 12)
    save(text, kept, f"- removed {dependency_id} {closing[0]['id']} {reason} {today()}")
    commit(f"Dependency removed: {dependency_id} {closing[0]['id']}", [FILE])
    print(f"removed {dependency_id}")


def run(args):
    require_main()
    require_branch()
    if len(args) == 5 and args[0] == "add":
        add(*args[1:])
    elif len(args) == 3 and args[0] == "remove":
        remove(args[1], args[2])
    else:
        fail(
            'usage: python -m tools.dependency add "<trigger>" "<action>" "<validation>" "<source>"'
            ' | remove <id> "<reason>"'
        )


if __name__ == "__main__":
    main(run)
