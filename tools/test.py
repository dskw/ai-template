import datetime
import os
import re
import subprocess
import xml.etree.ElementTree as ElementTree
from pathlib import Path

from tools._lib import (
    LOG_FOLDER,
    ROOT,
    active_plan,
    any_match,
    clean_tree,
    command_table,
    commit,
    fail,
    git,
    in_worktree,
    load_project,
    main,
    milestone_logs,
    parse_check,
    progress_row,
    read,
    require_plan,
    run as shell,
    take_option,
    unclean,
    write,
)

# the lines of output that the tool prints per failed test, and for a failed run without a report file
FAILURE_LINES = 60


def evidence_path(plan, step_id):
    return plan["dir"] / "evidence" / f"{step_id}-test.txt"


def append_evidence(plan, step_id, name, command, code, output, extra=()):
    """Appends one run to the evidence of a step. `extra` holds further header lines, for example of a run that must
    fail."""
    path = evidence_path(plan, step_id)
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = "".join(f"{line}\n" for line in extra)
    block = (
        f"=== run\nname: {name}\ncommand: {command}\nhead: {git('rev-parse', '--short=12', 'HEAD')}\n{lines}"
        f"exit: {code}\ndate: {stamp}\noutput:\n{output.rstrip()}\n=== end\n"
    )
    write(path, (read(path) if path.exists() else "") + block)
    commit(f"Evidence: {plan['id']} {step_id}", [path], verify=False)


def evidence_runs(plan, step_id):
    """The runs of the evidence file as dicts with the test name, the exit code, whether the run had to fail and
    whether it counts. A run of several tests gives one entry per test."""
    path = evidence_path(plan, step_id)
    runs = []
    run = None
    for line in read(path).split("\n") if path.exists() else []:
        if line == "=== run":
            run = {"names": None, "expect": "pass", "counts": True}
        elif line == "output:" and run:
            runs += [{"name": name, "code": run["code"], "expect": run["expect"], "counts": run["counts"]} for name in run["names"] or [] if "code" in run]
            run = None
        elif run is not None and line.startswith("name: "):
            run["names"] = line[6:].split()
        elif run is not None and line.startswith("exit: "):
            run["code"] = int(line[6:])
        elif run is not None and line.startswith("expect: "):
            run["expect"] = line[8:]
        elif run is not None and line == "counts: no":
            run["counts"] = False
    return runs


def failed_before_passed(plan, step_id, name):
    """Whether the evidence of a step shows a counted run of the test `name` that had to fail and failed, before a
    passing run, as a bug fix needs it."""
    runs = [run for run in evidence_runs(plan, step_id) if run["name"] == name]
    failed = next((index for index, run in enumerate(runs) if run["expect"] == "fail" and run["counts"] and run["code"] != 0), None)
    return failed is not None and any(run["expect"] == "pass" and run["code"] == 0 for run in runs[failed + 1 :])


def log_path(plan=None):
    """A new log file: in the temporary folder of the plan of this worktree, else in that of the milestones."""
    plan = plan or (active_plan() if in_worktree() else None)
    folder = plan["dir"] / "tmp" / LOG_FOLDER if plan and in_worktree() else milestone_logs()
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    return folder / f"{stamp}.log"


def end_tree(pid):
    """Ends a process and each process that it started."""
    import psutil

    try:
        parent = psutil.Process(pid)
        tree = parent.children(recursive=True) + [parent]
    except psutil.NoSuchProcess:
        return
    for process in tree:
        try:
            process.kill()
        except psutil.NoSuchProcess:
            pass
    psutil.wait_procs(tree, timeout=10)


def run_limited(command, limit):
    """Runs a command line with a time limit in seconds. On the limit and on each early stop it ends the whole process
    tree. Returns the exit code, the output and whether the run hung."""
    process = subprocess.Popen(command, cwd=ROOT, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    hung = False
    try:
        output, _ = process.communicate(timeout=limit)
    except subprocess.TimeoutExpired:
        hung = True
        end_tree(process.pid)
        output, _ = process.communicate()
    except BaseException:
        end_tree(process.pid)
        raise
    text = output.decode("utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")
    return (process.returncode or 1) if hung else process.returncode, text, hung


def end_leftovers(patterns):
    """Ends the test processes of this repository that still run, for example after a run whose tool was stopped.
    A test process runs an executable that matches a glob of `test_binaries`. Returns one line per ended process."""
    import psutil

    if not patterns:
        return []
    lines = []
    root = Path(ROOT).resolve()
    for process in psutil.process_iter(["pid", "exe"]):
        exe = process.info.get("exe")
        if not exe or process.pid == os.getpid():
            continue
        try:
            name = Path(exe).resolve().relative_to(root).as_posix()
        except ValueError:
            continue
        if any_match(name, patterns):
            end_tree(process.pid)
            lines.append(f"ended the leftover test process {process.pid} {name}")
    return lines


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


# a test runs this many times in all when it failed: the first run and the runs alone after it
RUNS = 4
# a run with more failed tests than this runs no test again: so many failures have a shared cause
RERUN_LIMIT = 5
# a run up to this many tests names each test in the output; a larger run names them in its log
LISTED = 30


def matches(case, name, contains=False):
    """Whether a test case has the name: one whole part of its name, or any part of it with `contains`."""
    if contains:
        return name in case
    return re.search(rf"(?:^|[\s:./]){re.escape(name)}(?:$|[\s:./])", case) is not None


def read_cases(report):
    if not report or not (ROOT / report).is_file():
        return None
    try:
        return report_cases(ROOT / report)
    except ElementTree.ParseError:
        return None


def run_once(command, project, plan):
    """One run of a command line with a fresh report. Returns the exit code, the output, the log, the cases of the
    report or None, and whether the run hung."""
    report = project.get("test_report")
    if report and (ROOT / report).is_file():
        os.remove(ROOT / report)
    ended = end_leftovers(project.get("test_binaries", []))
    code, output, hung = run_limited(command, project["test_run_limit"])
    output = "".join(line + "\n" for line in ended) + output
    log = log_path(plan)
    write(log, output)
    return code, output, log, read_cases(report), hung


def rerun(case, project, plan):
    """Runs one failed test alone `RUNS - 1` more times. Returns the count of failed runs and the logs."""
    short = re.split(r"[\s:./]+", case)[-1]
    template = project["test_command"]
    command = template.replace("{names}", short).replace("{name}", short)
    failed, logs = 0, []
    for _ in range(RUNS - 1):
        code, output, log, cases, hung = run_once(command, project, plan)
        logs.append(str(log))
        found = [bad for name, bad, _ in cases or [] if name == case]
        failed += 1 if hung or not found or found[0] else 0
    return failed, logs


def summary(code, output, cases, names, log, project, plan, contains=False, hung=False):
    """The short result of a run for the agent, and the exit code. It names each test that ran. A failed test runs
    alone again, so the result tells a steady defect from a test without a fixed result. A hang is a failure."""
    if hung:
        limit = project["test_run_limit"]
        return code, f"hang: the run reached the time limit of {limit} seconds and its processes were ended, full output: {log}\n{tail(output)}"
    if cases is None:
        if code == 0:
            return 0, "passed"
        return code, f"failed, full output: {log}\n{tail(output)}"
    counted = [item for item in cases if not names or any(matches(item[0], name, contains) for name in names)]
    extra = [item[0] for item in cases if item not in counted]
    missing = [name for name in names if not any(matches(case, name, contains) for case, _, _ in cases)]
    failed = [(case, text) for case, bad, text in counted if bad]
    ran = [case for case, _, _ in counted]
    lines = [f"ran {len(ran)}: {', '.join(ran)}" if len(ran) <= LISTED else f"ran {len(ran)}, each named in {log}"]
    if len(ran) > LISTED:
        write(log, read(log) + "\nTests that ran:\n" + "\n".join(ran) + "\n")
    if extra:
        lines.append(f"also ran, not counted: {', '.join(extra[:LISTED])}")
    explained = any(bad for case, bad, _ in cases if case in extra)
    if not failed and not missing and (code == 0 or explained):
        return 0, "\n".join([f"passed {len(ran)}"] + lines)
    if not failed and not missing:
        return code, "\n".join([f"failed with exit code {code} and no failed test, full output: {log}"] + lines + [tail(output)])
    lines.insert(0, f"passed {len(ran) - len(failed)}, failed {len(failed)}, full output: {log}")
    lines += [f"no test has the name {name}" for name in missing]
    if len(failed) > RERUN_LIMIT:
        lines.append(f"{len(failed)} tests failed, so no test runs again: look for a shared cause")
    for case, text in failed:
        if len(failed) > RERUN_LIMIT:
            lines += [f"--- failed: {case}", tail(text)]
            continue
        count, logs = rerun(case, project, plan)
        if count == RUNS - 1:
            lines.append(f"--- fails each time: {case}. A steady defect")
        else:
            lines.append(
                f"--- fails in {count + 1} of {RUNS} runs: {case}. The test has no fixed result: the cause lies in the"
                f" timeline or the order of the test. Logs: {log} {' '.join(logs)}"
            )
        lines.append(tail(text))
    return 1, "\n".join(lines)


def fails_as_expected(cases, name, contains):
    """Whether a run that must fail counts: the build passed, the test ran and it failed."""
    found = [bad for case, bad, _ in cases or [] if matches(case, name, contains)]
    if cases is None or not found:
        return False, "no failing run: the build failed or no test has the name"
    if not any(found):
        return False, "no failing run: the test passed"
    return True, "failed as it must"


def execute(kind, name="", plan=None, step_id=None, contains=False, must_fail=False, mutation=None):
    """Runs the suite, the named tests in one call of the runner, or a named command. `name` is one name or a list
    of test names. A run that must fail counts only when the build passes and the test fails. Returns the exit code and
    the short result."""
    project = load_project()
    names = [name] if isinstance(name, str) and name else list(name or [])
    if kind == "SUITE":
        commands, label = [project["test_suite"]], "suite"
    elif kind == "TEST":
        template, label = project["test_command"], " ".join(names)
        if "{names}" in template:
            commands = [template.replace("{names}", " ".join(names))]
        else:
            commands = [template.replace("{name}", item) for item in names]
    else:
        table = command_table()
        if names[0] not in table:
            fail(f"tools/project.toml: the command '{names[0]}' is not in [commands]")
        commands, label = [table[names[0]]], names[0]
    code, outputs, cases, hung = 0, [], [], False
    for command in commands:
        run_code, output, log, found, stuck = run_once(command, project, plan)
        code, hung = code or run_code, hung or stuck
        outputs.append(output)
        cases = None if found is None or cases is None else cases + found
    output, command = "\n".join(outputs), " && ".join(commands)
    wanted = names if kind == "TEST" else []
    extra = []
    if must_fail:
        counts, text = fails_as_expected(None if hung else cases, names[0], contains)
        extra = ["expect: fail"] + ([] if counts else ["counts: no"]) + ([f"mutation: {mutation}"] if mutation else [])
        evidence_code = 1 if counts else 0
        code, text = (0 if counts else 1), f"{text}, full output: {log}"
    else:
        code, text = summary(code, output, cases, wanted, log, project, plan, contains, hung)
        evidence_code = code
    if step_id:
        append_evidence(plan, step_id, label, command, evidence_code, output, extra)
    return code, text


def mutate(name, patch, plan, step_id, contains):
    """Runs a test as a run that must fail on the tree with a patch, then takes the patch back. The work tree is clean
    before and after."""
    if not clean_tree():
        fail(unclean())
    if not Path(patch).is_file():
        fail(f"the patch {patch} does not exist")
    code, output = shell(["git", "apply", "--check", patch])
    if code != 0:
        fail(f"the patch {patch} does not apply:\n{output}")
    git("apply", patch)
    try:
        return execute("TEST", name, plan, step_id, contains, True, patch)
    finally:
        code, output = shell(["git", "apply", "-R", patch])
        if code != 0 or not clean_tree():
            fail(f"the patch {patch} did not go back cleanly, restore the files by hand:\n{output}")


def changed_tests(base):
    """The names of the test files that changed or came since the commit `base`, committed or not. A test file lies
    in a test folder of a language of the project, in a folder named `tests`, outside the test support folder, and is
    no shared module."""
    project = load_project()
    support = str(project.get("test_support", "")).strip("/")
    changed = set(git("diff", "--name-only", "--diff-filter=d", base).splitlines())
    changed |= set(git("ls-files", "--others", "--exclude-standard").splitlines())
    names = []
    for path in sorted(changed):
        parts = path.split("/")
        stem, dot, extension = parts[-1].rpartition(".")
        if "tests" not in parts[:-1] or not dot or stem in ("mod", "common", "lib", "main"):
            continue
        if support and path.startswith(support + "/"):
            continue
        for language in project.get("language", []):
            folders = language.get("tests", [])
            extensions = language.get("extensions", [])
            if f".{extension}" in extensions and any(path.startswith(folder.rstrip("/") + "/") for folder in folders):
                names.append(stem)
                break
    return names


USAGE = (
    'usage: python -m tools.test [<name or "TEST <name> passes"> ...] [--contains] [--step <step>]'
    ' | "COMMAND <name> passes" [--step <step>] | <name> --fails [--step <step>] | <name> --mutation <patch> [--step <step>]'
)


def kind_and_names(args):
    """The kind of a run and its names. A check line of a plan gives its kind; a bare name is a test."""
    if not args:
        return "SUITE", []
    checks = [parse_check(arg) or ("TEST", arg) for arg in args]
    if any(kind == "MANUAL" for kind, _ in checks):
        fail("a MANUAL check runs through the step gate or the plan close, not through the test tool")
    if any(kind == "COMMAND" for kind, _ in checks):
        if len(checks) != 1:
            fail("a COMMAND check runs alone\n" + USAGE)
        return "COMMAND", [checks[0][1]]
    return "TEST", [name for _, name in checks]


def run(args):
    step_id = take_option(args, "--step")
    patch = take_option(args, "--mutation")
    must_fail = "--fails" in args or patch is not None
    contains = "--contains" in args
    kind, names = kind_and_names([arg for arg in args if arg not in ("--fails", "--contains")])
    if must_fail and (kind != "TEST" or len(names) != 1):
        fail("a run that must fail takes one test\n" + USAGE)
    if must_fail and not load_project().get("test_report"):
        fail("a run that must fail needs test_report in tools/project.toml, so the tool can tell a failed test from a failed build")
    plan = None
    if step_id:
        plan = require_plan()
        state = progress_row(plan, step_id)["State"]
        if state != "in progress":
            fail(f"step {step_id} has state {state}. Evidence is written for a step in progress only")
    if patch:
        code, output = mutate(names, patch, plan, step_id, contains)
    else:
        code, output = execute(kind, names, plan, step_id, contains, must_fail)
    print(output)
    print(f"exit: {code}")
    return code


if __name__ == "__main__":
    main(run)
