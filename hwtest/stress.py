#!/usr/bin/env python3
"""
stress.py - push the board to its limits, software only (no wiring, nothing a chip can be hurt by).

  A  pixel ladder   48 ports, Normal timing: more and more pixels per port at 20 fps and at 40 fps until a port no longer fits its frame
  B  widest format  48 ports of 16-bit RGBWC (10 bytes/pixel, the heaviest data path) at 20 fps, increasing pixels
  C  everything at once   48 ports x 1500 px (PRU) + 4 SPI outputs x 1500 px (SPIPixels) + the web API polled by 4 parallel clients
  D  soak           the 48 x 1500 px load for --soak minutes, sampled every 30 s: fppd CPU, load, free memory, SoC temperature, late frames, errors
  E  restart storm  fppd restarted N times with the full 48-port config (PRU recompiled and restarted each time) + one SIGKILL of fppd
A phase "holds" when achieved fps >= 97% of the target, <= 3% late lines and no errors (same criterion as perf_matrix.py).
The original pixel config is restored by the caller byte-for-byte; this script also puts back what it can through the API.

  python3 stress.py --out results/stress.jsonl [--soak 8] [--storm 8] [--phases A,B,C,D,E]
"""
import argparse, copy, json, os, re, subprocess, sys, threading, time, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import measure_limits as m
from verify_presets import FPP
import perf_matrix as pm
import perf_spi as ps

STEP = {20: 50, 25: 40, 30: 33, 40: 25}
RECORDS = []


def rec(out, **kw):
    RECORDS.append(kw)
    open(out, "a").write(json.dumps(kw) + "\n")


def holds(r, fps):
    if not r or not r.get("achieved_fps"):
        return False
    t = 1000.0 / STEP[fps]
    return r["achieved_fps"] >= 0.97 * t and 100.0 * r.get("late_lines", 0) / max(t * r["window_s"], 1) <= 3.0 and not r.get("errors")


def temp_c():
    o = m.ssh("cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null").strip().splitlines()
    try:
        return int(o[-1]) / 1000.0
    except Exception:
        return None


def build(base, timing, order, pixels, ports=48):
    cfg, ch = m.build_cfg(base, timing, order, pixels, ports=1)
    co = cfg["channelOutputs"][0]
    vss = co["outputs"][m.TEST_SLOT]["virtualStrings"]
    for o in co["outputs"]:
        o["virtualStrings"] = []
    for sl in range(ports):
        co["outputs"][sl]["virtualStrings"] = json.loads(json.dumps(vss))
    return cfg, ch


def show(tag, r, fps, extra=""):
    r = r or {}
    print("%-34s cpu=%5s%% load=%-5s work avg/max=%s/%s ms late=%-4s achieved=%-5s %s -> %s" % (
        tag, r.get("fppd_cpu_pct"), r.get("sys_busy_pct"), r.get("work_ms_avg"), r.get("work_ms_max"), r.get("late_lines"),
        r.get("achieved_fps"), extra, "HOLDS" if holds(r, fps) else "FAILS"), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fpp", default="http://192.168.6.2")
    ap.add_argument("--out", required=True)
    ap.add_argument("--phases", default="A,B,C,D,E")
    ap.add_argument("--soak", type=float, default=8)
    ap.add_argument("--storm", type=int, default=8)
    ap.add_argument("--cvariants", default="4:4", help="phase C variants as spi_outputs:api_clients, comma separated")
    a = ap.parse_args()
    ph = a.phases.split(",")
    fpp = FPP(a.fpp)
    m.push("mkfseq.py", "perfwin.py")
    base, bk = fpp.backup_config(os.path.join(HERE, "results", "config-backups"))
    print("starting pixel config saved to", bk)
    m.ssh("""python3 -c "import json;json.dump({'name':'perf','version':3,'repeat':0,'loopCount':0,'empty':False,'desc':'','random':0,'leadIn':[],'mainPlaylist':[{'type':'sequence','enabled':1,'playOnce':0,'sequenceName':'perf.fseq','duration':0}],'leadOut':[],'playlistInfo':{'total_duration':None,'total_items':1}},open('/home/fpp/media/playlists/perf.json','w'),indent=2)" """)
    fpp.req("/api/settings/LogLevel_ChannelOut", "PUT", "debug")
    t_start = temp_c()
    print("SoC temperature at start: %s C" % t_start, flush=True)
    try:
        if "A" in ph:
            print("\n== A: pixel ladder, 48 ports, Normal timing, GRB ==", flush=True)
            for fps, ladder in ((20, [1200, 1500, 1600, 1650, 1700, 1800]), (40, [700, 800, 830, 860, 900])):
                for n in ladder:
                    cfg, ch = build(base, 0, "GRB", n)
                    fpp.put_config(cfg); fpp.restart()
                    r = pm.run_point(fpp, ch * 48, fps)
                    wire_ms = n * 3 * 8 * 1.244 / 1000
                    show("A %d fps, %d px/port (%.1f ms)" % (fps, n, wire_ms), r, fps, "%d px total" % (n * 48))
                    rec(a.out, phase="A", fps=fps, pixels=n, ports=48, wire_ms=round(wire_ms, 1), metrics=r, holds=holds(r, fps), temp=temp_c())
        if "B" in ph:
            print("\n== B: widest data path (RGBWC16 = 10 bytes/pixel), 48 ports, 20 fps ==", flush=True)
            for n in (300, 400, 480, 520):
                cfg, ch = build(base, 0, "RGBWC16", n)
                fpp.put_config(cfg); fpp.restart()
                r = pm.run_point(fpp, ch * 48, 20)
                show("B 20 fps, %d px/port (%.1f ms)" % (n, n * 10 * 8 * 1.26 / 1000), r, 20)
                rec(a.out, phase="B", fps=20, pixels=n, ports=48, metrics=r, holds=holds(r, 20), temp=temp_c())
        if "C" in ph:
            print("\n== C: PRU 48 x 1500 px + SPI outputs (apa102, 1500 px each) + parallel API clients, by variant ==", flush=True)
            cfg, ch = build(base, 0, "GRB", 1500)
            for variant in a.cvariants.split(","):
                nspi, napi = [int(x) for x in variant.split(":")]
                fpp.put_config(cfg)
                if nspi:
                    sc = ps.spi_cfg("apa102", "BGR", 8_000_000, nspi)
                    off = ch * 48                   # the SPI outputs read the channels right after the PRU's
                    sc["channelOutputs"][0]["startChannel"] = off + 1
                    for o in sc["channelOutputs"][0]["outputs"]:
                        for v in o["virtualStrings"]:
                            v["startChannel"] += off
                    fpp.req("/api/configfile/co-other.json", "POST", json.dumps(sc, indent=2))
                else:
                    m.ssh("sudo rm -f /home/fpp/media/config/co-other.json")
                fpp.restart()
                stop = threading.Event(); hits = [0, 0]
                def hammer():
                    while not stop.is_set():
                        for path in ("/api/fppd/status", "/api/system/status", "/api/fppd/version", "/api/system/info"):
                            try:
                                urllib.request.urlopen(a.fpp + path, timeout=5).read(); hits[0] += 1
                            except Exception:
                                hits[1] += 1
                ths = [threading.Thread(target=hammer, daemon=True) for _ in range(napi)]
                [t.start() for t in ths]
                r = pm.run_point(fpp, ch * 48 + ps.NPIX * 3 * nspi, 20)
                stop.set(); [t.join(3) for t in ths]
                show("C 20 fps: PRU + %d SPI + %d API clients" % (nspi, napi), r, 20, "api ok=%d fail=%d send=%sms" % (hits[0], hits[1], (r or {}).get("send_ms")))
                rec(a.out, phase="C", spi=nspi, api=napi, fps=20, metrics=r, holds=holds(r, 20), api_ok=hits[0], api_fail=hits[1])
            m.ssh("sudo rm -f /home/fpp/media/config/co-other.json")
        if "D" in ph:
            print("\n== D: soak, 48 x 1500 px at 20 fps for %.0f min ==" % a.soak, flush=True)
            cfg, ch = build(base, 0, "GRB", 1500)
            fpp.put_config(cfg); fpp.restart(); fpp.stop_playlist()
            m.ssh("sudo rm -f /home/fpp/media/sequences/perf.fseq; python3 /tmp/mkfseq.py /home/fpp/media/sequences/perf.fseq %d %d 50" % (ch * 48, 40), 300)
            fpp.req("/api/command/Start%20Playlist/perf/true/false"); time.sleep(4)
            t_end = time.time() + a.soak * 60; k = 0; worst_temp = 0; bad = 0
            mem0 = None
            while time.time() < t_end:
                out = m.ssh("python3 /tmp/perfwin.py 30", 90)
                line = [l for l in out.splitlines() if l.startswith("{")]
                r = json.loads(line[-1]) if line else None
                tc = temp_c(); worst_temp = max(worst_temp, tc or 0); k += 1
                load = m.ssh("cat /proc/loadavg").split()[-5:-2]
                mem0 = mem0 or (r or {}).get("mem_free_mb")
                ok = holds(r, 20); bad += not ok
                print("  t+%4.1f min cpu=%5s%% mem_free=%sMB temp=%sC late=%-3s achieved=%s %s" % (
                    k * 0.5, (r or {}).get("fppd_cpu_pct"), (r or {}).get("mem_free_mb"), tc, (r or {}).get("late_lines"), (r or {}).get("achieved_fps"),
                    "ok" if ok else "MISS"), flush=True)
                rec(a.out, phase="D", minute=k * 0.5, metrics=r, holds=ok, temp=tc)
                if tc and tc > 88:
                    print("  !! SoC above 88 C: stopping the soak early"); break
            fpp.stop_playlist()
            print("  soak: %d windows, %d missed, hottest %.1f C" % (k, bad, worst_temp), flush=True)
        if "E" in ph:
            print("\n== E: restart storm (%d fppd restarts with the full 48-port config, then 1 SIGKILL) ==" % a.storm, flush=True)
            cfg, ch = build(base, 0, "GRB", 1500)
            fpp.put_config(cfg)
            okc = 0; times = []
            for i in range(a.storm):
                t0 = time.time()
                try:
                    fpp.restart(); good = True
                except Exception as e:
                    good = False
                dt = time.time() - t0
                log = m.ssh("tail -80 /home/fpp/media/logs/fppd.log | grep -ciE 'Unable to start PRU|segfault|terminate called'").strip().split()[-1]
                st = json.loads(fpp.req("/api/fppd/status")) if good else {}
                ok = good and st.get("fppd") == "running" and int(log) == 0
                okc += ok; times.append(dt)
                print("  restart %2d: %.0f s  fppd=%s  PRU/crash lines=%s -> %s" % (i + 1, dt, st.get("fppd"), log, "ok" if ok else "FAIL"), flush=True)
            # crash recovery: SIGKILL fppd and see whether the system brings it back by itself
            m.ssh("sudo pkill -9 -x fppd; true")
            back = None
            for s in range(1, 61):
                time.sleep(2)
                try:
                    if json.loads(fpp.req("/api/fppd/status", timeout=4)).get("fppd") == "running":
                        back = s * 2; break
                except Exception:
                    pass
            print("  SIGKILL: fppd %s" % ("came back by itself after ~%d s" % back if back else "did NOT come back within 120 s"), flush=True)
            rec(a.out, phase="E", restarts=a.storm, ok=okc, avg_s=round(sum(times) / len(times), 1), sigkill_recovery_s=back)
            if not back:
                m.ssh("sudo systemctl start fppd")
    finally:
        try:
            fpp.stop_playlist(); fpp.req("/api/settings/LogLevel_ChannelOut", "PUT", "info")
            m.ssh("sudo rm -f /home/fpp/media/sequences/perf.fseq /home/fpp/media/playlists/perf.json /home/fpp/media/config/co-other.json")
        except Exception as e:
            print("!! cleanup:", e)
        print("end temperature: %s C (start %s C)\nstress finished; caller must restore the byte-exact config" % (temp_c(), t_start), flush=True)


if __name__ == "__main__":
    main()
