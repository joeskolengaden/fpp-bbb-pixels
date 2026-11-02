#!/bin/bash
# Simulates scripts/preStart.sh in five file states and checks its verdicts. No FPP needed.
HERE="$(cd "$(dirname "$0")/.." && pwd)"; T=$(mktemp -d); trap 'rm -rf "$T"' EXIT; FAILS=0
mkdir -p $T/src/channeloutput $T/src/pru $T/www $T/cfg $T/log; touch $T/src/channeloutput/BBB48String.cpp $T/www/co-pixelStrings.php $T/src/libfpp.so
run() { rm -f $T/cfg/flag; FBP_SRC=$T/src FBP_WWW=$T/www FBP_CFG=$T/cfg/c.json FBP_LOG=$T/log/f.log FBP_FLAG=$T/cfg/flag bash "$HERE/scripts/preStart.sh" >/dev/null; echo $?; }
expect() { # name, want_rc, want_warning(1/0), want_flag(1/0)
  rc=$(run); w=$(grep -c "WARNING" $T/log/f.log 2>/dev/null); [ -f $T/cfg/flag ] && f=1 || f=0; : > $T/log/f.log
  if [ "$rc" = "$2" ] && [ "$( [ "$w" -gt 0 ] && echo 1 || echo 0)" = "$3" ] && [ "$f" = "$4" ]; then echo "ok   $1"; else echo "FAIL $1 (rc=$rc warn=$w flag=$f)"; FAILS=$((FAILS+1)); fi; }
: > $T/log/f.log
echo '#if defined(PIXELTYPE_APA104)' > $T/src/pru/FalconWS281x.asm; echo '-DPIXELTYPE_APA104' > $T/src/libfpp-co-BBB48String.so
echo '{"channelOutputs":[{"type":"BBB48String","pixelTiming":6}]}' > $T/cfg/c.json;  expect "round-1 install, config preset 6 -> no warning, note flag" 0 0 1
echo '{"channelOutputs":[{"type":"BBB48String","pixelTiming":11}]}' > $T/cfg/c.json; expect "round-1 install, config Custom (11) -> WARNING + flag" 0 1 1
: > $T/src/pru/FalconWS281x.asm; : > $T/src/libfpp-co-BBB48String.so
echo '{"channelOutputs":[{"type":"BBB48String","pixelTiming":6}]}' > $T/cfg/c.json;  expect "stock files, config preset 6 -> WARNING + flag" 0 1 1
echo 'PIXELTYPE_APA104 PIXELTYPE_CUSTOM' > $T/src/pru/FalconWS281x.asm; echo '-DPIXELTYPE_APA104 -DCUSTOM_T0=' > $T/src/libfpp-co-BBB48String.so; echo tm1908 > $T/src/libfpp.so; echo fbpCustT0 > $T/www/co-pixelStrings.php
expect "fully patched -> silent, no flag" 0 0 0
echo 'not json' > $T/cfg/c.json; expect "garbage config -> still exits 0, silent" 0 0 0
mkdir -p $T/nobbb; FBP_SRC=$T/nobbb bash "$HERE/scripts/preStart.sh" >/dev/null && echo "ok   not a BeagleBone (no driver) -> exit 0" || { echo "FAIL no-driver case"; FAILS=$((FAILS+1)); }
exit $FAILS
