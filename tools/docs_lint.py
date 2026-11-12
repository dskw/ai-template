import json
import re
import shutil

from tools import build_wiki_bundle
from tools._lib import DOCS, PROJECT_FILE, ROOT, any_match, fail, load_project, main, read, read_table, run as shell, tree_files

SCOPE = ["docs/**/*.md", "AGENTS.md", ".agents/**/*.md", "CHANGELOG.md"]
AGNOSTIC = [".agents/skills/**", ".agents/agents/**"]
CONTENT = [
    (re.compile(r"\bM\d{3}(?:-P\d{3})?\b"), "a milestone or plan id"),
    (re.compile(r"\b[BN]\d{2}\b"), "a bug or problem id"),
    (re.compile(r"\b\d{4}-\d{2}-\d{2}\b"), "a date"),
    (re.compile(r"\b\d+\.\d+\.\d+\b"), "a version number"),
]
STATE_PATH = re.compile(r"docs/(?:milestones|plans|design)/([^\s`'\")/]+)")
FIXED_NAMES = ("archive", "PROGRESS.md", "PROJECT.md")


def exclusions():
    path = DOCS / "DOCS_CONVENTIONS.md"
    return [row["Path"] for row in read_table(read(path), "Lint exclusions", ["Path"], "docs/DOCS_CONVENTIONS.md")]


def vale(files):
    binary = shutil.which("vale")
    if not binary:
        return ["Vale is not installed, run python -m tools.setup"], []
    errors, warnings = [], []
    for start in range(0, len(files), 40):
        command = [binary, "--output=JSON", "--no-exit", "--config", str(ROOT / ".vale.ini"), *files[start : start + 40]]
        code, output = shell(command)
        try:
            alerts = json.loads(output[output.index("{") :])
        except ValueError:
            return [f"Vale failed:\n{output}"], warnings
        for name, items in alerts.items():
            for item in items:
                line = f"{name.replace(chr(92), '/')}:{item['Line']}: {item['Message']}"
                (errors if item["Severity"] == "error" else warnings).append(line)
    return errors, warnings


def content_errors(name):
    errors = []
    terms = load_project()["product_terms"] if PROJECT_FILE.exists() else []
    for number, line in enumerate(read(ROOT / name).split("\n"), 1):
        for pattern, label in CONTENT:
            if pattern.search(line):
                errors.append(f"{name}:{number}: {label}. A skill or an agent definition holds no project content")
        for match in STATE_PATH.finditer(line):
            if match.group(1) not in FIXED_NAMES and not re.search(r"[\[<*]", match.group(1)):
                errors.append(f"{name}:{number}: the path '{match.group(0)}' names a specific file or folder")
        for term in terms:
            if re.search(rf"\b{re.escape(term)}\b", line, re.I):
                errors.append(f"{name}:{number}: the product term '{term}'")
    return errors


def lint(files=None):
    excluded = exclusions()
    names = [name for name in (files if files is not None else tree_files()) if (ROOT / name).is_file()]
    prose = [name for name in names if any_match(name, SCOPE) and not any_match(name, excluded)]
    errors, warnings = vale(prose) if prose else ([], [])
    diagrams = {name: read(ROOT / name) for name in prose if not name.startswith("docs/wiki/")}
    errors += build_wiki_bundle.mermaid_errors(diagrams)
    for name in names:
        if any_match(name, AGNOSTIC):
            errors += content_errors(name)
    return errors, warnings


def run(args):
    errors, warnings = lint(args or None)
    for line in warnings:
        print(f"warning: {line}")
    if errors:
        fail("\n".join(errors))
    print("docs ok")


if __name__ == "__main__":
    main(run)
