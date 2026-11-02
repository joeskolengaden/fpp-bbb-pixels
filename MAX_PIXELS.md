# Maximum pixels per port — BeagleBone Green, FPP 5.4.1

Measured on the board itself (`hwtest/measure_limits.py`, `hwtest/spibench.c`, `hwtest/max_pixels.py`); regenerate with
`python3 hwtest/max_pixels.py`. Frame rate = how often FPP hands the PRU a new frame; a sequence at 20 fps has a 50 ms frame.

## What limits a port

**Single-wire (PRU).** One port's frame must finish inside the frame interval. Measured: if it does not, the PRU output is
**cut off mid-frame** (the pixels at the far end of the string stop updating) — it does not slow down gracefully.

| test (Normal, GRB, 50 ms frame) | frame length on the pad | verdict |
|---|---|---|
| 1,560 px | 47.20 ms | intact |
| 1,600 px | 48.37 ms | intact |
| 1,640 px | 49.65 ms | intact (last size that fits) |
| 1,700 px | 48.7 ms (needs 51.3) | cut off |
| 2,000 px | 49.8 ms (needs 60.3) | cut off at ~49.8 ms |
| WS2811-400: 780 / 820 px | 47.19 / 49.61 ms | intact |
| WS2811-400: 860 / 900 px | 49.92 ms (needs 51.95 / 54.37) | cut off |

The model below predicted 1,641 (Normal) and 823 (WS2811-400) before those tests; both held to within the 40-pixel step used.

    frame time = (preamble + N × bytes/px + trailer) × 8 × bit period      must be ≤  interval − chip reset − ~0.2 ms

The **bit period is measured per chip format** (frame length ÷ bits, sampled from the output pad via the GPIO input register).
The PRU adds a steady **+106 to +124 ns** to every programmed `LOW_TIME` (Normal 1150 → 1256 ns, TM1814 1150 → 1258 ns,
WS2811-400 2400 → 2517 ns, APA104 1610 → 1726 ns, WS2805 990 → 1102 ns), which lands each preset on the library/datasheet
period: TM1814 1258 vs NeoPixelBus 1250; WS2811-400 2517 vs 2500; APA104 1726 vs 1700; WS2805 1102 vs 1090.

**Not a limit:** the PRU outputs share one bit clock, so port count does not slow a port down; the board also stayed healthy
with **all 48 outputs × 1,600 px (76,800 px, 230 KB per frame)** — fppd running, load ≈ 1.0, 147 MB free, no errors
(`hwtest/stability48.py`). The DDR frame buffers come from a 48 MiB CMA pool. The FPP UI limits one *virtual string* to
1,600 px, but several virtual strings can be chained on a port.

### Single-wire: max pixels per port (per chip, by frame rate)

| IC / format | bytes/px | bit period (measured) | µs/pixel | 20 fps (50 ms) | 25 fps (40 ms) | 33 fps (30 ms) | 40 fps (25 ms) | 50 fps (20 ms) |
|---|---|---|---|---|---|---|---|---|
| WS2812/WS2811-800 (Normal, GRB) | 3 | 1256 ns | 30.2 | 1641 | 1309 | 978 | 812 | 646 |
| ws281x Slow variant | 3 | 1331 ns | 31.9 | 1549 | 1236 | 923 | 766 | 610 |
| APA104/PL9823/SK6822 | 3 | 1726 ns | 41.4 | 1200 | 959 | 718 | 597 | 476 |
| WS2811 @ 400 Kbps | 3 | 2517 ns | 60.4 | 823 | 657 | 492 | 409 | 326 |
| UCS1903/UCS2903 @ 400 Kbps | 3 | 2518 ns | 60.4 | 823 | 657 | 492 | 409 | 326 |
| TM1803 | 3 | 2074 ns | 49.8 | 999 | 798 | 597 | 497 | 396 |
| TM1814 RGBW (inverted) | 4 | 1258 ns | 40.2 | 1230 | 981 | 733 | 609 | 485 |
| TM1829 RGB (inverted) | 3 | 1256 ns | 30.1 | 1645 | 1313 | 982 | 816 | 650 |
| WS2805 RGB+WW+CW (5ch) | 5 | 1102 ns | 44.1 | 1122 | 895 | 669 | 555 | 442 |
| TM1914 RGB (inverted) | 3 | 1256 ns | 30.1 | 1643 | 1311 | 980 | 814 | 648 |
| UCS7604 RGBW 8-bit | 4 | 1257 ns | 40.2 | 1226 | 977 | 729 | 605 | 480 |
| UCS7604 RGBW 16-bit | 8 | 1260 ns | 80.6 | 612 | 488 | 364 | 301 | 239 |
| SK6812/WS2814 RGBW (GRBW) | 4 | 1257 ns | 40.2 | 1235 | 987 | 738 | 614 | 490 |
| UCS8903 16-bit RGB | 6 | 1259 ns | 60.4 | 819 | 653 | 488 | 405 | 322 |
| UCS8904 16-bit RGBW | 8 | 1259 ns | 80.6 | 614 | 490 | 366 | 304 | 241 |
| SM16825E 16-bit RGBWC + trailer | 10 | 1260 ns | 100.8 | 490 | 391 | 292 | 242 | 193 |
| FW1906 6ch (RGBCWX) | 6 | 1259 ns | 60.4 | 819 | 653 | 488 | 405 | 322 |

Chip reset assumed (µs): Normal/Slow/WS2805/UCS7604/16-bit/SM16825E/FW1906 300 · TM1814/TM1829/TM1914 200 · SK6812 80 ·
APA104/WS2811-400/UCS1903-400/TM1803 50. Longer resets shave a few pixels; they never change the order of magnitude.

## Clocked (SPI) chips

A frame is pushed in 4 KB `spidev` chunks, as SPIPixels does. Measured transfer time on this board:
`t = 1.057 × (bytes × 8 / clock) + 0.13 ms per KB + 0.39 ms per chunk` (36 + 20 runs, 0 transfer errors). Effective ceiling ≈
0.8 MB/s at 8 MHz, 1.1 MB/s at 12 MHz, 1.4 MB/s at 20 MHz, 1.8 MB/s at 24 MHz.

| Clocked chip | plugin default clock | at default: 50 ms | 40 ms | 30 ms | 25 ms | 20 ms | at 12 MHz: 50 / 25 ms | at 24 MHz: 50 / 25 ms |
|---|---|---|---|---|---|---|---|---|
| APA102 | 8 MHz | 9564 | 7650 | 5737 | 4781 | 3824 | 13144 / 6571 | 21172 / 10580 |
| SK9822 | 8 MHz | 9564 | 7650 | 5737 | 4781 | 3824 | 13144 / 6571 | 21172 / 10580 |
| HD107S | 20 MHz | 18982 | 15122 | 11285 | 9404 | 7523 | 13144 / 6571 | 21172 / 10580 |
| HD108 / NS108 (16-bit) | 20 MHz | 9070 | 7225 | 5392 | 4493 | 3593 | 6280 / 3139 | 10117 / 5055 |
| WS2801 | 1 MHz | 1911 | 1522 | 1149 | 955 | 761 | 17800 / 8900 | 28672 / 14329 |
| LPD8806 | 2 MHz | 3697 | 2940 | 2212 | 1833 | 1455 | 17617 / 8808 | 28376 / 14181 |
| LPD6803 | 1 MHz | 2696 | 2147 | 1621 | 1346 | 1072 | 25128 / 12563 | 40476 / 20227 |
| P9813 | 1 MHz | 1409 | 1123 | 847 | 704 | 561 | 13143 / 6571 | 21172 / 10579 |
| SM16716/SM16726 | 16 MHz | 21092 | 16986 | 12692 | 10483 | 8398 | 17086 / 8542 | 27523 / 13753 |


`apa102hd` / `sk9822hd` / `hd107shd` use the same frame size as their plain versions, so they have the same limits.

The BBG is rarely the limit here: the practical ceiling is the **chip's rated clock** and signal integrity over long runs
(APA102 strips misbehave above ~6–12 MHz on long runs; WS2801 / LPD8806 / P9813 are normally run at 1–2 MHz). Use the
"at 12 MHz" columns only for chips and wiring that are rated for it.

## Not yet measured

- Frame length seen from outside the board (ESP32 analyzer on P8-30) — `hwtest/verify_presets.py` checks frame byte counts.
- The all-48-ports **timing** (as opposed to stability): fppd preparing the next frame starves the on-board sampler on this
  single core, so the pad-sampling method cannot time it. The shared-clock argument and the stability run say it is the same
  as one port; an ESP32 capture would confirm.
- T0H/T1H pulse widths (the sampler measures frame and bit *period*, not the 250–400 ns pulses).
