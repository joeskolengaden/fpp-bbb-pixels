#!/bin/bash
# Every automated check for this repository. Run locally or from CI:
#   FPP_SRC=/path/to/stock/fpp-5.4.1 [FBP_SCHEMA=/path/pluginInfo.schema.json] bash scripts/check-all.sh
# FPP_SRC is a checkout of FalconChristmas/fpp at tag 5.4.1 (unmodified). Without it the patcher checks are skipped (and reported as skipped).
cd "$(dirname "$0")/.."
FAILS=0; SKIPS=0
ok()   { echo "  ok    $*"; }
bad()  { echo "  FAIL  $*"; FAILS=$((FAILS+1)); }
skip() { echo "  skip  $*"; SKIPS=$((SKIPS+1)); }
step() { echo; echo "== $* =="; }

step "shell scripts parse"
for f in $(git ls-files '*.sh' 2>/dev/null || find . -name '*.sh' -not -path './dist/*'); do bash -n "$f" 2>/dev/null && ok "$f" || bad "$f"; done

step "python files compile"
for f in $(ls *.py hwtest/*.py tests/*.py 2>/dev/null | grep -v '_10x\.py$'); do python3 -m py_compile "$f" 2>/dev/null && ok "$f" || bad "$f"; done
find . -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null

step "page code parses"
if command -v node >/dev/null; then node --check ui_limits.js 2>/dev/null && ok ui_limits.js || bad ui_limits.js; else skip "node not installed (ui_limits.js)"; fi
if command -v php >/dev/null; then for f in plugin.php menu.inc; do php -l "$f" >/dev/null 2>&1 && ok "$f" || bad "$f"; done; else skip "php not installed"; fi

step "pluginInfo.json"
python3 - <<'PY' && ok "valid JSON, required fields, FPP schema (if available)" || bad "pluginInfo.json"
import json, os, sys
d = json.load(open("pluginInfo.json"))
for k in ("repoName", "name", "author", "description", "homeURL", "srcURL", "bugURL", "versions", "privacy"):
    assert k in d, "missing " + k
assert d["repoName"] == "fpp-bbb-pixels" and d["srcURL"].endswith("/fpp-bbb-pixels.git")
assert all(k in d["privacy"] for k in ("summary", "sends", "collects", "sensors", "remoteAccess", "systemChanges", "closedCode", "other"))
sch = os.environ.get("FBP_SCHEMA")
if sch and os.path.exists(sch):
    try:
        import jsonschema
    except ImportError:
        print("  (jsonschema not installed: schema check skipped)", file=sys.stderr); sys.exit(0)
    errs = list(jsonschema.Draft202012Validator(json.load(open(sch))).iter_errors(d))
    assert not errs, "; ".join(e.message for e in errs[:3])
PY

step "version consistency"
V=$(cat VERSION); grep -q "^## $V " CHANGELOG.md && ok "VERSION $V has a CHANGELOG entry" || bad "VERSION $V is missing from CHANGELOG.md"
./install.sh --version 2>/dev/null | grep -q "$V" && ok "install.sh --version" || bad "install.sh --version"

step "SPI chip framing (unit tests + independent cross-check)"
SPI=SPIPixels; [ -d "$SPI/src" ] || SPI=../plugins/SPIPixels
if [ -d "$SPI/src" ] && command -v c++ >/dev/null; then
  T=$(mktemp -d)
  c++ -std=gnu++17 -I"$SPI/src" "$SPI/tests/test_format.cpp" -o "$T/t" 2>"$T/err" && "$T/t" | tail -1 | grep -q "ALL TESTS PASSED" && ok "unit tests" || { bad "unit tests"; head -5 "$T/err"; }
  c++ -std=gnu++17 -I"$SPI/src" hwtest/spi_dump.cpp -o "$T/spi_dump" 2>/dev/null && python3 hwtest/spi_xcheck.py "$T/spi_dump" | tail -1 | grep -q PASSED && ok "225-vector cross-check, every protocol" || bad "spi cross-check"
  rm -rf "$T"
else skip "SPIPixels source or a C++ compiler not found"; fi

step "installer safety"
# After a successful rebuild the rollback (ERR) trap must be cleared: a harmless failing command later in the script once rolled a good install back.
python3 - <<'PY' && ok "ERR trap is cleared right after the rebuild succeeds, before anything else can fail" || bad "install.sh: ERR trap not cleared after the rebuild"
s = open("install.sh").read()
i = s.index('echo "  rebuilt libfpp.so + libfpp-co-BBB48String.so"'); j = s.index("trap - ERR")
assert j > i, "trap - ERR must come after the rebuild"
tail = s[j:]
assert "set -Eeuo pipefail" in s and "systemctl start fppd; sleep 10" in s[i:j], "expected structure changed"
assert 'trap \'rollback' not in tail, "rollback trap re-armed after success"
PY
grep -q "rm -f /home/fpp/media/config/fbp-version" install.sh && ok "rollback removes the version stamp" || bad "rollback leaves a stale version stamp"

bash tests/test_installer_retry.sh >/tmp/fbp_t3.out 2>&1 && ok "installer retries a crashed Python step, never a real failure" || { bad "installer retry"; cat /tmp/fbp_t3.out; }

step "start-up guard and health-check rule"
bash tests/test_prestart.sh >/tmp/fbp_t1.out 2>&1 && ok "preStart.sh guard (6 cases)" || { bad "preStart.sh guard"; cat /tmp/fbp_t1.out; }
python3 tests/test_doctor_rule.py >/tmp/fbp_t2.out 2>&1 && ok "output-thread budget rule reproduces the stress measurements" || { bad "doctor rule"; cat /tmp/fbp_t2.out; }

step "patchers against stock FPP 5.4.1"
if [ -n "$FPP_SRC" ] && [ -f "$FPP_SRC/src/channeloutput/BBB48String.cpp" ]; then
  W=$(mktemp -d); mkdir -p "$W/orig" "$W/work"
  FILES="src/pru/FalconWS281x.asm src/channeloutput/BBB48String.cpp src/channeloutput/PixelString.cpp www/co-pixelStrings.php www/api/controllers/system.php www/fppjson.php"
  for f in $FILES; do mkdir -p "$W/work/$(dirname "$f")"; cp "$FPP_SRC/$f" "$W/work/$f"; done
  run() { python3 "$1" "$2" >"$W/log" 2>&1 || { bad "$1 aborted: $(tail -1 "$W/log")"; return 1; }; }
  run patch_asm.py "$W/work/src/pru/FalconWS281x.asm" && ok "patch_asm.py"
  run patch_bbb48string.py "$W/work/src/channeloutput/BBB48String.cpp" && ok "patch_bbb48string.py"
  run patch_pixelstring.py "$W/work/src/channeloutput/PixelString.cpp" && ok "patch_pixelstring.py"
  run patch_ui.py "$W/work/www/co-pixelStrings.php" && ok "patch_ui.py"
  run patch_php_notices.py "$W/work/www/api/controllers/system.php" && ok "patch_php_notices.py (system.php)"
  run patch_php_notices.py "$W/work/www/fppjson.php" && ok "patch_php_notices.py (fppjson.php)"
  for f in $FILES; do cp "$W/work/$f" "$W/orig/$(echo "$f" | tr / _)"; done
  # second run must change nothing (idempotent) and must not abort
  run patch_asm.py "$W/work/src/pru/FalconWS281x.asm"; run patch_bbb48string.py "$W/work/src/channeloutput/BBB48String.cpp"
  run patch_pixelstring.py "$W/work/src/channeloutput/PixelString.cpp"; run patch_ui.py "$W/work/www/co-pixelStrings.php"
  for f in $FILES; do cmp -s "$W/work/$f" "$W/orig/$(echo "$f" | tr / _)" && ok "idempotent: $f" || bad "second run changed $f"; done
  # the stock files must have changed, and must carry every feature marker
  grep -q PIXELTYPE_CUSTOM "$W/work/src/pru/FalconWS281x.asm" && grep -q PIXELTYPE_APA104 "$W/work/src/pru/FalconWS281x.asm" && ok "PRU source has presets + Custom block" || bad "PRU markers"
  grep -q fbpCustomDefines "$W/work/src/channeloutput/BBB48String.cpp" && grep -q fbpCfgInt "$W/work/src/channeloutput/BBB48String.cpp" && ok "driver has Custom timing + safe config reads" || bad "driver markers"
  grep -q 'preambleProfile == "tm1908"' "$W/work/src/channeloutput/PixelString.cpp" && ok "PixelString has TM1908 + current controls" || bad "PixelString markers"
  grep -q fbpCustT0 "$W/work/www/co-pixelStrings.php" && php -l "$W/work/www/co-pixelStrings.php" >/dev/null 2>&1 && ok "patched pixel-strings page lints" || bad "page markers / lint"
  [ "$(grep -c 'value="1[1-8]"' "$W/work/www/co-pixelStrings.php")" -ge 8 ] && ok "page menu lists presets 11-18" || bad "page menu"
  rm -rf "$W"
else skip "FPP_SRC not set (a stock FPP 5.4.1 checkout is needed)"; fi

step "no private data in the tree"
LEAK=$(grep -rIlE '/Users/|/private/tmp/|joeandjoel|BEGIN (RSA|OPENSSH)|ghp_[A-Za-z0-9]{20}' . 2>/dev/null | grep -v '^./hwtest/results/\|^./.git/\|^./dist/\|check-all.sh$')
[ -z "$LEAK" ] && ok "no personal paths, addresses or keys" || { bad "private data in: $LEAK"; }

echo; echo "check-all: $FAILS failure(s), $SKIPS skipped"; exit $((FAILS>0))
