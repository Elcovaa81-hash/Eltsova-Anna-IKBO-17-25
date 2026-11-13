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

echo "=== Stage 2: direct dependencies from a real apk repository ==="
run -p curl -r "$URL"
run -p busybox -r "$URL"
run -p no-such-package-xyz -r "$URL"
run -p curl -r http://127.0.0.1:9/unreachable

echo "=== Stage 3: DFS, depth limit, filter, cycles (test repository) ==="
T="-m test"
run $T -r examples/chain.txt -p A
run $T -r examples/chain.txt -p A -d 2
run $T -r examples/chain.txt -p A -d 0
run $T -r examples/diamond.txt -p A
run $T -r examples/cycle.txt -p A -d 10
run $T -r examples/shortcut.txt -p A -d 3
run $T -r examples/prefixed.txt -p APP -f AB
run $T -r examples/chain.txt -p Z
