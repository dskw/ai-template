import os
import sys
import time

from tools._lib import (
    DRAFT_ONLY,
    GENERATED,
    ROOT,
    SHARED,
    TOOL_OWNED,
    Fail,
    any_match,
    common_dir,
    hook_input,
    in_worktree,
    main,
    main_root,
    outside,
    read,
    read_meta,
    split_hook,
)

GENERATED_MESSAGE = "Generated file. Edit the source and run the generator."
OUTSIDE_MESSAGE = "Outside the repository. An agent writes only inside the repository, a temporary file into its tmp folders."
TOOL_MESSAGE = "Write protected. Every write to this file goes through a tool, see docs/DOCS_CONVENTIONS.md."
# the first write of an agent binds it to the root of that write; a binding older than this many seconds goes away
BINDING_AGE = 7 * 24 * 3600


def outside_allowed(name):
    roots = [os.path.join(os.path.expanduser("~"), ".claude")]
    path = os.path.normcase(os.path.abspath(name))
    return any(path.startswith(os.path.normcase(os.path.abspath(root)) + os.sep) for root in roots)


def block_reason(name, kind):
    if outside(name):
        return None if outside_allowed(name) else OUTSIDE_MESSAGE
    if any_match(name, GENERATED):
        return GENERATED_MESSAGE
    if any_match(name, SHARED) and in_worktree():
        return f"Shared file of the milestone. Write it in the main repository: {main_root()}"
    if any_match(name, TOOL_OWNED):
        return TOOL_MESSAGE
    if any_match(name, DRAFT_ONLY):
        if kind != "write":
            return "Write protected. A milestone file or a plan file is not deleted and not renamed."
        path = ROOT / name
        if path.exists():
            try:
                status = read_meta(read(path), name).get("status")
            except Fail:
                status = None
            if status != "draft":
                return TOOL_MESSAGE
    return None


def bound_root(agent):
    """The root that the agent writes in. The first write of the agent binds it to this root."""
    folder = common_dir() / "setup-agents"
    folder.mkdir(exist_ok=True)
    path = folder / "".join(char if char.isalnum() or char in "-_" else "_" for char in str(agent))
    try:
        with open(path, "x", encoding="utf-8") as handle:
            handle.write(str(ROOT.resolve()))
    except FileExistsError:
        return path.read_text(encoding="utf-8").strip()
    for old in folder.iterdir():
        if time.time() - old.stat().st_mtime > BINDING_AGE:
            old.unlink(missing_ok=True)
    return str(ROOT.resolve())


def agent_reason(data):
    agent = data.get("agent_id")
    if not agent:
        return None
    bound = bound_root(agent)
    if bound == str(ROOT.resolve()):
        return None
    return f"The agent writes in {bound}. One agent writes in one worktree: start a new agent for this worktree."


def run(args):
    data = {} if args else hook_input()
    code, paths = split_hook("pre_write", [], data, args)
    for name, kind in paths:
        reason = block_reason(name, kind) or (None if outside(name) else agent_reason(data))
        if reason:
            print(f"{name}: {reason}", file=sys.stderr)
            code = 2
    return code


if __name__ == "__main__":
    main(run)
