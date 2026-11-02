#!/usr/bin/env python3
# [hwtest] board-side measurement window: fppd CPU, whole-system CPU, memory, and the channel-output thread's own
# timing lines ("Output Thread: Loop/Send/Read/Process/Sleep/FrameNum", logged each second and for every late frame).
import glob, json, re, subprocess, sys, time
secs = float(sys.argv[1]) if len(sys.argv) > 1 else 6
LOG = "/home/fpp/media/logs/fppd.log"
def pid():
    return subprocess.run(["pgrep", "-n", "fppd"], capture_output=True, text=True).stdout.strip()
def snap(p):
    cpu = [int(x) for x in open("/proc/stat").readline().split()[1:]]
    st = open("/proc/%s/stat" % p).read().rsplit(")", 1)[1].split()
    return time.time(), sum(cpu), cpu[3] + cpu[4], int(st[11]) + int(st[12])      # wall, total jiffies, idle+iowait, fppd utime+stime
p = pid()
n0 = sum(1 for _ in open(LOG, errors="replace"))
a = snap(p)
time.sleep(secs)
b = snap(p)
dt, dtot, didle, dproc = b[0] - a[0], b[1] - a[1], b[2] - a[2], b[3] - a[3]
mem = {k: int(v.split()[0]) for k, v in (l.split(":") for l in open("/proc/meminfo"))}
rows = []
for i, line in enumerate(open(LOG, errors="replace")):
    if i < n0:
        continue
    m = re.search(r"Output Thread: Loop: (\d+)us, Send: (-?\d+)us, Read: (-?\d+)us, Process: (-?\d+)us, Sleep: (\d+)us, FrameNum: (\d+)", line)
    if m:
        ts = re.match(r"\d{4}-\d\d-\d\d (\d\d):(\d\d):(\d\d)\.(\d+)", line)
        t = int(ts.group(1)) * 3600 + int(ts.group(2)) * 60 + int(ts.group(3)) + int("0." + ts.group(4).ljust(3, "0")[:3][2:] if False else 0) + float("0." + ts.group(4)) if ts else 0.0
        rows.append(tuple(int(x) for x in m.groups()) + (t,))
slow = sum(1 for i, l in enumerate(open(LOG, errors="replace")) if i >= n0 and "SLOW Output Thread" in l)
errs = [l.strip()[:160] for i, l in enumerate(open(LOG, errors="replace")) if i >= n0 and re.search(r"error|fail|unable|overrun|corrupt", l, re.I) and "pixelselect" not in l][:3]
out = {"window_s": round(dt, 2), "fppd_cpu_pct": round(100.0 * dproc / max(dtot, 1), 1), "sys_busy_pct": round(100.0 * (dtot - didle) / max(dtot, 1), 1),
       "mem_free_mb": mem["MemFree"] // 1024 + mem.get("Cached", 0) // 1024, "log_rows": len(rows), "slow_warn": slow, "errors": errs}
if rows:
    loop = rows[-1][0]
    late = [r for r in rows if r[4] == 0]
    # achieved frame rate: frames advanced between consecutive log lines (ignoring the wrap when the sequence loops)
    rates = []
    for r0, r1 in zip(rows, rows[1:]):
        if r1[5] > r0[5] and r1[6] - r0[6] > 0.2:
            rates.append((r1[5] - r0[5]) / (r1[6] - r0[6]))
    rates.sort()
    out.update({"loop_us": loop, "late_lines": len(late),
                "send_ms": round(sum(r[1] for r in rows) / len(rows) / 1000, 2),
                "read_ms": round(sum(r[2] for r in rows) / len(rows) / 1000, 2),
                "process_ms": round(sum(r[3] for r in rows) / len(rows) / 1000, 2),
                "work_ms_max": round(max(r[1] + r[2] + r[3] for r in rows) / 1000, 2),
                "work_ms_avg": round(sum(r[1] + r[2] + r[3] for r in rows) / len(rows) / 1000, 2),
                "achieved_fps": round(rates[len(rates) // 2], 1) if rates else None,
                "achieved_fps_min": round(rates[0], 1) if rates else None})
print(json.dumps(out))
