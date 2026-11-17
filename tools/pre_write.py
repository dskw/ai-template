import os
import sys

from tools._lib import (
    DRAFT_ONLY,
    GENERATED,
    ROOT,
    SHARED,
    TOOL_OWNED,
    Fail,
    any_match,
    hook_paths,
    in_worktree,
    main,
    main_root,
    outside,
    read,
    read_meta,
)

GENERATED_MESSAGE = "Generated file. Edit the source and run the generator."
OUTSIDE_MESSAGE = "Outside the repository. An agent writes only inside the repository, a temporary file into its tmp folders."
TOOL_MESSAGE = "Write protected. Every write to this file goes through a tool, see docs/DOCS_CONVENTIONS.md."


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


def run(args):
    code = 0
    for name, kind in hook_paths(args):
        reason = block_reason(name, kind)
        if reason:
            print(f"{name}: {reason}", file=sys.stderr)
            code = 2
    return code


if __name__ == "__main__":
    main(run)
