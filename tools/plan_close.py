import collections
import datetime
import os
import re
import shutil

from tools import memory_lint, progress, test
from tools._lib import (
    PLANS,
    ROOT,
    Problems,
    approval_errors,
    ask,
    clean_tree,
    commit,
    dirty_files,
    fail,
    find_milestone,
    git,
    git_ok,
    has_commit,
    load_project,
    main,
    milestones,
    open_important,
    open_milestone,
    parse_check,
    plans,
    problem_errors,
    read,
    read_table,
    rel,
    require_branch,
    require_plan,
    required_steps,
    save_plan,
    subjects,
    take_option,
    today,
    tool,
    words,
    write,
    BUG_HEADER,
    EXTENSION_HEADER,
)
from tools.approve import close_base

CHANGELOG = ROOT / "CHANGELOG.md"
PLAN_HINT = "add a fix step with python -m tools.step_close add-fix <problem> <step>"
BOUNDARIES = ("fix added", "plan unblocked", "review passed")


def context():
    plan = require_plan()
    milestone = open_milestone()
    if not milestone or milestone["id"] != plan["meta"]["milestone"]:
        fail(f"the milestone of plan {plan['id']} is not open")
    require_branch()
    return plan, milestone, Problems(plan)


def open_steps(plan, milestone):
    required = {step["Step"] for step in required_steps(plan, milestone)}
    return [row["Step"] for row in plan["progress"] if row["Step"] in required and row["State"] != "complete"]


def target_row(plan, milestone, item):
    table = milestone["features"] if plan["field"] == "features" else milestone["bugs"]
    return next((row for row in table if row["ID"] == item), None)


def passes(acceptance, item, problems):
    kind, name = parse_check(acceptance)
    if kind == "MANUAL":
        record = problems.last(("manual passed", "manual failed"), item)
        return bool(record) and record["type"] == "manual passed"
    return test.execute(kind, name)[0] == 0


def check(args, answer):
    plan, milestone, problems = context()
    code = 0
    for item in plan["ids"]:
        row = target_row(plan, milestone, item)
        if not row or row.get("State") == "dropped" or (args and item not in args):
            continue
        kind, name = parse_check(row["Acceptance"])
        if kind == "MANUAL":
            if answer is None and not os.isatty(0):
                print(f"{item} MANUAL {name}: ask the user, then run python -m tools.plan_close check {item} --answer yes|no")
                code = 1
                continue
            passed = ask(f"Manual check {name} for {item}: did it pass?", answer)
            problems.record("manual passed" if passed else "manual failed", item)
        else:
            passed = test.execute(kind, name)[0] == 0
        print(f"{item} {row['Acceptance']}: {'pass' if passed else 'fail'}")
    problems.save()
    return code


def verify_bug(bug_id):
    plan, milestone, problems = context()
    row = target_row(plan, milestone, bug_id)
    if plan["field"] != "bugs" or bug_id not in plan["ids"] or not row:
        fail(f"{bug_id} is not an open bug of the fix plan {plan['id']}")
    kind, name = parse_check(row["Acceptance"])
    verified = passes(row["Acceptance"], bug_id, problems)
    if not verified:
        print(f"{bug_id}: the acceptance check '{row['Acceptance']}' does not pass")
    elif kind == "TEST":
        step = next(step for step in plan["steps"] if step["Feature"] == bug_id)
        exits = [code for label, code in test.evidence_runs(plan, step["Step"]) if label == name]
        failed = next((index for index, code in enumerate(exits) if code != 0), None)
        verified = failed is not None and 0 in exits[failed + 1 :]
        if not verified:
            print(f"{bug_id}: the evidence of {step['Step']} must show a failing run of {name} before a passing run")
    if not verified:
        return 1
    problems.record("bug verified", bug_id)
    problems.save()
    print(f"bug verified {bug_id}")


def tuning():
    plan, milestone, problems = context()
    fixed, closed = collections.Counter(), collections.Counter()
    for other in plans():
        if other["meta"]["status"] == "draft":
            continue
        for row in Problems(other).rows:
            if row["Answer"].startswith("fixed"):
                fixed[row["Rule"]] += 1
            if re.match(r"closed (wrong|intentional) ", row["Answer"]) and row["Check"] == "confirmed":
                closed[row["Rule"]] += 1
    print("rule: fixed, closed as wrong or intentional and confirmed")
    for rule in sorted(set(fixed) | set(closed)):
        print(f"{rule}: {fixed[rule]}, {closed[rule]}")
    for rule in sorted(rule for rule in closed if closed[rule] >= 2):
        print(f"tune {rule}: remove the failure pattern from docs/REVIEW.md, or add the intent to the conventions")
    for rule in sorted(rule for rule in fixed if fixed[rule] >= 3):
        print(f"tune {rule}: add a lint rule or a convention rule")
    if plan["field"] == "bugs":
        states = {f"{m['id']}-{row['ID']}": row["State"] for m in milestones() for row in m["features"]}
        for row in milestone["bugs"]:
            feature = row["Feature"] if "-" in row["Feature"] else f"{milestone['id']}-{row['Feature']}"
            if row["ID"] in plan["ids"] and row["Source"] == "user" and states.get(feature) == "done":
                print(f"tune {row['ID']}: add one line to docs/REVIEW.md that describes the failure '{row['Bug']}'")
    problems.record("tuning done")
    problems.save()


def reviewed():
    plan, milestone, problems = context()
    if open_steps(plan, milestone):
        fail("steps are not complete: " + " ".join(open_steps(plan, milestone)))
    count = problems.count_since("plan reviewed", BOUNDARIES)
    if count >= 2:
        fail(f"the round cap is 2: record the pass, or {PLAN_HINT}")
    problems.record("plan reviewed")
    problems.save()
    print(f"plan review round {count + 1}")


def review_passed():
    plan, milestone, problems = context()
    subject = f"Review passed: {plan['id']}"
    if subjects()[0][1] == subject and clean_tree():
        print(subject)
        return
    errors = [f"step {step_id} is not complete" for step_id in open_steps(plan, milestone)]
    last = problems.last(BOUNDARIES + ("plan reviewed",))
    if not last or last["type"] not in ("plan reviewed", "plan unblocked"):
        errors.append("the plan has no review of the current state, run review-plan")
    errors += problem_errors(problems.rows, PLAN_HINT)
    dirty = [name for name in dirty_files() if name != problems.rel]
    if dirty:
        errors.append("commit these changes before the review pass: " + " ".join(dirty))
    if errors:
        fail("review pass:\n" + "\n".join(errors))
    problems.record("review passed", git("rev-parse", "--short=12", "HEAD"))
    problems.save()
    commit(subject, [problems.path])
    print(subject)


def review_commit(plan):
    for commit_hash, subject in subjects():
        if subject == f"Review passed: {plan['id']}":
            return commit_hash
        if not re.match(r"^(Bug fixed|Version): ", subject):
            break
    fail("changed after review, run review-plan again")


def extension_errors(plan):
    path = plan["dir"] / "extensions.md"
    errors = []
    known = [milestone["id"] for milestone in milestones()]
    for row in read_table(read(path), None, EXTENSION_HEADER, rel(path)):
        if row["Decision"] == "feature" and row["Detail"] in known:
            continue
        if row["Decision"] == "dropped" and 1 <= words(row["Detail"]) <= 12:
            continue
        errors.append(f"{rel(path)}: {row['ID']} needs the decision 'feature' with a milestone id or 'dropped' with a reason of max 12 words")
    return errors


def gate(plan, milestone, problems):
    review = review_commit(plan)
    record = problems.last(("review passed",))
    parent = git("rev-parse", f"{review}~1")
    names = git("diff", "--name-only", f"{review}~1", review).splitlines()
    if not record or not parent.startswith(record["ids"][0]) or names != [problems.rel]:
        fail("changed after review, run review-plan again")
    errors = []
    if not clean_tree():
        errors.append("the work tree is not clean. Discard the changes of an interrupted close, then run again")
    errors += [f"step {step_id} is not complete" for step_id in open_steps(plan, milestone)]
    errors += problem_errors(problems.rows, PLAN_HINT)
    if not problems.last(("tuning done",)):
        errors.append("problems.md is not processed, run python -m tools.plan_close tuning")
    errors += extension_errors(plan)
    errors += approval_errors(plan, problems, "close", close_base(plan))
    errors += [f"memory lint: {error}" for error in memory_lint.errors(strict=True)]
    errors += progress.check_errors()
    if errors:
        fail("plan gate:\n" + "\n".join(errors))
    code, output = tool("check")
    if code != 0:
        fail(f"plan gate:\npython -m tools.check fails:\n{output}")
    code, output = test.execute("SUITE")
    if code != 0:
        fail(f"plan gate:\nthe test suite fails:\n{output}")
    return review


def current_version():
    text = git("show", "HEAD:CHANGELOG.md", check=False) if git_ok("cat-file", "-e", "HEAD:CHANGELOG.md") else ""
    match = re.search(r"^# (\d+)\.(\d+)\.(\d+) ", text, re.M)
    if match:
        return [int(part) for part in match.groups()], text
    return [int(part) for part in str(load_project()["start_version"]).split(".")], text


def fix_bug(plan, milestone, bug_id):
    plan["meta"]["done"].append(bug_id)
    save_plan(plan)
    progress.remove_bug(milestone, bug_id)
    progress.regenerate()
    commit(f"Bug fixed: {milestone['id']} {bug_id}")


def fix_one(bug_id):
    plan, milestone, problems = context()
    gate(plan, milestone, problems)
    record = problems.last(("bug verified", "bug verified withdrawn"), bug_id)
    row = target_row(plan, milestone, bug_id)
    if plan["field"] != "bugs" or not row or not record or record["type"] != "bug verified":
        fail(f"{bug_id} is not a verified bug of the fix plan {plan['id']}")
    if not passes(row["Acceptance"], bug_id, problems):
        fail(f"the acceptance check of {bug_id} does not pass")
    fix_bug(plan, milestone, bug_id)
    print(f"Bug fixed: {milestone['id']} {bug_id}")


def finish_archive():
    for plan in plans():
        if plan["archived"] and not has_commit(f"Plan closed: {plan['id']}"):
            progress.regenerate()
            commit(f"Plan closed: {plan['id']}")
            print(f"Plan closed: {plan['id']}")
            return True
    return False


def close():
    if finish_archive():
        return
    plan, milestone, problems = context()
    review = gate(plan, milestone, problems)
    done = plan["meta"]["done"]
    replanned = {r["ids"][1] for r in problems.records if r["type"] == "plan unblocked" and r["ids"][0] == "replan"}
    reviewed_bugs = read_table(git("show", f"{review}:{milestone['rel']}"), "Bugs", BUG_HEADER, milestone["rel"])
    for item in plan["ids"]:
        row = target_row(plan, milestone, item)
        if item in done or not row or row.get("State") == "dropped" or item in replanned:
            continue
        if plan["field"] == "bugs":
            record = problems.last(("bug verified", "bug verified withdrawn"), item)
            if record and record["type"] == "bug verified" and passes(row["Acceptance"], item, problems):
                fix_bug(plan, milestone, item)
        elif passes(row["Acceptance"], item, problems):
            done.append(item)
    versioned = False
    for _, subject in subjects():
        if subject == f"Review passed: {plan['id']}":
            break
        versioned = versioned or subject.startswith("Version: ")
    if done and not versioned:
        numbers, previous = current_version()
        if plan["field"] == "features":
            numbers = [numbers[0], numbers[1] + 1, 0]
            rows = {row["ID"]: row for row in milestone["features"]}
            lines = [f"- {'New feature' if rows[i]['Type'] == 'new' else 'Update'}: {rows[i]['Feature']}" for i in done]
        else:
            numbers = [numbers[0], numbers[1], numbers[2] + 1]
            rows = {row["ID"]: row for row in reviewed_bugs}
            lines = [f"- Bugfix: {rows[i]['Bug']}" for i in done]
        version = ".".join(str(number) for number in numbers)
        stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"# {version} {stamp}\n" + "\n".join(lines) + "\n"
        write(CHANGELOG, entry + ("\n" + previous.strip("\n") + "\n" if previous.strip() else ""))
        save_plan(plan)
        commit(f"Version: {version}")
        print(f"Version: {version}")
    plan["meta"]["status"] = "closed"
    plan["meta"]["closed"] = today()
    save_plan(plan)
    shutil.rmtree(plan["dir"] / "tmp", ignore_errors=True)
    os.rename(plan["dir"], PLANS / "archive" / plan["dir"].name)
    progress.regenerate()
    commit(f"Plan closed: {plan['id']}")
    print(f"Plan closed: {plan['id']}")


def block():
    plan, milestone, problems = context()
    ids = open_important(problems.rows)
    if not ids:
        fail("no Important problem is open")
    plan["meta"]["status"] = "blocked"
    save_plan(plan)
    problems.record("plan blocked", *ids)
    problems.save()
    print(f"plan {plan['id']} is blocked, ask the user: accept, drop or replan")


def unblock(args):
    plan, milestone, problems = context()
    if plan["meta"]["status"] != "blocked":
        fail(f"plan {plan['id']} is not blocked")
    choice = args[0] if args else ""
    if choice == "accept" and len(args) == 2:
        item, reason = "", args[1]
    elif choice == "drop" and len(args) == 3:
        item, reason = args[1], args[2]
    elif choice == "replan" and len(args) == 2:
        item, reason = args[1], args[1]
    else:
        fail('usage: python -m tools.plan_close unblock <accept "<reason>" | drop <id> "<reason>" | replan <id>>')
    if not 1 <= words(reason) <= 12 or "|" in reason:
        fail("the reason must have 1 to 12 words")
    if item and item not in plan["ids"]:
        fail(f"{item} is not an id of plan {plan['id']}")
    if choice == "drop" and plan["field"] == "features":
        progress.drop_feature(item, reason)
    elif choice == "drop":
        progress.drop_bug(item, reason)
        problems = Problems(plan)
    elif choice == "replan" and plan["field"] == "bugs":
        problems.record("bug verified withdrawn", item)
    ids = open_important(problems.rows)
    for row in problems.rows:
        if row["ID"] in ids:
            row["Answer"] = f"user {choice} {reason}"
    problems.record("plan unblocked", choice, *([item] if item else []))
    problems.save()
    plan = require_plan()
    plan["meta"]["status"] = "in progress"
    save_plan(plan)
    print(f"plan {plan['id']} is in progress, record the review pass")


def run(args):
    answer = take_option(args, "--answer")
    command, rest = (args[0], args[1:]) if args else ("close", [])
    if command == "close" and not rest:
        return close()
    if command == "check":
        return check(rest, answer)
    if command == "verify-bug" and len(rest) == 1:
        return verify_bug(rest[0])
    if command == "unblock":
        return unblock(rest)
    simple = {"tuning": tuning, "reviewed": reviewed, "review-passed": review_passed, "block": block}
    if command in simple and not rest:
        return simple[command]()
    fail(
        "usage: python -m tools.plan_close [close | tuning | reviewed | review-passed | block"
        " | check [<id> --answer yes|no] | verify-bug <bug>"
        ' | unblock <accept "<reason>" | drop <id> "<reason>" | replan <id>>]'
    )


if __name__ == "__main__":
    main(run)
