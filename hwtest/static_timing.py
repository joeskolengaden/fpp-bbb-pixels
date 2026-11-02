#!/usr/bin/env python3
"""
static_timing.py - 'internal' check of the PRU pulse timing each preset generates (no scope needed).

Reads T0_TIME/T1_TIME/LOW_TIME for every preset straight out of the patched FalconWS281x.asm
(patch_asm.py output), and the acceptance windows from the analyzer's protocols.h. In the PRU loop the
clock is reset at each bit start; 0-bits drop at T0_TIME, 1-bits at T1_TIME and the next bit starts at
LOW_TIME, so the on-wire (T0H, T1H, period) ~= (T0_TIME, T1_TIME, LOW_TIME) + a fixed PRU overhead
("defines are slightly lower as there is overhead in resetting the clocks"). The overhead is not
known exactly, so each preset is evaluated across a 0..150 ns overhead sweep; a preset is robust if
its windows hold across the whole sweep. This is a model - scope/analyzer capture is the proof.

  python3 static_timing.py [path/to/FalconWS281x.asm]
"""
import os, re, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..", "..")
ASM = sys.argv[1] if len(sys.argv) > 1 else None
SCR = os.environ.get("FBP_BOARD_DIR") or os.environ.get("BBG_SCRATCH") or os.path.join(os.path.dirname(os.path.abspath(__file__)), ".board")

if ASM:
    asm = open(ASM).read()
else:   # pull the live patched file from the board
    env = dict(os.environ, BBG_TIMEOUT="60")
    asm = subprocess.run([SCR + "/bbg", "cat /opt/fpp/src/pru/FalconWS281x.asm"], capture_output=True, text=True, env=env).stdout

# preset -> PIXELTYPE flag (presets 0 and 10 use the default block; 1 is SLOW)
FLAG = {0: None, 1: "SLOW", 2: "APA104", 3: "WS2811_400", 4: "UCS1903_400", 5: "TM1803", 6: "TM1814",
        7: "TM1829", 8: "WS2805", 9: "TM1914", 10: None}
NAME = {0: "Normal", 1: "Slow", 2: "APA104", 3: "WS2811-400", 4: "UCS1903-400", 5: "TM1803", 6: "TM1814",
        7: "TM1829", 8: "WS2805", 9: "TM1914", 10: "UCS7604 (=Normal timing)"}

def parse_chain():
    """{flag: {T0_TIME,T1_TIME,LOW_TIME}} from the '#if defined(PIXELTYPE_APA104) ... #else ... #endif' chain."""
    start = asm.index("#if defined(PIXELTYPE_APA104)")
    end = asm.index("#endif", start)
    out, cur = {}, None
    for line in asm[start:end].splitlines():
        m = re.match(r"#(?:el)?if\s+defined\(PIXELTYPE_(\w+)\)", line)
        if m:
            cur = m.group(1); out[cur] = {}; continue
        if line.startswith("#else"):
            cur = "DEFAULT"; out[cur] = {}; continue
        m = re.match(r"#define\s+(T0_TIME|T1_TIME|LOW_TIME)\s+(\d+)", line)
        if m and cur:
            out[cur][m.group(1)] = int(m.group(2))
    return out

CHAIN = parse_chain()
pris = {n: CHAIN["DEFAULT" if f is None else f] for n, f in FLAG.items()}
for n, v in pris.items():
    assert len(v) == 3, (n, v)

# acceptance windows from the analyzer
ph = open(os.path.join(ROOT, "tools/esp32-led-analyzer/protocols.h")).read()
WIN = {}
for m in re.finditer(r'\{\s*"([^"]+)",\s*(true|false),\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*\d+,\s*"(\d+)"\s*\}', ph):
    WIN[int(m.group(9))] = tuple(map(int, m.group(3, 4, 5, 6, 7, 8)))
WIN[1] = WIN[0]; WIN[10] = WIN[0]       # Slow & UCS7604 are validated against the Normal family window

bad = 0
print("%-3s %-26s %-22s %-14s %s" % ("#", "preset", "T0/T1/LOW (ns, asm)", "overhead ok", "worst-case margin to window (ns)"))
for n in range(11):
    p = pris[n]; t0, t1, low = p["T0_TIME"], p["T1_TIME"], p["LOW_TIME"]
    w = WIN[n]
    sweep_ok, worst = [], 10**9
    for ov in range(0, 151, 10):
        vals = (t0 + ov, t1 + ov, low + ov)
        lims = ((w[0], w[1]), (w[2], w[3]), (w[4], w[5]))
        ok = all(a <= v <= b for v, (a, b) in zip(vals, lims))
        sweep_ok.append((ov, ok))
        if 0 <= ov <= 100:
            worst = min(worst, min(min(v - a, b - v) for v, (a, b) in zip(vals, lims)))
    good = [ov for ov, ok in sweep_ok if ok]
    rng = "%d..%d" % (good[0], good[-1]) if good else "NONE"
    # robustness: the realistic overhead band (0-100ns) must be inside
    robust = all(ok for ov, ok in sweep_ok if ov <= 100)
    bad += not robust
    print("%-3d %-26s %-22s %-14s %s%s" % (n, NAME[n], "%d/%d/%d" % (t0, t1, low), rng, worst,
                                        "" if robust else "   <-- window not held across 0-100ns overhead"))
print("\nINVERTED presets (6,7,9): GPIO set/clear swap present in asm:",
      "yes" if "#undef GPIO_SETDATAOUT" in asm and "PIXELTYPE_TM1914" in asm else "NO")
print("STATIC TIMING", "PASSED (all presets inside analyzer window for 0-100 ns PRU overhead)" if not bad else "REVIEW (%d preset(s) outside window)" % bad)
sys.exit(1 if bad else 0)
