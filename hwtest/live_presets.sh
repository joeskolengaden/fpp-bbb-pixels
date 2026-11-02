#!/bin/bash
# Live per-preset validation on the board: for pixelTiming 0..10 set it, restart fppd,
# confirm the right -DPIXELTYPE_* flag reached the PRU compiler and the PRU started
# (no BBB48String errors). Restores the original config byte-for-byte at the end.
set -u
CFG=/home/fpp/media/config/co-bbbStrings.json
SCR=/opt/fpp/src/pru/compileWS2811x.sh
LOG=/home/fpp/media/logs/fppd.log
ARGS=/tmp/preset_test_args.log

cp -f "$CFG" "$CFG.preset-test.bak"
[ -e "$SCR.orig" ] || cp "$SCR" "$SCR.orig"
cp "$SCR.orig" "$SCR"
sed -i "2a echo \"ARGS \$@\" >> $ARGS" "$SCR"
: > "$ARGS"; chmod 666 "$ARGS"

setpt() {
  python3 - "$CFG" "$1" <<'PY'
import json,sys
p,val=sys.argv[1],int(sys.argv[2])
d=json.load(open(p))
for o in d.get("channelOutputs",[]):
    if o.get("type")=="BBB48String":
        o["pixelTiming"]=val
json.dump(d,open(p,"w"),indent=4)
PY
}

NAMES=(Normal Slow APA104 WS2811_400 UCS1903_400 TM1803 TM1814 TM1829 WS2805 TM1914 UCS7604 Custom TM1903 UCS2912 UCS1912 TX1812 TM1908 LPD1886 LC8812)
EXP=("" PIXELTYPE_SLOW PIXELTYPE_APA104 PIXELTYPE_WS2811_400 PIXELTYPE_UCS1903_400 PIXELTYPE_TM1803 PIXELTYPE_TM1814 PIXELTYPE_TM1829 PIXELTYPE_WS2805 PIXELTYPE_TM1914 "" PIXELTYPE_CUSTOM PIXELTYPE_CUSTOM PIXELTYPE_CUSTOM PIXELTYPE_CUSTOM PIXELTYPE_CUSTOM PIXELTYPE_CUSTOM PIXELTYPE_CUSTOM PIXELTYPE_CUSTOM)
FAILS=0
for N in 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18; do
  setpt "$N"
  : > "$ARGS"
  BEFORE=$(wc -l < "$LOG")
  systemctl restart fppd
  sleep 16
  PID=$(pgrep -n fppd || echo "-")
  NEW=$(tail -n +$((BEFORE+1)) "$LOG" 2>/dev/null)
  FLAG=$(grep -o 'PIXELTYPE_[A-Z0-9_]*' "$ARGS" | tail -1)
  if [ -n "${EXP[$N]}" ]; then
    [ "$FLAG" = "${EXP[$N]}" ] && F=ok || F="BAD(flag=${FLAG:-none})"
  else
    [ -z "$FLAG" ] && F=ok || F="BAD(unexpected $FLAG)"
  fi
  if echo "$NEW" | grep -qiE "Unable to start PRU|Could not .*BBB48String|Failed to (load|open).*BBB48|segfault"; then R="FAIL (PRU/init error)"
  elif [ "$PID" != "-" ] && echo "$NEW" | grep -q "Determined range needed 0 - 48959"; then R="PASS"
  else R="INCONCLUSIVE (pid=$PID)"; fi
  [ "$R" = PASS ] && [ "$F" = ok ] || FAILS=$((FAILS+1))
  printf "pixelTiming=%-2s %-12s flag=%-6s %s\n" "$N" "${NAMES[$N]}" "$F" "$R"
  echo "$NEW" | grep -iE "error|fail|warn" | grep -v pixelselect | head -3 | sed 's/^/      log: /'
done
echo "--- restoring original config + compiler ---"
cp -f "$CFG.preset-test.bak" "$CFG"
cp "$SCR.orig" "$SCR"
systemctl restart fppd
sleep 14
PID=$(pgrep -n fppd || echo "-")
echo "restored: fppd pid=$PID, pixelTiming=$(python3 -c "import json;print([o.get('pixelTiming') for o in json.load(open('$CFG'))['channelOutputs'] if o.get('type')=='BBB48String'])"), cfg identical: $(cmp -s $CFG $CFG.preset-test.bak && echo yes || echo NO)"
cmp -s "$CFG" "$CFG.preset-test.bak" && rm -f "$CFG.preset-test.bak"   # only delete the safety copy once the restore is proven identical
echo "FAILS=$FAILS"
echo "== LIVE PRESET TEST FINISHED =="
