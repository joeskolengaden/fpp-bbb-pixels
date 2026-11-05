# Which other pixel ICs could be added?

> **Status (2026-11-05).** Sections 1 and 2 below are the research record. What they called "worth adding" is built: menu labels, HD108/NS108, APA102 HD mode, chip-current controls, TM1914 mode, and presets 12–18 (Round 2). Two rows stayed off on purpose. SM16803P / SM16813PB / SM16823E still have no datasheet that prints the frame bytes, so no trailer was added. UCS7604 at 1.6 Mbps needs a 100 ns pulse, which this PRU loop cannot hold and the pad cannot check.
>
> This pass: **GS8608** is a Normal label (WLED `TYPE_GS8608`: same driver as WS2812, and a test pattern unless data keeps arriving). **SM16824E** moved onto the 0.3/0.9 µs preset. Its sheet IBZOZOV1.2 prints T0H/T1H 0.3/0.9 µs ±50 ns at 800 kbps, which is outside Normal's measured 1-bit. The same sheet's 16-bit current word is not sent, because RGBW is shared with other chips and a silent trailer would hit them. **DP1903** stays off: a forum quote of a missing PDF says 0.5/2.0 µs, FastLED says 0.4/1.4 µs at 800 kHz and 0.8/2.4 µs at 400 kHz, and neither pair sits inside Normal or UCS1903-400.

Checked against: our own catalogue (`IC_IMPLEMENTATION_STUDY.md` §3, which maps every chip in xLights' vocabulary), WLED's chip list (copy in the
FPP tree), FastLED master (README, `chipsets.h`, `fl/chipsets/hd108.h`) and NeoPixelBus master (feature/method files). A chip is "new" only if it is
in none of our supported presets, colour orders or SPI protocols.

**Bottom line: almost everything popular already works.** The leftover work in the sections below was finished in later passes, except the chips the status note still refuses.

## 1. Already works — only the name is missing from the menus (cheap: documentation/labels, no new code)

| Chip | Why it already works |
|---|---|
| **WS2816** (16-bit RGB) | FastLED drives it as a WS2812 800 kHz stream with 16-bit channels = our `GRB16` order on *Normal* timing (6 bytes/pixel) |
| **SM16824E** | Moved to the 0.3/0.9 µs preset. Sheet IBZOZOV1.2 is T0H 0.3 µs / T1H 0.9 µs ±50 ns, not Normal. The 16-bit end-of-frame current word is not sent |
| **WS2812B-V5, WS2812B-Mini-V3** | 220/360/580 ns, inside *Normal* |
| **WS2818 / WS2813 / WS2815**, **TM1804 / TM1809 / TM1812**, **GS8206/8208**, **SM16703**, **UCS1903B / UCS2903** | in xLights' "ws2811 group" → *Normal* |
| **UCS2904, SK6812-RGBW, WS2814, SM16804** (RGBW) | *Normal* + a 4-character order (`GRBW`, `RGBW`, `WRGB`) |
| **GW6205 at 800 kHz** | FastLED 400/400/400 ns, a 1.2 µs bit, inside *Normal* |
| SPI aliases: **WS2803** (= WS2801), **LPD8803/8809, UCS8812** (= LPD8806), **D705, LPD1101, UCS6909/6912S** (= LPD6803), **APA101, APA102C** (= APA102) | same frames; the plugin only accepts the primary names today, so accepting the aliases is a few lines |

## 2. Worth adding

| # | Candidate | What it is | Effort | Notes |
|---|---|---|---|---|
| 1 | **HD108 / NS108** (SPI, 16-bit) | APA102-style, 16 bits per channel + three 5-bit gains | small–medium (plugin) | Frame (FastLED): 8 zero bytes start (NeoPixelBus sends 16), then per LED 8 bytes: `0x80 | R gain<<2 | G gain>>3`, `G gain<<5 | B gain`, then R, G, B as 16-bit big-endian; end `FF` × (n/2 + 4). The two libraries **disagree** on start/end length, so use the longer of each (extra clocks are harmless). Wants SPI mode 3 (the plugin currently sets mode 0). 8→16-bit expansion can happen inside the plugin (×257) |
| 2 | **APA102 "HD" mode** | uses the 5-bit global brightness field for smoother low-brightness fades (FastLED `APA102HD`) | small (plugin) | optional `hd` flag; today the field is fixed at 31 |
| 3 | **Current / gain control for chips we already drive** | TM1814 (6.5–38 mA), UCS7604 (4-bit per channel), SM16825E (5-bit gain) | small–medium | currently fixed: TM1814 at max, SM16825E at ~58 mA, UCS7604 at 0x08 — a "current" field per chip in the UI would be the most useful ease-of-use upgrade of all |
| 4 | **TM1914 mode** | NeoPixelBus: mode byte `F5` = DIN only (what we send), `FA` = FDIN only, `FF` = auto-switch | tiny | auto-switch is what backup-signal wiring wants |
| 5 | **SM16803P / SM16813PB / SM16823E** | RGB chips with 4-bit-per-channel current set in **2 bytes at the END** of the stream (NeoPixelBus) | small–medium | fits the trailer mechanism SM16825E already uses; timing not confirmed here (likely 800 kHz) so the datasheet needs checking first |
| 6 | **UCS7604 at 1.6 Mbps** | FastLED 100/350/175 ns (a 625 ns bit): doubles the pixels per port (16-bit RGBW would go from 612 to ~1,200 at 20 fps) | medium, **risky** | needs a PRU preset with a bit period roughly half the shortest we run today; whether the PRU loop can hold it, and whether the 100 ns pulse comes out right, can only be settled with a scope or the ESP32 analyser |

## 3. Possible but niche

| Candidate | Why it is niche |
|---|---|
| **MY9221 / MY9231 / MY9291** (clocked, 16-bit, command header + latch) | cheap LED-bulb drivers; the latch is a clock pause, which spidev can do between two messages, but it is a bespoke frame. Listed in the study as *C* |
| **TX1812** (NeoPixelBus 300/600/600/300 ns = 900 ns bit) | rare; would need a preset faster than ours |
| **UCS1912 / UCS2912** | FastLED marks UCS1912 "never tested"; no verified timing |

## 4. Cannot be done on this hardware (unchanged from the study)

| Chips | Reason |
|---|---|
| **SJ1221, GW6205 (12-bit), LPD1886, TLC5973, TLS3001/3002/3005, GECE, 9pdot/SPXL** | 12-bit (4.5 bytes/pixel), self-clocking, or proprietary framing; FPP's output map is byte-granular and the PRU loop is a fixed 3-phase bit loop |
| **MBI6020 / MBI6033** | a stateful three-phase sequence (config, dot-correction, then data) that does not fit a per-frame blob |
| **DMX pixel chips** (UCS512, WS2822, SM1x-DMX) | receivers on an RS-485 DMX line: use FPP's serial/DMX outputs |
| **TLC5947 / TLC59711** (NeoPixelBus) | constant-current LED drivers, not addressable pixels |
| **Pixie** (serial, 115 200 baud) | a UART protocol, not the PRU or SPI path |

## 5. Suggested order
1. Names/aliases in the menus (section 1) — an afternoon, no risk.
2. Current/gain control (2.3) and TM1914 mode (2.4) — the best usability gain for chips already in use.
3. HD108 and APA102-HD (2.1, 2.2) — the one genuinely new, popular chip family.
4. SM168x3 (2.5) after a datasheet check.
5. UCS7604 1.6 Mbps (2.6) only if a scope or the analyser is available.

## Round 2 (2026-11-02): added from new datasheet research (`research/single_wire_candidates.md`, `research/spi_candidates.md`)

**Built.** Bit periods measured on the board (within 1% on all 18 presets); SPI frames cross-checked against an independent framer (225 vectors per protocol).
Pulse widths (T0H/T1H) are NOT independently measured on this board (the pad sampler quantises to ~200 ns): they follow the same compensation as every other preset.

| Added | How | Source / confidence |
|---|---|---|
| **Custom timing** (Pixel Timing 11): T0H / T1H / bit period / inverted | one PRU block fed from the config, clamped, bad values cannot stop fppd | any single-wire chip with a datasheet, bit period 1000-4000 ns |
| **TM1903, TM1934 (RGB), TM1824 (RGBW)**, preset 12 | 360/720/1300 ns, not inverted | Titan Micro datasheets, HIGH |
| **UCS2912**, **UCS1912**, presets 13, 14 | 400/800 and 250/1000 | datasheets (UCS1912 via a translation), HIGH |
| **TX1812, TX1818, LC8816E (RGBW), GS8208B, SM16703SP**, preset 15 | 300/900/1250 | datasheets, HIGH (TX1812 from a web transcription) |
| **TM1908**, preset 16 | 240/480/1250 + 9-byte header (auto-switch mode, current 2-25 mA) | Titan Micro V1.2, HIGH |
| **LPD1886 (8-bit)**, preset 17 | 200/600/1250 | timing HIGH; the 24-bit assumption is LOW (FastLED) |
| **LC8812 / LC8812B**, preset 18 | 300/750/1250, inside both datasheet versions | MEDIUM (the two versions disagree) |
| **TLC59711 / TLC5971** (SPIPixels `tlc59711`) | TI constant-current driver, 4 RGB outputs per chip, 16-bit; 28 bytes per chip, chips sent last first, latches when the clock idles | TI datasheets HIGH + Adafruit / NeoPixelBus MEDIUM |
| **SK9826 / SK9826MINI / SK9826-EC20** | alias of the HD108 frame, 10 MHz, colour order GRB | Opsco datasheet Rev 04, HIGH |
| **APA107**, **LC8822 / LC8823**, **SK9822-EC20 / mini** | aliases of APA102 / SK9822 | APA107 HIGH; LC882x sold as compatible, frame not independently verified |
| labels only: SK6813, CS8812, HC2912C, WS2813B-RGBW, WS2811C, WS2812C | already inside Normal | datasheet windows contain the Normal pulses |

**Researched, deliberately not built** (so nobody repeats the search):
- **WS281x over SPI MOSI**: encodings are known (4 bits at 3.2 MHz, 5 bits at 4.0 MHz) but spidev here is capped at 4096 bytes per transfer (~340 pixels), the AM335x MOSI idle level and word gaps cannot be verified without a scope, and the PRU already does the job on 48 ports.
- **MY9221/9231/9291/9268**: sample on both clock edges and latch by pulsing DI while the clock idles; SPI cannot do either.
- **TLC5947/48, DM633/634/DM13A, MBI5xxx, HL1606, A6281 (needs CS wired as latch)**: need a latch pin or a free-running grayscale clock.
- **No datasheet with timing/frame found**: TM1830, TM1815, UCS2109/2114, UCS5604, XL-2812, WS2851, SM16803P/13PB/23E, INK1003, DM412, ICND2110, RM2021, HD109, APA102-8192/65536. GS8608 has no timing sheet either; WLED drives it as WS2812, which is why it is a Normal label and not a preset.

## Round 3 (2026-11-05): datasheet pass, no new waveform

| Chip | Result |
|---|---|
| **GS8608** | Label on Normal, plus a note that it shows a built-in pattern when the line goes quiet. Source: WLED `const.h` `TYPE_GS8608`. No new PRU define. |
| **SM16824E** | Label moved to preset 15. Source: Sunmoon/Linkage sheet IBZOZOV1.2 (800 kbps, 0.3/0.9 µs ±50 ns, 32-bit RGBW pixels, then 16 bits of 4-bit-per-channel gain). Gain word not sent. |
| **SM16803P / SM16813PB / SM16823E** | Not built. Chinaasic lists SM16823E as SID, 800 kbps, 4-bit gain per channel, but the page is not a timing table or a frame diagram. The SM16824E frame must not be copied onto a 3-channel part. |
| **DP1903** | Not built. FastLED `TIMING_DP1903_800KHZ` is 400/1400 ns and `TIMING_DP1903_400KHZ` is 800/2400 ns. A forum quote of the Depuw PDF (the PDF 404s) says 500/2000 ns and a 24 µs reset. Those three disagree, and none is Normal or the UCS1903-400 preset. |
- **12/20-bit chips** (UCS5603, UCS9812, GE8822, LPD1886 12-bit): the output map is byte-granular. **APA109, SK9816**: single-wire despite being listed as clocked.
