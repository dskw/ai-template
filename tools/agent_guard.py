import sys

from tools._lib import ROOT, any_match, fail, hook_input, hook_paths, main, read, read_meta

SHELL_OPERATORS = (";", "&", "|", "<", ">", "`", "$(", "\n")


def run(args):
    if len(args) != 2 or args[1] not in ("bash", "edit"):
        fail("usage: python -m tools.agent_guard <agent> <bash|edit>")
    agent, kind = args
    path = ROOT / ".agents" / "agents" / f"{agent}.md"
    if not path.exists():
        return 0
    meta = read_meta(read(path), f".agents/agents/{agent}.md")
    data = hook_input()
    if kind == "bash":
        allowed = meta.get("bash_allow")
        command = str((data.get("tool_input") or data.get("args") or {}).get("command", "")).strip()
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
