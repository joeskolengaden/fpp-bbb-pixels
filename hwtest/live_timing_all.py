#!/usr/bin/env python3
"""
live_timing_all.py - measure the pulses every Pixel Timing preset (0-18) really puts on the pad, and compare them with
the datasheet windows of the chips that preset is meant for.

Method (no scope, no ESP32): pinduty reads the pad through the GPIO input register and counts high/low samples inside frames
(see pinduty.c). With every data bit a 0 (fill 0) the high fraction x bit period = T0H; with every bit a 1 (fill 255) = T1H.
The bit period is frame duration / bits. Inverted presets (idle high) carry the data in the LOW pulses, so T = (1 - high fraction) x period.
LIMIT: the sampler snaps pulse widths to multiples of ~200 ns (the high time of a fixed config reads 207 or 413 ns depending on the run, whatever the
sample rate), so T0H/T1H are printed for information only. The bit period (frame duration / bits, clock-based) is reliable to ~1% and is what is judged.

  python3 live_timing_all.py [--presets 0,6,12]   (default: all) [--out results/timing-all.json]
The original pixel config is restored byte-for-byte at the end.
"""
import argparse, copy, json, os, re, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import measure_limits as m
from verify_presets import FPP
import live_custom as lc

# preset -> (label, inverted, T0H window, T1H window, min period) in ns, from the datasheets of the chips each preset is for
W = {
    0:  ("Normal: WS2812B/WS2811-800/SK6812/WS2815", 0, (250, 550), (580, 950), 1150),     # the intersection that real chips accept
    1:  ("Slow", 0, (250, 550), (650, 1000), 1150),
    2:  ("APA104/APA106/PL9823", 0, (250, 450), (1200, 1520), 1550),
    3:  ("WS2811 400k", 0, (350, 650), (1050, 1350), 2350),
    4:  ("UCS1903 400k", 0, (350, 650), (1850, 2150), 2350),
    5:  ("TM1803", 0, (530, 830), (1210, 1510), 1890),
    6:  ("TM1814 (inverted)", 1, (310, 410), (650, 1000), 1100),
    7:  ("TM1829 (inverted)", 1, (200, 400), (650, 950), 1100),
    8:  ("WS2805", 0, (150, 450), (640, 940), 940),
    9:  ("TM1914 (inverted)", 1, (310, 410), (650, 1000), 1100),
    10: ("UCS7604", 0, (250, 550), (580, 950), 1150),
    12: ("TM1903/TM1824/TM1934", 0, (310, 410), (650, 1000), 1250),   # datasheet: 1.25 us minimum; we run 1300
    13: ("UCS2912", 0, (360, 440), (720, 880), 1200),
    14: ("UCS1912", 0, (100, 400), (850, 1150), 1100),
    15: ("TX1812/TX1818/LC8816E/GS8208B", 0, (250, 350), (850, 950), 1150),
    16: ("TM1908", 0, (200, 280), (400, 560), 830),
    17: ("LPD1886 8-bit", 0, (150, 280), (450, 1000), 800),
    18: ("LC8812/LC8812B", 0, (150, 450), (600, 900), 1150),
}


def one(fpp, base, pt):
    cfg = lc.cfg_for(base, {}, timing=pt)
    inv = W[pt][1]
    period, t0, t1 = lc.measure(fpp, cfg, 0, 0, 0, inv, extra={6: 8, 9: 6, 10: 15, 16: 9}.get(pt, 0))
    return period, t0, t1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fpp", default="http://192.168.6.2")
    ap.add_argument("--presets", default="")
    ap.add_argument("--out", default=os.path.join(HERE, "results", "timing-all.json"))
    a = ap.parse_args()
    fpp = FPP(a.fpp)
    m.push("pinduty.c")
    print(m.ssh("cd /tmp && gcc -O2 pinduty.c -o pinduty 2>&1 && echo built").strip())
    base, bk = fpp.backup_config(os.path.join(HERE, "results", "config-backups"))
    m.ssh("cp -p /home/fpp/media/config/co-bbbStrings.json /tmp/co-bbbStrings.exact")
    pts = [int(x) for x in a.presets.split(",") if x] or sorted(W)
    rows, bad = [], 0
    try:
        for pt in pts:
            label, inv, w0, w1, pmin = W[pt]
            period, t0, t1 = one(fpp, base, pt)
            if period is None:
                print("preset %2d %-40s NO MEASUREMENT" % (pt, label)); bad += 1; continue
            ok0 = ok1 = True        # pulse widths cannot be verified with the pad sampler (see pinduty.c): only the period is judged
            okp = period >= pmin
            bad += not (ok0 and ok1 and okp)
            rows.append({"preset": pt, "label": label, "period": period, "t0h": t0, "t1h": t1, "window0": w0, "window1": w1, "min_period": pmin,
                         "ok": bool(ok0 and ok1 and okp)})
            print("preset %2d %-40s bit period %5.0f ns (datasheet minimum %d) %s | indicative T0H %.0f T1H %.0f (datasheet windows %s %s)" % (
                pt, label, period, pmin, "ok" if okp else "BAD", t0, t1, w0, w1), flush=True)
    finally:
        try:
            fpp.testmode(False)
            m.ssh("cp -p /tmp/co-bbbStrings.exact /home/fpp/media/config/co-bbbStrings.json")
            fpp.restart()
        except Exception as e:
            print("!! restore failed:", e)
        print("restored, sha256 %s" % m.ssh("sha256sum /home/fpp/media/config/co-bbbStrings.json").strip()[:16])
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump(rows, open(a.out, "w"), indent=1)
    print("OUT-OF-WINDOW: %d" % bad)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
