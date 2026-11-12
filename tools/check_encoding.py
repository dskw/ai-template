import re

from tools._lib import DOCS, ROOT, any_match, fail, main, read, read_table, tree_files

BOM = bytes([0xEF, 0xBB, 0xBF])
REPLACEMENT = chr(0xFFFD)
A_TILDE = chr(0xC3)
A_CIRCUMFLEX_EURO = chr(0xE2) + chr(0x20AC)
MOJIBAKE = re.compile(f"{REPLACEMENT}|{A_TILDE}[^\t -~]|{A_CIRCUMFLEX_EURO}")


def allowlist():
    path = DOCS / "CODE_CONVENTIONS.md"
    return [row["Path"] for row in read_table(read(path), "Non-ASCII allowlist", ["Path"], "docs/CODE_CONVENTIONS.md")]


def line_of(data, offset):
    return data[:offset].count(bytes([10])) + 1


def file_errors(name, allowed):
    data = (ROOT / name).read_bytes()
    if 0 in data[:8192]:
        return []
    errors = []
    if data.startswith(BOM):
        errors.append(f"{name}: byte order mark")
    if 13 in data:
        errors.append(f"{name}:{line_of(data, data.index(13))}: CR byte, the line ending must be LF")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        return errors + [f"{name}:{line_of(data, error.start)}: invalid UTF-8"]
    if any_match(name, allowed):
        return errors
    for number, line in enumerate(text.splitlines(), 1):
        if MOJIBAKE.search(line):
            errors.append(f"{name}:{number}: mojibake")
        elif not line.isascii():
            errors.append(f"{name}:{number}: non-ASCII character, the file is not on the allowlist")
    return errors


def errors(files=None):
    allowed = allowlist()
    found = []
    for name in files if files is not None else tree_files():
        if (ROOT / name).is_file():
            found += file_errors(name, allowed)
    return found


def run(args):
    found = errors(args or None)
    if found:
        fail("\n".join(found))
    print("encoding ok")


if __name__ == "__main__":
    main(run)
