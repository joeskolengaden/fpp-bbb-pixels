#!/usr/bin/env python3
"""
wire_check.py - 'internal' check of single-wire signal generation, no scope/ESP32 needed.

Builds wire_dump on the board against the patched libfpp.so, dumps the exact byte stream the
patched PixelString hands the PRU for every chip case in verify_presets.CASES, and compares it
byte for byte with the documented frame (preamble + pixel data in the chip's wire order +
trailer). Pair with static_timing.py for the PRU pulse widths.

  python3 wire_check.py [--pixels 3]
"""
import argparse
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from verify_presets import CASES, expected_wire  # noqa: E402

SCR = os.environ.get("FBP_BOARD_DIR") or os.environ.get("BBG_SCRATCH") or os.path.join(os.path.dirname(os.path.abspath(__file__)), ".board")
PROFILE = {6: "tm1814", 9: "tm1914", 10: "ucs7604", 16: "tm1908"}


def sh(cmd, timeout=240):
    env = dict(os.environ, BBG_TIMEOUT="60")
    return subprocess.run([os.path.join(SCR, "bbg"), cmd], capture_output=True, text=True, env=env, timeout=timeout).stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pixels", type=int, default=3)
    a = ap.parse_args()
    env = dict(os.environ, BBG_TIMEOUT="60")
    subprocess.run([os.path.join(SCR, "bbgcp"), os.path.join(HERE, "wire_dump.cpp"), "fpp@192.168.6.2:/tmp/wire_dump.cpp"],
                   check=True, env=env)
    build = ("cd /opt/fpp/src && for t in 1 2 3; do CCACHE_DISABLE=1 g++ -O0 -std=gnu++14 -I/opt/fpp/src -I/usr/include/jsoncpp "
             "/tmp/wire_dump.cpp -L/opt/fpp/src -lfpp -ljsoncpp -Wl,--allow-shlib-undefined -Wl,-rpath,/opt/fpp/src -o /tmp/wire_dump 2>&1 "
             "&& break; done; ls -la /tmp/wire_dump")
    print(sh(build, 600).strip().splitlines()[-1])
    runs = []
    for key, label, timing, order, inv, prof, pre, trail, sig in CASES:
        runs.append("echo '%s'; LD_LIBRARY_PATH=/opt/fpp/src LD_PRELOAD=\"$MAG $CURL\" /tmp/wire_dump %s %d %s"
                    % (key, order, a.pixels, PROFILE.get(timing, "")))
    pre_env = ('MAG=$(/sbin/ldconfig -p | grep -o "/usr/lib/libGraphicsMagick++[^ ]*" | head -1); '
               'CURL=$(ls /usr/lib/*/libcurl.so* 2>/dev/null | head -1); ')
    out = sh(pre_env + "; ".join(runs)).splitlines()
    got = {}
    keys = {c[0] for c in CASES}
    for i in range(len(out) - 1):          # the board prints a login banner; only trust "<case>" + hex line
        if out[i].strip() in keys and re.fullmatch(r"([0-9A-F]{2} )+", out[i + 1].rstrip() + " "):
            got[out[i].strip()] = [int(t, 16) for t in out[i + 1].split()]
    bad = 0
    for key, label, timing, order, inv, prof, pre, trail, sig in CASES:
        body, _ = expected_wire(order, a.pixels, pre, trail)
        want = body + trail
        g = got.get(key)
        ok = g == want
        bad += not ok
        print("%-5s %-12s %-8s %2d bytes  %s" % ("PASS" if ok else "FAIL", key, order, len(want),
                                              "" if ok else "\n   want %s\n   got  %s" % (
                                                  " ".join("%02X" % b for b in want),
                                                  " ".join("%02X" % b for b in g) if g else "(no output)")))
    print("\nWIRE CHECK", "PASSED" if not bad else "FAILED (%d)" % bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
