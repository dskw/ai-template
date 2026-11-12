import re

import yaml

from tools import memory_index
from tools._lib import DATE, ROOT, Fail, fail, main, plans, read, words

BLOCKLIST = ROOT / "tools" / "vale" / "styles" / "Project" / "Blocklist.yml"
TYPES = ("user", "feedback", "project", "reference")


def stale_date():
    closed = sorted((plan["meta"]["closed"] for plan in plans() if plan["archived"]), reverse=True)
    return closed[4] if len(closed) >= 5 else None


def lint():
    errors, stale = [], []
    for path in memory_index.ENTRIES.glob("*"):
        if path.name != ".gitkeep" and not memory_index.ENTRY_FILE.match(path.name):
            errors.append(f"docs/memories/{path.name}: the file name must have the form MEM-[NAME].md")
    if errors:
        return errors, stale
    try:
        entries = memory_index.entries()
        limit = stale_date()
    except Fail as error:
        return [str(error)], stale
    blocked = [token.lower() for token in yaml.safe_load(read(BLOCKLIST))["tokens"]]
    for entry in entries:
        name, meta = entry["rel"], entry["meta"]
        if meta.get("type") not in TYPES:
            errors.append(f"{name}: type must be one of {', '.join(TYPES)}")
        if meta.get("source") != "user" and not re.fullmatch(r"M\d{3}-P\d{3}", meta.get("source", "")):
            errors.append(f"{name}: source must be a plan id or 'user'")
        if not DATE.match(meta.get("modified", "")):
            errors.append(f"{name}: modified must be a date")
        elif limit and meta["modified"] < limit:
            stale.append(f"{name}: stale, modified {meta['modified']} is before {limit}")
        if words(entry["title"]) > 12:
            errors.append(f"{name}: the title is the index summary, max 12 words")
        if len([line for line in entry["body"] if line.strip()]) > 15:
            errors.append(f"{name}: max 15 body lines")
        text = read(ROOT / name)
        if not text.isascii():
            errors.append(f"{name}: ASCII only")
        errors += [f"{name}: '{token}' is on the blocklist" for token in blocked if token in text.lower()]
    if len(entries) > 100:
        errors.append("docs/MEMORY.md: max 100 lines, run memory-consolidate")
    index = read(memory_index.INDEX) if memory_index.INDEX.exists() else ""
    if index != memory_index.index_text():
        errors.append("docs/MEMORY.md is stale, run python -m tools.memory_index")
    return errors, stale


def errors(strict=False):
    found, stale = lint()
    return found + stale if strict else found


def run(args):
    if args not in ([], ["--strict"]):
        fail("usage: python -m tools.memory_lint [--strict]")
    found, stale = lint()
    for line in stale:
        print(f"warning: {line}")
    if found or (stale and args):
        fail("\n".join(found + (stale if args else [])))
    print("memory ok")


if __name__ == "__main__":
    main(run)
