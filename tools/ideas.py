"""Keeps the ideas file of later milestones: adds an idea with the next id, changes the text of an idea and removes
planned or dropped ideas."""

import re
from datetime import datetime

from tools._lib import DOCS, commit, fail, git, main, read, read_table, require_main, words, write, write_table

IDEAS = DOCS / "IDEAS.md"
IDEAS_HEADER = ["ID", "Time", "Source", "Idea"]
IDEA_WORDS = 100
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
    # an id is never used twice, so the git history of the file counts too, also from before a move of the file
    history = git("log", "-p", "--all", "--follow", "--", str(IDEAS), check=False)
    numbers = [int(number) for number in IDEA_ID.findall(text + "\n" + history)]
    return f"IDEA{max(numbers, default=0) + 1:03d}"


def check_text(idea):
    if not 1 <= words(idea) <= IDEA_WORDS:
        fail(f"the idea must have 1 to {IDEA_WORDS} words")


def add(idea, source):
    if source not in ("user", "agent"):
        fail("the source must be 'user' or 'agent'")
    check_text(idea)
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


def edit(idea_id, idea):
    """Writes the new text of an idea. The id, the time and the source stay, so each reference to the id holds."""
    check_text(idea)
    text, table = rows()
    found = [row for row in table if row["ID"] == idea_id]
    if not found:
        fail(f"no idea {idea_id}")
    found[0]["Idea"] = idea
    write(IDEAS, write_table(text, None, IDEAS_HEADER, table, IDEAS))
    commit(f"Idea changed: {idea_id}", [IDEAS])
    print(f"changed {idea_id}")


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
    elif len(args) == 3 and args[0] == "edit":
        edit(args[1], args[2])
    elif len(args) >= 3 and args[0] == "remove":
        remove(args[1:-1], args[-1])
    else:
        fail('usage: python -m tools.ideas add "<idea>" <user|agent> | edit <id> "<idea>" | remove <id> [<id> ...] "<reason>"')


if __name__ == "__main__":
    main(run)
