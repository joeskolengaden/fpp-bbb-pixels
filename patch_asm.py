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
// TM1814 (RGBW ~800kHz); inverted waveform handled by GPIO swap below.
// T0_TIME 310: NeoPixelBus' 360 ns minus the ~50 ns PRU overhead every other preset
// here assumes (350 put T0H ~40 ns high, within 10 ns of the chip's 410 ns maximum).
#define T0_TIME   310
#define T1_TIME   700
#define LOW_TIME  1150
#elif defined(PIXELTYPE_TM1829)
// TM1829 (RGB, inverted; NeoPixelBus NeoEsp32RmtMethod.h ~250/750/1250)
#define T0_TIME   250
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
#define T0_TIME   310
#define T1_TIME   700
#define LOW_TIME  1150
#elif defined(PIXELTYPE_SLOW)
#define T0_TIME   300
#define T1_TIME   800
#define LOW_TIME  1225
#else"""

if "PIXELTYPE_APA104" in s:
    # upgrade: earlier versions used T0_TIME 350 for TM1814/TM1914 (see CROSSREF_LIBRARIES.md)
    up = 0
    for flag in ("TM1814", "TM1914"):
        pat = re.compile(r"(#elif defined\(PIXELTYPE_%s\)(?:(?!#elif|#else).)*?#define T0_TIME\s+)350" % flag, re.S)
        s, k = pat.subn(r"\g<1>310", s); up += k
    print("  asm timings: already patched" + (" (TM1814/TM1914 T0_TIME upgraded to 310)" if up else ""))
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

open(A, "w").write(s)

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
open(A, "w").write(s)
print("  asm: done")
