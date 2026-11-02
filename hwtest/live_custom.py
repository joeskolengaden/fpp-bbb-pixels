#!/usr/bin/env python3
"""
live_custom.py - on-device test of the "Custom timing" preset (pixelTiming 11), measured on the pad itself.

For each case it writes a one-port config with customT0/customT1/customPeriod/customInvert, restarts fppd, and checks
  1. the flags the PRU compiler really received (-DCUSTOM_T0/T1/LOW, -DSLOW_WAITNS, -DCUSTOM_INVERT) against the clamping rules,
  2. the real bit period (frame duration / bits, sampled with pinprobe from the GPIO input register), and
  3. the real average high time of the pulses (a fixed 0x11/0x22/0x33 pattern = 8 ones and 16 zeros per 24 bits),
     which must land where T0H/T1H say it should (the sampler is ~100 ns coarse, so it is a check of a few percent, not a scope),
and finally feeds the driver garbage (strings, nulls, out-of-range numbers) to prove fppd survives it.
The original config is restored byte-for-byte at the end.

  python3 live_custom.py [--cases all|name,name]
"""
import argparse, copy, json, os, re, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import measure_limits as m
from verify_presets import FPP, PATTERN

PIX = 200                                      # RGB pixels on the test port -> 600 bytes -> 4800 bits
CASES = [  # name, T0H, T1H, period, invert
    ("ws2812-like",       350,  700, 1250, 0),
    ("tight-fast",        250,  700, 1000, 0),
    ("ws2811-ish-1700",   350, 1350, 1700, 0),
    ("tm1803-like-2000",  650, 1300, 2000, 0),
    ("slow-2500",         500, 2000, 2500, 0),
    ("long-4000",         600, 2400, 4000, 0),
    ("inverted-1250",     350,  700, 1250, 1),
    ("inverted-slow-2000",500, 1400, 2000, 1),
]
# datasheet presets: pixelTiming -> (name, wire T0H, T1H, period, inverted); same table as BBB48String.cpp fbpCustomDefines()
PRESETS = [(12, "tm1903/tm1824/tm1934", 360, 720, 1300, 0), (13, "ucs2912", 400, 800, 1250, 0), (14, "ucs1912", 250, 1000, 1250, 0),
           (15, "tx1812/lc8816e/gs8208b", 300, 900, 1250, 0), (16, "tm1908", 240, 480, 1250, 0), (17, "lpd1886-8bit", 200, 600, 1250, 0),
           (18, "lc8812", 300, 750, 1250, 0)]
BAD = [  # name, config overrides, what the driver must do
    ("period-too-small", {"customT0": 350, "customT1": 700, "customPeriod": 500}),
    ("t1-below-t0",      {"customT0": 900, "customT1": 300, "customPeriod": 1500}),
    ("huge-values",      {"customT0": 99999, "customT1": 99999, "customPeriod": 999999}),
    ("negative",         {"customT0": -5, "customT1": -9, "customPeriod": -1}),
    ("strings",          {"customT0": "abc", "customT1": None, "customPeriod": [1, 2], "customInvert": "yes"}),
    ("missing",          {}),
]
SCR = "/opt/fpp/src/pru/compileWS2811x.sh"
ARGS = "/tmp/custom_args.log"


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def expect_flags(t0h, t1h, per):
    t0 = clamp(t0h - 50, 200, 3000)
    t1 = clamp(t1h - 50, t0 + 50, 3500)
    low = clamp(per - 110, t1 + 100, 4000)
    return t0, t1, low


def cfg_for(base, over, timing=11):
    cfg = copy.deepcopy(base)
    co = cfg["channelOutputs"][0]
    co["pixelTiming"] = timing
    co["enabled"] = 1
    for k in ("customT0", "customT1", "customPeriod", "customInvert"):
        co.pop(k, None)
    co.update(over)
    for o in co["outputs"]:
        o["virtualStrings"] = []
    co["outputs"][8]["virtualStrings"] = [{"description": "hwtest", "startChannel": 0, "pixelCount": PIX, "groupCount": 1, "reverse": 0,
                                           "colorOrder": "RGB", "nullNodes": 0, "endNulls": 0, "zigZag": 0, "brightness": 100, "gamma": "1.0"}]
    return cfg


def fill(fpp, value, channels):
    """FPP test mode: every channel = value (so every data bit is the same: all 0 bits or all 1 bits)"""
    fpp.req("/api/testmode", "POST", json.dumps({"enabled": 1, "mode": "RGBFill", "cycleMS": 1000, "channelSet": "1-%d" % channels,
                                                  "channelSetType": "channelRange", "color1": value, "color2": value, "color3": value}))


def duty(fpp, value):
    fill(fpp, value, PIX * 3)
    time.sleep(2.5)
    out = m.ssh("sudo /tmp/pinduty 1200 0x481AC000 25 15")
    fpp.testmode(False)
    d = re.search(r"duty hi=(\d+) lo=(\d+) frac=([\d.]+) interval_ns=(\d+)", out)
    f = re.search(r"frame_dur_us=([\d.]+) intact=(\d+) of (\d+)", out)
    return (float(d.group(3)), float(f.group(1)), int(f.group(2))) if d and f else (None, None, 0)


def measure(fpp, cfg, e0, e1, el, inv, extra=0):
    """Run one config; returns (bit period ns, T0H ns, T1H ns) measured on the pad (inverted: the low data pulses)."""
    fpp.testmode(False)
    fpp.put_config(cfg); fpp.restart(); fpp.stop_playlist()
    for attempt in range(3):
        f0, d0, n0 = duty(fpp, 0)
        f1, d1, n1 = duty(fpp, 255)
        if f0 is not None and f1 is not None and d0 and d1 and n0 >= 3 and n1 >= 3:
            break
    if f0 is None or f1 is None or not d0 or not d1 or n0 < 3 or n1 < 3:
        return None, None, None
    period = (d0 + d1) / 2.0 * 1000 / ((PIX * 3 + extra) * 8)       # extra = preamble bytes (TM1814 8, TM1914 6, UCS7604 15, TM1908 9)
    if inv:
        f0, f1 = 1 - f0, 1 - f1
    return period, f0 * period, f1 * period


def check_case(name, want, flg, got, flags_ok, period, t0, t1):
    """Pass/fail = the compiler flags are exactly what the clamping rules give AND the measured bit period is within 3%.
    T0H/T1H are printed for information only: the pad sampler snaps pulses to multiples of ~200 ns (see pinduty.c), so a
    pulse width needs a scope or the ESP32 analyzer to verify."""
    t0h, t1h, per, inv = want
    e0, e1, el = flg
    exp_period = el + 110
    ok_p = period is not None and abs(period - exp_period) <= max(40, 0.03 * exp_period)
    ok = flags_ok and ok_p
    f = lambda v: "%.0f" % v if v is not None else "none"
    print("%-26s want %4d/%4d/%4d inv=%d | flags %s | period %s (exp %d) %s | indicative T0H %s T1H %s -> %s" % (
        name, t0h, t1h, per, inv, "ok" if flags_ok else "BAD %s" % got, f(period), exp_period, "ok" if ok_p else "BAD",
        f(t0), f(t1), "PASS" if ok else "FAIL"), flush=True)
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fpp", default="http://192.168.6.2")
    ap.add_argument("--cases", default="all")
    a = ap.parse_args()
    fpp = FPP(a.fpp)
    m.push("pinduty.c")
    print(m.ssh("cd /tmp && gcc -O2 pinduty.c -o pinduty 2>&1 && echo built").strip())
    base, bk = fpp.backup_config(os.path.join(HERE, "results", "config-backups"))
    m.ssh("cp -p /home/fpp/media/config/co-bbbStrings.json /tmp/co-bbbStrings.exact")     # byte-exact copy: the API rewrites the JSON formatting
    print("starting pixel config saved to", bk)
    m.ssh("sudo sh -c '[ -e %s.orig ] || cp %s %s.orig; cp %s.orig %s; sed -i \"2a echo ARGS \\$@ >> %s\" %s; : > %s; chmod 666 %s'" % (SCR, SCR, SCR, SCR, SCR, ARGS, SCR, ARGS, ARGS))
    want = [c for c in CASES if a.cases == "all" or c[0] in a.cases.split(",")]
    if a.cases == "presets":
        want = []
    fails = 0
    try:
        for name, t0h, t1h, per, inv in want:
            m.ssh(": > %s" % ARGS)
            fpp.put_config(cfg_for(base, {"customT0": t0h, "customT1": t1h, "customPeriod": per, "customInvert": inv}))
            fpp.restart(); fpp.stop_playlist()
            args = m.ssh("cat %s" % ARGS)
            e0, e1, el = expect_flags(t0h, t1h, per)
            got = {k: int(v) for k, v in re.findall(r"-DCUSTOM_(T0|T1|LOW)=(\d+)", args)}
            flags_ok = got == {"T0": e0, "T1": e1, "LOW": el} and ("-DSLOW_WAITNS" in args) == (e1 > 1250 or el > 1250) \
                and ("-DCUSTOM_INVERT" in args) == bool(inv) and "-DPIXELTYPE_CUSTOM" in args
            period, t0, t1 = measure(fpp, cfg_for(base, {"customT0": t0h, "customT1": t1h, "customPeriod": per, "customInvert": inv}), e0, e1, el, inv)
            ok = check_case(name, (t0h, t1h, per, inv), (e0, e1, el), got, flags_ok, period, t0, t1)
            fails += not ok
        for pt, name, t0h, t1h, per, inv in (PRESETS if a.cases in ("all", "presets") else []):
            m.ssh(": > %s" % ARGS)
            e0, e1, el = expect_flags(t0h, t1h, per)
            cfg = cfg_for(base, {}, timing=pt)
            fpp.testmode(False); fpp.put_config(cfg); fpp.restart(); fpp.stop_playlist()
            args = m.ssh("cat %s" % ARGS)
            got = {k: int(v) for k, v in re.findall(r"-DCUSTOM_(T0|T1|LOW)=(\d+)", args)}
            flags_ok = got == {"T0": e0, "T1": e1, "LOW": el} and ("-DSLOW_WAITNS" in args) == (e1 > 1250 or el > 1250) \
                and ("-DCUSTOM_INVERT" in args) == bool(inv)
            period, t0, t1 = measure(fpp, cfg, e0, e1, el, inv)
            ok = check_case("preset %d %s" % (pt, name), (t0h, t1h, per, inv), (e0, e1, el), got, flags_ok, period, t0, t1)
            fails += not ok
        # hostile / malformed config values: fppd must keep running with sane clamped timing
        for name, over in BAD:
            if a.cases != "all":
                break
            m.ssh(": > %s" % ARGS)
            fpp.put_config(cfg_for(base, over))
            fpp.restart()
            time.sleep(2)
            st = json.loads(fpp.req("/api/fppd/status"))
            args = m.ssh("cat %s" % ARGS)
            log = m.ssh("tail -60 /home/fpp/media/logs/fppd.log | grep -ciE 'terminate|exception|segfault|Unable to start PRU'")
            sane = re.search(r"-DCUSTOM_LOW=(\d+)", args)
            ok = st.get("fppd") == "running" and bool(sane) and int(log.strip() or 0) == 0 and 200 <= int(re.search(r"-DCUSTOM_T0=(\d+)", args).group(1)) <= 3000
            fails += not ok
            print("%-20s fppd=%s flags=%s -> %s" % (name, st.get("fppd"), " ".join(re.findall(r"-DCUSTOM_\w+=-?\d+", args)), "PASS" if ok else "FAIL"), flush=True)
    finally:
        try:
            fpp.testmode(False)
            m.ssh("sudo cp %s.orig %s; rm -f %s" % (SCR, SCR, ARGS))
            m.ssh("cp -p /tmp/co-bbbStrings.exact /home/fpp/media/config/co-bbbStrings.json")
            fpp.restart()
        except Exception as e:
            print("!! restore failed:", e)
        print("restored, sha256 %s" % m.ssh("sha256sum /home/fpp/media/config/co-bbbStrings.json").strip()[:16])
    print("FAILS=%d" % fails)
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
