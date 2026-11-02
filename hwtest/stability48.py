#!/usr/bin/env python3
"""stability48.py - populate every PRU output with N pixels, run FPP test mode, and check the board stays healthy
(fppd alive, no output/PRU errors in the log, memory and load sane). Restores the original config afterwards."""
import json, os, re, sys, time
sys.path.insert(0, ".")
import measure_limits as m
from verify_presets import FPP

N = int(sys.argv[1]) if len(sys.argv) > 1 else 1600
f = FPP("http://192.168.6.2"); base, _bk = f.backup_config(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results', 'config-backups'))
print('starting config saved to', _bk)
try:
    cfg, ch = m.build_cfg(base, 0, "GRB", N, ports=48)
    npx = sum(len(o["virtualStrings"]) and sum(v["pixelCount"] for v in o["virtualStrings"]) for o in cfg["channelOutputs"][0]["outputs"])
    f.put_config(cfg)
    log0 = int(m.ssh("wc -l < /home/fpp/media/logs/fppd.log").split()[-1])
    f.restart(); f.stop_playlist(); f.testmode(True, ch * 48)
    time.sleep(25)
    out = m.ssh("pgrep -a fppd | head -1; cat /proc/loadavg; free -m | sed -n 2p; "
                "tail -n +%d /home/fpp/media/logs/fppd.log | grep -i -E 'error|fail|unable|overrun|PRU' | grep -v -i pixelselect | head -8; "
                "curl -s -m5 localhost/api/fppd/status | head -c 120" % (log0 + 1))
    print("ports=48 pixels/port=%d total pixels=%d channels=%d" % (N, npx, ch * 48))
    print("\n".join(l for l in out.splitlines() if not l.startswith(("Debian", "Falcon"))))
finally:
    f.testmode(False); f.put_config(base); f.restart()
    print("restored original config")
