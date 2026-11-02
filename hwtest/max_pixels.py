#!/usr/bin/env python3
"""
max_pixels.py - maximum pixels per port, per IC, from the board's own measurements.

Single-wire (PRU): bit period measured per chip format by measure_limits.py (results/limits-calib.json). A frame
must finish inside the FPP frame interval or the PRU output is cut off mid-frame (measured, see MAX_PIXELS.md):
    (preamble + N*bytes_per_pixel + trailer) * 8 * T_bit  <=  interval - (chip reset + PRU/FPP slack)
Clocked (SPI): throughput measured by spibench (results/spibench.json); the frame must fit the interval the same way.

  python3 max_pixels.py            # prints markdown tables
"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from verify_presets import CASES, expected_wire  # noqa: E402

INTERVALS = [(50, "20 fps"), (40, "25 fps"), (30, "33 fps"), (25, "40 fps"), (20, "50 fps")]
SLACK_US = 200            # measured: output is cut at ~49.8 ms of a 50 ms interval
# chip reset/latch time (us): NeoPixelBus where it has the chip, datasheet-typical (rounded up) otherwise
RESET_US = {"normal-grb": 300, "slow": 300, "apa104": 50, "ws2811-400": 50, "ucs1903-400": 50, "tm1803": 50,
            "tm1814": 200, "tm1829": 200, "ws2805": 300, "tm1914": 200, "ucs7604-8": 300, "ucs7604-16": 300,
            "sk6812-rgbw": 80, "ucs8903-16": 300, "ucs8904-16": 300, "sm16825e": 300, "fw1906": 300,
            "tm1903": 200, "tm1824": 200, "ucs2912": 50, "ucs1912": 50, "tx1812": 300, "lc8816e": 300, "tm1908": 300, "lpd1886": 50, "lc8812": 300}   # the PRU always idles >= 300 us after a frame


def single_wire():
    cal = {r["key"]: r for r in json.load(open(os.path.join(HERE, "results/limits-calib.json"))) if r}
    rows = []
    for key, label, timing, order, inv, prof, pre, post, sig in CASES:
        r = cal.get(key)
        if not r:
            continue
        one, _ = expected_wire(order, 1, pre, post)
        zero, _ = expected_wire(order, 0, pre, post)
        bpp = len(one) - len(zero)
        fixed = len(zero) + len(post)
        tbit = r["dur_max"] * 1000.0 / r["bits"]                       # ns, measured
        row = {"key": key, "label": label, "bpp": bpp, "fixed": fixed, "tbit_ns": tbit,
               "us_per_px": bpp * 8 * tbit / 1000.0, "reset_us": RESET_US[key], "max": {}}
        for ms, _name in INTERVALS:
            budget_bits = (ms * 1000 - RESET_US[key] - SLACK_US) * 1000.0 / tbit
            row["max"][ms] = int((budget_bits / 8 - fixed) // bpp)
        rows.append(row)
    return rows


# --- clocked (SPI) chips -----------------------------------------------------------------------------------
def spi_wire_size(proto, n):             # mirrors plugins/SPIPixels/src/SPIChipFormat.h spiWireSize()
    if proto == "ws2801":
        return n * 3
    if proto in ("apa102", "sk9822", "hd107s", "apa102hd", "sk9822hd", "hd107shd"):
        return 4 + n * 4 + max(4, (n + 15) // 16)
    if proto in ("hd108", "sk9826"):
        return 16 + n * 8 + n // 2 + 4
    if proto == "tlc59711":
        return ((n + 3) // 4) * 28
    if proto == "lpd8806":
        return n * 3 + max(1, (n + 31) // 32)
    if proto == "lpd6803":
        return 4 + n * 2 + max(1, (n + 7) // 8)
    if proto == "p9813":
        return 4 + n * 4 + 4 * max(1, (n + 63) // 64)
    return ((50 + n * 25) + 7) // 8       # sm16716 / sm16726


SPI_CHIPS = [("APA102", "apa102", 8_000_000), ("SK9822", "sk9822", 8_000_000), ("HD107S", "hd107s", 20_000_000),
             ("HD108 / NS108 (16-bit)", "hd108", 20_000_000), ("SK9826 (16-bit)", "sk9826", 10_000_000),
             ("TLC59711 / TLC5971 (4 outputs per chip)", "tlc59711", 1_000_000),
             ("WS2801", "ws2801", 1_000_000), ("LPD8806", "lpd8806", 2_000_000), ("LPD6803", "lpd6803", 1_000_000),
             ("P9813", "p9813", 1_000_000), ("SM16716/SM16726", "sm16716", 16_000_000)]


def spi_time_ms(fit, nbytes, speed):
    nominal = nbytes * 8.0 * 1000.0 / speed
    return fit["k_nominal"] * nominal + fit["ms_per_kb"] * nbytes / 1000.0 + fit["ms_per_chunk"] * (-(-nbytes // 4096))


def spi_max(fit, proto, speed, interval_ms):
    lo, hi = 1, 1_000_000
    while lo < hi:                          # largest n whose frame fits the interval
        mid = (lo + hi + 1) // 2
        if spi_time_ms(fit, spi_wire_size(proto, mid), speed) <= interval_ms:
            lo = mid
        else:
            hi = mid - 1
    return lo


def spi_rows():
    fit = json.load(open(os.path.join(HERE, "results/spi-fit.json")))
    rows = []
    for label, proto, dspeed in SPI_CHIPS:
        r = {"label": label, "proto": proto, "default_hz": dspeed, "default": {}, "at_12mhz": {}, "at_24mhz": {}}
        for ms, _ in INTERVALS:
            r["default"][ms] = spi_max(fit, proto, dspeed, ms)
            r["at_12mhz"][ms] = spi_max(fit, proto, 12_000_000, ms)
            r["at_24mhz"][ms] = spi_max(fit, proto, 24_000_000, ms)
        rows.append(r)
    return rows


def main():
    rows = single_wire()
    print("| IC / format | bytes/px | bit period (measured) | µs/pixel | " + " | ".join("%s (%d ms)" % (n, ms) for ms, n in INTERVALS) + " |")
    print("|---|---|---|---|" + "---|" * len(INTERVALS))
    for r in rows:
        print("| %s | %d | %.0f ns | %.1f | %s |" % (r["label"], r["bpp"], r["tbit_ns"], r["us_per_px"],
                                                   " | ".join("%d" % r["max"][ms] for ms, _ in INTERVALS)))
    json.dump(rows, open(os.path.join(HERE, "results/single-wire-limits.json"), "w"), indent=2)
    print()
    srows = spi_rows()
    hdr = " | ".join("%d ms" % ms for ms, _ in INTERVALS)
    print("| Clocked chip | plugin default clock | at default: " + hdr + " | at 12 MHz: 50 / 25 ms | at 24 MHz: 50 / 25 ms |")
    print("|---|---|" + "---|" * (len(INTERVALS) + 2))
    for r in srows:
        print("| %s | %.0f MHz | %s | %d / %d | %d / %d |" % (r["label"], r["default_hz"] / 1e6,
              " | ".join("%d" % r["default"][ms] for ms, _ in INTERVALS),
              r["at_12mhz"][50], r["at_12mhz"][25], r["at_24mhz"][50], r["at_24mhz"][25]))
    json.dump(srows, open(os.path.join(HERE, "results/spi-limits.json"), "w"), indent=2)


if __name__ == "__main__":
    main()
