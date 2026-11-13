"""Tests for the test repository parser and the DFS traversal."""

import contextlib
import io
import os
import unittest

from depviz import apk, cli, testrepo
from depviz.graph import reverse_adjacency, traverse

EXAMPLES = os.path.join(os.path.dirname(__file__), "..", "examples")


def example(name):
    """Return the adjacency dict of an example repository."""
    return testrepo.load_graph(os.path.join(EXAMPLES, name))


class TestRepoTest(unittest.TestCase):
    """Parsing of the test repository format."""

    def test_parse(self):
        graph = testrepo.parse_text("# c\nA: B C # x\n\nB:\n")
        self.assertEqual(graph, {"A": ["B", "C"], "B": [], "C": []})

    def test_bad_line(self):
        with self.assertRaises(apk.RepoError):
            testrepo.parse_text("A B C\n")

    def test_lowercase_name(self):
        with self.assertRaises(apk.RepoError):
            testrepo.parse_text("a: B\n")

    def test_bad_dependency_name(self):
        with self.assertRaises(apk.RepoError):
            testrepo.parse_text("A: b1\n")

    def test_duplicate(self):
        with self.assertRaises(apk.RepoError):
            testrepo.parse_text("A:\nA:\n")

    def test_empty(self):
        with self.assertRaises(apk.RepoError):
            testrepo.parse_text("# nothing\n")

    def test_missing_file(self):
        with self.assertRaises(apk.RepoError):
            testrepo.load_graph("/no/such/file")


class TraverseTest(unittest.TestCase):
    """DFS behaviour."""

    def test_chain_full(self):
        graph = traverse(example("chain.txt"), "A", 10)
        self.assertEqual(graph.depths, {"A": 0, "B": 1, "C": 2, "D": 3})
        self.assertEqual(graph.edges, [("A", "B"), ("B", "C"), ("C", "D")])

    def test_depth_limit(self):
        graph = traverse(example("chain.txt"), "A", 2)
        self.assertEqual(set(graph.depths), {"A", "B", "C"})

    def test_depth_zero(self):
        graph = traverse(example("chain.txt"), "A", 0)
        self.assertEqual(graph.depths, {"A": 0})
        self.assertEqual(graph.edges, [])

    def test_diamond_has_unique_edges(self):
        graph = traverse(example("diamond.txt"), "A", 10)
        self.assertEqual(len(graph.edges), 5)
        self.assertEqual(graph.depths["D"], 2)

    def test_cycle_terminates(self):
        graph = traverse(example("cycle.txt"), "A", 100)
        self.assertEqual(set(graph.depths), {"A", "B", "C", "D", "E"})
        self.assertIn(("D", "B"), graph.edges)
        self.assertIn(("E", "E"), graph.edges)

    def test_shortest_depth_wins(self):
        graph = traverse(example("shortcut.txt"), "A", 3)
        self.assertEqual(graph.depths["D"], 1)
        self.assertEqual(graph.depths["F"], 3)

    def test_filter(self):
        graph = traverse(example("prefixed.txt"), "APP", 10, "AB")
        self.assertEqual(set(graph.depths), {"APP", "CORE", "BASE"})
        self.assertNotIn(("APP", "ABLIB"), graph.edges)

    def test_deep_graph_without_recursion_error(self):
        size = 5000
        adjacency = {str(i): [str(i + 1)] for i in range(size)}
        adjacency[str(size)] = []
        graph = traverse(adjacency, "0", size)
        self.assertEqual(len(graph.depths), size + 1)

    def test_reverse_adjacency(self):
        reverse = reverse_adjacency(example("diamond.txt"))
        self.assertEqual(sorted(reverse["D"]), ["B", "C"])
        self.assertEqual(reverse["A"], [])


class CliTest(unittest.TestCase):
    """End-to-end runs in test repository mode."""

    def run_cli(self, name, *extra):
        """Run the CLI on an example file, return (code, stdout)."""
        path = os.path.join(EXAMPLES, name)
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(
                io.StringIO()):
            code = cli.main(["-m", "test", "-r", path, *extra])
        return code, out.getvalue()

    def test_cycle_output(self):
        code, out = self.run_cli("cycle.txt", "-p", "A", "-d", "9")
        self.assertEqual(code, cli.EXIT_OK)
        self.assertIn("  D -> B", out)
        self.assertIn("Packages (5):", out)

    def test_unknown_package(self):
        code, _ = self.run_cli("chain.txt", "-p", "Z")
        self.assertEqual(code, cli.EXIT_ERROR)

    def test_reverse_chain(self):
        code, out = self.run_cli("chain.txt", "-p", "D", "--reverse")
        self.assertEqual(code, cli.EXIT_OK)
        self.assertIn("Reverse dependency graph of D", out)
        self.assertIn("  C -> D", out)
        self.assertIn("  A -> B", out)
        self.assertIn("Packages (4):", out)

    def test_reverse_depth_limit(self):
        _, out = self.run_cli("chain.txt", "-p", "D", "--reverse", "-d", "1")
        self.assertIn("Packages (2):", out)
        self.assertNotIn("B -> C", out)

    def test_reverse_cycle(self):
        code, out = self.run_cli("cycle.txt", "-p", "B", "--reverse",
                                 "-d", "9")
        self.assertEqual(code, cli.EXIT_OK)
        self.assertIn("Packages (4):", out)

    def test_reverse_filter(self):
        _, out = self.run_cli("diamond.txt", "-p", "D", "--reverse",
                              "-f", "B")
        self.assertNotIn("B", out.replace("Reverse", ""))

    def test_reverse_of_unreferenced_package(self):
        _, out = self.run_cli("chain.txt", "-p", "A", "--reverse")
        self.assertIn("Packages (1):", out)


if __name__ == "__main__":
    unittest.main()
