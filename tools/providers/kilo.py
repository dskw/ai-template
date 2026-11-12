import json

import yaml

PERMISSIONS = {
    "read": ["read", "list"],
    "edit": ["edit"],
    "write": ["edit"],
    "bash": ["bash"],
    "grep": ["grep"],
    "glob": ["glob"],
    "web": ["webfetch", "websearch"],
}
EVENTS = {"pre_tool_use": "tool.execute.before", "post_tool_use": "tool.execute.after"}

PLUGIN = """import { spawnSync } from "node:child_process"

const hooks = HOOKS

function run(event: string, tool: string, args: unknown, cwd: string) {
  for (const hook of hooks) {
    if (hook.event !== event || !new RegExp(`^(?:${hook.matcher})$`).test(tool)) continue
    const result = spawnSync(hook.command, {
      cwd,
      shell: true,
      input: JSON.stringify({ tool_name: tool, tool_input: args }),
      encoding: "utf8",
      timeout: hook.timeout * 1000,
    })
    if (result.status !== 0) {
      throw new Error(`${result.stderr ?? ""}${result.stdout ?? ""}`.trim() || `${hook.command} failed`)
    }
  }
}

const server = async ({ directory, worktree }: any) => ({
  "tool.execute.before": async (input: any, output: any) =>
    run("tool.execute.before", input.tool, output?.args ?? input?.args ?? {}, worktree || directory),
  "tool.execute.after": async (input: any, output: any) =>
    run("tool.execute.after", input.tool, input?.args ?? output?.args ?? {}, worktree || directory),
})

export default { id: "setup-hooks", server }
"""


def agent_file(agent):
    granted = {key for tool in agent["tools"] for key in PERMISSIONS[tool]}
    permission = {}
    for key in sorted({key for keys in PERMISSIONS.values() for key in keys}):
        permission[key] = "allow" if key in granted else "deny"
    if "bash_allow" in agent and "bash" in granted:
        rules = {"*": "deny"}
        for prefix in agent["bash_allow"]:
            rules[prefix] = "allow"
            rules[f"{prefix} *"] = "allow"
        permission["bash"] = rules
    if "edit_allow" in agent and "edit" in granted:
        permission["edit"] = {"*": "deny", **{glob: "allow" for glob in agent["edit_allow"]}}
    meta = {"description": agent["description"], "mode": "subagent", "permission": permission}
    return "---\n" + yaml.safe_dump(meta, sort_keys=False, allow_unicode=True, width=1000) + "---\n\n" + agent["body"]


def server_entry(server):
    env = server.get("env", [])
    if "url" in server:
        entry = {"type": "remote", "url": server["url"], "enabled": True}
        if env:
            entry["headers"] = {"Authorization": f"Bearer {{env:{env[0]}}}"}
        return entry
    entry = {"type": "local", "command": [server["command"], *server.get("args", [])], "enabled": True}
    if env:
        entry["environment"] = {name: f"{{env:{name}}}" for name in env}
    return entry


def generate(source, matcher):
    files = {f".kilo/agents/{agent['name']}.md": agent_file(agent) for agent in source["agents"]}
    hooks = [
        {"event": EVENTS[hook["event"]], "matcher": matcher(hook, "kilo"), "command": hook["command"], "timeout": hook["timeout"]}
        for hook in source["hooks"]
        if hook["event"] in EVENTS
    ]
    files[".kilo/plugin/setup-hooks.ts"] = PLUGIN.replace("HOOKS", json.dumps(hooks, indent=2))
    config = {"$schema": "https://app.kilo.ai/config.json", "permission": {"external_directory": "deny"}, "mcp": {server["name"]: server_entry(server) for server in source["mcp"]}}
    files["kilo.jsonc"] = json.dumps(config, indent=2) + "\n"
    return files
