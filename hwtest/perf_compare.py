#!/usr/bin/env python3
"""perf_compare.py - before/after view of two perf.jsonl runs: per-frame work time and which cells hold the frame cadence."""
import json, sys, collections
a_path, b_path = sys.argv[1], sys.argv[2]
FPS = {20: 50, 30: 33, 40: 25}
def load(p):
    d = {}
    for l in open(p):
        r = json.loads(l); d[(tuple(r["group"]), r["ports"], r["fps"])] = r["metrics"] or {}
    return d
def ok(m, f):
    if not m or not m.get("achieved_fps"): return None
    t = 1000.0 / FPS[f]
    return m["achieved_fps"] >= 0.97 * t and 100.0 * m.get("late_lines", 0) / (t * m["window_s"]) <= 3.0
A, B = load(a_path), load(b_path)
cells = [k for k in A if k in B]
tot_a = sum(1 for k in cells if ok(A[k], k[2])); tot_b = sum(1 for k in cells if ok(B[k], k[2]))
print("cells holding the frame cadence: before %d / %d, after %d / %d\n" % (tot_a, len(cells), tot_b, len(cells)))
print("%-10s %5s %4s | %9s %9s %7s | %9s %9s | %s" % ("data path", "ports", "fps", "work ms", "work ms", "", "fppd CPU", "fppd CPU", "cadence"))
print("%-10s %5s %4s | %9s %9s %7s | %9s %9s | %s" % ("(src/wire)", "", "", "before", "after", "speedup", "before", "after", "before -> after"))
for g in sorted({k[0] for k in cells}):
    for p in (24, 48):
        for f in (20, 30, 40):
            k = (g, p, f)
            if k not in A or k not in B: continue
            a, b = A[k], B[k]
            if "work_ms_avg" not in a or "work_ms_avg" not in b:
                print("%-10s %5d %4d | (no frame-timing lines captured in one of the runs)" % ("%d/%d" % g, p, f)); continue
            print("%-10s %5d %4d | %9.1f %9.1f %6.2fx | %8.0f%% %8.0f%% | %s -> %s" % (
                "%d/%d" % g, p, f, a["work_ms_avg"], b["work_ms_avg"], a["work_ms_avg"] / max(b["work_ms_avg"], 0.01),
                a["fppd_cpu_pct"], b["fppd_cpu_pct"], "OK " if ok(a, f) else "BAD", "OK " if ok(b, f) else "BAD"))
