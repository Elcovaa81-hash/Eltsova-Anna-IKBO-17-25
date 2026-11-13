"""Test repository: a plain text description of a dependency graph.

Format, one package per line (packages are upper-case Latin letters)::

    # comment
    A: B C
    B: C
    C:

A package that is only mentioned as a dependency is a leaf. Blank lines
and ``#`` comments are ignored.
"""

import re

from depviz.apk import RepoError

NAME_RE = re.compile(r"^[A-Z]+$")


def parse_line(line, number):
    """Parse ``NAME: DEP DEP`` into (name, [deps]) or None when empty."""
    text = line.split("#", 1)[0].strip()
    if not text:
        return None
    name, sep, rest = text.partition(":")
    name = name.strip()
    if not sep or not NAME_RE.match(name):
        raise RepoError(f"line {number}: expected 'NAME: DEPS', got {line!r}")
    deps = rest.split()
    for dep in deps:
        if not NAME_RE.match(dep):
            raise RepoError(f"line {number}: invalid package name {dep!r}")
    return name, deps


def parse_text(text):
    """Parse the test repository text into an adjacency dict."""
    graph = {}
    for number, line in enumerate(text.splitlines(), 1):
        parsed = parse_line(line, number)
        if parsed is None:
            continue
        name, deps = parsed
        if name in graph:
            raise RepoError(f"line {number}: duplicate package {name}")
        graph[name] = list(dict.fromkeys(deps))
    for deps in list(graph.values()):
        for dep in deps:
            graph.setdefault(dep, [])
    if not graph:
        raise RepoError("the test repository is empty")
    return graph


def load_graph(path):
    """Read a test repository file and return its adjacency dict."""
    try:
        with open(path, encoding="utf-8") as handle:
            return parse_text(handle.read())
    except (OSError, UnicodeDecodeError) as exc:
        raise RepoError(f"cannot read {path}: {exc}")
