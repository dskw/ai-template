import datetime
import json
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
MILESTONES = DOCS / "milestones"
PLANS = DOCS / "plans"
PROJECT_FILE = ROOT / "tools" / "project.toml"
CHANGELOG = ROOT / "CHANGELOG.md"
# the logs of the tools lie in this folder of the temporary folder of a plan or of the milestones, which git ignores
LOG_FOLDER = "logs"

MILESTONE_FILE = re.compile(r"^(M\d{3})-([a-z0-9]+(?:-[a-z0-9]+)*)\.md$")
PLAN_DIR = re.compile(r"^(M\d{3})-(P\d{3})-([a-z0-9]+(?:-[a-z0-9]+)*)$")
FEATURE_ID = re.compile(r"^F\d{2}$")
BUG_ID = re.compile(r"^B\d{2}$")
STEP_ID = re.compile(r"^S\d{2}(-fix)?$")
PROBLEM_ID = re.compile(r"^N\d{2}$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
CHECK = re.compile(r"^(?:(TEST|COMMAND) (\S+) passes|(MANUAL) (\S+))$")

FEATURE_HEADER = ["ID", "Feature", "Type", "Acceptance", "Plans", "State"]
BUG_HEADER = ["ID", "Bug", "Feature", "Source", "Acceptance", "Cause"]
# a milestone file from before the Cause column keeps its table
OLD_BUG_HEADER = ["ID", "Bug", "Feature", "Source", "Acceptance"]
STEP_HEADER = ["Step", "Feature", "Text", "Verification", "Dependencies"]
# a plan from before the Dependencies column keeps its table
OLD_STEP_HEADER = ["Step", "Feature", "Text", "Verification"]
FIX_HEADER = ["Step", "Feature", "Problem", "Text", "Verification"]
PROGRESS_HEADER = ["Step", "Feature", "State", "Evidence", "Round"]
PROBLEM_HEADER = ["ID", "Step", "Round", "Severity", "Rule", "Topic", "Location", "Trigger", "Class", "Fix", "Answer", "Check"]
# a problems file from before the Topic column keeps its table
OLD_PROBLEM_HEADER = ["ID", "Step", "Round", "Severity", "Rule", "Location", "Trigger", "Class", "Fix", "Answer", "Check"]
EXTENSION_HEADER = ["ID", "Extension", "Decision", "Detail"]
MILESTONE_HEADER = ["Milestone", "Features", "Done", "Bugs", "Status"]
DEPENDENCY_HEADER = ["ID", "Trigger", "Action", "Validation"]
DEPENDENCY_ID = re.compile(r"^DEP-\d{2}$")
PLAN_TYPES = ("feature", "fix", "refactor")
# a step with this verification is a research step: it adds a research file and changes no source or test file
RESEARCH_CHECK = "COMMAND research_check passes"
# the commands that each project has without a row in its bindings
BUILTIN_COMMANDS = {"research_check": "python -m tools.research check"}
FEATURE_TYPES = ("new", "update", "refactor")

# the files that a generator writes; an agent edits the source
GENERATED = [
    ".claude/**",
    ".codex/**",
    ".kilo/**",
    ".agents/.generated/**",
    "CLAUDE.md",
    ".mcp.json",
    "kilo.jsonc",
    "docs/MEMORY.md",
    "docs/wiki/assets/pages.js",
    "docs/wiki/index.html",
]
# the files that only a tool writes and commits
TOOL_OWNED = [
    "docs/milestones/PROGRESS.md",
    "docs/milestones/archive/**",
    "docs/plans/archive/**",
    "docs/plans/*/progress.md",
    "docs/plans/*/problems.md",
    "docs/plans/*/evidence/**",
    "docs/IDEAS.md",
    "docs/DEPENDENCIES.md",
]
# the tool that writes each file of a tool, for the message of a refused work tree
WRITERS = [
    ("docs/plans/*/problems.md", "the problem commands of python -m tools.step_close, or a state tool"),
    ("docs/plans/*/plan.md", "python -m tools.step_close or python -m tools.plan_close"),
    ("docs/plans/*/progress.md", "python -m tools.step_close"),
    ("docs/plans/*/evidence/**", "python -m tools.test"),
    ("docs/IDEAS.md", "python -m tools.ideas"),
    ("docs/DEPENDENCIES.md", "python -m tools.dependency"),
    ("docs/milestones/**", "python -m tools.progress or a milestone tool"),
    ("docs/MEMORY.md", "python -m tools.memory_index"),
    ("docs/wiki/index.html", "python -m tools.build_wiki_bundle"),
    ("docs/wiki/assets/**", "python -m tools.build_wiki_bundle"),
]
# a milestone file and a plan file are editable while their status is draft, then only a tool writes them
DRAFT_ONLY = ["docs/milestones/M*.md", "docs/plans/*/plan.md"]
# the files of the whole milestone: a session writes them in the main repository, never in the worktree of a plan
SHARED = [
    "docs/milestones/**",
    "docs/IDEAS.md",
    "docs/memories/**",
    "docs/MEMORY.md",
    "docs/ai-setup-adjustments.md",
    "docs/DEPENDENCIES.md",
]
# a tool sets this variable for its own commit, so the commit check accepts a tool-owned file
TOOL_COMMIT = "SETUP_TOOL_COMMIT"

RECORD_TYPES = [
    "milestone manual passed",
    "milestone manual failed",
    "plan manual passed",
    "plan manual failed",
    "bug verified withdrawn",
    "step started",
    "step reviewed",
    "step reverted",
    "step blocked",
    "step unblocked",
    "manual passed",
    "manual failed",
    "bug verified",
    "plan reviewed",
    "document reviewed",
    "fix added",
    "refactor added",
    "review passed",
    "plan blocked",
    "plan unblocked",
    "tuning done",
    "approved",
    "rejected",
    "text changed",
    "dependencies removed",
]
# the record lines of a milestone file, in its optional section Records
MILESTONE_RECORD_TYPES = ["feature dropped", "bug dropped", "milestone reviewed"]


class Fail(Exception):
    pass


def fail(message):
    raise Fail(message)


def main(function):
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")
    try:
        code = function(sys.argv[1:])
    except Fail as error:
        print(error, file=sys.stderr)
        code = 1
    sys.exit(code or 0)


def today():
    return datetime.date.today().isoformat()


def rel(path):
    return Path(path).resolve().relative_to(ROOT).as_posix()


def read(path):
    return Path(path).read_text(encoding="utf-8")


def write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    with open(temp, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    os.replace(temp, path)


def words(text):
    return len(text.split())


def run(command, stdin=None, env=None, cwd=None):
    result = subprocess.run(
        command,
        cwd=cwd or ROOT,
        shell=isinstance(command, str),
        input=stdin,
        env={**os.environ, **env} if env else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    output = result.stdout.decode("utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")
    return result.returncode, output


def tool(name, *args, env=None):
    return run([sys.executable, "-m", f"tools.{name}", *args], env=env)


def git(*args, check=True):
    code, output = run(["git", *args])
    if check and code != 0:
        fail(f"git {' '.join(args)} failed:\n{output.strip()}")
    return output.strip()


def git_ok(*args):
    return run(["git", *args])[0] == 0


def head():
    return git("rev-parse", "HEAD")


def clean_tree():
    return git("status", "--porcelain") == ""


def dirty_files(cwd=None):
    code, output = run(["git", "status", "--porcelain"], cwd=cwd)
    return [line[3:].split(" -> ")[-1].strip('"') for line in output.splitlines() if len(line) > 3]


def writer(name):
    """The tool that writes a file, or None for a file that no tool writes."""
    if any_match(name, [pattern for pattern in GENERATED if not pattern.startswith("docs/")]):
        return "python -m tools.provider"
    return next((tool_name for pattern, tool_name in WRITERS if glob_match(name, pattern)), None)


def unclean(place="the work tree", cwd=None):
    """The message for a work tree that is not clean: each changed file with the tool that wrote it."""
    lines = [f"{place} is not clean:"]
    for name in dirty_files(cwd):
        found = writer(name)
        lines.append(f"  {name}: written by {found}, which commits its own write" if found else f"  {name}: commit this change")
    return "\n".join(lines)


def subjects():
    code, output = run(["git", "log", "--format=%H%x09%s"])
    if code != 0:
        return []
    return [tuple(line.split("\t", 1)) for line in output.splitlines() if "\t" in line]


def has_commit(subject):
    return any(found == subject for _, found in subjects())


def tool_git(*args):
    """Runs a Git command that commits as a tool, so the commit check accepts the tool-owned files."""
    code, output = run(["git", *args], env={TOOL_COMMIT: "1"})
    if code != 0:
        fail(f"git {' '.join(args)} failed:\n{output.strip()}")
    return output.strip()


def commit(message, paths=None, verify=True):
    """Commits as a tool. `verify=False` skips the commit hook for a commit that holds state files of a tool only."""
    options = [] if verify else ["--no-verify"]
    if paths:
        paths = [rel(path) for path in paths]
        git("add", "-A", "--", *paths)
        if git_ok("diff", "--cached", "--quiet", "--", *paths):
            return False
        tool_git("commit", *options, "-m", message, "--", *paths)
    else:
        git("add", "-A")
        if git_ok("diff", "--cached", "--quiet"):
            return False
        tool_git("commit", *options, "-m", message)
    return True


def current_version():
    text = git("show", "HEAD:CHANGELOG.md", check=False) if git_ok("cat-file", "-e", "HEAD:CHANGELOG.md") else ""
    match = re.search(r"^# v?(\d+)\.(\d+)\.(\d+)\b", text, re.M)
    if match:
        return [int(part) for part in match.groups()], text
    return [int(part) for part in str(load_project()["start_version"]).split(".")], text


def git_dir():
    return ROOT / git("rev-parse", "--git-dir")


def merging():
    folder = git_dir()
    return any((folder / name).exists() for name in ("MERGE_HEAD", "rebase-merge", "rebase-apply"))


def branch():
    return git("symbolic-ref", "--short", "-q", "HEAD", check=False)


def milestone_branch(milestone):
    return f"milestone/{milestone['id']}-{milestone['name']}"


def milestone_branches():
    return git("branch", "--list", "milestone/*", "--format=%(refname:short)").splitlines()


_MAIN_ROOT = []


def common_dir():
    """The Git folder that the main repository and each worktree share."""
    if not _MAIN_ROOT:
        code, output = run(["git", "rev-parse", "--git-common-dir"])
        folder = (ROOT / output.strip()).resolve() if code == 0 else ROOT.resolve() / ".git"
        _MAIN_ROOT.append(folder)
    return _MAIN_ROOT[0]


def main_root():
    """The work tree of the main repository. In the worktree of a plan it differs from `ROOT`."""
    return common_dir().parent


def milestone_logs():
    """The log folder of the tools outside a plan: in the temporary folder of the milestones of the main repository.
    The milestone close removes it."""
    return main_root() / "docs" / "milestones" / "tmp" / LOG_FOLDER


def in_worktree():
    return main_root() != ROOT.resolve()


def plan_branch(plan_id):
    return f"plan/{plan_id}"


def worktree_path(plan_id):
    return main_root() / ".worktrees" / plan_id


def require_main():
    if in_worktree():
        fail(f"run this command in the main repository: {main_root()}")


def require_worktree(plan_id=None):
    if not in_worktree():
        place = worktree_path(plan_id) if plan_id else "the worktree of the plan"
        fail(f"run this command in {place}")


def expected_branch():
    if in_worktree():
        return plan_branch(ROOT.name)
    milestone = open_milestone()
    if milestone:
        return milestone_branch(milestone)
    branches = milestone_branches()
    return branches[0] if branches else load_project()["main_branch"]


def require_branch(expected=None):
    expected = expected or expected_branch()
    if merging():
        fail(f"unfinished merge or rebase. Finish it, then check out {expected}")
    current = branch()
    if not current:
        fail(f"detached HEAD. Check out {expected}")
    if current != expected:
        fail(f"wrong branch {current}. Check out {expected}")


def glob_match(path, pattern):
    if pattern.endswith("/"):
        pattern += "**"
    regex = ""
    index = 0
    while index < len(pattern):
        if pattern.startswith("**/", index):
            regex += "(?:.*/)?"
            index += 3
        elif pattern.startswith("**", index):
            regex += ".*"
            index += 2
        elif pattern[index] == "*":
            regex += "[^/]*"
            index += 1
        elif pattern[index] == "?":
            regex += "[^/]"
            index += 1
        else:
            regex += re.escape(pattern[index])
            index += 1
    return re.fullmatch(regex, path) is not None


def any_match(path, patterns):
    return any(glob_match(path, pattern) for pattern in patterns)


def tree_files():
    output = git("ls-files", "-co", "--exclude-standard", "-z")
    return sorted(name for name in output.split("\0") if name and (ROOT / name).is_file())


def split_row(line):
    cells = re.split(r"(?<!\\)\|", line.strip())[1:-1]
    return [cell.strip().replace("\\|", "|") for cell in cells]


def format_row(cells):
    return "|" + "".join(f" {cell.replace('|', chr(92) + '|')} |" if cell else " |" for cell in cells)


def table_span(lines, heading, path):
    start = 0
    if heading:
        if f"## {heading}" not in lines:
            fail(f"{path}: section '## {heading}' is missing")
        start = lines.index(f"## {heading}") + 1
    first = start
    while first < len(lines) and not lines[first].startswith("|"):
        if heading and lines[first].startswith("#"):
            break
        first += 1
    if first >= len(lines) or not lines[first].startswith("|"):
        fail(f"{path}: the table of '{heading or 'the file'}' is missing")
    last = first
    while last < len(lines) and lines[last].startswith("|"):
        last += 1
    return first, last


def read_table(text, heading, header, path, old_header=None):
    """The rows of a table. A table with `old_header` is read too; its rows get an empty cell per new column."""
    lines = text.split("\n")
    first, last = table_span(lines, heading, path)
    found = split_row(lines[first])
    if found != header and found != old_header:
        fail(f"{path}:{first + 1}: the table header must be {format_row(header)}")
    rows = []
    for number in range(first + 2, last):
        cells = split_row(lines[number])
        if len(cells) != len(found):
            fail(f"{path}:{number + 1}: the row must have {len(found)} cells")
        row = {name: "" for name in header}
        row.update(zip(found, cells))
        for name in STATE_COLUMNS & row.keys():
            row[name] = plain_state(row[name])
        rows.append(row)
    return rows


# the state of a tracking table stands in bold when it is neither open nor empty
STATE_COLUMNS = {"State", "Status"}


def plain_state(cell):
    return cell[2:-2] if len(cell) > 4 and cell.startswith("**") and cell.endswith("**") else cell


def shown_state(cell):
    state = plain_state(cell)
    return state if state in ("", "open") else f"**{state}**"


def table_lines(header, rows):
    table = [format_row(header), "|" + "---|" * len(header)]
    return table + [
        format_row([shown_state(row[name]) if name in STATE_COLUMNS else row[name] for name in header])
        for row in rows
    ]


def write_table(text, heading, header, rows, path):
    lines = text.split("\n")
    first, last = table_span(lines, heading, path)
    return "\n".join(lines[:first] + table_lines(header, rows) + lines[last:])


def read_meta(text, path):
    end = text.find("\n---\n", 3)
    if not text.startswith("---\n") or end < 0:
        fail(f"{path}:1: the frontmatter is missing")
    try:
        meta = yaml.safe_load(text[4 : end + 1]) or {}
    except yaml.YAMLError as error:
        fail(f"{path}: the frontmatter is not valid YAML: {error}")
    if not isinstance(meta, dict):
        fail(f"{path}:1: the frontmatter must hold fields")
    result = {}
    for key, value in meta.items():
        if isinstance(value, list):
            result[key] = [str(item) for item in value]
        else:
            result[key] = "" if value is None else str(value)
    return result


def write_meta(text, meta):
    end = text.find("\n---\n", 3)
    lines = []
    for key, value in meta.items():
        if isinstance(value, list):
            lines.append(f"{key}: [{', '.join(value)}]")
        else:
            lines.append(f"{key}: {value}".rstrip())
    return "---\n" + "\n".join(lines) + text[end:]


def parse_check(text):
    match = CHECK.match(text)
    if not match:
        return None
    return (match.group(1) or match.group(3), match.group(2) or match.group(4))


def load_project():
    if not PROJECT_FILE.exists():
        fail("not initialized, run project-init")
    try:
        return tomllib.loads(read(PROJECT_FILE))
    except tomllib.TOMLDecodeError as error:
        fail(f"tools/project.toml: {error}")


def command_table():
    """The named commands of the project: the commands of each project and those of its bindings."""
    return {**BUILTIN_COMMANDS, **load_project().get("commands", {})}


def missing_command(acceptance):
    """The name of the command of an acceptance that has no binding, or None."""
    check = parse_check(acceptance)
    return check[1] if check and check[0] == "COMMAND" and check[1] not in command_table() else None


def milestone_files():
    files = list(MILESTONES.glob("M*.md")) + list((MILESTONES / "archive").glob("M*.md"))
    return sorted(files, key=lambda path: path.name)


def load_milestone(path):
    path = Path(path)
    name = rel(path)
    match = MILESTONE_FILE.match(path.name)
    if not match:
        fail(f"{name}: the file name must have the form M[NNN]-[NAME].md")
    text = read(path)
    meta = read_meta(text, name)
    for key in ("id", "name", "status", "created", "closed"):
        if key not in meta:
            fail(f"{name}: the frontmatter field '{key}' is missing")
    if (meta["id"], meta["name"]) != match.groups():
        fail(f"{name}: the fields id and name must match the file name")
    if meta["status"] not in ("draft", "open", "closed"):
        fail(f"{name}: status must be draft, open or closed")
    return {
        "path": path,
        "rel": name,
        "text": text,
        "meta": meta,
        "id": meta["id"],
        "name": meta["name"],
        "archived": path.parent.name == "archive",
        "features": read_table(text, "Features", FEATURE_HEADER, name),
        "bugs": read_table(text, "Bugs", BUG_HEADER, name, OLD_BUG_HEADER),
        "records": record_lines(text, name, MILESTONE_RECORD_TYPES),
    }


def record_lines(text, name, kinds):
    """The record lines of the optional section Records of a milestone file as type, ids and date."""
    lines = text.split("\n")
    if "## Records" not in lines:
        return []
    records = []
    for number in range(lines.index("## Records") + 1, len(lines)):
        if lines[number].startswith("## "):
            break
        if not lines[number].strip():
            continue
        tokens = lines[number].removeprefix("- ").split()
        found = None
        for kind in kinds:
            size = len(kind.split())
            if tokens[:size] == kind.split() and len(tokens) > size and DATE.match(tokens[-1]):
                found = {"type": kind, "ids": tokens[size:-1], "date": tokens[-1]}
                break
        if not found:
            fail(f"{name}:{number + 1}: not a record line of the form - <type> <ids> <date>")
        records.append(found)
    return records


def add_milestone_record(milestone, kind, *ids):
    """Appends a record line to the section Records of a milestone file. The first record adds the section."""
    line = "- " + " ".join([kind, *ids, today()])
    text = milestone["text"].rstrip("\n")
    if "\n## Records" not in text:
        text += "\n\n## Records"
    milestone["text"] = text + "\n" + line + "\n"
    milestone["records"].append({"type": kind, "ids": list(ids), "date": today()})


def save_milestone(milestone):
    text = write_meta(milestone["text"], milestone["meta"])
    text = write_table(text, "Features", FEATURE_HEADER, milestone["features"], milestone["rel"])
    text = write_table(text, "Bugs", BUG_HEADER, milestone["bugs"], milestone["rel"])
    milestone["text"] = text
    write(milestone["path"], text)


def milestones():
    return [load_milestone(path) for path in milestone_files()]


def open_milestone():
    found = [m for m in milestones() if m["meta"]["status"] == "open" and not m["archived"]]
    if len(found) > 1:
        fail("two milestone files have status open: " + " ".join(m["id"] for m in found))
    return found[0] if found else None


def find_milestone(milestone_id):
    for milestone in milestones():
        if milestone["id"] == milestone_id:
            return milestone
    fail(f"milestone {milestone_id} does not exist")


def plan_dirs():
    folders = [p for p in PLANS.glob("M*") if p.is_dir()] + [p for p in (PLANS / "archive").glob("M*") if p.is_dir()]
    return sorted(folders, key=lambda path: path.name)


def load_plan(folder):
    folder = Path(folder)
    name = rel(folder / "plan.md")
    match = PLAN_DIR.match(folder.name)
    if not match:
        fail(f"{rel(folder)}: the folder name must have the form M[NNN]-P[NNN]-[NAME]")
    if not (folder / "plan.md").exists():
        fail(f"{name}: the file is missing")
    text = read(folder / "plan.md")
    meta = read_meta(text, name)
    for key in ("id", "milestone", "type", "done", "status", "closed"):
        if key not in meta:
            fail(f"{name}: the frontmatter field '{key}' is missing")
    if meta["id"] != f"{match.group(1)}-{match.group(2)}" or meta["milestone"] != match.group(1):
        fail(f"{name}: the fields id and milestone must match the folder name")
    if meta["type"] not in PLAN_TYPES:
        fail(f"{name}: type must be feature, fix or refactor")
    field = "bugs" if meta["type"] == "fix" else "features"
    other = "bugs" if field == "features" else "features"
    if other in meta or not isinstance(meta.get(field), list):
        fail(f"{name}: a {meta['type']} plan holds its ids in the list field '{field}'")
    if meta["status"] not in ("draft", "in progress", "blocked", "closed"):
        fail(f"{name}: status must be draft, in progress, blocked or closed")
    if not isinstance(meta["done"], list):
        meta["done"] = []
    progress = folder / "progress.md"
    return {
        "dir": folder,
        "rel": rel(folder),
        "path": folder / "plan.md",
        "text": text,
        "meta": meta,
        "id": meta["id"],
        "field": field,
        "ids": meta[field],
        "archived": folder.parent.name == "archive",
        "steps": read_table(text, "Steps", STEP_HEADER, name, OLD_STEP_HEADER),
        "fixes": read_table(text, "Fix steps", FIX_HEADER, name),
        "progress": read_table(read(progress), None, PROGRESS_HEADER, rel(progress)) if progress.exists() else [],
    }


def save_plan(plan):
    text = write_meta(plan["text"], plan["meta"])
    text = write_table(text, "Fix steps", FIX_HEADER, plan["fixes"], plan["rel"])
    plan["text"] = text
    write(plan["path"], text)
    if plan["progress"]:
        write(plan["dir"] / "progress.md", "\n".join(table_lines(PROGRESS_HEADER, plan["progress"])) + "\n")


def plans():
    return [load_plan(folder) for folder in plan_dirs()]


def active_plans():
    """Each plan in progress or blocked that this work tree holds."""
    return [p for p in plans() if not p["archived"] and p["meta"]["status"] in ("in progress", "blocked")]


def merged(plan_id):
    """Whether the milestone branch holds the squash commit of the plan."""
    return has_commit(f"Plan merged: {plan_id}")


def active_plan():
    """The plan of this work tree: in a worktree the plan of its branch, in the main repository the plan in close."""
    found = active_plans()
    if in_worktree():
        own = [p for p in found if plan_branch(p["id"]) == branch()]
        return own[0] if own else None
    closing = [p for p in found if merged(p["id"])]
    if len(closing) > 1:
        fail("two plans are in close: " + " ".join(p["id"] for p in closing))
    return closing[0] if closing else None


def require_plan():
    plan = active_plan()
    if not plan and in_worktree():
        fail(f"the branch {branch() or 'detached HEAD'} has no active plan")
    if not plan:
        names = " ".join(p["id"] for p in active_plans())
        fail(f"no plan is in close. Active plans: {names or 'none'}. Work on a plan in its worktree")
    return plan


def dependency_rows():
    """The rows of the dependencies file, or no row when the project has no such file."""
    path = DOCS / "DEPENDENCIES.md"
    if not path.exists():
        return []
    return read_table(read(path), "Dependencies", DEPENDENCY_HEADER, rel(path))


def dependency_errors(cell, name):
    """The errors of the Dependencies cell of a step: it holds `none` or ids of the dependencies file."""
    known = {row["ID"] for row in dependency_rows()}
    ids = cell.split()
    if not ids:
        return [f"{name}: the Dependencies cell is empty, write the ids or 'none'"]
    if ids == ["none"]:
        return []
    return [f"{name}: {item} is not an id of docs/DEPENDENCIES.md" for item in ids if item not in known]


def all_steps(plan):
    return plan["steps"] + plan["fixes"]


def required_steps(plan, milestone):
    if plan["field"] == "features":
        dropped = {row["ID"] for row in milestone["features"] if row["State"] == "dropped"}
        return [step for step in all_steps(plan) if step["Feature"] not in dropped]
    known = {row["ID"] for row in milestone["bugs"]} | set(plan["meta"]["done"])
    return [step for step in all_steps(plan) if step["Feature"] in known]


def next_id(prefix, used, width=2):
    numbers = [int(re.sub(r"\D", "", item.split("-")[0])) for item in used]
    return f"{prefix}{max(numbers, default=0) + 1:0{width}d}"


def find_step(plan, step_id):
    for step in all_steps(plan):
        if step["Step"] == step_id:
            return step
    fail(f"{plan['rel']}/plan.md: step {step_id} does not exist")


def progress_row(plan, step_id):
    for row in plan["progress"]:
        if row["Step"] == step_id:
            return row
    fail(f"{plan['rel']}/progress.md: step {step_id} does not exist")


class Problems:
    def __init__(self, plan):
        self.path = plan["dir"] / "problems.md"
        self.rel = rel(self.path)
        self.rows, self.records, self.header = [], [], PROBLEM_HEADER
        if not self.path.exists():
            if plan.get("archived"):
                self.text = ""
                return
            fail(f"{self.rel}: the file is missing")
        self.text = read(self.path)
        self.rows = read_table(self.text, "Problems", PROBLEM_HEADER, self.rel, OLD_PROBLEM_HEADER)
        lines = self.text.split("\n")
        if split_row(lines[table_span(lines, "Problems", self.rel)[0]]) == OLD_PROBLEM_HEADER:
            self.header = OLD_PROBLEM_HEADER
        if "## Records" not in lines:
            fail(f"{self.rel}: section '## Records' is missing")
        for number in range(lines.index("## Records") + 1, len(lines)):
            if lines[number].strip():
                self.records.append(self.parse(lines[number], number + 1))
        for row in self.rows:
            errors = row_errors(row, self.header)
            if errors:
                fail(f"{self.rel}: problem {row['ID']}: {errors[0]}")

    def parse(self, line, number):
        tokens = line.removeprefix("- ").split()
        for kind in RECORD_TYPES:
            size = len(kind.split())
            if tokens[:size] == kind.split() and len(tokens) > size and DATE.match(tokens[-1]):
                return {"type": kind, "ids": tokens[size:-1], "date": tokens[-1]}
        fail(f"{self.rel}:{number}: not a record line of the form - <type> <ids> <date>")

    def record(self, kind, *ids):
        line = "- " + " ".join([kind, *ids, today()])
        self.text = self.text.rstrip("\n") + "\n" + line + "\n"
        self.records.append({"type": kind, "ids": list(ids), "date": today()})

    def last(self, kinds, first_id=None):
        for record in reversed(self.records):
            if record["type"] in kinds and (first_id is None or record["ids"][:1] == [first_id]):
                return record
        return None

    def count_since(self, kind, boundaries, first_id=None):
        count = 0
        for record in self.records:
            if first_id is not None and record["ids"][:1] != [first_id]:
                continue
            if record["type"] in boundaries:
                count = 0
            elif record["type"] == kind:
                count += 1
        return count

    def save(self):
        self.text = write_table(self.text, "Problems", self.header, self.rows, self.rel)
        write(self.path, self.text)


SEVERITIES = ("Important", "Nit", "Pre-existing")
# the answers that an agent writes with the answer command, and the answers that only a state tool writes
AGENT_ANSWER = re.compile(r"^(fixed \S+|closed (wrong|intentional|prevented) \S.*|bug \S+)$")
TOOL_ANSWERS = ("reverted", "user ", "fix ")
CHECK_CELL = re.compile(r"^(confirmed|re-raised \S.*|carried N\d{2})$")


def row_errors(row, header=PROBLEM_HEADER):
    """The errors of one problem row, each with the rule that it breaks."""
    errors = []
    if not PROBLEM_ID.match(row["ID"]):
        errors.append("D900: the id must have the form N[NN]")
    if row["Step"] != "plan" and not STEP_ID.match(row["Step"]):
        errors.append("D900: Step must be a step id or 'plan'")
    if row["Round"] not in ROUNDS:
        errors.append("D1003: Round must be 1, 2 or 3")
    if row["Severity"] not in SEVERITIES:
        errors.append("docs/REVIEW.md, Problem format: Severity must be Important, Nit or Pre-existing")
    for cell in ("Rule", "Location", "Trigger", "Class", "Fix"):
        if not row[cell]:
            errors.append(f"docs/REVIEW.md, Problem format: the cell {cell} is empty")
    if header == PROBLEM_HEADER and not 1 <= words(row["Topic"]) <= 2:
        errors.append("D907: Topic must have one or two words")
    answer = row["Answer"]
    if answer and not (AGENT_ANSWER.match(answer) or answer == "reverted" or re.match(r"^(user \S.*|fix \S+)$", answer)):
        errors.append("D902: Answer must be 'fixed <commit>' or 'closed <wrong|intentional|prevented> <reason>'")
    if row["Check"] and not CHECK_CELL.match(row["Check"]):
        errors.append("D904: Check must be 'confirmed', 're-raised <trigger>' or 'carried <id>'")
    return errors


def settled(row):
    return row["Severity"] == "Pre-existing" or row["Answer"].startswith(TOOL_ANSWERS)


# a review has max 3 rounds; a further round runs only when the round before posted an Important problem
ROUNDS = ("1", "2", "3")
MAX_ROUNDS = len(ROUNDS)


def posted_important(rows, round_number):
    return any(row["Round"] == str(round_number) and row["Severity"] == "Important" for row in rows)


def problem_errors(rows, hint, held):
    """The gate errors of the problem rows of one subject after `held` review rounds."""
    errors = []
    last = held >= MAX_ROUNDS
    by_id = {row["ID"]: row for row in rows}
    for row in rows:
        if settled(row):
            continue
        important = row["Severity"] == "Important"
        if not row["Answer"]:
            errors.append(f"{row['ID']}: the problem has no answer")
        elif row["Check"].startswith("carried"):
            # a later row carries the re-raised trigger: the problem closes with the confirmed answer of that row
            carrier = by_id.get(row["Check"].split()[1])
            if not carrier or not carrier["Answer"] or carrier["Check"] != "confirmed":
                errors.append(f"{row['ID']}: {row['Check']} needs an answer of that row and the check confirmed")
        elif row["Check"].startswith("re-raised"):
            if important and last:
                errors.append(f"{row['ID']}: Important problem re-raised in round {held}: {hint}")
            elif important or row["Answer"].startswith("closed"):
                errors.append(f"{row['ID']}: the problem was re-raised, fix it and run round {held + 1}")
        elif important and not row["Check"]:
            if row["Round"] == str(held) and last:
                errors.append(f"{row['ID']}: Important problem posted in round {held}: {hint}")
            elif row["Round"] == str(held):
                errors.append(f"{row['ID']}: the fix of an Important problem has no check, run round {held + 1}")
            else:
                errors.append(f"{row['ID']}: the answer has no check, run the review again")
    return errors


def open_important(rows, held):
    """The Important problems that stay open after `held` rounds: unanswered, re-raised in the last round, or
    posted in the last round without the short check of their fix."""
    last = held >= MAX_ROUNDS
    return [
        row["ID"]
        for row in rows
        if not settled(row)
        and row["Severity"] == "Important"
        and (not row["Answer"] or (last and (row["Check"].startswith("re-raised") or (row["Round"] == str(held) and not row["Check"]))))
    ]


def protected_patterns():
    review = DOCS / "REVIEW.md"
    patterns = [row["Path"] for row in read_table(read(review), "Protected paths", ["Path"], rel(review))]
    deployment = ROOT / "DEPLOYMENT.md"
    if deployment.exists():
        header = ["Path", "What must stay compatible"]
        patterns += [row["Path"] for row in read_table(read(deployment), "Compatible", header, "DEPLOYMENT.md")]
    if PROJECT_FILE.exists() and load_project().get("ci", "none") != "none":
        patterns.append(load_project()["ci"])
    return patterns


def changed_since(base):
    names = set(git("diff", "--name-only", base).splitlines())
    names |= set(git("ls-files", "-o", "--exclude-standard").splitlines())
    return sorted(names)


def approval_errors(plan, problems, target, base):
    patterns = protected_patterns()
    touched = [name for name in changed_since(base) if any_match(name, patterns)]
    if not touched:
        return []
    record = problems.last(("approved", "rejected"), target)
    command = f"python -m tools.approve {plan['id']} {target}"
    if not record or record["type"] != "approved":
        return [f"protected paths changed without approval ({' '.join(touched)}): run {command}"]
    stale = [name for name in touched if not git_ok("diff", "--quiet", record["ids"][1], "--", name)]
    if stale:
        return [f"protected paths changed after the approval ({' '.join(stale)}): run {command} again"]
    return []


def ask(question, answer=None):
    if answer is None:
        fail(f"{question}\nAsk the user, then run the command again with --answer yes or --answer no")
    answer = answer.strip().lower()
    if answer not in ("yes", "no", "y", "n"):
        fail("the answer must be yes or no")
    return answer.startswith("y")


# the records of a manual check; a record of the current form ends with the name of the check and the checked commit
MANUAL_RECORDS = ("manual passed", "manual failed", "plan manual passed", "plan manual failed", "milestone manual passed", "milestone manual failed")
SETUP_PATHS = ["tools/**", ".agents/**", "AGENTS.md", ".claude/**", ".codex/**", ".kilo/**", "CLAUDE.md", ".mcp.json", "kilo.jsonc", ".vale.ini"]


def product_changes(commit_hash):
    """The files of the product that changed since a commit, committed or not: each file outside `docs/` and the
    setup, except a Markdown file."""
    names = set(git("diff", "--name-only", commit_hash).splitlines()) | set(git("ls-files", "-o", "--exclude-standard").splitlines())
    return sorted(name for name in names if not name.startswith("docs/") and not name.endswith(".md") and not any_match(name, SETUP_PATHS))


def earlier_pass(all_problems, name):
    """The newest manual record of the check `name` that names its commit, and the product files that changed since
    that commit. A failed record or no record gives (None, [])."""
    found = []
    for problems in all_problems:
        for record in problems.records:
            ids = record["ids"]
            if record["type"] in MANUAL_RECORDS and len(ids) >= 2 and ids[-2] == name and re.fullmatch(r"[0-9a-f]{7,40}", ids[-1]):
                code, stamp = run(["git", "log", "-1", "--format=%ct", ids[-1]])
                if code == 0 and stamp.strip().isdigit():
                    found.append((int(stamp.strip()), len(found), record))
    if not found:
        return None, []
    record = max(found, key=lambda item: item[:2])[2]
    if not record["type"].endswith("passed"):
        return None, []
    return record, product_changes(record["ids"][-1])


def manual_answer(all_problems, name, question, answer):
    """Whether the manual check `name` passed, and the source of the result. Without `--answer`, an earlier pass holds
    while no product file changed since its commit. After such a change, the question names the changed files."""
    if answer is not None:
        return ask(question, answer), "answer"
    record, changed = earlier_pass(all_problems, name)
    if record and not changed:
        return True, f"earlier pass at {record['ids'][-1]}"
    if record:
        question += f"\nThe pass at {record['ids'][-1]} no longer holds, these files changed since: {' '.join(changed)}"
    return ask(question, None), "answer"


def user_reason(answer, question, limit=12):
    """The reason of the user that `--answer` passes. The permission rule on `--answer` makes it the user key."""
    if answer is None:
        fail(f'{question}\nAsk the user, then run the command again with --answer "<answer of the user>"')
    text = " ".join(answer.split())
    if not 1 <= words(text) <= limit or "|" in text:
        fail(f"the answer of the user must have 1 to {limit} words and no '|'")
    return text


def take_option(args, name):
    if name in args:
        index = args.index(name)
        if index + 1 >= len(args):
            fail(f"{name} needs a value")
        value = args[index + 1]
        del args[index : index + 2]
        return value
    return None


def stop_package(folder):
    """Stops each program of a manual check package, so the close can remove the folder."""
    folder = Path(folder)
    if not folder.exists():
        return
    for path in folder.rglob("*"):
        if not path.is_file() or not (path.suffix == ".exe" or os.access(path, os.X_OK) and not path.suffix):
            continue
        if os.name == "nt":
            run(["taskkill", "/F", "/IM", path.name])
        else:
            run(["pkill", "-f", path.name])


def hook_input():
    try:
        data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def outside(name):
    return os.path.isabs(name)


def setup_root(path):
    """The root of the main repository or of one of its worktrees that holds `path`: the first folder upward that holds
    the tools of the setup. None for a path outside of them, also for a path in another repository."""
    folder = Path(os.path.abspath(path))
    for candidate in [folder, *folder.parents]:
        if (candidate / "tools" / "_lib.py").is_file():
            candidate = candidate.resolve()
            main_folder = main_root()
            return candidate if candidate == main_folder or candidate.parent == main_folder / ".worktrees" else None
    return None


def split_hook(module, args, data, argv=()):
    """Runs the hook `module` with `args` in the root of each path of an agent write that lies in another worktree of
    this repository, or in the main repository. A write without an agent keeps the root of the session. Returns the
    highest exit code of those runs and the paths of this root, as `hook_paths` gives them."""
    paths = hook_paths(list(argv), data)
    if not data.get("agent_id") or os.environ.get(HOOK_PATHS):
        return 0, paths
    own, local, foreign = ROOT.resolve(), [], {}
    for name, kind in paths:
        root = setup_root(os.path.join(ROOT, name))
        if root is None or root == own:
            local.append((name, kind))
        else:
            foreign.setdefault(root, []).append((os.path.abspath(os.path.join(ROOT, name)), kind))
    code = 0
    for root, found in foreign.items():
        result = subprocess.run(
            [sys.executable, "-m", f"tools.{module}", *args],
            cwd=root,
            input=json.dumps(data).encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={**os.environ, HOOK_PATHS: json.dumps(found)},
        )
        sys.stdout.write(result.stdout.decode("utf-8", errors="replace"))
        sys.stderr.write(result.stderr.decode("utf-8", errors="replace"))
        code = max(code, result.returncode)
    return code, local


# a hook that runs in the root of a write gets the paths of that root in this variable
HOOK_PATHS = "SETUP_HOOK_PATHS"


def hook_paths(argv, data=None):
    if argv:
        found = [(name, "write") for name in argv]
    elif os.environ.get(HOOK_PATHS):
        found = [tuple(item) for item in json.loads(os.environ[HOOK_PATHS])]
    else:
        data = hook_input() if data is None else data
        values = data.get("tool_input") or data.get("args") or {}
        found = []
        for key in ("file_path", "filePath", "path"):
            if isinstance(values.get(key), str):
                found.append((values[key], "write"))
        for key in ("command", "patchText", "patch"):
            patch = values.get(key)
            if isinstance(patch, str) and "*** Begin Patch" in patch:
                for match in re.finditer(r"^\*\*\* (Add File|Update File|Delete File|Move to): (.+)$", patch, re.M):
                    kind = {"Delete File": "delete", "Move to": "move"}.get(match.group(1), "write")
                    found.append((match.group(2).strip(), kind))
                for match in re.finditer(r"^\*\*\* Update File: (.+)\n\*\*\* Move to: ", patch, re.M):
                    found.append((match.group(1).strip(), "move"))
    result = []
    for name, kind in found:
        path = os.path.abspath(os.path.join(ROOT, name))
        try:
            relative = os.path.relpath(path, ROOT).replace("\\", "/")
        except ValueError:
            relative = ".."
        result.append((path.replace("\\", "/") if relative.startswith("..") else relative, kind))
    return result
