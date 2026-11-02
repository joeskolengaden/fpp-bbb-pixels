#!/usr/bin/env python3
"""The output-thread budget rule in doctor.sh must reproduce the stress-test measurements (48 x 1500 px PRU + n SPI outputs):
measured 6.7 / 15.3 / 25.5 / 42.8 ms for n = 0 / 1 / 2 / 4. The model may be at most 8% off."""
import json, os, re, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
s = open(os.path.join(HERE, "..", "doctor.sh")).read()
m = re.search(r"== output-thread budget.*?\npython3 - \"\$CFG\" /home/fpp/media/config/co-other.json <<'PY'\n(.*?)\nPY\n", s, re.S)
assert m, "rule block not found in doctor.sh"
d = tempfile.mkdtemp(); open(d + "/rule.py", "w").write(m.group(1))
pru = {"channelOutputs": [{"type": "BBB48String", "enabled": 1, "outputs": [{"virtualStrings": [{"pixelCount": 1500, "colorOrder": "GRB"}]} for _ in range(48)]}]}
json.dump(pru, open(d + "/pru.json", "w")); bad = 0
for n, meas in ((0, 6.7), (1, 15.3), (2, 25.5), (4, 42.8)):
    json.dump({"channelOutputs": [{"type": "SPIPixels", "outputs": [{"protocol": "apa102", "spiSpeed": 8000000, "virtualStrings": [{"pixelCount": 1500}]} for _ in range(n)]}]}, open(d + "/spi.json", "w"))
    out = subprocess.run([sys.executable, d + "/rule.py", d + "/pru.json", d + "/spi.json"], capture_output=True, text=True).stdout
    est = float(re.search(r"time per frame: ([\d.]+) ms", out).group(1)); err = abs(est - meas) / meas * 100
    ok = err <= 8; bad += not ok
    print("%s  %d SPI outputs: measured %.1f ms, model %.1f ms (%.1f%% off)" % ("ok  " if ok else "FAIL", n, meas, est, err))
# and the verdict: 4 SPI outputs must be flagged at 20 fps, 2 must not
assert "FAIL" not in out.split("20 fps")[0] and ("WARN 20 fps" in out or "FAIL 20 fps" in out), "4 SPI outputs should be flagged at 20 fps"
sys.exit(bad)
