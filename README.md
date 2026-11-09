# fpp-bbb-pixels

**More pixel chips for Falcon Player (FPP) on a BeagleBone: about 40 ICs, a Custom timing mode for any other single-wire chip, a per-port pixel-limit panel and a health check.**
Installs on stock **FPP 5.4.x** from the Plugin Manager or from a release bundle, and uninstalls cleanly. See **[INSTALL.md](INSTALL.md)**, **[CHANGELOG.md](CHANGELOG.md)** and the measured limits in **[PERFORMANCE.md](PERFORMANCE.md)**.

| I want to... | Go to |
|---|---|
| install it (Plugin Manager, offline, by hand) | [INSTALL.md](INSTALL.md) |
| know how to set up a chip | [CONFIG.md](CONFIG.md) |
| know how many pixels a port can drive | [MAX_PIXELS.md](MAX_PIXELS.md), [PERFORMANCE.md](PERFORMANCE.md) |
| see which chips were researched and why some are not supported | [IC_CANDIDATES.md](IC_CANDIDATES.md), [research/](research/) |
| make a release | [RELEASING.md](RELEASING.md) |

---


A single, reproducible installer that adds a broad set of LED-driver ICs to FPP's
BeagleBone outputs, on top of the built-in `ws281x`. Consolidates work previously
applied piecemeal into one idempotent, backed-up, re-appliable package.

**Target:** BeagleBone, **FPP 5.4+** (5.x line). Timings are datasheet-verified
(cross-checked against FastLED).

```
sudo bash install.sh          # install
sudo bash install.sh --test   # install + run the self-test
sudo bash uninstall.sh        # revert to stock
sudo bash selftest.sh         # validate an existing install
```

**Safe by construction:** the installer first validates *every* patch anchor on
copies (all-or-nothing — a version mismatch aborts before any edit), preflights the
environment (BeagleBone, toolchain, ≥1.3 GB free), and if the rebuild fails it
**auto-rolls back to stock and restarts fppd**. See [CONFIG.md](CONFIG.md) for
per-chip setup (Pixel Timing + color order, and the TM1814 preamble).

## Install as an FPP plugin (or by hand)
**Plugin Manager:** Content Setup → Plugins → paste the repo's `pluginInfo.json` URL → Install. FPP runs `scripts/fpp_install.sh` (the same `install.sh`: patches,
rebuilds two FPP libraries, builds SPIPixels; a few minutes, fppd stops while it compiles) and adds **Pixel IC Support** to the menu: a status page with the health
check and a *Re-apply patches* button. **Uninstall** in the Plugin Manager runs `uninstall.sh` (restores stock FPP).
Why it is not a "pure" plugin: the BeagleBone pixel driver (`BBB48String`, its PRU program and the pixel-strings page) is part of FPP itself and has no plugin hook, so the
single-wire features have to patch those files; the SPI chips (SPIPixels) are a normal plugin. An FPP upgrade replaces the patched files; the plugin's `preStart.sh` guard
notices on the next fppd start, writes a warning to `fppd.log` and shows it on the plugin page, and one click re-applies everything.
Before publishing run `scripts/bundle-spipixels.sh` so the repo carries the SPIPixels source. Supported: FPP 5.x on BeagleBone (the patchers abort safely on other versions).

## Chip support added

### Single-wire (PRU) — `Pixel Timing` dropdown on the WL16/strings page
T0H/T1H/period below are the PRU's own `T0_TIME`/`T1_TIME`/`LOW_TIME` defines
(each ~50-100ns below nominal to cover PRU clock-reset overhead — `LOW_TIME`
*is* the full bit period, not a separate low-time).
| Value | Preset | Chips | T0H/T1H/period (ns) |
|---|---|---|---|
| 0 | Normal | WS2811-800, WS2812/B, WS2813, WS2815, SK6812, GS8208, GS8608 | 200/675/1150 |
| 1 | Slow | ws281x variant (longer high) | 300/800/1225 |
| 2 | APA104 | APA104/APA106/PL9823/SK6822 | 300/1300/1610 |
| 3 | WS2811-400 | WS2811 @ 400 Kbps | 450/1150/2400 |
| 4 | UCS1903-400 | UCS1903/UCS2903 @ 400 Kbps | 450/1900/2400 |
| 5 | TM1803 | TM1803 (Titan V1.6) | 650/1300/1950 |
| 6 | **TM1814** | TM1814 RGBW — **inverted waveform** | 330/700/1150, idle-high |
| 7 | **TM1829** | TM1829 RGB — **inverted waveform** | 310/750/1150, idle-high |
| 8 | **WS2805** | WS2805 RGB+WW+CW, 5ch | 250/740/990 |
| 9 | **TM1914** | TM1914 RGB — **inverted waveform** | 330/700/1150, idle-high (same wire timing as TM1814, different preamble) |
| 10 | **UCS7604** | UCS7604 RGBW, 8/16-bit | same as Normal (WS2812x-equivalent) + config preamble |
| 11 | **Custom timing** | any single-wire chip: you type T0H / T1H / bit period (ns) and tick *Inverted* if it idles high | whatever you enter (period 1000-4000) |
| 12 | **TM1903 / TM1824 / TM1934** | Titan Micro RGB / RGBW, 800 kHz, not inverted | 360/720/1300 (datasheet period >= 1250) |
| 13 | **UCS2912** | 12-channel RGB driver | 400/800/1250 |
| 14 | **UCS1912** | 12-channel RGB driver | 250/1000/1250 |
| 15 | **TX1812 / TX1818 / LC8816E / GS8208B** | the 0.3 / 0.9 us family (SM16703SP and SM16824E too) | 300/900/1250 |
| 16 | **TM1908** | TM1908 RGB + 9-byte header (auto-switch mode, current) | 240/480/1250 |
| 17 | **LPD1886 (8-bit)** | LPD1886 with GM floating | 200/600/1250 |
| 18 | **LC8812 / LC8812B** | RGB, T1H inside both datasheet versions | 300/750/1250 |

### Channel formats — via **color order** (any timing preset)
| Order | Chip |
|---|---|
| `GRBW`/`RGBW`/`WRGB`… (4-char) | RGBW: SK6812-RGBW, WS2814, TM1814 (use `WRGB`) |
| `RGBWC`/`GRBWC` (5-char) | **WS2805** / **SM16804** (RGB + WW + CW, 8-bit) |
| `RGBCWX` (6-char) | **FW1906** (RGB + CW + WW + unused) |
| `RGB16` (16-bit) | **UCS8903** (16-bit RGB; 6 bytes/px) |
| `RGBW16`/`GRBW16` | **UCS8904** (16-bit RGBW; 8 bytes/px) |
| `RGBWC16` (16-bit) | **SM16825 / SM16825E** (16-bit RGBWW; 10 bytes/px + 4-byte current-gain trailer; **no 8-bit variant exists in silicon**) |

> White ordering matters: WS2805 is **WW then CW** (`…WC`), FW1906 is **CW then WW**
> (`…CW`) — the letters are positional labels, so model your xLights channels to
> match the chip's actual wire order (per WLED's IC definitions). See CONFIG.md.

### SPI (clocked) — via the bundled **SPIPixels plugin** (Pi + BBB)
APA102 / SK9822 / HD107S / HD108 / WS2801 / LPD8806 / LPD6803 / P9813 / SM16716 / SM16726, and new: **TLC59711 / TLC5971** (TI, 4 RGB outputs per chip), **SK9826** family (16-bit, HD108 frame), **APA107**, LC8822 / LC8823.

## How it works (what the installer touches)
| Patcher | File | Change | Rebuild |
|---|---|---|---|
| `patch_asm.py` | `pru/FalconWS281x.asm` | timing presets 2-10 + inverted-waveform GPIO-swap (TM1814/TM1829/TM1914) | runtime (fppd recompiles) |
| `patch_bbb48string.py` | `channeloutput/BBB48String.cpp` | `pixelTiming` 2-10 → `-DPIXELTYPE_*`; preamble-profile flag (TM1814/TM1914/UCS7604); **faster `prepData`** (LUT pointer hoisted per virtual string + software prefetch of the channel map: ~1.6× faster frame preparation on the Cortex-A8, byte-identical output, proven by `test_prepdata.cpp`); **frame-budget log line** at start-up (longest port → ms on the wire → highest sustainable fps) | `libfpp-co-BBB48String.so` |
| `patch_pixelstring.py` | `channeloutput/PixelString.cpp` | 5/6-ch + 16-bit (via `whiteOffset` sentinels 5/6/100+N); generalized `FlipPixels`; **generalized literal-byte preamble/trailer mechanism** (arbitrary bytes via synthetic decoration strings sourced from FPP's constant OFF channel, each carrying its own literal in `brightnessMap` — TM1814/TM1914/UCS7604 preambles, SM16825E current-gain trailer); fixes a latent FPP bug (uninitialized `brightnessMap` in the default `VirtualString` ctor could emit garbage on null pixels) | **`libfpp.so`** |
| `patch_ui.py` (+ `ui_limits.js`) | `www/co-pixelStrings.php` | dropdown 0-10 + chip color orders + **limits panel**: per-chip pixel limits by frame rate, a *Plan for* frame-rate menu, live per-port check with *Fix automatically*, and a confirm-before-save when a port would be cut off | none |

All patch parts are independently guarded and idempotent, so the patchers also
**layer onto a partially-patched tree** (e.g. upgrading an earlier install: the
already-present parts are skipped, only the new parts apply).

The installer applies all four, then does **one** consolidated rebuild — compiling
`PixelString.o` + `BBB48String.o` (with the precompiled header, retrying the BBB's
occasional low-RAM compiler ICE) and **link-only** relinks (a full `make` would
cascade-recompile ~80 files because the PCH timestamp is newer). It adds temporary
swap + stops fppd for the compile, then restores both.

## Limits, performance and health check
- **A port's frame must fit the sequence's frame interval.** If it does not, the PRU output is cut off mid-frame (the end of
  the string stops updating) — nothing warns you. The UI now shows the budget live, and `fppd.log` prints it at start-up.
  Per-IC pixel limits by frame rate: **[MAX_PIXELS.md](MAX_PIXELS.md)**; how the whole board behaves with 8…48 ports of
  1,500 pixels at 20/30/40 fps: **[PERFORMANCE.md](PERFORMANCE.md)**.
- **Limits on the chip menu.** On the FPP pixel-strings page, choosing a Pixel Timing now shows a small card: which chips it covers
  and the most pixels **one port** can drive at 20 / 25 / 30 / 40 fps for each pixel width (RGB, RGBW, 16-bit...). A **Plan for**
  menu sets the frame rate you intend to run (saved with the config as `targetFps`); every port is checked against it live, too-long
  ports get a red outline with the exact limit, and **Fix automatically** shortens them. **Save** asks first if any port is over
  its limit. At start-up the driver also logs `BBB48String LIMIT: port N ... Only the first X% of that port will update` for each
  such port (or `limit check: every port fits at N fps`). Source: `ui_limits.js` (page) and `patch_bbb48string.py` part F (driver);
  both use the measured bit periods, so they never promise more than the board delivered.
- **Chip current and TM1914 mode** (see CONFIG.md): a *Chip current* box for TM1814 / UCS7604 / SM16825E and a *TM1914 mode* menu appear
  on the page only when they apply. **New SPI chips:** HD108/NS108 (16-bit), APA102/SK9822/HD107S "HD" brightness modes, and the
  aliases xLights and other controllers use (WS2803, LPD8803/8809, D705, ...).
- **`bash doctor.sh`** — read-only health report: patch state (sources and compiled), the live config's frame budget,
  clock sanity (the BBG has no RTC), plugin load failures, disk/memory and installer leftovers.
- **`system-fixes.sh`** — OS-level fixes for a board with no RTC and only a USB link (`--check` first; `--apply`, `--undo`): saves the
  clock across reboots (it otherwise boots in 2019, which also breaks logrotate), drops two module names this kernel cannot load, and
  stops the USB console unit hitting systemd's start limit. **`patch_php_notices.py`** (installed by `install.sh`) guards four array
  reads in FPP 5.4.1's status API that otherwise write ~100,000 "Undefined index" notices a day to Apache's log on such a board.
- **`hwtest/`** — the measurement tools behind those documents (pad sampler, per-IC wire-byte check, SPI cross-check,
  throughput benchmarks, the 126-point performance matrix). `hwtest/live_presets.sh` and `hwtest/live_spipixels.sh` are
  on-device regression tests for the 11 timing presets and the 9 SPI protocols.

## Preamble/trailer notes (TM1814, TM1914, UCS7604, SM16825E)
- **Inverted waveform** (TM1814/TM1829/TM1914) swaps the PRU's GPIO set/clear
  registers. On a BeagleBone Green the pad idles high for those three presets and
  low for Normal. The pad sampler only resolves pulses in ~200 ns steps, so the
  0-bit / 1-bit low times it reported (about 378 / 725 ns for TM1814 and TM1914,
  314 / 806 ns for TM1829) are indicative. This PRU loop cannot make a 0-bit
  shorter than about 220 ns: a short-pulse define under about 300 ns collapses
  to that, which is why TM1829's 250 was short. Not yet checked with a scope.
- **Preambles are automatic and per-port-instance, not per-string**: selecting
  Pixel Timing = TM1814/TM1914/UCS7604 prepends the matching config frame to
  **every port on that BBB48String instance** (TM1814: 8 bytes max-current;
  TM1914: 6-byte mode frame; UCS7604: 15-byte sync+config), consuming no sequence
  channels. This means **one chip family per BBB** for these three — you can't mix
  e.g. TM1814 on one port and plain WS2812 needing no preamble on another *if*
  they'd need different `pixelTiming` values; ports that tolerate the same timing
  can still coexist, but every one of them gets the preamble.
- **TM1814/TM1914 current is fixed at max** (6-bit code 0x3F; preamble `3F×4 C0×4`); use string brightness to manage power. UCS7604's default
  per-channel current byte is `0x08` of `0x00-0x0F` (~mid-range).
- **SM16825E gets an automatic 4-byte current-gain trailer** (no Pixel Timing
  selection needed — triggered purely by `RGBWC16`/`GRBWC16` color order) at a
  conservative default of ~58mA/channel (gain index 5 of 0-31). This **overrides
  whatever current the module powered up with, every frame, with no opt-out**
  short of not using that color order. If your modules need more, edit the `g`
  value in `patch_pixelstring.py`'s SM16825E trailer block and reinstall.

## Why chip selection is manual (design rationale)
Confirmed by reading FPP 5.4 + xLights source:
- FPP's BeagleBone driver (`BBB48String`) **ignores the per-port `protocol`
  string** — it drives waveform timing from a single **global `pixelTiming`** int
  (stock: 0=Normal, non-zero=Slow), applied to all 48 ports. Only the Pi SPI
  driver reads `protocol`.
- **xLights never writes `pixelTiming` (or a per-port protocol) into an FPP
  strings config** ([FPP.cpp](../xLights/src-core/controllers/FPP.cpp) only sets
  `colorOrder` — derived from channels-per-pixel: 4→`RGBW`, 1→`W`, else `RGB`/the
  user's order). xLights' `tm1814`/`ucs8904`/`ws2805` vocabulary is for *hardware*
  controllers (Falcon/Advatek/…) whose firmware handles per-port protocol.

So on FPP-BBB the waveform preset (Pixel Timing) and the exotic color orders
(`RGBWC`/`RGBW16`) are **set in FPP's UI, not driven by an xLights upload** — this
is inherent to FPP's model, not a gap we can patch. Our global-`pixelTiming`
approach is therefore the *only* viable mechanism, and it's fully compatible with
what xLights does emit: **all 19 color orders xLights can send (6 RGB perms + 12
RGBW variants + `W`) parse correctly** (verified; `selftest.sh` guards it), and our
5/6/16 sentinels never collide with them.

## 10.x port (`patch_*_10x.py`)

A second, independent set of patchers targets FPP's master/10.x line directly
(`patch_colorOrder_10x.py`, `patch_pixelstring_10x.py`, `patch_bbb48string_10x.py`,
`patch_asm_10x.py`) — same feature set as the 5.x patchers (5/6-ch, 16-bit×N,
TM1814/TM1914/UCS7604 preambles, SM16825E trailer), re-expressed against master's
class-based `FPPColorOrder` since `VirtualString` has no spare int field to reuse
as a sentinel there. **Not installed by `install.sh`** (5.4.1 is what's deployed;
these are for whenever the BBB moves to 10.x) — run them by hand against a 10.x
checkout if/when that happens.

What's structurally different from the 5.x line, confirmed by reading real
`origin/master` source (not guessed): `SetupMap` is fully rewritten around
`colorOrder.redOffset()/greenOffset()/blueOffset()/whiteOffset()`; `channelCount()`
lives on `FPPColorOrder` itself; the old `patch_bbb48string.py` Part C (`prepData`
hoist) has **no 10.x equivalent at all** — upstream's `prepData` is now a NEON/SIMD
tiled rewrite that walks each virtual string via its own `chMap`/`chMapCount`
(set automatically for every string, including our synthetic decoration ones),
confirmed to need zero changes for our mechanism to work correctly on it.

**Found and fixed a real bug in FPP's own upstream master while testing this**,
unrelated to any of our patches: any "W-first" color order (`WRGB`/`WRBG`/`WGRB`/
`WGBR`/`WBRG`/`WBGR` — six of FPP's own 19 built-in values) overflows the output
buffer by one element per virtual string using it, via a stray post-increment in
`SetupMap`. Confirmed against 100% pristine `origin/master` (`de6d0199`,
2026-08-12) with an isolated test under AddressSanitizer — nothing to do with
`fpp-bbb-pixels`. `patch_pixelstring_10x.py` fixes it (clearly labeled as an
upstream fix, separate from our own feature patches) because TM1814/TM1914 need
`WRGB`/`RGB` respectively and would otherwise corrupt memory on 10.x. Worth
reporting upstream independently of this project.

**Tested for real**, same standard as the 5.x line: every patcher applied cleanly
against real extracted `origin/master` blobs (`git show`, read-only, the local
`fpp/` clone's working tree untouched) on the first try, idempotency verified, and
the patched `PixelString.cpp`/`ColorOrder.cpp` compiled and ran end-to-end under
ASan/UBSan against every new color order, all three preambles, the SM16825E
trailer, the per-port opt-out, and the smart-receiver-ordering fix — zero memory
errors, all correct byte-for-byte. `BBB48String.cpp`/`FalconWS281x.asm` could only
get anchor-matching + structural checks (brace/directive balance) — no BBB-specific
headers or PRU toolchain available here to compile those for real.

## Caveats
- **`pixelTiming` is per-output-instance** (all ports share one timing) — existing FPP behaviour.
- **Core files** (`.asm`, `PixelString.cpp`, `BBB48String.cpp`, `co-pixelStrings.php`)
  are overwritten by an FPP upgrade → **re-run `install.sh`** afterward (idempotent).
- **FPP 6.x–9.x** (between 5.x and the 10.x line above): not targeted by either
  patcher set. The 5.x patchers will abort cleanly on a missing anchor (no partial
  edits) if run against these.
- `FalconWS281x.asm` / `BBB48String.cpp` are CC-BY-ND — **personal-use modification** only.

## Verify
- **`sudo bash selftest.sh`** — checks the PixelString channel maps (all chip
  modes, all preambles/trailer) against the live `libfpp`, compiles all 11 PRU
  presets (if an output is configured), and the SPIPixels factory symbol. Run
  automatically with `--test`.
- **On the wire:** the BeagleBone pad confirms idle level and the 1-bit low time.
  An ESP32 analyzer or a scope is what would resolve the 0-bit, which is shorter
  than the pad sampler.

## Files
`install.sh` · `uninstall.sh` · `selftest.sh` · `patch_{asm,bbb48string,pixelstring,ui}.py`
(5.4.1, installed) · `patch_{colorOrder,pixelstring,bbb48string,asm}_10x.py` (10.x line,
not installed — see "10.x port" above) · `test_maps.cpp` · `CONFIG.md` · `REFERENCE.md`
· `IC_IMPLEMENTATION_STUDY.md` · `README.md`
