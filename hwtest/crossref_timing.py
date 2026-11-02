#!/usr/bin/env python3
"""
crossref_timing.py - single-wire timing cross-reference: this package's PRU presets vs FastLED,
NeoPixelBus and Adafruit NeoPixel.

All library numbers are (T0H, T1H, period) in ns, normalised from each library's own convention:
  FastLED      ClocklessController<T1,T2,T3>  ->  T0H=T1, T1H=T1+T2, period=T1+T2+T3
               (src/chipsets.h in ~/Documents/Arduino/libraries/FastLED, Mar 2025 snapshot)
  NeoPixelBus  NeoEsp32RmtSpeed*  (T0H,T0L,T1H,T1L) -> T0H, T1H, period=T0H+T0L
               (Makuna/NeoPixelBus master, src/internal/methods/NeoEsp32RmtMethod.h)
  Adafruit     800 kHz / 400 kHz cycle-count constants (Adafruit_NeoPixel.cpp ARM/nRF paths)
Our column is the PRU define set read from the patched FalconWS281x.asm; "wire" = define + PRU
overhead (model: +OVERHEAD ns on every edge, the fixed offset the asm header comment describes).
Run:  python3 crossref_timing.py [overhead_ns]
"""
import sys

OVERHEAD = int(sys.argv[1]) if len(sys.argv) > 1 else 50

# preset, chip, ours(T0,T1,LOW defines from patch_asm.py / stock), inverted, {lib: (T0H,T1H,period)}
ROWS = [
    (0, "WS2812/WS2811-800 (Normal)", (200, 675, 1150), False,
        {"FastLED": (250, 875, 1250), "NeoPixelBus": (400, 800, 1250), "Adafruit": (250, 800, 1250)}),
    (1, "Slow",                       (300, 800, 1225), False,
        {"NeoPixelBus": (400, 800, 1250)}),
    (2, "APA104/PL9823/SK6822",       (300, 1300, 1610), False,
        {"FastLED PL9823": (350, 1360, 1710), "FastLED SK6822": (375, 1375, 1750), "NeoPixelBus Apa106": (350, 1350, 1700)}),
    (3, "WS2811 400 kHz",             (450, 1150, 2400), False,
        {"FastLED": (800, 1600, 2500), "NeoPixelBus": (800, 1600, 2500), "Adafruit": (500, 1200, 2500)}),
    (4, "UCS1903 400 kHz",            (450, 1900, 2400), False,
        {"FastLED": (500, 2000, 2500)}),
    (5, "TM1803",                     (650, 1300, 1950), False,
        {"FastLED": (700, 1800, 2500)}),
    (6, "TM1814 (inverted)",          (350, 700, 1150), True,
        {"NeoPixelBus": (360, 720, 1250)}),
    (7, "TM1829 (inverted)",          (250, 750, 1150), True,
        {"FastLED": (340, 680, 1230), "NeoPixelBus": (300, 800, 1200)}),
    (8, "WS2805",                     (250, 740, 990), False,
        {"NeoPixelBus": (300, 790, 1090)}),
    (9, "TM1914 (inverted)",          (350, 700, 1150), True,
        {"NeoPixelBus": (360, 720, 1250)}),
]

out = []
out.append("| # | chip | ours: define T0/T1/period | ours on wire (+%d) | library | lib T0H/T1H/period | delta (ours - lib) |" % OVERHEAD)
out.append("|---|---|---|---|---|---|---|")
worst = {}
for n, chip, (t0, t1, lo), inv, libs in ROWS:
    w = (t0 + OVERHEAD, t1 + OVERHEAD, lo + OVERHEAD)
    first = True
    for lib, v in libs.items():
        d = tuple(a - b for a, b in zip(w, v))
        out.append("| %s | %s | %s | %s | %s | %s | %s |" % (
            n if first else "", chip if first else "", "%d/%d/%d" % (t0, t1, lo) if first else "",
            "%d/%d/%d" % w if first else "", lib, "%d/%d/%d" % v, "%+d/%+d/%+d" % d))
        first = False
        worst[(n, lib)] = max(abs(x) for x in d[:2])
print("\n".join(out))
print("\nPresets whose T0H or T1H differs from a library by more than 60 ns at +%d ns overhead:" % OVERHEAD)
for (n, lib), v in sorted(worst.items()):
    if v > 60:
        print("  preset %d vs %s: max |delta| = %d ns" % (n, lib, v))
