#!/bin/bash
# fpp-bbb-pixels start-up guard. FPP runs every plugin's scripts/preStart.sh as root before each fppd start. It never blocks
# the start (always exits 0) and changes nothing except our own leftovers; it only makes a half-applied state visible, because
# the dangerous case is silent: after an FPP upgrade/restore puts a stock BBB48String library back, a saved "Pixel Timing" of
# 11-18 (Custom / datasheet presets) is read by the stock driver as plain "Slow" timing and the pixels show wrong colours.
#   - checks the compiled library, the PRU source and the UI page for our patches
#   - warns in fppd.log (and writes a flag file the plugin page shows) when the saved config needs a patch that is missing
#   - removes a test-harness compiler shim if one was left behind (hwtest/live_*.py/sh)
# Paths can be overridden for testing: FBP_SRC FBP_WWW FBP_CFG FBP_LOG FBP_FLAG
SRC="${FBP_SRC:-/opt/fpp/src}"; WWW="${FBP_WWW:-/opt/fpp/www}"
CFG="${FBP_CFG:-/home/fpp/media/config/co-bbbStrings.json}"
LOG="${FBP_LOG:-/home/fpp/media/logs/fppd.log}"
FLAG="${FBP_FLAG:-/home/fpp/media/config/fbp-needs-reapply}"
say() { echo "[fpp-bbb-pixels] $*"; [ -w "$(dirname "$LOG")" ] && echo "$(date '+%F %T') [fpp-bbb-pixels] $*" >> "$LOG" 2>/dev/null; }

# nothing to guard on a board without the BBB driver (Raspberry Pi: only the SPIPixels plugin applies)
[ -f "$SRC/channeloutput/BBB48String.cpp" ] || exit 0

# a leftover compiler shim from an interrupted test run: restore the stock compile script
SCR="$SRC/pru/compileWS2811x.sh"
if [ -f "$SCR.orig" ] && grep -q "ARGS" "$SCR" 2>/dev/null && grep -q "preset_test_args\|custom_args" "$SCR" 2>/dev/null; then
  cp -f "$SCR.orig" "$SCR" && say "restored the stock PRU compile script (a test shim was left behind)"
fi

base=""; r2=""        # base = presets 2-10 / UI limits (round 1), r2 = Custom + datasheet presets 11-18 (round 2)
grep -q "PIXELTYPE_APA104" "$SRC/pru/FalconWS281x.asm" 2>/dev/null || base="$base pru-timing-source"
grep -q "PIXELTYPE_CUSTOM" "$SRC/pru/FalconWS281x.asm" 2>/dev/null || r2="$r2 pru-timing-source"
if [ -f "$SRC/libfpp-co-BBB48String.so" ]; then
  grep -aq -- "-DPIXELTYPE_APA104" "$SRC/libfpp-co-BBB48String.so" 2>/dev/null || base="$base driver-library"
  grep -aq -- "-DCUSTOM_T0=" "$SRC/libfpp-co-BBB48String.so" 2>/dev/null || r2="$r2 driver-library"
fi
grep -aq "tm1908" "$SRC/libfpp.so" 2>/dev/null || r2="$r2 pixelstring-library"
grep -q "fbpCustT0" "$WWW/co-pixelStrings.php" 2>/dev/null || r2="$r2 config-page"
uniq() { echo "$@" | tr " " "\n" | sort -u | tr "\n" " " | sed "s/ $//"; }
missing=" $(uniq $base $r2)"

# what does the saved configuration need?
need=""
if [ -f "$CFG" ]; then
  need=$(python3 - "$CFG" <<'PY' 2>/dev/null
import json, sys
try:
    d = json.load(open(sys.argv[1]))
except Exception:
    sys.exit(0)
pt = set()
for co in d.get("channelOutputs", []):
    if co.get("type") == "BBB48String" and co.get("enabled", 1):
        try: pt.add(int(co.get("pixelTiming", 0)))
        except Exception: pass
if any(p >= 11 for p in pt): print("custom-or-datasheet-timing")
elif any(p >= 2 for p in pt): print("timing-preset")
PY
)
fi

harm=""     # missing patches that matter for the CURRENT config
case "$need" in
  custom-or-datasheet-timing) harm=" $(uniq $base $r2)" ;;
  timing-preset)              harm=" $(uniq $base)" ;;
esac
if [ -n "${harm// /}" ]; then
  say "WARNING: your pixel-string config uses a Pixel Timing preset ($need) but these patches are missing:$harm. FPP will drive the wrong pulse timing. Re-apply from Plugins > Pixel IC Support, or run: sudo bash $(cd "$(dirname "$0")/.." && pwd)/install.sh"
  echo "$missing" > "$FLAG" 2>/dev/null
elif [ -n "${missing// /}" ]; then
  say "note: patches missing:$missing (your current config does not need them). Re-apply from the plugin page when you do."
  echo "$missing" > "$FLAG" 2>/dev/null
else
  rm -f "$FLAG" 2>/dev/null
fi
exit 0
