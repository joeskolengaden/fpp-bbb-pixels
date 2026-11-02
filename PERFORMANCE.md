# How the system performs at 1,500 pixels per port, 8–48 ports, 20/30/40 fps

BeagleBone Green, FPP 5.4.1, single 1 GHz Cortex-A8 core. Every populated port carries **1,500 pixels**; each cell below was
measured under real FSEQ playback with the data changing every frame (126 measurements: 7 data paths × 8/16/24/32/40/48 ports × 20/30/40 fps, 6-second windows, `hwtest/perf_matrix.py`, re-run on the current build that includes the chip-current / TM1914-mode controls and the new SPI chips). Frame rates are FPP step times: 20 fps = 50 ms, 30 fps = 33 ms, 40 fps = 25 ms.

## Two independent limits

1. **Wire time (PRU).** 1,500 pixels must clock out inside the frame. This depends on the IC and frame rate, **not on the number of
   ports** (all ports shift on one shared clock). If it does not fit, the end of every string is cut off.
2. **CPU (fppd).** fppd must read the sequence, map every channel and copy the frame to the PRU each frame. This depends on **ports ×
   bytes per pixel × frame rate**. If it does not fit, frames go out late.

## Short answer

- **At 20 fps**, only the WS2812-timing family (WS2811/WS2812/WS2813/WS2815/SK6812-style "Normal", TM1829, TM1914) fits 1,500
  pixels, and it runs on **all 48 ports** with fppd using about 11% of the core (7.7 ms of work per 50 ms frame). Every other IC is already beyond its wire time at 1,500
  pixels (APA104 tops out at 1,200; 400 kHz chips at 823; 16-bit RGBW at 614; SM16825E at 490).
- **At 30 and 40 fps no IC can drive 1,500 pixels per port**: Normal tops out at 1,077 px (30 fps) and 812 px (40 fps).
- The CPU is not the first limit except for the wide data formats at high port counts (below).

## Verdict per IC at 1,500 px/port

`OK` = frame fits the interval and the system holds the cadence. `PRU` = the wire time of 1,500 px exceeds the frame (shows the pixel count that does fit). `SYS n` = system keeps cadence only up to n ports.

| IC / format | frame time @1,500 px | 20 fps (50 ms) | 30 fps (33 ms) | 40 fps (25 ms) |
|---|---|---|---|---|
| WS2812/WS2811-800 (Normal, GRB) | 45.2 ms | OK, all 48 | PRU — max 1077 px | PRU — max 812 px |
| ws281x Slow variant | 47.9 ms | OK, all 48 | PRU — max 1017 px | PRU — max 766 px |
| APA104/PL9823/SK6822 | 62.1 ms | PRU — max 1200 px | PRU — max 790 px | PRU — max 597 px |
| WS2811 @ 400 Kbps | 90.6 ms | PRU — max 823 px | PRU — max 542 px | PRU — max 409 px |
| UCS1903/UCS2903 @ 400 Kbps | 90.6 ms | PRU — max 823 px | PRU — max 542 px | PRU — max 409 px |
| TM1803 | 74.7 ms | PRU — max 999 px | PRU — max 657 px | PRU — max 497 px |
| TM1814 RGBW (inverted) | 60.4 ms | PRU — max 1230 px | PRU — max 808 px | PRU — max 609 px |
| TM1829 RGB (inverted) | 45.2 ms | OK, all 48 | PRU — max 1081 px | PRU — max 816 px |
| WS2805 RGB+WW+CW (5ch) | 66.1 ms | PRU — max 1122 px | PRU — max 737 px | PRU — max 555 px |
| TM1914 RGB (inverted) | 45.3 ms | OK, all 48 | PRU — max 1079 px | PRU — max 814 px |
| UCS7604 RGBW 8-bit | 60.5 ms | PRU — max 1226 px | PRU — max 804 px | PRU — max 605 px |
| UCS7604 RGBW 16-bit | 121.1 ms | PRU — max 612 px | PRU — max 401 px | PRU — max 301 px |
| SK6812/WS2814 RGBW (GRBW) | 60.3 ms | PRU — max 1235 px | PRU — max 813 px | PRU — max 614 px |
| UCS8903 16-bit RGB | 90.7 ms | PRU — max 819 px | PRU — max 537 px | PRU — max 405 px |
| UCS8904 16-bit RGBW | 120.9 ms | PRU — max 614 px | PRU — max 403 px | PRU — max 304 px |
| SM16825E 16-bit RGBWC + trailer | 151.3 ms | PRU — max 490 px | PRU — max 321 px | PRU — max 242 px |
| FW1906 6ch (RGBCWX) | 90.6 ms | PRU — max 819 px | PRU — max 537 px | PRU — max 405 px |

## CPU ceiling by data path (the system limit, independent of wire time)

Highest port count at which fppd still holds the frame cadence (each port 1,500 px; all smaller counts also pass). **Stock frame preparation → current build** (prefetching gather, ~1.6× faster):

| source ch → wire bytes per pixel | ICs | 20 fps | 30 fps | 40 fps |
|---|---|---|---|---|
| 3 → 3 | normal-grb, slow, apa104, ws2811-400, ucs1903-400, tm1803, tm1829, tm1914 | 48 → **48** | 48 → **48** | 48 → **48** |
| 3 → 6 | ucs8903-16 | 48 → **48** | 48 → **48** | 32 → **48** |
| 4 → 4 | tm1814, ucs7604-8, sk6812-rgbw | 48 → **48** | 48 → **48** | 32 → **48** |
| 4 → 8 | ucs7604-16, ucs8904-16 | 48 → **48** | 32 → **40** | 24 → **40** |
| 5 → 5 | ws2805 | 48 → **48** | 48 → **48** | 40 → **48** |
| 5 → 10 | sm16825e | 48 → **48** | 32 → **48** | 16 → **32** |
| 6 → 6 | fw1906 | 48 → **48** | 48 → **48** | 24 → **48** |

Cells holding the frame cadence: **108 / 126 before → 122 / 126 now**. Median fppd CPU: **23% → 18%**.

The 4 cells that still miss the cadence are all the widest data formats at the highest loads (ucs7604-16/ucs8904-16 at 48 ports, 30 fps; ucs7604-16/ucs8904-16 at 48 ports, 40 fps; sm16825e at 40 ports, 40 fps; sm16825e at 48 ports, 40 fps). Their wire time already rules out those frame rates, so the CPU limit costs nothing in practice.

The same matrix ran with the new chip-current (TM1814 / UCS7604 / SM16825E at 50%) and TM1914 auto-switch settings active: those controls change only a few preamble/trailer bytes, so the numbers are the same as for the chip's data path above.

## System load by data path (1,500 px on every populated port, FSEQ playback, data changing each frame)

Each cell: fppd CPU % of the single core · work ms per frame (avg/max: sequence read + channel map + copy to PRU memory) · achieved fps · late frames in the 6 s window.

**3 source ch/px → 3 wire bytes/px** — ICs: normal-grb, slow, apa104, ws2811-400, ucs1903-400, tm1803, tm1829, tm1914

| ports | channels/frame | 20 fps (50 ms) | 30 fps (33 ms) | 40 fps (25 ms) |
|---|---|---|---|---|
| 8 | 36,000 | ✅ 4.9% · 1.47/1.93 ms · 20.0 fps · 0 late | ✅ 6.5% · 1.42/2.15 ms · 30.2 fps · 0 late | ✅ 7.6% · 1.44/2.04 ms · 39.9 fps · 0 late |
| 16 | 72,000 | ✅ 6.5% · 2.72/3.85 ms · 20.0 fps · 0 late | ✅ 9.1% · 2.69/4.44 ms · 30.3 fps · 0 late | ✅ 11.4% · 2.64/3.48 ms · 39.9 fps · 0 late |
| 24 | 108,000 | ✅ 8.1% · 3.75/5.62 ms · 20.0 fps · 0 late | ✅ 11.1% · 3.55/6.56 ms · 30.2 fps · 0 late | ✅ 13.9% · 3.9/5.55 ms · 39.9 fps · 0 late |
| 32 | 144,000 | ✅ 10.0% · 5.36/7.7 ms · 20.1 fps · 0 late | ✅ 14.1% · 5.61/11.73 ms · 30.2 fps · 0 late | ✅ 17.9% · 6.29/10.0 ms · 39.8 fps · 0 late |
| 40 | 180,000 | ✅ 12.0% · 9.87/26.33 ms · 20.4 fps · 0 late | ✅ 16.2% · 5.8/9.54 ms · 30.2 fps · 0 late | ✅ 20.6% · 8.93/17.88 ms · 40.4 fps · 0 late |
| 48 | 216,000 | ✅ 12.9% · 7.91/17.24 ms · 20.2 fps · 0 late | ✅ 18.3% · 7.68/17.05 ms · 30.2 fps · 0 late | ✅ 23.6% · 8.62/20.28 ms · 39.9 fps · 0 late |

**4 source ch/px → 4 wire bytes/px** — ICs: tm1814, ucs7604-8, sk6812-rgbw

| ports | channels/frame | 20 fps (50 ms) | 30 fps (33 ms) | 40 fps (25 ms) |
|---|---|---|---|---|
| 8 | 48,000 | ✅ 5.9% · 1.86/2.35 ms · 20.0 fps · 0 late | ✅ 7.8% · 1.8/2.38 ms · 30.2 fps · 0 late | ✅ 9.5% · 1.95/2.67 ms · 39.9 fps · 0 late |
| 16 | 96,000 | ✅ 8.0% · 3.55/5.73 ms · 20.0 fps · 0 late | ✅ 11.2% · 3.85/8.22 ms · 30.2 fps · 0 late | ✅ 14.3% · 3.47/5.79 ms · 39.8 fps · 0 late |
| 24 | 144,000 | ✅ 9.7% · 5.54/6.78 ms · 20.0 fps · 0 late | ✅ 13.7% · 5.14/8.22 ms · 30.2 fps · 0 late | ✅ 17.7% · 6.33/10.97 ms · 40.0 fps · 0 late |
| 32 | 192,000 | ✅ 11.7% · 6.15/8.7 ms · 20.0 fps · 0 late | ✅ 17.0% · 7.21/13.64 ms · 30.2 fps · 0 late | ✅ 21.8% · 7.36/19.09 ms · 39.9 fps · 0 late |
| 40 | 240,000 | ✅ 13.6% · 7.51/11.16 ms · 20.1 fps · 0 late | ✅ 19.7% · 7.62/19.94 ms · 30.2 fps · 0 late | ✅ 25.3% · 9.25/16.13 ms · 40.1 fps · 0 late |
| 48 | 288,000 | ✅ 15.3% · 11.31/23.64 ms · 20.0 fps · 0 late | ✅ 22.5% · 7.85/13.93 ms · 30.2 fps · 0 late | ✅ 29.2% · 10.26/15.9 ms · 40.1 fps · 0 late |

**5 source ch/px → 5 wire bytes/px** — ICs: ws2805

| ports | channels/frame | 20 fps (50 ms) | 30 fps (33 ms) | 40 fps (25 ms) |
|---|---|---|---|---|
| 8 | 60,000 | ✅ 6.5% · 2.32/2.98 ms · 20.0 fps · 0 late | ✅ 9.0% · 2.51/5.03 ms · 30.2 fps · 0 late | ✅ 11.2% · 3.67/10.46 ms · 40.1 fps · 0 late |
| 16 | 120,000 | ✅ 9.0% · 5.56/11.81 ms · 20.0 fps · 0 late | ✅ 13.1% · 4.29/6.28 ms · 30.2 fps · 0 late | ✅ 16.7% · 6.64/19.32 ms · 40.0 fps · 0 late |
| 24 | 180,000 | ✅ 11.4% · 8.38/23.41 ms · 20.1 fps · 0 late | ✅ 16.3% · 6.24/14.76 ms · 30.2 fps · 0 late | ✅ 21.0% · 5.6/7.71 ms · 39.9 fps · 0 late |
| 32 | 240,000 | ✅ 13.7% · 7.65/12.11 ms · 20.0 fps · 0 late | ✅ 19.8% · 8.2/15.71 ms · 30.3 fps · 0 late | ✅ 25.3% · 10.58/22.08 ms · 40.4 fps · 0 late |
| 40 | 300,000 | ✅ 16.0% · 10.33/22.74 ms · 20.3 fps · 0 late | ✅ 23.1% · 10.32/24.01 ms · 30.2 fps · 0 late | ✅ 29.5% · 8.71/14.65 ms · 39.9 fps · 0 late |
| 48 | 360,000 | ✅ 18.1% · 10.59/16.62 ms · 20.0 fps · 0 late | ✅ 26.3% · 10.05/16.81 ms · 30.2 fps · 0 late | ✅ 34.3% · 13.14/27.35 ms · 39.9 fps · 1 late |

**4 source ch/px → 8 wire bytes/px** — ICs: ucs7604-16, ucs8904-16

| ports | channels/frame | 20 fps (50 ms) | 30 fps (33 ms) | 40 fps (25 ms) |
|---|---|---|---|---|
| 8 | 48,000 | ✅ 7.8% · 4.16/10.63 ms · 20.0 fps · 0 late | ✅ 10.7% · 3.15/4.63 ms · 30.2 fps · 0 late | ✅ 13.6% · 4.13/10.06 ms · 39.9 fps · 0 late |
| 16 | 96,000 | ✅ 11.9% · 6.27/9.86 ms · 20.0 fps · 0 late | ✅ 17.0% · 6.01/10.01 ms · 30.2 fps · 0 late | ✅ 21.8% · 8.78/15.81 ms · 40.0 fps · 0 late |
| 24 | 144,000 | ✅ 15.4% · 9.88/20.38 ms · 20.1 fps · 0 late | ✅ 22.4% · 9.13/14.65 ms · 30.2 fps · 0 late | ✅ 28.6% · 10.87/25.75 ms · 40.2 fps · 1 late |
| 32 | 192,000 | ✅ 18.5% · 14.11/36.3 ms · 20.0 fps · 0 late | ✅ 27.4% · 9.38/13.02 ms · 30.3 fps · 0 late | ✅ 35.5% · 16.19/28.18 ms · 40.7 fps · 4 late |
| 40 | 240,000 | ✅ 22.1% · 12.1/15.97 ms · 20.0 fps · 0 late | ✅ 32.7% · 12.38/20.66 ms · 30.2 fps · 0 late | ✅ 42.9% · 18.49/37.81 ms · 40.0 fps · 4 late |
| 48 | 288,000 | ✅ 26.1% · 18.29/30.34 ms · 20.0 fps · 0 late | ❌ 38.5% · 26.13/61.17 ms · 30.2 fps · 6 late | ❌ 49.6% · 25.26/52.55 ms · 40.0 fps · 14 late |

**3 source ch/px → 6 wire bytes/px** — ICs: ucs8903-16

| ports | channels/frame | 20 fps (50 ms) | 30 fps (33 ms) | 40 fps (25 ms) |
|---|---|---|---|---|
| 8 | 36,000 | ✅ 6.6% · 2.82/3.88 ms · 20.0 fps · 0 late | ✅ 9.4% · 2.57/3.87 ms · 30.2 fps · 0 late | ✅ 11.7% · 3.19/5.75 ms · 40.0 fps · 0 late |
| 16 | 72,000 | ✅ 9.9% · 4.87/6.84 ms · 20.0 fps · 0 late | ✅ 13.8% · 6.34/16.58 ms · 30.3 fps · 0 late | ✅ 18.2% · 6.69/15.63 ms · 40.5 fps · 0 late |
| 24 | 108,000 | ✅ 13.2% · 8.0/15.6 ms · 20.0 fps · 0 late | ✅ 18.0% · 6.26/10.19 ms · 30.2 fps · 0 late | ✅ 23.1% · 10.45/25.9 ms · 39.9 fps · 1 late |
| 32 | 144,000 | ✅ 15.0% · 9.63/27.46 ms · 20.4 fps · 0 late | ✅ 21.9% · 11.46/24.4 ms · 30.2 fps · 0 late | ✅ 28.1% · 14.65/38.16 ms · 40.0 fps · 2 late |
| 40 | 180,000 | ✅ 17.5% · 9.09/11.87 ms · 20.0 fps · 0 late | ✅ 25.9% · 10.95/16.79 ms · 30.2 fps · 0 late | ✅ 33.6% · 9.14/15.54 ms · 39.9 fps · 0 late |
| 48 | 216,000 | ✅ 20.3% · 14.63/33.92 ms · 20.0 fps · 0 late | ✅ 30.0% · 14.74/34.27 ms · 30.2 fps · 1 late | ✅ 39.1% · 15.33/26.39 ms · 40.0 fps · 1 late |

**5 source ch/px → 10 wire bytes/px** — ICs: sm16825e

| ports | channels/frame | 20 fps (50 ms) | 30 fps (33 ms) | 40 fps (25 ms) |
|---|---|---|---|---|
| 8 | 60,000 | ✅ 8.5% · 3.96/5.47 ms · 20.0 fps · 0 late | ✅ 11.9% · 4.07/7.78 ms · 30.2 fps · 0 late | ✅ 15.0% · 4.11/7.52 ms · 39.9 fps · 0 late |
| 16 | 120,000 | ✅ 13.6% · 7.0/11.1 ms · 20.0 fps · 0 late | ✅ 19.7% · 8.05/11.68 ms · 30.2 fps · 0 late | ✅ 25.1% · 7.74/11.87 ms · 39.8 fps · 0 late |
| 24 | 180,000 | ✅ 17.6% · 9.69/15.23 ms · 20.0 fps · 0 late | ✅ 26.0% · 10.58/23.02 ms · 30.2 fps · 0 late | ✅ 34.0% · 10.35/16.75 ms · 39.9 fps · 0 late |
| 32 | 240,000 | ✅ 22.2% · 11.61/15.71 ms · 20.0 fps · 0 late | ✅ 32.5% · 16.17/40.29 ms · 30.2 fps · 1 late | ✅ 42.1% · 14.35/30.83 ms · 40.0 fps · 1 late |
| 40 | 300,000 | ✅ 26.5% · 21.82/60.64 ms · 20.0 fps · 1 late | ✅ 39.1% · 15.2/22.78 ms · 30.2 fps · 0 late | ❌ 50.9% · 25.51/62.87 ms · 40.0 fps · 15 late |
| 48 | 360,000 | ✅ 31.0% · 20.24/35.35 ms · 20.0 fps · 0 late | ✅ 45.9% · 22.18/42.91 ms · 30.2 fps · 4 late | ❌ 60.5% · 27.61/65.77 ms · 40.0 fps · 25 late |

**6 source ch/px → 6 wire bytes/px** — ICs: fw1906

| ports | channels/frame | 20 fps (50 ms) | 30 fps (33 ms) | 40 fps (25 ms) |
|---|---|---|---|---|
| 8 | 72,000 | ✅ 6.9% · 2.65/3.56 ms · 20.0 fps · 0 late | ✅ 9.5% · 3.23/10.0 ms · 30.2 fps · 0 late | ✅ 11.9% · 3.51/11.39 ms · 39.9 fps · 0 late |
| 16 | 144,000 | ✅ 9.9% · 5.29/12.24 ms · 20.1 fps · 0 late | ✅ 14.4% · 5.8/14.8 ms · 30.2 fps · 0 late | ✅ 18.4% · 5.24/8.04 ms · 39.9 fps · 0 late |
| 24 | 216,000 | ✅ 12.5% · 8.02/18.56 ms · 20.0 fps · 0 late | ✅ 18.1% · 6.8/11.66 ms · 30.2 fps · 0 late | ✅ 23.3% · 7.08/10.98 ms · 39.9 fps · 0 late |
| 32 | 288,000 | ✅ 15.3% · 8.3/12.33 ms · 20.0 fps · 0 late | ✅ 22.4% · 9.32/24.84 ms · 30.2 fps · 0 late | ✅ 28.8% · 8.44/14.37 ms · 39.9 fps · 0 late |
| 40 | 360,000 | ✅ 18.0% · 11.48/30.17 ms · 20.0 fps · 0 late | ✅ 26.4% · 12.21/25.01 ms · 30.2 fps · 0 late | ✅ 34.1% · 11.17/27.59 ms · 39.9 fps · 1 late |
| 48 | 432,000 | ✅ 20.6% · 11.6/19.03 ms · 20.0 fps · 0 late | ✅ 30.6% · 12.44/30.5 ms · 30.2 fps · 0 late | ✅ 39.9% · 13.36/28.15 ms · 40.0 fps · 2 late |

## Clocked (SPI) chips — SPIPixels at 1,500 px per output

The BeagleBone Green has 4 SPI chip-selects (`spidev0.0`, `0.1`, `1.0`, `1.1`) on two buses. SPIPixels writes each output **synchronously** from fppd's output thread, so the outputs are sent one after another and the time per frame is the **sum** of their transfers (measured: 2 outputs = exactly 2× one). Measured under real FSEQ playback with the data changing every frame, each chip at its plugin default clock: 1, 2 and 4 outputs × 1,500 px at 20/30/40 fps (90 measurements, 6-second windows, `hwtest/perf_spi.py`).

A frame is on time when all outputs finish inside the frame interval. fppd CPU stays below 20% in every case; the limit is the **clock**, not the CPU.

| chip | clock | frame @1,500 px, 1 output (measured) | outputs that hold 20 fps | 30 fps | 40 fps | max px, 1 output: 20 / 30 / 40 fps |
|---|---|---|---|---|---|---|
| apa102 | 8 MHz | 7.87 ms | 4 | 2 | 2 | 9,564 / 6,279 / 4,781 |
| apa102hd | 8 MHz | 8.02 ms | 4 | 2 | 2 | 9,564 / 6,279 / 4,781 |
| sk9822hd | 8 MHz | 8.08 ms | 4 | 2 | 2 | 9,564 / 6,279 / 4,781 |
| hd107s | 20 MHz | 4.58 ms | 4 | 4 | 4 | 18,982 / 12,448 / 9,404 |
| hd108 | 20 MHz | 9.34 ms | 4 | 2 | 2 | 9,070 / 5,947 / 4,493 |
| ws2801 | 1 MHz | 39.48 ms | 1 | none | none | 1,911 / 1,266 / 955 |
| lpd8806 | 2 MHz | 20.5 ms | 2 | 1 | 1 | 3,697 / 2,439 / 1,833 |
| lpd6803 | 1 MHz | 27.99 ms | 1 | 1 | none | 2,696 / 1,785 / 1,346 |
| p9813 | 1 MHz | 53.35 ms | none | none | none | 1,409 / 933 / 704 |
| sm16716 | 16 MHz | 3.8 ms | 4 | 4 | 4 | 21,092 / 13,961 / 10,483 |

Reading the table: `4` means all four chip-selects at 1,500 px hold the cadence; `none` means even one output of 1,500 px takes longer than the frame (raise the clock if the chip allows it, or shorten the string — `MAX_PIXELS.md` has the pixel limit per chip and clock).

<details><summary>Every SPI measurement</summary>

## SPI chips at 1,500 px per output (BeagleBone Green, 4 spidev chip-selects on 2 buses)

Each cell: ✅/❌ cadence held · SPI send ms per frame (all outputs, they are sent one after another) · fppd CPU · achieved fps · late frames in 6 s.

| chip | clock | wire bytes @1,500 px | outputs | 20 fps (50 ms) | 30 fps (33 ms) | 40 fps (25 ms) |
|---|---|---|---|---|---|---|
| apa102 | 8 MHz | 6098 | 1 | ✅ 7.87 ms · 3.4% · 20.0 fps · 0 late | ✅ 7.81 ms · 4.6% · 30.2 fps · 0 late | ✅ 7.88 ms · 5.4% · 39.9 fps · 0 late |
|  | 8 MHz | 6098 | 2 | ✅ 15.69 ms · 4.8% · 20.0 fps · 0 late | ✅ 15.59 ms · 6.5% · 30.2 fps · 0 late | ✅ 15.75 ms · 7.9% · 39.9 fps · 0 late |
|  | 8 MHz | 6098 | 4 | ✅ 31.56 ms · 7.7% · 20.0 fps · 0 late | ❌ 31.87 ms · 11.5% · 30.2 fps · 47 late | ❌ 31.71 ms · 14.9% · None fps · 189 late |
| apa102hd | 8 MHz | 6098 | 1 | ✅ 8.02 ms · 4.1% · 20.0 fps · 0 late | ✅ 7.9 ms · 5.3% · 30.2 fps · 0 late | ✅ 8.86 ms · 6.6% · 39.9 fps · 0 late |
|  | 8 MHz | 6098 | 2 | ✅ 16.08 ms · 6.1% · 20.0 fps · 0 late | ✅ 15.84 ms · 8.1% · 30.2 fps · 0 late | ✅ 17.14 ms · 10.1% · 39.9 fps · 1 late |
|  | 8 MHz | 6098 | 4 | ✅ 32.15 ms · 9.9% · 20.0 fps · 0 late | ❌ 31.37 ms · 16.6% · 30.2 fps · 173 late | ❌ 31.71 ms · 17.8% · None fps · 183 late |
| sk9822hd | 8 MHz | 6098 | 1 | ✅ 8.08 ms · 4.2% · 20.0 fps · 0 late | ✅ 7.94 ms · 5.3% · 30.2 fps · 0 late | ✅ 8.05 ms · 6.5% · 39.9 fps · 0 late |
|  | 8 MHz | 6098 | 2 | ✅ 16.18 ms · 6.0% · 20.0 fps · 0 late | ✅ 15.88 ms · 8.2% · 30.2 fps · 0 late | ✅ 15.64 ms · 10.2% · 39.8 fps · 0 late |
|  | 8 MHz | 6098 | 4 | ✅ 31.55 ms · 9.7% · 20.0 fps · 0 late | ❌ 31.44 ms · 16.7% · None fps · 177 late | ❌ 31.7 ms · 18.0% · None fps · 185 late |
| hd107s | 20 MHz | 6098 | 1 | ✅ 4.58 ms · 3.2% · 20.0 fps · 0 late | ✅ 4.55 ms · 4.2% · 30.2 fps · 0 late | ✅ 4.62 ms · 5.3% · 39.9 fps · 0 late |
|  | 20 MHz | 6098 | 2 | ✅ 9.16 ms · 4.8% · 20.0 fps · 0 late | ✅ 8.99 ms · 5.9% · 30.2 fps · 0 late | ✅ 9.07 ms · 7.4% · 39.9 fps · 0 late |
|  | 20 MHz | 6098 | 4 | ✅ 18.2 ms · 7.0% · 20.0 fps · 0 late | ✅ 17.85 ms · 9.4% · 30.2 fps · 0 late | ✅ 19.97 ms · 12.2% · 39.9 fps · 3 late |
| hd108 | 20 MHz | 12770 | 1 | ✅ 9.34 ms · 4.1% · 20.0 fps · 0 late | ✅ 9.35 ms · 5.1% · 30.2 fps · 0 late | ✅ 9.28 ms · 5.8% · 39.9 fps · 0 late |
|  | 20 MHz | 12770 | 2 | ✅ 18.69 ms · 5.2% · 20.0 fps · 0 late | ✅ 18.6 ms · 7.0% · 30.2 fps · 0 late | ✅ 18.85 ms · 8.9% · 40.0 fps · 0 late |
|  | 20 MHz | 12770 | 4 | ✅ 37.62 ms · 8.9% · 20.0 fps · 0 late | ❌ 37.7 ms · 14.6% · None fps · 162 late | ❌ 37.8 ms · 15.4% · None fps · 162 late |
| ws2801 | 1 MHz | 4500 | 1 | ✅ 39.48 ms · 5.4% · 20.0 fps · 0 late | ❌ 39.35 ms · 9.3% · None fps · 158 late | ❌ 39.45 ms · 10.3% · None fps · 158 late |
|  | 1 MHz | 4500 | 2 | ❌ 79.01 ms · 9.0% · None fps · 82 late | ❌ 78.7 ms · 9.9% · None fps · 83 late | ❌ 79.01 ms · 10.1% · None fps · 82 late |
|  | 1 MHz | 4500 | 4 | ❌ 157.79 ms · 9.4% · None fps · 38 late | ❌ 158.19 ms · 10.4% · None fps · 38 late | ❌ 157.85 ms · 11.1% · None fps · 39 late |
| lpd8806 | 2 MHz | 4547 | 1 | ✅ 20.5 ms · 4.6% · 20.0 fps · 0 late | ✅ 20.4 ms · 5.8% · 30.2 fps · 0 late | ✅ 20.48 ms · 7.0% · 39.9 fps · 0 late |
|  | 2 MHz | 4547 | 2 | ✅ 41.19 ms · 6.6% · 20.0 fps · 0 late | ❌ 41.05 ms · 10.7% · None fps · 153 late | ❌ 40.9 ms · 11.3% · None fps · 153 late |
|  | 2 MHz | 4547 | 4 | ❌ 81.8 ms · 10.7% · None fps · 76 late | ❌ 81.93 ms · 11.5% · None fps · 77 late | ❌ 82.1 ms · 11.9% · None fps · 75 late |
| lpd6803 | 1 MHz | 3192 | 1 | ✅ 27.99 ms · 4.2% · 20.0 fps · 0 late | ✅ 27.93 ms · 5.3% · 30.2 fps · 0 late | ❌ 27.91 ms · 9.6% · None fps · 226 late |
|  | 1 MHz | 3192 | 2 | ❌ 55.69 ms · 8.5% · None fps · 114 late | ❌ 55.91 ms · 9.7% · None fps · 117 late | ❌ 55.81 ms · 10.0% · None fps · 115 late |
|  | 1 MHz | 3192 | 4 | ❌ 111.82 ms · 8.8% · None fps · 57 late | ❌ 111.55 ms · 9.5% · None fps · 58 late | ❌ 111.85 ms · 10.2% · None fps · 59 late |
| p9813 | 1 MHz | 6100 | 1 | ❌ 53.35 ms · 8.2% · None fps · 120 late | ❌ 53.28 ms · 8.9% · None fps · 122 late | ❌ 53.25 ms · 9.4% · None fps · 122 late |
|  | 1 MHz | 6100 | 2 | ❌ 106.69 ms · 8.3% · None fps · 61 late | ❌ 106.81 ms · 8.8% · None fps · 61 late | ❌ 106.69 ms · 9.4% · None fps · 61 late |
|  | 1 MHz | 6100 | 4 | ❌ 213.1 ms · 8.5% · 23.3 fps · 29 late | ❌ 213.13 ms · 9.7% · 23.3 fps · 31 late | ❌ 213.31 ms · 10.4% · 23.3 fps · 29 late |
| sm16716 | 16 MHz | 4694 | 1 | ✅ 3.8 ms · 4.2% · 20.0 fps · 0 late | ✅ 3.68 ms · 5.4% · 30.2 fps · 0 late | ✅ 3.82 ms · 6.4% · 39.8 fps · 0 late |
|  | 16 MHz | 4694 | 2 | ✅ 7.75 ms · 6.3% · 20.0 fps · 0 late | ✅ 7.29 ms · 8.5% · 30.2 fps · 0 late | ✅ 7.27 ms · 10.4% · 39.9 fps · 0 late |
|  | 16 MHz | 4694 | 4 | ✅ 15.8 ms · 10.7% · 20.1 fps · 0 late | ✅ 16.02 ms · 15.0% · 30.2 fps · 1 late | ✅ 15.25 ms · 18.9% · 40.0 fps · 0 late |


</details>

## What changed in this round

| change | effect |
|---|---|
| `prepData` prefetching gather (`prepdata_prefetch.inc`) | frame preparation **1.6× faster** (measured in isolation on the board: 8.1 → 5.0 ms for 48 × 1,500 RGB px; 21.4 → 13.4 ms for 8-byte pixels), byte-identical output proven on 300 random configurations; cadence cells 108 → 120 of 126 |
| frame-budget log line + live UI readout | the cut-off hazard is now visible: the UI shows each port's wire time and the highest sustainable fps; `fppd.log` prints it at start-up |
| `doctor.sh` | one-screen health report |

Why the loop was slow: it is DRAM-latency bound, not compute bound. The Cortex-A8 has no L1 hardware prefetcher and a DDR miss costs a
few hundred ns; the loop streams a 4-byte map entry plus a channel byte per output byte. Software prefetch recovers about a third. What
did **not** help (measured, so not shipped): tiling the transpose, staging the frame in cached memory before copying to the PRU buffer,
and unrolling.

## Stress-test rules (measured on the BeagleBone Green, 2026-11-03)

`hwtest/stress.py` pushed the board to its limits. What it found became rules, enforced in the pixel-strings page (limits panel) and in `doctor.sh`:

| # | Rule | Evidence |
|---|---|---|
| 1 | **A port must fit its frame**: pixels per port <= the limit shown on the page for the chip and frame rate (Normal timing: 1,636 px at 20 fps, 810 at 40; 16-bit RGBWC: 490 at 20). Past it fppd is still fine but the far end of the string stops updating. | 48 ports: 1,650 px held at 20 fps, 1,700 / 1,800 cut off; 830 held at 40 fps, 860 / 900 cut off; RGBWC16 480 held, 520 cut off. fppd CPU never went above 17%. |
| 2 | **Wire time, not CPU, is the limit.** All 48 ports at the per-port limit run at 12-17% fppd CPU. | same runs |
| 3 | **SPI outputs cost output-thread time, one after another** (about 8.6 ms per 1,500-pixel APA102 output at 8 MHz). Keep the estimated output-thread time (PRU frame preparation + SPI sends) **under 60% of the frame interval**, so peaks (up to 1.5x the average) still fit. `doctor.sh` prints the estimate per frame rate. | 48 x 1,500 px PRU + 0 / 1 / 2 / 4 SPI outputs: 6.7 / 15.3 / 25.5 / 42.8 ms (model 6.7 / 16.3 / 25.9 / 45.2); 4 SPI outputs gave late frames at 20 fps. |
| 4 | **Do not hammer the web API.** Four clients polling it continuously push the single core to 100% and about 25% of requests time out; the output itself kept its frame rate. | PRU + 4 API clients: 25% requests failed, 0 late frames |
| 5 | **Stable under load and abuse**: 8 minutes at 48 x 1,500 px with no missed window and flat memory; 8 fppd restarts with the full config all clean (~12 s each); fppd comes back by itself ~6 s after a `kill -9`. | `results/stress.log`, `results/stress-c.log` |

Not measured: SoC temperature (this kernel exposes no thermal sensor), and stress per individual IC (the stress runs used stock Normal timing and the 16-bit RGBWC data path; every other chip shares one of these data paths and the same wire time per byte).
