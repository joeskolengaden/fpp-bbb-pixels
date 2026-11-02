## System load by data path (1,500 px on every populated port, FSEQ playback, data changing each frame)

Each cell: fppd CPU % of the single core · work ms per frame (avg/max: sequence read + channel map + copy to PRU memory) · achieved fps · late frames in the 6 s window.

**3 source ch/px → 3 wire bytes/px** — ICs: normal-grb, slow, apa104, ws2811-400, ucs1903-400, tm1803, tm1829, tm1914

| ports | channels/frame | 20 fps (50 ms) | 30 fps (33 ms) | 40 fps (25 ms) |
|---|---|---|---|---|
| 8 | 36,000 | ✅ 3.4% · 1.45/1.91 ms · 20.0 fps · 0 late | ✅ 5.0% · 1.73/5.21 ms · 30.2 fps · 0 late | ✅ 6.6% · 1.61/3.5 ms · 39.8 fps · 0 late |
| 16 | 72,000 | ✅ 5.2% · 2.47/3.42 ms · 20.0 fps · 0 late | ✅ 7.4% · 2.56/4.48 ms · 30.2 fps · 0 late | ✅ 9.9% · 3.55/6.78 ms · 39.9 fps · 0 late |
| 24 | 108,000 | ✅ 6.7% · 3.63/5.2 ms · 20.0 fps · 0 late | ✅ 9.4% · 3.45/5.12 ms · 30.2 fps · 0 late | ✅ 12.3% · 3.81/7.3 ms · 40.0 fps · 0 late |
| 32 | 144,000 | ✅ 8.2% · 4.45/6.42 ms · 20.0 fps · 0 late | ✅ 12.4% · 4.64/6.65 ms · 30.2 fps · 0 late | ✅ 16.4% · 5.11/7.79 ms · 39.9 fps · 0 late |
| 40 | 180,000 | ✅ 9.8% · 7.38/14.76 ms · 20.0 fps · 0 late | ✅ 14.5% · 5.72/9.23 ms · 30.2 fps · 0 late | ✅ 18.8% · 6.26/10.22 ms · 40.0 fps · 0 late |
| 48 | 216,000 | ✅ 11.3% · 7.66/12.48 ms · 20.1 fps · 0 late | ✅ 16.6% · 6.25/9.61 ms · 30.2 fps · 0 late | ✅ 21.6% · 7.62/9.64 ms · 39.9 fps · 0 late |

**4 source ch/px → 4 wire bytes/px** — ICs: tm1814, ucs7604-8, sk6812-rgbw

| ports | channels/frame | 20 fps (50 ms) | 30 fps (33 ms) | 40 fps (25 ms) |
|---|---|---|---|---|
| 8 | 48,000 | ✅ 4.4% · 1.82/2.52 ms · 20.0 fps · 0 late | ✅ 6.2% · 1.82/2.54 ms · 30.2 fps · 0 late | ✅ 7.9% · 1.9/2.54 ms · 39.9 fps · 0 late |
| 16 | 96,000 | ✅ 6.7% · 3.33/5.12 ms · 20.0 fps · 0 late | ✅ 9.6% · 3.8/8.81 ms · 30.2 fps · 0 late | ✅ 12.3% · 3.28/4.77 ms · 39.9 fps · 0 late |
| 24 | 144,000 | ✅ 8.4% · 5.94/12.45 ms · 20.0 fps · 0 late | ✅ 12.5% · 4.92/9.3 ms · 30.2 fps · 0 late | ✅ 16.4% · 8.22/23.56 ms · 40.1 fps · 0 late |
| 32 | 192,000 | ✅ 10.4% · 6.96/15.47 ms · 20.0 fps · 0 late | ✅ 15.3% · 5.66/8.81 ms · 30.2 fps · 0 late | ✅ 19.9% · 6.26/8.96 ms · 40.0 fps · 0 late |
| 40 | 240,000 | ✅ 12.2% · 8.04/11.43 ms · 20.1 fps · 0 late | ✅ 17.8% · 6.8/10.96 ms · 30.2 fps · 0 late | ✅ 23.6% · 8.43/11.78 ms · 39.9 fps · 0 late |
| 48 | 288,000 | ✅ 14.0% · 11.25/22.89 ms · 20.0 fps · 0 late | ✅ 20.5% · 8.7/13.58 ms · 30.2 fps · 0 late | ✅ 26.9% · 9.09/15.48 ms · 40.1 fps · 0 late |

**5 source ch/px → 5 wire bytes/px** — ICs: ws2805

| ports | channels/frame | 20 fps (50 ms) | 30 fps (33 ms) | 40 fps (25 ms) |
|---|---|---|---|---|
| 8 | 60,000 | ✅ 4.9% · 2.14/2.72 ms · 20.0 fps · 0 late | ✅ 7.3% · 2.19/2.92 ms · 30.2 fps · 0 late | ✅ 10.2% · 2.24/2.86 ms · 39.9 fps · 0 late |
| 16 | 120,000 | ✅ 7.5% · 4.2/5.81 ms · 20.0 fps · 0 late | ✅ 11.3% · 4.21/5.71 ms · 30.2 fps · 0 late | ✅ 14.9% · 4.93/11.46 ms · 39.9 fps · 0 late |
| 24 | 180,000 | ✅ 9.8% · 5.17/7.56 ms · 20.0 fps · 0 late | ✅ 14.5% · 5.08/7.65 ms · 30.2 fps · 0 late | ✅ 19.2% · 6.27/8.62 ms · 39.9 fps · 0 late |
| 32 | 240,000 | ✅ 12.0% · 9.32/19.41 ms · 20.0 fps · 0 late | ✅ 17.8% · 7.14/12.43 ms · 30.2 fps · 0 late | ✅ 23.1% · 6.78/10.67 ms · 39.9 fps · 0 late |
| 40 | 300,000 | ✅ 14.1% · 9.55/14.93 ms · 20.0 fps · 0 late | ✅ 21.1% · 8.79/13.69 ms · 30.2 fps · 0 late | ✅ 27.2% · 10.78/18.92 ms · 40.1 fps · 0 late |
| 48 | 360,000 | ✅ 16.5% · 10.53/15.92 ms · 20.1 fps · 0 late | ✅ 24.4% · 9.57/16.1 ms · 30.2 fps · 0 late | ✅ 32.3% · 12.3/20.64 ms · 39.9 fps · 0 late |

**4 source ch/px → 8 wire bytes/px** — ICs: ucs7604-16, ucs8904-16

| ports | channels/frame | 20 fps (50 ms) | 30 fps (33 ms) | 40 fps (25 ms) |
|---|---|---|---|---|
| 8 | 48,000 | ✅ 6.4% · 3.04/4.27 ms · 20.0 fps · 0 late | ✅ 9.1% · 3.06/5.43 ms · 30.2 fps · 0 late | ✅ 11.7% · 3.01/5.05 ms · 39.8 fps · 0 late |
| 16 | 96,000 | ✅ 10.1% · 7.72/20.65 ms · 20.0 fps · 0 late | ✅ 15.2% · 6.28/14.05 ms · 30.2 fps · 0 late | ✅ 19.9% · 6.1/9.51 ms · 39.9 fps · 0 late |
| 24 | 144,000 | ✅ 13.5% · 9.22/12.71 ms · 20.0 fps · 0 late | ✅ 20.3% · 9.31/18.56 ms · 30.3 fps · 0 late | ✅ 26.6% · 10.14/17.47 ms · 39.9 fps · 0 late |
| 32 | 192,000 | ✅ 16.8% · 11.78/29.0 ms · 20.0 fps · 0 late | ✅ 25.2% · 10.72/16.16 ms · 30.2 fps · 0 late | ✅ 32.9% · 13.92/30.9 ms · 40.3 fps · 1 late |
| 40 | 240,000 | ✅ 20.5% · 17.18/28.83 ms · 20.2 fps · 0 late | ✅ 30.7% · 17.02/42.94 ms · 30.4 fps · 2 late | ✅ 40.2% · 15.35/28.91 ms · 39.9 fps · 2 late |
| 48 | 288,000 | ✅ 24.1% · 17.07/43.75 ms · 20.0 fps · 0 late | ❌ 36.0% · 24.21/54.2 ms · 30.2 fps · 7 late | ❌ 47.5% · 33.69/87.65 ms · 39.8 fps · 54 late |

**3 source ch/px → 6 wire bytes/px** — ICs: ucs8903-16

| ports | channels/frame | 20 fps (50 ms) | 30 fps (33 ms) | 40 fps (25 ms) |
|---|---|---|---|---|
| 8 | 36,000 | ✅ 5.4% · 2.37/2.89 ms · 20.0 fps · 0 late | ✅ 7.9% · 2.34/3.64 ms · 30.2 fps · 0 late | ✅ 10.0% · 2.76/4.83 ms · 39.8 fps · 0 late |
| 16 | 72,000 | ✅ 8.4% · 4.93/7.81 ms · 20.0 fps · 0 late | ✅ 12.5% · 4.94/9.56 ms · 30.2 fps · 0 late | ✅ 16.4% · 4.87/7.12 ms · 40.0 fps · 0 late |
| 24 | 108,000 | ✅ 11.0% · 6.98/12.91 ms · 20.0 fps · 0 late | ✅ 16.4% · 6.15/9.49 ms · 30.2 fps · 0 late | ✅ 21.0% · 7.36/10.02 ms · 40.0 fps · 0 late |
| 32 | 144,000 | ✅ 13.3% · 9.12/20.17 ms · 20.0 fps · 0 late | ✅ 19.7% · 7.25/9.97 ms · 30.2 fps · 0 late | ✅ 25.8% · 8.99/15.63 ms · 39.9 fps · 0 late |
| 40 | 180,000 | ✅ 16.0% · 9.85/15.53 ms · 20.0 fps · 0 late | ✅ 23.7% · 12.19/27.87 ms · 30.2 fps · 0 late | ❌ 31.1% · 23.57/50.97 ms · 40.1 fps · 17 late |
| 48 | 216,000 | ✅ 18.3% · 17.82/45.66 ms · 20.0 fps · 0 late | ✅ 28.1% · 17.39/45.98 ms · 30.2 fps · 2 late | ✅ 36.6% · 13.8/25.06 ms · 40.2 fps · 1 late |

**5 source ch/px → 10 wire bytes/px** — ICs: sm16825e

| ports | channels/frame | 20 fps (50 ms) | 30 fps (33 ms) | 40 fps (25 ms) |
|---|---|---|---|---|
| 8 | 60,000 | ✅ 6.9% · 3.63/5.61 ms · 20.0 fps · 0 late | ✅ 10.5% · 3.62/5.54 ms · 30.2 fps · 0 late | ✅ 13.7% · 4.52/9.61 ms · 39.9 fps · 0 late |
| 16 | 120,000 | ✅ 12.0% · 7.8/10.66 ms · 20.1 fps · 0 late | ✅ 17.8% · 9.21/17.48 ms · 30.2 fps · 0 late | ✅ 23.1% · 12.0/24.23 ms · 40.1 fps · 0 late |
| 24 | 180,000 | ✅ 16.2% · 11.56/25.28 ms · 20.0 fps · 0 late | ✅ 24.2% · 15.99/41.22 ms · 30.4 fps · 2 late | ✅ 31.1% · 16.86/31.08 ms · 40.5 fps · 3 late |
| 32 | 240,000 | ✅ 19.8% · 13.99/22.04 ms · 20.0 fps · 0 late | ✅ 29.9% · 13.41/23.97 ms · 30.2 fps · 0 late | ✅ 39.5% · 13.66/26.72 ms · 39.9 fps · 1 late |
| 40 | 300,000 | ✅ 24.7% · 20.91/41.41 ms · 20.0 fps · 0 late | ✅ 37.0% · 17.7/33.22 ms · 30.2 fps · 1 late | ❌ 47.4% · 27.45/75.68 ms · 39.9 fps · 21 late |
| 48 | 360,000 | ✅ 28.8% · 21.8/55.84 ms · 20.0 fps · 1 late | ❌ 43.8% · 30.54/63.2 ms · 30.2 fps · 28 late | ❌ 56.6% · 36.74/112.01 ms · 40.3 fps · 67 late |

**6 source ch/px → 6 wire bytes/px** — ICs: fw1906

| ports | channels/frame | 20 fps (50 ms) | 30 fps (33 ms) | 40 fps (25 ms) |
|---|---|---|---|---|
| 8 | 72,000 | ✅ 5.4% · 2.42/3.0 ms · 20.0 fps · 0 late | ✅ 8.1% · 2.4/3.43 ms · 30.2 fps · 0 late | ✅ 10.1% · 3.43/9.4 ms · 39.9 fps · 0 late |
| 16 | 144,000 | ✅ 8.6% · 5.43/11.38 ms · 20.0 fps · 0 late | ✅ 12.5% · 5.0/7.55 ms · 30.2 fps · 0 late | ✅ 16.3% · 4.77/6.82 ms · 39.9 fps · 0 late |
| 24 | 216,000 | ✅ 11.1% · 6.99/10.23 ms · 20.1 fps · 0 late | ✅ 16.5% · 6.53/10.47 ms · 30.2 fps · 0 late | ✅ 21.7% · 7.61/11.78 ms · 39.9 fps · 0 late |
| 32 | 288,000 | ✅ 13.6% · 8.61/19.58 ms · 19.9 fps · 0 late | ✅ 20.2% · 9.35/18.28 ms · 30.2 fps · 0 late | ✅ 26.6% · 9.76/20.41 ms · 39.9 fps · 0 late |
| 40 | 360,000 | ✅ 16.7% · 12.69/21.49 ms · 20.1 fps · 0 late | ✅ 24.2% · 10.99/21.37 ms · 30.2 fps · 0 late | ✅ 31.8% · 18.43/33.13 ms · 40.2 fps · 3 late |
| 48 | 432,000 | ✅ 19.2% · 12.68/19.2 ms · 20.0 fps · 0 late | ✅ 28.5% · 16.91/38.52 ms · 30.4 fps · 2 late | ✅ 37.0% · 15.43/30.35 ms · 39.9 fps · 1 late |

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
