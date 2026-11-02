## System load by data path (1,500 px on every populated port, FSEQ playback, data changing each frame)

Each cell: fppd CPU % of the single core · work ms per frame (avg/max: sequence read + channel map + copy to PRU memory) · achieved fps · late frames in the 6 s window.

**3 source ch/px → 3 wire bytes/px** — ICs: normal-grb, slow, apa104, ws2811-400, ucs1903-400, tm1803, tm1829, tm1914

| ports | channels/frame | 20 fps (50 ms) | 30 fps (33 ms) | 40 fps (25 ms) |
|---|---|---|---|---|
| 8 | 36,000 | ✅ 4.0% · 2.01/2.78 ms · 20.0 fps · 0 late | ✅ 5.9% · 2.09/4.2 ms · 30.2 fps · 0 late | ✅ 7.4% · 1.87/2.67 ms · 39.9 fps · 0 late |
| 16 | 72,000 | ✅ 6.6% · 3.78/5.84 ms · 20.0 fps · 0 late | ✅ 9.3% · 3.36/5.22 ms · 30.2 fps · 0 late | ✅ 12.1% · 4.22/10.32 ms · 39.8 fps · 0 late |
| 24 | 108,000 | ✅ 8.8% · 6.3/13.35 ms · 20.2 fps · 0 late | ✅ 12.6% · 5.09/10.81 ms · 30.2 fps · 0 late | ✅ 16.7% · 5.27/7.29 ms · 39.9 fps · 0 late |
| 32 | 144,000 | ✅ 11.6% · 6.71/9.79 ms · 20.1 fps · 0 late | ✅ 17.2% · 7.99/19.8 ms · 30.2 fps · 0 late | ✅ 22.3% · 10.55/21.41 ms · 40.5 fps · 0 late |
| 40 | 180,000 | ✅ 13.8% · 7.99/12.49 ms · 20.0 fps · 0 late | ✅ 20.2% · 10.67/19.35 ms · 30.4 fps · 0 late | ✅ 27.0% · 9.98/14.69 ms · 39.9 fps · 0 late |
| 48 | 216,000 | ✅ 15.9% · 12.65/44.28 ms · 20.0 fps · 0 late | ✅ 23.8% · 9.99/15.63 ms · 30.2 fps · 0 late | ✅ 31.6% · 21.33/57.87 ms · 40.3 fps · 5 late |

**4 source ch/px → 4 wire bytes/px** — ICs: tm1814, ucs7604-8, sk6812-rgbw

| ports | channels/frame | 20 fps (50 ms) | 30 fps (33 ms) | 40 fps (25 ms) |
|---|---|---|---|---|
| 8 | 48,000 | ✅ 5.4% · 3.21/5.83 ms · 20.0 fps · 0 late | ✅ 7.8% · 2.42/3.13 ms · 30.2 fps · 0 late | ✅ 10.2% · 2.61/3.76 ms · 39.9 fps · 0 late |
| 16 | 96,000 | ✅ 8.6% · 6.92/16.98 ms · 20.0 fps · 0 late | ✅ 13.7% · 6.76/12.72 ms · 30.2 fps · 0 late | ✅ 16.3% · 6.3/15.51 ms · 40.0 fps · 0 late |
| 24 | 144,000 | ✅ 11.4% · 10.33/28.99 ms · 20.2 fps · 0 late | ✅ 17.0% · 8.6/20.61 ms · 30.3 fps · 0 late | ✅ 22.4% · 8.4/15.71 ms · 40.1 fps · 0 late |
| 32 | 192,000 | ✅ 14.3% · 12.75/29.95 ms · 20.3 fps · 0 late | ✅ 21.4% · 9.68/15.97 ms · 30.2 fps · 0 late | ✅ 28.1% · 10.85/15.06 ms · 40.1 fps · 0 late |
| 40 | 240,000 | ✅ 17.1% · 10.29/16.44 ms · 20.0 fps · 0 late | ✅ 25.8% · 10.41/17.7 ms · 30.4 fps · 0 late | ❌ 34.2% · 19.58/33.0 ms · 39.6 fps · 8 late |
| 48 | 288,000 | ✅ 20.4% · 13.91/30.88 ms · 20.0 fps · 0 late | ✅ 30.3% · 10.56/13.29 ms · 30.2 fps · 0 late | ✅ 40.2% · 18.99/46.24 ms · 39.9 fps · 5 late |

**5 source ch/px → 5 wire bytes/px** — ICs: ws2805

| ports | channels/frame | 20 fps (50 ms) | 30 fps (33 ms) | 40 fps (25 ms) |
|---|---|---|---|---|
| 8 | 60,000 | ✅ 6.4% · 3.39/5.13 ms · 20.0 fps · 0 late | ✅ 9.6% · 3.38/5.7 ms · 30.2 fps · 0 late | ✅ 11.9% · 3.39/4.59 ms · 39.9 fps · 0 late |
| 16 | 120,000 | ✅ 10.1% · 5.94/9.15 ms · 20.0 fps · 0 late | ✅ 15.0% · 6.21/9.3 ms · 30.2 fps · 0 late | ✅ 19.5% · 7.57/15.48 ms · 40.2 fps · 0 late |
| 24 | 180,000 | ✅ 13.6% · 8.21/12.48 ms · 20.1 fps · 0 late | ✅ 20.2% · 7.53/13.16 ms · 30.4 fps · 0 late | ✅ 26.8% · 8.96/16.06 ms · 40.2 fps · 0 late |
| 32 | 240,000 | ✅ 17.1% · 13.32/34.34 ms · 20.1 fps · 0 late | ✅ 26.0% · 9.5/16.83 ms · 30.2 fps · 0 late | ✅ 33.8% · 12.33/23.15 ms · 40.1 fps · 0 late |
| 40 | 300,000 | ✅ 20.6% · 13.65/21.78 ms · 20.2 fps · 0 late | ✅ 31.0% · 15.58/31.13 ms · 30.2 fps · 0 late | ✅ 41.0% · 15.13/32.76 ms · 39.8 fps · 2 late |
| 48 | 360,000 | ✅ 24.2% · 12.94/16.17 ms · 20.0 fps · 0 late | ✅ 36.8% · 21.97/57.91 ms · 30.2 fps · 3 late | ❌ 47.2% · 26.3/57.38 ms · 39.9 fps · 17 late |

**4 source ch/px → 8 wire bytes/px** — ICs: ucs7604-16, ucs8904-16

| ports | channels/frame | 20 fps (50 ms) | 30 fps (33 ms) | 40 fps (25 ms) |
|---|---|---|---|---|
| 8 | 48,000 | ✅ 8.6% · 6.17/13.89 ms · 20.2 fps · 0 late | ✅ 12.4% · 4.62/7.33 ms · 30.2 fps · 0 late | ✅ 16.3% · 5.53/10.94 ms · 40.0 fps · 0 late |
| 16 | 96,000 | ✅ 14.6% · 11.32/22.83 ms · 20.1 fps · 0 late | ✅ 21.3% · 9.62/18.43 ms · 30.2 fps · 0 late | ✅ 28.0% · 11.77/20.28 ms · 40.1 fps · 0 late |
| 24 | 144,000 | ✅ 19.9% · 14.83/30.09 ms · 20.2 fps · 0 late | ✅ 30.0% · 15.08/33.14 ms · 30.4 fps · 1 late | ✅ 39.2% · 18.44/43.27 ms · 39.9 fps · 4 late |
| 32 | 192,000 | ✅ 25.3% · 17.13/31.52 ms · 20.0 fps · 0 late | ✅ 38.0% · 20.64/38.83 ms · 30.2 fps · 3 late | ❌ 50.3% · 25.53/47.76 ms · 39.8 fps · 41 late |
| 40 | 240,000 | ✅ 31.0% · 19.57/38.84 ms · 20.0 fps · 0 late | ❌ 45.9% · 41.58/89.29 ms · 30.2 fps · 28 late | ❌ 59.4% · 36.07/81.94 ms · 40.0 fps · 31 late |
| 48 | 288,000 | ✅ 36.9% · 21.67/37.0 ms · 20.0 fps · 0 late | ❌ 54.6% · 38.58/82.76 ms · 30.9 fps · 27 late | ❌ 69.8% · 36.0/79.63 ms · 40.2 fps · 35 late |

**3 source ch/px → 6 wire bytes/px** — ICs: ucs8903-16

| ports | channels/frame | 20 fps (50 ms) | 30 fps (33 ms) | 40 fps (25 ms) |
|---|---|---|---|---|
| 8 | 36,000 | ✅ 7.0% · 3.86/5.45 ms · 20.0 fps · 0 late | ✅ 10.3% · 4.04/7.46 ms · 30.2 fps · 0 late | ✅ 13.3% · 5.12/9.93 ms · 40.2 fps · 0 late |
| 16 | 72,000 | ✅ 11.1% · 6.77/10.13 ms · 20.1 fps · 0 late | ✅ 17.0% · 8.17/18.25 ms · 30.1 fps · 0 late | ✅ 22.2% · 7.87/12.48 ms · 40.0 fps · 0 late |
| 24 | 108,000 | ✅ 15.4% · 8.68/11.47 ms · 20.0 fps · 0 late | ✅ 23.3% · 14.18/39.26 ms · 30.2 fps · 1 late | ✅ 30.6% · 11.89/21.08 ms · 40.1 fps · 0 late |
| 32 | 144,000 | ✅ 19.4% · 10.64/13.44 ms · 20.0 fps · 0 late | ✅ 29.3% · 11.9/19.36 ms · 30.2 fps · 0 late | ✅ 38.8% · 15.74/25.71 ms · 39.9 fps · 7 late |
| 40 | 180,000 | ✅ 23.7% · 15.87/32.34 ms · 20.0 fps · 0 late | ✅ 35.8% · 18.61/37.02 ms · 30.2 fps · 1 late | ❌ 46.5% · 34.26/78.04 ms · 39.8 fps · 41 late |
| 48 | 216,000 | ✅ 28.0% · 16.36/25.88 ms · 20.0 fps · 0 late | ✅ 42.4% · 23.17/56.59 ms · 30.2 fps · 3 late | ❌ 54.2% · 30.3/80.11 ms · 40.0 fps · 58 late |

**5 source ch/px → 10 wire bytes/px** — ICs: sm16825e

| ports | channels/frame | 20 fps (50 ms) | 30 fps (33 ms) | 40 fps (25 ms) |
|---|---|---|---|---|
| 8 | 60,000 | ✅ 9.9% · 5.55/8.57 ms · 20.0 fps · 0 late | ✅ 14.3% · 5.44/8.93 ms · 30.2 fps · 0 late | ✅ 19.1% · 6.76/10.71 ms · 40.0 fps · 0 late |
| 16 | 120,000 | ✅ 17.1% · 9.57/12.17 ms · 20.0 fps · 0 late | ✅ 25.5% · 15.79/39.52 ms · 30.2 fps · 2 late | ✅ 33.7% · 20.36/49.88 ms · 40.2 fps · 3 late |
| 24 | 180,000 | ✅ 23.9% · 16.71/30.71 ms · 20.0 fps · 0 late | ✅ 36.0% · 25.91/68.89 ms · 30.2 fps · 5 late | ❌ 47.4% · 32.63/78.04 ms · 39.4 fps · 40 late |
| 32 | 240,000 | ✅ 30.6% · 21.39/58.53 ms · 20.0 fps · 1 late | ✅ 46.2% · 20.5/43.33 ms · 30.2 fps · 2 late | ❌ 59.4% · 31.26/66.75 ms · 39.3 fps · 48 late |
| 40 | 300,000 | ✅ 38.0% · 26.52/84.62 ms · 20.0 fps · 1 late | ❌ 55.0% · 46.66/134.12 ms · 30.2 fps · 37 late | ❌ 71.0% · 37.88/85.13 ms · 40.0 fps · 37 late |
| 48 | 360,000 | ✅ 45.1% · 31.1/63.35 ms · 20.0 fps · 2 late | ❌ 66.4% · 41.05/91.77 ms · 30.4 fps · 45 late | ❌ 72.0% · 49.7/112.11 ms · 39.9 fps · 67 late |

**6 source ch/px → 6 wire bytes/px** — ICs: fw1906

| ports | channels/frame | 20 fps (50 ms) | 30 fps (33 ms) | 40 fps (25 ms) |
|---|---|---|---|---|
| 8 | 72,000 | ✅ 7.1% · 3.89/5.54 ms · 20.0 fps · 0 late | ✅ 10.3% · 4.02/8.71 ms · 30.2 fps · 0 late | ✅ 13.5% · 4.57/9.16 ms · 39.9 fps · 0 late |
| 16 | 144,000 | ✅ 11.4% · 6.83/10.35 ms · 20.0 fps · 0 late | ✅ 17.0% · 7.01/10.82 ms · 30.3 fps · 0 late | ✅ 22.7% · 9.27/13.5 ms · 40.1 fps · 0 late |
| 24 | 216,000 | ✅ 15.8% · 9.08/14.78 ms · 20.0 fps · 0 late | ✅ 23.4% · 9.8/15.72 ms · 30.2 fps · 0 late | ✅ 31.2% · 11.93/24.02 ms · 39.9 fps · 0 late |
| 32 | 288,000 | ✅ 20.1% · 14.77/31.69 ms · 20.1 fps · 0 late | ✅ 30.0% · 18.49/36.61 ms · 30.2 fps · 1 late | ❌ 39.0% · 31.17/52.08 ms · 40.0 fps · 19 late |
| 40 | 360,000 | ✅ 24.2% · 13.74/19.95 ms · 20.0 fps · 0 late | ✅ 36.5% · 13.01/15.54 ms · 30.2 fps · 0 late | ❌ 47.7% · 23.74/50.83 ms · 40.0 fps · 15 late |
| 48 | 432,000 | ✅ 28.4% · 23.44/79.72 ms · 20.0 fps · 1 late | ✅ 42.5% · 16.54/23.08 ms · 30.2 fps · 0 late | ❌ 55.5% · 28.82/65.53 ms · 40.0 fps · 57 late |

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
