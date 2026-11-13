"""Tests for command line parsing and validation."""

import contextlib
import io
import os
import tempfile
import unittest

from depviz import cli

URL = "https://dl-cdn.alpinelinux.org/alpine/v3.20/main/x86_64"


def run(argv):
    """Run the CLI, returning (exit code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = cli.main(argv)
        except SystemExit as exc:
            code = exc.code
    return code, out.getvalue(), err.getvalue()


class ParamsTest(unittest.TestCase):
    """Valid invocations."""

    def test_unreachable_repo_is_reported(self):
        code, _, err = run(["-p", "curl", "-r", "http://127.0.0.1:9/x"])
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("cannot download", err)


class ErrorsTest(unittest.TestCase):
    """Every parameter reports errors."""

    def test_missing_package(self):
        self.assertEqual(run(["-r", URL])[0], cli.EXIT_USAGE)

    def test_bad_package_name(self):
        code, _, err = run(["-p", "bad name!", "-r", URL])
        self.assertEqual(code, cli.EXIT_USAGE)
        self.assertIn("invalid package name", err)

    def test_bad_url(self):
        code, _, err = run(["-p", "curl", "-r", "ftp://x"])
        self.assertEqual(code, cli.EXIT_USAGE)
        self.assertIn("http(s) URL", err)

    def test_missing_test_file(self):
        code, _, err = run(["-p", "A", "-r", "/no/such", "-m", "test"])
        self.assertEqual(code, cli.EXIT_USAGE)
        self.assertIn("not found", err)

    def test_bad_mode(self):
        self.assertEqual(
            run(["-p", "A", "-r", URL, "-m", "fake"])[0], cli.EXIT_USAGE)

    def test_negative_depth(self):
        self.assertEqual(
            run(["-p", "A", "-r", URL, "-d", "-1"])[0], cli.EXIT_USAGE)

    def test_non_integer_depth(self):
        self.assertEqual(
            run(["-p", "A", "-r", URL, "-d", "x"])[0], cli.EXIT_USAGE)

    def test_package_matches_filter(self):
        code, _, err = run(["-p", "libfoo", "-r", URL, "-f", "lib"])
        self.assertEqual(code, cli.EXIT_USAGE)
        self.assertIn("filter", err)

    def test_test_mode_with_existing_file(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt",
                                         delete=False) as handle:
            handle.write("A: B\n")
        try:
            code, _, _ = run(["-p", "A", "-r", handle.name, "-m", "test"])
        finally:
            os.unlink(handle.name)
        self.assertEqual(code, cli.EXIT_OK)


if __name__ == "__main__":
    unittest.main()
