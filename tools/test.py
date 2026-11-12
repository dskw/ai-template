import datetime

from tools._lib import fail, git, load_project, main, progress_row, read, require_plan, run as shell, take_option, write


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


def evidence_runs(plan, step_id):
    path = evidence_path(plan, step_id)
    runs = []
    name = None
    header = False
    for line in read(path).split("\n") if path.exists() else []:
        if line == "=== run":
            header, name = True, None
        elif line == "output:":
            header = False
        elif header and line.startswith("name: "):
            name = line[6:]
        elif header and line.startswith("exit: ") and name is not None:
            runs.append((name, int(line[6:])))
    return runs


def execute(kind, name="", plan=None, step_id=None):
    project = load_project()
    if kind == "SUITE":
        command, name = project["test_suite"], "suite"
    elif kind == "TEST":
        command = project["test_command"].replace("{name}", name)
    else:
        commands = project.get("commands", {})
        if name not in commands:
            fail(f"tools/project.toml: the command '{name}' is not in [commands]")
        command = commands[name]
    code, output = shell(command)
    if step_id:
        append_evidence(plan, step_id, name, command, code, output)
    return code, output


def run(args):
    step_id = take_option(args, "--step")
    named_command = "--command" in args
    names = [arg for arg in args if arg != "--command"]
    if len(names) > 1 or (named_command and not names):
        fail("usage: python -m tools.test [<name>] [--command] [--step <step>]")
    plan = None
    if step_id:
        plan = require_plan()
        state = progress_row(plan, step_id)["State"]
        if state != "in progress":
            fail(f"step {step_id} has state {state}. Evidence is written for a step in progress only")
    kind = "SUITE" if not names else "COMMAND" if named_command else "TEST"
    code, output = execute(kind, names[0] if names else "", plan, step_id)
    print(output, end="")
    print(f"exit: {code}")
    return code


if __name__ == "__main__":
    main(run)
