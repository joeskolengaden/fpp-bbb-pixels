#!/usr/bin/env python3
"""
spi_xcheck.py - 'internal' check of SPIPixels signal generation, no scope/ESP32 needed.

Runs the plugin's real framing code (SPIChipFormat.h, built natively) over random pixel data for
pixel counts 1..200 and compares every output byte with the independent Python framers in
verify_spi.py (written from each chip's frame description). Also checks wire sizes and the
default SPI clock per protocol.
"""
import os, random, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from verify_spi import CASES  # noqa: E402

BIN = sys.argv[1] if len(sys.argv) > 1 else "spi_dump"
SPEED = {"apa102": 8000000, "sk9822": 8000000, "hd107s": 20000000, "ws2801": 1000000, "lpd8806": 2000000,
         "lpd6803": 1000000, "p9813": 1000000, "sm16716": 16000000, "sm16726": 16000000,
         "apa102hd": 8000000, "sk9822hd": 8000000, "hd108": 20000000,
         "sk9826": 10000000, "sk9826mini": 10000000, "tlc59711": 1000000, "apa107": 8000000, "lc8822": 8000000, "lc8823": 8000000}
rnd = random.Random(1234)
bad = 0
for key, label, proto, order, framer, block in CASES:
    runs = fails = 0
    first = None
    for n in list(range(1, 70)) + [96, 100, 128, 150, 199, 200]:
        for trial in range(3):
            rgb = [[rnd.randrange(256) for _ in range(3)] for _ in range(n)]
            if trial == 0:
                rgb = [[0, 0, 0]] * n if n % 2 else [[255, 255, 255]] * n      # edge values
            hexin = "".join("%02X" % b for p in rgb for b in p)
            out = subprocess.run([BIN, proto, str(n), hexin], capture_output=True, text=True).stdout.split()
            want = "".join("%02X" % b for b in framer(rgb, n))
            runs += 1
            if len(out) != 2 or out[0] != want or int(out[1]) != SPEED[proto]:
                fails += 1
                first = first or (n, want, out)
    bad += fails > 0
    print("%-5s %-8s %3d vectors%s" % ("PASS" if not fails else "FAIL", key, runs,
                                      "" if not fails else "  first diff n=%d\n   want %s\n   got  %s" % first))
print("\nSPI CROSS-CHECK", "PASSED" if not bad else "FAILED (%d)" % bad)
sys.exit(1 if bad else 0)
