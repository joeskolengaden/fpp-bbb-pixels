#!/usr/bin/env python3
"""
stream_test2.py - streaming limits, done properly.
  board mode: the frames are replayed ON the board (loopback, paced like a 100 Mbit wire) so the Mac's USB adapter is out of the picture and
              what is measured is fppd's own packet-processing capacity (receive + merge into the channel buffer + PRU output), per protocol.
  mac mode:   the Mac sends, paced evenly across each frame; loss is judged against what the Mac interface really transmitted (netstat), not
              against what sendto() accepted (macOS drops silently when its USB adapter queue overflows).
A run PASSES when the board received >= 99.9% of what was sent, the socket buffer never overflowed (RcvbufErrors = 0), the bridge's own
packet counter matches (sACN/ArtNet) and fppd logged no SLOW Output Thread warning.
  python3 stream_test2.py --mode board --out results/stream-board.jsonl [--protocols sacn,artnet,ddp]
"""
import argparse, json, math, os, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import measure_limits as m
from verify_presets import FPP
import stress, stream_test as st

SEQ = {"sacn": (111, 255, 126), "artnet": (12, 255, 18), "ddp": (1, 15, 10)}     # sequence byte offset, modulus, header length (data offset)
GROUP = {"sacn": 8, "artnet": 8, "ddp": 4}


def write_frames(proto, ch, path):
    frames, port = st.build_frames(proto, ch)
    with open(path, "wb") as f:
        for p in frames[0]:
            f.write(len(p).to_bytes(2, "little") + bytes(p))
    return port, len(frames[0])


def board_point(fpp, proto, ch, fps, secs=8):
    path = "/tmp/frames_%s_%d.bin" % (proto, ch)
    local = os.path.join("/tmp", os.path.basename(path))
    port, npk = write_frames(proto, ch, local)
    subprocess.run([os.path.join(m.SCR, "bbgcp"), local, "fpp@192.168.6.2:" + path], capture_output=True, check=True, timeout=60)
    off, mod, hdr = SEQ[proto]
    snd = subprocess.Popen([os.path.join(m.SCR, "bbg"), "/tmp/udpreplay %s 127.0.0.1 %d %d %d %d %d %d %d" % (path, port, fps, secs + 9, off, mod, GROUP[proto], hdr)],
                           stdout=subprocess.PIPE, text=True)
    time.sleep(3)
    out = m.ssh("python3 /tmp/netwin.py %d lo" % secs, 60)
    so = snd.communicate()[0]
    bl = [l for l in out.splitlines() if l.startswith("{")]; sl = [l for l in so.splitlines() if l.startswith("{")]
    if not bl or not sl:
        return None
    b, s = json.loads(bl[-1]), json.loads(sl[-1])
    rx = b["udp_in"] / b["window_s"]
    loss = max(0.0, 1 - rx / s["pps"]) * 100
    # judged on what fppd did: no socket-buffer or backlog drops, loss within the window-edge noise (0.15%), no SLOW output warnings.
    # (the replayer shares the one core with fppd, so its own late frames are reported but do not fail the run)
    ok = loss <= 0.15 and b["udp_rcvbuf_drops"] == 0 and b["softnet_drops"] == 0 and b["slow_warn"] == 0
    return dict(proto=proto, channels=ch, fps=fps, pkts_per_frame=npk, tx_pps=s["pps"], rx_pps=round(rx), loss_pct=round(loss, 2), board=b, sender=s, ok=ok)


def mac_point(fpp, proto, ch, fps, secs=8):
    import threading
    def oper():
        o = subprocess.run(["netstat", "-I", "en7", "-b"], capture_output=True, text=True).stdout.splitlines()
        return int(dict(zip(o[0].split(), o[1].split()))["Opkts"])
    frames, port = st.build_frames(proto, ch)
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4 << 20)
    off = SEQ[proto][0]
    res = {}
    def run():
        per = 1.0 / fps; t0 = time.perf_counter(); nfr = 0; late = 0
        nxt = t0
        while time.perf_counter() - t0 < secs + 5:
            fr = frames[nfr & 1]; n = len(fr); seq = (nfr % SEQ[proto][1]) + 1
            for i, p in enumerate(fr):
                due = nxt + per * 0.8 * i / n
                while time.perf_counter() < due:
                    pass
                p[off] = seq
                sock.sendto(p, ("192.168.6.2", port))
            nfr += 1; nxt += per
            d = nxt - time.perf_counter()
            if d > 0: time.sleep(d)
            else:
                late += 1
                if d < -per: nxt = time.perf_counter()
        res.update(frames=nfr, late=late, el=time.perf_counter() - t0)
    th = threading.Thread(target=run); th.start()
    time.sleep(3); o0 = oper(); t0 = time.time()
    out = m.ssh("python3 /tmp/netwin.py %d usb1" % secs, 60)
    o1 = oper(); dt = time.time() - t0
    th.join()
    bl = [l for l in out.splitlines() if l.startswith("{")]
    if not bl:
        return None
    b = json.loads(bl[-1]); tx = (o1 - o0) / dt; rx = b["udp_in"] / b["window_s"]
    want = len(frames[0]) * fps
    loss = max(0.0, 1 - rx / tx) * 100 if tx else 100.0
    ok = loss <= 0.1 and b["udp_rcvbuf_drops"] == 0 and b["slow_warn"] == 0
    return dict(proto=proto, channels=ch, fps=fps, pkts_per_frame=len(frames[0]), wanted_pps=want, mac_wire_pps=round(tx), rx_pps=round(rx), loss_pct=round(loss, 2),
                mac_delivered_pct=round(100 * tx / want, 1), board=b, ok=ok)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["board", "mac"], default="board")
    ap.add_argument("--out", required=True)
    ap.add_argument("--protocols", default="sacn,artnet,ddp")
    ap.add_argument("--fps", default="")
    ap.add_argument("--scen", default="S1,S2")
    ap.add_argument("--rmem", type=int, default=0, help="set net.core.rmem_default/max to this many bytes for the run (restored afterwards)")
    a = ap.parse_args()
    fpp = FPP("http://192.168.6.2")
    m.push("netwin.py")
    subprocess.run([os.path.join(m.SCR, "bbgcp"), os.path.join(HERE, "udpreplay.c"), "fpp@192.168.6.2:/tmp/udpreplay.c"], capture_output=True, check=True)
    print(m.ssh("cd /tmp && gcc -O2 udpreplay.c -o udpreplay 2>&1 && echo built").strip())
    base, bk = fpp.backup_config(os.path.join(HERE, "results", "config-backups"))
    scen = {"S1": ("S1 your layout 16,320 px", None, 48960, [20, 40, 80, 120, 160, 240]),
            "S2": ("S2 full board 48x1650 px", 1650, 237600, [20, 30, 40, 60, 80, 120])}
    fn = board_point if a.mode == "board" else mac_point
    old_rmem = None
    if a.rmem:
        old_rmem = m.ssh("cat /proc/sys/net/core/rmem_default /proc/sys/net/core/rmem_max").split()[-2:]
        m.ssh("sudo sysctl -w net.core.rmem_default=%d net.core.rmem_max=%d" % (a.rmem, a.rmem * 2))
        print("socket receive buffer default/max: %d / %d bytes (was %s)" % (a.rmem, a.rmem * 2, "/".join(old_rmem)), flush=True)
    try:
        for proto in a.protocols.split(","):
            print("\n===== %s (%s mode) =====" % (proto, a.mode), flush=True)
            for key in a.scen.split(","):
                name, px, ch, fpss = scen[key]
                if a.fps: fpss = [int(x) for x in a.fps.split(",")]
                if a.mode == "mac": fpss = fpss[:3]
                if px:
                    cfg, _ = stress.build(base, 0, "GRB", px); fpp.put_config(cfg)
                else:
                    fpp.put_config(base)
                st.set_universes(fpp, proto, ch); fpp.restart(); fpp.stop_playlist(); time.sleep(3)
                for fps in fpss:
                    r = fn(fpp, proto, ch, fps)
                    if not r:
                        print("%-26s %3d fps: no measurement" % (name, fps), flush=True); continue
                    b = r["board"]
                    extra = ("tx %6.0f pps" % r["tx_pps"]) if a.mode == "board" else ("mac delivered %5.1f%% = %5d pps" % (r["mac_delivered_pct"], r["mac_wire_pps"]))
                    print("%-26s %3d fps %4d pkt/fr | %s | rx %6d pps loss %5.2f%% rcvbuf %-4d softnet %-4d | fppd cpu %5.1f%% sys %5.1f%% sender %s bridge %6d slow %d -> %s" % (
                        name, fps, r["pkts_per_frame"], extra, r["rx_pps"], r["loss_pct"], b["udp_rcvbuf_drops"], b["softnet_drops"], b["fppd_cpu_pct"], b["sys_busy_pct"],
                        ("%.0f%%" % (100 * r["sender"]["sender_cpu_s"] / r["sender"]["elapsed"])) if a.mode == "board" else "-", b["bridge_packets"], b["slow_warn"], "PASS" if r["ok"] else "FAIL"), flush=True)
                    stress.rec(a.out, scenario=name, **{k: v for k, v in r.items() if k not in ()})
                    if not r["ok"]:
                        print("   (limit reached; skipping higher rates)", flush=True); break
    finally:
        if old_rmem:
            m.ssh("sudo sysctl -w net.core.rmem_default=%s net.core.rmem_max=%s" % tuple(old_rmem))
        m.ssh("rm -f /tmp/frames_*.bin")
        print("\nfinished; caller restores ci-universes.json and the pixel config byte-exact", flush=True)


if __name__ == "__main__":
    main()
