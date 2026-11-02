#!/bin/bash
# Live SPIPixels load test: for each clocked-chip protocol write co-other.json, restart fppd,
# confirm the plugin loaded the output, opened the spidev and fppd stayed up. Restores afterwards.
set -u
CFG=/home/fpp/media/config/co-other.json
LOG=/home/fpp/media/logs/fppd.log
HAD=0; [ -e "$CFG" ] && { HAD=1; cp -f "$CFG" "$CFG.spitest.bak"; }
declare -A ORD=([apa102]=BGR [sk9822]=BGR [hd107s]=BGR [apa102hd]=BGR [sk9822hd]=BGR [hd107shd]=BGR [hd108]=RGB [ns108]=RGB [sk9826]=GRB [sk9826mini]=GRB [sk9826ec20]=GRB [tlc59711]=BGR [tlc5971]=BGR [apa107]=BGR [lc8822]=BGR [lc8823]=BGR [ws2801]=RGB [ws2803]=RGB [lpd8806]=GRB [lpd8803]=GRB [lpd6803]=RGB [d705]=RGB [apa102c]=BGR [p9813]=BGR [sm16716]=RGB [sm16726]=RGB)
FAILS=0
for P in apa102 sk9822 hd107s apa102hd sk9822hd hd107shd hd108 ns108 sk9826 sk9826mini sk9826ec20 tlc59711 tlc5971 apa107 lc8822 lc8823 ws2801 ws2803 lpd8806 lpd8803 lpd6803 d705 apa102c p9813 sm16716 sm16726; do
cat > "$CFG" <<JSON
{"channelOutputs":[{"type":"SPIPixels","enabled":1,"startChannel":1,"channelCount":18,
 "outputs":[{"device":"spidev0.0","protocol":"$P","spiSpeed":200000,"portNumber":0,
  "virtualStrings":[{"description":"t","startChannel":0,"pixelCount":6,"groupCount":0,"reverse":0,
   "colorOrder":"${ORD[$P]}","nullNodes":0,"endNulls":0,"zigZag":0,"brightness":100,"gamma":"1.0"}]}]}]}
JSON
  BEFORE=$(wc -l < "$LOG")
  systemctl restart fppd; sleep 14
  PID=$(pgrep -n fppd || echo -)
  NEW=$(tail -n +$((BEFORE+1)) "$LOG")
  SPI=$(echo "$NEW" | grep -i "spipixels" | head -2 | sed 's/^.*\] //' | tr '\n' '|')
  if echo "$NEW" | grep -qiE "spipixels.*(fail|error|cannot|unable|unknown)"; then R=FAIL
  elif [ "$PID" != - ] && echo "$NEW" | grep -qi "spipixels"; then R=PASS
  else R="INCONCLUSIVE"; fi
  [ "$R" = PASS ] || FAILS=$((FAILS+1))
  printf "%-8s %-13s %s\n" "$P" "$R" "$SPI"
done
if [ $HAD = 1 ]; then cp -f "$CFG.spitest.bak" "$CFG"; else rm -f "$CFG"; fi
systemctl restart fppd; sleep 14
rm -f "$CFG.spitest.bak"
echo "restored: fppd pid=$(pgrep -n fppd || echo -), co-other.json present=$([ -e $CFG ] && echo yes || echo no)"
echo "FAILS=$FAILS"; echo "== SPI LOAD TEST FINISHED =="
