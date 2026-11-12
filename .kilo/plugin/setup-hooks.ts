import { spawnSync } from "node:child_process"

const hooks = [
  {
    "event": "tool.execute.before",
    "matcher": "edit|write|multiedit|apply_patch",
    "command": "python -m tools.pre_write",
    "timeout": 30
  },
  {
    "event": "tool.execute.after",
    "matcher": "edit|write|multiedit|apply_patch",
    "command": "python -m tools.post_write",
    "timeout": 300
  }
]

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
