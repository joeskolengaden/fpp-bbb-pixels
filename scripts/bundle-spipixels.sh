#!/bin/bash
# Run before publishing the repo: copies the SPIPixels plugin source next to install.sh so a Plugin Manager install is self-contained
# (install.sh builds it from $HERE/SPIPixels first). The single source of truth stays plugins/SPIPixels in the project.
set -e
HERE="$(cd "$(dirname "$0")/.." && pwd)"
SRC="${1:-$HERE/../plugins/SPIPixels}"
[ -d "$SRC/src" ] || { echo "SPIPixels source not found at $SRC" >&2; exit 1; }
rm -rf "$HERE/SPIPixels" && mkdir -p "$HERE/SPIPixels"
cp -R "$SRC/src" "$SRC/Makefile" "$SRC/README.md" "$SRC/tests" "$HERE/SPIPixels/"
echo "bundled SPIPixels ($(ls "$HERE/SPIPixels/src" | tr '\n' ' '))"
