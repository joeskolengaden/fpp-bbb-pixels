#!/usr/bin/env python3
"""
verify_spi.py - on-the-wire verification of the SPIPixels plugin with the ESP32-S3
analyzer in SPI mode.

For each clocked chip it writes a SPIPixels output to FPP (co-other.json), restarts
fppd, drives FPP's RGBFill test pattern (11/22/33), captures the real SCLK/MOSI the
BeagleBone puts on the header with the ESP32, and checks (a) the analyzer's own
independent framing decoders (APA102/P9813/WS2801/SM16716 blocks) and (b) the exact
bytes against the chip's documented frame.

The analyzer's SPI capture is GPIO-interrupt based and only reliable to ~200-500 kHz,
so every case runs at spiSpeed=200000 (framing is clock-independent).

Wiring (spidev0.0): P9_22 SCLK -> ESP32 GPIO5, P9_18 MOSI(D1) -> ESP32 GPIO6, GND<->GND.
(spidev1.0 instead: P9_31 SCLK, P9_30 MOSI.)  BeagleBone header pins are 3.3 V logic.

  python3 verify_spi.py --selftest
  python3 verify_spi.py --run all [--device spidev0.0]
"""
import argparse
import copy
import datetime
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "tools", "esp32-led-analyzer"))
from verify_presets import FPP, PATTERN, RGB_IDX, find_analyzer_port, OUTPUT_FILE  # noqa: E402

OTHER_FILE = "co-other.json"
SPEED = 200000
MAX_REPORT_BYTES = 64


# -- documented frames, written from each chip's frame description ---------------
def apa102(px, n):            # start 4x00 | [0xFF, c0,c1,c2] per pixel | end >=4 x FF (1 byte per 16 px)
    out = [0, 0, 0, 0]
    for p in px:
        out += [0xFF] + p
    return out + [0xFF] * max(4, (n + 15) // 16)


def apa102_zero_end(px, n):   # SK9822 / HD107S: same frame, end frame of zeros (FastLED, NeoPixelBus)
    return apa102(px, n)[:-max(4, (n + 15) // 16)] + [0] * max(4, (n + 15) // 16)


def _hd_pixel(p):             # APA102 HD: smallest 5-bit brightness reaching the brightest channel, colours scaled by 31/b
    m = max(p)
    b = (m * 31 + 254) // 255 if m else 1
    return [0xE0 | b] + [min(255, (c * 31 + b // 2) // b) for c in p]


def apa102hd(px, n):
    return [0, 0, 0, 0] + [x for p in px for x in _hd_pixel(p)] + [0xFF] * max(4, (n + 15) // 16)


def sk9822hd(px, n):
    return [0, 0, 0, 0] + [x for p in px for x in _hd_pixel(p)] + [0] * max(4, (n + 15) // 16)


def hd108(px, n):             # Rose Lighting HD108 spec V1.2: 128 zero bits, per LED: 1+3x5-bit gain (all 1) + RGB16, then padding
    out = [0] * 16
    for p in px:
        out += [0xFF, 0xFF]
        for c in p:
            out += [c, c]                                     # 8-bit -> 16-bit by x257
    return out + [0xFF] * (n // 2 + 4)


def tlc59711(px, n):          # TI SBVS181A fig.31 / table 5, assembled bit by bit: per chip 224 bits, last chip first
    out = []
    for c in range((n + 3) // 4 - 1, -1, -1):
        bits = [int(b) for b in "100101"]                     # write command 25h
        bits += [1, 0, 1, 1, 0]                               # OUTTMG EXTGCK TMGRST DSPRPT BLANK
        bits += [1] * 21                                      # BC_B, BC_G, BC_R = 127 (7 bits each)
        for o in (3, 2, 1, 0):                                # GS: OUTB3 OUTG3 OUTR3 ... OUTB0 OUTG0 OUTR0, 16 bits each
            q = 4 * c + o
            for ch in range(3):
                v = px[q][ch] if q < n else 0
                w = v * 257
                bits += [(w >> k) & 1 for k in range(15, -1, -1)]
        assert len(bits) == 224
        out += [int("".join(map(str, bits[i:i + 8])), 2) for i in range(0, 224, 8)]
    return out


def ws2801(px, n):            # raw colour bytes, no framing (latch = idle gap)
    return [b for p in px for b in p]


def lpd8806(px, n):           # 0x80 | 7-bit value, then >=1 zero latch byte per 32 px
    return [0x80 | (b >> 1) for p in px for b in p] + [0] * max(1, (n + 31) // 32)


def lpd6803(px, n):           # start 4x00 | 0x8000 + 5 bits per channel | zero end, 1 clock per px (ceil(n/8) bytes)
    out = [0, 0, 0, 0]
    for c0, c1, c2 in px:
        v = 0x8000 | ((c0 >> 3) << 10) | ((c1 >> 3) << 5) | (c2 >> 3)
        out += [v >> 8, v & 0xFF]
    return out + [0] * max(1, (n + 7) // 8)


def p9813(px, n):             # start 4x00 | [flag, c0,c1,c2] | end 4 bytes zero per 64 px
    out = [0, 0, 0, 0]
    for c0, c1, c2 in px:
        flag = 0xC0 | ((~c0 & 0xC0) >> 2) | ((~c1 & 0xC0) >> 4) | ((~c2 & 0xC0) >> 6)
        out += [flag, c0, c1, c2]
    return out + [0] * (4 * max(1, (n + 63) // 64))


def sm16716(px, n):           # 50 zero bits | per pixel: '1' + 24 bits MSB-first | zero padded to a byte
    bits = [0] * 50
    for p in px:
        bits.append(1)
        for c in p:
            bits += [(c >> k) & 1 for k in range(7, -1, -1)]
    while len(bits) % 8:
        bits.append(0)
    return [int("".join(map(str, bits[i:i + 8])), 2) for i in range(0, len(bits), 8)]


# key, label, plugin protocol, colorOrder, framer, analyzer block (independent decoder) or None
CASES = [
    ("apa102", "APA102 / DotStar",       "apa102",  "BGR", apa102,   "APA102/SK9822/HD107S"),
    ("sk9822", "SK9822",                 "sk9822",  "BGR", apa102_zero_end, "APA102/SK9822/HD107S"),
    ("hd107s", "HD107S",                 "hd107s",  "BGR", apa102_zero_end, "APA102/SK9822/HD107S"),
    ("apa102hd", "APA102 HD mode",       "apa102hd", "BGR", apa102hd, None),
    ("sk9822hd", "SK9822 HD mode",       "sk9822hd", "BGR", sk9822hd, None),
    ("hd108",  "HD108 / NS108 (16-bit)", "hd108",   "RGB", hd108,    None),
    ("sk9826", "Opsco SK9826 (= HD108 frame)", "sk9826", "GRB", hd108, None),
    ("sk9826mini", "SK9826MINI",         "sk9826mini", "GRB", hd108, None),
    ("tlc59711", "TI TLC59711 / TLC5971", "tlc59711", "BGR", tlc59711, None),
    ("apa107", "APA107 (= APA102 frame)", "apa107", "BGR", apa102,   None),
    ("lc8822", "LC8822 (APA102-compatible)", "lc8822", "BGR", apa102,  None),
    ("lc8823", "LC8823 (APA102-compatible)", "lc8823", "BGR", apa102,  None),
    ("ws2801", "WS2801",                 "ws2801",  "RGB", ws2801,   None),
    ("lpd8806", "LPD8806",               "lpd8806", "GRB", lpd8806,  None),
    ("lpd6803", "LPD6803",               "lpd6803", "RGB", lpd6803,  None),
    ("p9813",  "P9813 / Total Control",  "p9813",   "BGR", p9813,    "P9813"),
    ("sm16716", "SM16716",               "sm16716", "RGB", sm16716,  "SM16716/SM16726"),
    ("sm16726", "SM16726",               "sm16726", "RGB", sm16716,  "SM16716/SM16726"),
]


def pixels_for(order, n):
    """n pixels of source RGB (pattern 11/22/33 continuing across pixels) permuted to colour order."""
    src = [PATTERN[k % 3] for k in range(n * 3)]
    px = []
    for p in range(n):
        s = src[p * 3:p * 3 + 3]
        px.append([s[RGB_IDX[c]] for c in order])
    return px


def expected(case, n):
    return case[4](pixels_for(case[3], n), n)


def pick_n(case, want):
    n = want
    while n > 1 and len(expected(case, n)) > MAX_REPORT_BYTES:
        n -= 1
    return n


def case_by_key(k):
    for c in CASES:
        if c[0] == k:
            return c
    raise KeyError(k)


def capture_spi(port, seconds):
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
        ser.write(b"2")
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


def evaluate(case, n, frames):
    key, label, proto, order, framer, block = case
    exp = expected(case, n)
    checks = []

    def chk(name, ok, detail=""):
        checks.append({"check": name, "ok": bool(ok), "detail": detail})

    chk("frames captured (>=3)", len(frames) >= 3, "%d frames" % len(frames))
    if not frames:
        return checks, {}
    # most frames carry the whole burst; pick the modal one
    f0 = max(frames, key=lambda f: sum(1 for g in frames if g.get("bytes_hex") == f.get("bytes_hex")))
    got = [int(t, 16) for t in f0.get("bytes_hex", "").split() if re.fullmatch(r"[0-9A-Fa-f]{2}", t)]
    want = exp[:MAX_REPORT_BYTES]
    chk("frame length %d bytes" % len(exp), f0.get("byte_count") == len(exp), "got %s" % f0.get("byte_count"))
    chk("wire bytes identical to documented frame", got == want,
        "expected %s | got %s" % (" ".join("%02X" % b for b in want), " ".join("%02X" % b for b in got)))
    if block:
        info = f0.get("spi_checks", {}).get(block, {})
        bad = [k for k, v in info.items() if ("MISSING" in v or "WRONG" in v)]
        chk("analyzer's own %s decoder: framing OK" % block, bool(info) and not bad, "flags: %s" % (bad or "none"))
        px = [v for k, v in info.items() if k.startswith("pixel frames found")]
        if px:
            m = re.match(r"\s*(\d+)", px[0])
            chk("analyzer decodes %d pixels" % n, bool(m) and int(m.group(1)) == n, "decoded %s" % px[0])
    same = sum(1 for f in frames if f.get("bytes_hex") == f0.get("bytes_hex"))
    chk("steady output (>=90%% identical frames)", same >= 0.9 * len(frames), "%d/%d identical" % (same, len(frames)))
    return checks, {"got": got, "expected": exp, "frames": len(frames)}


def run(a):
    port = a.port or find_analyzer_port()
    if not port:
        sys.exit("no ESP32 analyzer serial port found - pass --port")
    fpp = FPP(a.fpp)
    keys = [c[0] for c in CASES] if a.run == "all" else a.run.split(",")
    orig_strings = fpp.get_config()
    try:
        orig_other = fpp.req("/api/configfile/" + OTHER_FILE)
        orig_other = orig_other if orig_other.lstrip().startswith("{") else None
    except Exception:
        orig_other = None
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    outdir = os.path.join(HERE, "results")
    os.makedirs(outdir, exist_ok=True)
    json.dump(orig_strings, open(os.path.join(outdir, "spi-original-strings-%s.json" % stamp), "w"), indent=2)
    results = []
    try:
        off = copy.deepcopy(orig_strings)
        off["channelOutputs"][0]["enabled"] = 0       # isolate: only SPIPixels drives anything
        fpp.put_config(off)
        for k in keys:
            case = case_by_key(k)
            key, label, proto, order, framer, block = case
            n = pick_n(case, a.pixels)
            print("\n=== %s [%s on %s, %d px, %d Hz] ===" % (label, proto, a.device, n, SPEED), flush=True)
            cfg = {"channelOutputs": [{"type": "SPIPixels", "enabled": 1, "startChannel": 1, "channelCount": n * 3,
                                       "outputs": [{"device": a.device, "protocol": proto, "spiSpeed": SPEED, "portNumber": 0,
                                                    "virtualStrings": [{"description": "hwtest", "startChannel": 0, "pixelCount": n,
                                                                        "groupCount": 0, "reverse": 0, "colorOrder": order,
                                                                        "nullNodes": 0, "endNulls": 0, "zigZag": 0,
                                                                        "brightness": 100, "gamma": "1.0"}]}]}]}
            fpp.req("/api/configfile/" + OTHER_FILE, "POST", json.dumps(cfg, indent=2))
            fpp.restart()
            fpp.stop_playlist()
            fpp.testmode(True, n * 3)
            time.sleep(a.settle)
            frames = capture_spi(port, a.capture)
            fpp.testmode(False)
            checks, info = evaluate(case, n, frames)
            for c in checks:
                print("  %-4s %-48s %s" % ("PASS" if c["ok"] else "FAIL", c["check"], "" if c["ok"] else c["detail"]), flush=True)
            results.append({"key": key, "label": label, "ok": all(c["ok"] for c in checks), "checks": checks, "pixels": n})
    finally:
        print("\nrestoring original FPP config ...", flush=True)
        try:
            fpp.testmode(False)
            fpp.put_config(orig_strings)
            if orig_other is not None:
                fpp.req("/api/configfile/" + OTHER_FILE, "POST", orig_other)
            else:
                try:
                    fpp.req("/api/configfile/" + OTHER_FILE, "DELETE")
                except Exception:
                    pass
            fpp.restart()
        except Exception as e:
            print("!! restore failed (%s); original strings config saved in results/" % e)
    base = os.path.join(outdir, "spi-report-%s" % stamp)
    json.dump(results, open(base + ".json", "w"), indent=2)
    lines = ["# SPIPixels on-the-wire verification", "",
             "%d/%d chips passed" % (sum(r["ok"] for r in results), len(results)), "",
             "| Chip | Result | failed checks |", "|---|---|---|"]
    for r in results:
        lines.append("| %s | %s | %s |" % (r["label"], "PASS" if r["ok"] else "**FAIL**",
                                           "; ".join(c["check"] for c in r["checks"] if not c["ok"]) or "-"))
    open(a.report or base + ".md", "w").write("\n".join(lines) + "\n")
    print("\n" + "\n".join(lines))
    return 0 if all(r["ok"] for r in results) else 1


def selftest():
    bad = 0

    def eq(name, got, want):
        nonlocal bad
        ok = got == want
        bad += not ok
        print("%-5s %s%s" % ("ok" if ok else "FAIL", name, "" if ok else "\n   got  %s\n   want %s" % (got, want)))

    # worked examples straight from the chips' frame descriptions
    eq("apa102 2px", apa102([[0x33, 0x22, 0x11], [0x33, 0x22, 0x11]], 2),
       [0, 0, 0, 0, 0xFF, 0x33, 0x22, 0x11, 0xFF, 0x33, 0x22, 0x11, 0xFF, 0xFF, 0xFF, 0xFF])
    eq("ws2801 raw", ws2801([[1, 2, 3]], 1), [1, 2, 3])
    eq("lpd8806 7-bit", lpd8806([[0xFF, 0x00, 0x22]], 1), [0xFF, 0x80, 0x91, 0x00])
    eq("lpd6803 15-bit", lpd6803([[0xF8, 0x00, 0x00]], 1), [0, 0, 0, 0, 0xFC, 0x00, 0x00])
    # P9813: c=[0x11,0x22,0x33] -> top2 bits all 0 -> inverted = 11 -> flag = 0xC0|0x30|0x0C|0x03 = 0xFF
    eq("p9813 flag", p9813([[0x11, 0x22, 0x33]], 1), [0, 0, 0, 0, 0xFF, 0x11, 0x22, 0x33, 0, 0, 0, 0])
    sm = sm16716([[0xFF, 0x00, 0x00]], 1)          # 50 zeros + 1 + 8 ones + 16 zeros = 75 bits -> 10 bytes
    eq("sm16716 length", len(sm), 10)
    eq("sm16716 start bits all zero (first 6 bytes + 2 bits)", sm[:6] + [sm[6] >> 6], [0] * 6 + [0])
    eq("sm16716 marker at bit 50", (sm[6] >> 5) & 1, 1)
    for c in CASES:
        n = pick_n(c, 6)
        ok = 1 <= n and len(expected(c, n)) <= MAX_REPORT_BYTES
        bad += not ok
        print("%-5s %-8s %d px -> %d wire bytes" % ("ok" if ok else "FAIL", c[0], n, len(expected(c, n))))
    print("\nSELFTEST", "PASSED" if bad == 0 else "FAILED (%d)" % bad)
    return bad


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fpp", default="http://192.168.6.2")
    ap.add_argument("--port")
    ap.add_argument("--device", default="spidev0.0")
    ap.add_argument("--run", default="")
    ap.add_argument("--pixels", type=int, default=6)
    ap.add_argument("--settle", type=float, default=5.0)
    ap.add_argument("--capture", type=float, default=4.0)
    ap.add_argument("--report")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(1 if selftest() else 0)
    if a.list:
        for c in CASES:
            print("%-8s %-10s order=%s  %s" % (c[0], c[2], c[3], c[1]))
        return
    if not a.run:
        ap.error("need --run all|key[,key...] (or --selftest / --list)")
    sys.exit(run(a))


if __name__ == "__main__":
    main()
