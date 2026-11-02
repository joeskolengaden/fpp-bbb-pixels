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
