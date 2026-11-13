"""Helpers shared by the tests: a fake APKINDEX archive and HTTP server."""

import gzip
import http.server
import io
import tarfile
import threading

INDEX_TEXT = """C:Q1abc=
P:musl
V:1.2.5-r0
p:so:libc.musl-x86_64.so.1=1

C:Q1def=
P:zlib
V:1.3.1-r1
D:so:libc.musl-x86_64.so.1
p:so:libz.so.1=1.3.1

C:Q1ghi=
P:curl
V:8.9.0-r0
D:ca-certificates so:libc.musl-x86_64.so.1 so:libz.so.1 !conflict>=1
p:cmd:curl=8.9.0-r0

C:Q1jkl=
P:ca-certificates
V:20240705-r0
D:so:libc.musl-x86_64.so.1 so:libmissing.so.9 zlib>=1.0
"""


def make_archive(text=INDEX_TEXT):
    """Build an APKINDEX.tar.gz like Alpine does (two gzip members)."""
    signature = io.BytesIO()
    with tarfile.open(fileobj=signature, mode="w") as tar:
        info = tarfile.TarInfo(".SIGN.RSA.test")
        info.size = 4
        tar.addfile(info, io.BytesIO(b"fake"))
    data = text.encode("utf-8")
    body = io.BytesIO()
    with tarfile.open(fileobj=body, mode="w") as tar:
        info = tarfile.TarInfo("APKINDEX")
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))
    return gzip.compress(signature.getvalue()) + gzip.compress(
        body.getvalue())


class QuietHandler(http.server.BaseHTTPRequestHandler):
    """Serve the fake archive for any path."""

    archive = b""

    def do_GET(self):
        """Reply with the archive."""
        self.send_response(200)
        self.end_headers()
        self.wfile.write(self.archive)

    def log_message(self, *args):
        """Silence request logging."""


def serve(archive):
    """Start a local HTTP server, returning (server, base_url)."""
    handler = type("Handler", (QuietHandler,), {"archive": archive})
    server = http.server.HTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_port}/alpine/main/x86_64"


def stop(server):
    """Stop a server started by serve() and release its socket."""
    server.shutdown()
    server.server_close()
