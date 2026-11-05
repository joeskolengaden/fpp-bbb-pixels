# Configuring each chip in FPP (after `install.sh`)

On the **Channel Outputs → Pixel Strings (WL16)** page, per output you set a
**Pixel Timing** preset and per virtual-string a **Color Order**. Pick from:

| Chip | Pixel Timing | Color Order | Extra |
|---|---|---|---|
| WS2811 (800k), WS2812/B, WS2813, **WS2815**, SK6812, GS8208 | **Normal** | RGB/GRB/… | — |
| SK6812-RGBW, WS2814 | **Normal** | `GRBW` (or your chip's) | 4 ch/pixel |
| APA104 / APA106 / PL9823 / SK6822 | **APA104** | RGB/GRB | — |
| WS2811 @ 400 Kbps | **WS2811 400Kbps** | RGB | — |
| UCS1903 / UCS2903 | **UCS1903 400Kbps** | RGB | — |
| TM1803 | **TM1803** | RGB/GRB | — |
| **WS2805** / **SM16804** (8-bit) | Normal | `RGBWC` / `GRBWC` | RGB+WW+CW, 5 ch/px; wire order R,G,B,**WW,CW**. |
| **FW1906** (6 ch) | Normal | `RGBCWX` | 6 ch/px; wire order R,G,B,**CW,WW**,unused — model ch+3=cool-white, ch+4=warm-white, ch+5=dummy |
| **UCS8903** (16-bit RGB) | Normal | `RGB16` / `GRB16` | model as 3-ch RGB; FPP emits 6 bytes/px |
| **UCS8904** (16-bit RGBW) | Normal | `RGBW16` / `GRBW16` | model as 4-ch RGBW; FPP emits 8 bytes/px (value×257) |
| **SM16825 / SM16825E** (16-bit only — no 8-bit variant exists in silicon) | Normal | `RGBWC16` / `GRBWC16` | model as 5-ch RGB+WW+CW; FPP emits 10 bytes/px + an automatic 4-byte current-gain trailer, see below |
| **TM1814** (RGBW, inverted) | **TM1814** | `WRGB` | + current preamble, see below |
| **TM1829** (RGB, inverted) | **TM1829** | RGB/GRB | — |
| **TM1914** (RGB, inverted) | **TM1914** | RGB/GRB | + mode preamble, see below |
| **UCS7604** (RGBW, 8 or 16-bit) | **UCS7604** | `RGBW` (8-bit) or `RGBW16` (16-bit) | + config preamble, bit depth auto-detected from color order, see below |
| **TM1903**, **TM1934** (RGB), **TM1824** (RGBW) | **TM1903 / TM1824 / TM1934** | `RGB` / `RGBW` | TM1814's pulses but not inverted, no preamble (TM1934's optional mode frame is not sent: its bytes are not in the datasheet text) |
| **UCS2912**, **UCS1912** (12-channel drivers: 4 RGB groups per chip) | **UCS2912** / **UCS1912** | `RGB` | each chip eats 4 pixels of the port; both need a longer pulse than Normal |
| **TX1812**, **TX1818**, **GS8208B**, **SM16703SP** (RGB) / **LC8816E** (RGBW) | **TX1812 / TX1818 / LC8816E / GS8208B** | `GRB` / `GRBW` | the 0.3 / 0.9 us pulse family; TX1812 and LC8816E are GRB / GRBW |
| **TM1908** (RGB) | **TM1908** | `RGB` | + 9-byte header sent on every port (auto-switch mode + current, 2-25 mA via *Chip current*) |
| **LPD1886** (8-bit mode, GM pin floating) | **LPD1886 (8-bit)** | `RGB` | its 12-bit mode cannot be driven |
| **LC8812 / LC8812B** (RGB) | **LC8812 / LC8812B** | `GRB` | one T1H (750 ns) that is inside both datasheet versions |
| **any other single-wire chip** | **Custom timing** | whatever the chip uses | type T0H, T1H and the full bit period (ns) from the datasheet; tick *Inverted* for idle-high chips (TM18xx style). Bit period 1000-4000 ns |

Notes:
- **Color order = wire order.** For 5/6-ch the whites are appended positionally
  (src ch+3, ch+4, …) — arrange your xLights model to output channels in that order.
- **`pixelTiming` is per-output** (all ports on one BBB48String instance share
  it) — that part is unavoidable, the PRU program is compiled once for the
  whole board. The **preamble** that timing selects (TM1814/TM1914/UCS7604)
  defaults to applying on every port too, but can be opted out per port: add
  `"noPreamble": true` to a specific port's own JSON config (each entry in
  `config["outputs"]`) to skip the preamble on that port while keeping it on
  the rest. Useful for mixing chips that share compatible wire timing but not
  the same preamble need — e.g. UCS7604 (preset 10 is WS2812x-equivalent
  timing + a 15-byte preamble) on one port and plain WS2812 (no preamble) on
  another port of the same BBB: without the opt-out, the WS2812 port would
  get 5 pixels' worth of garbage prepended and its whole string would shift.

  This isn't exposed as a UI checkbox yet — hand-edit the port's entry (the
  matching object in that port's position within the `"outputs"` array) in
  `/home/fpp/media/config/co-bbbStrings.json` to add the field, then restart
  fppd. `sudo bash selftest.sh` will still validate the result.

## Note: "Normal" already covers most chips
Per xLights' IC compatibility database ([Pixels.cpp:119-126](../xLights/src-core/models/Pixels.cpp)),
**APA104, APA106, TM1803, TM1804, TM1809, UCS1903, UCS2903, SK6812, GS8208** and
~30 others are grouped as **`ws2811`-equivalent** — the ecosystem runs them all on
one 800 kHz timing. So try **Normal** first for these; use the dedicated preset
(APA104 / TM1803 / UCS1903-400) only if a long run or marginal batch misbehaves —
those presets are tighter to each datasheet, giving more margin, but aren't
required for typical use. Genuinely distinct (need their own preset/format):
**TM1814/TM1829/TM1914** (inverted), **WS2811-400/UCS1903-400** (400 Kbps),
**WS2805/FW1906** (5/6-ch), **UCS8903/8904/SM16825** (16-bit), **UCS7604** (config
preamble).

**SJ1221** is the one remaining gap — 12-bit (4.5 bytes/pixel), which can't be
expressed by FPP's byte-granular output map at all. See
[IC_IMPLEMENTATION_STUDY.md](IC_IMPLEMENTATION_STUDY.md) and
[REFERENCE.md](REFERENCE.md) for the full cross-codebase IC map.

## Preambles/trailer (fully automatic once selected)

All of these are built via a generalized decoration-byte mechanism — synthetic
virtual strings sourced from FPP's constant always-zero channel, each carrying
one literal byte value in its own `brightnessMap`. They consume **no sequence
channels** and need no Output Processor setup.

**TM1814** — selecting Pixel Timing = TM1814 prepends the 8-byte frame
`3F 3F 3F 3F C0 C0 C0 C0` (max-current code 0x3F on all four channels, then its complements) to
every port on the instance, and inverts the waveform. Set color order to
**`WRGB`** and configure pixels normally.
- Current is fixed at the chip's maximum (6-bit code 0x3F = 38 mA, the same bytes
  NeoPixelBus sends at max current; releases before 2026-11 sent `FF…/00…`). Lower *brightness* per string to reduce power — an
  adjustable current setting would need a UI field (future work).

**TM1914** — Pixel Timing = TM1914 prepends the 6-byte frame
`FF FF F5 00 00 0A` and inverts the waveform (identical wire timing to TM1814,
different preamble). Plain `RGB`/`GRB` color order (no white channel).

**UCS7604** — Pixel Timing = UCS7604 prepends a 15-byte frame (`FF×6, 00, 02`
sync, then a config byte + 4 current bytes + 2 reserved). The config byte is
chosen automatically: `0x8B` (16-bit/800kbps/RGBW) if **any** virtual string on
that port uses a color order ending in `16` (e.g. `RGBW16`), else `0x03`
(8-bit/800kbps/RGBW). Per-channel current defaults to `0x08` of a `0x00-0x0F`
range (~mid-range). No waveform inversion — same timing as Normal.

**SM16825E** — needs **no Pixel Timing selection**; the trailer is triggered
automatically by color order `RGBWC16`/`GRBWC16` alone. A mandatory 4-byte
current-gain frame is appended **after** the pixel data (not a preamble — the
chip reads it from the end of the frame). ⚠️ **This overrides whatever current
the module powered up with, every single frame, with no UI opt-out.** The
shipped default is a conservative gain index of 5 (of 0-31, roughly
10-310mA/channel) ≈ **58mA/channel** — if your modules are rated for more,
edit the `g` value in `patch_pixelstring.py`'s SM16825E trailer block (search
for "SAFETY") and reinstall.

The inverted waveform was checked on the BeagleBone's own pad (P8-30), not with
a scope. Those three presets idle high; Normal idles low. TM1814 and TM1914 at
`T0_TIME` 330 measured a 0-bit low of 378 ns and 375 ns (datasheet 310–410) and
a 1-bit low of about 725 ns. TM1829's 0-bit still measured about 219 ns, short of
the 300 ns NeoPixelBus figure, so its defines were left at 250/750/1150.

## Verify an install
`sudo bash selftest.sh` — checks the channel maps and every preamble/trailer,
compiles all 11 PRU presets (if an output is configured), and the SPIPixels
factory symbol.

## How to read the limits panel (pixel-strings page)

1. **Pick the Pixel Timing** for your chip. The card under it lists the chips it covers and a table: *"One port can drive up to
   N pixels"* at 20, 25, 30 and 40 fps for each pixel width (RGB = 3 bytes, RGBW = 4, 16-bit RGBW = 8, ...).
2. **Choose "Plan for"** — the frame rate of the sequences you will play (most shows are 20 fps; 40 fps needs much shorter strings).
3. **Look at the status line.** Green *All ports fit* means you are inside the limit. Red *N port(s) too long* names the ports and the
   limit; the pixel-count boxes of those ports get a red outline. **Fix automatically** shortens them to the limit.
4. **Save** warns you if a port is still over. Saving anyway is allowed: the pixels beyond the limit just never update.

The limit is **per port**: using more ports does not lower it (all ports shift together), up to 48. For setup bytes: TM1814, TM1914
and UCS7604 add a setup frame to *every* port, so a board runs one of those families, not a mix.

## Chip current and TM1914 mode (pixel-strings page)

Three chips have a software-settable output current; the page shows a **Chip current** box when one of them is selected
(TM1814, UCS7604, or an SM16825E colour order such as `RGBWC16`). It is a **percent of that chip's own range**, and the line next
to it says what it means:

| Chip | 0 % | 50 % | 100 % | When empty |
|---|---|---|---|---|
| TM1814 | 6.5 mA per channel | about 22 mA | 38 mA | 38 mA (maximum, as before) |
| UCS7604 | level 1 of 15 | level 8 | level 15 | level 8 |
| SM16825E | gain 0 = 10 mA | gain 15 = 160 mA | gain 31 = 310 mA | gain 5 = 61 mA (as before) |

Lower it to cut power draw or heat on long runs. For **TM1914** a **TM1914 mode** menu appears: *DIN only* (normal wiring, the
default), *Auto-switch (backup signal)* for strips wired with the backup data line, or *FDIN only*.
Both are saved in the output config as `chipCurrent` (0-100) and `tm1914Mode` (`din`/`auto`/`fdin`); leave them out and nothing changes.

## Clocked chips added to SPIPixels

`hd108` / `ns108` (16-bit per channel, frame from the manufacturer's spec V1.2), the HD modes `apa102hd` / `sk9822hd` / `hd107shd`
(per-pixel 5-bit brightness chosen from the colour, so dim levels have much finer steps), and the aliases `apa101`, `apa102c`,
`ws2803`, `lpd8803`, `lpd8809`, `ucs8812`, `d705`, `lpd1101`, `ucs6909`, `ucs6912s`. See `plugins/SPIPixels/README.md`.

## Custom timing (any single-wire chip with a datasheet)

Choose **Custom timing** in the Pixel Timing menu and three boxes appear: **T0H** (high time of a 0 bit), **T1H** (high time of a 1 bit) and **Bit period**,
all in nanoseconds exactly as printed in the datasheet (use the typical values), plus an **Inverted (idle high)** tick box. The page checks the numbers
(T0H 250-3000, T1H at least 100 ns above T0H, bit period 1000-4000 and at least 150 ns above T1H) and the limits panel uses your bit period.

- The driver subtracts the same PRU overhead the presets use (about 50 ns from each high time, about 110 ns from the period). The **bit period is
  measured on the board** (frame time / bits, within 1% on every value tested from 1000 to 4000 ns); the **pulse widths are not independently
  measured** (that needs a scope or the ESP32 analyzer), exactly like every other preset.
- A bit period under about 1000 ns is outside what this PRU loop can produce. 12-bit and self-clocking chips cannot be driven.
- Colour order and any chip setup frame are up to you: pick the order the chip uses; chips that need a setup frame (preamble) need a dedicated preset.
- Values from a hand-edited config are clamped, and a value that is not a number falls back to the default: a bad file cannot stop fppd.
  (`customT0`, `customT1`, `customPeriod`, `customInvert` in `co-bbbStrings.json`, next to `pixelTiming: 11`.)
