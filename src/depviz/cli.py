"""Command line interface of the dependency graph visualizer."""

import argparse
import os
import re
import sys
from dataclasses import dataclass
from urllib.parse import urlparse

from depviz import apk, render, testrepo
from depviz.dot import to_dot
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
    dot: str = ""
    output: str = ""
    show: bool = False


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
    parser.add_argument("--dot", metavar="FILE", default="",
                        help="write the Graphviz DOT text to FILE "
                             "('-' prints it to stdout)")
    parser.add_argument("-o", "--output", metavar="IMAGE", default="",
                        help="render an image (png, svg or pdf) with "
                             "Graphviz")
    parser.add_argument("--show", action="store_true",
                        help="open the rendered image in a viewer")
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
    if config.output:
        try:
            render.image_format(config.output)
        except render.RenderError as exc:
            raise ConfigError(str(exc))


def parse_config(argv=None):
    """Parse and validate command line options into a Config."""
    args = build_parser().parse_args(argv)
    config = Config(args.package, args.repo, args.repo_mode,
                    args.max_depth, args.name_filter, args.reverse,
                    args.dot, args.output, args.show)
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


def build_graph(config):
    """Load the repository and traverse it, returning a DepGraph."""
    adjacency = load_graph(config)
    if config.reverse:
        adjacency = reverse_adjacency(adjacency)
    return traverse(adjacency, config.package, config.max_depth,
                    config.name_filter)


def write_dot(text, path):
    """Write DOT text to a file, or to stdout when path is '-'."""
    if path == "-":
        print(text, end="")
        return
    try:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
    except OSError as exc:
        raise render.RenderError(f"cannot write {path}: {exc}")


def visualize(graph, config):
    """Produce the DOT file, image and preview requested by the user."""
    edges = oriented_edges(graph, config.reverse)
    text = to_dot(graph, edges, config.package)
    if config.dot:
        write_dot(text, config.dot)
    image = config.output
    if config.show and not image:
        image = render.temp_image_path()
    if image:
        render.render_image(text, image)
        print(f"image written to {image}")
    if config.show:
        render.show_image(image)


def main(argv=None):
    """Run the tool, returning a process exit code."""
    try:
        config = parse_config(argv)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    try:
        graph = build_graph(config)
        if config.dot != "-":
            print_graph(graph, config)
        visualize(graph, config)
    except (apk.RepoError, render.RenderError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR
    return EXIT_OK
