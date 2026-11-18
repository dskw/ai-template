import copy
import re

from tools import project
from tools._lib import (
    BUG_ID,
    EXTENSION_HEADER,
    FEATURE_ID,
    MILESTONE_HEADER,
    MILESTONES,
    Fail,
    FEATURE_TYPES,
    Problems,
    active_plan,
    active_plans,
    all_steps,
    branch,
    commit,
    in_worktree,
    merged,
    require_main,
    worktree_path,
    expected_branch,
    fail,
    find_milestone,
    git,
    main,
    milestones,
    next_id,
    open_milestone,
    parse_check,
    plans,
    read,
    read_table,
    rel,
    require_branch,
    required_steps,
    run as shell,
    save_milestone,
    table_lines,
    words,
    write,
)

PROGRESS = MILESTONES / "PROGRESS.md"


def derive(milestone, all_plans):
    own = [
        plan
        for plan in all_plans
        if plan["meta"]["milestone"] == milestone["id"] and plan["meta"]["status"] != "draft" and plan["field"] == "features"
    ]
    for row in milestone["features"]:
        if row["State"] in ("dropped", "migrated"):
            continue
        references = [plan for plan in own if row["ID"] in plan["ids"]]
        row["Plans"] = " ".join(plan["id"] for plan in references)
        done = any(plan["archived"] and row["ID"] in plan["meta"]["done"] for plan in references)
        if done and all(plan["archived"] for plan in references):
            row["State"] = "done"
        else:
            row["State"] = "in progress" if references else "open"


def progress_text(all_milestones):
    # a draft counts from its first commit on, so the table never names a file that the repository does not hold
    tracked = set(git("ls-files", "--", rel(MILESTONES)).splitlines())
    rows = []
    for milestone in all_milestones:
        if milestone["meta"]["status"] == "draft" and milestone["rel"] not in tracked:
            continue
        rows.append(
            {
                "Milestone": f"{milestone['id']} {milestone['name']}",
                "Features": str(len(milestone["features"])),
                "Done": str(sum(row["State"] == "done" for row in milestone["features"])),
                "Bugs": str(len(milestone["bugs"])),
                "Status": milestone["meta"]["status"],
            }
        )
    return "\n".join(table_lines(MILESTONE_HEADER, rows)) + "\n"


def regenerate():
    # the tables of the milestone belong to the main repository; a worktree of a plan never writes them
    if in_worktree():
        return
    all_milestones = milestones()
    all_plans = plans()
    for milestone in all_milestones:
        if milestone["meta"]["status"] == "draft":
            continue
        before = copy.deepcopy(milestone["features"])
        derive(milestone, all_plans)
        if before != milestone["features"]:
            save_milestone(milestone)
    text = progress_text(all_milestones)
    if not PROGRESS.exists() or read(PROGRESS) != text:
        write(PROGRESS, text)


def withdrawn(plan):
    problems = Problems(plan)
    result = set()
    for record in problems.records:
        if record["type"] == "bug verified withdrawn":
            result.add(record["ids"][0])
    return result


def check_errors():
    try:
        all_milestones = milestones()
        all_plans = plans()
    except Fail as error:
        return [str(error)]
    errors = []
    tracked = set(git("ls-files").splitlines())
    by_id = {milestone["id"]: milestone for milestone in all_milestones}
    opened = [m["id"] for m in all_milestones if m["meta"]["status"] == "open"]
    if len(opened) > 1:
        errors.append("two milestone files have status open: " + " ".join(opened))
    for milestone in all_milestones:
        name, status = milestone["rel"], milestone["meta"]["status"]
        if milestone["archived"] and status != "closed":
            errors.append(f"{name}: an archived milestone has status {status}")
        if not milestone["archived"] and status == "closed":
            errors.append(f"{name}: a closed milestone is not in archive/")
        if status == "closed" and milestone["bugs"]:
            errors.append(f"{name}: a closed milestone has a Bugs table with rows")
        for row in milestone["features"]:
            if row["State"] == "migrated":
                match = re.fullmatch(r"(M\d{3})-(F\d{2})", row["Plans"])
                target = by_id.get(match.group(1)) if match else None
                if not target or match.group(2) not in [item["ID"] for item in target["features"]]:
                    errors.append(f"{name}: {row['ID']} is migrated to an unknown feature '{row['Plans']}'")
    for plan in all_plans:
        name, status = f"{plan['rel']}/plan.md", plan["meta"]["status"]
        if status == "draft":
            if name in tracked:
                errors.append(f"{name}: a committed plan file has status draft")
            continue
        if plan["archived"] and status != "closed":
            errors.append(f"{name}: an archived plan has status {status}")
        if not plan["archived"] and status == "closed":
            errors.append(f"{name}: a closed plan is not in archive/")
        milestone = by_id.get(plan["meta"]["milestone"])
        if not milestone:
            errors.append(f"{name}: milestone {plan['meta']['milestone']} does not exist")
            continue
        if milestone["meta"]["status"] == "draft":
            errors.append(f"{name}: the milestone {milestone['id']} is a draft, only the open milestone has plans")
        pattern = FEATURE_ID if plan["field"] == "features" else BUG_ID
        for item in plan["ids"]:
            if not pattern.match(item):
                errors.append(f"{name}: a {plan['meta']['type']} plan references the id {item}")
        if plan["field"] == "features":
            known = {row["ID"] for row in milestone["features"]}
        elif plan["archived"]:
            known = set(plan["ids"])
        else:
            known = {row["ID"] for row in milestone["bugs"]} | set(plan["meta"]["done"]) | withdrawn(plan)
        for item in plan["ids"]:
            if item not in known:
                errors.append(f"{name}: the id {item} is not in the tables of {milestone['id']}")
        for row in plan["progress"]:
            if row["State"] == "complete" and not (row["Evidence"] and (plan["dir"] / row["Evidence"]).is_file()):
                errors.append(f"{plan['rel']}/progress.md: the complete step {row['Step']} has no evidence file")
    if errors:
        return errors
    for milestone in all_milestones:
        if milestone["meta"]["status"] == "draft":
            continue
        before = copy.deepcopy(milestone["features"])
        derive(milestone, all_plans)
        if before != milestone["features"]:
            errors.append(f"{milestone['rel']}: the feature table is stale, run python -m tools.progress")
    if not PROGRESS.exists() or read(PROGRESS) != progress_text(all_milestones):
        errors.append("docs/milestones/PROGRESS.md is stale, run python -m tools.progress")
    return errors


def undecided(plan):
    path = plan["dir"] / "extensions.md"
    rows = read_table(read(path), None, EXTENSION_HEADER, rel(path))
    return [row["ID"] for row in rows if not row["Decision"]]


def next_step(plan, milestone):
    required = [step["Step"] for step in required_steps(plan, milestone)]
    rows = [row for row in plan["progress"] if row["Step"] in required]
    for state in ("in progress", "open"):
        for row in rows:
            if row["State"] == state:
                return row["Step"]
    return None


def status():
    if project.errors():
        print("not initialized, run project-init")
        return
    if branch() != expected_branch():
        print(f"wrong branch {branch() or 'detached HEAD'}, check out {expected_branch()}")
        return
    milestone = open_milestone()
    if not in_worktree():
        return main_status(milestone)
    plan = active_plan()
    if not plan:
        print(f"the branch {branch()} has no active plan, work in the main repository")
        return
    print(f"plan {plan['id']}: {plan['meta']['status']}")
    problems = Problems(plan)
    blocked = [row["Step"] for row in plan["progress"] if row["State"] == "blocked"]
    for step_id in blocked:
        record = problems.last(("step blocked",), step_id)
        print(f"blocked step {step_id}: open problems {' '.join(record['ids'][1:]) if record else ''}")
    if plan["meta"]["status"] == "blocked" and not blocked:
        record = problems.last(("plan blocked",))
        print(f"blocked plan: open problems {' '.join(record['ids']) if record else ''}")
    if plan["meta"]["status"] == "in progress":
        step_id = next_step(plan, milestone)
        if step_id:
            step = next(step for step in all_steps(plan) if step["Step"] == step_id)
            print(f"next step {step_id} {step['Feature']}: {step['Text']}")
        else:
            print("no open step, run plan-close")
    print(f"undecided extensions: {len(undecided(plan))}")


def main_status(milestone):
    """The status of the main repository: each active plan with its worktree, and the features and bugs that no
    active plan holds."""
    found = active_plans()
    for plan in found:
        if merged(plan["id"]):
            print(f"plan {plan['id']}: in close, run plan-close")
        else:
            print(f"plan {plan['id']}: {plan['meta']['status']} in the worktree {worktree_path(plan['id'])}")
    if not found:
        print("no active plan")
    if len(found) > 1:
        print("each agent starts in the worktree of its plan: change the directory right before each agent start")
    open_status(milestone, found)
    for draft in milestones():
        if draft["meta"]["status"] == "draft" and not draft["archived"]:
            print(f"draft milestone {draft['id']} {draft['name']}")


def open_status(milestone, found):
    if not milestone:
        print("no open milestone")
        return
    held = {item for plan in found for item in plan["ids"]}
    features = [row["ID"] for row in milestone["features"] if row["State"] in ("open", "in progress") and row["ID"] not in held]
    bugs = [row["ID"] for row in milestone["bugs"] if row["ID"] not in held]
    if features:
        print(f"milestone {milestone['id']}: open features {' '.join(features)}")
        if bugs:
            print(f"milestone {milestone['id']}: open bugs {' '.join(bugs)}")
    elif bugs and not any(row["State"] in ("open", "in progress") for row in milestone["features"]):
        print(f"bugfix phase: {' '.join(bugs)}")
    elif bugs:
        print(f"milestone {milestone['id']}: open bugs {' '.join(bugs)}")
    elif not found:
        print(f"milestone {milestone['id']}: no open feature and no bug, run milestone-close")


def check_text(text, limit, name):
    if not 1 <= words(text) <= limit:
        fail(f"{name} must have 1 to {limit} words")
    if "|" in text or "\n" in text:
        fail(f"{name} must be one line without '|'")


def add_feature(milestone_id, kind, text, acceptance):
    require_main()
    milestone = find_milestone(milestone_id)
    if milestone["meta"]["status"] == "closed":
        fail(f"milestone {milestone_id} is closed")
    if kind not in FEATURE_TYPES:
        fail("the type must be new, update or refactor")
    check_text(text, 12, "the feature text")
    if not parse_check(acceptance):
        fail("the acceptance must be 'TEST <name> passes', 'COMMAND <name> passes' or 'MANUAL <name>'")
    feature_id = next_id("F", [row["ID"] for row in milestone["features"]])
    milestone["features"].append(
        {"ID": feature_id, "Feature": text, "Type": kind, "Acceptance": acceptance, "Plans": "", "State": "open"}
    )
    save_milestone(milestone)
    regenerate()
    commit(f"Feature added: {milestone_id} {feature_id}", [milestone["path"], PROGRESS], verify=False)
    print(f"added {milestone_id} {feature_id}")


def require_milestone():
    require_main()
    milestone = open_milestone()
    if not milestone:
        fail("no open milestone, run milestone-create")
    require_branch()
    return milestone


def section_span(lines, heading, name):
    if f"## {heading}" not in lines:
        fail(f"{name}: the section '## {heading}' is missing")
    start = lines.index(f"## {heading}") + 1
    end = next((index for index in range(start, len(lines)) if lines[index].startswith("## ")), len(lines))
    return start, end


def replace_section(milestone, heading, body):
    lines = milestone["text"].split("\n")
    start, end = section_span(lines, heading, milestone["rel"])
    tail = lines[end:]
    lines = lines[:start] + body + ([""] if tail else []) + tail
    milestone["text"] = "\n".join(lines).rstrip("\n") + "\n"
    save_milestone(milestone)
    commit(f"Milestone updated: {milestone['id']}", [milestone["path"]])


def set_goal(text):
    milestone = require_milestone()
    check_text(text, 60, "the goal")
    replace_section(milestone, "Goal", [text])
    print(f"goal set {milestone['id']}")


def out_of_scope(action, item):
    milestone = require_milestone()
    check_text(item, 20, "the item")
    lines = milestone["text"].split("\n")
    start, end = section_span(lines, "Out of scope", milestone["rel"])
    items = [line[2:] for line in lines[start:end] if line.startswith("- ")]
    if action == "add":
        if item in items:
            fail(f"'{item}' is already out of scope")
        items.append(item)
    else:
        if item not in items:
            fail(f"'{item}' is not in the out of scope list of {milestone['id']}")
        items.remove(item)
    replace_section(milestone, "Out of scope", [f"- {entry}" for entry in items])
    print(f"out of scope {action} {milestone['id']}")


def drop_feature(feature_id, reason):
    milestone = require_milestone()
    check_text(reason, 12, "the reason")
    for row in milestone["features"]:
        if row["ID"] == feature_id:
            if row["State"] not in ("open", "in progress"):
                fail(f"{feature_id} has state {row['State']}")
            row["State"], row["Acceptance"] = "dropped", reason
            save_milestone(milestone)
            regenerate()
            commit(f"Feature dropped: {milestone['id']} {feature_id} {reason}", [milestone["path"], PROGRESS], verify=False)
            print(f"dropped {milestone['id']} {feature_id}")
            return
    fail(f"{feature_id} is not in the feature table of {milestone['id']}")


def bug_errors(milestone, row, all_milestones):
    errors = []
    if not 1 <= words(row["Bug"]) <= 12:
        errors.append(f"{row['ID']}: the bug text must have 1 to 12 words")
    feature = row["Feature"]
    if feature:
        match = re.fullmatch(r"(?:(M\d{3})-)?(F\d{2})", feature)
        owner = None
        if match:
            owner = next((m for m in all_milestones if m["id"] == (match.group(1) or milestone["id"])), None)
        if not owner or match.group(2) not in [item["ID"] for item in owner["features"]]:
            errors.append(f"{row['ID']}: the feature '{feature}' does not exist")
    source = row["Source"]
    match = re.fullmatch(r"(M\d{3}-P\d{3}) N\d{2}", source)
    if source != "user" and not (match and match.group(1) in [plan["id"] for plan in plans()]):
        errors.append(f"{row['ID']}: the source must be 'user' or a plan id with a problem id")
    if not parse_check(row["Acceptance"]):
        errors.append(f"{row['ID']}: the acceptance must be 'TEST <name> passes', 'COMMAND <name> passes' or 'MANUAL <name>'")
    return errors


def next_bug_id(milestone):
    used = [row["ID"] for row in milestone["bugs"]]
    for plan in plans():
        if plan["meta"]["milestone"] == milestone["id"] and plan["field"] == "bugs":
            used += plan["ids"]
    code, output = shell(["git", "log", "--all", "--format=%s", f"--grep=^Bug reported: {milestone['id']} B"])
    if code == 0:
        used += re.findall(r"B\d{2}$", output, re.M)
    return next_id("B", used)


def add_bug(text, feature, source, acceptance):
    milestone = require_milestone()
    row = {"ID": next_bug_id(milestone), "Bug": text, "Feature": feature, "Source": source, "Acceptance": acceptance}
    if any("|" in value for value in row.values()):
        fail("a cell must not hold '|'")
    errors = bug_errors(milestone, row, milestones())
    if errors:
        fail("\n".join(errors))
    milestone["bugs"].append(row)
    save_milestone(milestone)
    regenerate()
    commit(f"Bug reported: {milestone['id']} {row['ID']}", [milestone["path"], PROGRESS])
    print(f"reported {milestone['id']} {row['ID']}")


def remove_bug(milestone, bug_id):
    rows = [row for row in milestone["bugs"] if row["ID"] == bug_id]
    if not rows:
        fail(f"{bug_id} is not in the Bugs table of {milestone['id']}")
    milestone["bugs"].remove(rows[0])
    save_milestone(milestone)
    return rows[0]


def drop_bug(bug_id, reason):
    milestone = require_milestone()
    check_text(reason, 12, "the reason")
    remove_bug(milestone, bug_id)
    paths = [milestone["path"], PROGRESS]
    # the plan in close holds its folder in this work tree; a plan in a worktree records the drop at its next sync
    plan = active_plan()
    if plan and bug_id in plan["ids"] and bug_id not in plan["meta"]["done"] and bug_id not in withdrawn(plan):
        problems = Problems(plan)
        problems.record("bug verified withdrawn", bug_id)
        problems.save()
        paths.append(problems.path)
    regenerate()
    commit(f"Bug dropped: {milestone['id']} {bug_id} {reason}", paths)
    print(f"dropped {milestone['id']} {bug_id}")


def run(args):
    command = args[0] if args else ""
    rest = args[1:]
    if command == "":
        regenerate()
        errors = check_errors()
        if errors:
            fail("\n".join(errors))
        print("progress ok")
    elif command == "check":
        errors = check_errors()
        if errors:
            fail("\n".join(errors))
        print("progress ok")
    elif command == "status":
        status()
    elif command == "add-feature" and len(rest) == 4:
        add_feature(*rest)
    elif command == "drop-feature" and len(rest) == 2:
        drop_feature(*rest)
    elif command == "set-goal" and len(rest) == 1:
        set_goal(rest[0])
    elif command == "out-of-scope" and len(rest) == 2 and rest[0] in ("add", "remove"):
        out_of_scope(*rest)
    elif command == "add-bug" and len(rest) == 4:
        add_bug(*rest)
    elif command == "fix-bug" and len(rest) == 1:
        from tools import plan_close

        plan_close.fix_one(rest[0])
    elif command == "drop-bug" and len(rest) == 2:
        drop_bug(*rest)
    else:
        fail(
            "usage: python -m tools.progress [check | status"
            ' | add-feature <milestone> <new|update|refactor> "<text>" "<acceptance>"'
            ' | drop-feature <feature> "<reason>"'
            ' | set-goal "<text>" | out-of-scope <add|remove> "<item>"'
            ' | add-bug "<text>" "<feature or empty>" "<source>" "<acceptance>"'
            ' | fix-bug <bug> | drop-bug <bug> "<reason>"]'
        )


if __name__ == "__main__":
    main(run)
