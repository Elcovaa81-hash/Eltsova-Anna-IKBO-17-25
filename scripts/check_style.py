"""Simple style checker mirroring the course review rules."""

import ast
import pathlib
import sys

MAX_LINE = 80
MAX_FUNC_LINES = 40
MAX_ARGS = 7
MAX_FILE_LINES = 1000
ROOTS = ("src", "tests", "scripts")


def check_file(path):
    """Return a list of problems found in one Python file."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    problems = []
    if len(lines) > MAX_FILE_LINES:
        problems.append(f"{path}: file too large")
    for number, line in enumerate(lines, 1):
        if len(line) > MAX_LINE:
            problems.append(f"{path}:{number}: line too long")
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            problems.extend(check_function(path, node))
    return problems


def check_function(path, node):
    """Check length, arguments and docstring of one function."""
    problems = []
    length = node.end_lineno - node.lineno + 1
    if length > MAX_FUNC_LINES:
        problems.append(f"{path}:{node.lineno}: {node.name} too long")
    if len(node.args.args) > MAX_ARGS:
        problems.append(f"{path}:{node.lineno}: {node.name} too many args")
    exempt = node.name.startswith("test_")
    if not exempt and ast.get_docstring(node) is None:
        problems.append(f"{path}:{node.lineno}: {node.name} no docstring")
    return problems


def main():
    """Check all Python files, return non-zero when problems exist."""
    problems = []
    for root in ROOTS:
        for path in sorted(pathlib.Path(root).rglob("*.py")):
            problems.extend(check_file(path))
    print("\n".join(problems) or "style: OK")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
