import json

import yaml

from tools._lib import TOOL_COMMIT

MODELS = {"fast": "haiku", "balanced": "sonnet", "strong": "opus"}
TOOLS = {
    "read": ["Read"],
    "edit": ["Edit"],
    "write": ["Write"],
    "bash": ["Bash"],
    "grep": ["Grep"],
    "glob": ["Glob"],
    "web": ["WebFetch", "WebSearch"],
    "agent": ["Agent"],
}
# the harness asks the user before a command that passes an answer of the user, or that reaches a guarded write
# without one: through the variable of a tool commit, or through a module of the tools in a line of code
ASK_RULES = [
    "Bash(* --answer *)",
    f"Bash(*{TOOL_COMMIT}*)",
    "Bash(*import tools*)",
    "Bash(*from tools.*)",
    "Bash(*from tools import*)",
]
EVENTS = {"session_start": "SessionStart", "pre_tool_use": "PreToolUse", "post_tool_use": "PostToolUse"}


def command_hook(command, timeout=None):
    hook = {"type": "command", "command": command}
    if timeout:
        hook["timeout"] = timeout
    return hook


def agent_file(agent):
    meta = {
        "name": agent["name"],
        "description": agent["description"],
        "tools": ", ".join(name for tool in agent["tools"] for name in TOOLS[tool]),
        "model": MODELS[agent["model"]],
    }
    return "---\n" + yaml.safe_dump(meta, sort_keys=False, allow_unicode=True, width=1000) + "---\n\n" + agent["body"]


def server_entry(server):
    env = server.get("env", [])
    if "url" in server:
        entry = {"type": "http", "url": server["url"]}
        if env:
            entry["headers"] = {"Authorization": f"Bearer ${{{env[0]}}}"}
        return entry
    entry = {"command": server["command"], "args": server.get("args", [])}
    if env:
        entry["env"] = {name: f"${{{name}}}" for name in env}
    return entry


def generate(source, matcher):
    files = {"CLAUDE.md": "@AGENTS.md\n"}
    for skill in source["skills"]:
        for path in sorted(skill["dir"].rglob("*")):
            if path.is_file():
                files[f".claude/skills/{skill['name']}/{path.relative_to(skill['dir']).as_posix()}"] = path.read_bytes()
    for agent in source["agents"]:
        files[f".claude/agents/{agent['name']}.md"] = agent_file(agent)
    hooks = {}
    for hook in source["hooks"]:
        group = {"hooks": [command_hook(hook["command"], hook["timeout"])]}
        if hook["event"] != "session_start":
            group = {"matcher": matcher(hook, "claude"), **group}
        hooks.setdefault(EVENTS[hook["event"]], []).append(group)
    permissions = {"ask": ASK_RULES}
    settings = {"autoMemoryEnabled": False, "env": {"PYTHONUTF8": "1"}, "permissions": permissions, "hooks": hooks}
    files[".claude/settings.json"] = json.dumps(settings, indent=2) + "\n"
    servers = {server["name"]: server_entry(server) for server in source["mcp"]}
    files[".mcp.json"] = json.dumps({"mcpServers": servers}, indent=2) + "\n"
    return files
