import hashlib
import json
import re

import yaml

from tools._lib import ROOT, fail, main, read, words, write
from tools.providers import claude, codex, kilo

SOURCE = ROOT / ".agents"
MANIFEST = SOURCE / ".generated" / "manifest.json"
MODELS = ("fast", "balanced", "strong")
TOOLS = ("read", "edit", "write", "bash", "grep", "glob", "web")
EVENTS = ("session_start", "pre_tool_use", "post_tool_use")
PROVIDERS = ("claude", "codex", "kilo")
OUTPUT_ROOTS = (".claude/", ".codex/", ".kilo/", "CLAUDE.md", ".mcp.json", "kilo.jsonc")


def split(path):
    name = path.relative_to(ROOT).as_posix()
    text = read(path)
    end = text.find("\n---\n", 3)
    if not text.startswith("---\n") or end < 0:
        fail(f"{name}:1: the frontmatter is missing")
    try:
        meta = yaml.safe_load(text[4 : end + 1])
    except yaml.YAMLError as error:
        fail(f"{name}: the frontmatter is not valid YAML: {error}")
    if not isinstance(meta, dict):
        fail(f"{name}:1: the frontmatter must hold fields")
    return name, meta, text[end + 5 :].lstrip("\n")


def load_list(path):
    data = yaml.safe_load(read(path)) if path.exists() else None
    if data is not None and not (isinstance(data, list) and all(isinstance(item, dict) for item in data)):
        fail(f"{path.relative_to(ROOT).as_posix()}: the file must hold a list of entries")
    return data or []


def load_source():
    skills, agents = [], []
    for folder in sorted(path for path in (SOURCE / "skills").iterdir() if path.is_dir()):
        name, meta, _ = split(folder / "SKILL.md") if (folder / "SKILL.md").exists() else fail(f"{folder.name}: SKILL.md is missing")
        if meta.get("name") != folder.name or not meta.get("description"):
            fail(f"{name}: name must equal the folder name and description is necessary")
        skills.append({"name": folder.name, "dir": folder})
    for path in sorted((SOURCE / "agents").glob("*.md")):
        name, meta, body = split(path)
        if meta.get("name") != path.stem or not meta.get("description"):
            fail(f"{name}: name must equal the file name and description is necessary")
        if meta.get("model") not in MODELS:
            fail(f"{name}: model must be one of {', '.join(MODELS)}")
        tools = meta.get("tools")
        if not isinstance(tools, list) or not tools or any(tool not in TOOLS for tool in tools):
            fail(f"{name}: tools must be a list with a subset of {' '.join(TOOLS)}")
        for key in ("bash_allow", "edit_allow"):
            if key in meta and not (isinstance(meta[key], list) and all(isinstance(item, str) for item in meta[key])):
                fail(f"{name}: {key} must be a list of strings")
        agents.append({**meta, "body": body})
    hooks = load_list(SOURCE / "hooks.yaml")
    for number, hook in enumerate(hooks, 1):
        name = f".agents/hooks.yaml: entry {number}"
        if hook.get("event") not in EVENTS:
            fail(f"{name}: event must be one of {', '.join(EVENTS)}")
        if not re.fullmatch(r"python -m tools\.\w+( [\w-]+)*", str(hook.get("command"))):
            fail(f"{name}: command must have the form python -m tools.<name>")
        if not isinstance(hook.get("timeout"), int):
            fail(f"{name}: timeout must be a number of seconds")
        matcher = hook.get("matcher")
        if isinstance(matcher, dict) and set(matcher) != set(PROVIDERS):
            fail(f"{name}: a matcher per provider needs the keys {', '.join(PROVIDERS)}")
        if hook["event"] != "session_start" and not isinstance(matcher, (str, dict)):
            fail(f"{name}: matcher is necessary")
    servers = load_list(SOURCE / "mcp.yaml")
    for number, server in enumerate(servers, 1):
        name = f".agents/mcp.yaml: entry {number}"
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", str(server.get("name"))):
            fail(f"{name}: name must have lower case letters, digits, '-' or '_'")
        if ("command" in server) == ("url" in server):
            fail(f"{name}: one of command or url is necessary")
        if not isinstance(server.get("args", []), list):
            fail(f"{name}: args must be a list")
        env = server.get("env", [])
        if not isinstance(env, list) or not all(re.fullmatch(r"[A-Z_][A-Z0-9_]*", str(item)) for item in env):
            fail(f"{name}: env must be a list of environment variable names, never a value")
        if "url" in server and len(env) > 1:
            fail(f"{name}: a url entry has max one env name, the bearer token")
        if not 1 <= words(str(server.get("used_for", ""))) <= 12:
            fail(f"{name}: used_for must have 1 to 12 words")
        unknown = set(server) - {"name", "command", "url", "args", "env", "used_for"}
        if unknown:
            fail(f"{name}: unknown field {' '.join(sorted(unknown))}")
    return {"skills": skills, "agents": agents, "hooks": hooks, "mcp": servers}


def matcher(hook, provider):
    value = hook.get("matcher")
    return value[provider] if isinstance(value, dict) else value


def source_hash():
    digest = hashlib.sha256()
    files = [path for path in SOURCE.rglob("*") if path.is_file() and ".generated" not in path.parts]
    for path in sorted(files + [ROOT / "AGENTS.md"], key=lambda item: item.relative_to(ROOT).as_posix()):
        digest.update(path.relative_to(ROOT).as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def manifest():
    return json.loads(read(MANIFEST)) if MANIFEST.exists() else {"source_hash": "", "files": []}


def generate():
    source = load_source()
    if (ROOT / ".kilo" / "kilo.jsonc").exists():
        fail(".kilo/kilo.jsonc exists and wins over the generated kilo.jsonc, remove it")
    files = {}
    for module in (claude, codex, kilo):
        files.update(module.generate(source, matcher))
    hooks_file = ROOT / ".codex" / "hooks.json"
    hooks_before = hooks_file.read_bytes() if hooks_file.exists() else None
    for name in manifest()["files"]:
        if name.startswith(OUTPUT_ROOTS) and name not in files and (ROOT / name).is_file():
            (ROOT / name).unlink()
    for name, content in files.items():
        path = ROOT / name
        if isinstance(content, bytes):
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists() or path.read_bytes() != content:
                path.write_bytes(content)
        elif not path.exists() or read(path) != content:
            write(path, content)
    for root in (".claude", ".codex", ".kilo"):
        folders = sorted((path for path in (ROOT / root).rglob("*") if path.is_dir()), reverse=True)
        for folder in folders:
            if not any(folder.iterdir()):
                folder.rmdir()
    write(MANIFEST, json.dumps({"source_hash": source_hash(), "files": sorted(files)}, indent=2) + "\n")
    print(f"generated {len(files)} provider files")
    if hooks_before is not None and hooks_before != hooks_file.read_bytes():
        print("Codex: the hooks changed, approve them again in /hooks")


def check_errors():
    data = manifest()
    if data["source_hash"] != source_hash():
        return ["the provider files are stale, run python -m tools.provider"]
    return [f"{name}: the generated file is missing, run python -m tools.provider" for name in data["files"] if not (ROOT / name).is_file()]


def run(args):
    if args == ["check"]:
        errors = check_errors()
        if errors:
            fail("\n".join(errors))
        print("provider ok")
    elif not args:
        generate()
    else:
        fail("usage: python -m tools.provider [check]")


if __name__ == "__main__":
    main(run)
