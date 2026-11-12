import re

from tools._lib import DOCS, fail, main, read, read_meta, rel, write

INDEX = DOCS / "MEMORY.md"
ENTRIES = DOCS / "memories"
ENTRY_FILE = re.compile(r"^MEM-[a-z0-9]+(?:-[a-z0-9]+)*\.md$")


def load(path):
    name = rel(path)
    text = read(path)
    meta = read_meta(text, name)
    body = text[text.find("\n---\n", 3) + 5 :].strip("\n").split("\n")
    if not body[0].startswith("# ") or not body[0][2:].strip():
        fail(f"{name}: the first line after the frontmatter must be the title '# <summary>'")
    return {"name": path.stem, "rel": name, "meta": meta, "title": body[0][2:].strip(), "body": body[1:]}


def entries():
    return [load(path) for path in sorted(ENTRIES.glob("*.md"))]


def index_text():
    return "".join(f"- [{entry['meta'].get('type', '')}] {entry['name']}: {entry['title']}\n" for entry in entries())


def run(args):
    if args == ["show"]:
        print(read(INDEX) if INDEX.exists() else "", end="")
    elif not args:
        write(INDEX, index_text())
        print("memory index written")
    else:
        fail("usage: python -m tools.memory_index [show]")


if __name__ == "__main__":
    main(run)
