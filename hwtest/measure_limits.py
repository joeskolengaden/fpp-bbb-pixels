#!/usr/bin/env python3
"""
measure_limits.py - measure the real output frame time per chip/pixel count on the board itself.

Drives one port (slot 8 = header P8-30) through FPP, then samples that pad with pinprobe (reads the GPIO
input register - no ESP32/wiring needed) to get the actual frame duration and frame period. Frame duration /
total bits = the true bit period, so the PRU overhead per preset is measured, not assumed, and the maximum
pixels per port at any frame rate follows from  (interval - idle gap) / (bits_per_pixel * bit_period).

  python3 measure_limits.py --case normal-grb --pixels 200,800
  python3 measure_limits.py --all --out results/limits.json
"""
import argparse, copy, json, os, re, statistics, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from verify_presets import (FPP, CASES, expected_wire, case_by_key, order_info, PATTERN, TEST_SLOT)  # noqa: E402

SCR = os.environ.get("FBP_BOARD_DIR") or os.environ.get("BBG_SCRATCH") or os.path.join(os.path.dirname(os.path.abspath(__file__)), ".board")
MAX_VS = 1600                    # FPP UI limit per virtual string; longer ports chain several


def ssh(cmd, timeout=120):
    env = dict(os.environ, BBG_TIMEOUT="45")
    p = subprocess.run([os.path.join(SCR, "bbg"), cmd], capture_output=True, text=True, env=env, timeout=timeout)
    return p.stdout


def push(*names):
    """copy helper scripts from this folder to the board's /tmp (a reboot wipes /tmp, so tests must not assume they are there)"""
    subprocess.run([os.path.join(SCR, "bbgcp")] + [os.path.join(HERE, n) for n in names] + ["fpp@192.168.6.2:/tmp/"],
                   capture_output=True, text=True, check=True, timeout=60)
    ssh("chmod +x " + " ".join("/tmp/" + n for n in names))


def build_cfg(base, timing, order, pixels, ports=1):
    cfg = copy.deepcopy(base)
    co = cfg["channelOutputs"][0]
    co["pixelTiming"] = timing
    co["enabled"] = 1
    for o in co["outputs"]:
        o["virtualStrings"] = []
    src_per, _ = order_info(order)
    vss, left, ch = [], pixels, 0
    while left > 0:
        n = min(MAX_VS, left)
        vss.append({"description": "hwtest%d" % len(vss), "startChannel": ch, "pixelCount": n, "groupCount": 1,
                    "reverse": 0, "colorOrder": order, "nullNodes": 0, "endNulls": 0, "zigZag": 0,
                    "brightness": 100, "gamma": "1.0"})
        ch += n * src_per; left -= n
    slots = [TEST_SLOT] if ports == 1 else list(range(min(ports, len(co["outputs"]))))
    if TEST_SLOT not in slots:
        slots.append(TEST_SLOT)
    for sl in slots:                       # every populated port carries its own copy of the same string set
        co["outputs"][sl]["virtualStrings"] = copy.deepcopy(vss)
    return cfg, ch


def probe(ms=1300, gap_us=100):
    out = ssh("sudo /tmp/pinprobe %d 0x481AC000 25 %d" % (ms, gap_us))
    frames = []
    for m in re.finditer(r"frame (\d+) start=([\d.]+)ms dur=([\d.]+)us rises=(\d+) period=([\d.]+)ms idle=(\d) stalls=(\d+)", out):
        frames.append((float(m.group(3)), float(m.group(5)), int(m.group(7))))
    return frames


def summarize(frames):
    """frames: [(dur_us, period_ms, _)]. The longest frames are the intact ones (see pinprobe.c)."""
    durs = sorted(f[0] for f in frames)
    if len(durs) < 3:
        return None
    top = durs[-max(3, len(durs) // 4):]          # upper quartile = intact frames
    return {"frames": len(durs), "dur_us": statistics.median(top), "dur_min": top[0], "dur_max": durs[-1],
            "period_ms": None}


def measure(fpp, base, key, pixels, ports=1):
    case = case_by_key(key)
    _, label, timing, order, inv, prof, pre, post, sig = case
    cfg, chans = build_cfg(base, timing, order, pixels, ports)
    fpp.put_config(cfg); fpp.restart(); fpp.stop_playlist()
    fpp.testmode(True, chans)
    time.sleep(3)
    frames = probe()
    fpp.testmode(False)
    exp, _ = expected_wire(order, pixels, pre, post)
    nbytes = len(exp) + len(post)
    r = summarize(frames)
    if r:
        r.update(key=key, pixels=pixels, ports=ports, bytes=nbytes, bits=nbytes * 8,
                 bit_period_ns=r["dur_us"] * 1000 / (nbytes * 8))
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fpp", default="http://192.168.6.2")
    ap.add_argument("--case", default="")
    ap.add_argument("--pixels", default="200,800")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--ports", type=int, default=1, help="populate this many PRU outputs (1 = test port only, 48 = all)")
    ap.add_argument("--out")
    a = ap.parse_args()
    fpp = FPP(a.fpp)
    base, _bk = fpp.backup_config(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results', 'config-backups'))
    print('starting config saved to', _bk)
    keys = [c[0] for c in CASES] if a.all else [k for k in a.case.split(",") if k]
    results = []
    try:
        for k in keys:
            for n in [int(x) for x in a.pixels.split(",")]:
                r = measure(fpp, base, k, n, a.ports)
                results.append(r)
                print(json.dumps(r), flush=True)
    finally:
        try:
            fpp.testmode(False); fpp.put_config(base); fpp.restart()
        except Exception as e:
            print("!! restore failed:", e)
        if a.out:
            os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
            json.dump(results, open(a.out, "w"), indent=2)


if __name__ == "__main__":
    main()
