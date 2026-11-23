"""Keeps the research files: starts a file with the next id, checks its common frame and commits it. A spike of a
research gets its own branch and worktree, which the end of the spike deletes."""

import re

from tools._lib import DOCS, commit, fail, git, git_ok, main, main_root, read, rel, run as shell, today, write

RESEARCH = DOCS / "research"
RESEARCH_FILE = re.compile(r"^(R\d{3})-([a-z0-9]+(?:-[a-z0-9]+)*)\.md$")
TITLE = re.compile(r"^# (R\d{3}):? \S")
NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SOURCES = "## Sources"


def files():
    found = sorted(path for path in RESEARCH.glob("R*.md") if RESEARCH_FILE.match(path.name)) if RESEARCH.is_dir() else []
    return {RESEARCH_FILE.match(path.name).group(1): path for path in found}


def next_id():
    # an id is never used twice, so the git history of each branch counts too
    history = git("log", "--all", "--name-only", "--format=", "--", rel(RESEARCH), check=False)
    numbers = [int(number) for number in re.findall(r"research/R(\d{3})-", history)]
    numbers += [int(item[1:]) for item in files()]
    return f"R{max(numbers, default=0) + 1:03d}"


def start(name):
    if not NAME.match(name):
        fail("the name must have lower case letters, digits and hyphens")
    item = next_id()
    path = RESEARCH / f"{item}-{name}.md"
    title = name.replace("-", " ")
    write(path, f"# {item}: {title[:1].upper() + title[1:]}\n\nDate: {today()}. Scope:\n\n{SOURCES}\n")
    print(f"research file: {rel(path)}")


def frame_errors(path):
    """The errors of the common frame of a research file: the title with the id, the line with date and scope, and
    the section of the sources. Each part between them has the shape that fits the subject."""
    name = rel(path)
    lines = [line.rstrip() for line in read(path).split("\n")]
    filled = [line for line in lines if line]
    errors = []
    title = TITLE.match(filled[0]) if filled else None
    if not title or title.group(1) != RESEARCH_FILE.match(path.name).group(1):
        errors.append(f"{name}: the first line must be the title with the id of the file")
    scope = filled[1] if len(filled) > 1 else ""
    if not scope.startswith("Date") or not re.search(r"\d{4}-\d{2}-\d{2}", scope) or len(scope.split()) < 5:
        errors.append(f"{name}: the line under the title must hold the date and the scope")
    if SOURCES not in lines:
        errors.append(f"{name}: the section {SOURCES} is missing")
    else:
        body = lines[lines.index(SOURCES) + 1 :]
        end = next((index for index, line in enumerate(body) if line.startswith("## ")), len(body))
        if not any(body[:end]):
            errors.append(f"{name}: the section {SOURCES} is empty")
    return errors


def find(item):
    known = files()
    if item not in known:
        fail(f"no research file {item}")
    return known[item]


def check(items):
    paths = [find(item) for item in items] if items else list(files().values())
    errors = [error for path in paths for error in frame_errors(path)]
    if errors:
        fail("\n".join(errors))
    print(f"research ok: {len(paths)} files")


def save(item):
    path = find(item)
    errors = frame_errors(path)
    if errors:
        fail("\n".join(errors))
    commit(f"Research added: {item}", [path])
    print(f"committed {rel(path)}")


def spike_place(item):
    if not re.fullmatch(r"R\d{3}", item):
        fail(f"{item} is no research id")
    return f"spike/{item}", main_root() / ".worktrees" / f"spike-{item}"


def spike(item):
    """Creates the branch and the worktree of a spike from HEAD. No commit of the spike reaches the milestone branch."""
    find(item)
    name, path = spike_place(item)
    if not git_ok("rev-parse", "--verify", "--quiet", f"refs/heads/{name}"):
        git("branch", name, "HEAD")
    if not path.exists():
        git("worktree", "add", str(path), name)
    print(f"spike worktree: {path}")


def spike_end(item):
    """Deletes the worktree and the branch of a spike."""
    name, path = spike_place(item)
    if path.exists():
        code, output = shell(["git", "worktree", "remove", "--force", str(path)])
        if code != 0:
            fail(f"the spike worktree {path} is in use, close the programs there:\n{output}")
    shell(["git", "worktree", "prune"])
    if git_ok("rev-parse", "--verify", "--quiet", f"refs/heads/{name}"):
        git("branch", "-D", name)
    print(f"spike {item} removed")


def run(args):
    if len(args) == 2 and args[0] == "start":
        start(args[1])
    elif len(args) == 2 and args[0] == "spike":
        spike(args[1])
    elif len(args) == 2 and args[0] == "spike-end":
        spike_end(args[1])
    elif args[:1] == ["check"]:
        check(args[1:])
    elif len(args) == 2 and args[0] == "commit":
        save(args[1])
    else:
        fail("usage: python -m tools.research start <name> | check [<id> ...] | commit <id> | spike <id> | spike-end <id>")


if __name__ == "__main__":
    main(run)
