#!/usr/bin/env python3
"""
perf_spi.py - system performance of the SPIPixels clocked chips at 1,500 pixels per output, under real FSEQ playback.

The BeagleBone Green exposes 4 spidev chip-selects (spidev0.0, 0.1, 1.0, 1.1) on two buses; SPIPixels writes each output
synchronously from fppd's output thread, so the per-frame "Send" time IS the SPI transfer. For each chip at its plugin
default clock: 1 / 2 / 4 outputs x 1,500 px, at 20 / 30 / 40 fps, 6 s window each (perfwin.py). Verdict = fppd keeps the
frame cadence (achieved >= 97% of target, <= 3% late frames).

  python3 perf_spi.py --out results/perf-spi.jsonl [--chips apa102,hd108] [--outputs 1,2,4] [--fps 20,30,40]

The pixel-string config (co-bbbStrings.json) is switched off for the run so the PRU does not also work; the caller restores it.
"""
import argparse, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import measure_limits as m
from verify_presets import FPP

NPIX = 1500
STEP = {20: 50, 30: 33, 40: 25}
DEVICES = ["spidev0.0", "spidev1.0", "spidev0.1", "spidev1.1"]       # one per bus first, then the second chip-select
# protocol, colour order, plugin default clock (Hz)  - mirrors SPIChipFormat.h / max_pixels.SPI_CHIPS
CHIPS = [("apa102", "BGR", 8_000_000), ("apa102hd", "BGR", 8_000_000), ("sk9822hd", "BGR", 8_000_000),
         ("hd107s", "BGR", 20_000_000), ("hd108", "RGB", 20_000_000), ("ws2801", "RGB", 1_000_000),
         ("sk9826", "GRB", 10_000_000), ("tlc59711", "BGR", 1_000_000), ("apa107", "BGR", 8_000_000),
         ("lpd8806", "GRB", 2_000_000), ("lpd6803", "RGB", 1_000_000), ("p9813", "BGR", 1_000_000),
         ("sm16716", "RGB", 16_000_000)]


def spi_cfg(proto, order, hz, nout):
    outs = []
    for i in range(nout):
        outs.append({"device": DEVICES[i], "protocol": proto, "spiSpeed": hz, "portNumber": i,
                     "virtualStrings": [{"description": "perf", "startChannel": i * NPIX * 3, "pixelCount": NPIX, "groupCount": 0,
                                         "reverse": 0, "colorOrder": order, "nullNodes": 0, "endNulls": 0, "zigZag": 0,
                                         "brightness": 100, "gamma": "1.0"}]})
    return {"channelOutputs": [{"type": "SPIPixels", "enabled": 1, "startChannel": 1, "channelCount": nout * NPIX * 3, "outputs": outs}]}


def run_point(fpp, ch_total, fps, secs=6):
    step = STEP[fps]
    frames = max(40, int(2000 / step))
    m.ssh("sudo rm -f /home/fpp/media/sequences/perf.fseq; python3 /tmp/mkfseq.py /home/fpp/media/sequences/perf.fseq %d %d %d" % (ch_total, frames, step), 300)
    fpp.stop_playlist(); time.sleep(1)
    fpp.req("/api/command/Start%20Playlist/perf/true/false")
    time.sleep(3.5)
    out = m.ssh("python3 /tmp/perfwin.py %d" % secs, 60)
    line = [l for l in out.splitlines() if l.startswith("{")]
    fpp.stop_playlist()
    return json.loads(line[-1]) if line else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fpp", default="http://192.168.6.2")
    ap.add_argument("--chips", default="")
    ap.add_argument("--outputs", default="1,2,4")
    ap.add_argument("--fps", default="20,30,40")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    fpp = FPP(a.fpp)
    m.push("mkfseq.py", "perfwin.py")
    base, bk = fpp.backup_config(os.path.join(HERE, "results", "config-backups"))
    print("starting pixel config saved to", bk)
    off = json.loads(json.dumps(base))
    for co in off["channelOutputs"]:
        co["enabled"] = 0
    done = set()
    if os.path.exists(a.out):
        for l in open(a.out):
            r = json.loads(l); done.add((r["chip"], r["outputs"], r["fps"]))
    chips = [c for c in CHIPS if not a.chips or c[0] in a.chips.split(",")]
    m.ssh("""python3 -c "import json;json.dump({'name':'perf','version':3,'repeat':0,'loopCount':0,'empty':False,'desc':'','random':0,'leadIn':[],'mainPlaylist':[{'type':'sequence','enabled':1,'playOnce':0,'sequenceName':'perf.fseq','duration':0}],'leadOut':[],'playlistInfo':{'total_duration':None,'total_items':1}},open('/home/fpp/media/playlists/perf.json','w'),indent=2)" """)
    fpp.req("/api/settings/LogLevel_ChannelOut", "PUT", "debug")
    try:
        fpp.put_config(off)
        for proto, order, hz in chips:
            for nout in [int(x) for x in a.outputs.split(",")]:
                todo = [f for f in [int(x) for x in a.fps.split(",")] if (proto, nout, f) not in done]
                if not todo:
                    continue
                fpp.req("/api/configfile/co-other.json", "POST", json.dumps(spi_cfg(proto, order, hz, nout), indent=2))
                fpp.restart()
                for fps in todo:
                    r = run_point(fpp, NPIX * 3 * nout, fps)
                    rec = {"chip": proto, "hz": hz, "outputs": nout, "fps": fps, "metrics": r}
                    open(a.out, "a").write(json.dumps(rec) + "\n")
                    mm = r or {}
                    print("%-9s %2.0fMHz outputs=%d fps=%d cpu=%5s%% send/work avg=%s/%s ms max=%s late=%s achieved=%s" % (
                        proto, hz / 1e6, nout, fps, mm.get("fppd_cpu_pct"), mm.get("send_ms"), mm.get("work_ms_avg"),
                        mm.get("work_ms_max"), mm.get("late_lines"), mm.get("achieved_fps")), flush=True)
    finally:
        try:
            fpp.stop_playlist(); fpp.req("/api/settings/LogLevel_ChannelOut", "PUT", "info")
            m.ssh("sudo rm -f /home/fpp/media/config/co-other.json /home/fpp/media/sequences/perf.fseq /home/fpp/media/playlists/perf.json")
            fpp.put_config(base); fpp.restart()
        except Exception as e:
            print("!! restore failed:", e)
        print("restored")


if __name__ == "__main__":
    main()
