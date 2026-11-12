from tools._lib import ROOT, main, tree_files
from tools.check_encoding import BOM


def fix(name):
    path = ROOT / name
    data = path.read_bytes()
    if b"\0" in data[:8192]:
        return False
    fixed = data[len(BOM) :] if data.startswith(BOM) else data
    try:
        fixed.decode("utf-8")
    except UnicodeDecodeError:
        fixed = fixed.decode("cp1252", errors="replace").encode("utf-8")
    fixed = fixed.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    if fixed == data:
        return False
    path.write_bytes(fixed)
    return True


def run(args):
    for name in args or tree_files():
        if (ROOT / name).is_file() and fix(name):
            print(f"fixed {name}")


if __name__ == "__main__":
    main(run)
