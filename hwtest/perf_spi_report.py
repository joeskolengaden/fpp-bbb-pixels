#!/usr/bin/env python3
"""
perf_spi_report.py - markdown tables from perf_spi.py output: per clocked chip, 1/2/4 outputs x 1,500 px at 20/30/40 fps.

  python3 perf_spi_report.py results/perf-spi.jsonl > results/perf-spi.md
"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from max_pixels import spi_wire_size

FPS = {20: 50, 30: 33, 40: 25}
OUTS = [1, 2, 4]
path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "results/perf-spi.jsonl")
recs = [json.loads(l) for l in open(path)]
by = {(r["chip"], r["outputs"], r["fps"]): r for r in recs}
chips = []
for r in recs:
    if r["chip"] not in [c for c, _ in chips]:
        chips.append((r["chip"], r["hz"]))


def ok(m, fps):
    if not m or not m.get("achieved_fps"):
        return None
    target = 1000.0 / FPS[fps]
    late_pct = 100.0 * m.get("late_lines", 0) / max(target * m["window_s"], 1)
    return m["achieved_fps"] >= 0.97 * target and late_pct <= 3.0 and not m.get("errors")


print("## SPI chips at 1,500 px per output (BeagleBone Green, 4 spidev chip-selects on 2 buses)\n")
print("Each cell: ✅/❌ cadence held · SPI send ms per frame (all outputs, they are sent one after another) · fppd CPU · achieved fps · late frames in 6 s.\n")
print("| chip | clock | wire bytes @1,500 px | outputs | " + " | ".join("%d fps (%d ms)" % (f, FPS[f]) for f in FPS) + " |")
print("|---|---|---|---|" + "---|" * len(FPS))
for chip, hz in chips:
    nb = spi_wire_size("apa102" if chip in ("apa102hd", "sk9822hd", "hd107s", "apa107") else chip, 1500)
    for n in OUTS:
        cells = []
        for f in FPS:
            r = by.get((chip, n, f))
            m = r["metrics"] if r else None
            if not m:
                cells.append("—"); continue
            v = ok(m, f)
            cells.append("%s %s ms · %s%% · %s fps · %s late" % ("✅" if v else "❌", m.get("send_ms"), m["fppd_cpu_pct"], m.get("achieved_fps"), m.get("late_lines")))
        print("| %s | %.0f MHz | %d | %d | %s |" % (chip if n == OUTS[0] else "", hz / 1e6, nb, n, " | ".join(cells)))
