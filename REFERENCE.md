# Pixel-IC reference — how FPP, xLights & controllers model LED protocols

Cross-referenced from FPP 5.4 + master, xLights, the Falcon reference firmware,
WLED, and manufacturer datasheets. This is the knowledge base behind
`fpp-bbb-pixels`. File:line evidence is given so claims are checkable.

> §5's scorecard and §6's open items are kept current here, but
> [IC_IMPLEMENTATION_STUDY.md](IC_IMPLEMENTATION_STUDY.md) is the fuller,
> dated per-IC implementation matrix and patch-currency audit — check there first
> for "can I build X, and how."

## 1. The three-axis model
Every addressable LED IC is described by three independent axes:

| Axis | What it is | Where it lives |
|---|---|---|
| **Waveform / timing** | bit-timing + polarity (ws281x 800k, 400k slow, APA104, TM1814 inverted…) | **FPP: global `pixelTiming`** (PRU compiled once); Falcon: a protocol number; xLights: doesn't send it to FPP |
| **Channel count** | 3 (RGB) / 4 (RGBW) / 5 (RGBWW) / 6 | **FPP: `colorOrder` string length**; xLights: `GetChannelsPerPixel()` |
| **Bit depth** | 8-bit or 16-bit (2 wire bytes/ch) | **output-side flag** — never a channel-count change |

The key realization: **bit depth and timing are output/firmware concerns, not
sequence-data concerns.** xLights sends the same 4-channel RGBW data for `ucs8904`
and `ucs8904 (16)` — `GetChannelsPerPixel` returns 4 for both
([Pixels.cpp:365-368](../xLights/src-core/models/Pixels.cpp)). The controller
decides 8 vs 16 bit. Falcon encodes that as **separate protocol numbers**
(`UCS8904`=11 vs `UCS8904_16`=12; `SM16825`=18 vs `SM16825_16`=19;
`WS2811`=14 vs `WS2811_SLOW`=15 — [Falcon.cpp:476-495](../xLights/src-core/controllers/Falcon.cpp)).
FPP-BBB has no such flag in its string config, so we encode format in `colorOrder`
(`RGBW16`) and timing in `pixelTiming`.

## 2. FPP-BeagleBone specifics (why config is manual)
- `BBB48String` **ignores the per-port `protocol`** string; timing is one global
  `pixelTiming` int for all 48 ports (the PRU program is compiled once).
- xLights' FPP uploader writes only `colorOrder` (from channels-per-pixel: 4→RGBW,
  1→W, else RGB) — **never `pixelTiming`/protocol**
  ([FPP.cpp:2931-2973](../xLights/src-core/controllers/FPP.cpp)). It also can't
  express >4 channels (a 5-ch model uploads as `RGB`).
- FPP master (9.x) `ColorOrder` is a class but still caps at **4 channels** (12
  RGBW/WRGB variants) and has no 16-bit/5-ch single-wire
  ([ColorOrder.h:16-37](../fpp/src/channeloutput/ColorOrder.h)).

→ Waveform preset and exotic formats are set in **FPP's own UI**, and 5/6-ch/16-bit
strings need a **manual/generic xLights model**. This isn't a bug we can patch —
it's inherent. Our global-`pixelTiming` + `colorOrder`-sentinel design is the only
FPP-native mechanism, and it's forward-compatible with what xLights *does* send.

## 3. IC compatibility groups (the practical map)
From xLights `__equivalentPixels` + Falcon protocol table + WLED:

| Group | Members | Timing | Ch | On our system |
|---|---|---|---|---|
| **ws2811-equivalent** (the big one) | ws2811/12/13/**2815**, apa104, apa106, gs8208, sk6812, sk6813, sk6822, sm16703, tm1803, tm1804, tm1809, ucs1903, ucs2903, +~20 | 800k | 3 | **Normal** (our APA104/TM1803/UCS1903 presets are optional datasheet-tighter refinements — even Falcon doesn't separate them) |
| **RGBW 4-ch** | sk6812rgbw, sk6818, sm16704, ws2814, ucs2904, apa109 | 800k | 4 | Normal + 4-char order (`GRBW`…) |
| **RGBW-inverted** | **tm1814**, tm1814a (alias) | ~800k inverted | 4 | **TM1814** preset (`WRGB`) |
| **inverted, no white** | **tm1914**\*\*, tm1829 | ~800k inverted | 3 | **TM1914** / **TM1829** presets — xLights lumps tm1914 into ws2811-equivalent, which is wrong (it's inverted with its own preamble); tm1829 xLights already lists as its own group |
| **RGBWW 5-ch, 8-bit** | ws2805*, sm16804 | 800k | 5 | our 5-ch path (`RGBWC`) |
| **6-ch** | fw1906* | 800k | 6 | our 6-ch path (`RGBCWX`) |
| **16-bit** | ucs8903(16), ucs8904(16), **sm16825/sm16825(16)** (16-bit only, no 8-bit silicon exists), ucs7604 | 800k | 3/4/5/4† | **unified 16-bit×N mode**: `RGB16`(UCS8903), `RGBW16`(UCS8904), `RGBWC16`(SM16825), preamble-only for UCS7604 |
| **400 Kbps** | ws2811-slow, ucs1903-400 | 400k | 3 | **WS2811-400 / UCS1903-400** presets |
| **SPI clocked** | apa102/apa101/hd107s/sk9822, lpd6803, lpd8806, p9813, ws2801 | clock | 3/4 | **SPIPixels plugin** |

\* WS2805/FW1906 are **not** in xLights or Falcon — genuinely niche; we support them
but xLights can't drive them (manual FPP + generic xLights model only).
\*\* tm1914 **is** in xLights, grouped (incorrectly, per NeoPixelBus) with the plain
ws2811-equivalent family — treat it as inverted with its own preamble regardless of
what xLights' grouping implies.
† UCS7604 is **4-channel** (RGBW), not 6 — xLights' `rgbw+2` alias names its Minleon
config-byte count, not a channel count. See
[IC_IMPLEMENTATION_STUDY.md §4.1](IC_IMPLEMENTATION_STUDY.md#41-ucs7604--resolved-it-is-a-4-channel-chip-not-6).

## 4. Per-IC datasheet specs (authoritative, as used by our presets)
| IC | T0H/T1H/period ns | Ch | Bits | Special | Source |
|---|---|---|---|---|---|
| WS2811-800 / WS2812 | 250/600/1250 | 3 | 8 | — | WorldSemi; FastLED chipsets.h |
| APA104/APA106 | 350/1360/1710 | 3 | 8 | — | ledlightinghut datasheet |
| WS2811-400 | 500/1200/2500 | 3 | 8 | — | WorldSemi |
| UCS1903-400 | 500/2000/2500 | 3 | 8 | — | UCS datasheet |
| TM1803 | 680/1360/2040 | 3 | 8 | — | Titan V1.6 datasheet |
| **TM1814** | ~360/720/1250 | 4 | 8 | **inverted idle-high** + 8-byte current preamble `[c×4,~c×4]` = `3F×4 C0×4` at max (WRGB order) | NeoPixelBus `NeoTm1814Features.h` |
| **UCS8904** | ~250/600/1250 | 4 | **16** | each ch → 2 bytes MSB-first | Advatek; FastLED WS2816 encoder |
| **WS2805** | ~300/790/1090 | 5 | 8 | RGB + **WW,CW** | NeoPixelBus; WLED const.h |
| **FW1906** | ~800k | 6 | 8 | RGB + **CW,WW** + unused | WLED const.h |
| **SM16825E** | ~800k | 5 | **16 only** | RGB+WW,CW; single-wire (xLights' "4 wire" note is wrong); mandatory 4-byte current-gain **trailer** after the last pixel — overrides module current every frame, our default is a conservative gain index 5/31 (~58mA/ch), no UI opt-out yet | NeoPixelBus `NeoSm168x5Features.h`; chinaasic.com |
| **UCS7604** | ~800k (Fd2 1.6M optional) | 4 | 8/12/14/**16** | RGBW; 15-byte config **preamble** (`FF×6,00,02` + CFG + 4 current + 2 rsvd); datasheet publishes no bit-timing table, WS2812x-equivalent confirmed by hardware RE | UCS7604 ds VER1.1; FastLED #2088 |
| **TM1914** | ~360/720/1250 | 3 | 8 | inverted idle-high (same as TM1814); 6-byte mode preamble `FF FF F5 00 00 0A` | NeoPixelBus `NeoTm1914Features.h` |
| **TM1829** | ~300/800/1250 | 3 | 8 | inverted idle-high; 200µs reset (nominal chip spec — our PRU preset defines 250/750/1150, ~50ns below nominal for clock-reset overhead, same convention as every other preset here) | NeoPixelBus `NeoEsp32RmtMethod.h` |

## 5. Our implementation's alignment scorecard
- ✅ **Design axis-correct**: timing=`pixelTiming`, format=`colorOrder`, matches how
  FPP models it and forward-compatible with xLights uploads.
- ✅ **Ahead of stock FPP** (5.4 + 9.x both lack TM1814/16-bit/5-6-ch single-wire).
- ✅ **Ecosystem-consistent**: ws2811-equivalence documented; 16-bit as output flag.
- ✅ **16-bit × N-channel gap CLOSED**: a unified mode (`whiteOffset = 100 + N`,
  N source channels → N×2 wire bytes, N=3..6) covers **UCS8903-16** (`RGB16`),
  **UCS8904-16** (`RGBW16`), **SM16825-16** (`RGBWC16`) and a 6-ch form — matching
  Falcon's `_16` protocols. Validated against real patched 5.4 code.
- ✅ **UCS7604, TM1914, TM1829 added** via a generalized literal-byte
  preamble/trailer mechanism (arbitrary constants, not just the TM1814-only
  `0x00`/`0xFF` pair) — see [IC_IMPLEMENTATION_STUDY.md §6](IC_IMPLEMENTATION_STUDY.md).
  UCS7604 turned out to be **4-channel**, not 6 — the earlier guess on this page was
  wrong on channel count (right on "needs a config preamble"). WS2805/FW1906 stay
  niche (unknown to xLights/Falcon).
- 📋 **9.x/10.x port**: the class-based `FPPColorOrder` on master has no `whiteOffset`
  field at all (full rewrite, not a re-anchor); `patch_asm.py`'s `SLOW_WAITNS` macro
  was deleted upstream (→ `LONGWAITNS`); `patch_bbb48string.py`'s `prepData` hoist is
  superseded by an upstream optimization. Full drift analysis in
  [IC_IMPLEMENTATION_STUDY.md §1-2](IC_IMPLEMENTATION_STUDY.md) — **not required for
  the deployed 5.4.1 BBB**, only for a future FPP upgrade.

## 6. Open datasheet items — resolved
Both items below were open as of the last pass; both are now closed. See
[IC_IMPLEMENTATION_STUDY.md §4](IC_IMPLEMENTATION_STUDY.md) for full sourcing.
- **TM1814 T0H/T1H**: confirmed in-spec against the manufacturer datasheet and
  NeoPixelBus's independent implementation (both ~360/720 typ). Our preset lands
  ~400/750ns on the wire — inside spec, near the top edge on T0.
- **SM16825**: confirmed **16-bit only** — no 8-bit variant exists in silicon. The
  "(8-bit)" label previously on this chip in CONFIG.md described a part that
  doesn't exist; corrected.
