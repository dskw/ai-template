from tools import progress
from tools._lib import (
    BUG_ID,
    EXTENSION_HEADER,
    FEATURE_ID,
    PLAN_DIR,
    PLAN_TYPES,
    PLANS,
    PROBLEM_HEADER,
    active_plans,
    commit,
    dependency_errors,
    fail,
    git,
    git_ok,
    plan_branch,
    worktree_path,
    read,
    today,
    main,
    open_milestone,
    parse_check,
    plans,
    rel,
    require_branch,
    require_main,
    save_plan,
    table_lines,
    words,
    write,
)
from tools.milestone_create import section

TEMPLATE = """---
id: {id}
milestone: {milestone}
type: {type}
{field}: []
done: []
status: draft
closed:
---
# {id} {title}

## Steps
| Step | Feature | Text | Verification | Dependencies |
|---|---|---|---|---|

## Fix steps
| Step | Feature | Problem | Text | Verification |
|---|---|---|---|---|

## Verification
"""


def skeleton(folder):
    if not (folder / "extensions.md").exists():
        write(folder / "extensions.md", "\n".join(table_lines(EXTENSION_HEADER, [])) + "\n")
    if not (folder / "problems.md").exists():
        table = "\n".join(table_lines(PROBLEM_HEADER, []))
        write(folder / "problems.md", f"## Problems\n{table}\n\n## Records\n")


def drafts():
    return [plan for plan in plans() if plan["meta"]["status"] == "draft" and not plan["archived"]]


def context():
    milestone = open_milestone()
    if not milestone:
        fail("no open milestone, run milestone-create")
    require_main()
    require_branch()
    return milestone


def start(kind, name):
    if kind not in PLAN_TYPES:
        fail("the type must be feature, fix or refactor")
    if not PLAN_DIR.match(f"M000-P000-{name}"):
        fail("the name must have lower case letters, digits and hyphens")
    milestone = context()
    if drafts():
        fail(f"a draft plan exists: {drafts()[0]['rel']}")
    numbers = [int(plan["id"][6:]) for plan in plans() if plan["meta"]["milestone"] == milestone["id"]]
    plan_id = f"{milestone['id']}-P{max(numbers, default=0) + 1:03d}"
    folder = PLANS / f"{plan_id}-{name}"
    field = "bugs" if kind == "fix" else "features"
    title = name.replace("-", " ").capitalize()
    write(folder / "plan.md", TEMPLATE.format(id=plan_id, milestone=milestone["id"], type=kind, field=field, title=title))
    skeleton(folder)
    print(f"draft: {rel(folder)}/plan.md")


def validate(plan, milestone):
    errors = []
    name = f"{plan['rel']}/plan.md"
    if plan["meta"]["milestone"] != milestone["id"]:
        errors.append(f"{name}: the plan must belong to the open milestone {milestone['id']}")
    if not plan["ids"]:
        errors.append(f"{name}: the field '{plan['field']}' is empty")
    if plan["field"] == "features":
        # a refactor plan holds refactor features only; a feature plan holds any feature, its refactor steps first
        refactor = plan["meta"]["type"] == "refactor"
        valid = {
            row["ID"]
            for row in milestone["features"]
            if row["State"] in ("open", "in progress") and (row["Type"] == "refactor" or not refactor)
        }
        pattern = FEATURE_ID
        label = "an open or in progress feature of the type refactor" if refactor else "an open or in progress feature"
    else:
        valid = {row["ID"] for row in milestone["bugs"]}
        pattern, label = BUG_ID, "a bug of the Bugs table"
    for item in plan["ids"]:
        if not pattern.match(item) or item not in valid:
            errors.append(f"{name}: {item} is not {label} of {milestone['id']}")
    for other in active_plans():
        held = [item for item in plan["ids"] if other["field"] == plan["field"] and item in other["ids"]]
        if other["id"] != plan["id"] and held:
            errors.append(f"{name}: the active plan {other['id']} holds {' '.join(held)}")
    if not plan["steps"]:
        errors.append(f"{name}: the Steps table is empty")
    if plan["fixes"]:
        errors.append(f"{name}: the Fix steps table must be empty")
    acceptance = {row["ID"]: row["Acceptance"] for row in milestone["bugs"]}
    for number, step in enumerate(plan["steps"], 1):
        if step["Step"] != f"S{number:02d}":
            errors.append(f"{name}: step row {number} must have the id S{number:02d}")
        if step["Feature"] not in plan["ids"]:
            errors.append(f"{name}: {step['Step']}: {step['Feature']} is not in the field '{plan['field']}'")
        if not 1 <= words(step["Text"]) <= 20:
            errors.append(f"{name}: {step['Step']}: the step text must have 1 to 20 words")
        if not parse_check(step["Verification"]):
            errors.append(f"{name}: {step['Step']}: the verification must be 'TEST <name> passes', 'COMMAND <name> passes' or 'MANUAL <name>'")
        elif plan["field"] == "bugs" and step["Verification"] != acceptance.get(step["Feature"]):
            errors.append(f"{name}: {step['Step']}: the verification must be the acceptance of {step['Feature']}")
        errors += dependency_errors(step["Dependencies"], f"{name}: {step['Step']}")
    if plan["field"] == "features":
        refactors = {row["ID"] for row in milestone["features"] if row["Type"] == "refactor"}
        other = next((step["Step"] for step in plan["steps"] if step["Feature"] not in refactors), None)
        for step in plan["steps"]:
            if other and step["Feature"] in refactors and step["Step"] > other:
                errors.append(f"{name}: {step['Step']}: the refactor step stands after the step {other} of a feature that is no refactor")
        # the steps of one feature extend the one test of that feature
        for item in plan["ids"]:
            tests = {
                check[1]
                for step in plan["steps"]
                if step["Feature"] == item and (check := parse_check(step["Verification"])) and check[0] == "TEST"
            }
            if len(tests) > 1:
                errors.append(f"{name}: {item} has the tests {', '.join(sorted(tests))}; its steps share one test")
    for item in plan["ids"]:
        count = sum(step["Feature"] == item for step in plan["steps"])
        if count == 0 or (plan["field"] == "bugs" and count != 1):
            errors.append(f"{name}: {item} needs {'one step' if plan['field'] == 'bugs' else 'a step'}")
    checks = [line[2:] for line in (section(plan["text"], "Verification") or "").split("\n") if line.startswith("- ")]
    if not checks or not all(parse_check(check) for check in checks):
        errors.append(f"{name}: the Verification section must list one check per line")
    return errors


def reviewed():
    """Records a document review round of the draft, so the review yield counts it."""
    found = drafts()
    if len(found) != 1:
        fail("one draft plan is expected")
    skeleton(found[0]["dir"])
    path = found[0]["dir"] / "problems.md"
    write(path, read(path).rstrip("\n") + f"\n- document reviewed {today()}\n")
    print("document review recorded")


def create():
    found = drafts()
    if len(found) != 1:
        fail("one draft plan folder is necessary, run python -m tools.plan_create start <feature|fix> <name>")
    plan = found[0]
    milestone = context()
    errors = validate(plan, milestone)
    if errors:
        fail("\n".join(errors))
    skeleton(plan["dir"])
    plan["progress"] = [
        {"Step": step["Step"], "Feature": step["Feature"], "State": "open", "Evidence": "", "Round": ""}
        for step in plan["steps"]
    ]
    plan["meta"]["status"] = "in progress"
    save_plan(plan)
    progress.regenerate()
    commit(f"Plan created: {plan['id']}")
    print(f"Plan created: {plan['id']}")
    worktree(plan["id"])


def worktree(plan_id):
    """Creates the branch and the worktree of a plan from the milestone branch, when they do not exist yet."""
    name, path = plan_branch(plan_id), worktree_path(plan_id)
    if not git_ok("rev-parse", "--verify", "--quiet", f"refs/heads/{name}"):
        git("branch", name)
    if not path.exists():
        git("worktree", "add", str(path), name)
    print(f"worktree: {path}")


def run(args):
    if args[:1] == ["start"] and len(args) == 3:
        start(args[1], args[2])
    elif args[:1] == ["worktree"] and len(args) == 2:
        require_main()
        if args[1] not in [plan["id"] for plan in active_plans()]:
            fail(f"{args[1]} is no active plan")
        worktree(args[1])
    elif args == ["reviewed"]:
        reviewed()
    elif args == ["commit"]:
        create()
    else:
        fail("usage: python -m tools.plan_create <start <feature|fix|refactor> <name> | reviewed | commit | worktree <plan>>")


if __name__ == "__main__":
    main(run)
