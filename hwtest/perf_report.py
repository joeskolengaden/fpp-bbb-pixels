#!/usr/bin/env python3
"""
perf_report.py - combine the measured system performance (perf.jsonl) with each IC's wire time (measured bit period)
into a verdict per IC x ports x frame rate at 1,500 pixels per port.

  cell verdict = PRU wire time  (frame time at 1,500 px vs FPP frame interval - chip reset - 0.2 ms; a miss means the far end
                                 of each string is cut off, measured earlier)
               + system         (fppd keeps the frame cadence: achieved fps >= 97% of target and <= 3% late frames)
"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from verify_presets import CASES, expected_wire
from max_pixels import RESET_US, SLACK_US

PORTS = [8, 16, 24, 32, 40, 48]
FPS = {20: 50, 30: 33, 40: 25}
N = 1500
perf_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "results/perf.jsonl")

cal = {r["key"]: r for r in json.load(open(os.path.join(HERE, "results/limits-calib.json"))) if r}
recs = [json.loads(l) for l in open(perf_path)]
by = {}
for r in recs:
    by[(tuple(r["group"]), r["ports"], r["fps"])] = r["metrics"] or {}


def group_of(c):
    from perf_matrix import group_of as g
    return g(c)


def sys_ok(m, fps):
    if not m or not m.get("achieved_fps"):
        return None
    target = 1000.0 / FPS[fps]
    exp_frames = target * m["window_s"]
    late_pct = 100.0 * m.get("late_lines", 0) / max(exp_frames, 1)
    return m["achieved_fps"] >= 0.97 * target and late_pct <= 3.0 and not m.get("errors")


def pru(key, fps):
    c = [c for c in CASES if c[0] == key][0]
    order, pre, post = c[3], c[6], c[7]
    one, _ = expected_wire(order, 1, pre, post); zero, _ = expected_wire(order, 0, pre, post)
    bpp, fixed = len(one) - len(zero), len(zero) + len(post)
    tbit = cal[key]["dur_max"] * 1000.0 / cal[key]["bits"]
    ft = (fixed + N * bpp) * 8 * tbit / 1e6                       # ms
    budget = FPS[fps] - (RESET_US[key] + SLACK_US) / 1000.0
    return ft, budget, int((budget * 1e6 / tbit / 8 - fixed) // bpp)


lines = []
add = lines.append
add("## System load by data path (1,500 px on every populated port, FSEQ playback, data changing each frame)\n")
add("Each cell: fppd CPU % of the single core · work ms per frame (avg/max: sequence read + channel map + copy to PRU memory) · "
    "achieved fps · late frames in the 6 s window.\n")
groups = {}
for c in CASES:
    groups.setdefault(group_of(c), []).append(c[0])
for g, members in groups.items():
    add("**%d source ch/px → %d wire bytes/px** — ICs: %s\n" % (g[0], g[1], ", ".join(members)))
    add("| ports | channels/frame | " + " | ".join("%d fps (%d ms)" % (f, FPS[f]) for f in FPS) + " |")
    add("|---|---|" + "---|" * len(FPS))
    for p in PORTS:
        cells = []
        for f in FPS:
            m = by.get((g, p, f))
            if not m:
                cells.append("—"); continue
            ok = sys_ok(m, f)
            cells.append("%s %s%% · %s/%s ms · %s fps · %s late" % ("✅" if ok else "❌", m["fppd_cpu_pct"], m.get("work_ms_avg"), m.get("work_ms_max"),
                                                                  m.get("achieved_fps"), m.get("late_lines")))
        ch = next((r["channels"] for r in recs if tuple(r["group"]) == g and r["ports"] == p), None)
        add("| %d | %s | %s |" % (p, "{:,}".format(ch) if ch else "—", " | ".join(cells)))
    add("")

add("## Verdict per IC at 1,500 px/port\n")
add("`OK` = frame fits the interval and the system holds the cadence. `PRU` = the wire time of 1,500 px exceeds the frame "
    "(shows the pixel count that does fit). `SYS n` = system keeps cadence only up to n ports.\n")
add("| IC / format | frame time @1,500 px | " + " | ".join("%d fps (%d ms)" % (f, FPS[f]) for f in FPS) + " |")
add("|---|---|" + "---|" * len(FPS))
for c in CASES:
    key = c[0]; g = group_of(c)
    cells = []
    for f in FPS:
        ft, budget, maxpx = pru(key, f)
        sysports = [p for p in PORTS if sys_ok(by.get((g, p, f)), f)]
        measured = [p for p in PORTS if by.get((g, p, f))]
        if ft > budget:
            v = "PRU — max %d px" % maxpx
            if measured and not sysports:
                v += "; SYS 0"
        elif not measured:
            v = "OK (PRU) — system n/a"
        elif len(sysports) == len(PORTS):
            v = "OK, all 48"
        elif not sysports:
            v = "SYS — fails at 8 ports"
        else:
            v = "SYS ≤ %d ports" % max(sysports)
        cells.append(v)
    ft1, _, _ = pru(key, 20)
    add("| %s | %.1f ms | %s |" % (c[1], ft1, " | ".join(cells)))
print("\n".join(lines))
