"""Dependency graph traversal."""

from dataclasses import dataclass, field


@dataclass
class DepGraph:
    """Result of a traversal: reached nodes with depths and edges."""

    root: str
    depths: dict = field(default_factory=dict)
    edges: list = field(default_factory=list)


def allowed(name, name_filter):
    """Return True when a package is not excluded by the filter."""
    return not name_filter or name_filter not in name


def traverse(adjacency, root, max_depth, name_filter=""):
    """Build the dependency graph with an iterative (stack) DFS.

    Packages whose name contains ``name_filter`` are ignored. Nodes deeper
    than ``max_depth`` are not visited. A node is expanded again only when
    it is reached by a strictly shorter path, so cycles terminate and the
    depth limit is applied to the shortest distance from the root.
    """
    graph = DepGraph(root, {root: 0})
    seen_edges = set()
    stack = [root]
    while stack:
        node = stack.pop()
        depth = graph.depths[node]
        if depth >= max_depth:
            continue
        pending = []
        for dep in adjacency.get(node, []):
            if not allowed(dep, name_filter):
                continue
            if (node, dep) not in seen_edges:
                seen_edges.add((node, dep))
                graph.edges.append((node, dep))
            if dep not in graph.depths or depth + 1 < graph.depths[dep]:
                graph.depths[dep] = depth + 1
                pending.append(dep)
        stack.extend(reversed(pending))
    return graph


def reverse_adjacency(adjacency):
    """Return the graph with every edge reversed (dependents)."""
    reverse = {name: [] for name in adjacency}
    for name, deps in adjacency.items():
        for dep in deps:
            reverse.setdefault(dep, []).append(name)
    return reverse
