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

MILESTONE_FILE = re.compile(r"^(M\d{3})-([a-z0-9]+(?:-[a-z0-9]+)*)\.md$")
PLAN_DIR = re.compile(r"^(M\d{3})-(P\d{3})-([a-z0-9]+(?:-[a-z0-9]+)*)$")
FEATURE_ID = re.compile(r"^F\d{2}$")
BUG_ID = re.compile(r"^B\d{2}$")
STEP_ID = re.compile(r"^S\d{2}(-fix)?$")
PROBLEM_ID = re.compile(r"^N\d{2}$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
CHECK = re.compile(r"^(?:(TEST|COMMAND) (\S+) passes|(MANUAL) (\S+))$")

FEATURE_HEADER = ["ID", "Feature", "Type", "Acceptance", "Plans", "State"]
BUG_HEADER = ["ID", "Bug", "Feature", "Source", "Acceptance"]
STEP_HEADER = ["Step", "Feature", "Text", "Verification"]
FIX_HEADER = ["Step", "Feature", "Problem", "Text", "Verification"]
PROGRESS_HEADER = ["Step", "Feature", "State", "Evidence", "Round"]
PROBLEM_HEADER = ["ID", "Step", "Round", "Severity", "Rule", "Location", "Trigger", "Class", "Fix", "Answer", "Check"]
EXTENSION_HEADER = ["ID", "Extension", "Decision", "Detail"]
MILESTONE_HEADER = ["Milestone", "Features", "Done", "Bugs", "Status"]

RECORD_TYPES = [
    "milestone manual passed",
    "milestone manual failed",
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
    "fix added",
    "review passed",
    "plan blocked",
    "plan unblocked",
    "tuning done",
    "approved",
    "rejected",
]


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


def run(command, stdin=None):
    result = subprocess.run(
        command,
        cwd=ROOT,
        shell=isinstance(command, str),
        input=stdin,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    output = result.stdout.decode("utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")
    return result.returncode, output


def tool(name, *args):
    return run([sys.executable, "-m", f"tools.{name}", *args])


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


def dirty_files():
    code, output = run(["git", "status", "--porcelain"])
    return [line[3:].split(" -> ")[-1].strip('"') for line in output.splitlines() if len(line) > 3]


def subjects():
    code, output = run(["git", "log", "--format=%H%x09%s"])
    if code != 0:
        return []
    return [tuple(line.split("\t", 1)) for line in output.splitlines() if "\t" in line]


def has_commit(subject):
    return any(found == subject for _, found in subjects())


def commit(message, paths=None):
    if paths:
        paths = [rel(path) for path in paths]
        git("add", "-A", "--", *paths)
        if git_ok("diff", "--cached", "--quiet", "--", *paths):
            return False
        git("commit", "-m", message, "--", *paths)
    else:
        git("add", "-A")
        if git_ok("diff", "--cached", "--quiet"):
            return False
        git("commit", "-m", message)
    return True


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


def expected_branch():
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


def read_table(text, heading, header, path):
    lines = text.split("\n")
    first, last = table_span(lines, heading, path)
    if split_row(lines[first]) != header:
        fail(f"{path}:{first + 1}: the table header must be {format_row(header)}")
    rows = []
    for number in range(first + 2, last):
        cells = split_row(lines[number])
        if len(cells) != len(header):
            fail(f"{path}:{number + 1}: the row must have {len(header)} cells")
        rows.append(dict(zip(header, cells)))
    return rows


def table_lines(header, rows):
    table = [format_row(header), "|" + "---|" * len(header)]
    return table + [format_row([row[name] for name in header]) for row in rows]


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
        "bugs": read_table(text, "Bugs", BUG_HEADER, name),
    }


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
    if meta["type"] not in ("feature", "fix"):
        fail(f"{name}: type must be feature or fix")
    field = "features" if meta["type"] == "feature" else "bugs"
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
        "steps": read_table(text, "Steps", STEP_HEADER, name),
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


def active_plan():
    found = [p for p in plans() if not p["archived"] and p["meta"]["status"] in ("in progress", "blocked")]
    if len(found) > 1:
        fail("two plans are active: " + " ".join(p["id"] for p in found))
    return found[0] if found else None


def require_plan():
    plan = active_plan()
    if not plan:
        fail("no active plan")
    return plan


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
        if not self.path.exists():
            fail(f"{self.rel}: the file is missing")
        self.text = read(self.path)
        self.rows = read_table(self.text, "Problems", PROBLEM_HEADER, self.rel)
        self.records = []
        lines = self.text.split("\n")
        if "## Records" not in lines:
            fail(f"{self.rel}: section '## Records' is missing")
        for number in range(lines.index("## Records") + 1, len(lines)):
            if lines[number].strip():
                self.records.append(self.parse(lines[number], number + 1))
        for row in self.rows:
            self.validate(row)

    def parse(self, line, number):
        tokens = line.removeprefix("- ").split()
        for kind in RECORD_TYPES:
            size = len(kind.split())
            if tokens[:size] == kind.split() and len(tokens) > size and DATE.match(tokens[-1]):
                return {"type": kind, "ids": tokens[size:-1], "date": tokens[-1]}
        fail(f"{self.rel}:{number}: not a record line of the form - <type> <ids> <date>")

    def validate(self, row):
        name = f"{self.rel}: problem {row['ID']}"
        if not PROBLEM_ID.match(row["ID"]):
            fail(f"{name}: the id must have the form N[NN]")
        if row["Step"] != "plan" and not STEP_ID.match(row["Step"]):
            fail(f"{name}: Step must be a step id or 'plan'")
        if row["Round"] not in ("1", "2"):
            fail(f"{name}: Round must be 1 or 2")
        if row["Severity"] not in ("Important", "Nit", "Pre-existing"):
            fail(f"{name}: Severity must be Important, Nit or Pre-existing")
        for cell in ("Rule", "Location", "Trigger", "Class", "Fix"):
            if not row[cell]:
                fail(f"{name}: the cell {cell} is empty")
        answer = row["Answer"]
        if answer and not re.match(r"^(fixed \S+|closed (wrong|intentional|prevented) \S.*|reverted|user \S.*|fix \S+|bug \S+)$", answer):
            fail(f"{name}: Answer must be 'fixed <commit>' or 'closed <wrong|intentional|prevented> <reason>'")
        if row["Check"] and not re.match(r"^(confirmed|re-raised \S.*)$", row["Check"]):
            fail(f"{name}: Check must be 'confirmed' or 're-raised <trigger>'")

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
        self.text = write_table(self.text, "Problems", PROBLEM_HEADER, self.rows, self.rel)
        write(self.path, self.text)


def settled(row):
    return row["Severity"] == "Pre-existing" or row["Answer"].startswith(("reverted", "user ", "fix "))


def problem_errors(rows, hint):
    errors = []
    for row in rows:
        if settled(row):
            continue
        important = row["Severity"] == "Important"
        if not row["Answer"]:
            errors.append(f"{row['ID']}: the problem has no answer")
        elif row["Check"].startswith("re-raised"):
            if important:
                errors.append(f"{row['ID']}: Important problem re-raised in round 2: {hint}")
            elif row["Answer"].startswith("closed"):
                errors.append(f"{row['ID']}: the closed answer was re-raised, fix the problem")
        elif row["Round"] == "1" and not row["Check"]:
            errors.append(f"{row['ID']}: the answer has no check, run the review again as round 2")
        elif row["Round"] == "2" and important:
            errors.append(f"{row['ID']}: Important problem posted in round 2: {hint}")
    return errors


def open_important(rows):
    return [
        row["ID"]
        for row in rows
        if not settled(row)
        and row["Severity"] == "Important"
        and (not row["Answer"] or row["Check"].startswith("re-raised") or row["Round"] == "2")
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


def take_option(args, name):
    if name in args:
        index = args.index(name)
        if index + 1 >= len(args):
            fail(f"{name} needs a value")
        value = args[index + 1]
        del args[index : index + 2]
        return value
    return None


def hook_input():
    try:
        data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def outside(name):
    return os.path.isabs(name)


def hook_paths(argv, data=None):
    if argv:
        found = [(name, "write") for name in argv]
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
