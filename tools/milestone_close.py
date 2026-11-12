import datetime
import os
import shutil

from tools import milestone_create, progress, test
from tools._lib import (
    CHANGELOG,
    MILESTONES,
    PLANS,
    Problems,
    active_plan,
    ask,
    branch,
    commit,
    current_version,
    fail,
    find_milestone,
    git,
    git_dir,
    load_project,
    main,
    milestone_branch,
    milestones,
    open_milestone,
    parse_check,
    plans,
    read,
    rel,
    require_branch,
    run as shell,
    save_milestone,
    subjects,
    take_option,
    today,
    tool,
    write,
)

MANUAL = ("milestone manual passed", "milestone manual failed")
TMP = MILESTONES / "tmp"


def done_plan(milestone, feature_id):
    for plan in plans():
        if plan["archived"] and plan["meta"]["milestone"] == milestone["id"] and feature_id in plan["meta"]["done"]:
            return plan
    return None


def check(args, answer):
    milestone = open_milestone()
    if not milestone:
        fail("no open milestone")
    require_branch()
    code = 0
    for row in milestone["features"]:
        if row["State"] != "done" or (args and row["ID"] not in args):
            continue
        kind, name = parse_check(row["Acceptance"])
        if kind == "MANUAL":
            if answer is None and not os.isatty(0):
                print(f"{row['ID']} MANUAL {name}: ask the user, then run python -m tools.milestone_close check {row['ID']} --answer yes|no")
                code = 1
                continue
            passed = ask(f"Manual check {name} for {row['ID']}: did it pass?", answer)
            problems = Problems(done_plan(milestone, row["ID"]))
            problems.record(MANUAL[0] if passed else MANUAL[1], row["ID"])
            problems.save()
        else:
            passed = test.execute(kind, name)[0] == 0
        print(f"{row['ID']} {row['Acceptance']}: {'pass' if passed else 'fail'}")
        code = code if passed else 1
    return code


def gate(milestone, migrate):
    errors = []
    pending = [p["id"] for p in plans() if p["meta"]["milestone"] == milestone["id"] and not p["archived"]]
    if pending:
        errors.append("plans are not archived: " + " ".join(pending))
    allowed = ("done", "dropped", "open", "in progress") if migrate else ("done", "dropped")
    for row in milestone["features"]:
        if row["State"] not in allowed:
            errors.append(f"{row['ID']} has state {row['State']}")
    if milestone["bugs"] and not migrate:
        errors.append("open bugs: " + " ".join(row["ID"] for row in milestone["bugs"]))
    errors += progress.check_errors()
    if errors:
        fail("milestone gate:\n" + "\n".join(errors))
    for row in milestone["features"]:
        if row["State"] != "done":
            continue
        kind, name = parse_check(row["Acceptance"])
        if kind == "MANUAL":
            record = Problems(done_plan(milestone, row["ID"])).last(MANUAL, row["ID"])
            if not record or record["type"] != MANUAL[0]:
                errors.append(f"{row['ID']}: the manual check {name} has no pass, run python -m tools.milestone_close check")
        elif test.execute(kind, name)[0] != 0:
            errors.append(f"{row['ID']}: the acceptance check '{row['Acceptance']}' fails")
    if errors:
        fail("milestone gate:\n" + "\n".join(errors))


def fixed_bugs(milestone):
    code, output = shell(["git", "log", "--format=%s%x00%b%x01", f"--grep=^Bug fixed: {milestone['id']} "])
    bugs = []
    for entry in output.split("\x01"):
        subject, _, body = entry.strip().partition("\x00")
        if subject.startswith(f"Bug fixed: {milestone['id']} ") and body.strip():
            bugs.append(body.strip().splitlines()[0])
    return bugs


def released(milestone_id, ref="HEAD"):
    code, output = shell(["git", "log", "--format=%s", ref])
    for subject in output.splitlines() if code == 0 else []:
        if subject.startswith("Version: "):
            return subject[len("Version: ") :]
        if subject.startswith("Plan closed: ") or subject == f"Milestone created: {milestone_id}":
            return None
    return None


def release(milestone):
    version = released(milestone["id"])
    if version:
        return version
    done = [row for row in milestone["features"] if row["State"] == "done"]
    bugs = fixed_bugs(milestone)
    if not done and not bugs:
        return None
    numbers, previous = current_version()
    numbers = [numbers[0], numbers[1] + 1, 0] if done else [numbers[0], numbers[1], numbers[2] + 1]
    version = ".".join(str(number) for number in numbers)
    lines = [f"- {'New feature' if row['Type'] == 'new' else 'Update'}: {row['Feature']}" for row in done]
    lines += [f"- Bugfix: {text}" for text in bugs]
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"# {version} {stamp}\n" + "\n".join(lines) + "\n"
    write(CHANGELOG, entry + ("\n" + previous.strip("\n") + "\n" if previous.strip() else ""))
    commit(f"Version: {version}", [CHANGELOG])
    print(f"Version: {version}")
    return version


def clear_tmp():
    shutil.rmtree(TMP, ignore_errors=True)
    if TMP.exists():
        fail(f"{rel(TMP)} is in use: close the manual check package, then run the close again")


def archive(milestone, paths=None):
    milestone["meta"]["status"] = "closed"
    milestone["meta"]["closed"] = today()
    save_milestone(milestone)
    source = milestone["path"]
    os.rename(source, MILESTONES / "archive" / source.name)
    progress.regenerate()
    subject = f"Milestone closed: {milestone['id']}"
    commit(subject, paths and [source, *paths])
    print(subject)


def closed_branch():
    current = branch()
    if current.startswith("milestone/") and subjects()[0][1].startswith("Milestone closed: "):
        return current
    return None


def squash_marker():
    return git_dir() / "MILESTONE_SQUASH"


def summary(name):
    milestone = next(m for m in milestones() if m["archived"] and milestone_branch(m) == name)
    version = released(milestone["id"], name)
    title = f"Milestone closed: {milestone['id']}" + (f" {version}" if version else "")
    lines = [title, "", milestone_create.section(milestone["text"], "Goal") or ""]
    for state, label in (("done", "Done"), ("dropped", "Dropped"), ("migrated", "Migrated")):
        rows = [row["Feature"] for row in milestone["features"] if row["State"] == state]
        if rows:
            lines += ["", f"{label}:"] + [f"- {text}" for text in rows]
    return "\n".join(lines)


def merge():
    conflicts_file = git_dir() / "MILESTONE_CONFLICTS"
    marker = squash_marker()
    main_branch = load_project()["main_branch"]
    if not marker.exists():
        name = closed_branch()
        if not name:
            return
        git("checkout", main_branch)
        write(marker, name + "\n")
        code, output = shell(["git", "merge", "--squash", name])
        conflicts = git("diff", "--name-only", "--diff-filter=U").splitlines()
        if conflicts:
            write(conflicts_file, "\n".join(conflicts) + "\n")
            fail(
                "merge conflict in:\n" + "\n".join(conflicts) + "\nResolve the files and run git add."
                " Then run the same command again"
            )
        if code != 0:
            fail(f"git merge failed:\n{output}")
    name = read(marker).strip()
    if git("diff", "--name-only", "--diff-filter=U"):
        fail("the merge has files with a conflict, resolve them and run git add")
    message = summary(name)
    if conflicts_file.exists():
        for check in ("check", "test"):
            code, output = tool(check)
            if code != 0:
                fail(f"python -m tools.{check} fails after the conflict resolution:\n{output}")
        message += "\n\nConflicts resolved in:\n" + read(conflicts_file)
        conflicts_file.unlink()
    git("commit", "-m", message)
    git("branch", "-D", name)
    marker.unlink()
    print(f"merged {name} into {main_branch} as one commit")


def close():
    if squash_marker().exists():
        return merge()
    milestone = open_milestone()
    if milestone:
        require_branch(milestone_branch(milestone))
        gate(milestone, False)
        clear_tmp()
        release(milestone)
        archive(milestone)
    elif not closed_branch():
        require_branch()
        print("no open milestone")
    merge()


def migrate(new_id):
    old = None if squash_marker().exists() else open_milestone()
    new = find_milestone(new_id)
    if old and old["id"] != new_id:
        require_branch(milestone_branch(old))
        if active_plan():
            fail(f"plan {active_plan()['id']} is active, close it first")
        if new["meta"]["status"] != "draft":
            fail(f"{new['rel']} must have status draft")
        moving = [row for row in old["features"] if row["State"] in ("open", "in progress")]
        errors = milestone_create.validate(new, milestones())
        for number, row in enumerate(moving):
            if number >= len(new["features"]) or new["features"][number]["Feature"] != row["Feature"]:
                errors.append(f"{new['rel']}: feature row {number + 1} must be the migrated feature '{row['Feature']}'")
        for number, row in enumerate(old["bugs"]):
            if number >= len(new["bugs"]) or new["bugs"][number]["Bug"] != row["Bug"]:
                errors.append(f"{new['rel']}: bug row {number + 1} must be the migrated bug '{row['Bug']}'")
        if errors:
            fail("\n".join(errors))
        gate(old, True)
        clear_tmp()
        release(old)
        for number, row in enumerate(moving, 1):
            row["State"], row["Plans"] = "migrated", f"{new_id}-F{number:02d}"
        old["bugs"] = []
        archive(old, [MILESTONES / "archive", MILESTONES / "PROGRESS.md", PLANS])
    merge()
    new = find_milestone(new_id)
    if new["meta"]["status"] == "draft":
        require_branch(load_project()["main_branch"])
        git("checkout", "-b", milestone_branch(new))
        new["meta"]["status"] = "open"
        save_milestone(new)
        progress.regenerate()
        commit(f"Milestone created: {new_id}")
        print(f"Milestone created: {new_id}")


def run(args):
    answer = take_option(args, "--answer")
    if not args:
        return close()
    if args[0] == "check":
        return check(args[1:], answer)
    if args[0] == "migrate" and len(args) == 2:
        return migrate(args[1])
    fail("usage: python -m tools.milestone_close [check [<feature> --answer yes|no] | migrate <new milestone id>]")


if __name__ == "__main__":
    main(run)
