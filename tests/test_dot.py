"""Tests for DOT generation, rendering and the visualization options."""

import contextlib
import io
import os
import shutil
import tempfile
import unittest

from depviz import cli, render
from depviz.dot import quote, to_dot
from depviz.graph import traverse

EXAMPLES = os.path.join(os.path.dirname(__file__), "..", "examples")
CHAIN = os.path.join(EXAMPLES, "chain.txt")


def run(*argv):
    """Run the CLI in test mode, return (code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = cli.main(["-m", "test", *argv])
        except SystemExit as exc:
            code = exc.code
    return code, out.getvalue(), err.getvalue()


class DotTest(unittest.TestCase):
    """DOT text."""

    def test_quote(self):
        self.assertEqual(quote('a"b'), '"a\\"b"')

    def test_dot_text(self):
        graph = traverse({"A": ["B"], "B": []}, "A", 5)
        text = to_dot(graph, graph.edges, "A")
        self.assertTrue(text.startswith('digraph "A" {'))
        self.assertIn('"A" -> "B";', text)
        self.assertIn("fillcolor", text)
        self.assertTrue(text.rstrip().endswith("}"))

    def test_isolated_root_is_declared(self):
        graph = traverse({"A": []}, "A", 5)
        self.assertIn('"A" [', to_dot(graph, [], "A"))

    def test_cli_dot_to_stdout(self):
        code, out, _ = run("-r", CHAIN, "-p", "A", "--dot", "-")
        self.assertEqual(code, cli.EXIT_OK)
        self.assertTrue(out.startswith("digraph"))
        self.assertNotIn("Packages", out)

    def test_reverse_keeps_original_direction(self):
        _, out, _ = run("-r", CHAIN, "-p", "D", "--reverse", "--dot", "-")
        self.assertIn('"C" -> "D";', out)


class FilesTest(unittest.TestCase):
    """Writing DOT files and images."""

    def setUp(self):
        """Create a scratch directory."""
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)

    def test_dot_file(self):
        path = os.path.join(self.tmp, "g.dot")
        code, _, _ = run("-r", CHAIN, "-p", "A", "--dot", path)
        self.assertEqual(code, cli.EXIT_OK)
        with open(path, encoding="utf-8") as handle:
            self.assertIn('"B" -> "C";', handle.read())

    def test_bad_dot_path(self):
        code, _, err = run("-r", CHAIN, "-p", "A", "--dot", "/no/dir/g.dot")
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("cannot write", err)

    def test_bad_image_extension(self):
        code, _, err = run("-r", CHAIN, "-p", "A", "-o", "x.bmp")
        self.assertEqual(code, cli.EXIT_USAGE)
        self.assertIn("unsupported image format", err)

    @unittest.skipUnless(shutil.which("dot"), "Graphviz is not installed")
    def test_render_svg(self):
        path = os.path.join(self.tmp, "g.svg")
        code, out, _ = run("-r", CHAIN, "-p", "A", "-o", path)
        self.assertEqual(code, cli.EXIT_OK)
        self.assertIn("image written", out)
        with open(path, encoding="utf-8") as handle:
            self.assertIn("<svg", handle.read())

    def test_render_without_dot_program(self):
        old = os.environ["PATH"]
        os.environ["PATH"] = ""
        self.addCleanup(os.environ.__setitem__, "PATH", old)
        with self.assertRaises(render.RenderError):
            render.render_image("digraph {}", os.path.join(self.tmp, "a.png"))


if __name__ == "__main__":
    unittest.main()
