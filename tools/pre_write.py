import os
import sys
import tempfile

from tools._lib import ROOT, Fail, any_match, hook_paths, main, outside, read, read_meta

GENERATED = [
    ".claude/**",
    ".codex/**",
    ".kilo/**",
    ".agents/.generated/**",
    "CLAUDE.md",
    ".mcp.json",
    "kilo.jsonc",
    "docs/MEMORY.md",
    "docs/wiki/assets/pages.js",
    "docs/wiki/index.html",
]
TOOL_OWNED = [
    "docs/milestones/PROGRESS.md",
    "docs/milestones/archive/**",
    "docs/plans/archive/**",
    "docs/plans/*/progress.md",
    "docs/plans/*/evidence/**",
]
DRAFT_ONLY = ["docs/milestones/M*.md", "docs/plans/*/plan.md"]
GENERATED_MESSAGE = "Generated file. Edit the source and run the generator."
OUTSIDE_MESSAGE = "Outside the repository. An agent writes only inside the repository and the temporary folder."
TOOL_MESSAGE = "Write protected. Every write to this file goes through a tool, see docs/DOCS_CONVENTIONS.md."


def outside_allowed(name):
    roots = [tempfile.gettempdir(), os.path.join(os.path.expanduser("~"), ".claude")]
    path = os.path.normcase(os.path.abspath(name))
    return any(path.startswith(os.path.normcase(os.path.abspath(root)) + os.sep) for root in roots)


def block_reason(name, kind):
    if outside(name):
        return None if outside_allowed(name) else OUTSIDE_MESSAGE
    if any_match(name, GENERATED):
        return GENERATED_MESSAGE
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
