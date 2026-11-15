import re

from tools import progress, test
from tools._lib import (
    BUG_ID,
    FEATURE_ID,
    Problems,
    all_steps,
    approval_errors,
    ask,
    clean_tree,
    commit,
    fail,
    find_step,
    git,
    has_commit,
    main,
    next_id,
    MAX_ROUNDS,
    open_important,
    posted_important,
    open_milestone,
    parse_check,
    problem_errors,
    progress_row,
    require_branch,
    require_plan,
    run as shell,
    save_plan,
    settled,
    take_option,
    tool,
    words,
)
from tools.approve import step_base

STEP_HINT = "revert the step with python -m tools.step_close revert, or block it after the second attempt"


def context(step_id=None):
    plan = require_plan()
    milestone = open_milestone()
    if not milestone or milestone["id"] != plan["meta"]["milestone"]:
        fail(f"the milestone of plan {plan['id']} is not open")
    require_branch()
    row = progress_row(plan, step_id) if step_id else None
    return plan, milestone, Problems(plan), row


def rounds(problems, step_id):
    return problems.count_since("step reviewed", ("step reverted", "step unblocked"), step_id)


def reverts(problems, step_id):
    return problems.count_since("step reverted", ("step unblocked",), step_id)


def start(step_id):
    plan, milestone, problems, row = context(step_id)
    if plan["meta"]["status"] != "in progress":
        fail(f"plan {plan['id']} is blocked")
    if row["State"] == "in progress":
        print(f"step {step_id} is in progress")
        return
    expected = progress.next_step(plan, milestone)
    if row["State"] != "open" or step_id != expected:
        fail(f"the next step is {expected}")
    row["State"] = "in progress"
    save_plan(plan)
    problems.record("step started", step_id, git("rev-parse", "--short=12", "HEAD"))
    problems.save()
    print(f"step {step_id} is in progress")


def review(step_id):
    plan, milestone, problems, row = context(step_id)
    if row["State"] != "in progress":
        fail(f"step {step_id} has state {row['State']}")
    count = rounds(problems, step_id)
    if count >= MAX_ROUNDS:
        fail(f"the round cap is {MAX_ROUNDS}: answer the problems, then close the step, or {STEP_HINT}")
    if count and not posted_important(step_rows(problems, step_id), count):
        fail(f"round {count} posted no Important problem: answer the problems, then close the step")
    problems.record("step reviewed", step_id)
    problems.save()
    print(f"review round {count + 1} of step {step_id}")


def outside_step(path, plan_rel):
    """Whether a path lies outside the step: the memory, the setup findings, the milestones and the other plans."""
    if path.startswith("docs/memories/") or path in ("docs/MEMORY.md", "docs/ai-setup-adjustments.md"):
        return True
    if path.startswith("docs/milestones/"):
        return True
    plan_rel = plan_rel.replace("\\", "/").rstrip("/") + "/"
    return path.startswith("docs/plans/") and not path.startswith(plan_rel)


def revert(step_id):
    plan, milestone, problems, row = context(step_id)
    if row["State"] != "in progress":
        fail(f"step {step_id} has state {row['State']}")
    if reverts(problems, step_id) >= 1:
        fail(f"a step has one new attempt: run python -m tools.step_close block {step_id}")
    if not clean_tree():
        fail("the work tree is not clean, commit the changes first")
    base = step_base(problems, step_id)
    lines = git("log", "--format=%H%x09%s", f"{base}..HEAD").splitlines()
    commits = [line.split("\t")[0] for line in lines if not re.match(r"^\S+\t(Bug reported|Bug dropped|Milestone updated): ", line)]
    # a commit of memories, setup findings, milestones or other plans stays, also inside a mixed commit
    kept, mixed = [], []
    for commit_hash in commits:
        files = git("show", "--name-only", "--format=", commit_hash).splitlines()
        outside = [path for path in files if outside_step(path, plan["rel"])]
        if files and len(outside) == len(files):
            kept.append(commit_hash)
        elif outside:
            mixed.append((commit_hash, outside))
    commits = [commit_hash for commit_hash in commits if commit_hash not in kept]
    if commits:
        code, output = shell(["git", "revert", "--no-commit", *commits])
        if code != 0:
            shell(["git", "revert", "--abort"])
            fail(f"git revert failed, revert the commits of the step by hand:\n{output}")
        for commit_hash, outside in reversed(mixed):
            git("checkout", commit_hash, "--", *outside)
        git("checkout", "HEAD", "--", plan["rel"])
    for commit_hash in kept:
        print(f"kept {git('log', '--format=%h %s', '-1', commit_hash)}")
    for item in problems.rows:
        if item["Step"] == step_id and not settled(item):
            item["Answer"] = "reverted"
    problems.record("step reverted", step_id)
    problems.save()
    commit(f"Revert step {plan['id']} {step_id}")
    shell(["git", "revert", "--quit"])
    print(f"step {step_id} is reverted, the new attempt starts at round 1")


def step_rows(problems, step_id):
    return [row for row in problems.rows if row["Step"] == step_id]


def close(step_id, answer, by=None):
    plan, milestone, problems, row = context(step_id)
    subject = f"Step closed: {plan['id']} {step_id}"
    if row["State"] == "complete":
        if not has_commit(subject):
            commit(subject)
        print(subject)
        return
    if row["State"] != "in progress":
        fail(f"step {step_id} has state {row['State']}")
    step = find_step(plan, step_id)
    if plan["field"] == "features":
        pattern, known = FEATURE_ID, {item["ID"] for item in milestone["features"]}
    else:
        pattern, known = BUG_ID, {item["ID"] for item in milestone["bugs"]}
    errors = []
    if not pattern.match(step["Feature"]) or step["Feature"] not in known:
        errors.append(f"the id {step['Feature']} of the step is not in the tables of {milestone['id']}")
    count = rounds(problems, step_id)
    if count == 0:
        errors.append("the step has no review, run review-step")
    errors += problem_errors(step_rows(problems, step_id), STEP_HINT, count)
    errors += approval_errors(plan, problems, step_id, step_base(problems, step_id))
    if errors:
        fail("step gate:\n" + "\n".join(errors))
    kind, name = parse_check(step["Verification"])
    if kind == "MANUAL":
        passed = ask(f"Manual check {name} of step {step_id}: did it pass?", answer)
        problems.record("manual passed" if passed else "manual failed", step_id)
        problems.save()
        test.append_evidence(plan, step_id, name, "MANUAL", 0 if passed else 1, manual_source(by, passed))
        if not passed:
            errors.append(f"the manual check {name} failed")
    else:
        code, output = test.execute(kind, name, plan, step_id)
        if code != 0:
            errors.append(f"the verification '{step['Verification']}' fails:\n{output}")
    if not test.evidence_path(plan, step_id).is_file():
        errors.append("the evidence file is missing")
    code, output = tool("check")
    if code != 0:
        errors.append(f"python -m tools.check fails:\n{output}")
    # the related tests: each test file that the step changed or added; the whole suite runs at the milestone close
    for test_name in test.changed_tests(step_base(problems, step_id)):
        if (kind, name) == ("TEST", test_name):
            continue
        code, output = test.execute("TEST", test_name, plan, step_id)
        if code != 0:
            errors.append(f"the changed test {test_name} fails:\n{output}")
    if errors:
        fail("step gate:\n" + "\n".join(errors))
    row["State"], row["Evidence"], row["Round"] = "complete", f"evidence/{step_id}-test.txt", str(count)
    save_plan(plan)
    progress.regenerate()
    commit(subject)
    print(subject)


def block(step_id):
    plan, milestone, problems, row = context(step_id)
    if row["State"] != "in progress":
        fail(f"step {step_id} has state {row['State']}")
    if reverts(problems, step_id) == 0:
        fail(f"a block needs a failed second attempt: {STEP_HINT}")
    row["State"], row["Round"] = "blocked", str(rounds(problems, step_id))
    plan["meta"]["status"] = "blocked"
    save_plan(plan)
    problems.record("step blocked", step_id, *open_important(step_rows(problems, step_id), rounds(problems, step_id)))
    problems.save()
    print(f"step {step_id} is blocked, ask the user")


def unblock(step_id, answer):
    """Takes the decision of the user on the open Important problems of a blocked step, or of a step in progress
    after its last review round, so the step goes on without a revert."""
    plan, milestone, problems, row = context(step_id)
    accepted = row["State"] == "in progress" and open_important(step_rows(problems, step_id), rounds(problems, step_id))
    if row["State"] != "blocked" and not accepted:
        fail(f"step {step_id} has state {row['State']} and no open Important problem")
    if not answer.strip() or "|" in answer or "\n" in answer:
        fail("the user answer must be one line without '|'")
    for item in step_rows(problems, step_id):
        if not settled(item):
            item["Answer"] = f"user {answer.strip()}"
    problems.record("step unblocked", step_id)
    problems.save()
    row["State"] = "in progress"
    plan["meta"]["status"] = "in progress"
    save_plan(plan)
    print(f"step {step_id} is in progress")


def add_fix(problem_id, step_id):
    plan, milestone, problems, _ = context()
    origin = find_step(plan, step_id)
    rows = [row for row in problems.rows if row["ID"] == problem_id]
    if not rows or rows[0]["Step"] != "plan" or rows[0]["Severity"] != "Important" or settled(rows[0]):
        fail(f"{problem_id} must be an open Important problem of the plan review")
    problem = rows[0]
    if any(row["Rule"] == problem["Rule"] and row["Answer"].startswith("fix ") for row in problems.rows):
        fail(f"the rule {problem['Rule']} has a fix step in this plan close: run python -m tools.plan_close block")
    if not 1 <= words(problem["Fix"]) <= 20:
        fail(f"the Fix cell of {problem_id} must have 1 to 20 words")
    fix_id = next_id("S", [step["Step"] for step in all_steps(plan)]) + "-fix"
    plan["fixes"].append(
        {"Step": fix_id, "Feature": origin["Feature"], "Problem": problem_id, "Text": problem["Fix"], "Verification": origin["Verification"]}
    )
    plan["progress"].append({"Step": fix_id, "Feature": origin["Feature"], "State": "open", "Evidence": "", "Round": ""})
    plan["meta"]["status"] = "in progress"
    save_plan(plan)
    problem["Answer"] = f"fix {fix_id}"
    problems.record("fix added", fix_id, problem_id)
    problems.save()
    print(f"fix step {fix_id} added, run step-run")


def manual_source(by, passed):
    if by == "agent":
        return f"checked by the agent on request of the user: {'passed' if passed else 'failed'}"
    return f"answer of the user: {'yes' if passed else 'no'}"


def run(args):
    answer = take_option(args, "--answer")
    by = take_option(args, "--by")
    if by not in (None, "agent"):
        fail("--by takes the value agent")
    command, rest = (args[0], args[1:]) if args else ("", [])
    if command in ("start", "review", "revert", "block") and len(rest) == 1:
        {"start": start, "review": review, "revert": revert, "block": block}[command](rest[0])
    elif command == "close" and len(rest) == 1:
        close(rest[0], answer, by)
    elif command == "unblock" and len(rest) == 2:
        unblock(*rest)
    elif command == "add-fix" and len(rest) == 2:
        add_fix(*rest)
    else:
        fail(
            "usage: python -m tools.step_close <start|review|revert|block> <step>"
            " | close <step> [--answer yes|no] [--by agent]"
            ' | unblock <step> "<user answer>"'
            " | add-fix <problem> <step>"
        )


if __name__ == "__main__":
    main(run)
