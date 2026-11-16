import re
import tomllib

from tools._lib import DOCS, PROJECT_FILE, ROOT, active_plans, branch, commit, fail, git, git_ok, main, merging, read, read_table, tool

REQUIRED = ["product_terms", "start_version", "main_branch", "ci", "test_suite", "test_command", "test_support"]
LANGUAGE = ["name", "extensions", "source", "tests", "format", "lint"]
LANGUAGE_HEADER = ["Language", "Formatter", "Linter", "Naming", "Source", "Tests"]
RUNNER_HEADER = ["Runner", "Support folder"]
PLACEHOLDER = "Not initialized."


def errors():
    if not PROJECT_FILE.exists():
        return ["tools/project.toml is missing"]
    try:
        project = tomllib.loads(read(PROJECT_FILE))
    except tomllib.TOMLDecodeError as error:
        return [f"tools/project.toml: {error}"]
    found = [f"tools/project.toml: the key '{key}' is missing" for key in REQUIRED if key not in project]
    if found:
        return found
    if not isinstance(project["product_terms"], list) or not project["product_terms"]:
        found.append("tools/project.toml: product_terms must be a list with the product name")
    if not re.fullmatch(r"\d+\.\d+\.\d+", str(project["start_version"])):
        found.append("tools/project.toml: start_version must have the form 0.0.0")
    if "dependency_source" in project and not isinstance(project["dependency_source"], str):
        found.append("tools/project.toml: dependency_source must be one folder")
    languages = project.get("language")
    if not isinstance(languages, list) or not languages:
        found.append("tools/project.toml: one [[language]] entry is necessary")
        languages = []
    for entry in languages:
        for key in LANGUAGE:
            if key not in entry:
                found.append(f"tools/project.toml: [[language]] {entry.get('name', '')}: the key '{key}' is missing")
    found += folder_errors(project, languages)
    if "{name}" not in project["test_command"] and "{names}" not in project["test_command"]:
        found.append("tools/project.toml: test_command must hold {name} or {names}")
    if "test_report" in project and not isinstance(project["test_report"], str):
        found.append("tools/project.toml: test_report must be the path of one report file")
    if not all(isinstance(value, str) for value in project.get("commands", {}).values()):
        found.append("tools/project.toml: each entry of [commands] must be one command line")
    if project["ci"] != "none" and not (ROOT / project["ci"]).is_file():
        found.append(f"tools/project.toml: ci must be 'none' or the path of the pipeline file, {project['ci']} is missing")
    if not (DOCS / "design" / "PROJECT.md").is_file():
        found.append("docs/design/PROJECT.md is missing")
    if PLACEHOLDER in read(ROOT / "AGENTS.md"):
        found.append("AGENTS.md: the Project section is not written")
    if not (ROOT / ".agents" / "mcp.yaml").is_file():
        found.append(".agents/mcp.yaml is missing")
    code = DOCS / "CODE_CONVENTIONS.md"
    named = {row["Language"] for row in read_table(read(code), "Languages", LANGUAGE_HEADER, "docs/CODE_CONVENTIONS.md")}
    for entry in languages:
        if entry.get("name") not in named:
            found.append(f"docs/CODE_CONVENTIONS.md: the Languages table has no row for {entry.get('name')}")
    test = DOCS / "TEST_CONVENTIONS.md"
    if not read_table(read(test), "Test runner", RUNNER_HEADER, "docs/TEST_CONVENTIONS.md"):
        found.append("docs/TEST_CONVENTIONS.md: the Test runner table is empty")
    return found


def folder_errors(project, languages):
    """The bound folders that do not exist. A project without a file of its languages has no folder yet."""
    code = False
    extensions = tuple(extension for entry in languages for extension in entry.get("extensions", []))
    if extensions and git_ok("rev-parse", "--is-inside-work-tree"):
        code = any(name.endswith(extensions) for name in git("ls-files").splitlines())
    if not code:
        return []
    found = []
    for entry in languages:
        for key in ("source", "tests"):
            for folder in entry.get(key, []):
                if not (ROOT / folder).is_dir():
                    found.append(f"tools/project.toml: [[language]] {entry.get('name', '')}: the {key} folder {folder} does not exist")
    if not (ROOT / str(project["test_support"])).is_dir():
        found.append(f"tools/project.toml: the test_support folder {project['test_support']} does not exist")
    return found


def bind(kind):
    initialized = git_ok("cat-file", "-e", "HEAD:tools/project.toml")
    if kind == "init" and initialized:
        fail("the project is initialized, use project-update")
    if kind == "update" and not initialized:
        fail("not initialized, run project-init")
    if kind == "update" and active_plans():
        fail("a plan is active, close it before project-update")
    found = errors()
    if found:
        fail("\n".join(found))
    if merging() or not branch():
        fail("check out a branch and finish the open merge or rebase")
    project = tomllib.loads(read(PROJECT_FILE))
    if kind == "init" and project["main_branch"] != branch():
        fail(f"tools/project.toml: main_branch must be the checked out branch {branch()}")
    for name in ("provider", "check"):
        code, output = tool(name)
        if code != 0:
            fail(f"python -m tools.{name} failed:\n{output}")
    message = "Project initialized" if kind == "init" else "Project updated"
    if not commit(message):
        fail("no change to commit")
    print(message)


def run(args):
    command = args[0] if args else ""
    if command == "check":
        found = errors()
        if found:
            fail("\n".join(found))
        print("project bindings ok")
    elif command in ("init", "update"):
        bind(command)
    else:
        fail("usage: python -m tools.project <init|update|check>")


if __name__ == "__main__":
    main(run)
