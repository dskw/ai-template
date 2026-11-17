"""Logs the duration of each tool call of an agent session and reports the slowest calls and the time per tool.

Hook entries: `start` runs before a tool call, `end` after it. The log of a session lies in the log folder of the main
repository, one line per call. `report [<log>]` prints the slowest calls and the time per tool of the newest log."""

import json
import time
from collections import Counter
from pathlib import Path

from tools._lib import LOG_FOLDER, fail, hook_input, main, main_root

LOG_DIR = main_root() / LOG_FOLDER / "timing"
SLOWEST = 15


def session_of(data):
    return str(data.get("session_id") or "session").replace("/", "_")


def call_id(data):
    return str(data.get("tool_use_id") or data.get("call_id") or data.get("tool_name") or "call")


def detail(data):
    values = data.get("tool_input") or data.get("args") or {}
    for key in ("command", "file_path", "filePath", "path", "description", "pattern"):
        if isinstance(values.get(key), str):
            return values[key][:120].replace("\n", " ")
    return ""


def pending_path(session):
    return LOG_DIR / f"{session}.pending.json"


def log_path(session):
    return LOG_DIR / f"{session}.jsonl"


def start():
    data = hook_input()
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    path = pending_path(session_of(data))
    pending = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    pending[call_id(data)] = time.time()
    path.write_text(json.dumps(pending), encoding="utf-8")


def end():
    data = hook_input()
    session = session_of(data)
    path = pending_path(session)
    pending = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    started = pending.pop(call_id(data), None)
    if path.exists():
        path.write_text(json.dumps(pending), encoding="utf-8")
    if started is None:
        return
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(started)),
        "tool": str(data.get("tool_name") or data.get("tool") or "tool"),
        "seconds": round(time.time() - started, 2),
        "detail": detail(data),
    }
    with open(log_path(session), "a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry) + "\n")


def report(path=None):
    if path is None:
        logs = sorted(LOG_DIR.glob("*.jsonl"), key=lambda item: item.stat().st_mtime) if LOG_DIR.exists() else []
        if not logs:
            fail(f"no timing log in {LOG_DIR}")
        path = logs[-1]
    entries = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    print(f"{path}: {len(entries)} calls")
    totals, counts, longest = Counter(), Counter(), Counter()
    for entry in entries:
        totals[entry["tool"]] += entry["seconds"]
        counts[entry["tool"]] += 1
        longest[entry["tool"]] = max(longest[entry["tool"]], entry["seconds"])
    print("\n| Tool | Calls | Seconds | Longest |\n|---|---|---|---|")
    for tool_name, seconds in totals.most_common():
        print(f"| {tool_name} | {counts[tool_name]} | {seconds:.0f} | {longest[tool_name]:.0f} |")
    print(f"\n| Slowest {SLOWEST} | Seconds | Call |\n|---|---|---|")
    for entry in sorted(entries, key=lambda item: -item["seconds"])[:SLOWEST]:
        print(f"| {entry['at']} | {entry['seconds']:.0f} | {entry['tool']}: {entry['detail']} |")


def run(args):
    if args == ["start"]:
        start()
    elif args == ["end"]:
        end()
    elif args[:1] == ["report"] and len(args) <= 2:
        report(*args[1:])
    else:
        fail("usage: python -m tools.timing start | end | report [<log>]")


if __name__ == "__main__":
    main(run)
