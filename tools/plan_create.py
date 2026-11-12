from tools import progress
from tools._lib import (
    BUG_ID,
    EXTENSION_HEADER,
    FEATURE_ID,
    PLAN_DIR,
    PLANS,
    PROBLEM_HEADER,
    active_plan,
    commit,
    fail,
    main,
    open_milestone,
    parse_check,
    plans,
    rel,
    require_branch,
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
| Step | Feature | Text | Verification |
|---|---|---|---|

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
    require_branch()
    if active_plan():
        fail(f"plan {active_plan()['id']} is active. One plan runs at a time")
    return milestone


def start(kind, name):
    if kind not in ("feature", "fix"):
        fail("the type must be feature or fix")
    if not PLAN_DIR.match(f"M000-P000-{name}"):
        fail("the name must have lower case letters, digits and hyphens")
    milestone = context()
    if drafts():
        fail(f"a draft plan exists: {drafts()[0]['rel']}")
    numbers = [int(plan["id"][6:]) for plan in plans() if plan["meta"]["milestone"] == milestone["id"]]
    plan_id = f"{milestone['id']}-P{max(numbers, default=0) + 1:03d}"
    folder = PLANS / f"{plan_id}-{name}"
    field = "features" if kind == "feature" else "bugs"
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
        valid = {row["ID"] for row in milestone["features"] if row["State"] in ("open", "in progress")}
        pattern, label = FEATURE_ID, "an open or in progress feature"
    else:
        valid = {row["ID"] for row in milestone["bugs"]}
        pattern, label = BUG_ID, "a bug of the Bugs table"
    for item in plan["ids"]:
        if not pattern.match(item) or item not in valid:
            errors.append(f"{name}: {item} is not {label} of {milestone['id']}")
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
    for item in plan["ids"]:
        count = sum(step["Feature"] == item for step in plan["steps"])
        if count == 0 or (plan["field"] == "bugs" and count != 1):
            errors.append(f"{name}: {item} needs {'one step' if plan['field'] == 'bugs' else 'a step'}")
    checks = [line[2:] for line in (section(plan["text"], "Verification") or "").split("\n") if line.startswith("- ")]
    if not checks or not all(parse_check(check) for check in checks):
        errors.append(f"{name}: the Verification section must list one check per line")
    return errors


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


def run(args):
    if args[:1] == ["start"] and len(args) == 3:
        start(args[1], args[2])
    elif args == ["commit"]:
        create()
    else:
        fail("usage: python -m tools.plan_create <start <feature|fix> <name> | commit>")


if __name__ == "__main__":
    main(run)
