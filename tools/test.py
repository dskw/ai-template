import datetime
import os
import tempfile
import xml.etree.ElementTree as ElementTree
from pathlib import Path

from tools._lib import BUILTIN_COMMANDS, ROOT, commit, fail, git, load_project, main, progress_row, read, require_plan, run as shell, take_option, write

# the lines of output that the tool prints per failed test, and for a failed run without a report file
FAILURE_LINES = 60


def evidence_path(plan, step_id):
    return plan["dir"] / "evidence" / f"{step_id}-test.txt"


def append_evidence(plan, step_id, name, command, code, output):
    path = evidence_path(plan, step_id)
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    block = (
        f"=== run\nname: {name}\ncommand: {command}\nhead: {git('rev-parse', '--short=12', 'HEAD')}\n"
        f"exit: {code}\ndate: {stamp}\noutput:\n{output.rstrip()}\n=== end\n"
    )
    write(path, (read(path) if path.exists() else "") + block)
    commit(f"Evidence: {plan['id']} {step_id}", [path], verify=False)


def evidence_runs(plan, step_id):
    """The runs of the evidence file as (test name, exit code). A run of several tests gives one entry per test."""
    path = evidence_path(plan, step_id)
    runs = []
    names = None
    header = False
    for line in read(path).split("\n") if path.exists() else []:
        if line == "=== run":
            header, names = True, None
        elif line == "output:":
            header = False
        elif header and line.startswith("name: "):
            names = line[6:].split()
        elif header and line.startswith("exit: ") and names is not None:
            runs += [(name, int(line[6:])) for name in names]
    return runs


def log_path():
    folder = Path(tempfile.gettempdir()) / "ai-setup-test"
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    return folder / f"{stamp}.log"


def report_cases(path):
    """The test cases of a report file in the JUnit XML format as (name, failed, output)."""
    cases = []
    for case in ElementTree.parse(path).getroot().iter("testcase"):
        name = " ".join(part for part in (case.get("classname"), case.get("name")) if part)
        if case.find("skipped") is not None:
            continue
        failures = [child for child in case if child.tag in ("failure", "error")]
        parts = []
        for child in failures + [child for child in case if child.tag in ("system-out", "system-err")]:
            parts += [child.get("message") or "", child.text or ""]
        cases.append((name, bool(failures), "\n".join(part.strip("\n") for part in parts if part.strip())))
    return cases


def tail(text, limit=FAILURE_LINES):
    lines = text.rstrip().split("\n")
    return "\n".join(lines[-limit:])


def summary(code, output, report, names, log):
    """The short result of a run for the agent, and the exit code. A passed run is one line. A failed run names each
    failed test with the end of its output. The full output is in `log`."""
    cases = None
    if report and (ROOT / report).is_file():
        try:
            cases = report_cases(ROOT / report)
        except ElementTree.ParseError:
            cases = None
    if cases is None:
        if code == 0:
            return 0, "passed"
        return code, f"failed, full output: {log}\n{tail(output)}"
    missing = [name for name in names if not any(name in case for case, _, _ in cases)]
    failed = [(name, text) for name, bad, text in cases if bad]
    passed = len(cases) - len(failed)
    if code == 0 and not failed and not missing:
        return 0, f"passed {passed}"
    lines = [f"passed {passed}, failed {len(failed)}, full output: {log}"]
    lines += [f"no test has the name {name}" for name in missing]
    for name, text in failed:
        lines += [f"--- failed: {name}", tail(text)]
    if not failed and not missing:
        lines.append(tail(output))
    return code or 1, "\n".join(lines)


def execute(kind, name="", plan=None, step_id=None):
    """Runs the suite, the named tests in one call of the runner, or a named command. `name` is one name or a list
    of test names. Returns the exit code and the short result."""
    project = load_project()
    names = [name] if isinstance(name, str) and name else list(name or [])
    report = project.get("test_report")
    if kind == "SUITE":
        commands, label = [project["test_suite"]], "suite"
    elif kind == "TEST":
        template, label = project["test_command"], " ".join(names)
        if "{names}" in template:
            commands = [template.replace("{names}", " ".join(names))]
        else:
            commands = [template.replace("{name}", item) for item in names]
    else:
        table = {**BUILTIN_COMMANDS, **project.get("commands", {})}
        if names[0] not in table:
            fail(f"tools/project.toml: the command '{names[0]}' is not in [commands]")
        commands, label, report = [table[names[0]]], names[0], None
    code, results, outputs = 0, [], []
    for index, command in enumerate(commands):
        if report and (ROOT / report).is_file():
            os.remove(ROOT / report)
        run_code, output = shell(command)
        log = log_path()
        write(log, output)
        outputs.append(output)
        wanted = names if len(commands) == 1 else names[index : index + 1]
        run_code, text = summary(run_code, output, report, wanted if kind == "TEST" else [], log)
        code = code or run_code
        results.append(text)
    if step_id:
        append_evidence(plan, step_id, label, " && ".join(commands), code, "\n".join(outputs))
    return code, "\n".join(results)


def changed_tests(base):
    """The names of the test files that changed or came since the commit `base`, committed or not. A test file lies
    in a test folder of a language of the project, in a folder named `tests`, and is no shared module."""
    project = load_project()
    changed = set(git("diff", "--name-only", base).splitlines())
    changed |= set(git("ls-files", "--others", "--exclude-standard").splitlines())
    names = []
    for path in sorted(changed):
        parts = path.split("/")
        stem, dot, extension = parts[-1].rpartition(".")
        if "tests" not in parts[:-1] or not dot or stem in ("mod", "common", "lib", "main"):
            continue
        for language in project.get("language", []):
            folders = language.get("tests", [])
            extensions = language.get("extensions", [])
            if f".{extension}" in extensions and any(path.startswith(folder.rstrip("/") + "/") for folder in folders):
                names.append(stem)
                break
    return names


def run(args):
    step_id = take_option(args, "--step")
    named_command = "--command" in args
    names = [arg for arg in args if arg != "--command"]
    if named_command and len(names) != 1:
        fail("usage: python -m tools.test [<name> ...] [--step <step>] | <name> --command [--step <step>]")
    plan = None
    if step_id:
        plan = require_plan()
        state = progress_row(plan, step_id)["State"]
        if state != "in progress":
            fail(f"step {step_id} has state {state}. Evidence is written for a step in progress only")
    kind = "SUITE" if not names else "COMMAND" if named_command else "TEST"
    code, output = execute(kind, names, plan, step_id)
    print(output)
    print(f"exit: {code}")
    return code


if __name__ == "__main__":
    main(run)
