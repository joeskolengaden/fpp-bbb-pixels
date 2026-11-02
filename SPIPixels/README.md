# SPIPixels — SPI pixel-chip channel output for FPP

An FPP plugin that adds a **`SPIPixels`** channel-output type for driving
**clocked (SPI) LED pixel chips** straight off a Raspberry Pi or BeagleBone:

| Protocol | Chips | Default clock | Native order |
|----------|-------|---------------|--------------|
| `apa102` | APA102 / DotStar | 8 MHz | BGR |
| `sk9822` | SK9822 (APA102 clone) | 8 MHz | BGR |
| `hd107s` | HD107S (fast APA102) | 20 MHz | BGR |
| `apa102hd` / `sk9822hd` / `hd107shd` | the same chips in **HD mode**: the 5-bit per-pixel brightness is chosen from the colour, so low light levels get ~8x finer steps (e.g. brightness 10/255 → colour byte 155 at 2/31 instead of 10 at 31/31) | 8 / 8 / 20 MHz | BGR |
| `hd108` / `ns108` | **HD108 / NS108**, 16 bits per channel (8-bit input widened ×257, full scale stays full scale); frame per Rose Lighting spec V1.2: ≥128 zero bits, then 1 marker bit + 3×5-bit gains (set to max) + R,G,B 16-bit, then padding clocks | 20 MHz | RGB |
| `sk9826` / `sk9826mini` / `sk9826ec20` | **Opsco SK9826 family**: 16-bit, same frame as HD108 (datasheet Rev 04); the part lights in **G,R,B** order, so use colour order GRB | 10 MHz | GRB |
| `tlc59711` / `tlc5971` | **TI TLC59711 / TLC5971**: constant-current driver, **4 RGB outputs per chip**, 16-bit, no latch pin (latches when the clock goes idle). 28 bytes per chip; chips are sent last-to-first. Each pixel = one RGB output (B,G,R slots). **The whole chain must fit one spidev transfer**: 584 pixels per output with the default 4096-byte `spidev.bufsiz` (the plugin warns at start-up if not; raise `spidev.bufsiz` on the kernel command line for longer chains) | 1 MHz (chip max 10) | BGR |
| `apa107` / `lc8822` / `lc8823` | APA107 (datasheet frame = APA102), LC8822 / LC8823 (sold as APA102-compatible; frame not independently verified) | 8 MHz | BGR |
| `ws2801` | WS2801 | 1 MHz | RGB |
| `lpd8806`| LPD8806 | 2 MHz | GRB |
| `lpd6803`| LPD6803 | 1 MHz | RGB (15-bit) |
| `p9813`  | P9813 / Cool Neon Total Control | 1 MHz | BGR |
| `sm16716`| SM16716 | 16 MHz | RGB |
| `sm16726`| SM16726 (SM16716-compatible) | 16 MHz | RGB |

**Aliases** (same frame as the chip they follow, so the names xLights and other controllers use work as-is):
`apa101`, `apa102c` = `apa102` · `sk9822ec20`, `sk9822mini` = `sk9822` · `ws2803` = `ws2801` · `lpd8803`, `lpd8809`, `ucs8812` = `lpd8806` ·
`d705`, `lpd1101`, `ucs6909`, `ucs6912s` = `lpd6803`.

> **MBI6020** was investigated twice. The second pass found the real
> manufacturer datasheet and confirmed the exact frame — but it's still not
> implemented, for a structural reason rather than a missing source: MBI6020
> needs a stateful 3-phase sequence (one-time config packet, one-time
> dot-correction packet, then repeating gray-scale packets), each with its
> own preamble encoding the exact chain length, plus a silent >172-cycle
> idle prefix between packets instead of a clocked end frame. None of that
> fits this file's stateless `(chip, rgb, nPix) → bytes` shape — it would
> need its own small state machine, not a `case` in the existing switches.
> See `SPIChipFormat.h`'s header comment for the full frame spec if this is
> ever worth building as its own thing.

Works on **FPP 5.4 → 9.x** on both **Raspberry Pi and BeagleBone** — it talks the
generic Linux `spidev` interface, so there's one code path for every board.

> **How it loads:** the build produces `libfpp-co-SPIPixels.so`, installed onto the
> linker path. When you configure a channel output of type `SPIPixels`, fppd
> `dlopen`s it. The same source compiles against both FPP APIs and exports the
> right factory automatically — `createOutputSPIPixels` on 5.4, `createPlugin`
> (ChannelOutputPlugin) on 6.x–9.x — verified compiling against real 5.4 headers.

### What this does NOT do
Single-wire chips (WS2811/WS2812/WS2815/SK6812/TM1814/UCS…) need precise
sub-microsecond timing that FPP generates from **core** code — the BeagleBone PRU
assembly and the Pi `rpi_ws281x` library — which a loadable plugin can't
reproduce (and the BBB PRU code is CC-BY-ND, so a modified copy can't be
shipped). Use FPP's built-in **Pixel Strings** output for those.

All per-string behaviour (color order, brightness, gamma, grouping, zig-zag,
reverse, null pixels) is handled by FPP's own `PixelString` class, so it behaves
exactly like the built-in pixel string outputs.

---

## Install

1. Copy this folder to `/home/fpp/media/plugins/SPIPixels` (the directory name
   **must** be `SPIPixels` for the config page), or install from the Plugin
   Manager once published.
2. Build + install the driver on the device:
   ```bash
   cd /home/fpp/media/plugins/SPIPixels
   bash scripts/fpp_install.sh
   ```
   This runs `make` against the local FPP headers (`/opt/fpp/src`), producing
   `libfpp-co-SPIPixels.so`, then copies it to `/usr/local/lib` and runs
   `ldconfig` so fppd can find it. Because it compiles against the installed FPP,
   the ABI automatically matches your version (5.4 … 9.x).
3. Restart FPPD (**Status/Control → Restart FPPD**).

## Enable SPI on the board

**Raspberry Pi** — enable SPI and (for big strings) raise the spidev buffer:
```
# /boot/config.txt  (or /boot/firmware/config.txt)
dtparam=spi=on
# optional 2nd SPI bus for a 3rd/4th port:
dtoverlay=spi1-3cs
# allow large single transfers (pixels * bytes-per-pixel):
# /boot/cmdline.txt  -> append:  spidev.bufsiz=65536
```
Devices appear as `/dev/spidev0.0`, `/dev/spidev0.1`, …

**BeagleBone** — enable an SPI overlay (e.g. `BB-SPIDEV0`) so `/dev/spidev*`
exists. On FPP BBB images SPI0 is usually already available on the P9 header.

### Wiring
Each port uses two lines: **MOSI → DATA (DI)** and **SCLK → CLOCK (CI)**, plus
common **GND**. (WS2801/APA102/etc. are 5 V logic — level-shift the Pi/BBB 3.3 V
data+clock for reliable long runs.)

---

## Configure

Open **Content Setup → SPI Pixels** in the FPP UI and edit the JSON, or hand-edit
`config/co-other.json`. One channel-output entry can hold several SPI ports:

```json
{
  "type": "SPIPixels",
  "enabled": 1,
  "startChannel": 1,
  "channelCount": 900,
  "outputs": [
    {
      "device": "spidev0.0",
      "protocol": "apa102",
      "spiSpeed": 8000000,
      "portNumber": 0,
      "virtualStrings": [
        { "description": "Roof", "startChannel": 0, "pixelCount": 300,
          "groupCount": 0, "reverse": 0, "colorOrder": "BGR",
          "nullNodes": 0, "endNulls": 0, "zigZag": 0,
          "brightness": 100, "gamma": "1.0" }
      ]
    }
  ]
}
```

Key points:
- Output **`startChannel`** is **1-based** (FPP channel 1 = `1`); the output-level
  `channelCount` is the total channels across all ports.
- Each **`virtualStrings[].startChannel`** is **0-based** (FPP channel 1 = `0`),
  matching how FPP stores pixel-string configs.
- `colorOrder` lets you match the chip (APA102/SK9822/HD107S/P9813 = `BGR`).
- `spiSpeed` is optional — omit to use the per-chip default above.

> ⚠️ Configure these outputs **only via this plugin's page**. The core
> **Status/Control → Other** page doesn't know the `SPIPixels` type and will drop
> the entry if you Save there.

---

## Verify on the device

```bash
# 1. library installed + findable?
ls -l /usr/local/lib/libfpp-co-SPIPixels.so && ldconfig -p | grep SPIPixels

# 2. loaded + ports up? (after configuring an output + Restart FPPD)
grep -i SPIPixels /home/fpp/media/logs/fppd.log
# expect: "SPIPixels: apa102 on /dev/spidev0.0, 300 pixels @ 8000000 Hz"
#   "Unknown Channel Output type" => the .so isn't on the linker path
#   "cannot open /dev/spidev..." => SPI not enabled on the board

# 3. SPI device present?
ls -l /dev/spidev*

# 3. light it up: FPP UI -> Status/Control -> Display Testing -> pick the channel
#    range, run an R/G/B cycle, watch the pixels.
```

`make test` (in `tests/`) runs the wire-framing unit tests on any machine:
```bash
cd tests && c++ -std=gnu++2a -I../src test_format.cpp -o t && ./t
```

## Performance notes
- Output is synchronous (sent in `SendData`). An APA102 string of 600 px @ 8 MHz
  is ~2.5 ms; with many ports the per-frame total is the sum, so spread big runs
  across SPI buses or lower the frame rate if you push thousands of pixels.
- WS2801 latches after an idle gap; for very long WS2801 runs raise
  `spidev.bufsiz` so the frame goes out in one transfer (see above).

## Layout
```
SPIPixels/
├── Makefile              builds libfpp-co-SPIPixels.so (compile on-device)
├── pluginInfo.json       plugin metadata (minFPPVersion 5.4)
├── menu.inc / plugin.php config UI
├── scripts/              fpp_install.sh (build + install + ldconfig) / fpp_uninstall.sh
├── src/
│   ├── SPIChipFormat.h   pure, unit-tested chip wire framing
│   └── SPIPixels.cpp     output driver + dual-API (5.4 + 6.x-9.x) factories
└── tests/test_format.cpp native unit tests for the framing
```

GPL v2 (same terms as FPP's own pixel-string channel outputs).
