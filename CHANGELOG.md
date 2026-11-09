# Changelog

## 1.0.4 (unreleased)
Limits panel and documentation only; no timing changed.
- Custom timing now says so when T0H is under 350 ns: this PRU loop cannot make a 0-bit shorter than about 220 ns, so the pulse comes out longer than typed (not an error, an amber note).
- Preset 15 (TX1812 / TX1818 / LC8816E / GS8208B / SM16824E) carries the same caveat: its 0.3 us 0-bit has not been checked with a scope and may come out shorter than the datasheet figure.
- README and CONFIG no longer present the pad-sampler pulse widths in 1.0.1 and 1.0.2 as measurements: the sampler reads in ~200 ns steps, so they are indicative. The idle level and bit period are what it proves.
- hwtest/stress_ics.py: per-chip stress test that judges the wire (computed wire time, the driver's own LIMIT warning, output really running), replacing an earlier sweep whose "HOLDS" only meant fppd kept its frame rate.

## 1.0.3 (2026-11-05)
GS8608 is named on the Normal timing menu. WLED drives it with the WS2812 waveform and notes that the chip shows a test pattern unless data keeps arriving, so the limits card says the same. No new pulse times.

SM16824E moved from the Normal label to the 0.3/0.9 µs preset. Its datasheet (IBZOZOV1.2) is 300/900 ns ±50 ns at 800 kbps, which is outside the Normal 1-bit. The 16-bit current-gain word at the end of that frame is not sent. SM16803P, SM16813PB, SM16823E and DP1903 were checked and left out: the first three still have no printed frame, and the DP1903 numbers in FastLED and in a forum quote of a missing PDF do not agree.

## 1.0.2 (2026-11-05)
TM1829 short-pulse define is 310 ns, up from 250. On a BeagleBone Green, with the preset period of 1150 ns, defines of 250 and 280 ns both collapsed to a 0-bit of about 220 ns: the wait had already expired. Define 310 measured a 0-bit low of 314 ns and, with T1 left at 750, a 1-bit low of about 806 ns (NeoPixelBus 300/800). The bit period was about 1234 ns and the line idled high. Installs that still have the unpublished 270/740 trial are put back to 310/750.

## 1.0.1 (2026-11-05)
TM1814 and TM1914 short-pulse defines are 330 ns, up from 310. On a BeagleBone Green the pad measured a 0-bit low of 378 ns and 375 ns (datasheet window 310–410, typical 360) and a 1-bit low of 724 ns and 726 ns (typical 720). Both idle high. A 48-port sequence at 20 fps holds: TM1814 at 1100 pixels per port (44.4 ms on the wire), TM1829 and TM1914 at 1500 (45.2 ms and 45.3 ms). TM1814 at 1500 pixels is 60.5 ms, past the frame; fppd keeps 20 fps and logs that only the first 82% of each port updates.

TM1829 is unchanged. A trial define of 270 ns still measured a 0-bit of about 219 ns, short of the 300 ns NeoPixelBus figure, so the defines stay 250/750/1150.

## 1.0.0 (2026-11-03)
First versioned release: everything built and verified on a BeagleBone Green running FPP 5.4.1.

### Single-wire (PRU) chips
- Pixel Timing presets 2-10: APA104/APA106/PL9823/SK6822, WS2811 400 kHz, UCS1903 400 kHz, TM1803, TM1814, TM1829, WS2805, TM1914 (inverted waveforms), UCS7604.
- **New: Custom timing (preset 11)** for any single-wire chip with a datasheet (T0H, T1H, bit period, inverted flag; clamped, bad values cannot stop fppd).
- **New: datasheet presets 12-18**: TM1903/TM1824/TM1934, UCS2912, UCS1912, TX1812/TX1818/LC8816E/GS8208B, TM1908 (with its 9-byte header), LPD1886 (8-bit), LC8812/LC8812B.
- 5/6-channel and 16-bit colour orders (WS2805, FW1906, UCS8903/8904, SM16825/E), chip-current controls (TM1814, UCS7604, SM16825E, TM1908), TM1914 mode.
- About 1.6x faster frame preparation, a frame-budget log line and a per-port limit check at start-up.
- FPP page: pixel-limit panel per chip and frame rate, a red **Fix automatically** button, Custom timing boxes, live budget readout.

### Clocked (SPI) chips - SPIPixels plugin
- APA102/SK9822/HD107S (+HD brightness modes), HD108/NS108, WS2801, LPD8806, LPD6803, P9813, SM16716/SM16726.
- **New:** TLC59711/TLC5971 (4 RGB outputs per chip), SK9826 family, APA107, LC8822/LC8823, SK9822-EC20/mini; reads the kernel's spidev transfer limit.

### Health and stability
- `doctor.sh` health check (patch state, frame budget, output-thread budget rule, clock, services), `system-fixes.sh` (clock persistence for boards without an RTC), start-up guard that warns when an FPP upgrade removed the patches.
- Installer is all-or-nothing: validates every patch anchor on copies first, rolls back to stock if the rebuild fails.

### Streaming (sACN / ArtNet / DDP)
- Measured the board's own packet-processing limits (see PERFORMANCE.md); `system-fixes.sh` can raise the UDP receive buffer to 2 MB (removed every socket drop in the stress test), `doctor.sh` warns when streaming is configured with the small default.

### Measured limits (see PERFORMANCE.md)
- 48 ports x 1,650 pixels at 20 fps and 48 x 830 at 40 fps (Normal timing) hold with fppd at 12-17% CPU; wire time, not CPU, is the limit.
- 8-minute soak, 8 fppd restarts and a hard kill all clean.
