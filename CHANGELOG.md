# Changelog

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
