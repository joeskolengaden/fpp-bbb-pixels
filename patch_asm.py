#!/usr/bin/env python3
# [fpp-bbb-pixels] Patch the BBB PRU driver FalconWS281x.asm:
#   - single-wire timing presets  2=APA104 3=WS2811-400 4=UCS1903-400 5=TM1803
#   - 6=TM1814 (RGBW, inverted)   7=TM1829 (RGB, inverted)   8=WS2805 (RGBWWCW)
#   - 9=TM1914 (RGB, inverted; same wire timing as TM1814, different preamble)
#   - 10=UCS7604: no dedicated timing block -- WS2812x-equivalent, falls
#     through to the "#else" default (Normal) like preset 0
#   - inverted waveform (GPIO set/clr swap) applies to TM1814/TM1829/TM1914
# Idempotent. Anchors match FPP 5.x. Runtime-compiled by fppd (no rebuild needed
# for the asm itself; BBB48String.cpp maps pixelTiming -> the -D flags).
import re, sys

def _atomic_write(path, data):
    """write to a temp file, then rename over the target: a crash (this board has random ones) can never leave a half-written FPP file"""
    import os as _os
    tmp = path + ".fbp-tmp"
    try:
        st = _os.stat(path)
    except OSError:
        st = None
    with open(tmp, "w") as f:
        f.write(data); f.flush(); _os.fsync(f.fileno())
    if st is not None:
        _os.chmod(tmp, st.st_mode & 0o7777)
        try:
            _os.chown(tmp, st.st_uid, st.st_gid)
        except OSError:
            pass
    _os.replace(tmp, path)

A = sys.argv[1] if len(sys.argv) > 1 else "/opt/fpp/src/pru/FalconWS281x.asm"
s = open(A).read()

# 1) timing #if chain (presets 2-5 + TM1814 + preserve Slow/default)
old = ("#ifdef PIXELTYPE_SLOW\n"
       "#define T0_TIME   300\n"
       "#define T1_TIME   800\n"
       "#define LOW_TIME  1225\n"
       "#else")
new = """#if defined(PIXELTYPE_APA104)
// APA104 / APA106 / PL9823 / SK6822  (T0H~350 T1H~1360 period~1710)
#define SLOW_WAITNS
#define T0_TIME   300
#define T1_TIME   1300
#define LOW_TIME  1610
#elif defined(PIXELTYPE_WS2811_400)
// WS2811 400Kbps  (T0H~500 T1H~1200 period~2500)
#define SLOW_WAITNS
#define T0_TIME   450
#define T1_TIME   1150
#define LOW_TIME  2400
#elif defined(PIXELTYPE_UCS1903_400)
// UCS1903 400Kbps  (T0H~500 T1H~2000 period~2500)
#define SLOW_WAITNS
#define T0_TIME   450
#define T1_TIME   1900
#define LOW_TIME  2400
#elif defined(PIXELTYPE_TM1803)
// TM1803 (datasheet Titan V1.6: T0H 680, T1H 1360, period 2040, reset 24us)
#define SLOW_WAITNS
#define T0_TIME   650
#define T1_TIME   1300
#define LOW_TIME  1950
#elif defined(PIXELTYPE_TM1814)
// TM1814 (RGBW, inverted). Datasheet: 0-bit low 310-410 ns (typical 360),
// 1-bit low 650-1000 (typical 720), period 1250. Pad on a BeagleBone Green,
// 200 pixels, all-zero and all-one frames: idle high, period ~1246 ns,
// 0-bit low 378 ns, 1-bit low 724 ns. 310 (datasheet minus an assumed 50 ns)
// sat on the bottom of that window; 330 is what measured inside it.
#define T0_TIME   330
#define T1_TIME   700
#define LOW_TIME  1150
#elif defined(PIXELTYPE_TM1829)
// TM1829 (RGB, inverted). NeoPixelBus 300/800/1200. On this PRU, with
// LOW_TIME 1150, a T0 define under ~300 ns has already expired when the
// wait runs, so the 0-bit collapses to the set-to-clear gap (~220 ns).
// Pad, 120 pixels, P8-30: T0_TIME 310 measured a 0-bit low of 314 ns and
// T1_TIME 750 a 1-bit low of about 806 ns. Period ~1234 ns. Idle high.
#define T0_TIME   310
#define T1_TIME   750
#define LOW_TIME  1150
#elif defined(PIXELTYPE_WS2805)
// WS2805 (RGB+WW+CW 5ch, ~800kHz; NeoPixelBus nominal 300/790/1090). Defines
// are ~50ns below nominal for PRU clock-reset overhead, same convention as
// every other preset here (e.g. APA104 350/1360/1710 -> 300/1300/1610).
#define T0_TIME   250
#define T1_TIME   740
#define LOW_TIME  990
#elif defined(PIXELTYPE_TM1914)
// TM1914 (RGB, inverted; identical wire timing to TM1814 -- only the
// PixelString-level preamble differs, see preambleProfile="tm1914")
#define T0_TIME   330
#define T1_TIME   700
#define LOW_TIME  1150
#elif defined(PIXELTYPE_SLOW)
#define T0_TIME   300
#define T1_TIME   800
#define LOW_TIME  1225
#else"""

if "PIXELTYPE_APA104" in s:
    # 350 and 310 were both "datasheet minus an assumed 50 ns". The pad measured
    # 330 ns inside the TM1814/TM1914 window (see the comments on those defines).
    # TM1829 T0 is 310: 250 and 280 both collapsed to ~220 ns at LOW_TIME 1150,
    # and 310 measured 314 ns. T1 stays 750 (board trials at 740 are put back).
    want = [("TM1814", "T0_TIME", 330), ("TM1914", "T0_TIME", 330),
            ("TM1829", "T0_TIME", 310), ("TM1829", "T1_TIME", 750)]
    orig = s
    for flag, name, value in want:
        pat = re.compile(r"(#elif defined\(PIXELTYPE_%s\)(?:(?!#elif|#else).)*?#define %s\s+)\d+" % (flag, name), re.S)
        s = pat.sub(r"\g<1>%d" % value, s, count=1)
    # 1.0.1 and the on-board 270/740 trial both left a comment that now lies.
    tm1829_note = ("// TM1829 (RGB, inverted). NeoPixelBus 300/800/1200. On this PRU, with\n"
                   "// LOW_TIME 1150, a T0 define under ~300 ns has already expired when the\n"
                   "// wait runs, so the 0-bit collapses to the set-to-clear gap (~220 ns).\n"
                   "// Pad, 120 pixels, P8-30: T0_TIME 310 measured a 0-bit low of 314 ns and\n"
                   "// T1_TIME 750 a 1-bit low of about 806 ns. Period ~1234 ns. Idle high.\n")
    for stale in (
        "// TM1829 (RGB, inverted). NeoPixelBus 300/800/1200, defines 50 ns under that.\n"
        "// A trial at 270/740 was measured on the same pad: the 1-bit low was ~812 ns,\n"
        "// but the 0-bit low was ~219 ns, still short of 300. Left at 250/750/1150.\n",
        "// TM1829 (RGB, inverted). NeoPixelBus 300/800/1200. Measured edge overhead\n"
        "// puts the defines at 270/740 (750 measured ~810 ns on this pad).\n",
    ):
        if stale in s:
            s = s.replace(stale, tm1829_note, 1)
    print("  asm timings: already patched" + (" (inverted presets retimed)" if s != orig else ""))
elif old in s:
    s = s.replace(old, new); print("  asm timings: patched (presets 2-5 + TM1814)")
else:
    sys.exit("  asm ERROR: timing block anchor not found")

# 2) inverted-idle-high waveform (TM1814/TM1829/TM1914): swap GPIO set/clr
#    data regs after PRUDefs include
inc = '#include "FalconPRUDefs.hp"'
if "PIXELTYPE_TM1814" in s and "#undef GPIO_SETDATAOUT" not in s:
    swap = inc + ("\n#if defined(PIXELTYPE_TM1814) || defined(PIXELTYPE_TM1829) || defined(PIXELTYPE_TM1914)\n"
                  "// These idle HIGH (inverted vs WS281x). Swapping the GPIO set/clear\n"
                  "// data registers inverts every drive op -> the whole waveform inverts.\n"
                  "#undef GPIO_SETDATAOUT\n#undef GPIO_CLRDATAOUT\n"
                  "#define GPIO_SETDATAOUT (0x190 - 0x100)\n"
                  "#define GPIO_CLRDATAOUT (0x194 - 0x100)\n#endif")
    assert s.count(inc) == 1, "  asm ERROR: PRUDefs include anchor not unique"
    s = s.replace(inc, swap); print("  asm invert: TM1814/TM1829/TM1914 GPIO swap added")
else:
    print("  asm invert: already present")

_atomic_write(A, s)

# 3) user-defined "Custom" timing (pixelTiming 11): BBB48String passes -DPIXELTYPE_CUSTOM -DCUSTOM_T0/T1/LOW (ns, already
#    compensated for the PRU overhead) and -DSLOW_WAITNS when a wait exceeds the 8-bit immediate (1275 ns); -DCUSTOM_INVERT
#    makes the waveform idle-high. Lets any single-wire chip with a datasheet be driven without a dedicated preset.
s = open(A).read()
if "PIXELTYPE_CUSTOM" not in s:
    anchor = "#elif defined(PIXELTYPE_SLOW)\n#define T0_TIME   300"
    assert s.count(anchor) == 1, "  asm ERROR: custom-timing anchor not found"
    s = s.replace(anchor, "#elif defined(PIXELTYPE_CUSTOM)\n"
                  "// user-defined timing, see BBB48String.cpp (pixelTiming 11)\n"
                  "#define T0_TIME   CUSTOM_T0\n#define T1_TIME   CUSTOM_T1\n#define LOW_TIME  CUSTOM_LOW\n" + anchor)
    print("  asm custom timing: added")
else:
    print("  asm custom timing: already present")
old_inv = "#if defined(PIXELTYPE_TM1814) || defined(PIXELTYPE_TM1829) || defined(PIXELTYPE_TM1914)\n"
if "CUSTOM_INVERT" not in s and old_inv in s:
    s = s.replace(old_inv, "#if defined(PIXELTYPE_TM1814) || defined(PIXELTYPE_TM1829) || defined(PIXELTYPE_TM1914) || defined(CUSTOM_INVERT)\n")
    print("  asm custom invert: added")
_atomic_write(A, s)
print("  asm: done")
