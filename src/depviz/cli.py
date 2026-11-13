"""Command line interface of the dependency graph visualizer."""

import argparse
import os
import re
import sys
from dataclasses import dataclass
from urllib.parse import urlparse

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
                    args.max_depth, args.name_filter)
    validate(config)
    return config


def print_params(config):
    """Print all user configurable parameters as key: value."""
    print(f"package: {config.package}")
    print(f"repo: {config.repo}")
    print(f"repo_mode: {config.repo_mode}")
    print(f"max_depth: {config.max_depth}")
    print(f"filter: {config.name_filter}")


def main(argv=None):
    """Run the tool, returning a process exit code."""
    try:
        config = parse_config(argv)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    print_params(config)
    return EXIT_OK
