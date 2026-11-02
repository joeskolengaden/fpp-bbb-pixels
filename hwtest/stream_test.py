#!/usr/bin/env python3
"""
stream_test.py - find the limits of streaming pixel data to the controller over the network (sACN/E1.31, ArtNet, DDP).

This Mac sends complete frames at a chosen rate to the board (unicast, over the 100 Mbit link it is plugged into) while a board-side
window (netwin.py) records what fppd did: UDP datagrams received and dropped (socket buffer full = fppd could not keep up), NIC drops,
fppd and system CPU, the bridge's own packet counters and SLOW-output warnings. Loss is judged by rate:  1 - received/sent.
A run PASSES when loss <= 0.1%, the sender kept its schedule (<= 1% late frames) and there are no SLOW Output Thread warnings.

  python3 stream_test.py --out results/stream.jsonl [--protocols sacn,artnet,ddp]
Changes made on the board (restored by the caller byte-for-byte): ci-universes.json (input universes), and the pixel config for the full-board scenario.
"""
import argparse, json, math, os, socket, struct, subprocess, sys, threading, time, uuid
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import measure_limits as m
from verify_presets import FPP
import stress

BOARD = "192.168.6.2"
UNI = 510                                   # channels per universe (170 RGB pixels), as in the board's own input config
CID = uuid.UUID("12345678-1234-5678-1234-567812345678").bytes


def sacn_packets(channels):
    """E1.31 data packets, ANSI E1.31-2016 layout: 126 header bytes + data; one universe per 510 channels."""
    n = math.ceil(channels / UNI)
    pk = []
    for u in range(1, n + 1):
        cnt = min(UNI, channels - (u - 1) * UNI)
        total = 126 + cnt
        p = bytearray()
        p += struct.pack(">HH", 0x0010, 0) + b"ASC-E1.17\x00\x00\x00"                         # preamble, postamble, ACN id           (0-15)
        p += struct.pack(">HI", 0x7000 | (total - 16), 4) + CID                               # root PDU: length, vector, CID           (16-37)
        p += struct.pack(">HI", 0x7000 | (total - 38), 2) + b"stream_test".ljust(64, b"\x00")  # framing PDU: length, vector, source     (38-107)
        p += struct.pack(">BHBBH", 100, 0, 0, 0, u)                                           # priority, sync, seq(111), options, universe (108-114)
        p += struct.pack(">HBBHHH", 0x7000 | (total - 115), 2, 0xA1, 0, 1, cnt + 1) + b"\x00"  # DMP PDU, start code                     (115-125)
        assert len(p) == 126
        pk.append([bytes(p), cnt, u])
    return pk


def artnet_packets(channels):
    n = math.ceil(channels / UNI)
    pk = []
    for u in range(1, n + 1):
        cnt = min(UNI, channels - (u - 1) * UNI)
        cnt += cnt & 1                       # ArtNet lengths are even
        pk.append([b"Art-Net\x00" + struct.pack("<H", 0x5000) + struct.pack(">H", 14) + bytes([0, 0]) + struct.pack("<H", u) + struct.pack(">H", cnt), cnt, u])
    return pk


def ddp_packets(channels):
    pk, off = [], 0
    while off < channels:
        cnt = min(1440, channels - off)
        last = off + cnt >= channels
        pk.append([bytes([0x40 | (0x01 if last else 0), 0x01, 0x00, 0x01]) + struct.pack(">IH", off, cnt), cnt, off])
        off += cnt
    return pk


def build_frames(proto, channels, ncolors=2):
    """returns (packet list builder for a frame index, port). Two alternating payloads so every frame changes the data."""
    mk = {"sacn": sacn_packets, "artnet": artnet_packets, "ddp": ddp_packets}[proto](channels)
    port = {"sacn": 5568, "artnet": 6454, "ddp": 4048}[proto]
    pay = [bytes((i * 7 + k) & 0xFF for i in range(1440)) for k in range(ncolors)]
    frames = []
    for k in range(ncolors):
        fr = []
        for hdr, cnt, ident in mk:
            body = (pay[k] * (cnt // 1440 + 1))[:cnt]
            fr.append(bytearray(hdr + body))
        frames.append(fr)
    return frames, port


def send_stream(proto, channels, fps, seconds, result):
    frames, port = build_frames(proto, channels)
    seq_off = {"sacn": 111, "artnet": 12, "ddp": 1}[proto]
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4 << 20)
    addr = (BOARD, port)
    per = 1.0 / fps
    sent = late = nfr = 0
    t0 = time.time(); nxt = t0
    while time.time() - t0 < seconds:
        fr = frames[nfr & 1]
        seq = (nfr % 255) + 1 if proto != "ddp" else (nfr % 15) + 1       # E1.31 / ArtNet 1-255, DDP 1-15
        for p in fr:
            p[seq_off] = seq
            try:
                sock.sendto(p, addr)
            except OSError:
                pass
        sent += len(fr); nfr += 1
        nxt += per
        d = nxt - time.time()
        if d > 0:
            time.sleep(d)
        else:
            late += 1
            if d < -per:
                nxt = time.time()          # fell far behind: resync instead of bursting to catch up
    el = time.time() - t0
    result.update(sent=sent, frames=nfr, elapsed=el, late_frames=late, pps=sent / el, pkts_per_frame=len(frames[0]),
                  mbit=sum(len(p) + 42 for p in frames[0]) * 8 * nfr / el / 1e6)


def set_universes(fpp, proto, channels):
    n = math.ceil(channels / UNI)
    typ = {"sacn": 1, "artnet": 2, "ddp": 2}[proto]
    cfg = {"channelInputs": [{"type": "universes", "enabled": 1, "timeout": 1000, "startChannel": 1, "channelCount": -1,
                              "universes": [{"active": 1, "description": "", "id": 1, "startChannel": 1, "universeCount": n, "channelCount": UNI,
                                             "type": typ, "address": "", "priority": 0}]}]}
    fpp.req("/api/configfile/ci-universes.json", "POST", json.dumps(cfg, indent=2))


def run_point(fpp, proto, channels, fps, secs=8):
    res = {}
    th = threading.Thread(target=send_stream, args=(proto, channels, fps, secs + 5, res))
    th.start()
    time.sleep(2.5)                                         # let the stream settle before the board-side window opens
    out = m.ssh("python3 /tmp/netwin.py %d usb1" % secs, 60)
    th.join()
    line = [l for l in out.splitlines() if l.startswith("{")]
    b = json.loads(line[-1]) if line else None
    if not b:
        return None
    rx_rate = (b["udp_in"] / b["window_s"]) if b["window_s"] else 0
    loss = max(0.0, 1.0 - rx_rate / res["pps"]) * 100 if res.get("pps") else 100.0
    res.update(board=b, loss_pct=round(loss, 2), rx_pps=round(rx_rate))
    res["late_pct"] = round(100.0 * res["late_frames"] / max(res["frames"], 1), 1)
    res["pass"] = loss <= 0.1 and res["late_pct"] <= 1.0 and b["slow_warn"] == 0 and b["udp_rcvbuf_drops"] == 0
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fpp", default="http://192.168.6.2")
    ap.add_argument("--out", required=True)
    ap.add_argument("--protocols", default="sacn,artnet,ddp")
    a = ap.parse_args()
    fpp = FPP(a.fpp)
    m.push("netwin.py")
    base, bk = fpp.backup_config(os.path.join(HERE, "results", "config-backups"))
    print("starting pixel config saved to", bk)
    scen = [("S1 your layout 16,320 px", None, 48960, (20, 40, 80)),
            ("S2 full board 48x1650 px", 1650, 237600, (20, 30, 40, 60, 80, 120))]
    try:
        for proto in a.protocols.split(","):
            print("\n===== %s =====" % proto, flush=True)
            for name, px, ch, fpss in scen:
                if px:
                    cfg, _ = stress.build(base, 0, "GRB", px)
                    fpp.put_config(cfg)
                else:
                    fpp.put_config(base)
                set_universes(fpp, proto, ch)
                fpp.restart(); fpp.stop_playlist(); time.sleep(3)
                for fps in fpss:
                    r = run_point(fpp, proto, ch, fps)
                    if not r:
                        print("%-26s %3d fps: no measurement" % (name, fps), flush=True); continue
                    b = r["board"]
                    print("%-26s %3d fps %5d pkt/frame sent %6.0f pps %5.1f Mbit | rx %6d pps loss %5.2f%% rcvbuf_drops %-6d | fppd cpu %5.1f%% sys %5.1f%% | late_tx %4.1f%% slow %d -> %s" % (
                        name, fps, r["pkts_per_frame"], r["pps"], r["mbit"], r["rx_pps"], r["loss_pct"], b["udp_rcvbuf_drops"], b["fppd_cpu_pct"],
                        b["sys_busy_pct"], r["late_pct"], b["slow_warn"], "PASS" if r["pass"] else "FAIL"), flush=True)
                    stress.rec(a.out, protocol=proto, scenario=name, channels=ch, fps=fps, **{k: v for k, v in r.items() if k != "board"}, board=b)
                    if not r["pass"] and fps >= 40:
                        print("   (limit reached for this scenario; skipping higher rates)", flush=True)
                        break
    finally:
        print("\nstreaming test finished; caller restores ci-universes.json and the pixel config byte-exact", flush=True)


if __name__ == "__main__":
    main()
