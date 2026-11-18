import re
import tomllib

from tools._lib import (
    DOCS,
    MILESTONES,
    PLANS,
    PROJECT_FILE,
    ROOT,
    active_plans,
    branch,
    load_project,
    commit,
    fail,
    git,
    git_ok,
    main,
    main_root,
    merging,
    read,
    read_table,
    rel,
    run as shell,
    tool,
)

REQUIRED = ["product_terms", "start_version", "main_branch", "ci", "test_suite", "test_command", "test_run_limit", "test_support"]
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
        if "comments" in entry and not isinstance(entry["comments"], str):
            found.append(f"tools/project.toml: [[language]] {entry.get('name', '')}: comments must be one command line")
    found += folder_errors(project, languages)
    if "{name}" not in project["test_command"] and "{names}" not in project["test_command"]:
        found.append("tools/project.toml: test_command must hold {name} or {names}")
    if "test_report" in project and not isinstance(project["test_report"], str):
        found.append("tools/project.toml: test_report must be the path of one report file")
    if not isinstance(project["test_run_limit"], int) or isinstance(project["test_run_limit"], bool) or project["test_run_limit"] < 1:
        found.append("tools/project.toml: test_run_limit must be a number of seconds")
    if not is_text_list(project.get("test_binaries", [])):
        found.append("tools/project.toml: test_binaries must be a list of globs")
    start_script = project.get("start_script", {})
    if not isinstance(start_script, dict) or not all(isinstance(value, str) and value and "." not in value for value in start_script.values()):
        found.append("tools/project.toml: [start_script] maps each platform to a file type without dot, for example windows = \"bat\"")
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


def is_text_list(value):
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


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


def binding_paths():
    """The changed files that the binding commit takes. An untracked draft of a running plan or milestone creation
    belongs to its own tool and stays out of the commit."""
    code, output = shell(["git", "status", "--porcelain", "--untracked-files=all"])
    drafts = (rel(PLANS) + "/", rel(MILESTONES) + "/")
    paths = []
    for line in output.splitlines():
        if len(line) <= 3:
            continue
        names = [name.strip('"') for name in line[3:].split(" -> ")]
        if line.startswith("??") and names[-1].startswith(drafts):
            continue
        paths += names
    return paths


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
    paths = binding_paths()
    if not paths or not commit(message, paths):
        fail("no change to commit")
    print(message)


def source():
    """The absolute path of the dependency sources, resolved from the main repository. A worktree of a plan holds no
    copy of them."""
    folder = load_project().get("dependency_source")
    print((main_root() / folder).resolve().as_posix() if folder else "none")


def run(args):
    command = args[0] if args else ""
    if command == "source":
        source()
    elif command == "check":
        found = errors()
        if found:
            fail("\n".join(found))
        print("project bindings ok")
    elif command in ("init", "update"):
        bind(command)
    else:
        fail("usage: python -m tools.project <init|update|check|source>")


if __name__ == "__main__":
    main(run)
