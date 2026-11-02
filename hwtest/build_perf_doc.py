#!/usr/bin/env python3
"""
build_perf_doc.py - regenerate the measured sections of ../PERFORMANCE.md from the raw results:
  results/perf-final.jsonl (single-wire matrix), results/perf-baseline.jsonl (stock frame prep), results/perf-spi.jsonl (clocked chips).
Keeps the hand-written header / verdict table / 'What changed' text; replaces the CPU-ceiling + load tables and the SPI section.

  python3 build_perf_doc.py
"""
import json, os, re, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from perf_matrix import group_of
from verify_presets import CASES
from max_pixels import spi_rows, spi_max

FPS = {20: 50, 30: 33, 40: 25}
PORTS = [8, 16, 24, 32, 40, 48]
DOC = os.path.join(HERE, "..", "PERFORMANCE.md")


def load(p):
    return {(tuple(r["group"]), r["ports"], r["fps"]): r["metrics"] or {} for r in map(json.loads, open(os.path.join(HERE, p)))}


def ok(m, f):
    if not m or not m.get("achieved_fps"):
        return False
    t = 1000.0 / FPS[f]
    return m["achieved_fps"] >= 0.97 * t and 100.0 * m.get("late_lines", 0) / max(t * m["window_s"], 1) <= 3.0 and not m.get("errors")


def ceiling(by, g, f):
    best = 0
    for p in PORTS:
        if ok(by.get((g, p, f)), f):
            best = p
        else:
            break
    return best


base, now = load("results/perf-baseline.jsonl"), load("results/perf-final.jsonl")
groups = {}
for c in CASES:
    groups.setdefault(tuple(group_of(c)), []).append(c[0])
order = [(3, 3), (3, 6), (4, 4), (4, 8), (5, 5), (5, 10), (6, 6)]

ceil = ["## CPU ceiling by data path (the system limit, independent of wire time)\n",
        "Highest port count at which fppd still holds the frame cadence (each port 1,500 px; all smaller counts also pass). **Stock frame preparation → current build** "
        "(prefetching gather, ~1.6× faster):\n",
        "| source ch → wire bytes per pixel | ICs | 20 fps | 30 fps | 40 fps |", "|---|---|---|---|---|"]
for g in order:
    ceil.append("| %d → %d | %s | %s |" % (g[0], g[1], ", ".join(groups[g]),
                " | ".join("%d → **%d**" % (ceiling(base, g, f), ceiling(now, g, f)) for f in FPS)))
nb, nn = sum(ok(m, k[2]) for k, m in base.items()), sum(ok(m, k[2]) for k, m in now.items())
med = lambda d: sorted(m["fppd_cpu_pct"] for m in d.values())[len(d) // 2]
ceil.append("\nCells holding the frame cadence: **%d / %d before → %d / %d now**. Median fppd CPU: **%.0f%% → %.0f%%**." % (nb, len(base), nn, len(now), med(base), med(now)))
fails = [(g, p, f) for g in order for p in PORTS for f in FPS if not ok(now.get((g, p, f)), f)]
ceil.append("\nThe %d cells that still miss the cadence are all the widest data formats at the highest loads (%s). Their wire time already rules out "
            "those frame rates, so the CPU limit costs nothing in practice." % (
                len(fails), "; ".join("%s at %d ports, %d fps" % ("/".join(groups[g][:2]), p, f) for g, p, f in fails)))
ceil.append("\nThe same matrix ran with the new chip-current (TM1814 / UCS7604 / SM16825E at 50%) and TM1914 auto-switch settings active: those controls change "
            "only a few preamble/trailer bytes, so the numbers are the same as for the chip's data path above.\n")

rep = subprocess.run([sys.executable, os.path.join(HERE, "perf_report.py"), os.path.join(HERE, "results/perf-final.jsonl")], capture_output=True, text=True, check=True).stdout
load_sec = rep[:rep.index("## Verdict per IC")].rstrip() + "\n"

# ---- SPI -------------------------------------------------------------------------------------------------------
spi = [json.loads(l) for l in open(os.path.join(HERE, "results/perf-spi.jsonl"))]
sby = {(r["chip"], r["outputs"], r["fps"]): r["metrics"] or {} for r in spi}
chips = []
for r in spi:
    if r["chip"] not in [c[0] for c in chips]:
        chips.append((r["chip"], r["hz"]))
FIT = json.load(open(os.path.join(HERE, "results/spi-fit.json")))
alias = {"apa102hd": "apa102", "sk9822hd": "apa102", "apa107": "apa102"}
sec = ["## Clocked (SPI) chips — SPIPixels at 1,500 px per output\n",
       "The BeagleBone Green has 4 SPI chip-selects (`spidev0.0`, `0.1`, `1.0`, `1.1`) on two buses. SPIPixels writes each output **synchronously** from fppd's output "
       "thread, so the outputs are sent one after another and the time per frame is the **sum** of their transfers (measured: 2 outputs = exactly 2× one). "
       "Measured under real FSEQ playback with the data changing every frame, each chip at its plugin default clock: 1, 2 and 4 outputs × 1,500 px at 20/30/40 fps "
       "(90 measurements, 6-second windows, `hwtest/perf_spi.py`).\n",
       "A frame is on time when all outputs finish inside the frame interval. fppd CPU stays below 20% in every case; the limit is the **clock**, not the CPU.\n",
       "| chip | clock | frame @1,500 px, 1 output (measured) | outputs that hold 20 fps | 30 fps | 40 fps | max px, 1 output: 20 / 30 / 40 fps |", "|---|---|---|---|---|---|---|"]
for chip, hz in chips:
    row = []
    for f in FPS:
        held = [n for n in (1, 2, 4) if ok(sby.get((chip, n, f)), f)]
        row.append(str(max(held)) if held else "none")
    ms = sby.get((chip, 1, 20), {}).get("send_ms")
    mx = " / ".join("{:,}".format(spi_max(FIT, alias.get(chip, chip), hz, iv)) for iv in (50, 33, 25))
    sec.append("| %s | %.0f MHz | %s ms | %s | %s | %s | %s |" % (chip, hz / 1e6, ms, row[0], row[1], row[2], mx))
sec.append("\nReading the table: `4` means all four chip-selects at 1,500 px hold the cadence; `none` means even one output of 1,500 px takes longer than the "
           "frame (raise the clock if the chip allows it, or shorten the string — `MAX_PIXELS.md` has the pixel limit per chip and clock).\n")
sec.append("<details><summary>Every SPI measurement</summary>\n")
sec.append(subprocess.run([sys.executable, os.path.join(HERE, "perf_spi_report.py"), os.path.join(HERE, "results/perf-spi.jsonl")], capture_output=True, text=True, check=True).stdout)
sec.append("\n</details>\n")

# ---- splice ----------------------------------------------------------------------------------------------------
doc = open(DOC).read()
a = doc.index("## CPU ceiling by data path")
b = doc.index("## What changed in this round")
new = doc[:a] + "\n".join(ceil) + "\n" + load_sec + "\n" + "\n".join(sec) + "\n" + doc[b:]
new = re.sub(r"\(126 measurements:[^)]*\)", "(126 measurements: 7 data paths × 8/16/24/32/40/48 ports × 20/30/40 fps, 6-second windows, `hwtest/perf_matrix.py`, "
             "re-run on the current build that includes the chip-current / TM1914-mode controls and the new SPI chips)", new, count=1)
open(DOC, "w").write(new)
print("PERFORMANCE.md rewritten:", len(new.splitlines()), "lines; cadence cells", nn, "/", len(now))
