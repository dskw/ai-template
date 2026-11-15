import collections
import os
import re
import shutil

from tools import memory_lint, progress, test
from tools._lib import (
    PLANS,
    Problems,
    approval_errors,
    ask,
    clean_tree,
    commit,
    dirty_files,
    fail,
    git,
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
    EXTENSION_HEADER,
)
from tools._lib import MAX_ROUNDS, posted_important
from tools.approve import close_base, created_commit
from tools.milestone_create import section

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


def check(args, answer, by=None):
    plan, milestone, problems = context()
    code = 0
    for item in plan["ids"]:
        row = target_row(plan, milestone, item)
        if not row or row.get("State") == "dropped" or (args and item not in args):
            continue
        kind, name = parse_check(row["Acceptance"])
        if kind == "MANUAL":
            if answer is None:
                print(f"{item} MANUAL {name}: ask the user, then run python -m tools.plan_close check {item} --answer yes|no")
                code = 1
                continue
            passed = ask(f"Manual check {name} for {item}: did it pass?", answer)
            problems.record("manual passed" if passed else "manual failed", item)
        else:
            passed = test.execute(kind, name)[0] == 0
        source = " (checked by the agent on request of the user)" if by == "agent" else ""
        print(f"{item} {row['Acceptance']}: {'pass' if passed else 'fail'}{source}")
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


def plan_rows(problems):
    return [row for row in problems.rows if row["Step"] == "plan"]


def step_problem_rows(problems):
    """The rows of the steps: their rounds are over, so each one needs its answer and its check."""
    return [row for row in problems.rows if row["Step"] != "plan"]


def plan_rounds(problems):
    return problems.count_since("plan reviewed", BOUNDARIES)


def plan_problem_errors(problems):
    errors = problem_errors(plan_rows(problems), PLAN_HINT, plan_rounds(problems))
    return errors + problem_errors(step_problem_rows(problems), PLAN_HINT, MAX_ROUNDS)


def open_plan_important(problems):
    held = plan_rounds(problems)
    return open_important(plan_rows(problems), held) + open_important(step_problem_rows(problems), MAX_ROUNDS)


def reviewed():
    plan, milestone, problems = context()
    if open_steps(plan, milestone):
        fail("steps are not complete: " + " ".join(open_steps(plan, milestone)))
    count = problems.count_since("plan reviewed", BOUNDARIES)
    if count >= MAX_ROUNDS:
        fail(f"the round cap is {MAX_ROUNDS}: record the pass, or {PLAN_HINT}")
    if count and not posted_important(plan_rows(problems), count):
        fail(f"round {count} posted no Important problem: answer the problems, then record the pass")
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
    errors += plan_problem_errors(problems)
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
        if not subject.startswith("Bug fixed: "):
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


def product_changed(plan):
    """Whether the plan changed a source or test file of a language of the project since its creation."""
    project = load_project()
    roots = [root.rstrip("/") + "/" for entry in project.get("language", []) for root in entry["source"] + entry["tests"]]
    names = git("diff", "--name-only", created_commit(plan), "HEAD").splitlines()
    return any(name.startswith(tuple(roots)) for name in names)


def gate(plan, milestone, problems):
    review = None
    if product_changed(plan):
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
    errors += plan_problem_errors(problems)
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
    # the related tests: the checks of the Verification section and each test file the plan changed or added
    failures = []
    for check in plan_checks(plan):
        kind, name = check
        if kind == "MANUAL":
            continue
        code, output = test.execute(kind, name)
        if code != 0:
            failures.append(f"the check '{kind} {name}' fails:\n{output}")
    checked = {name for kind, name in plan_checks(plan) if kind == "TEST"}
    for test_name in test.changed_tests(created_commit(plan)):
        if test_name in checked:
            continue
        code, output = test.execute("TEST", test_name)
        if code != 0:
            failures.append(f"the changed test {test_name} fails:\n{output}")
    if failures:
        fail("plan gate:\n" + "\n".join(failures))
    return review


def plan_checks(plan):
    """The checks of the Verification section of a plan as (kind, name)."""
    lines = (section(plan["text"], "Verification") or "").split("\n")
    return [check for line in lines if line.startswith("- ") and (check := parse_check(line[2:]))]


def fix_bug(plan, milestone, bug_id):
    plan["meta"]["done"].append(bug_id)
    save_plan(plan)
    row = progress.remove_bug(milestone, bug_id)
    progress.regenerate()
    commit(f"Bug fixed: {milestone['id']} {bug_id}\n\n{row['Bug']}")


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


def prune(folder):
    extensions = folder / "extensions.md"
    if extensions.exists() and not read_table(read(extensions), None, EXTENSION_HEADER, rel(extensions)):
        extensions.unlink()
    problems = folder / "problems.md"
    if problems.exists():
        loaded = Problems({"dir": folder, "archived": False})
        if not loaded.rows and not loaded.records:
            problems.unlink()
    evidence = folder / "evidence"
    if evidence.is_dir() and not any(evidence.iterdir()):
        evidence.rmdir()


def finish_archive():
    pending = dirty_files()
    for plan in plans():
        if plan["archived"] and any(name.startswith(plan["rel"] + "/") for name in pending):
            progress.regenerate()
            commit(f"Plan closed: {plan['id']}")
            print(f"Plan closed: {plan['id']}")
            return True
    return False


def close():
    if finish_archive():
        return
    plan, milestone, problems = context()
    gate(plan, milestone, problems)
    done = plan["meta"]["done"]
    replanned = {r["ids"][1] for r in problems.records if r["type"] == "plan unblocked" and r["ids"][0] == "replan"}
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
    save_plan(plan)
    tmp = plan["dir"] / "tmp"
    stop_package(tmp)
    shutil.rmtree(tmp, ignore_errors=True)
    if tmp.exists():
        fail(f"{rel(tmp)} is in use: close the manual check package, then run the close again")
    prune(plan["dir"])
    target = PLANS / "archive" / plan["dir"].name
    try:
        os.rename(plan["dir"], target)
    except OSError:
        shutil.copytree(plan["dir"], target)
        shutil.rmtree(plan["dir"])
    plan["dir"], plan["path"], plan["rel"] = target, target / "plan.md", rel(target)
    plan["meta"]["status"] = "closed"
    plan["meta"]["closed"] = today()
    save_plan(plan)
    progress.regenerate()
    commit(f"Plan closed: {plan['id']}")
    print(f"Plan closed: {plan['id']}")


def block():
    plan, milestone, problems = context()
    ids = open_plan_important(problems)
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
    ids = open_plan_important(problems)
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
    by = take_option(args, "--by")
    command, rest = (args[0], args[1:]) if args else ("close", [])
    if command == "close" and not rest:
        return close()
    if command == "check":
        return check(rest, answer, by)
    if command == "verify-bug" and len(rest) == 1:
        return verify_bug(rest[0])
    if command == "unblock":
        return unblock(rest)
    simple = {"tuning": tuning, "reviewed": reviewed, "review-passed": review_passed, "block": block}
    if command in simple and not rest:
        return simple[command]()
    fail(
        "usage: python -m tools.plan_close [close | tuning | reviewed | review-passed | block"
        " | check [<id> --answer yes|no [--by agent]] | verify-bug <bug>"
        ' | unblock <accept "<reason>" | drop <id> "<reason>" | replan <id>>]'
    )


if __name__ == "__main__":
    main(run)
