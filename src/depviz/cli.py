"""Command line interface of the dependency graph visualizer."""

import argparse
import os
import re
import sys
from dataclasses import dataclass
from urllib.parse import urlparse

from depviz import apk, testrepo
from depviz.graph import reverse_adjacency, traverse

REPO_MODES = ("remote", "test")
DEFAULT_DEPTH = 3
MIN_DEPTH = 0
EXIT_OK = 0
EXIT_ERROR = 1
EXIT_USAGE = 2
PACKAGE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]*$")
URL_SCHEMES = ("http", "https")


class ConfigError(Exception):
    """Raised when a user supplied parameter is invalid."""


@dataclass
class Config:
    """User configurable parameters of the tool."""

    package: str
    repo: str
    repo_mode: str
    max_depth: int
    name_filter: str
    reverse: bool = False


def non_negative_int(text):
    """Parse a non-negative integer for argparse."""
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not an integer: {text!r}")
    if value < MIN_DEPTH:
        raise argparse.ArgumentTypeError(f"must be >= {MIN_DEPTH}: {value}")
    return value


def build_parser():
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="depviz",
        description="Dependency graph visualizer for apk packages.",
    )
    parser.add_argument("-p", "--package", required=True,
                        help="name of the package to analyze")
    parser.add_argument("-r", "--repo", required=True,
                        help="repository URL or path to a test repo file")
    parser.add_argument("-m", "--repo-mode", choices=REPO_MODES,
                        default="remote",
                        help="remote: real apk repository URL; "
                             "test: path to a test repository file")
    parser.add_argument("-d", "--max-depth", type=non_negative_int,
                        default=DEFAULT_DEPTH,
                        help="maximum dependency depth (default: 3)")
    parser.add_argument("-f", "--filter", default="", dest="name_filter",
                        help="skip packages whose name contains this text")
    parser.add_argument("--reverse", action="store_true",
                        help="show reverse dependencies (packages that "
                             "depend on the given package)")
    return parser


def validate_package(package):
    """Check that the package name is syntactically valid."""
    if not PACKAGE_RE.match(package):
        raise ConfigError(f"invalid package name: {package!r}")


def validate_repo(repo, mode):
    """Check the repository location according to the selected mode."""
    if mode == "remote":
        parsed = urlparse(repo)
        if parsed.scheme not in URL_SCHEMES or not parsed.netloc:
            raise ConfigError(f"repository must be an http(s) URL: {repo!r}")
    elif not os.path.isfile(repo):
        raise ConfigError(f"test repository file not found: {repo!r}")


def validate(config):
    """Validate every parameter, raising ConfigError on problems."""
    validate_package(config.package)
    validate_repo(config.repo, config.repo_mode)
    if config.name_filter and config.name_filter in config.package:
        raise ConfigError("the analyzed package matches the filter "
                          f"{config.name_filter!r}")


def parse_config(argv=None):
    """Parse and validate command line options into a Config."""
    args = build_parser().parse_args(argv)
    config = Config(args.package, args.repo, args.repo_mode,
                    args.max_depth, args.name_filter, args.reverse)
    validate(config)
    return config


def print_graph(graph, config):
    """Print the dependency graph as a list of edges and nodes."""
    kind = "Reverse dependency" if config.reverse else "Dependency"
    print(f"{kind} graph of {config.package} "
          f"(max depth {config.max_depth}):")
    for source, target in oriented_edges(graph, config.reverse):
        print(f"  {source} -> {target}")
    print(f"Packages ({len(graph.depths)}):")
    for name, depth in graph.depths.items():
        print(f"  {name} (depth {depth})")


def oriented_edges(graph, reverse):
    """Return edges as "dependent -> dependency" pairs."""
    if reverse:
        return [(target, source) for source, target in graph.edges]
    return graph.edges


def load_graph(config):
    """Load the adjacency dict described by the configuration."""
    if config.repo_mode == "test":
        adjacency = testrepo.load_graph(config.repo)
    else:
        adjacency = apk.load_graph(config.repo)
    if config.package not in adjacency:
        raise apk.RepoError(f"package not found: {config.package}")
    return adjacency


def main(argv=None):
    """Run the tool, returning a process exit code."""
    try:
        config = parse_config(argv)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    try:
        adjacency = load_graph(config)
    except apk.RepoError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR
    if config.reverse:
        adjacency = reverse_adjacency(adjacency)
    graph = traverse(adjacency, config.package, config.max_depth,
                     config.name_filter)
    print_graph(graph, config)
    return EXIT_OK
