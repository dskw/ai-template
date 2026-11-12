import hashlib
import json
import re
import shutil
import urllib.request

from tools._lib import DOCS, ROOT, fail, main, read, run as shell, write

WIKI = DOCS / "wiki"
ASSETS = WIKI / "assets"
SUPPORT = ROOT / "tools" / "wiki"
CDN = "https://cdn.jsdelivr.net/npm/"
LIBRARIES = {
    "docsify.min.js": ("docsify@4.13.1/lib/docsify.min.js", "9123f808d3f6ad736b4a8f99944a611f87c5d4f9328030080a5c029ed5f450a5"),
    "vue.css": ("docsify@4.13.1/lib/themes/vue.css", "1f8ddcde10fe1d9f3ab60de8469ed26f9b09716fb882b225d666d4f62838de2e"),
    "mermaid.min.js": ("mermaid@11.4.1/dist/mermaid.min.js", "a43bc1afd446f9c4cc66ac5dd45d02e8d65e26fc5344ec0ef787f88d6ddb6f9e"),
    "docsify-mermaid.js": ("docsify-mermaid@2.0.1/dist/docsify-mermaid.js", "4850a5afd73684cd0b7d399f63aa71003cff754f0cdfc00de92427d5fe03b8c7"),
}
MERMAID = re.compile(r"^```mermaid\n(.*?)^```", re.M | re.S)


def pages():
    files = [path for path in sorted(WIKI.rglob("*.md")) if ASSETS not in path.parents]
    return {path.relative_to(WIKI).as_posix(): read(path) for path in files}


def pages_text():
    return "window.WIKI_PAGES = " + json.dumps(pages(), indent=0, sort_keys=True) + ";\n"


def download(name):
    source, digest = LIBRARIES[name]
    with urllib.request.urlopen(CDN + source, timeout=120) as response:
        data = response.read()
    if hashlib.sha256(data).hexdigest() != digest:
        fail(f"{CDN + source}: the download does not match the pinned hash")
    if name == "vue.css":
        data = re.sub(rb"@import url\([^)]*\);", b"", data)
    ASSETS.mkdir(parents=True, exist_ok=True)
    (ASSETS / name).write_bytes(data.replace(b"\r\n", b"\n"))


def build():
    for name in LIBRARIES:
        if not (ASSETS / name).is_file():
            download(name)
    for name, target in (("offline.js", ASSETS / "offline.js"), ("index.html", WIKI / "index.html")):
        if not target.exists() or read(target) != read(SUPPORT / name):
            write(target, read(SUPPORT / name))
    if not (ASSETS / "pages.js").exists() or read(ASSETS / "pages.js") != pages_text():
        write(ASSETS / "pages.js", pages_text())
    print("wiki bundle written")


def mermaid_errors(texts):
    blocks = [(name, block) for name, text in texts.items() for block in MERMAID.findall(text)]
    if not blocks:
        return []
    node = shutil.which("node")
    if not node:
        return ["Node.js is necessary to parse the Mermaid blocks"]
    command = [node, str(SUPPORT / "mermaid_parse.js"), str(ASSETS / "mermaid.min.js")]
    code, output = shell(command, json.dumps([block for _, block in blocks]).encode("utf-8"))
    try:
        results = json.loads(output.strip().split("\n")[-1])
    except ValueError:
        return [f"the Mermaid parser failed:\n{output}"]
    return [f"{name}: Mermaid block does not parse: {error}" for (name, _), error in zip(blocks, results) if error]


def check_errors():
    missing = [name for name in LIBRARIES if not (ASSETS / name).is_file()]
    if missing:
        return [f"docs/wiki/assets/{name} is missing, run python -m tools.build_wiki_bundle" for name in missing]
    errors = []
    stale = not (ASSETS / "pages.js").exists() or read(ASSETS / "pages.js") != pages_text()
    for name, target in (("offline.js", ASSETS / "offline.js"), ("index.html", WIKI / "index.html")):
        stale = stale or not target.exists() or read(target) != read(SUPPORT / name)
    if stale:
        errors.append("the wiki bundle is older than the wiki pages, run python -m tools.build_wiki_bundle")
    return errors + mermaid_errors({f"docs/wiki/{name}": text for name, text in pages().items()})


def run(args):
    if args == ["check"]:
        errors = check_errors()
        if errors:
            fail("\n".join(errors))
        print("wiki bundle ok")
    elif not args:
        build()
    else:
        fail("usage: python -m tools.build_wiki_bundle [check]")


if __name__ == "__main__":
    main(run)
