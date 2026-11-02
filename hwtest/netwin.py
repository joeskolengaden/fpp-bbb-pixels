#!/usr/bin/env python3
# [hwtest] board-side measurement window for streamed input (sACN / ArtNet / DDP): over <secs> seconds report fppd CPU, whole-system CPU,
# UDP datagrams in / dropped (socket buffer full = fppd could not keep up), NIC drops, the bridge's per-universe packet counters and
# "SLOW Output Thread" warnings. usage: netwin.py <secs> [iface=usb1]
import json, subprocess, sys, time, urllib.request
secs = float(sys.argv[1]) if len(sys.argv) > 1 else 8
iface = sys.argv[2] if len(sys.argv) > 2 else "usb1"
LOG = "/home/fpp/media/logs/fppd.log"


def pid():
    return subprocess.run(["pgrep", "-n", "fppd"], capture_output=True, text=True).stdout.strip()


def snmp():
    rows = [l.split() for l in open("/proc/net/snmp") if l.startswith("Udp:")]
    return dict(zip(rows[0][1:], map(int, rows[1][1:])))


def dev():
    for l in open("/proc/net/dev"):
        if l.strip().startswith(iface + ":"):
            f = l.split(":")[1].split()
            return {"rx_bytes": int(f[0]), "rx_packets": int(f[1]), "rx_errs": int(f[2]), "rx_drop": int(f[3])}
    return {"rx_bytes": 0, "rx_packets": 0, "rx_errs": 0, "rx_drop": 0}


def stats():
    try:
        d = json.loads(urllib.request.urlopen("http://127.0.0.1:32322/fppd/e131stats", timeout=5).read())
        return sum(int(u["packetsReceived"]) for u in d["universes"]), sum(int(u["errors"]) for u in d["universes"]), len(d["universes"])
    except Exception:
        return 0, 0, 0


def softnet_drops():
    # packets dropped in the per-CPU backlog before they reach a socket (column 2 of /proc/net/softnet_stat, hex): not counted by the UDP counters
    try:
        return sum(int(l.split()[1], 16) for l in open("/proc/net/softnet_stat"))
    except Exception:
        return 0


def snap(p):
    cpu = [int(x) for x in open("/proc/stat").readline().split()[1:]]
    st = open("/proc/%s/stat" % p).read().rsplit(")", 1)[1].split()
    return time.time(), sum(cpu), cpu[3] + cpu[4], int(st[11]) + int(st[12])


p = pid()
n0 = sum(1 for _ in open(LOG, errors="replace"))
a, s0, d0, e0, n0s = snap(p), snmp(), dev(), stats(), softnet_drops()
time.sleep(secs)
b, s1, d1, e1, n1s = snap(p), snmp(), dev(), stats(), softnet_drops()
dt, dtot, didle, dproc = b[0] - a[0], b[1] - a[1], b[2] - a[2], b[3] - a[3]
slow = sum(1 for i, l in enumerate(open(LOG, errors="replace")) if i >= n0 and "SLOW Output Thread" in l)
out = {"window_s": round(dt, 2), "fppd_cpu_pct": round(100.0 * dproc / max(dtot, 1), 1), "sys_busy_pct": round(100.0 * (dtot - didle) / max(dtot, 1), 1),
       "udp_in": s1["InDatagrams"] - s0["InDatagrams"], "udp_rcvbuf_drops": s1.get("RcvbufErrors", 0) - s0.get("RcvbufErrors", 0),
       "udp_in_errors": s1["InErrors"] - s0["InErrors"], "nic_rx_packets": d1["rx_packets"] - d0["rx_packets"], "nic_rx_drop": d1["rx_drop"] - d0["rx_drop"],
       "nic_rx_errs": d1["rx_errs"] - d0["rx_errs"], "nic_mbit": round((d1["rx_bytes"] - d0["rx_bytes"]) * 8 / dt / 1e6, 1),
       "bridge_packets": e1[0] - e0[0], "bridge_errors": e1[1] - e0[1], "bridge_universes": e1[2], "slow_warn": slow, "softnet_drops": n1s - n0s}
print(json.dumps(out))
