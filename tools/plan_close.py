import collections
import os
import re
import shutil

from tools import licenses, memory_lint, progress, test
from tools._lib import (
    EXTENSION_HEADER,
    MAX_ROUNDS,
    PLANS,
    TOOL_COMMIT,
    Problems,
    active_plans,
    all_steps,
    approval_errors,
    ask,
    branch,
    clean_tree,
    commit,
    dirty_files,
    earlier_pass,
    fail,
    git,
    git_dir,
    git_ok,
    has_commit,
    load_plan,
    load_project,
    main,
    merging,
    missing_command,
    milestone_branch,
    milestones,
    open_important,
    open_milestone,
    parse_check,
    plan_branch,
    plans,
    posted_important,
    problem_errors,
    read,
    read_table,
    rel,
    require_branch,
    require_main,
    require_plan,
    require_worktree,
    required_steps,
    run as shell,
    save_plan,
    stop_package,
    subjects,
    take_option,
    today,
    tool,
    tool_git,
    unclean,
    user_reason,
    words,
    worktree_path,
    write,
)
from tools.approve import close_base
from tools.milestone_create import section

PLAN_HINT = "add a fix step with python -m tools.step_close add-fix <problem> <step>"
BOUNDARIES = ("fix added", "plan unblocked", "review passed")
FEATURE_EXTENSIONS = ("feature", "refactor")


def worktree_context(branch_check=True):
    """The plan of this worktree with its milestone and problems. The plan review and its records run here."""
    require_worktree()
    plan = require_plan()
    milestone = open_milestone()
    if not milestone or milestone["id"] != plan["meta"]["milestone"]:
        fail(f"the milestone of plan {plan['id']} is not open")
    if branch_check:
        require_branch()
    return plan, milestone, Problems(plan)


def context():
    """The plan in close in the main repository, after its merge."""
    require_main()
    plan = require_plan()
    milestone = open_milestone()
    if not milestone or milestone["id"] != plan["meta"]["milestone"]:
        fail(f"the milestone of plan {plan['id']} is not open")
    require_branch()
    return plan, milestone, Problems(plan)


def dropped_ids(problems):
    """The ids that the user dropped for this plan in its worktree. The merge writes the drop to the milestone."""
    return {r["ids"][1] for r in problems.records if r["type"] == "plan unblocked" and r["ids"][:1] == ["drop"] and len(r["ids"]) > 1}


def open_steps(plan, milestone, problems=None):
    dropped = dropped_ids(problems) if problems else set()
    required = {step["Step"] for step in required_steps(plan, milestone) if step["Feature"] not in dropped}
    return [row["Step"] for row in plan["progress"] if row["Step"] in required and row["State"] != "complete"]


def target_row(plan, milestone, item):
    table = milestone["features"] if plan["field"] == "features" else milestone["bugs"]
    return next((row for row in table if row["ID"] == item), None)


def unbound(acceptance, item):
    """Whether the acceptance names a command without a binding. It prints the failure: the check fails, and the
    feature stays in progress."""
    name = missing_command(acceptance)
    if name:
        print(
            f"{item} {acceptance}: fail, the command {name} has no binding in [commands] of tools/project.toml."
            " The feature stays in progress. Run project-update to add the binding"
        )
    return bool(name)


def passes(acceptance, item, problems):
    kind, name = parse_check(acceptance)
    if kind == "MANUAL":
        record = problems.last(("manual passed", "manual failed"), item)
        return bool(record) and record["type"] == "manual passed"
    return not unbound(acceptance, item) and test.execute(kind, name)[0] == 0


def check(args, answer, by=None):
    plan, milestone, problems = context()
    code = 0
    for item in plan["ids"]:
        row = target_row(plan, milestone, item)
        if not row or row.get("State") == "dropped" or (args and item not in args):
            continue
        kind, name = parse_check(row["Acceptance"])
        source = " (checked by the agent on request of the user)" if by == "agent" else ""
        if kind == "MANUAL":
            passed, note = manual_result(problems, name, f"Manual check {name} for {item}: did it pass?", answer, f"{item} MANUAL {name}", item)
            if passed is None:
                code = 1
                continue
            source = note or source
            problems.record("manual passed" if passed else "manual failed", item, name, git("rev-parse", "--short=12", "HEAD"))
        elif unbound(row["Acceptance"], item):
            continue
        else:
            passed = test.execute(kind, name)[0] == 0
        print(f"{item} {row['Acceptance']}: {'pass' if passed else 'fail'}{source}")
    for name in manual_lines(plan, milestone):
        if args and name not in args:
            continue
        passed, note = manual_result(problems, name, f"Manual check {name} of the plan verification: did it pass?", answer, f"verification MANUAL {name}", name)
        if passed is None:
            code = 1
            continue
        problems.record("plan manual passed" if passed else "plan manual failed", name, git("rev-parse", "--short=12", "HEAD"))
        source = note or (" (checked by the agent on request of the user)" if by == "agent" else "")
        print(f"verification MANUAL {name}: {'pass' if passed else 'fail'}{source}")
    problems.save()
    commit(f"Manual check recorded: {plan['id']}", [problems.path], verify=False)
    return code


def manual_result(problems, name, question, answer, label, target):
    """The result of a manual check of the plan close and a note on its source. Without `--answer`, an earlier pass
    holds while no product file changed since its commit. None means that the user has to answer."""
    if answer is not None:
        return ask(question, answer), ""
    record, changed = earlier_pass([problems], name)
    if record and not changed:
        return True, f" (the pass at {record['ids'][-1]} holds, no product file changed since)"
    stale = f". The pass at {record['ids'][-1]} no longer holds, these files changed since: {' '.join(changed)}" if record else ""
    print(f"{label}: ask the user, then run python -m tools.plan_close check {target} --answer yes|no{stale}")
    return None, ""


def manual_lines(plan, milestone):
    """The names of the manual lines of the plan verification that are no acceptance of an item of the plan. The
    check of the item records the acceptance. A line that only the steps of dropped items verify asks no check."""
    rows = {item: row for item in plan["ids"] if (row := target_row(plan, milestone, item))}
    acceptances = {row["Acceptance"] for row in rows.values()}
    gone = {item for item in plan["ids"] if item not in rows or rows[item].get("State") == "dropped"}
    names = []
    for kind, name in plan_checks(plan):
        if kind != "MANUAL" or f"MANUAL {name}" in acceptances or name in names:
            continue
        owners = {step["Feature"] for step in all_steps(plan) if step["Verification"] == f"MANUAL {name}"}
        if owners and owners <= gone:
            continue
        names.append(name)
    return names


def manual_line_errors(plan, milestone, problems):
    errors = []
    for name in manual_lines(plan, milestone):
        record = problems.last(("plan manual passed", "plan manual failed"), name)
        if not record or record["type"] != "plan manual passed":
            errors.append(f"the manual line {name} of the plan verification has no passed record, run python -m tools.plan_close check {name}")
    return errors


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
        step = next(step for step in plan["steps"] if step["Feature"] == bug_id and step["Verification"] == row["Acceptance"])
        verified = test.failed_before_passed(plan, step["Step"], name)
        if not verified:
            print(f"{bug_id}: the evidence of {step['Step']} must show a failing run of {name} before a passing run")
    if not verified:
        return 1
    problems.record("bug verified", bug_id)
    problems.save()
    commit(f"Bug verified: {plan['id']} {bug_id}", [problems.path], verify=False)
    print(f"bug verified {bug_id}")


def tuning():
    plan, milestone, problems = context()
    fixed, closed = collections.Counter(), collections.Counter()
    topics = collections.defaultdict(set)
    for other in plans():
        if other["meta"]["status"] == "draft":
            continue
        for row in Problems(other).rows:
            if row["Answer"].startswith("fixed"):
                fixed[row["Rule"]] += 1
            if re.match(r"closed (wrong|intentional) ", row["Answer"]) and row["Check"] == "confirmed":
                closed[row["Rule"]] += 1
            if row["Severity"] == "Important" and row["Topic"]:
                topics[row["Topic"].lower()].add(other["id"])
    print("rule: fixed, closed as wrong or intentional and confirmed")
    for rule in sorted(set(fixed) | set(closed)):
        print(f"{rule}: {fixed[rule]}, {closed[rule]}")
    print("topic: plans with an Important problem")
    for topic in sorted(topics):
        print(f"{topic}: {len(topics[topic])}")
    for rule in sorted(rule for rule in closed if closed[rule] >= 2):
        print(f"tune {rule}: remove the failure pattern from docs/REVIEW.md, or add the intent to the conventions")
    for rule in sorted(rule for rule in fixed if fixed[rule] >= 3):
        print(f"tune {rule}: add a lint rule or a convention rule")
    # a topic of this plan that an earlier plan had too: the same failure came back
    for topic in sorted(topic for topic in topics if plan["id"] in topics[topic] and len(topics[topic]) >= 2):
        others = " ".join(sorted(topics[topic] - {plan["id"]}))
        print(
            f"tune topic {topic}: also in {others}. Add one row to the failure patterns of docs/REVIEW.md, propose a dependency,"
            " or run a research on the cause with a refactor feature as its possible result"
        )
    if plan["field"] == "bugs":
        states = {f"{m['id']}-{row['ID']}": row["State"] for m in milestones() for row in m["features"]}
        for row in milestone["bugs"]:
            feature = row["Feature"] if "-" in row["Feature"] else f"{milestone['id']}-{row['Feature']}"
            if row["ID"] in plan["ids"] and row["Source"] == "user" and states.get(feature) == "done":
                print(f"tune {row['ID']}: add one line to docs/REVIEW.md that describes the failure '{row['Bug']}'")
    problems.record("tuning done")
    problems.save()
    commit(f"Tuning done: {plan['id']}", [problems.path], verify=False)


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


def sync():
    """Merges the milestone branch into the plan branch of this worktree, so the plan holds the work of the plans
    that closed before it. A merge with a conflict stops; the next call commits the resolved merge."""
    plan, milestone, problems = worktree_context(branch_check=False)
    target = milestone_branch(milestone)
    if merging():
        if git("diff", "--name-only", "--diff-filter=U"):
            fail("the merge has files with a conflict, resolve them and run git add")
        withdraw(plan)
        tool_git("commit", "-m", f"Plan synced with conflicts: {plan['id']}")
        print(f"Plan synced with conflicts: {plan['id']}. The plan needs a plan review of this state")
        return
    require_branch()
    if not clean_tree():
        fail(unclean())
    if git_ok("merge-base", "--is-ancestor", target, "HEAD"):
        print(f"plan {plan['id']} holds the tip of {target}")
        return
    code, output = shell(["git", "merge", "--no-ff", "--no-commit", target])
    conflicts = git("diff", "--name-only", "--diff-filter=U").splitlines()
    if conflicts:
        fail("merge conflict in:\n" + "\n".join(conflicts) + "\nResolve the files and run git add. Then run the same command again")
    if code != 0:
        fail(f"git merge failed:\n{output}")
    withdraw(plan)
    tool_git("commit", "--no-verify", "-m", f"Plan synced: {plan['id']}")
    print(f"Plan synced: {plan['id']}")


def withdraw(plan):
    """Records each bug of a fix plan that left the Bugs table of the merged milestone file without a fix."""
    if plan["field"] != "bugs":
        return
    plan, milestone = require_plan(), open_milestone()
    problems = Problems(plan)
    known = {row["ID"] for row in milestone["bugs"]} | set(plan["meta"]["done"]) | progress.withdrawn(plan)
    for item in plan["ids"]:
        if item not in known:
            problems.record("bug verified withdrawn", item)
    problems.save()
    git("add", "--", rel(problems.path))


def reviewed():
    plan, milestone, problems = worktree_context()
    if open_steps(plan, milestone, problems):
        fail("steps are not complete: " + " ".join(open_steps(plan, milestone, problems)))
    count = problems.count_since("plan reviewed", BOUNDARIES)
    if count >= MAX_ROUNDS:
        fail(f"the round cap is {MAX_ROUNDS}: record the pass, or {PLAN_HINT}")
    if count and not posted_important(plan_rows(problems), count):
        fail(f"round {count} posted no Important problem: answer the problems, then record the pass")
    if count == 0:
        # the full run of the plan checks before the review, so a broken test that no step names shows up before the merge
        failed = False
        for kind, name in plan_checks(plan):
            if kind != "COMMAND":
                continue
            code, output = test.execute(kind, name)
            if code != 0:
                failed = True
                print(f"the check 'COMMAND {name} passes' fails:\n{output}")
        if failed:
            print("name each failing test in the task of the plan review")
    problems.record("plan reviewed")
    problems.save()
    commit(f"Plan reviewed: {plan['id']}", [problems.path], verify=False)
    print(f"plan review round {count + 1}")


def review_passed():
    plan, milestone, problems = worktree_context()
    subject = f"Review passed: {plan['id']}"
    if subjects()[0][1] == subject and clean_tree():
        print(subject)
        return
    errors = [f"step {step_id} is not complete" for step_id in open_steps(plan, milestone, problems)]
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


def roots():
    project = load_project()
    return tuple(root.rstrip("/") + "/" for entry in project.get("language", []) for root in entry["source"] + entry["tests"])


def review_errors(plan, name, problems):
    """The errors of the review state of a plan branch that changed a source or test file: its newest own commit is
    the review pass. Only a merge of the milestone branch without a conflict can follow it."""
    subject = f"Review passed: {plan['id']}"
    synced = f"Plan synced: {plan['id']}"
    for line in git("log", "--first-parent", "--format=%H%x09%s", f"HEAD..{name}").splitlines():
        commit_hash, _, found = line.partition("\t")
        if found == synced:
            continue
        if found != subject:
            break
        record = problems.last(("review passed",))
        parent = git("rev-parse", f"{commit_hash}~1")
        names = git("diff", "--name-only", f"{commit_hash}~1", commit_hash).splitlines()
        if record and parent.startswith(record["ids"][0]) and names == [problems.rel]:
            return []
        break
    return [f"the plan changed after its review: run review-plan in {worktree_path(plan['id'])}"]


def merge(plan_id):
    """Brings a reviewed plan from its branch to the milestone branch as one commit. The tag keeps its commits."""
    require_main()
    milestone = open_milestone()
    if not milestone:
        fail("no open milestone")
    require_branch()
    subject = f"Plan merged: {plan_id}"
    if has_commit(subject):
        print(subject)
        return
    plan = next((p for p in active_plans() if p["id"] == plan_id), None)
    if not plan:
        fail(f"{plan_id} is no active plan")
    closing = [p["id"] for p in active_plans() if has_commit(f"Plan merged: {p['id']}")]
    if closing:
        fail(f"plan {closing[0]} is in close. Close it first")
    name, path = plan_branch(plan_id), worktree_path(plan_id)
    marker = git_dir() / "PLAN_MERGE"
    if marker.exists():
        # an interrupted merge left the staged squash behind
        shell(["git", "reset", "--hard", "HEAD"])
        marker.unlink()
    if not clean_tree():
        fail(unclean("the work tree of the main repository"))
    errors = []
    if path.exists() and shell(["git", "status", "--porcelain"], cwd=path)[1].strip():
        errors.append(unclean(f"the worktree {path}", path))
    if not git_ok("merge-base", "--is-ancestor", "HEAD", name):
        errors.append(f"the plan branch does not hold the tip of {branch()}: run python -m tools.plan_close sync in {path}")
    if errors:
        fail("plan merge:\n" + "\n".join(errors))
    # the plan branch holds the tip of the milestone branch, so this diff holds the own changes of the plan only
    changed = git("diff", "--name-only", "HEAD", name).splitlines()
    # the squash puts the state of the plan branch into this work tree; the checks run on it before the commit
    write(marker, plan_id + "\n")
    code, output = shell(["git", "merge", "--squash", name])
    if code == 0:
        plan = load_plan(plan["dir"])
        problems = Problems(plan)
        errors += [f"step {step_id} is not complete" for step_id in open_steps(plan, milestone, problems)]
        errors += plan_problem_errors(problems)
        if any(item.startswith(roots()) for item in changed):
            errors += review_errors(plan, name, problems)
        errors = errors or merged_tree_errors(plan)
    if code != 0 or errors:
        shell(["git", "reset", "--hard", "HEAD"])
        marker.unlink()
        hint = f"\nFix it in {path}: a failing test goes into the task of the plan review"
        fail(f"git merge failed:\n{output}" if code != 0 else "plan merge:\n" + "\n".join(errors) + hint)
    marker.unlink()
    if not git_ok("rev-parse", "--verify", "--quiet", f"refs/tags/closed/{plan_id}"):
        git("tag", f"closed/{plan_id}", name)
    tool_git("commit", "--no-verify", "-m", subject)
    print(subject)
    reasons = [match.group(1) for row in problems.rows if (match := re.match(r"user drop (\S.*)$", row["Answer"]))]
    for item in sorted(dropped_ids(problems)):
        target = target_row(plan, open_milestone(), item)
        reason = reasons[0] if reasons else "dropped in the plan review"
        if plan["field"] == "features" and target and target["State"] in ("open", "in progress"):
            progress.drop_feature(item, reason)
        elif plan["field"] == "bugs" and target:
            progress.drop_bug(item, reason)


def merged_tree_errors(plan):
    """The failures of the checks on the merged tree: the full check, then in one call of the runner the checks of
    the Verification section and each test file that the plan changed or added."""
    # a feature that joined the plan after its creation leaves the tables of the milestone stale; the merge owns them
    progress.regenerate()
    shell(["git", "add", "--", "docs/milestones"])
    # the staged squash is the work of a tool, so the commit order check accepts its source files
    code, output = tool("check", env={TOOL_COMMIT: "1"})
    if code != 0:
        return [f"python -m tools.check fails:\n{output}"]
    failures = []
    names = [name for kind, name in plan_checks(plan) if kind == "TEST"]
    names += [name for name in test.changed_tests("HEAD") if name not in names]
    if names:
        code, output = test.execute("TEST", names)
        if code != 0:
            failures.append(f"the tests {' '.join(names)} fail:\n{output}")
    for kind, name in plan_checks(plan):
        if kind != "COMMAND":
            continue
        code, output = test.execute(kind, name)
        if code != 0:
            failures.append(f"the check '{kind} {name}' fails:\n{output}")
    return failures


def extension_errors(plan):
    path = plan["dir"] / "extensions.md"
    errors = []
    known = [milestone["id"] for milestone in milestones()]
    for row in read_table(read(path), None, EXTENSION_HEADER, rel(path)):
        if row["Decision"] in FEATURE_EXTENSIONS and row["Detail"] in known:
            continue
        if row["Decision"] == "dropped" and 1 <= words(row["Detail"]) <= 12:
            continue
        errors.append(
            f"{rel(path)}: {row['ID']} needs the decision 'feature' or 'refactor' with a milestone id, or 'dropped' with a reason of max 12 words"
        )
    return errors


def gate(plan, milestone, problems):
    base = close_base(plan)
    errors = []
    if not clean_tree():
        errors.append(unclean() + "\nDiscard the changes of an interrupted close, then run again")
    changed = [name for name in git("diff", "--name-only", base, "HEAD").splitlines() if name.startswith(roots())]
    if changed:
        errors.append("a source or test file changed after the merge of the plan, revert the change: " + " ".join(changed))
    errors += [f"step {step_id} is not complete" for step_id in open_steps(plan, milestone, problems)]
    errors += plan_problem_errors(problems)
    errors += manual_line_errors(plan, milestone, problems)
    if not problems.last(("tuning done",)):
        errors.append("problems.md is not processed, run python -m tools.plan_close tuning")
    errors += extension_errors(plan)
    errors += approval_errors(plan, problems, "close", base)
    errors += [f"memory lint: {error}" for error in memory_lint.errors(strict=True)]
    errors += progress.check_errors()
    errors += licenses.errors()
    if errors:
        fail("plan gate:\n" + "\n".join(errors))
    # the tests of the plan passed on this tree at the merge, and no source or test file changed since
    code, output = tool("check")
    if code != 0:
        fail(f"plan gate:\npython -m tools.check fails:\n{output}")


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


def remove_worktree(plan_id):
    """Removes the worktree and the branch of a closed plan. The tag of the plan keeps its commits."""
    path = worktree_path(plan_id)
    if path.exists():
        code, output = shell(["git", "worktree", "remove", "--force", str(path)])
        if code != 0:
            print(f"the worktree {path} is in use: close the programs there, then run git worktree remove --force {path}")
            return
    shell(["git", "worktree", "prune"])
    if git_ok("rev-parse", "--verify", "--quiet", f"refs/heads/{plan_branch(plan_id)}"):
        git("branch", "-D", plan_branch(plan_id))


def finish_archive():
    pending = dirty_files()
    for plan in plans():
        if plan["archived"] and any(name.startswith(plan["rel"] + "/") for name in pending):
            progress.regenerate()
            commit(f"Plan closed: {plan['id']}")
            remove_worktree(plan["id"])
            print(f"Plan closed: {plan['id']}")
            return True
    return False


def close():
    require_main()
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
    remove_worktree(plan["id"])
    print(f"Plan closed: {plan['id']}")


def block():
    plan, milestone, problems = worktree_context()
    ids = open_plan_important(problems)
    if not ids:
        fail("no Important problem is open")
    plan["meta"]["status"] = "blocked"
    save_plan(plan)
    problems.record("plan blocked", *ids)
    problems.save()
    commit(f"Plan blocked: {plan['id']}", [plan["dir"]], verify=False)
    print(f"plan {plan['id']} is blocked, ask the user: accept, drop or replan")


def unblock(args, answer):
    plan, milestone, problems = worktree_context()
    if plan["meta"]["status"] != "blocked":
        fail(f"plan {plan['id']} is not blocked")
    choice = args[0] if args else ""
    if choice == "accept" and len(args) == 1:
        item = ""
    elif choice in ("drop", "replan") and len(args) == 2:
        item = args[1]
    else:
        fail('usage: python -m tools.plan_close unblock <accept | drop <id> | replan <id>> --answer "<reason of the user>"')
    if item and item not in plan["ids"]:
        fail(f"{item} is not an id of plan {plan['id']}")
    ids = open_plan_important(problems)
    reason = user_reason(answer, f"Open problems of plan {plan['id']}: {' '.join(ids)}. Why does the user choose {choice}?")
    if choice in ("drop", "replan") and plan["field"] == "bugs":
        problems.record("bug verified withdrawn", item)
    changed = []
    for row in problems.rows:
        if row["ID"] in ids:
            changed.append(f"{row['ID']}={row['Answer'] or 'open'}")
            row["Answer"] = f"user {choice} {reason}"
    problems.record("plan unblocked", choice, *([item] if item else []), "old:", *changed, "new:", f"user {choice} {reason}")
    problems.save()
    plan["meta"]["status"] = "in progress"
    save_plan(plan)
    commit(f"Plan unblocked: {plan['id']}", [plan["dir"]], verify=False)
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
    if command == "merge" and len(rest) == 1:
        return merge(rest[0])
    if command == "unblock":
        return unblock(rest, answer)
    simple = {"sync": sync, "tuning": tuning, "reviewed": reviewed, "review-passed": review_passed, "block": block}
    if command in simple and not rest:
        return simple[command]()
    fail(
        "usage: python -m tools.plan_close [close | merge <plan> | tuning"
        " | check [<id> --answer yes|no [--by agent]] | verify-bug <bug>]\n"
        "in the worktree of the plan: python -m tools.plan_close <sync | reviewed | review-passed | block"
        ' | unblock <accept | drop <id> | replan <id>> --answer "<reason of the user>">'
    )


if __name__ == "__main__":
    main(run)
