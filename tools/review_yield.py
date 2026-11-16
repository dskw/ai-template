"""Counts what each review kind found in the archived plans: reviews per round, problems per severity and what
became of them, next to the bugs that the milestones fixed later."""

from collections import Counter

from tools._lib import CHANGELOG, Problems, main, plans, read

KINDS = ("step review", "plan review")
ROUNDS = ("1", "2", "3")


def outcome(row):
    answer = row["Answer"]
    if answer.startswith(("fixed", "fix ")):
        return "fixed"
    if answer.startswith("closed wrong"):
        return "wrong"
    if answer.startswith("closed"):
        return "closed"
    if answer.startswith("bug"):
        return "bug"
    return "other" if answer else "open"


def reviews(problems):
    """The reviews of a plan as (kind, subject, round) from its records: each step and the plan count their rounds."""
    rounds = Counter()
    found = []
    for record in problems.records:
        if record["type"] == "step reviewed":
            subject = record["ids"][0]
            rounds[subject] += 1
            found.append(("step review", subject, str(min(rounds[subject], 3))))
        elif record["type"] == "plan reviewed":
            rounds["plan"] += 1
            found.append(("plan review", "plan", str(min(rounds["plan"], 3))))
    return found


def counts():
    held = Counter()
    posted = Counter()
    problems_found = Counter()
    for plan in plans():
        if not plan["archived"]:
            continue
        problems = Problems(plan)
        for kind, subject, round_number in reviews(problems):
            held[(kind, round_number)] += 1
            if any(row["Step"] == subject and row["Round"] == round_number for row in problems.rows):
                posted[(kind, round_number)] += 1
        for row in problems.rows:
            kind = "plan review" if row["Step"] == "plan" else "step review"
            problems_found[(kind, row["Round"], row["Severity"], outcome(row))] += 1
    return held, posted, problems_found


def fixed_bugs():
    """The bugs that each closed milestone fixed, from the changelog: bugs that no review prevented."""
    bugs = Counter()
    version = None
    for line in read(CHANGELOG).split("\n") if CHANGELOG.exists() else []:
        if line.startswith("# "):
            version = line[2:].split(" - ")[0]
        elif line.startswith("- Bugfix:") and version:
            bugs[version] += 1
    return bugs


def report():
    held, posted, found = counts()
    lines = [
        "| Review | Round | Reviews | With a problem | Important fixed | Nit fixed | Closed | Wrong | Bugs |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for kind in KINDS:
        for round_number in ROUNDS:
            def total(severity=None, result=None):
                return sum(
                    count
                    for (k, r, s, o), count in found.items()
                    if k == kind and r == round_number and (severity is None or s == severity) and (result is None or o == result)
                )
            lines.append(
                f"| {kind} | {round_number} | {held[(kind, round_number)]} | {posted[(kind, round_number)]} | "
                f"{total('Important', 'fixed')} | {total('Nit', 'fixed')} | {total(result='closed')} | "
                f"{total(result='wrong')} | {total(result='bug')} |"
            )
    topics = Counter()
    for plan in plans():
        if plan["archived"]:
            topics.update({row["Topic"].lower() for row in Problems(plan).rows if row["Severity"] == "Important" and row["Topic"]})
    if topics:
        lines += ["", "| Topic | Plans with an Important problem |", "|---|---|"]
        lines += [f"| {topic} | {count} |" for topic, count in sorted(topics.items(), key=lambda item: (-item[1], item[0]))]
    bugs = fixed_bugs()
    lines.append("")
    lines.append("Bugs fixed per version, found after the reviews: " + ", ".join(f"{v} {n}" for v, n in sorted(bugs.items())))
    return "\n".join(lines)


def run(args):
    if args:
        raise SystemExit("usage: python -m tools.review_yield")
    print(report())


if __name__ == "__main__":
    main(run)
