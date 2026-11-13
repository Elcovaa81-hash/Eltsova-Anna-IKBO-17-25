"""Rendering DOT text to an image with the Graphviz ``dot`` program."""

import os
import subprocess
import tempfile
import webbrowser
from pathlib import Path

IMAGE_FORMATS = ("png", "svg", "pdf")
DEFAULT_FORMAT = "png"


class RenderError(Exception):
    """Raised when the image cannot be produced or shown."""


def image_format(path):
    """Return the image format implied by the file extension."""
    ext = Path(path).suffix.lstrip(".").lower()
    if ext not in IMAGE_FORMATS:
        raise RenderError(f"unsupported image format {ext!r}, "
                          f"use one of: {', '.join(IMAGE_FORMATS)}")
    return ext


def render_image(dot_text, path):
    """Render DOT text into the image file ``path`` using Graphviz."""
    fmt = image_format(path)
    try:
        subprocess.run(["dot", f"-T{fmt}", "-o", path], input=dot_text,
                       text=True, check=True, capture_output=True)
    except FileNotFoundError:
        raise RenderError("Graphviz 'dot' is not installed")
    except subprocess.CalledProcessError as exc:
        raise RenderError(f"dot failed: {exc.stderr.strip()}")
    except OSError as exc:
        raise RenderError(f"cannot write {path}: {exc}")


def temp_image_path():
    """Return a fresh temporary path for a preview image."""
    handle, path = tempfile.mkstemp(suffix="." + DEFAULT_FORMAT)
    os.close(handle)
    return path


def show_image(path):
    """Open the image in the default viewer (browser)."""
    uri = Path(path).resolve().as_uri()
    if not webbrowser.open(uri):
        print(f"cannot open a viewer automatically, open {path}")
