"""Text representation of a dependency graph in the Graphviz DOT language."""

ROOT_STYLE = 'style=filled, fillcolor="#ffe08a"'


def quote(name):
    """Quote an identifier for DOT."""
    return '"' + name.replace("\\", "\\\\").replace('"', '\\"') + '"'


def to_dot(graph, edges, title):
    """Return DOT text for the nodes of ``graph`` and the given edges.

    ``edges`` are "dependent -> dependency" pairs; the root package is
    highlighted so isolated roots are still drawn.
    """
    lines = [f"digraph {quote(title)} {{",
             "  rankdir=LR;",
             "  node [shape=box, fontname=\"Helvetica\"];"]
    for name in graph.depths:
        style = f" [{ROOT_STYLE}]" if name == graph.root else ""
        lines.append(f"  {quote(name)}{style};")
    for source, target in edges:
        lines.append(f"  {quote(source)} -> {quote(target)};")
    lines.append("}")
    return "\n".join(lines) + "\n"
