import re

from tools import docs_lint, progress, test
from tools._lib import (
    AGENT_ANSWER,
    BUG_ID,
    CHECK_CELL,
    TOOL_ANSWERS,
    FEATURE_ID,
    FIX_HEADER,
    RESEARCH_CHECK,
    STEP_HEADER,
    Problems,
    active_plans,
    all_steps,
    approval_errors,
    ask,
    clean_tree,
    commit,
    fail,
    find_step,
    git,
    git_ok,
    has_commit,
    load_project,
    main,
    manual_answer,
    next_id,
    MAX_ROUNDS,
    open_important,
    posted_important,
    open_milestone,
    parse_check,
    problem_errors,
    progress_row,
    dependency_errors,
    dependency_rows,
    read,
    require_branch,
    require_plan,
    require_worktree,
    row_errors,
    run as shell,
    save_plan,
    settled,
    take_option,
    tool,
    unclean,
    user_reason,
    words,
    write,
    write_table,
)
from tools.approve import step_base

STEP_HINT = "revert the step with python -m tools.step_close revert, or block it after the second attempt"


def context(step_id=None):
    require_worktree()
    plan = require_plan()
    milestone = open_milestone()
    if not milestone or milestone["id"] != plan["meta"]["milestone"]:
        fail(f"the milestone of plan {plan['id']} is not open")
    require_branch()
    row = progress_row(plan, step_id) if step_id else None
    return plan, milestone, Problems(plan), row


def rounds(problems, step_id):
    """The review rounds of a step since its last revert. The unblock of a blocked step starts the count again;
    the acceptance of an open problem of a step in progress does not."""
    count, blocked = 0, False
    for record in problems.records:
        if record["ids"][:1] != [step_id]:
            continue
        if record["type"] == "step reverted" or (record["type"] == "step unblocked" and blocked):
            count, blocked = 0, False
        elif record["type"] == "step blocked":
            blocked = True
        elif record["type"] == "step reviewed":
            count += 1
    return count


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
    step = find_step(plan, step_id)
    errors = dependency_errors(step["Dependencies"], f"step {step_id}") if "Dependencies" in step else []
    if errors:
        fail("\n".join(errors))
    row["State"] = "in progress"
    save_plan(plan)
    problems.record("step started", step_id, git("rev-parse", "--short=12", "HEAD"))
    problems.save()
    commit(f"Step started: {plan['id']} {step_id}", [plan["dir"]], verify=False)
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
    commit(f"Step reviewed: {plan['id']} {step_id}", [problems.path], verify=False)
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
        fail(unclean())
    base = step_base(problems, step_id)
    # the own commits of the plan branch only: a merge of the milestone branch brings the work of other plans
    lines = git("log", "--first-parent", "--no-merges", "--format=%H%x09%s", f"{base}..HEAD").splitlines()
    commits = [line.split("\t")[0] for line in lines]
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


def research_errors(step_id, base):
    """The errors of a research step: it adds one or more research files and changes no source or test file."""
    changed = git("diff", "--name-only", base).splitlines()
    roots = [root.rstrip("/") + "/" for entry in load_project().get("language", []) for root in entry["source"] + entry["tests"]]
    code = [name for name in changed if name.startswith(tuple(roots))]
    errors = []
    if code:
        errors.append(f"the research step {step_id} changed source or test files: {' '.join(code)}")
    if not git("diff", "--name-only", "--diff-filter=A", base, "--", "docs/research").splitlines():
        errors.append(f"the research step {step_id} added no research file, run research-run")
    return errors


def last_record(problems, step_id):
    found = [record["type"] for record in problems.records if record["ids"][:1] == [step_id]]
    return found[-1] if found else None


def step_text(text):
    text = " ".join(text.split())
    if not 1 <= words(text) <= 20 or "|" in text:
        fail("the step text must have 1 to 20 words and no '|'")
    return text


def set_text(step_id, text, answer):
    """Writes the new text of a step that is not complete, after the user approved the change. The record keeps the
    old and the new text."""
    plan, milestone, problems, row = context(step_id)
    if row["State"] == "complete":
        fail(f"step {step_id} is complete, a complete step takes no new text")
    text = step_text(text)
    step = find_step(plan, step_id)
    old = step["Text"]
    if not ask(f"Change the text of {step_id} from '{old}' to '{text}': did the user approve it?", answer):
        fail("the user did not approve the new text")
    step["Text"] = text
    heading, header, rows = ("Fix steps", FIX_HEADER, plan["fixes"]) if step in plan["fixes"] else ("Steps", STEP_HEADER, plan["steps"])
    plan["text"] = write_table(plan["text"], heading, header, rows, plan["rel"])
    save_plan(plan)
    problems.record("text changed", step_id, "old:", old, "new:", text)
    problems.save()
    commit(f"Step changed: {plan['id']} {step_id}", [plan["dir"]], verify=False)
    print(f"step {step_id} has the new text")


def insert_refactor(feature_id, text, verification, answer):
    """Inserts a refactor step before the open steps of the running plan, after the approval of the user. The
    feature is a refactor feature of the milestone; the plan takes it into its features."""
    plan, milestone, problems, _ = context()
    if plan["field"] != "features":
        fail("a fix plan takes no refactor step")
    rows = [row for row in milestone["features"] if row["ID"] == feature_id]
    if not rows or rows[0]["Type"] != "refactor" or rows[0]["State"] not in ("open", "in progress"):
        fail(f"{feature_id} is not an open or in progress feature of the type refactor of {milestone['id']}")
    for other in active_plans():
        if other["id"] != plan["id"] and other["field"] == "features" and feature_id in other["ids"]:
            fail(f"the active plan {other['id']} holds {feature_id}")
    text = step_text(text)
    if not parse_check(verification):
        fail("the verification must be 'TEST <name> passes', 'COMMAND <name> passes' or 'MANUAL <name>'")
    if not ask(f"Insert the refactor step '{text}' for {feature_id} before the open steps: did the user approve it?", answer):
        fail("the user did not approve the refactor step")
    # a reverted step waits for its new attempt: it goes back to open, so the refactor step runs first
    for row in plan["progress"]:
        if row["State"] == "in progress" and last_record(problems, row["Step"]) == "step reverted":
            row["State"] = "open"
    position = next((index for index, row in enumerate(plan["progress"]) if row["State"] == "open"), None)
    if position is None:
        fail("the plan has no open step")
    step_id = next_id("S", [step["Step"] for step in all_steps(plan)])
    before = plan["progress"][position]["Step"]
    index = next(index for index, step in enumerate(plan["steps"]) if step["Step"] == before)
    plan["steps"].insert(index, {"Step": step_id, "Feature": feature_id, "Text": text, "Verification": verification, "Dependencies": "none"})
    plan["progress"].insert(position, {"Step": step_id, "Feature": feature_id, "State": "open", "Evidence": "", "Round": ""})
    if feature_id not in plan["ids"]:
        plan["ids"].append(feature_id)
    plan["text"] = write_table(plan["text"], "Steps", STEP_HEADER, plan["steps"], plan["rel"])
    plan["text"] = add_verification(plan["text"], verification)
    errors = refactor_order_errors(plan, milestone)
    if errors:
        fail("\n".join(errors))
    save_plan(plan)
    problems.record("refactor added", step_id, feature_id)
    problems.save()
    commit(f"Refactor step added: {plan['id']} {step_id}", [plan["dir"]], verify=False)
    print(f"refactor step {step_id} stands before {before}")


def refactor_order_errors(plan, milestone):
    """Each open refactor step stands before each open step of a feature that is no refactor."""
    refactors = {row["ID"] for row in milestone["features"] if row["Type"] == "refactor"}
    errors, other = [], None
    for row in plan["progress"]:
        if row["State"] != "open":
            continue
        if row["Feature"] not in refactors:
            other = other or row["Step"]
        elif other:
            errors.append(f"{row['Step']}: the refactor step stands after the open step {other} of a feature that is no refactor")
    return errors


def add_verification(text, check):
    """The plan text with one more line in its verification section. A line that the section holds stays once."""
    lines = text.split("\n")
    start = lines.index("## Verification")
    end = start + 1
    while end < len(lines) and not lines[end].startswith("## "):
        end += 1
    held = [line[2:] for line in lines[start + 1 : end] if line.startswith("- ")]
    if check in held:
        return text
    last = max((index for index in range(start + 1, end) if lines[index].startswith("- ")), default=start)
    lines.insert(last + 1, f"- {check}")
    return "\n".join(lines)


def add_check(check, answer):
    """Adds a check line to the verification of the running plan, for a test that a step added and the plan did not
    name, after the approval of the user."""
    plan, milestone, problems, _ = context()
    if not parse_check(check):
        fail("the check must be 'TEST <name> passes', 'COMMAND <name> passes' or 'MANUAL <name>'")
    if not ask(f"Add the check '{check}' to the verification of {plan['id']}: did the user approve it?", answer):
        fail("the user did not approve the check")
    text = add_verification(plan["text"], check)
    if text == plan["text"]:
        print(f"the verification holds {check}")
        return
    plan["text"] = text
    save_plan(plan)
    commit(f"Check added: {plan['id']} {check}", [plan["dir"]], verify=False)
    print(f"the verification holds {check}")


def set_dependencies(step_id, cell, answer=None):
    """Writes the Dependencies cell of a step of the running plan, for a row that a review found, and adds the
    validation of each named row that is a check to the verification of the plan. A cell that drops a named row loosens
    the plan, so it needs the approval of the user."""
    plan, milestone, problems, row = context(step_id)
    step = find_step(plan, step_id)
    if step in plan["fixes"]:
        fail(f"{step_id} is a fix step, it has no Dependencies cell")
    cell = " ".join(cell.split())
    errors = dependency_errors(cell, step_id)
    if errors:
        fail("\n".join(errors))
    old = step["Dependencies"]
    removed = [item for item in old.split() if item != "none" and item not in cell.split()]
    if removed:
        if not ask(f"Remove {' '.join(removed)} from the dependencies of {step_id}: did the user approve it?", answer):
            fail("the user did not approve the removal")
        problems.record("dependencies removed", step_id, "old:", old, "new:", cell)
        problems.save()
    step["Dependencies"] = cell
    plan["text"] = write_table(plan["text"], "Steps", STEP_HEADER, plan["steps"], plan["rel"])
    validations = {item["ID"]: item["Validation"] for item in dependency_rows()}
    for item in cell.split() if cell != "none" else []:
        if parse_check(validations[item]):
            plan["text"] = add_verification(plan["text"], validations[item])
    save_plan(plan)
    commit(f"Dependencies changed: {plan['id']} {step_id}", [plan["dir"]], verify=False)
    print(f"step {step_id} names the dependencies {cell}")


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
    if step["Verification"] == RESEARCH_CHECK:
        errors += research_errors(step_id, step_base(problems, step_id))
    if errors:
        fail("step gate:\n" + "\n".join(errors))
    kind, name = parse_check(step["Verification"])
    if kind == "MANUAL":
        passed, source = manual_answer([problems], name, f"Manual check {name} of step {step_id}: did it pass?", answer)
        problems.record("manual passed" if passed else "manual failed", step_id, name, git("rev-parse", "--short=12", "HEAD"))
        problems.save()
        text = manual_source(by, passed) if source == "answer" else f"{source} holds, no product file changed since"
        test.append_evidence(plan, step_id, name, "MANUAL", 0 if passed else 1, text)
        if not passed:
            commit(f"Manual check recorded: {plan['id']} {step_id}", [problems.path], verify=False)
            errors.append(f"the manual check {name} failed")
    elif kind == "COMMAND":
        code, output = test.execute(kind, name, plan, step_id)
        if code != 0:
            errors.append(f"the verification '{step['Verification']}' fails:\n{output}")
    # one call of the runner: the verification and each test file that the step changed or added
    names = [name] if kind == "TEST" else []
    names += [item for item in test.changed_tests(step_base(problems, step_id)) if item not in names]
    if names:
        code, output = test.execute("TEST", names, plan, step_id)
        if code != 0:
            errors.append(f"the tests {' '.join(names)} fail:\n{output}")
    if not test.evidence_path(plan, step_id).is_file():
        errors.append("the evidence file is missing")
    # the step of a bug shows that its test caught the bug: a failing run before a passing run
    if plan["field"] == "bugs" and step in plan["steps"] and kind == "TEST" and not test.failed_before_passed(plan, step_id, name):
        errors.append(
            f"the evidence of {step_id} must show a failing run of {name} before a passing run:"
            f" run python -m tools.test {name} --step {step_id} on the code before the fix"
        )
    code, output = tool("check")
    if code != 0:
        errors.append(f"python -m tools.check fails:\n{output}")
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
    commit(f"Step blocked: {plan['id']} {step_id}", [plan["dir"]], verify=False)
    print(f"step {step_id} is blocked, ask the user")


def unblock(step_id, answer):
    """Takes the decision of the user on the open Important problems of a blocked step, or of a step in progress
    after its last review round, so the step goes on without a revert."""
    plan, milestone, problems, row = context(step_id)
    held = open_important(step_rows(problems, step_id), rounds(problems, step_id))
    if row["State"] != "blocked" and not (row["State"] == "in progress" and held):
        fail(f"step {step_id} has state {row['State']} and no open Important problem")
    reason = user_reason(answer, f"Open problems of step {step_id}: {' '.join(held) or 'see the step blocked record'}. What does the user decide?")
    changed = []
    for item in step_rows(problems, step_id):
        if not settled(item):
            changed.append(f"{item['ID']}={item['Answer'] or 'open'}")
            item["Answer"] = f"user {reason}"
    problems.record("step unblocked", step_id, "old:", *changed, "new:", f"user {reason}")
    problems.save()
    row["State"] = "in progress"
    plan["meta"]["status"] = "in progress"
    save_plan(plan)
    commit(f"Step unblocked: {plan['id']} {step_id}", [plan["dir"]], verify=False)
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
    commit(f"Fix step added: {plan['id']} {fix_id}", [plan["dir"]], verify=False)
    print(f"fix step {fix_id} added, run step-run")


def problem_context():
    """The plan of the problem commands: the plan of this worktree, or the plan in close in the main repository."""
    plan = require_plan()
    require_branch()
    return plan, Problems(plan)


def find_problem(problems, problem_id):
    rows = [row for row in problems.rows if row["ID"] == problem_id]
    if not rows:
        fail(f"{problems.rel}: the problem {problem_id} does not exist")
    return rows[0]


def save_problems(plan, problems, problem_id, subject):
    """Writes the problems file and commits it. A row that fails the writing rules leaves the file as it was."""
    before = read(problems.path)
    problems.save()
    number = next(index for index, line in enumerate(problems.text.split("\n"), 1) if line.startswith(f"| {problem_id} |"))
    errors = [error for error in docs_lint.lint([problems.rel])[0] if re.match(rf"^.+:{number}: ", error)]
    if errors:
        write(problems.path, before)
        fail("the writing rules of docs/DOCS_CONVENTIONS.md:\n" + "\n".join(errors))
    commit(f"{subject}: {plan['id']} {problem_id}", [problems.path], verify=False)


def one_line(value, name):
    if "|" in value or "\n" in value:
        fail(f"{name} must be one line without '|'")
    return " ".join(value.split())


def add_problem(cells):
    """Appends one problem row that a review posted. The tool gives it the next id."""
    plan, problems = problem_context()
    names = ["Step", "Round", "Severity", "Rule", "Topic", "Location", "Trigger", "Class", "Fix"]
    row = {name: one_line(value, name) for name, value in zip(names, cells)}
    row.update({"ID": next_id("N", [item["ID"] for item in problems.rows]), "Answer": "", "Check": ""})
    errors = row_errors(row, problems.header)
    if row["Step"] != "plan" and row["Step"] not in [step["Step"] for step in all_steps(plan)]:
        errors.append(f"D65: {row['Step']} is no step of {plan['id']}")
    if words(row["Fix"]) > 20:
        errors.append("docs/REVIEW.md, Problem format: Fix is max 20 words")
    if errors:
        fail("the problem is not added:\n" + "\n".join(errors))
    problems.rows.append(row)
    save_problems(plan, problems, row["ID"], "Problem added")
    print(f"problem {row['ID']} added")


def answer_problem(problem_id, answer):
    """Writes the answer of the implementor into one problem. A state tool writes each other answer."""
    plan, problems = problem_context()
    row = find_problem(problems, problem_id)
    answer = one_line(answer, "the answer")
    if row["Answer"].startswith(TOOL_ANSWERS):
        fail(f"D71: the answer '{row['Answer']}' of {problem_id} comes from a tool and stays. A fix step answers its own problems")
    if answer.startswith(TOOL_ANSWERS):
        fail("D71: a tool writes the answers reverted, user and fix. A user answer needs the user key: run the unblock command")
    if not AGENT_ANSWER.match(answer):
        fail("D66: the answer must be 'fixed <commit>', 'closed <wrong|intentional|prevented> <reason>' or 'bug <id>'")
    if (row["Severity"] == "Pre-existing") != answer.startswith("bug "):
        fail("D70: a Pre-existing problem takes the answer 'bug <id>', and only such a problem takes it")
    if answer.startswith("fixed ") and not git_ok("cat-file", "-e", answer.split()[1] + "^{commit}"):
        fail(f"D66: {answer.split()[1]} is no commit")
    row["Answer"] = answer
    save_problems(plan, problems, problem_id, "Problem answered")
    print(f"problem {problem_id} answered")


def check_problem(problem_id, value):
    """Writes the result of a later review round into the Check cell of one problem."""
    plan, problems = problem_context()
    row = find_problem(problems, problem_id)
    value = one_line(value, "the check")
    if not CHECK_CELL.match(value):
        fail("D69: the check must be 'confirmed', 're-raised <trigger>' or 'carried <id>'")
    if value.startswith("carried "):
        carrier = find_problem(problems, value.split()[1])
        if carrier["ID"] <= problem_id or carrier["Step"] != row["Step"]:
            fail(f"D69: the carrier {carrier['ID']} must be a later row of the same step")
    row["Check"] = value
    save_problems(plan, problems, problem_id, "Problem checked")
    print(f"problem {problem_id} checked")


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
    elif command == "unblock" and len(rest) == 1:
        unblock(rest[0], answer)
    elif command == "add-fix" and len(rest) == 2:
        add_fix(*rest)
    elif command == "set-text" and len(rest) == 2:
        set_text(*rest, answer)
    elif command == "insert-refactor" and len(rest) == 3:
        insert_refactor(*rest, answer)
    elif command == "set-dependencies" and len(rest) == 2:
        set_dependencies(*rest, answer)
    elif command == "add-check" and len(rest) == 1:
        add_check(rest[0], answer)
    elif command == "add-problem" and len(rest) == 9:
        add_problem(rest)
    elif command == "answer-problem" and len(rest) == 2:
        answer_problem(*rest)
    elif command == "check-problem" and len(rest) == 2:
        check_problem(*rest)
    else:
        fail(
            "usage: python -m tools.step_close <start|review|revert|block> <step>"
            " | close <step> [--answer yes|no] [--by agent]"
            ' | unblock <step> --answer "<answer of the user>"'
            " | add-fix <problem> <step>"
            ' | set-text <step> "<text>" --answer yes|no'
            ' | set-dependencies <step> "<ids or none>" [--answer yes|no]'
            ' | insert-refactor <feature> "<text>" "<verification>" [--answer yes|no]'
            ' | add-check "<check>" [--answer yes|no]'
            ' | add-problem <step|plan> <round> <severity> <rule> "<topic>" "<location>" "<trigger>" "<class>" "<fix>"'
            ' | answer-problem <problem> "<answer>" | check-problem <problem> "<check>"'
        )


if __name__ == "__main__":
    main(run)
