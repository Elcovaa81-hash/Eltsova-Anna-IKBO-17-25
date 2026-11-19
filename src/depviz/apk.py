"""Reading dependencies from an Alpine Linux (apk) repository index.

The repository publishes ``APKINDEX.tar.gz``. It is a tar archive that
contains a text file ``APKINDEX`` with one record per package. Records are
separated by an empty line, every line looks like ``K:value``:

* ``P`` - package name, ``V`` - version;
* ``D`` - space separated dependencies;
* ``p`` - space separated names the package provides.
"""

import io
import re
import tarfile
import urllib.error
import urllib.request

INDEX_NAME = "APKINDEX"
INDEX_ARCHIVE = "APKINDEX.tar.gz"
TIMEOUT_SECONDS = 30
CONSTRAINT_RE = re.compile(r"[<>=~].*$")


class RepoError(Exception):
    """Raised when the repository cannot be loaded or parsed."""


def index_url(base):
    """Return the URL of the index archive for a repository URL."""
    if base.endswith(".tar.gz"):
        return base
    return base.rstrip("/") + "/" + INDEX_ARCHIVE


def download(url):
    """Download a URL and return its body as bytes."""
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT_SECONDS) as reply:
            return reply.read()
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise RepoError(f"cannot download {url}: {exc}")


def extract_index(archive):
    """Return the text of the APKINDEX file inside the archive bytes.

    The archive consists of several gzip segments (signature and index).
    The signature segment may end with padding blocks, so the archive is
    opened with ``ignore_zeros=True`` to keep reading past them.

    Args:
        archive: contents of ``APKINDEX.tar.gz`` as bytes.

    Returns:
        The decoded text of the ``APKINDEX`` file.

    Raises:
        RepoError: if the archive is damaged or has no regular
            ``APKINDEX`` file.
    """
    try:
        stream = io.BytesIO(archive)
        with tarfile.open(fileobj=stream, mode="r:gz",
                          ignore_zeros=True) as tar:
            member = tar.extractfile(INDEX_NAME)
            if member is None:
                raise RepoError(f"{INDEX_NAME} is not a regular file")
            return member.read().decode("utf-8")
    except (tarfile.TarError, OSError, KeyError, EOFError) as exc:
        raise RepoError(f"invalid index archive: {exc}")


def parse_index(text):
    """Parse APKINDEX text into ``{name: {"D": [...], "p": [...]}}``."""
    packages = {}
    for block in text.split("\n\n"):
        fields = {}
        for line in block.splitlines():
            key, sep, value = line.partition(":")
            if sep:
                fields[key] = value.strip()
        name = fields.get("P")
        if name:
            packages[name] = {"D": fields.get("D", "").split(),
                              "p": fields.get("p", "").split()}
    return packages


def strip_constraint(token):
    """Drop a version constraint: ``so:libz.so.1=1.3`` -> ``so:libz.so.1``."""
    return CONSTRAINT_RE.sub("", token)


def build_provides(packages):
    """Map every provided virtual name (so:, cmd:, ...) to a package."""
    provides = {}
    for name, info in packages.items():
        for token in info["p"]:
            provides.setdefault(strip_constraint(token), name)
    return provides


def resolve(token, name, packages, provides):
    """Resolve a dependency token to a real package name or None.

    Conflicts (``!pkg``) and names absent from the index give None, as
    does a dependency that resolves to the package itself.
    """
    if token.startswith("!"):
        return None
    target = strip_constraint(token)
    if target not in packages:
        target = provides.get(target)
    return None if target in (None, name) else target


def build_graph(packages):
    """Return ``{package: [direct dependency, ...]}`` for all packages."""
    provides = build_provides(packages)
    graph = {}
    for name, info in packages.items():
        deps = []
        for token in info["D"]:
            target = resolve(token, name, packages, provides)
            if target is not None and target not in deps:
                deps.append(target)
        graph[name] = deps
    return graph


def load_graph(url):
    """Download and parse a repository, returning its dependency graph."""
    text = extract_index(download(index_url(url)))
    packages = parse_index(text)
    if not packages:
        raise RepoError("the index does not contain any packages")
    return build_graph(packages)
