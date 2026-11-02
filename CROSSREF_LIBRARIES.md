# Signal-generation cross-reference: FastLED, NeoPixelBus, Adafruit NeoPixel

Compares what `fpp-bbb-pixels` (single-wire PRU presets + preambles) and `SPIPixels` (clocked chips)
put on the wire against three independent open-source drivers.

Sources read:
- **FastLED** — local copy, `~/Documents/Arduino/libraries/FastLED/src/chipsets.h` (Mar 2025 snapshot; also re-checked against GitHub master).
- **Adafruit NeoPixel** — local copy, `Adafruit_NeoPixel.cpp` (ARM/nRF timing constants).
- **NeoPixelBus** (Makuna) — GitHub master: `NeoEsp32RmtMethod.h`, `*GenericMethod.h`, `NeoTm1814Features.h`, `NeoTm1914Features.h`.

Not covered by any of the three (no reference exists): UCS7604, UCS8903/8904 (16-bit), SM16825E, FW1906, and the
`WS2805` byte layout. Those can only be verified against datasheets / the on-wire capture.

Reproduce: `hwtest/crossref_timing.py`, `hwtest/spi_xcheck.py`, `hwtest/wire_check.py`.

## 1. Single-wire timing

Library numbers are normalised to (T0H / T1H / period). FastLED `T1,T2,T3` → `T0H=T1, T1H=T1+T2, period=T1+T2+T3`.
Our PRU defines sit below nominal by design (asm header: "defines are slightly lower as there is overhead in resetting
the clocks"); the table assumes +50 ns.

| # | chip | ours (defines) | ours on wire (+50) | library → T0H/T1H/period | delta |
|---|---|---|---|---|---|
| 0 | WS2812 (Normal, stock FPP) | 200/675/1150 | 250/725/1200 | FastLED 250/875/1250 · NeoPixelBus 400/800/1250 · Adafruit 250/800/1250 | within WS2812 tolerance; stock FPP |
| 2 | APA104/PL9823/SK6822 | 300/1300/1610 | 350/1350/1660 | FastLED PL9823 350/1360/1710 · NeoPixelBus Apa106 350/1350/1700 | ≤ 10 ns (T0H/T1H) |
| 3 | WS2811 400 kHz | 450/1150/2400 | 500/1200/2450 | Adafruit 500/1200/2500 · FastLED & NeoPixelBus 800/1600/2500 | matches Adafruit/datasheet; libs run slower |
| 4 | UCS1903 400 kHz | 450/1900/2400 | 500/1950/2450 | FastLED 500/2000/2500 | ≤ 50 ns |
| 5 | TM1803 | 650/1300/1950 | 700/1350/2000 | FastLED 700/1800/2500 | T0H exact; T1H/period shorter (datasheet 680/1360/2040) |
| 6 | TM1814 inv. | 350/700/1150 | **400**/750/1200 | NeoPixelBus 360/720/1250 | **T0H +40, T1H +30** |
| 7 | TM1829 inv. | 250/750/1150 | 300/800/1200 | NeoPixelBus 300/800/1200 · FastLED 340/680/1230 | exact vs NeoPixelBus |
| 8 | WS2805 | 250/740/990 | 300/790/1040 | NeoPixelBus 300/790/1090 | exact T0H/T1H |
| 9 | TM1914 inv. | 350/700/1150 | **400**/750/1200 | NeoPixelBus 360/720/1250 | **T0H +40, T1H +30** |

Reading it: presets 2, 4, 7, 8 were evidently derived as *library minus ~50 ns*, and land within 10 ns of NeoPixelBus/FastLED.
Presets 3 and 5 follow the datasheets instead of the libraries — the libraries use deliberately slower, centred timings.
Both decode on spec-compliant chips because the chip threshold sits between the two; it is a design choice, not an error.

**Outlier: TM1814 / TM1914 (presets 6 and 9).** Consistently applying the library−50 convention to NeoPixelBus's
360/720/1250 gives defines of ~310/670/1200. We use 350/700/1150, so T0H lands ~40 ns above the library figure and ~10 ns
below the chip's 410 ns maximum. The window is only held while PRU overhead ≤ 60 ns (`hwtest/static_timing.py`).
**Recommendation: `T0_TIME` 350 → 310** for presets 6 and 9 (also suggested by `IC_IMPLEMENTATION_STUDY.md` §4.3).
Confirm against the first measured Normal-preset capture before applying.

FastLED's TM1829 (340/680/1230) differs from NeoPixelBus (300/800/1200): the two libraries disagree with each other;
ours matches NeoPixelBus and sits inside the chip's accepted range for both.

## 2. Preambles / colour order

| item | ours | reference | result |
|---|---|---|---|
| TM1914 preamble | `FF FF F5 00 00 0A` | NeoPixelBus default (DIN-only): `FF FF F5` + complement `00 00 0A` | **identical** |
| TM1814 preamble | `FF FF FF FF 00 00 00 00` | NeoPixelBus at max current: `3F 3F 3F 3F C0 C0 C0 C0` (6-bit value `(mA×10−65)/5`, second half = bitwise complement) | **differs** — see below |
| TM1814 byte order | W,R,G,B | NeoPixelBus `Neo4ByteFeature<W,R,G,B>` | identical |
| RGBW order semantics | W-first `WRGB` = W,R,G,B on wire; W-last `GRBW` = G,R,B,W | Adafruit `NEO_WRGB` / `NEO_GRBW` (wire order = name) | identical |
| 400 kHz / 800 kHz | presets 3/0 | Adafruit `NEO_KHZ400` / `NEO_KHZ800` | consistent |

**TM1814 preamble.** Ours is an exact 8-bit complement pair (`FF`/`00`), so a chip that checks `C2 == ~C1` accepts it, and a
chip that reads only the low 6 bits sees the same maximum-current value (`0x3F`) as NeoPixelBus. It differs only in the top
two bits of each current byte (`11` vs `00`). `FF`/`00` was chosen when FPP could only emit `00`/`FF` literals; the
generalised literal-byte mechanism now allows `3F×4 C0×4` (2 synthetic strings, same cost). NeoPixelBus's form is the one
proven on real TM1814 strips (it is what WLED ships), so switching removes the dependence on how the chip treats those bits.
**Recommendation: change the TM1814 preamble to `3F 3F 3F 3F C0 C0 C0 C0`** (touch points: `patch_pixelstring.py`,
`test_maps.cpp`, `hwtest/verify_presets.py` `TM1814_PRE`, analyzer `SIG_TM1814` — keep both signatures matchable).

## 3. SPI / clocked chips

| chip | ours | FastLED | NeoPixelBus | result |
|---|---|---|---|---|
| APA102 start | `00×4` | `00×4` | `00×4` | identical |
| APA102 pixel header | `FF` (E0 \| 31) | `E0 \| brightness` (31 default → `FF`) | settings in data | identical |
| APA102 end | `FF × max(4,(n+15)/16)` | `FF 00 00 00` × (n/32+1) | `(n+15)/16` × `00` (after a `00×4` reset frame) | count compatible; **value differs** |
| **SK9822 / HD107S end** | **same as APA102** (`FF…`) | **`00 00 00 00`** × (n/32+1) | zeros | **differs** |
| WS2801 | raw RGB, no framing | raw RGB + ≥ 1 ms idle | raw + ≥ 500 µs idle | identical (idle is covered by FPP's ≥ 20 ms frame period) |
| LPD8806 pixel | `0x80 \| (v>>1)` | `(v>>1)\|0x80` **+1 for v in 1..253** (rounds up) | encoded upstream | ≤ 1 LSB of 7 bits |
| LPD8806 latch | `(n+31)/32` × `00` | `(3n+63)>>6` × `00` (≈ n/21) | `(n+31)/32` bytes before and after (value `00` start; end reported `FF`) | ours matches Adafruit/NeoPixelBus count; FastLED sends more |
| LPD6803 pixel | `1 RRRRR GGGGG BBBBB` | identical | identical | identical |
| **LPD6803 end** | **`00 × max(1,(n+15)/16)`** (½ bit per pixel) | `FF 00 00 00` × (n/32+1) ≈ **n/8 bytes** | **`(n+7)/8` × `00`** | **ours is half of both libraries** |
| P9813 flag/colour order | flag = `C0 \| ~c0>>2 \| ~c1>>4 \| ~c2>>6` over the 3 wire bytes | same formula (wire order B,G,R) | start/end `00×4` | identical formula |
| P9813 end | `00 × 4·max(1,⌈n/64⌉)` | `00×4` | `00×4` | ours ≥ both |
| SM16716 | 50 zeros, then `1`+RGB per pixel | `1`+RGB per pixel, 50 zeros trailing | 50 zeros + `1`, RGB, `1` marker per pixel | equivalent bit stream in steady state |

**LPD6803 end frame (recommend fixing).** FastLED and NeoPixelBus independently send ≈ one zero clock per pixel
(`n/8` bytes); we send half of that. On long chains the tail pixels may not be clocked through. Fix:
`end = max(1, (n+7)/8)` zero bytes in both `spiWireSize` and `spiFormat` (extra zero clocks are harmless).

**SK9822 / HD107S end frame (recommend fixing).** FastLED treats SK9822 and HD107 as APA102 *with an all-zero end frame*,
and NeoPixelBus uses zeros for the whole family. We send `FF`. Sending zeros is accepted by APA102 as well (clocks only),
so zeros are the safe common denominator. Fix: end-frame byte `0x00` for `sk9822` and `hd107s` (or for all three).

## 4. What is *not* a finding
- Default SPI clocks differ (ours: APA102 8 MHz, HD107S 20 MHz, LPD8806 2 MHz; FastLED 6/40/12 MHz). Ours are conservative; configurable via `spiSpeed`.
- Presets 3 and 5 differ from the libraries on purpose (datasheet vs. library margin).
- Normal (preset 0) is stock FPP timing and unchanged.

## 5. Changes applied
1. TM1814 preamble → `3F×4 C0×4` (`patch_pixelstring.py`, upgrades already-patched files; analyzer matches both forms).
2. TM1814/TM1914 `T0_TIME` 350 → 310 (`patch_asm.py`, upgrades already-patched files). Revisit once the first Normal-preset capture measures the PRU overhead.
3. LPD6803 end frame → `ceil(n/8)` zero bytes (`SPIChipFormat.h`).
4. SK9822 / HD107S end frame → zeros, new `SPIChip::SK9822` (`SPIChipFormat.h`); the analyzer now accepts an all-zero or all-FF APA102 end frame.
