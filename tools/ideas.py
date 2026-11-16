"""Keeps the ideas file of later milestones: adds an idea with the next id and removes planned or dropped ideas."""

import re
from datetime import datetime

from tools._lib import PLANS, commit, fail, git, main, read, read_table, require_main, words, write, write_table

IDEAS = PLANS / "IDEAS.md"
IDEAS_HEADER = ["ID", "Time", "Source", "Idea"]
IDEA_ID = re.compile(r"IDEA(\d{3})")
TEMPLATE = """# Ideas

Ideas for features of later milestones that no milestone plans yet. `milestone-propose` reads them.
A milestone that plans an idea removes its row.

| ID | Time | Source | Idea |
|---|---|---|---|
"""


def rows():
    text = read(IDEAS) if IDEAS.exists() else TEMPLATE
    return text, read_table(text, None, IDEAS_HEADER, IDEAS)


def next_id(text):
    # an id is never used twice, so the git history of the file counts too
    history = git("log", "-p", "--all", "--", str(IDEAS), check=False)
    numbers = [int(number) for number in IDEA_ID.findall(text + "\n" + history)]
    return f"IDEA{max(numbers, default=0) + 1:03d}"


def add(idea, source):
    if source not in ("user", "agent"):
        fail("the source must be 'user' or 'agent'")
    if not 1 <= words(idea) <= 25:
        fail("the idea must have 1 to 25 words")
    text, table = rows()
    row = {
        "ID": next_id(text),
        "Time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "Source": source,
        "Idea": idea,
    }
    write(IDEAS, write_table(text, None, IDEAS_HEADER, table + [row], IDEAS))
    commit(f"Idea added: {row['ID']}", [IDEAS])
    print(f"added {row['ID']}")


def remove(ids, reason):
    text, table = rows()
    known = {row["ID"] for row in table}
    missing = [item for item in ids if item not in known]
    if missing:
        fail(f"no idea {', '.join(missing)}")
    kept = [row for row in table if row["ID"] not in ids]
    write(IDEAS, write_table(text, None, IDEAS_HEADER, kept, IDEAS))
    commit(f"Ideas removed: {' '.join(ids)} {reason}", [IDEAS])
    print(f"removed {' '.join(ids)}")


def run(args):
    require_main()
    if len(args) == 3 and args[0] == "add":
        add(args[1], args[2])
    elif len(args) >= 3 and args[0] == "remove":
        remove(args[1:-1], args[-1])
    else:
        fail('usage: python -m tools.ideas add "<idea>" <user|agent> | remove <id> [<id> ...] "<reason>"')


if __name__ == "__main__":
    main(run)
