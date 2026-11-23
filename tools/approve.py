import re

from tools._lib import (
    Problems,
    any_match,
    ask,
    changed_since,
    clean_tree,
    commit,
    fail,
    git,
    main,
    protected_patterns,
    require_branch,
    require_main,
    require_plan,
    require_worktree,
    subjects,
    take_option,
    unclean,
)


def step_base(problems, step_id):
    record = problems.last(("step started",), step_id)
    if not record:
        fail(f"step {step_id} was not started")
    return record["ids"][1]


def created_commit(plan):
    """The commit that created the plan."""
    created = f"Plan created: {plan['id']}"
    for commit_hash, subject in subjects():
        if subject == created:
            return commit_hash
    fail(f"the commit '{created}' is missing")


def close_base(plan):
    """The commit that the writes of the plan close follow: the squash commit of the plan."""
    merged = f"Plan merged: {plan['id']}"
    for commit_hash, subject in subjects():
        if subject == merged:
            return commit_hash
    fail(f"the commit '{merged}' is missing, run python -m tools.plan_close merge {plan['id']}")


def run(args):
    answer = take_option(args, "--answer")
    if len(args) != 2:
        fail("usage: python -m tools.approve <plan> <step|close> [--answer yes|no]")
    plan = require_plan()
    if plan["id"] != args[0]:
        fail(f"the active plan is {plan['id']}")
    require_branch()
    if not clean_tree():
        fail(unclean())
    target = args[1]
    if target == "close":
        require_main()
    else:
        require_worktree(plan["id"])
    problems = Problems(plan)
    base = close_base(plan) if target == "close" else step_base(problems, target)
    patterns = protected_patterns()
    touched = [name for name in changed_since(base) if any_match(name, patterns)]
    if not touched:
        print("no protected path changed, no approval is necessary")
        return
    question = f"Approve the changes of {plan['id']} {target} to the protected paths?\n" + "\n".join(touched)
    approved = ask(question, answer)
    problems.record("approved" if approved else "rejected", target, git("rev-parse", "--short=12", "HEAD"))
    problems.save()
    commit(f"Approval recorded: {plan['id']} {target}", [problems.path], verify=False)
    print(f"{'approved' if approved else 'rejected'} {plan['id']} {target}")


if __name__ == "__main__":
    main(run)
