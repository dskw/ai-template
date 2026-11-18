import os
import shlex
import subprocess

from tools import build_wiki_bundle, check_encoding, docs_lint, memory_lint, progress, provider
from tools._lib import (
    DRAFT_ONLY,
    PROJECT_FILE,
    ROOT,
    TOOL_COMMIT,
    TOOL_OWNED,
    Fail,
    Problems,
    active_plan,
    active_plans,
    any_match,
    git_ok,
    in_worktree,
    load_project,
    main,
    open_milestone,
    run as shell,
)


def quote(targets):
    if os.name == "nt":
        return subprocess.list2cmdline(targets)
    return " ".join(shlex.quote(target) for target in targets)


def language_errors(files, format_only=False):
    if not PROJECT_FILE.exists():
        return []
    errors = []
    for entry in load_project().get("language", []):
        roots = [root.rstrip("/") for root in entry["source"] + entry["tests"]]
        if files is None:
            targets = [root for root in roots if (ROOT / root).exists()]
        else:
            targets = [
                name
                for name in files
                if name.endswith(tuple(entry["extensions"])) and any(name.startswith(root + "/") for root in roots)
            ]
        if not targets:
            continue
        keys = ("format",) if format_only else ("format", "lint", "comments")
        for key in (key for key in keys if key in entry):
            code, output = shell(entry[key].replace("{files}", quote(targets)))
            if code != 0:
                rule = ", the comment rule of docs/CODE_CONVENTIONS.md" if key == "comments" else ""
                errors.append(f"{entry['name']} {key}{rule}:\n{output.rstrip()}")
    return errors


def commit_order_errors():
    if not PROJECT_FILE.exists():
        return []
    code, output = shell(["git", "diff", "--cached", "--name-only"])
    staged = output.split()
    roots = [root.rstrip("/") + "/" for entry in load_project().get("language", []) for root in entry["source"] + entry["tests"]]
    if code != 0 or not any(name.startswith(tuple(roots)) for name in staged):
        return []
    if os.environ.get(TOOL_COMMIT):
        return []
    try:
        plan = active_plan()
        waiting = active_plans()
    except Fail:
        return []
    if not in_worktree() and waiting:
        return ["a source or test change belongs to a step: make it in the worktree of its plan"]
    if not plan or any(row["State"] == "in progress" for row in plan["progress"]):
        return []
    last = Problems(plan).last(("step started", "plan reviewed"))
    if last and last["type"] == "plan reviewed":
        return []
    milestone = open_milestone()
    step = progress.next_step(plan, milestone) if milestone else None
    return [f"start the step first: python -m tools.step_close start {step or '<step>'}"]


def owner_errors():
    """The staged files that only a tool commits. A tool sets the variable `TOOL_COMMIT` for its own commit."""
    if os.environ.get(TOOL_COMMIT):
        return []
    code, output = shell(["git", "diff", "--cached", "--name-only"])
    owned = []
    for name in output.split() if code == 0 else []:
        # a milestone file and a plan file belong to a tool from their first commit on
        draft = any_match(name, DRAFT_ONLY) and git_ok("cat-file", "-e", f"HEAD:{name}")
        if any_match(name, TOOL_OWNED) or draft:
            owned.append(name)
    if not owned:
        return []
    return ["only a tool commits these files, undo the change and use the tool of the file: " + " ".join(owned)]


def touches(files, patterns):
    return files is None or any(any_match(name, patterns) for name in files)


def staged_files():
    code, output = shell(["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"])
    return [name for name in output.split() if (ROOT / name).is_file()] if code == 0 else []


def run(args):
    format_only = "--format-only" in args
    # the commit hook lints the staged documents only, so a commit prints no warning of an unchanged document
    staged = "--staged" in args
    args = [name for name in args if name not in ("--format-only", "--staged")]
    files = None
    if args:
        files = [os.path.relpath(os.path.abspath(name), ROOT).replace("\\", "/") for name in args]
        files = [name for name in files if (ROOT / name).is_file()]
    documents = [name for name in staged_files() if name.endswith(".md")] if staged and files is None else files
    checks = [("lint and format", lambda: (language_errors(files, format_only), [])), ("encoding", lambda: (check_encoding.errors(files), []))]
    checks.append(("docs lint", lambda: docs_lint.lint(documents or None) if documents or not staged else ([], [])))
    if touches(files, ["docs/MEMORY.md", "docs/memories/**"]):
        checks.append(("memory lint", memory_lint.lint))
    if touches(files, [".agents/**", "AGENTS.md"]):
        checks.append(("provider", lambda: (provider.check_errors(), [])))
    if touches(files, ["docs/wiki/**"]):
        checks.append(("wiki bundle", lambda: (build_wiki_bundle.check_errors(), [])))
    if touches(files, ["docs/milestones/**", "docs/plans/**"]):
        checks.append(("progress", lambda: (progress.check_errors(), [])))
    if files is None:
        checks.append(("commit order", lambda: (commit_order_errors(), [])))
    if staged:
        checks.append(("tool files", lambda: (owner_errors(), [])))
    failed = False
    for name, function in checks:
        try:
            errors, warnings = function()
        except Fail as error:
            errors, warnings = [str(error)], []
        for line in warnings:
            print(f"warning: {line}")
        if errors:
            failed = True
            print(f"FAIL {name}")
            print("\n".join(errors))
        else:
            print(f"ok {name}")
    return 1 if failed else 0


if __name__ == "__main__":
    main(run)
