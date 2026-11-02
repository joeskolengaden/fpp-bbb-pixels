#!/usr/bin/env python3
"""
perf_matrix.py - system performance at <ports> populated PRU outputs x 1,500 pixels each, per pixel-IC data path and
frame rate, under real FSEQ playback (data changes every frame).

Per (representative IC, ports): configure FPP, restart fppd, then for 20 / 30 / 40 fps generate an FSEQ on the board,
loop it, and take a 6 s measurement window (perfwin.py): fppd CPU, system CPU, memory, per-frame Send/Read/Process
time and fppd's own frame timing log (late frames, achieved frame rate).
ICs that share a data path (same source channels/pixel and output bytes/pixel) share the software measurement; the PRU
wire-time verdict is per IC (computed in perf_report.py from the measured bit periods).

  python3 perf_matrix.py --out results/perf.jsonl [--ports 8,16,24,32,40,48] [--fps 20,30,40] [--groups all]
"""
import argparse, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import measure_limits as m
from verify_presets import FPP, CASES, expected_wire, order_info, case_by_key

SCR = m.SCR
NPIX = 1500
STEP = {20: 50, 30: 33, 40: 25}


def group_of(case):
    key, label, timing, order, inv, prof, pre, post, sig = case
    src_per, _ = order_info(order)
    one, _ = expected_wire(order, 1, pre, post); zero, _ = expected_wire(order, 0, pre, post)
    return (src_per, len(one) - len(zero))


def groups():
    g = {}
    for c in CASES:
        g.setdefault(group_of(c), []).append(c[0])
    return g


def cfg_for(base, case, ports):
    key, label, timing, order, *_ = case
    cfg, ch = m.build_cfg(base, timing, order, NPIX, ports=1)
    co = cfg["channelOutputs"][0]
    vss = co["outputs"][m.TEST_SLOT]["virtualStrings"]
    for o in co["outputs"]:
        o["virtualStrings"] = []
    for sl in range(ports):
        co["outputs"][sl]["virtualStrings"] = json.loads(json.dumps(vss))
    # exercise the chip-current / TM1914-mode controls on the chips that have them (same bytes on the wire, new code path)
    sig = case[8]
    if sig in ("TM1814", "UCS7604", "SM16825E"):
        co["chipCurrent"] = 50
    if sig == "TM1914":
        co["tm1914Mode"] = "auto"
    return cfg, ch


def run_point(fpp, ch_total, fps, secs=6):
    step = STEP[fps]
    frames = max(40, int(2000 / step))
    m.ssh("sudo rm -f /home/fpp/media/sequences/perf.fseq; python3 /tmp/mkfseq.py /home/fpp/media/sequences/perf.fseq %d %d %d" % (ch_total, frames, step), 300)
    fpp.stop_playlist(); time.sleep(1)
    fpp.req("/api/command/Start%20Playlist/perf/true/false")
    time.sleep(3.5)
    out = m.ssh("python3 /tmp/perfwin.py %d" % secs, 60)
    line = [l for l in out.splitlines() if l.startswith("{")]
    fpp.stop_playlist()
    return json.loads(line[-1]) if line else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fpp", default="http://192.168.6.2")
    ap.add_argument("--ports", default="8,16,24,32,40,48")
    ap.add_argument("--fps", default="20,30,40")
    ap.add_argument("--only", default="", help="comma list of case keys to use as group representatives")
    ap.add_argument("--all-ics", action="store_true", help="measure every IC individually instead of one per data path")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    fpp = FPP(a.fpp)
    m.push("mkfseq.py", "perfwin.py")
    base, _bk = fpp.backup_config(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results', 'config-backups'))
    print('starting config saved to', _bk)
    done = set()
    if os.path.exists(a.out):
        for l in open(a.out):
            r = json.loads(l); done.add((r["case"], r["ports"], r["fps"]))
    if a.all_ics:
        reps = [(c[0], group_of(c)) for c in CASES]
    else:
        reps = [(v[0], k) for k, v in groups().items()]
    if a.only:
        reps = [r for r in reps if r[0] in a.only.split(",")]
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    fpp.req("/api/settings/LogLevel_ChannelOut", "PUT", "debug")
    # the run plays a throw-away playlist named 'perf' (removed again at the end)
    m.ssh("""python3 -c "import json;json.dump({'name':'perf','version':3,'repeat':0,'loopCount':0,'empty':False,'desc':'','random':0,'leadIn':[],'mainPlaylist':[{'type':'sequence','enabled':1,'playOnce':0,'sequenceName':'perf.fseq','duration':0}],'leadOut':[],'playlistInfo':{'total_duration':None,'total_items':1}},open('/home/fpp/media/playlists/perf.json','w'),indent=2)" """)
    try:
        for key, grp in reps:
            case = case_by_key(key)
            for ports in [int(x) for x in a.ports.split(",")]:
                todo = [f for f in [int(x) for x in a.fps.split(",")] if (key, ports, f) not in done]
                if not todo:
                    continue
                cfg, ch = cfg_for(base, case, ports)
                fpp.put_config(cfg); fpp.restart()
                for fps in todo:
                    r = run_point(fpp, ch * ports, fps)
                    rec = {"case": key, "group": list(grp), "ports": ports, "fps": fps, "channels": ch * ports, "metrics": r}
                    open(a.out, "a").write(json.dumps(rec) + "\n")
                    mm = r or {}
                    print("%-12s ports=%-2d fps=%d cpu=%5s%% sys=%5s%% work avg/max=%s/%s ms late=%s achieved=%s" % (
                        key, ports, fps, mm.get("fppd_cpu_pct"), mm.get("sys_busy_pct"), mm.get("work_ms_avg"), mm.get("work_ms_max"),
                        mm.get("late_lines"), mm.get("achieved_fps")), flush=True)
    finally:
        try:
            fpp.stop_playlist(); fpp.req("/api/settings/LogLevel_ChannelOut", "PUT", "info"); fpp.put_config(base); fpp.restart()
            m.ssh("sudo rm -f /home/fpp/media/sequences/perf.fseq /home/fpp/media/playlists/perf.json")
        except Exception as e:
            print("!! restore failed:", e)
        print("restored")


if __name__ == "__main__":
    main()
