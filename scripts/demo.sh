#!/bin/sh
# Demo of depviz. Run from the repository root: sh scripts/demo.sh
export PYTHONPATH=src
URL=https://dl-cdn.alpinelinux.org/alpine/v3.20/main/x86_64
run() { echo "\$ depviz $*"; python3 -m depviz "$@"; echo "(exit $?)"; echo; }

echo "=== Stage 1: parameters and error handling ==="
run -p curl -r "$URL" -d 2 -f lib
run -p "bad name" -r "$URL"
run -p curl -r ftp://example.org
run -p A -r /no/such/file -m test
run -p A -r "$URL" -m fake
run -p A -r "$URL" -d -5
run -p A -r "$URL" -d abc
run -p libfoo -r "$URL" -f lib
