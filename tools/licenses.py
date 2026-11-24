"""Checks the license of each dependency of the manifests against the free list of the project bindings. Lists each
dependency with a license outside that list that has no row in the licenses file."""

import re

from tools._lib import DOCS, fail, load_project, main, read, read_table, run as shell

LICENSES = DOCS / "LICENSES.md"
LICENSES_NAME = "docs/LICENSES.md"
LICENSES_HEADER = ["Item", "Source", "License", "Author", "Attribution", "Condition"]
BINDING = "tools/project.toml: [licenses]"
TOKEN = re.compile(r"\(|\)|[^\s()]+")
OPERATORS = ("AND", "OR", "WITH")


def binding_errors(project):
    """The errors of the binding `[licenses]`: the answers of the user and the list of free licenses."""
    binding = project.get("licenses")
    if not isinstance(binding, dict):
        return [f"{BINDING} is missing"]
    found = [f"{BINDING}: {key} must be true or false" for key in ("commercial", "paid") if not isinstance(binding.get(key), bool)]
    for key in ("held", "free"):
        value = binding.get(key)
        if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
            found.append(f"{BINDING}: {key} must be a list of names")
    if "dependencies" in binding and not isinstance(binding["dependencies"], str):
        found.append(f"{BINDING}: dependencies must be one command line")
    return found


def allowed(expression, free):
    """Whether a license expression holds a choice whose licenses are all on the free list. `A OR B` is a choice,
    `A AND B` needs both, and `A WITH B` is one license with its own name. A slash is an old form of `OR`."""
    tokens = TOKEN.findall(expression.replace("/", " OR "))
    position = 0

    def word():
        return tokens[position].upper() if position < len(tokens) else ""

    def license_name():
        nonlocal position
        if position >= len(tokens) or tokens[position] == ")" or word() in OPERATORS:
            raise ValueError(expression)
        if tokens[position] == "(":
            position += 1
            result = choice()
            if position >= len(tokens) or tokens[position] != ")":
                raise ValueError(expression)
            position += 1
            return result
        name = tokens[position]
        position += 1
        if word() == "WITH" and position + 1 < len(tokens):
            name = f"{name} WITH {tokens[position + 1]}"
            position += 2
        return name in free

    def chain(part, operator, join):
        nonlocal position
        results = [part()]
        while word() == operator:
            position += 1
            results.append(part())
        return join(results)

    def choice():
        return chain(lambda: chain(license_name, "AND", all), "OR", any)

    try:
        result = choice()
    except ValueError:
        return False
    return result and position == len(tokens)


def dependencies(command):
    """The dependencies that the command of the binding prints: one line per dependency with its name, a tab and
    its license expression."""
    code, output = shell(command)
    if code != 0:
        fail(f"{BINDING}: the dependencies command failed:\n{output.strip()}")
    found = {}
    for line in output.splitlines():
        name, _, expression = line.partition("\t")
        if name.strip():
            found.setdefault(name.strip(), set()).add(expression.strip())
    return found


def rows():
    if not LICENSES.exists():
        fail(f"{LICENSES_NAME} is missing")
    return read_table(read(LICENSES), None, LICENSES_HEADER, LICENSES_NAME)


def errors():
    project = load_project()
    found = binding_errors(project)
    if found:
        return found
    binding = project["licenses"]
    free = set(binding["free"])
    table = rows()
    for row in table:
        label = f"{LICENSES_NAME}: the row {row['Item'] or '<empty>'}"
        found += [f"{label} needs a value in {key}" for key in ("Item", "Source", "License") if not row[key]]
        if row["License"] and allowed(row["License"], free) and not row["Condition"]:
            found.append(f"{label} has a license of the free list and no condition, so it needs no row")
    listed = {row["Item"] for row in table}
    if "dependencies" in binding:
        for name, expressions in sorted(dependencies(binding["dependencies"]).items()):
            for expression in sorted(expressions):
                if name not in listed and not allowed(expression, free):
                    shown = expression or "no license"
                    found.append(f"{name}: {shown} is outside the free list and {LICENSES_NAME} has no row for it")
    return found


def run(args):
    if args:
        fail("usage: python -m tools.licenses")
    found = errors()
    if found:
        fail("\n".join(found))
    print("licenses ok")


if __name__ == "__main__":
    main(run)
