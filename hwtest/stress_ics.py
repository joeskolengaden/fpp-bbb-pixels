#!/usr/bin/env python3
"""
stress_ics.py - per-chip stress test of the 48-port PRU output, judged against the WIRE, not only against fppd's own pacing.

For every chip case (verify_presets.CASES) it builds a 48-port config and runs two points at 20 fps:
  hold  pixels per port chosen so the frame fits the wire time with 5% margin  -> the driver must raise no LIMIT warning, the output
        must be alive (real work per frame) and fppd must keep 20 fps
  over  pixels per port 15% past what the wire allows                          -> the driver must say so (BBB48String LIMIT line in
        fppd.log: that port is cut short), fppd must stay up and keep 20 fps (graceful truncation, no crash)
Wire time = (pixels x wire bytes per pixel + preamble) x 8 x measured bit period + 0.3 ms chip reset, against 50 ms (20 fps) - 0.2 ms.
(Pacing alone is NOT a hold: fppd keeps its frame rate and silently updates only the first part of an over-long port.)

  python3 stress_ics.py --out results/stress-ics.jsonl [--only tm1814,tx1812] [--fps 20]
The live pixel config is restored byte-for-byte at the end (copy kept on the board in /tmp/co-bbbStrings.exact).
"""
import argparse, json, os, re, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import measure_limits as m
from verify_presets import FPP, CASES, order_info
import perf_matrix as pm
import stress

# bit period in ns measured on the board per Pixel Timing preset (live_timing_all.py); 11 (Custom) is not part of this sweep
PERIOD_NS = {0: 1244, 1: 1319, 2: 1713, 3: 2506, 4: 2507, 5: 2066, 6: 1245, 7: 1244, 8: 1092, 9: 1244, 10: 1244,
             12: 1293, 13: 1243, 14: 1243, 15: 1243, 16: 1250, 17: 1243, 18: 1244}
PREAMBLE_BYTES = {6: 8, 9: 6, 10: 15, 16: 9}     # setup bytes sent at the start of every port
RESET_MS = 0.3
LOG = "/home/fpp/media/logs/fppd.log"


def wire_ms(timing, order, pixels):
    src_per, _ = order_info(order)
    bpp = src_per * (2 if order.endswith("16") else 1)
    nbytes = pixels * bpp + PREAMBLE_BYTES.get(timing, 0)
    return nbytes * 8 * PERIOD_NS[timing] / 1e6 + RESET_MS, bpp


def pixels_for(timing, order, budget_ms, margin):
    src_per, _ = order_info(order)
    bpp = src_per * (2 if order.endswith("16") else 1)
    avail = (budget_ms - 0.2 - RESET_MS) * margin
    return max(1, int((avail * 1e6 / (8 * PERIOD_NS[timing]) - PREAMBLE_BYTES.get(timing, 0)) / bpp))


def one(fpp, base, key, label, timing, order, kind, fps):
    budget = {20: 50.0, 25: 40.0, 30: 33.0, 40: 25.0}[fps]
    px = pixels_for(timing, order, budget, 0.95 if kind == "hold" else 1.15)
    wms, bpp = wire_ms(timing, order, px)
    cfg, ch = stress.build(base, timing, order, px)
    n0 = int(m.ssh("wc -l < %s" % LOG).strip().split()[-1] or 0)
    fpp.put_config(cfg); fpp.restart()
    r = pm.run_point(fpp, ch * 48, fps)
    new = m.ssh("tail -n +%d %s | grep -E 'BBB48String (LIMIT|frame budget)|Unable to start PRU|segfault|terminate called' | head -12" % (n0 + 1, LOG))
    limit_lines = [l for l in new.splitlines() if "LIMIT" in l or "cannot sustain" in l]
    crashed = bool(re.search(r"Unable to start PRU|segfault|terminate called", new))
    st = {}
    try:
        st = json.loads(fpp.req("/api/fppd/status"))
    except Exception:
        pass
    alive = st.get("fppd") == "running"
    r = r or {}
    working = (r.get("work_ms_avg") or 0) >= 0.5          # the output thread really prepared frames (a stopped/disabled output shows ~0.05 ms)
    paced = stress.holds(r, fps) if r else False
    if kind == "hold":
        ok = paced and working and not limit_lines and not crashed and alive
    else:
        ok = paced and working and bool(limit_lines) and not crashed and alive
    why = []
    if not working: why.append("output not working (work_ms_avg %s)" % r.get("work_ms_avg"))
    if not paced: why.append("fppd missed its frame rate")
    if kind == "hold" and limit_lines: why.append("driver raised a LIMIT warning")
    if kind == "over" and not limit_lines: why.append("driver did not report the overrun")
    if crashed or not alive: why.append("fppd/PRU fault")
    return {"key": key, "label": label, "timing": timing, "order": order, "kind": kind, "fps": fps, "pixels": px, "ports": 48,
            "wire_ms": round(wms, 1), "budget_ms": budget, "ok": ok, "why": "; ".join(why), "limit_lines": limit_lines[:2],
            "metrics": r}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fpp", default="http://192.168.6.2")
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", default="")
    ap.add_argument("--fps", type=int, default=20)
    a = ap.parse_args()
    fpp = FPP(a.fpp)
    m.push("mkfseq.py", "perfwin.py")
    base, bk = fpp.backup_config(os.path.join(HERE, "results", "config-backups"))
    m.ssh("cp -p /home/fpp/media/config/co-bbbStrings.json /tmp/co-bbbStrings.exact")
    print("starting pixel config saved to", bk)
    m.ssh("""python3 -c "import json;json.dump({'name':'perf','version':3,'repeat':0,'loopCount':0,'empty':False,'desc':'','random':0,'leadIn':[],'mainPlaylist':[{'type':'sequence','enabled':1,'playOnce':0,'sequenceName':'perf.fseq','duration':0}],'leadOut':[],'playlistInfo':{'total_duration':None,'total_items':1}},open('/home/fpp/media/playlists/perf.json','w'),indent=2)" """)
    want = set(x for x in a.only.split(",") if x)
    bad = 0
    try:
        for key, label, timing, order, *_ in CASES:
            if want and key not in want:
                continue
            for kind in ("hold", "over"):
                r = one(fpp, base, key, label, timing, order, kind, a.fps)
                bad += not r["ok"]
                print("%-13s %-5s %5d px/port  wire %5.1f ms of %4.1f  work avg %-5s -> %s %s" % (
                    key, kind, r["pixels"], r["wire_ms"], r["budget_ms"], (r["metrics"] or {}).get("work_ms_avg"),
                    "PASS" if r["ok"] else "FAIL", r["why"]), flush=True)
                stress.rec(a.out, **r)
    finally:
        try:
            fpp.stop_playlist()
            m.ssh("sudo rm -f /home/fpp/media/sequences/perf.fseq /home/fpp/media/playlists/perf.json")
            m.ssh("cp -p /tmp/co-bbbStrings.exact /home/fpp/media/config/co-bbbStrings.json")
            fpp.restart()
        except Exception as e:
            print("!! restore failed:", e)
        print("restored, sha256 %s" % m.ssh("sha256sum /home/fpp/media/config/co-bbbStrings.json").strip()[:16])
    print("FAILURES: %d" % bad)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
