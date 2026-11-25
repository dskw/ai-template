import json
import os
import re
import subprocess
import sys
import tomllib

from tools._lib import PROJECT_FILE, ROOT, any_match, fail, hook_input, main, main_root, read, read_meta, setup_root, split_hook

SHELL_OPERATORS = (";", "&", "|", "<", ">", "`", "$(", "\n")
# a share has a server name and a share name; an escaped line break of a text, for example \\n\\n, is no share
SHARE = r"\\\\[\w.-]+\\(?=[\w.$-])"
# an absolute path starts a token: a drive, a share, the home folder or a root folder
ABSOLUTE = re.compile(rf"""(?:^|(?<=[\s"'=(<>|;&,]))((?:[A-Za-z]:[\\/]|{SHARE}|//?|~(?=[\\/\s"']|$))[^\s"';&|<>()`]*)""")
# a root folder of a shell on Windows or on a Unix system; a different first part is no path, for example a pattern
# an absolute path in quotes is one token, also when it holds a space, for example "C:/Program Files/..."
QUOTED_ABSOLUTE = re.compile(rf"""(["'])((?:[A-Za-z]:[\\/]|{SHARE}|/|~/)[^"'\n]*)\1""")
ROOT_FOLDERS = {
    "tmp", "usr", "home", "etc", "var", "opt", "mnt", "dev", "proc", "root", "bin", "sbin", "srv", "run", "snap",
    "nix", "users", "windows", "private", "volumes", "library", "applications", "system",
}
ALLOWED_DEVICES = {"/dev/null", "/dev/stdout", "/dev/stderr"}
# a switch of a Windows command, for example /F, or its escaped form //c in a POSIX shell
SWITCH = re.compile(r"^//?[A-Za-z]{1,2}$")
# a shell loop: its word starts a command, and a do and a done follow
LOOP_START = r"(?:^|[;&|(\n]|\b(?:do|then|else)\s)\s*"
LOOP_BODY = r"(?=.*?[;\n]\s*do\s)(?=.*?\bdone\b)"
# a shell loop that waits: while or until around a sleep or a file test, or for around a sleep
# a loop of a script that waits: a while line or a for line with a colon before a call of sleep
# a loop word in a text is no loop
WAIT_LOOP = re.compile(
    rf"{LOOP_START}(?:while|until)\s{LOOP_BODY}(?=.*?(?:\bsleep\b|\[\[?\s|\btest\s))"
    rf"|{LOOP_START}for\b{LOOP_BODY}(?=.*?\bsleep\b)"
    r"|\b(?:while\b|for\s[^\n:]*\sin\s)[^\n]*:.*?\bsleep\s*\(",
    re.DOTALL,
)
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
    if SWITCH.match(token):
        return False
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
    quoted = [match for match in QUOTED_ABSOLUTE.finditer(command) if is_path(match.group(2)) and match.group(2) not in ALLOWED_DEVICES]
    for match in quoted:
        if not inside(native(match.group(2)), folders):
            found.append(match.group(2))
    for match in reversed(quoted):
        command = command[: match.start()] + " " * len(match.group(0)) + command[match.end() :]
    for match in ABSOLUTE.finditer(command):
        token = match.group(1).rstrip(".,:")
        if token in ALLOWED_DEVICES or not is_path(token):
            continue
        if not inside(native(token), folders):
            found.append(token)
    return found


# a command that starts with a change into a folder: the folder is the root of the work of the command
CHANGE_FOLDER = re.compile(r"""^cd\s+("[^"]+"|'[^']+'|[^\s;&|]+)\s*&&\s*""")
# a git command that names its folder: the folder is the root of the work of the command
GIT_FOLDER = re.compile(r"""^git\s+-C\s+("[^"]+"|'[^']+'|[^\s;&|]+)\s+""")


def work_root(command):
    """The root of the main repository or of a worktree that a command works in, and the command without the part
    that names that root. The root comes from a leading change of the folder or from the folder option of a git
    command, else from the first absolute path of the command that lies in a root. None when the command names no
    root."""
    for pattern, start in ((CHANGE_FOLDER, ""), (GIT_FOLDER, "git ")):
        match = pattern.match(command)
        if not match:
            continue
        folder = native(match.group(1).strip("\"'"))
        root = setup_root(os.path.join(ROOT, folder))
        if root is not None and os.path.normcase(os.path.abspath(os.path.join(ROOT, folder))) == os.path.normcase(str(root)):
            return root, start + command[match.end() :]
        break
    for match in ABSOLUTE.finditer(command):
        token = match.group(1).rstrip(".,:")
        if is_path(token) and token not in ALLOWED_DEVICES:
            root = setup_root(native(token))
            if root is not None:
                return root, command
    return None, command


def answer_chain(command):
    """Whether a command holds `--answer` and a second command. A leading change into a folder is no second command."""
    plain = re.sub(r""""(?:\\.|[^"\\])*"|'[^']*'""", '""', command.strip())
    if not re.search(r"(?:^|\s)--answer(?:\s|=|$)", plain):
        return False
    plain = re.sub(r"\d*>&\d+", " ", plain)
    if plain.startswith("(") and plain.endswith(")"):
        plain = plain[1:-1].strip()
    plain = re.sub(r"""^cd\s+[^\s;&|]+\s*&&\s*""", "", plain)
    return any(operator in plain for operator in (";", "&", "|", "\n", "`", "$("))


def delegate(root, args, data):
    """Runs the guard of another root with the same hook input and returns its exit code."""
    result = subprocess.run(
        [sys.executable, "-m", "tools.agent_guard", *args],
        cwd=root,
        input=json.dumps(data).encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    sys.stdout.write(result.stdout.decode("utf-8", errors="replace"))
    sys.stderr.write(result.stderr.decode("utf-8", errors="replace"))
    return result.returncode


def run(args):
    if len(args) not in (1, 2) or args[-1] not in ("bash", "edit"):
        fail("usage: python -m tools.agent_guard [<agent>] <bash|edit>")
    data = hook_input()
    tool_type = args[-1]
    agent = args[0] if len(args) == 2 else data.get("agent_type")
    command = str((data.get("tool_input") or data.get("args") or {}).get("command", "")).strip()
    if tool_type == "bash" and answer_chain(command):
        print(
            "A command with --answer runs alone, so the question of the user key stands alone in the prompt."
            " Run each other command in its own call",
            file=sys.stderr,
        )
        return 2
    if not agent:
        return 0
    paths = []
    if tool_type == "bash":
        root, command = work_root(command)
        if root is not None and root != ROOT.resolve() and data.get("agent_id"):
            return delegate(root, args, data)
        outside = outside_paths(command)
        if outside:
            print(f"The agent {agent} works only inside the repository: {', '.join(outside)}", file=sys.stderr)
            return 2
        if WAIT_LOOP.search(command):
            print(
                f"The agent {agent} never waits in a shell loop. Run the build or the test in the foreground with the"
                " longest timeout",
                file=sys.stderr,
            )
            return 2
    else:
        code, paths = split_hook("agent_guard", args, data)
        if code:
            return code
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
            for name, _ in paths:
                if not any_match(name, allowed):
                    print(f"The agent {agent} edits only files that match: {', '.join(allowed)}", file=sys.stderr)
                    return 2
    return 0


if __name__ == "__main__":
    main(run)
