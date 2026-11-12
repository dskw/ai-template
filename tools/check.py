import os
import shlex
import subprocess

from tools import build_wiki_bundle, check_encoding, docs_lint, memory_lint, progress, provider
from tools._lib import PROJECT_FILE, ROOT, Fail, Problems, active_plan, any_match, load_project, main, open_milestone, run as shell


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
        for key in ("format",) if format_only else ("format", "lint"):
            code, output = shell(entry[key].replace("{files}", quote(targets)))
            if code != 0:
                errors.append(f"{entry['name']} {key}:\n{output.rstrip()}")
    return errors


def commit_order_errors():
    if not PROJECT_FILE.exists():
        return []
    code, output = shell(["git", "diff", "--cached", "--name-only"])
    staged = output.split()
    roots = [root.rstrip("/") + "/" for entry in load_project().get("language", []) for root in entry["source"] + entry["tests"]]
    if code != 0 or not any(name.startswith(tuple(roots)) for name in staged):
        return []
    try:
        plan = active_plan()
    except Fail:
        return []
    if not plan or any(row["State"] == "in progress" for row in plan["progress"]):
        return []
    last = Problems(plan).last(("step started", "plan reviewed"))
    if last and last["type"] == "plan reviewed":
        return []
    milestone = open_milestone()
    step = progress.next_step(plan, milestone) if milestone else None
    return [f"start the step first: python -m tools.step_close start {step or '<step>'}"]


def touches(files, patterns):
    return files is None or any(any_match(name, patterns) for name in files)


def run(args):
    format_only = "--format-only" in args
    args = [name for name in args if name != "--format-only"]
    files = None
    if args:
        files = [os.path.relpath(os.path.abspath(name), ROOT).replace("\\", "/") for name in args]
        files = [name for name in files if (ROOT / name).is_file()]
    checks = [("lint and format", lambda: (language_errors(files, format_only), [])), ("encoding", lambda: (check_encoding.errors(files), []))]
    checks.append(("docs lint", lambda: docs_lint.lint(files)))
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
