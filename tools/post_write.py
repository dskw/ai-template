import sys

from tools._lib import ROOT, any_match, hook_input, main, outside, split_hook, tool

GENERATORS = [
    ("provider", [".agents/**", "AGENTS.md"], [".agents/.generated/**"]),
    ("build_wiki_bundle", ["docs/wiki/**"], ["docs/wiki/assets/**", "docs/wiki/index.html"]),
    ("memory_index", ["docs/memories/**"], []),
]


def run(args):
    data = {} if args else hook_input()
    delegated, paths = split_hook("post_write", [], data, args)
    names = [name for name, _ in paths if not outside(name)]
    if not names:
        return delegated
    failed = []
    for generator, sources, outputs in GENERATORS:
        if any(any_match(name, sources) and not any_match(name, outputs) for name in names):
            code, output = tool(generator)
            if code != 0:
                failed.append(f"python -m tools.{generator} failed:\n{output.rstrip()}")
    code, output = tool("check", "--format-only", *[name for name in names if (ROOT / name).is_file()])
    if code != 0:
        failed.append(output.rstrip())
    if failed:
        print("\n".join(failed), file=sys.stderr)
        return 2
    print(output, end="")
    return delegated


if __name__ == "__main__":
    main(run)
