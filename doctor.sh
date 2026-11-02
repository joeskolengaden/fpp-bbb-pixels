#!/bin/bash
# [fpp-bbb-pixels] One-screen health check. Read-only: changes nothing.   Run on the device:  bash doctor.sh
# Reports: FPP/fppd state, whether every patch is applied and built, the frame budget of the live pixel config
# (the longest port vs. the frame rates FPP asks for), clock sanity, plugin load failures, disk/memory, installer leftovers.
CFG=/home/fpp/media/config/co-bbbStrings.json
SRC=/opt/fpp/src
LOG=/home/fpp/media/logs/fppd.log
ok()   { printf "  \033[32mOK\033[0m    %s\n" "$*"; }
warn() { printf "  \033[33mWARN\033[0m  %s\n" "$*"; WARNS=$((WARNS+1)); }
bad()  { printf "  \033[31mFAIL\033[0m  %s\n" "$*"; FAILS=$((FAILS+1)); }
WARNS=0; FAILS=0

echo "== FPP =="
[ -f /home/fpp/media/config/fbp-version ] && echo "  installed: $(grep -E "^fbp_version" /home/fpp/media/config/fbp-version | cut -d= -f2) ($(grep -E "^installed" /home/fpp/media/config/fbp-version | cut -d= -f2))" || echo "  (no fbp-version stamp: installed before versioning, or not installed)"
V=$(curl -s -m5 localhost/api/fppd/version | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d["version"])' 2>/dev/null)
if [ -n "$V" ]; then ok "fppd answering, FPP $V"; else bad "fppd is not answering on localhost (is it running? sudo systemctl status fppd)"; fi
case "$V" in 5.4*|5.5*|5.6*) ;; "") ;; *) warn "FPP $V: the patcher anchors were written for 5.4.x - run install.sh --check first";; esac

echo "== patches (sources) =="
A=$SRC/pru/FalconWS281x.asm; C=$SRC/channeloutput/BBB48String.cpp; P=$SRC/channeloutput/PixelString.cpp; U=/opt/fpp/www/co-pixelStrings.php
grep -q "PIXELTYPE_TM1814" "$A" 2>/dev/null && ok "PRU timing presets 2-10 + inverted waveform" || bad "PRU asm is not patched (run install.sh)"
grep -q "T0_TIME   310" "$A" 2>/dev/null && ok "TM1814/TM1914 T0_TIME 310" || warn "TM1814/TM1914 still on the older T0_TIME 350 (re-run install.sh to upgrade)"
grep -q "Prefetching gather" "$C" 2>/dev/null && ok "prefetching prepData (1.6x faster frame prep)" || warn "prepData is not the prefetching version (re-run install.sh)"
grep -q "frame budget" "$C" 2>/dev/null && ok "frame-budget log line" || warn "no frame-budget log line (re-run install.sh)"
grep -q "preambleProfile" "$P" 2>/dev/null || grep -q "addDecorationBytes" "$P" 2>/dev/null && ok "PixelString: 5/6-ch, 16-bit, preambles/trailers" || bad "PixelString is not patched"
grep -q "chipCurrent" "$P" 2>/dev/null && ok "chip current (TM1814/UCS7604/SM16825E) and TM1914 mode controls" || warn "chip current / TM1914 mode controls missing (re-run install.sh)"
grep -q "channelRanges'\]\s*??\s*null\|channelRanges'\] ?? null" /opt/fpp/www/api/controllers/system.php 2>/dev/null && ok "PHP notice guard (no log flooding on a USB-only board)" || warn "PHP 'Undefined index' notice flood not patched (re-run install.sh)"
grep -q "PIXELTYPE_CUSTOM" "$A" 2>/dev/null && ok "Custom timing + datasheet presets 11-18 (PRU)" || warn "Custom timing / presets 11-18 missing in the PRU source (re-run install.sh)"
grep -q "fbpCustT0" "$U" 2>/dev/null && ok "UI: Custom timing boxes + presets 11-18" || warn "UI lacks Custom timing / presets 11-18 (re-run install.sh)"
[ -f /home/fpp/media/config/fbp-needs-reapply ] && warn "start-up guard flagged missing patches:$(cat /home/fpp/media/config/fbp-needs-reapply) (an FPP upgrade replaced files? re-run install.sh)"
grep -q "fbpUpdateBudget" "$U" 2>/dev/null && ok "UI: live frame-budget readout" || warn "UI frame-budget readout missing (re-run install.sh)"

echo "== patches (built) =="
for so in libfpp.so libfpp-co-BBB48String.so; do
  if [ -f "$SRC/$so.orig" ] && [ -f "$SRC/$so" ]; then
    cmp -s "$SRC/$so" "$SRC/$so.orig" && bad "$so is byte-identical to stock - patches are not compiled in (re-run install.sh)" || ok "$so differs from stock (patched build)"
    [ "$SRC/$so" -ot "$C" ] && warn "$so is older than BBB48String.cpp - rebuild needed (re-run install.sh)"
  else warn "$so or its .orig backup is missing"; fi
done
[ -f /usr/local/lib/libfpp-co-SPIPixels.so ] || [ -f "$SRC/libfpp-co-SPIPixels.so" ] && ok "SPIPixels plugin library present" || warn "SPIPixels library not installed"
grep -aq "hd108" /usr/local/lib/libfpp-co-SPIPixels.so 2>/dev/null && ok "SPIPixels knows HD108 and the HD brightness modes" || warn "SPIPixels library predates HD108 (re-run install.sh)"
ls /dev/spidev* >/dev/null 2>&1 && ok "SPI devices: $(ls /dev/spidev* | tr '\n' ' ')" || warn "no /dev/spidev* (SPI chips need the SPI overlay enabled)"

echo "== live pixel configuration =="
if [ -f "$CFG" ]; then
python3 - "$CFG" <<'PY'
import json, sys
BIT = [1260, 1331, 1726, 2518, 2518, 2074, 1258, 1256, 1102, 1256, 1260]       # ns per bit incl. ~110 ns PRU overhead (measured)
NAMES = ["Normal", "Slow", "APA104", "WS2811-400", "UCS1903-400", "TM1803", "TM1814", "TM1829", "WS2805", "TM1914", "UCS7604",
         "Custom", "TM1903/TM1824/TM1934", "UCS2912", "UCS1912", "TX1812/LC8816E/GS8208B", "TM1908", "LPD1886-8bit", "LC8812"]
PRE = {6: 8, 9: 6, 10: 15, 16: 9}
RESET = [300, 300, 50, 50, 50, 50, 200, 200, 300, 200, 300] + [300] * 8
def num(d, k, dflt):
    v = d.get(k)
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else dflt
PRESET_TIMING = {12: (360, 720, 1300), 13: (400, 800, 1250), 14: (250, 1000, 1250), 15: (300, 900, 1250), 16: (240, 480, 1250), 17: (200, 600, 1250), 18: (300, 750, 1250)}
def period(co, pt):          # bit period on the wire, mirrors BBB48String.cpp (datasheet period, clamped, minus the 110 ns the PRU adds back)
    if pt <= 10: return BIT[pt]
    t0, t1, per = (num(co, "customT0", 350), num(co, "customT1", 700), num(co, "customPeriod", 1250)) if pt == 11 else PRESET_TIMING[pt]
    t0 = min(max(t0 - 50, 200), 3000); t1 = min(max(t1 - 50, t0 + 50), 3500)
    return min(max(per - 110, t1 + 100), 4000) + 110
def bpp(o):
    o = o or "RGB"; s = o.endswith("16"); n = len(o) - (2 if s else 0); return n * 2 if s else n
d = json.load(open(sys.argv[1]))
if any(str(v.get("description", "")).startswith("hwtest") for co in d.get("channelOutputs", []) for o in co.get("outputs", []) for v in (o.get("virtualStrings") or [])):
    print("  WARN  this looks like a TEST configuration left by hwtest (strings named 'hwtest*') - restore your real layout")
for co in d.get("channelOutputs", []):
    if co.get("type") != "BBB48String": continue
    pt = min(max(int(co.get("pixelTiming", 0)), 0), 18)
    BITP = period(co, pt)
    ports = []
    for o in co.get("outputs", []):
        b = 0; px = 0
        for key in ("virtualStrings", "virtualStringsB", "virtualStringsC", "virtualStringsD"):
            for v in o.get(key, []) or []:
                n = int(v.get("pixelCount", 0)) + int(v.get("nullNodes", 0)) + int(v.get("endNulls", 0))
                if n: b += n * bpp(v.get("colorOrder")); px += int(v.get("pixelCount", 0))
        ports.append((b + PRE.get(pt, 0) if b else 0, px, o.get("portNumber")))
    act = [p for p in ports if p[0]]
    print("  BBB48String %s, Pixel Timing %d (%s), %d active ports, %d pixels total, enabled=%s" % (co.get("subType", ""), pt, NAMES[pt], len(act), sum(p[1] for p in act), co.get("enabled")))
    tf = int(co.get("targetFps", 20)); avail = 1000 // tf - (RESET[pt] + 200) / 1000.0
    over = [(p[2], p[1], p[0] * 8 * BITP / 1e6) for p in act if p[0] * 8 * BITP / 1e6 > avail]
    if over:
        for port, px, ms in over:
            print("  WARN  planned for %d fps (%.1f ms/frame available): port %s has %d pixels = %.1f ms - only %d%% of it will update" % (tf, avail, port, px, ms, 100 * avail / ms))
    elif act:
        print("  OK    planned for %d fps: every port fits (%.1f ms available per frame)" % (tf, avail))
    if act:
        w = max(act); ms = w[0] * 8 * BITP / 1e6; fps = 1000 / (ms + 0.5)
        flag = "OK  " if fps >= 40 else ("OK  " if fps >= 20 else "WARN")
        print("  %s longest port %s: %d px, %d bytes -> %.1f ms on the wire -> sustains up to ~%.0f fps" % (flag, w[2], w[1], w[0], ms, fps))
        if fps < 20: print("        a 20 fps sequence will cut off the end of that port; shorten it or use a slower sequence")
        elif fps < 40: print("        sequences above ~%.0f fps will cut off the end of that port" % fps)
PY
else warn "no $CFG yet"; fi

echo "== output-thread budget (PRU frame preparation + SPI sends, measured by the stress test) =="
python3 - "$CFG" /home/fpp/media/config/co-other.json <<'PY'
import json, os, sys
# Stress-test rule: fppd's output thread does the PRU frame preparation (~0.031 us per byte) and then sends every SPI output one
# after another (SPI time = 1.057 x bytes x 8 / clock + 0.13 ms per KB + 0.39 ms per 4 KB chunk, x1.2 while the PRU is busy).
# Keep the total under 60% of the frame interval: measured 6.7 + 4 x 8.6 ms = 43 ms on a 50 ms frame gave late frames.
SPEED = {"apa102": 8e6, "sk9822": 8e6, "hd107s": 20e6, "apa102hd": 8e6, "sk9822hd": 8e6, "hd107shd": 20e6, "hd108": 20e6, "ns108": 20e6, "sk9826": 10e6,
         "sk9826mini": 10e6, "sk9826ec20": 10e6, "ws2801": 1e6, "ws2803": 1e6, "lpd8806": 2e6, "lpd8803": 2e6, "lpd8809": 2e6, "ucs8812": 2e6,
         "lpd6803": 1e6, "d705": 1e6, "lpd1101": 1e6, "p9813": 1e6, "sm16716": 16e6, "sm16726": 16e6, "apa107": 8e6, "lc8822": 8e6, "lc8823": 8e6,
         "apa101": 8e6, "apa102c": 8e6, "sk9822ec20": 8e6, "sk9822mini": 8e6, "tlc59711": 1e6, "tlc5971": 1e6}
def wire(proto, n):
    if proto in ("ws2801", "ws2803"): return n * 3
    if proto in ("hd108", "ns108", "sk9826", "sk9826mini", "sk9826ec20"): return 16 + n * 8 + n // 2 + 4
    if proto in ("lpd8806", "lpd8803", "lpd8809", "ucs8812"): return n * 3 + max(1, (n + 31) // 32)
    if proto in ("lpd6803", "d705", "lpd1101", "ucs6909", "ucs6912s"): return 4 + n * 2 + max(1, (n + 7) // 8)
    if proto == "p9813": return 4 + n * 4 + 4 * max(1, (n + 63) // 64)
    if proto in ("sm16716", "sm16726"): return (50 + n * 25 + 7) // 8
    if proto in ("tlc59711", "tlc5971"): return ((n + 3) // 4) * 28
    return 4 + n * 4 + max(4, (n + 15) // 16)          # APA102 family
def load(p):
    try: return json.load(open(p))
    except Exception: return {}
pru_bytes = 0
for co in load(sys.argv[1]).get("channelOutputs", []):
    if co.get("type") == "BBB48String" and co.get("enabled", 1):
        for o in co.get("outputs", []):
            for key in ("virtualStrings", "virtualStringsB", "virtualStringsC", "virtualStringsD"):
                for v in o.get(key, []) or []:
                    od = v.get("colorOrder") or "RGB"; sx = od.endswith("16"); k = len(od) - (2 if sx else 0)
                    pru_bytes += (int(v.get("pixelCount", 0)) + int(v.get("nullNodes", 0)) + int(v.get("endNulls", 0))) * (k * 2 if sx else k)
spi, spi_ms = [], 0.0
for co in load(sys.argv[2]).get("channelOutputs", []):
    if co.get("type") == "SPIPixels" and co.get("enabled", 1):
        for o in co.get("outputs", []):
            px = sum(int(v.get("pixelCount", 0)) + int(v.get("nullNodes", 0)) + int(v.get("endNulls", 0)) for v in o.get("virtualStrings", []) or [])
            if not px: continue
            pr = str(o.get("protocol", "apa102")).lower(); hz = float(o.get("spiSpeed") or SPEED.get(pr, 1e6)); nb = wire(pr, px)
            spi_ms += 1.2 * (1.0569 * nb * 8 * 1000.0 / hz + 0.1304 * nb / 1000.0 + 0.3863 * (-(-nb // 4096)))
            spi.append((pr, px))
prep = pru_bytes * 0.031 / 1000.0
tot = prep + spi_ms
if not pru_bytes and not spi:
    print("  (no pixel outputs configured)")
else:
    print("  estimated output-thread time per frame: %.1f ms  (PRU frame preparation %.1f ms for %d bytes + %d SPI output(s) %.1f ms)" % (tot, prep, pru_bytes, len(spi), spi_ms))
    for fps in (20, 30, 40):
        iv = 1000 // fps; pct = 100.0 * tot / iv
        tag = "OK  " if pct <= 60 else ("WARN" if pct <= 100 else "FAIL")
        print("  %s %d fps: %.0f%% of the %d ms frame%s" % (tag, fps, pct, iv, "" if pct <= 60 else "  (rule: stay under 60% so peaks, up to 1.5x the average, still fit; fewer SPI pixels, a faster SPI clock or a lower frame rate)"))
PY
echo "== system =="
Y=$(date +%Y); [ "$Y" -lt 2024 ] && warn "system clock reads $(date '+%F %T'): no RTC / no time sync. Schedules and timestamps are unreliable. Fix: connect it to the network once (NTP), or: sudo date -s 'YYYY-MM-DD HH:MM:SS'" || ok "clock $(date '+%F %T')"
FREE=$(df -Pm / | awk 'NR==2{print $4}'); [ "$FREE" -lt 300 ] && warn "only ${FREE} MB free on /" || ok "${FREE} MB free on /"
read -r _ _ avail _ < <(grep -E '^MemAvailable' /proc/meminfo | tr -s ' ' ' ' | sed 's/MemAvailable: \([0-9]*\) kB/x x \1 x/'); ok "memory available: $((avail/1024)) MB, load $(cut -d' ' -f1-3 /proc/loadavg)"
[ -f /swapfile ] && warn "leftover /swapfile from an installer run (sudo swapoff /swapfile; sudo rm /swapfile)"
[ -f "$CFG.preset-test.bak" ] && warn "leftover $CFG.preset-test.bak from a test run (safe to delete)"
[ -f /home/fpp/media/config/co-other.json.spitest.bak ] && warn "leftover co-other.json.spitest.bak from a test run (safe to delete)"

if python3 -c "import json,sys; d=json.load(open('/home/fpp/media/config/ci-universes.json')); sys.exit(0 if any(u.get('active') for c in d.get('channelInputs',[]) if c.get('enabled',1) for u in c.get('universes',[])) else 1)" 2>/dev/null; then
  RB=$(cat /proc/sys/net/core/rmem_default 2>/dev/null || echo 0)
  [ "$RB" -ge 1048576 ] && ok "streamed input configured; UDP receive buffer $((RB/1024)) KB" || warn "streamed input (sACN/ArtNet) is configured but the UDP receive buffer is only $((RB/1024)) KB: a big stream can overflow it (sudo bash system-fixes.sh --apply)"
fi
FU=$(systemctl --failed --no-legend 2>/dev/null | awk '{print $1}' | tr '\n' ' ')
[ -z "$FU" ] && ok "no failed system services" || warn "failed system services: $FU (see: sudo bash system-fixes.sh --check)"
[ -x /usr/local/sbin/fbp-clock ] && ok "clock persists across reboots (fbp-clock)" || warn "clock is not saved across reboots - this board has no RTC, so it will start in the past after a power cycle (sudo bash system-fixes.sh --apply)"
echo "== recent problems in fppd.log (last 400 lines) =="
if [ -f "$LOG" ]; then
  tail -400 "$LOG" | grep -E "Failed to load plugin shlib" | sed 's/.*shlib: //' | sort -u | while read -r l; do warn "plugin failed to load: $l (rebuild/reinstall that plugin)"; done
  N=$(tail -400 "$LOG" | grep -c "SLOW Output Thread"); [ "$N" -gt 0 ] && warn "$N 'SLOW Output Thread' warnings: frame preparation is taking longer than the frame interval (fewer ports, fewer pixels or a lower frame rate)" || ok "no SLOW Output Thread warnings"
  tail -400 "$LOG" | grep -iE "error|unable to start pru|could not" | grep -v "Failed to load plugin" | tail -3 | cut -c1-200 | while read -r l; do warn "$l"; done
  tail -400 "$LOG" | grep -E "frame budget" | tail -1 | sed 's/.*BBB48String frame budget: /  budget at last start: /' | cut -c1-220
fi

echo
echo "doctor: $FAILS failure(s), $WARNS warning(s)"
exit $((FAILS>0))
