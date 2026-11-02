#!/bin/bash
# Build the release bundle from the committed tree:  bash scripts/build-release.sh   ->  dist/fpp-bbb-pixels-<version>.tar.gz + SHA256SUMS
# The bundle is exactly what `git archive` takes from HEAD, so it contains only tracked files (no local test evidence, no private data).
set -e
cd "$(dirname "$0")/.."
V=$(cat VERSION)
[ -z "$(git status --porcelain 2>/dev/null)" ] || { echo "working tree has uncommitted changes: commit first so the bundle matches a commit" >&2; exit 1; }
[ -d SPIPixels/src ] || { echo "SPIPixels/ is missing: run scripts/bundle-spipixels.sh and commit" >&2; exit 1; }
mkdir -p dist; rm -f dist/*
git archive --format=tar --prefix="fpp-bbb-pixels-$V/" HEAD | gzip -9n > "dist/fpp-bbb-pixels-$V.tar.gz"
( cd dist && { sha256sum "fpp-bbb-pixels-$V.tar.gz" 2>/dev/null || shasum -a 256 "fpp-bbb-pixels-$V.tar.gz"; } > SHA256SUMS )
cat dist/SHA256SUMS; ls -la dist | sed 's/^/  /'
