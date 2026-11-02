#!/usr/bin/env python3
"""live_chip_current.py - end to end: config file -> fppd -> BBB48String -> PixelString -> bytes in the PRU buffer.
Sets chipCurrent / tm1914Mode in the real output config, restarts fppd, and scans the PRU output window (read-only) for the
expected preamble/trailer bytes. Restores the board's config byte-for-byte afterwards."""
import json, sys, time, copy
sys.path.insert(0, ".")
import measure_limits as m
from verify_presets import FPP

CASES = [  # label, pixelTiming, order, extra output keys, expected byte pattern (hex) found at the start/end of the port data
    ("TM1814 default (max current)",    6, "WRGB",    {},                       "3f3f3f3fc0c0c0c0"),
    ("TM1814 chipCurrent 50%",         6, "WRGB",    {"chipCurrent": 50},      "1f1f1f1fe0e0e0e0"),
    ("TM1914 default (DIN only)",      9, "RGB",     {},                       "fffff500000a"),
    ("TM1914 auto-switch",             9, "RGB",     {"tm1914Mode": "auto"},   "ffffff000000"),
    ("TM1914 FDIN only",               9, "RGB",     {"tm1914Mode": "fdin"},   "fffffa000005"),
    ("UCS7604 chipCurrent 100%",      10, "RGBW",    {"chipCurrent": 100},     "ffffffffffff000203" "0f0f0f0f0000"),
    ("SM16825E chipCurrent 50% (g15)", 0, "RGBWC16", {"chipCurrent": 50},      "7bdef79f"),
]
ssh = m.ssh
m.push("ddrscan.py")
f = FPP("http://192.168.6.2")
base, bk = f.backup_config("results/config-backups")
ssh("cp /home/fpp/media/config/co-bbbStrings.json /tmp/co-bbbStrings.json.live-test")
bad = 0
try:
    for label, timing, order, extra, hexpat in CASES:
        hexpat = hexpat.replace(" ", "")
        cfg, chans = m.build_cfg(base, timing, order, 2, ports=1)
        cfg["channelOutputs"][0].update(extra)
        for k in ("chipCurrent", "tm1914Mode"):
            if k not in extra:
                cfg["channelOutputs"][0].pop(k, None)
        f.put_config(cfg); f.restart(); f.stop_playlist(); f.testmode(True, chans)
        time.sleep(3)
        out = ssh("sudo python3 /tmp/ddrscan.py %s" % hexpat)
        hit = [l for l in out.splitlines() if l.startswith("hits:")]
        ok = bool(hit) and "none" not in hit[-1]
        bad += not ok
        print("%-5s %-34s expect %-34s %s" % ("PASS" if ok else "FAIL", label, hexpat, hit[-1] if hit else out.strip()[-80:]))
finally:
    f.testmode(False)
    ssh("sudo cp /tmp/co-bbbStrings.json.live-test /home/fpp/media/config/co-bbbStrings.json; sudo chown fpp:fpp /home/fpp/media/config/co-bbbStrings.json; rm -f /tmp/co-bbbStrings.json.live-test")
    f.restart()
    print("config restored byte-for-byte; sha256:", ssh("sha256sum /home/fpp/media/config/co-bbbStrings.json").split()[-2][:16] if ssh("sha256sum /home/fpp/media/config/co-bbbStrings.json").split() else "?")
print("LIVE CHIP CURRENT TEST", "PASSED" if not bad else "FAILED (%d)" % bad)
sys.exit(1 if bad else 0)
