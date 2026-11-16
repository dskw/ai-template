"""Tests of the tools. Each test class builds a scratch repository in the temporary folder from the setup files of
this repository and plays the agent in it. Run: python -m unittest discover tools/tests"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SETUP_PATHS = ["tools", ".agents", "AGENTS.md", "docs/wiki", ".vale.ini", ".gitattributes", ".editorconfig", ".gitignore"]
SETUP_DOCS = ["CODE_CONVENTIONS.md", "TEST_CONVENTIONS.md", "DOCS_CONVENTIONS.md", "REVIEW.md"]
PROJECT_ONLY = ["tools/project.toml", "tools/tests", ".agents/.generated"]

PROJECT = """product_terms = ["Scratch Product"]
start_version = "0.0.0"
main_branch = "main"
ci = "none"
test_suite = "python fake_runner.py"
test_command = "python fake_runner.py {names}"
test_report = "build/junit.xml"
test_support = "tests/support"

[[language]]
name = "fake"
extensions = [".fk"]
source = ["src"]
tests = ["tests"]
format = "python fake_runner.py --none"
lint = "python fake_runner.py --none"
"""

# a test runner for the scratch project: the test <name> is the file tests/<name>.fk and passes when it holds "pass"
RUNNER = '''import pathlib, sys
names = [name for name in sys.argv[1:] if not name.startswith("--")]
if "--none" in sys.argv:
    sys.exit(0)
found = {path.stem: path.read_text().strip() for path in pathlib.Path("tests").glob("*.fk")}
names = names or sorted(found)
cases, code = [], 0
for name in names:
    if name not in found:
        continue
    if found[name] == "pass":
        cases.append(f'<testcase classname="scratch" name="{name}"/>')
    else:
        code = 1
        cases.append(f'<testcase classname="scratch" name="{name}"><failure message="assert">{name} is broken</failure></testcase>')
if not cases:
    code = 1
pathlib.Path("build").mkdir(exist_ok=True)
pathlib.Path("build/junit.xml").write_text("<testsuites><testsuite>" + "".join(cases) + "</testsuite></testsuites>")
print("noise of the runner\\n" * 50)
sys.exit(code)
'''

DEPENDENCIES = """# Dependencies

## Dependencies
| ID | Trigger | Action | Validation |
|---|---|---|---|
| DEP-01 | A step adds another instance of something that exists | Add it in max 3 places, else stop and record a structural extension | The reviewer counts the places in the step diff |

## Records
- added DEP-01 template 2026-01-01
"""


class Scratch:
    """A scratch repository with the setup of this repository and a project of a fake language."""

    def __init__(self):
        self.root = Path(tempfile.mkdtemp(prefix="setup-test-")).resolve()
        for name in SETUP_PATHS:
            source = ROOT / name
            if source.is_dir():
                shutil.copytree(source, self.root / name, ignore=shutil.ignore_patterns("__pycache__"))
            elif source.exists():
                shutil.copy(source, self.root / name)
        for name in SETUP_DOCS:
            shutil.copy(ROOT / "docs" / name, self.root / "docs" / name)
        for name in PROJECT_ONLY:
            path = self.root / name
            shutil.rmtree(path) if path.is_dir() else path.exists() and path.unlink()
        self.write("tools/project.toml", PROJECT)
        self.write("fake_runner.py", RUNNER)
        self.write("docs/DEPENDENCIES.md", DEPENDENCIES)
        self.write("docs/design/PROJECT.md", "# Project\nA scratch product for the tests of the tools.\n")
        self.write("src/main.fk", "start\n")
        self.write("tests/support/keep.fk", "pass\n")
        self.edit("AGENTS.md", r"## Project\n(?:.+\n)+", "## Project\nA scratch product. The design documents are in `docs/design/`.\n")
        self.add_row("docs/CODE_CONVENTIONS.md", "Languages", "| fake | none | none | none | `src` | `tests` |")
        self.add_row("docs/TEST_CONVENTIONS.md", "Test runner", "| fake | `tests/support` |")
        (self.root / "docs/memories").mkdir(parents=True, exist_ok=True)
        for folder in ("docs/milestones/archive", "docs/plans/archive"):
            self.write(f"{folder}/.gitkeep", "")
        self.write(".gitignore", self.read(".gitignore") + "build/\n")
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "core.autocrlf", "false")
        self.tool("provider")
        self.tool("memory_index")
        self.tool("build_wiki_bundle")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "Project initialized")

    def remove(self):
        subprocess.run(["git", "worktree", "prune"], cwd=self.root, capture_output=True)
        shutil.rmtree(self.root, ignore_errors=True)

    def path(self, name, where=None):
        return (where or self.root) / name

    def read(self, name, where=None):
        return self.path(name, where).read_text(encoding="utf-8")

    def write(self, name, text, where=None):
        path = self.path(name, where)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)

    def edit(self, name, pattern, replacement, where=None):
        text, count = re.subn(pattern, lambda _: replacement, self.read(name, where), count=1)
        assert count == 1, f"{name}: {pattern} not found"
        self.write(name, text, where)

    def add_row(self, name, heading, row, where=None):
        """Adds a row below the table of a section, or below the first table when `heading` is empty."""
        lines = self.read(name, where).split("\n")
        index = lines.index(f"## {heading}") if heading else 0
        while not lines[index].startswith("|---"):
            index += 1
        while index + 1 < len(lines) and lines[index + 1].startswith("|"):
            index += 1
        lines.insert(index + 1, row)
        self.write(name, "\n".join(lines), where)

    def run(self, command, where=None, env=None):
        result = subprocess.run(
            command,
            cwd=where or self.root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env={**os.environ, **(env or {})},
        )
        return result.returncode, result.stdout.decode("utf-8", errors="replace").replace("\r\n", "\n")

    def git(self, *args, where=None):
        code, output = self.run(["git", *args], where)
        assert code == 0, f"git {' '.join(args)}:\n{output}"
        return output.strip()

    def tool(self, name, *args, where=None, fails=False, env=None):
        """Runs a tool and returns its output. It must pass, or fail when `fails` is set."""
        code, output = self.run([sys.executable, "-m", f"tools.{name}", *args], where, env)
        assert (code != 0) == fails, f"python -m tools.{name} {' '.join(args)} gave exit {code}:\n{output}"
        return output

    def milestone(self):
        self.tool("milestone_create", "start", "demo")
        name = "docs/milestones/M001-demo.md"
        self.edit(name, r"## Goal\n", "## Goal\nThe user gets the parts alpha and beta.\n")
        self.add_row(name, "Features", "| F01 | Part alpha exists | new | TEST alpha passes | | open |")
        self.add_row(name, "Features", "| F02 | Part beta exists | new | TEST beta passes | | open |")
        self.edit(name, r"## Out of scope\n", "## Out of scope\n- Part gamma\n")
        self.tool("milestone_create", "commit")

    def plan(self, kind, name, feature, test, dependencies="none"):
        """Writes and commits a plan with one step. Returns the plan id and its worktree."""
        output = self.tool("plan_create", "start", kind, name)
        folder = re.search(r"draft: (\S+)/plan.md", output).group(1)
        plan = f"{folder}/plan.md"
        field = "bugs" if kind == "fix" else "features"
        self.edit(plan, rf"{field}: \[\]", f"{field}: [{feature}]")
        self.add_row(plan, "Steps", f"| S01 | {feature} | Add the part {test} | TEST {test} passes | {dependencies} |")
        self.edit(plan, r"## Verification\n", f"## Verification\n- TEST {test} passes\n")
        return folder, plan

    def commit_plan(self, folder):
        self.tool("plan_create", "reviewed")
        output = self.tool("plan_create", "commit")
        plan_id = re.search(r"Plan created: (\S+)", output).group(1)
        return plan_id, Path(re.search(r"worktree: (.+)", output).group(1).strip())

    def step(self, worktree, folder, test, topic=None):
        """Plays one step in a worktree: start, code, evidence, review, close. With `topic` the review posts one
        Important problem that the second round confirms."""
        self.tool("step_close", "start", "S01", where=worktree)
        self.write(f"src/{test}.fk", "part\n", worktree)
        self.write(f"tests/{test}.fk", "pass\n", worktree)
        self.git("add", "-A", where=worktree)
        self.git("commit", "-q", "-m", f"Add the part {test}", where=worktree)
        self.tool("test", test, "--step", "S01", where=worktree)
        self.tool("step_close", "review", "S01", where=worktree)
        if topic:
            problems = f"{folder}/problems.md"
            row = f"| N01 | S01 | 1 | Important | C01 | {topic} | src/{test}.fk:1 | The part loses its state | {test} only | Keep the state | | |"
            self.add_row(problems, "Problems", row, worktree)
            self.edit(problems, r"\| Keep the state \| \| \|", "| Keep the state | fixed abc1234 | |", worktree)
            self.tool("step_close", "review", "S01", where=worktree)
            self.edit(problems, r"\| fixed abc1234 \| \|", "| fixed abc1234 | confirmed |", worktree)
        self.git("add", "-A", where=worktree)
        self.git("commit", "-q", "-m", "Review answers", "--allow-empty", where=worktree)
        return self.tool("step_close", "close", "S01", where=worktree)

    def review_plan(self, worktree):
        self.tool("plan_close", "reviewed", where=worktree)
        return self.tool("plan_close", "review-passed", where=worktree)

    def close_plan(self, plan_id):
        self.tool("plan_close", "merge", plan_id)
        output = self.tool("plan_close", "tuning")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "Close writes")
        return output + self.tool("plan_close")


class ParallelPlans(unittest.TestCase):
    """Two plans of one milestone run in two worktrees at the same time and close one after the other."""

    @classmethod
    def setUpClass(cls):
        cls.repo = Scratch()

    @classmethod
    def tearDownClass(cls):
        cls.repo.remove()

    def test_lifecycle(self):
        repo = self.repo
        repo.tool("project", "check")
        repo.milestone()

        # a step without a Dependencies cell does not pass, and the document review record reaches the draft
        folder, plan = repo.plan("feature", "alpha", "F01", "alpha", dependencies="")
        self.assertIn("document review recorded", repo.tool("plan_create", "reviewed"))
        self.assertIn("document reviewed", repo.read(f"{folder}/problems.md"))
        self.assertIn("the Dependencies cell is empty", repo.tool("plan_create", "commit", fails=True))
        repo.edit(plan, r"passes \|  \|\n", "passes | DEP-07 |\n")
        self.assertIn("DEP-07 is not an id", repo.tool("plan_create", "commit", fails=True))
        repo.edit(plan, r"DEP-07", "none")
        first, tree_one = repo.commit_plan(folder)
        self.assertTrue(tree_one.is_dir())

        # a second plan runs at the same time, but not for a feature that an active plan holds
        folder_two, plan_two = repo.plan("feature", "beta", "F01", "beta")
        self.assertIn(f"the active plan {first} holds F01", repo.tool("plan_create", "commit", fails=True))
        repo.edit(plan_two, r"features: \[F01\]", "features: [F02]")
        repo.edit(plan_two, r"\| S01 \| F01 \|", "| S01 | F02 |")
        second, tree_two = repo.commit_plan(folder_two)
        status = repo.tool("progress", "status")
        self.assertIn(f"plan {first}: in progress in the worktree", status)
        self.assertIn(f"plan {second}: in progress in the worktree", status)

        # the step tools run in the worktree only, and a worktree writes no shared file of the milestone
        self.assertIn("run this command in", repo.tool("step_close", "start", "S01", fails=True))
        self.assertIn("main repository", repo.tool("ideas", "add", "An idea", "user", where=tree_one, fails=True))
        self.assertIn("next step S01", repo.tool("progress", "status", where=tree_one))

        # both steps run, each in its worktree, and each review posts a problem with the same topic
        repo.tool("step_close", "start", "S01", where=tree_two)
        self.assertIn("Step closed", repo.step(tree_one, folder, "alpha", topic="restart state"))
        repo.write("src/beta.fk", "part\n", tree_two)
        repo.write("tests/beta.fk", "fail\n", tree_two)
        repo.git("add", "-A", where=tree_two)
        repo.git("commit", "-q", "-m", "Add the part beta", where=tree_two)

        # a failed run prints the count and the failed test only, a passed run one line
        failed = repo.tool("test", "beta", "--step", "S01", where=tree_two, fails=True)
        self.assertIn("passed 0, failed 1", failed)
        self.assertIn("--- failed: scratch beta", failed)
        self.assertNotIn("noise of the runner", failed)
        repo.write("tests/beta.fk", "pass\n", tree_two)
        repo.git("commit", "-q", "-am", "Fix the part beta", where=tree_two)
        passed = repo.tool("test", "beta", "keep", "--step", "S01", where=tree_two, fails=True)
        self.assertIn("no test has the name keep", passed)
        self.assertEqual(repo.tool("test", "beta", where=tree_two).split("\n")[0], "passed 1")

        # a tool commits its state files, and no other commit takes one
        self.assertEqual(repo.git("status", "--porcelain", where=tree_two), "")
        progress = f"{folder_two}/progress.md"
        repo.write(progress, repo.read(progress, tree_two).replace("in progress", "complete"), tree_two)
        repo.git("add", "-A", where=tree_two)
        self.assertIn("only a tool commits these files", repo.tool("check", "--staged", where=tree_two, fails=True))
        repo.git("reset", "-q", "--hard", "HEAD", where=tree_two)

        repo.tool("step_close", "review", "S01", where=tree_two)
        problems = f"{folder_two}/problems.md"
        row = "| N01 | S01 | 1 | Important | C01 | restart state | src/beta.fk:1 | The part loses its state | beta only | Keep the state | fixed abc1234 | |"
        repo.add_row(problems, "Problems", row, tree_two)
        repo.tool("step_close", "review", "S01", where=tree_two)
        repo.edit(problems, r"\| fixed abc1234 \| \|", "| fixed abc1234 | confirmed |", tree_two)
        repo.git("commit", "-q", "-am", "Review answers", where=tree_two)
        self.assertIn("Step closed", repo.tool("step_close", "close", "S01", where=tree_two))

        # the first plan closes: review in the worktree, merge and close in the main repository
        self.assertIn("Plan synced", repo.tool("plan_close", "sync", where=tree_one))
        self.assertIn("holds the tip", repo.tool("plan_close", "sync", where=tree_one))
        self.assertIn("Review passed", repo.review_plan(tree_one))
        step_commit = repo.git("log", "--format=%H", "--grep=^Step closed:", "-1", where=tree_one)
        repo.close_plan(first)
        self.assertFalse(tree_one.exists())
        self.assertEqual(repo.git("branch", "--list", f"plan/{first}"), "")
        repo.git("merge-base", "--is-ancestor", step_commit, f"closed/{first}")
        log = repo.git("log", "--format=%s")
        self.assertIn(f"Plan merged: {first}", log)
        self.assertNotIn("Add the part alpha", log)

        # the second plan must hold the tip of the milestone branch before its merge
        self.assertIn("Review passed", repo.review_plan(tree_two))
        self.assertIn("does not hold the tip", repo.tool("plan_close", "merge", second, fails=True))
        self.assertIn("Plan synced", repo.tool("plan_close", "sync", where=tree_two))
        output = repo.close_plan(second)
        self.assertIn("tune topic restart state", output)
        self.assertIn("M001 demo | 2 | 2 |", repo.read("docs/milestones/PROGRESS.md"))

        # the milestone close keeps the commits of the milestone branch under a tag
        tip = repo.git("rev-parse", "HEAD")
        repo.tool("milestone_close")
        self.assertEqual(repo.git("branch", "--show-current"), "main")
        repo.git("merge-base", "--is-ancestor", tip, "milestone/M001")
        self.assertEqual(repo.git("branch", "--list", "milestone/*"), "")


class OtherPlans(unittest.TestCase):
    """A fix plan, a refactor plan with the removal of a dependency, and a sync with a conflict."""

    @classmethod
    def setUpClass(cls):
        cls.repo = Scratch()

    @classmethod
    def tearDownClass(cls):
        cls.repo.remove()

    def test_fix_refactor_and_conflict(self):
        repo = self.repo
        repo.milestone()
        repo.tool("progress", "add-bug", "Part gamma is broken", "", "user", "TEST bug_gamma passes")
        self.assertEqual(repo.git("status", "--porcelain"), "")

        # a fix plan: the evidence shows the failing run before the passing run, the close removes the bug
        folder, _ = repo.plan("fix", "gamma", "B01", "bug_gamma")
        fix, tree = repo.commit_plan(folder)
        repo.tool("step_close", "start", "S01", where=tree)
        repo.write("tests/bug_gamma.fk", "fail\n", tree)
        repo.git("add", "-A", where=tree)
        repo.git("commit", "-q", "-m", "Regression test", where=tree)
        repo.tool("test", "bug_gamma", "--step", "S01", where=tree, fails=True)
        repo.write("tests/bug_gamma.fk", "pass\n", tree)
        repo.git("commit", "-q", "-am", "Fix part gamma", where=tree)
        repo.tool("test", "bug_gamma", "--step", "S01", where=tree)
        repo.tool("step_close", "review", "S01", where=tree)
        repo.git("commit", "-q", "-am", "Review", "--allow-empty", where=tree)
        repo.tool("step_close", "close", "S01", where=tree)
        repo.tool("plan_close", "sync", where=tree)
        repo.review_plan(tree)
        repo.tool("plan_close", "merge", fix)
        self.assertIn("bug verified B01", repo.tool("plan_close", "verify-bug", "B01"))
        repo.tool("plan_close", "tuning")
        repo.git("add", "-A")
        repo.git("commit", "-q", "-m", "Close writes")
        repo.tool("plan_close")
        self.assertIn("Bug fixed: M001 B01", repo.git("log", "--format=%s"))
        self.assertNotIn("B01", repo.read("docs/milestones/M001-demo.md"))

        # a refactor is a feature of its own type with a refactor plan; its close can remove a dependency
        repo.tool("dependency", "add", "A step adds state", "Carry it", "TEST alpha passes", "M001")
        repo.tool("progress", "add-feature", "M001", "refactor", "Share the code of the parts", "TEST shared passes")
        folder, plan = repo.plan("feature", "shared", "F03", "shared")
        self.assertIn("is not an open or in progress feature that is no refactor", repo.tool("plan_create", "commit", fails=True))
        repo.edit(plan, r"type: feature", "type: refactor")
        refactor, tree = repo.commit_plan(folder)

        # a second plan changes the same file, so the later sync has a conflict
        folder_two, _ = repo.plan("feature", "alpha", "F01", "alpha")
        other, tree_two = repo.commit_plan(folder_two)
        repo.write("src/main.fk", "start of the refactor\n", tree)
        repo.git("commit", "-q", "-am", "Change the start", where=tree)
        self.assertIn("Step closed", repo.step(tree, folder, "shared"))
        repo.write("src/main.fk", "start of alpha\n", tree_two)
        repo.git("commit", "-q", "-am", "Change the start", where=tree_two)
        self.assertIn("Step closed", repo.step(tree_two, folder_two, "alpha"))

        repo.tool("plan_close", "sync", where=tree)
        repo.review_plan(tree)
        repo.tool("plan_close", "merge", refactor)
        self.assertIn("removed DEP-02", repo.tool("dependency", "remove", "DEP-02", "The parts share the state"))
        repo.tool("plan_close", "tuning")
        repo.git("add", "-A")
        repo.git("commit", "-q", "-m", "Close writes")
        # the dependencies file is a protected path, so the close needs the approval of the user
        self.assertIn("protected paths changed without approval", repo.tool("plan_close", fails=True))
        repo.tool("approve", refactor, "close", "--answer", "yes")
        repo.tool("plan_close")

        repo.review_plan(tree_two)
        self.assertIn("merge conflict in", repo.tool("plan_close", "sync", where=tree_two, fails=True))
        repo.write("src/main.fk", "start of the refactor and of alpha\n", tree_two)
        repo.git("add", "-A", where=tree_two)
        self.assertIn("Plan synced with conflicts", repo.tool("plan_close", "sync", where=tree_two))
        self.assertIn("changed after its review", repo.tool("plan_close", "merge", other, fails=True))
        self.assertEqual(repo.git("status", "--porcelain"), "")
        repo.review_plan(tree_two)
        repo.close_plan(other)
        self.assertEqual(repo.read("src/main.fk"), "start of the refactor and of alpha\n")
        # the refactor gives no changelog line
        repo.tool("progress", "drop-feature", "F02", "Not needed")
        repo.tool("milestone_close")
        changelog = repo.read("CHANGELOG.md")
        self.assertIn("New feature: Part alpha exists", changelog)
        self.assertNotIn("Share the code", changelog)


class Bindings(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo = Scratch()

    @classmethod
    def tearDownClass(cls):
        cls.repo.remove()

    def test_missing_folder_fails_the_project_check(self):
        repo = self.repo
        repo.edit("tools/project.toml", r'test_support = "tests/support"', 'test_support = "tests/none"')
        self.assertIn("the test_support folder tests/none does not exist", repo.tool("project", "check", fails=True))
        repo.edit("tools/project.toml", r'test_support = "tests/none"', 'test_support = "tests/support"')
        repo.tool("project", "check")

    def test_dependency_tool(self):
        repo = self.repo
        self.assertIn("added DEP-02", repo.tool("dependency", "add", "A step adds state", "Carry it", "TEST state passes", "M001"))
        self.assertIn("- added DEP-02 M001", repo.read("docs/DEPENDENCIES.md"))
        self.assertIn("only in the close of a refactor plan", repo.tool("dependency", "remove", "DEP-02", "No value", fails=True))
        for _ in range(7):
            repo.tool("dependency", "add", "A step adds state", "Carry it", "TEST state passes", "M001")
        self.assertIn("maximum of 9", repo.tool("dependency", "add", "A step adds state", "Carry it", "TEST state passes", "M001", fails=True))

    def test_wiki_structure(self):
        repo = self.repo
        repo.tool("build_wiki_bundle")
        repo.tool("build_wiki_bundle", "check")
        page = ["# Broken", "", "## What it does", "Nothing.", "", "[Gone](gone.md)", ""]
        repo.write("docs/wiki/systems/broken.md", "\n".join(page))
        repo.tool("build_wiki_bundle")
        output = repo.tool("build_wiki_bundle", "check", fails=True)
        self.assertIn("the sidebar must list systems/broken.md once", output)
        self.assertIn("the page map has no row for systems/broken.md", output)
        self.assertIn("the section 'Gotchas' is missing", output)
        self.assertIn("the link gone.md names no page", output)
        (repo.root / "docs/wiki/systems/broken.md").unlink()
        repo.tool("build_wiki_bundle")
        self.assertIn('href="assets/theme.css"', repo.read("docs/wiki/index.html"))
        self.assertTrue((repo.root / "docs/wiki/assets/theme.css").is_file())

    def test_ask_rule_for_the_answer_of_the_user(self):
        self.assertIn('"Bash(* --answer *)"', self.repo.read(".claude/settings.json"))


class Rounds(unittest.TestCase):
    def test_acceptance_keeps_the_review_rounds_of_the_step(self):
        sys.path.insert(0, str(ROOT))
        from tools.step_close import rounds

        class Records:
            def __init__(self, *kinds):
                self.records = [{"type": kind, "ids": ["S01"]} for kind in kinds]

        reviewed = ["step reviewed"] * 3
        self.assertEqual(rounds(Records(*reviewed, "step unblocked"), "S01"), 3)
        self.assertEqual(rounds(Records(*reviewed, "step reverted", "step reviewed"), "S01"), 1)
        self.assertEqual(rounds(Records(*reviewed, "step blocked", "step unblocked"), "S01"), 0)


if __name__ == "__main__":
    unittest.main()


class Research(unittest.TestCase):
    def test_research_file_and_research_step(self):
        repo = Scratch()
        self.addCleanup(repo.remove)
        repo.milestone()
        folder, plan = repo.plan("feature", "alpha", "F01", "alpha")
        repo.edit(plan, r"\| S01 \| F01 \| Add the part alpha \| TEST alpha passes \|", "| S01 | F01 | Which way builds the part alpha | COMMAND research_check passes |")
        repo.add_row(plan, "Steps", "| S02 | F01 | Add the part alpha | TEST alpha passes | none |")
        repo.edit(plan, r"## Verification\n", "## Verification\n- COMMAND research_check passes\n")
        plan_id, worktree = repo.commit_plan(folder)
        repo.tool("step_close", "start", "S01", where=worktree)
        repo.tool("step_close", "review", "S01", where=worktree)
        self.assertIn("added no research file", repo.tool("step_close", "close", "S01", where=worktree, fails=True))
        self.assertIn("docs/research/R001-alpha-way.md", repo.tool("research", "start", "alpha-way", where=worktree))
        output = repo.tool("research", "check", "R001", where=worktree, fails=True)
        self.assertIn("must hold the date and the scope", output)
        self.assertIn("the section ## Sources is empty", output)
        name = "docs/research/R001-alpha-way.md"
        text = repo.read(name, worktree).replace("Scope:", "Scope: the ways to build the part alpha.")
        repo.write(name, text.replace("## Sources\n", "Any shape fits here.\n\n## Recommendation\nBuild it the short way.\n\n## Sources\n- The design.\n"), worktree)
        self.assertIn("committed", repo.tool("research", "commit", "R001", where=worktree))
        repo.write("src/extra.fk", "part\n", worktree)
        repo.git("add", "-A", where=worktree)
        repo.git("commit", "-q", "-m", "Code in a research step", where=worktree)
        self.assertIn("changed source or test files: src/extra.fk", repo.tool("step_close", "close", "S01", where=worktree, fails=True))
        repo.git("rm", "-q", "src/extra.fk", where=worktree)
        repo.git("commit", "-q", "-m", "Remove the code", where=worktree)
        self.assertIn("Step closed", repo.tool("step_close", "close", "S01", where=worktree))
        repo.tool("step_close", "set-text", "S02", "Add the part alpha the short way of R001", where=worktree)
        self.assertIn("| S02 | F01 | Add the part alpha the short way of R001 |", repo.read(plan, worktree))
        self.assertIn("only an open step", repo.tool("step_close", "set-text", "S01", "A new question", where=worktree, fails=True))
        self.assertIn("R002", repo.tool("research", "start", "second", where=worktree))
