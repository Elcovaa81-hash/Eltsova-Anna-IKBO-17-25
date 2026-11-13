"""Tests for the apk index reader."""

import contextlib
import io
import unittest

from depviz import apk, cli
from helpers import INDEX_TEXT, make_archive, serve, stop


class ParseTest(unittest.TestCase):
    """Index parsing and dependency resolution."""

    def setUp(self):
        """Parse the sample index once per test."""
        self.packages = apk.parse_index(INDEX_TEXT)
        self.graph = apk.build_graph(self.packages)

    def test_parse_names(self):
        self.assertEqual(set(self.packages),
                         {"musl", "zlib", "curl", "ca-certificates"})

    def test_provides_and_constraints_are_resolved(self):
        self.assertEqual(self.graph["curl"],
                         ["ca-certificates", "musl", "zlib"])

    def test_unknown_and_conflicts_skipped(self):
        self.assertEqual(self.graph["ca-certificates"], ["musl", "zlib"])

    def test_leaf_package(self):
        self.assertEqual(self.graph["musl"], [])

    def test_strip_constraint(self):
        self.assertEqual(apk.strip_constraint("zlib>=1.0"), "zlib")
        self.assertEqual(apk.strip_constraint("so:libz.so.1=1.3"),
                         "so:libz.so.1")

    def test_index_url(self):
        self.assertEqual(apk.index_url("http://h/a/"),
                         "http://h/a/APKINDEX.tar.gz")
        self.assertEqual(apk.index_url("http://h/x.tar.gz"),
                         "http://h/x.tar.gz")


class ArchiveTest(unittest.TestCase):
    """Archive extraction and HTTP download."""

    def test_extract_multi_member_archive(self):
        text = apk.extract_index(make_archive())
        self.assertIn("P:curl", text)

    def test_broken_archive(self):
        with self.assertRaises(apk.RepoError):
            apk.extract_index(b"not an archive")

    def test_load_graph_over_http(self):
        server, url = serve(make_archive())
        self.addCleanup(stop, server)
        graph = apk.load_graph(url)
        self.assertIn("zlib", graph["curl"])

    def test_empty_index(self):
        server, url = serve(make_archive("\n"))
        self.addCleanup(stop, server)
        with self.assertRaises(apk.RepoError):
            apk.load_graph(url)


class CliTest(unittest.TestCase):
    """End-to-end run of the CLI against a local server."""

    def run_cli(self, package):
        """Run the CLI and return (code, stdout)."""
        server, url = serve(make_archive())
        self.addCleanup(stop, server)
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(
                io.StringIO()):
            code = cli.main(["-p", package, "-r", url])
        return code, out.getvalue()

    def test_prints_direct_dependencies(self):
        code, out = self.run_cli("curl")
        self.assertEqual(code, cli.EXIT_OK)
        self.assertIn("Direct dependencies of curl (3):", out)
        self.assertIn("  zlib", out)

    def test_unknown_package(self):
        code, _ = self.run_cli("nothing")
        self.assertEqual(code, cli.EXIT_ERROR)


if __name__ == "__main__":
    unittest.main()
