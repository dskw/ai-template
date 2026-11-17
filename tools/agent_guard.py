import os
import re
import sys
import tomllib
from pathlib import Path

from tools._lib import PROJECT_FILE, ROOT, any_match, fail, hook_input, hook_paths, main, main_root, read, read_meta

SHELL_OPERATORS = (";", "&", "|", "<", ">", "`", "$(", "\n")
# an absolute path starts a token: a drive, a share, the home folder or a root folder
ABSOLUTE = re.compile(r"""(?:^|(?<=[\s"'=(<>|;&,]))((?:[A-Za-z]:[\\/]|\\\\[\w.-]+\\|//?|~(?=[\\/\s"']|$))[^\s"';&|<>()`]*)""")
# a root folder of a shell on Windows or on a Unix system; a different first part is no path, for example a pattern
ROOT_FOLDERS = {
    "tmp", "usr", "home", "etc", "var", "opt", "mnt", "dev", "proc", "root", "bin", "sbin", "srv", "run", "snap",
    "nix", "users", "windows", "private", "volumes", "library", "applications", "system",
}
ALLOWED_DEVICES = {"/dev/null", "/dev/stdout", "/dev/stderr"}
# a variable that names a folder outside the repository
OUTSIDE_VARIABLES = re.compile(
    r"\$\{?(?:HOME|TEMP|TMP|TMPDIR|USERPROFILE|APPDATA|LOCALAPPDATA)\b|%(?:TEMP|TMP|USERPROFILE|APPDATA|LOCALAPPDATA|HOMEPATH)%"
    r"|\$env:(?:TEMP|TMP|USERPROFILE|APPDATA|LOCALAPPDATA|HOME)\b",
    re.IGNORECASE,
)


def toolchain_folders():
    """The folders of the tool chain that the project binding names: `toolchain_folders` and `dependency_source`."""
    if not PROJECT_FILE.exists():
        return []
    try:
        project = tomllib.loads(read(PROJECT_FILE))
    except tomllib.TOMLDecodeError:
        return []
    folders = list(project.get("toolchain_folders", []))
    if isinstance(project.get("dependency_source"), str):
        folders.append(project["dependency_source"])
    return [os.path.join(main_root(), os.path.expanduser(folder)) for folder in folders if isinstance(folder, str)]


def native(token):
    """The path of a token for this machine. A shell on Windows writes the drive C as /c/."""
    match = re.match(r"^/([A-Za-z])(/.*)?$", token)
    if os.name == "nt" and match:
        return f"{match.group(1)}:{match.group(2) or '/'}"
    if token.startswith("~"):
        return os.path.expanduser(token)
    return token


def is_path(token):
    if re.match(r"^[A-Za-z]:|^\\\\|^~", token):
        return True
    parts = [part for part in token.split("/") if part]
    if not parts:
        return False
    first = parts[0].lower()
    return (os.name == "nt" and len(first) == 1 and first.isalpha()) or first in ROOT_FOLDERS


def inside(path, folders):
    path = os.path.normcase(os.path.abspath(path))
    for folder in folders:
        folder = os.path.normcase(os.path.abspath(folder))
        if path == folder or path.startswith(folder.rstrip(os.sep) + os.sep):
            return True
    return False


def outside_paths(command):
    """The absolute paths of a command outside the repository and the tool chain folders of the binding."""
    found = [match.group(0) for match in OUTSIDE_VARIABLES.finditer(command)]
    folders = [str(main_root())] + toolchain_folders()
    for match in ABSOLUTE.finditer(command):
        token = match.group(1).rstrip(".,:")
        if token in ALLOWED_DEVICES or not is_path(token):
            continue
        if not inside(native(token), folders):
            found.append(token)
    return found


def run(args):
    if len(args) not in (1, 2) or args[-1] not in ("bash", "edit"):
        fail("usage: python -m tools.agent_guard [<agent>] <bash|edit>")
    data = hook_input()
    tool_type = args[-1]
    agent = args[0] if len(args) == 2 else data.get("agent_type")
    if not agent:
        return 0
    command = str((data.get("tool_input") or data.get("args") or {}).get("command", "")).strip()
    if tool_type == "bash":
        outside = outside_paths(command)
        if outside:
            print(f"The agent {agent} works only inside the repository: {', '.join(outside)}", file=sys.stderr)
            return 2
    path = ROOT / ".agents" / "agents" / f"{agent}.md"
    if not path.exists():
        return 0
    meta = read_meta(read(path), f".agents/agents/{agent}.md")
    if tool_type == "bash":
        allowed = meta.get("bash_allow")
        if isinstance(allowed, list):
            prefix = any(command == item or command.startswith(item + " ") for item in allowed)
            if not prefix or any(operator in command for operator in SHELL_OPERATORS):
                print(f"The agent {agent} runs only one command that starts with: {', '.join(allowed)}", file=sys.stderr)
                return 2
    else:
        allowed = meta.get("edit_allow")
        if isinstance(allowed, list):
            for name, _ in hook_paths([], data):
                if not any_match(name, allowed):
                    print(f"The agent {agent} edits only files that match: {', '.join(allowed)}", file=sys.stderr)
                    return 2
    return 0


if __name__ == "__main__":
    main(run)
