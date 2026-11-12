import json

EFFORT = {"fast": "low", "balanced": "medium", "strong": "high"}
EVENTS = {"session_start": "SessionStart", "pre_tool_use": "PreToolUse", "post_tool_use": "PostToolUse"}


def text(value):
    return json.dumps(value)


def block(value):
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"""\n{escaped.rstrip()}\n"""'


def restrictions(agent):
    lines = ["", "Restrictions:", f"- Use only these tools: {', '.join(agent['tools'])}."]
    if not {"edit", "write"} & set(agent["tools"]):
        lines.append("- Do not edit a file and do not write a file.")
    if "bash_allow" in agent:
        lines.append(f"- Run only one command per call that starts with: {'; '.join(agent['bash_allow'])}.")
    if "edit_allow" in agent:
        lines.append(f"- Edit only files that match: {'; '.join(agent['edit_allow'])}.")
    return "\n".join(lines)


def agent_file(agent):
    return (
        f"name = {text(agent['name'])}\n"
        f"description = {text(agent['description'])}\n"
        f"model_reasoning_effort = {text(EFFORT[agent['model']])}\n"
        f"developer_instructions = {block(agent['body'].rstrip() + chr(10) + restrictions(agent))}\n"
    )


def config(source):
    lines = ["[features]", "hooks = true", "memories = false"]
    for server in source["mcp"]:
        env = server.get("env", [])
        lines += ["", f"[mcp_servers.{server['name']}]"]
        if "url" in server:
            lines.append(f"url = {text(server['url'])}")
            if env:
                lines.append(f"bearer_token_env_var = {text(env[0])}")
        else:
            lines.append(f"command = {text(server['command'])}")
            lines.append(f"args = {text(server.get('args', []))}")
            if env:
                lines.append(f"env_vars = {text(env)}")
    return "\n".join(lines) + "\n"


def generate(source, matcher):
    files = {f".codex/agents/{agent['name']}.toml": agent_file(agent) for agent in source["agents"]}
    files[".codex/config.toml"] = config(source)
    hooks = {}
    for hook in source["hooks"]:
        group = {"hooks": [{"type": "command", "command": hook["command"], "timeout": hook["timeout"]}]}
        if hook["event"] != "session_start":
            group = {"matcher": matcher(hook, "codex"), **group}
        hooks.setdefault(EVENTS[hook["event"]], []).append(group)
    files[".codex/hooks.json"] = json.dumps({"hooks": hooks}, indent=2) + "\n"
    return files
