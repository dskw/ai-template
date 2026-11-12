import hashlib
import os
import stat
import subprocess
import sys

from tools._lib import ROOT, fail, git, git_dir, git_ok, main, run as shell, tool

HOOK = "#!/bin/sh\nexec python -m tools.check\n"


def step(text):
    print(f"setup: {text}")


def run(args):
    if args:
        fail("usage: python -m tools.setup")
    if not git_ok("rev-parse", "--is-inside-work-tree"):
        if not git_ok("init", "-b", "main"):
            git("init")
            git("symbolic-ref", "HEAD", "refs/heads/main")
        step("created the Git repository with the branch main")
    code, output = shell([sys.executable, "-m", "pip", "install", "--quiet", "-r", "tools/requirements.txt"])
    if code != 0:
        fail(f"pip install failed:\n{output}")
    code, output = shell("vale --version")
    if code != 0:
        fail(f"Vale does not run:\n{output}")
    step(f"Python dependencies and {output.strip().splitlines()[-1]} are installed")
    hook = git_dir() / "hooks" / "pre-commit"
    hook.parent.mkdir(parents=True, exist_ok=True)
    with open(hook, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(HOOK)
    hook.chmod(hook.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    step("installed the Git pre-commit hook")
    if os.name == "nt" and os.environ.get("PYTHONUTF8") != "1":
        subprocess.run(["setx", "PYTHONUTF8", "1"], capture_output=True, check=False)
        step("set PYTHONUTF8=1 for the user, open a new terminal to use it")
    marker = git_dir() / "setup-gitattributes"
    digest = hashlib.sha256((ROOT / ".gitattributes").read_bytes()).hexdigest()
    if not marker.exists() or marker.read_text(encoding="utf-8") != digest:
        git("add", "--renormalize", ".")
        marker.write_text(digest, encoding="utf-8")
        step("normalized the line endings of the tracked files")
    for name in ("build_wiki_bundle", "provider"):
        code, output = tool(name)
        if code != 0:
            fail(f"python -m tools.{name} failed:\n{output}")
        step(output.strip().splitlines()[-1])
    step("Codex: trust this project, then approve the hooks in /hooks")
    step("Kilo: keep the Claude Code compatibility off")
    step("done. Run the project-init skill when tools/project.toml does not exist")


if __name__ == "__main__":
    main(run)
