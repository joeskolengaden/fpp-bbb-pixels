#!/usr/bin/env python3
"""
verify_presets.py - on-the-wire verification of fpp-bbb-pixels using the ESP32-S3
LED signal analyzer (tools/esp32-led-analyzer).

For each chip case it (1) writes a minimal BBB48String config to a live FPP over
its HTTP API, (2) restarts fppd, (3) drives a KNOWN channel pattern with FPP's own
test mode (RGBFill 11/22/33), (4) lets the ESP32 capture what the BeagleBone's PRU
really puts on the pin, and (5) compares polarity, timing profile, preamble /
trailer, byte count and every byte against an expectation derived from the
documented chip format (CONFIG.md / patch comments) - NOT from reading the code's
own output back, so a bug in the patchers shows up as a FAIL, not a tautology.

Wiring (single-wire): BBB header pin of the test port -> ESP32 GPIO4, GND <-> GND.
A bare BeagleBone header pin is 3.3 V logic, which the ESP32-S3 tolerates; if a
cape with 5 V buffers is fitted, use the divider described in the analyzer README.

  python3 verify_presets.py --selftest                 # offline: expectation logic
  python3 verify_presets.py --list
  python3 verify_presets.py --run all --report out.md  # needs board + ESP32
"""
import argparse
import copy
import datetime
import glob
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ANALYZER = os.path.join(HERE, "..", "..", "tools", "esp32-led-analyzer")
sys.path.insert(0, ANALYZER)

PATTERN = (0x11, 0x22, 0x33)          # RGBFill colours -> distinct bytes, easy to read
TEST_SLOT = 8                          # BBB48String slot 8 = WL48 "port 9" = header P8-30
OUTPUT_FILE = "co-bbbStrings.json"
MAX_REPORT_BYTES = 64                  # analyzer prints at most the first 64 bytes
RGB_IDX = {"R": 0, "G": 1, "B": 2}

# --------------------------------------------------------------------------
# Chip cases. preamble/trailer are the documented literal frames.
# profile  = substring of the analyzer's timing-profile name that must match
# sig      = substring of the analyzer's signature name that must be found
# --------------------------------------------------------------------------
TM1814_PRE = [0x3F, 0x3F, 0x3F, 0x3F, 0xC0, 0xC0, 0xC0, 0xC0]
TM1914_PRE = [0xFF, 0xFF, 0xF5, 0x00, 0x00, 0x0A]
TM1908_PRE = [0xFF, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0x7F, 0x7F, 0x7F]     # C1 FF FF FF, C2 00 00 00 (auto-switch), C3 = 25 mA per channel
UCS7604_PRE = lambda cfg: [0xFF] * 6 + [0x00, 0x02, cfg, 0x08, 0x08, 0x08, 0x08, 0x00, 0x00]


def sm16825e_trailer(g=5):
    """4-byte current-gain frame: 5x5-bit gains MSB-first, 2 action bits (00), 5 ones."""
    bits = 0
    for _ in range(5):
        bits = (bits << 5) | g
    bits = (bits << 2) | 0b00
    bits = (bits << 5) | 0b11111
    return list(bits.to_bytes(4, "big"))


CASES = [
    # key, label, pixelTiming, colorOrder, inverted, profile, preamble, trailer, sig
    ("normal-grb",  "WS2812/WS2811-800 (Normal, GRB)", 0, "GRB",     False, "Normal/WS281x", [], [], None),
    ("slow",        "ws281x Slow variant",              1, "RGB",     False, "Normal/WS281x", [], [], None),
    ("apa104",      "APA104/PL9823/SK6822",             2, "RGB",     False, "APA104",        [], [], None),
    ("ws2811-400",  "WS2811 @ 400 Kbps",                3, "RGB",     False, "WS2811 400",    [], [], None),
    ("ucs1903-400", "UCS1903/UCS2903 @ 400 Kbps",       4, "RGB",     False, "UCS1903",       [], [], None),
    ("tm1803",      "TM1803",                           5, "RGB",     False, "TM1803",        [], [], None),
    ("tm1814",      "TM1814 RGBW (inverted)",           6, "WRGB",    True,  "TM1814",        TM1814_PRE, [], "TM1814"),
    ("tm1829",      "TM1829 RGB (inverted)",            7, "RGB",     True,  "TM1829",        [], [], None),
    ("ws2805",      "WS2805 RGB+WW+CW (5ch)",           8, "RGBWC",   False, "WS2805",        [], [], None),
    ("tm1914",      "TM1914 RGB (inverted)",            9, "RGB",     True,  "TM1914",        TM1914_PRE, [], "TM1914"),
    ("ucs7604-8",   "UCS7604 RGBW 8-bit",              10, "RGBW",    False, "Normal/WS281x", UCS7604_PRE(0x03), [], "UCS7604"),
    ("ucs7604-16",  "UCS7604 RGBW 16-bit",             10, "RGBW16",  False, "Normal/WS281x", UCS7604_PRE(0x8B), [], "UCS7604"),
    ("sk6812-rgbw", "SK6812/WS2814 RGBW (GRBW)",        0, "GRBW",    False, "Normal/WS281x", [], [], None),
    ("ucs8903-16",  "UCS8903 16-bit RGB",               0, "RGB16",   False, "Normal/WS281x", [], [], None),
    ("ucs8904-16",  "UCS8904 16-bit RGBW",              0, "RGBW16",  False, "Normal/WS281x", [], [], None),
    ("sm16825e",    "SM16825E 16-bit RGBWC + trailer",  0, "RGBWC16", False, "Normal/WS281x", [], sm16825e_trailer(5), "SM16825E"),
    ("fw1906",      "FW1906 6ch (RGBCWX)",              0, "RGBCWX",  False, "Normal/WS281x", [], [], None),
    # datasheet presets 12-18 (profile "-" = no analyzer profile exists for them; pulses are not checked by the ESP32 path)
    ("tm1903",      "TM1903 / TM1934 RGB (800 kHz)",   12, "RGB",     False, "-", [], [], None),
    ("tm1824",      "TM1824 RGBW",                     12, "RGBW",    False, "-", [], [], None),
    ("ucs2912",     "UCS2912 12-ch driver",            13, "RGB",     False, "-", [], [], None),
    ("ucs1912",     "UCS1912 12-ch driver",            14, "RGB",     False, "-", [], [], None),
    ("tx1812",      "TX1812 / TX1818 / GS8208B (GRB)", 15, "GRB",     False, "-", [], [], None),
    ("lc8816e",     "LC8816E RGBW (GRBW)",             15, "GRBW",    False, "-", [], [], None),
    ("tm1908",      "TM1908 RGB + 9-byte header",      16, "RGB",     False, "-", TM1908_PRE, [], None),
    ("lpd1886",     "LPD1886 8-bit",                   17, "RGB",     False, "-", [], [], None),
    ("lc8812",      "LC8812 / LC8812B (GRB)",          18, "GRB",     False, "-", [], [], None),
]


def case_by_key(k):
    for c in CASES:
        if c[0] == k:
            return c
    raise KeyError(k)


# --------------------------------------------------------------------------
# Expectation model (documented FPP colour-order semantics)
# --------------------------------------------------------------------------
def order_info(order):
    """-> (src_channels_per_pixel, wire_fn(src_list)->wire_list)"""
    sixteen = order.endswith("16")
    o = order[:-2] if sixteen else order
    n = len(o)
    if n == 3:
        def wire(src):
            return [src[RGB_IDX[c]] for c in o]
    elif n == 4 and o[0] == "W":                 # W-first: source is [W,R,G,B]
        def wire(src):
            return [src[0]] + [src[1 + RGB_IDX[c]] for c in o[1:]]
    elif n == 4:                                 # W-last: source is [R,G,B,W]
        def wire(src):
            return [src[RGB_IDX[c]] for c in o[:3]] + [src[3]]
    elif n in (5, 6):                            # first 3 = RGB order, extras positional
        def wire(src):
            return [src[RGB_IDX[c]] for c in o[:3]] + list(src[3:n])
    else:
        raise ValueError("unsupported colour order " + order)
    if sixteen:
        base = wire
        def wire(src):                           # each 8-bit value -> 2 bytes (x257)
            out = []
            for b in base(src):
                out += [b, b]
            return out
    return n, wire


def expected_wire(order, pixels, preamble, trailer):
    src_per, wire = order_info(order)
    chans = [PATTERN[k % 3] for k in range(pixels * src_per)]
    body = []
    for p in range(pixels):
        body += wire(chans[p * src_per:(p + 1) * src_per])
    return preamble + body, src_per


def pick_pixels(order, preamble, trailer, want):
    """Largest pixel count <= want that keeps the whole frame within the report's 64 bytes."""
    _, w = order_info(order)
    per = len(w(list(range(8))))
    room = MAX_REPORT_BYTES - len(preamble) - len(trailer)
    return max(1, min(want, room // per))


# --------------------------------------------------------------------------
# FPP access
# --------------------------------------------------------------------------
class FPP:
    def __init__(self, base):
        self.base = base.rstrip("/")

    def req(self, path, method="GET", body=None, timeout=20):
        data = None if body is None else (body if isinstance(body, bytes) else body.encode())
        r = urllib.request.Request(self.base + path, data=data, method=method)
        if data is not None:
            r.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.read().decode("utf-8", "replace")

    def get_config(self):
        return json.loads(self.req("/api/configfile/" + OUTPUT_FILE))

    def backup_config(self, outdir):
        """Save the board's current pixel config under outdir/original-<hash>.json (once per distinct content) BEFORE a test
        rewrites it, so the real layout can always be recovered, whatever state a previous run left behind."""
        import hashlib
        cfg = self.get_config()
        raw = json.dumps(cfg, indent=2, sort_keys=True)
        h = hashlib.sha256(raw.encode()).hexdigest()[:10]
        os.makedirs(outdir, exist_ok=True)
        p = os.path.join(outdir, "original-%s.json" % h)
        if not os.path.exists(p):
            open(p, "w").write(raw)
        return cfg, p

    def put_config(self, cfg):
        out = json.loads(self.req("/api/configfile/" + OUTPUT_FILE, "POST", json.dumps(cfg, indent=2)))
        if out.get("Status") != "OK":
            raise RuntimeError("config write failed: %s" % out)

    def restart(self, wait=90):
        self.req("/api/system/fppd/restart")
        time.sleep(4)
        end = time.time() + wait
        while time.time() < end:
            try:
                st = json.loads(self.req("/api/fppd/status", timeout=5))
                if st.get("fppd") == "running":
                    return True
            except Exception:
                pass
            time.sleep(2)
        raise RuntimeError("fppd did not come back after restart")

    def stop_playlist(self):
        try:
            self.req("/api/playlists/stop")
        except Exception:
            pass

    def testmode(self, enabled, channels=0):
        body = {"enabled": 1 if enabled else 0, "mode": "RGBFill", "cycleMS": 1000,
                "channelSet": "1-%d" % max(channels, 1), "channelSetType": "channelRange",
                "color1": PATTERN[0], "color2": PATTERN[1], "color3": PATTERN[2]}
        self.req("/api/testmode", "POST", json.dumps(body))


def build_config(base_cfg, timing, order, pixels):
    cfg = copy.deepcopy(base_cfg)
    co = cfg["channelOutputs"][0]
    co["pixelTiming"] = timing
    co["enabled"] = 1
    for o in co["outputs"]:
        o["virtualStrings"] = []
    co["outputs"][TEST_SLOT]["virtualStrings"] = [{
        "description": "hwtest", "startChannel": 0, "pixelCount": pixels, "groupCount": 1,
        "reverse": 0, "colorOrder": order, "nullNodes": 0, "endNulls": 0,
        "zigZag": 0, "brightness": 100, "gamma": "1.0"}]
    return cfg


# --------------------------------------------------------------------------
# ESP32 analyzer access
# --------------------------------------------------------------------------
def find_analyzer_port():
    cands = sorted(glob.glob("/dev/cu.usbmodem*") + glob.glob("/dev/cu.usbserial*"))
    return cands[0] if cands else None


def capture(port, seconds):
    import serial
    from frame_parser import FrameAccumulator
    ser = serial.Serial(port, 115200, timeout=0.3)
    try:
        ser.dtr = False; ser.rts = True; time.sleep(0.1); ser.rts = False; time.sleep(0.1); ser.dtr = True
        end = time.time() + 8
        buf = b""
        while time.time() < end and b"Send 1 or 2" not in buf:
            buf += ser.read(256)
        ser.reset_input_buffer()
        ser.write(b"1")
        acc, frames, buf = FrameAccumulator(), [], b""
        end = time.time() + seconds
        while time.time() < end:
            chunk = ser.read(512)
            if not chunk:
                continue
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                f = acc.feed(line.decode("utf-8", "replace").rstrip("\r"))
                if f is not None:
                    frames.append(f)
        ser.write(b"x")
        return frames
    finally:
        ser.close()


def num(raw, key):
    m = re.search(r"^%s\s*:\s*~(\d+)ns" % key, raw, re.M)
    return int(m.group(1)) if m else None


# --------------------------------------------------------------------------
# Evaluate one case
# --------------------------------------------------------------------------
def evaluate(case, pixels, frames):
    key, label, timing, order, inv, profile, pre, post, sig = case
    exp, _ = expected_wire(order, pixels, pre, post)
    exp_full = exp + post
    checks, info = [], {}

    def chk(name, ok, detail=""):
        checks.append({"check": name, "ok": bool(ok), "detail": detail})

    chk("frames captured (>=3)", len(frames) >= 3, "%d frames" % len(frames))
    if not frames:
        return checks, info
    f0 = frames[len(frames) // 2]
    got_hex = [int(t, 16) for t in f0.get("bytes_hex", "").split() if re.fullmatch(r"[0-9A-Fa-f]{2}", t)]
    info.update(frames=len(frames), byte_count=f0.get("byte_count"), got=got_hex, expected=exp_full,
                T0=num(f0["raw_text"], r"T0[HL]"), T1=num(f0["raw_text"], r"T1[HL]"),
                period=num(f0["raw_text"], "period"), timing_matches=f0.get("timing_matches"),
                signatures=[s["name"] for s in f0.get("signature_matches", [])])
    chk("polarity %s" % ("inverted" if inv else "normal"), f0.get("inverted") == inv, f0.get("polarity_raw", ""))
    chk("timing profile ~ '%s'" % profile, any(profile in m for m in f0.get("timing_matches", [])),
        "matched: %s" % f0.get("timing_matches"))
    chk("frame length %d bytes" % len(exp_full), f0.get("byte_count") == len(exp_full),
        "got %s" % f0.get("byte_count"))
    chk("wire bytes identical to expected", got_hex == exp_full[:len(got_hex)] and len(got_hex) == min(len(exp_full), MAX_REPORT_BYTES),
        "expected %s | got %s" % (" ".join("%02X" % b for b in exp_full[:MAX_REPORT_BYTES]),
                                  " ".join("%02X" % b for b in got_hex)))
    if sig:
        chk("signature '%s' found" % sig, any(sig in s for s in info["signatures"]), "found: %s" % info["signatures"])
    same = sum(1 for f in frames if f.get("bytes_hex") == f0.get("bytes_hex"))
    chk("steady output (>=90%% identical frames)", same >= 0.9 * len(frames), "%d/%d identical" % (same, len(frames)))
    return checks, info


def run(args):
    port = args.port or find_analyzer_port()
    if not port:
        sys.exit("no ESP32 analyzer serial port found - pass --port")
    fpp = FPP(args.fpp)
    keys = [c[0] for c in CASES] if args.run == "all" else args.run.split(",")
    original = fpp.get_config()
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    outdir = os.path.join(HERE, "results")
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "original-%s.json" % stamp), "w") as f:
        json.dump(original, f, indent=2)
    results = []
    try:
        for k in keys:
            case = case_by_key(k)
            _, label, timing, order, inv, profile, pre, post, sig = case
            pixels = pick_pixels(order, pre, post, args.pixels)
            src_per, _ = order_info(order)
            print("\n=== %s  [pixelTiming=%d order=%s px=%d] ===" % (label, timing, order, pixels), flush=True)
            fpp.put_config(build_config(original, timing, order, pixels))
            fpp.restart()
            fpp.stop_playlist()
            fpp.testmode(True, pixels * src_per)
            time.sleep(args.settle)
            frames = capture(port, args.capture)
            fpp.testmode(False)
            checks, info = evaluate(case, pixels, frames)
            ok = all(c["ok"] for c in checks)
            for c in checks:
                print("  %-4s %-40s %s" % ("PASS" if c["ok"] else "FAIL", c["check"], "" if c["ok"] else c["detail"]), flush=True)
            if info:
                print("  measured T0=%sns T1=%sns period=%sns" % (info.get("T0"), info.get("T1"), info.get("period")), flush=True)
            results.append({"key": k, "label": label, "ok": ok, "pixels": pixels, "pixelTiming": timing,
                            "order": order, "checks": checks, "info": {x: y for x, y in info.items() if x != "got"}})
    finally:
        print("\nrestoring original FPP config ...", flush=True)
        try:
            fpp.testmode(False)
            fpp.put_config(original)
            fpp.restart()
        except Exception as e:
            print("!! restore failed (%s) - original saved in results/original-%s.json" % (e, stamp))
    write_report(results, os.path.join(outdir, "report-%s" % stamp), args.report)
    return 0 if all(r["ok"] for r in results) else 1


def write_report(results, base, md_path):
    with open(base + ".json", "w") as f:
        json.dump(results, f, indent=2)
    lines = ["# fpp-bbb-pixels on-the-wire verification", "",
             "Run: %s - %d/%d chip cases passed" % (datetime.datetime.now().isoformat(timespec="seconds"),
                                                   sum(r["ok"] for r in results), len(results)), "",
             "| Case | Result | pixelTiming | order | T0/T1/period (ns) | failed checks |", "|---|---|---|---|---|---|"]
    for r in results:
        i = r["info"]
        bad = "; ".join(c["check"] for c in r["checks"] if not c["ok"]) or "-"
        lines.append("| %s | %s | %d | %s | %s/%s/%s | %s |" % (
            r["label"], "PASS" if r["ok"] else "**FAIL**", r["pixelTiming"], r["order"],
            i.get("T0"), i.get("T1"), i.get("period"), bad))
    text = "\n".join(lines) + "\n"
    with open(md_path or base + ".md", "w") as f:
        f.write(text)
    print("\n" + text)


# --------------------------------------------------------------------------
# Offline self-test of the expectation model
# --------------------------------------------------------------------------
def selftest():
    s = [0x11, 0x22, 0x33, 0x44, 0x55, 0x66]
    cases = [
        ("RGB",     s[:3], [0x11, 0x22, 0x33]),
        ("GRB",     s[:3], [0x22, 0x11, 0x33]),
        ("BGR",     s[:3], [0x33, 0x22, 0x11]),
        ("GRBW",    s[:4], [0x22, 0x11, 0x33, 0x44]),     # W-last, W=src[3]
        ("WRGB",    s[:4], [0x11, 0x22, 0x33, 0x44]),     # W-first, source is [W,R,G,B]
        ("WGRB",    s[:4], [0x11, 0x33, 0x22, 0x44]),
        ("RGBWC",   s[:5], [0x11, 0x22, 0x33, 0x44, 0x55]),
        ("RGBCWX",  s[:6], [0x11, 0x22, 0x33, 0x44, 0x55, 0x66]),
        ("RGB16",   s[:3], [0x11, 0x11, 0x22, 0x22, 0x33, 0x33]),
        ("RGBW16",  s[:4], [0x11, 0x11, 0x22, 0x22, 0x33, 0x33, 0x44, 0x44]),
        ("RGBWC16", s[:5], [0x11, 0x11, 0x22, 0x22, 0x33, 0x33, 0x44, 0x44, 0x55, 0x55]),
    ]
    bad = 0
    for order, src, want in cases:
        n, wire = order_info(order)
        got = wire(src[:n])
        ok = got == want
        bad += not ok
        print("%-5s %-8s %s" % ("ok" if ok else "FAIL", order, "" if ok else "got %s want %s" % (got, want)))
    t = sm16825e_trailer(5)
    ok = t == [0x29, 0x4A, 0x52, 0x9F]
    bad += not ok
    print("%-5s SM16825E trailer(g=5) = %s" % ("ok" if ok else "FAIL", " ".join("%02X" % b for b in t)))
    for key, label, timing, order, inv, profile, pre, post, sig in CASES:
        px = pick_pixels(order, pre, post, 6)
        exp, _ = expected_wire(order, px, pre, post)
        ok = len(exp) + len(post) <= MAX_REPORT_BYTES and px >= 1
        bad += not ok
        print("%-5s %-12s %d px -> %2d wire bytes" % ("ok" if ok else "FAIL", key, px, len(exp) + len(post)))
    print("\nSELFTEST", "PASSED" if bad == 0 else "FAILED (%d)" % bad)
    return bad


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fpp", default="http://192.168.6.2")
    ap.add_argument("--port", help="ESP32 analyzer serial port (default: first /dev/cu.usbmodem*)")
    ap.add_argument("--run", default="", help="'all' or comma list of case keys")
    ap.add_argument("--pixels", type=int, default=6, help="pixels per test string (capped to fit 64 bytes)")
    ap.add_argument("--settle", type=float, default=6.0, help="seconds after enabling test mode before capture")
    ap.add_argument("--capture", type=float, default=4.0, help="capture seconds per case")
    ap.add_argument("--report", help="markdown report path")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(1 if selftest() else 0)
    if a.list:
        for c in CASES:
            print("%-12s timing=%-2d order=%-8s %s" % (c[0], c[2], c[3], c[1]))
        return
    if not a.run:
        ap.error("need --run all|key[,key...] (or --selftest / --list)")
    sys.exit(run(a))


if __name__ == "__main__":
    main()
