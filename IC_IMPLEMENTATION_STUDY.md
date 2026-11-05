# Pixel-IC implementation study — FPP on BeagleBone, definitive per-IC guide

Study date: **2026-08-12**. Supersedes the "open items" scorecard in
[REFERENCE.md](REFERENCE.md) §6 and corrects [CONFIG.md](CONFIG.md) (see §5).

> **Status: implemented.** §6's ranked next-steps (generalized preamble/trailer
> mechanism, UCS7604, TM1914, SM16825E trailer, TM1829/WS2805 presets, SPIPixels
> SM16716/SM16726) have since been built, tested against a real compiled
> `PixelString.cpp`, and audited (see CONFIG.md/README.md/REFERENCE.md for
> current, living documentation — this file remains the design record of *why*).
> The inverted waveforms (TM1814/TM1829/TM1914) have since been checked on the
> BeagleBone pad: they idle high, and the 1-bit low time matches the datasheet.
> The 0-bit is below the sampler's resolution, so its define uses the overhead
> measured on the 1-bit. MBI6020 was investigated and deliberately not
> implemented (no source gives its exact frame). §7's 10.x port has not been started.

Ground truth for "what is implemented" is **`patch_pixelstring.py` / `patch_asm.py` /
`patch_bbb48string.py` / `patch_ui.py`**, read line-by-line for this study. Prose in
README/CONFIG/REFERENCE is commentary on that code, not the reverse.

---

## 1. FPP version snapshot

| Thing | Value | Date |
|---|---|---|
| Latest **stable release** (GitHub "Latest" badge) | **9.5** | 2026-01-08 |
| Newest **9.5.x point tag** | `9.5.3` (`7979a4bb`) | 2026-02-24 |
| Latest **pre-release** | `10.0-beta3` (`64875e8d`) | 2026-08-08 |
| **master / testing HEAD** (`origin/master`) | `ba2656df` | 2026-08-11 |
| Local `fpp/` clone HEAD | `e2c21dc3` | 2026-06-20 |
| Local `fpp-5.4/` clone (the 5.4.1 release point) | `2396ffcb` | 2023-10-09 |
| **Deployed on the user's BBB** | FPP **5.4.1** | — |

Drift: the local `fpp/` snapshot is **595 commits / ~52 days behind `origin/master`**.
`git fetch origin` was run read-only; the working tree was **not** touched (still on
`e2c21dc3`). Note `fpp/` is a *grafted shallow* clone, so `git rev-list --count
<tag>..origin/master` is meaningless there — use dates.

The master line is now the **10.0** development branch (`10.x-master`, `10.0-beta*`
tags exist). The 5.4 → master gap is therefore 5.x → 10.x, not 5.x → 9.x as
README.md's caveat section still says.

### Pixel-protocol-relevant commits landed since the local snapshot

| Commit | Date | Why it matters here |
|---|---|---|
| `8c5bfee` BBB48String: tiled fused prepData, 3x on AM335x | 07-08 | **Supersedes our `patch_bbb48string.py` Part C.** Upstream now hoists `vs.brightnessMap` per virtual string *and* adds L1-tiled interleave + an "affine channel map" fast path. Strictly better than our hoist. |
| `f62cd51` shared-memory ring for streaming PRU output (AM62x) | 07-08 | AM62x only; no BBB (AM335x) impact. |
| `f020191` shared allocator for the PRU reserved DDR region | 07-09 | `BBB48String.cpp` churn near our Part A/B anchors — anchors still intact (verified). |
| `3fef605` split Falcon smart receiver into V4/V5 | 07-09 | `PixelString.h` gained `enum class ReceiverType {None=-1, Standard=0, v1, v2, FalconV5=3, FalconV4=4}` and `isFalconV5SmartReceiver()`. Our `receiverNum == -3` TM1814 sentinel is still unclaimed, but **-3 is now adjacent to a live enum space** — re-check before porting. |
| `32eb263` BBB48String: Falcon V4 smart receiver support | 07-09 | Touches `BBB48String.cpp/.h` **and** `FalconWS281x.asm`. |
| `e791964` **drop `rpi_ws281x`, migrate Pi string configs to DPIPixels** | 07-16 | The Pi single-wire path is now DPIPixels only. **`../patches/rpi_ws281x_protocols_patch.py` targets a library upstream has deleted** — that patch is dead on 10.x. DPIPixels hardcodes `protocol == "ws2811"` and rejects everything else, so the Pi has *fewer* protocol knobs than before, not more. |
| `efad242`/`5bcd758`/`ce0f4ef` RGBW display-testing rework | 07-20 | Three commits editing `PixelString.cpp` for `channelsPerNode()`-aware test patterns. Did **not** change channel counts or color orders. |
| `3d7430b` DPIPixels per-sequence frame rate | 07-20 | Pi only. |
| `1822559` fix: pixel string "Reverse" was never saved | 08-08 | UI/config fix; interacts with our generalized `FlipPixels`. |
| `85dffb4`, `4b22eb8` FalconV5 SMEM / BBShiftPanel IMEM | 08-08/11 | `src/pru/` churn, not the string driver. |

**No upstream commit in this window mentions TM1814, UCS7604, UCS8903/8904, SM16825,
WS2805, FW1906, 16-bit, or 5/6-channel.** See §6/E below — upstream has closed
*none* of the gaps this patch set fills.

---

## 2. Patch-currency check

Method: each patcher was executed against the exact `origin/master` blob (extracted
with `git show origin/master:<path>` — the working tree was never modified), with
`repl()` instrumented to report a per-anchor match count instead of aborting at the
first failure. The same run was done against `fpp-5.4` as a control.

### Control — FPP 5.4.1 (what is actually deployed): **all 15 `repl()` anchors match 1:1**

`patch_pixelstring.py` 12/12 · `patch_bbb48string.py` 3/3 · `patch_asm.py` both
anchors · `patch_ui.py` both anchors. Nothing to do before the next BBB deploy.

### Against `origin/master` (`ba2656df`, the 10.x line)

| Patcher | Result |
|---|---|
| `patch_asm.py` | ✅ **both anchors match** — the `#ifdef PIXELTYPE_SLOW / 300 / 800 / 1225 / #else` block and the single `#include "FalconPRUDefs.hp"` are byte-identical on master. ⚠️ **but see the SLOW_WAITNS trap below.** |
| `patch_ui.py` | ✅ both anchors match. `<option value="0">Normal (ws281x)</option>`, `<option value="1">Slow (1903)</option>`, and the single 8-space-indented `result += pixelOutputTableInputOrderOption('W', colorOrder);` all still present verbatim. |
| `patch_bbb48string.py` | ⚠️ **2 of 3.** Parts A (`pixelTiming` cases) and B (`tm1814` flag inject) match. **Part C (`prepData` LUT hoist) → 0 matches, aborts.** |
| `patch_pixelstring.py` | ❌ **0 of 12.** Aborts on the very first anchor. |

#### `patch_pixelstring.py` — why it fails, precisely

Anchor #1 is the literal string:

```
    return whiteOffset == -1 ? 3 : 4;
```

That line no longer exists. `VirtualString` on master has **no `int whiteOffset`
field at all**; `PixelString.h` now carries `FPPColorOrder colorOrder` and
`channelsPerNode()` is:

```cpp
int VirtualString::channelsPerNode() const {
    if (receiverNum >= 0) { return 1; }
    return colorOrder.channelCount();
}
```

Every one of the 12 anchors depends on the pre-refactor shape:
the `whiteOffset` int sentinel (Parts A + B), the `ch1/ch2/ch3` per-permutation
assignment block in `SetupMap` (master replaced it with
`m_outputMap[offset + redOffset] = ch;` using `vs.colorOrder.redOffset()`), and the
`kColorOrderONE` comparison spelling (`FPPColorOrder::kColorOrderONE` on master).
So the whole `whiteOffset = 5/6` and `whiteOffset = 100+N` sentinel design has to be
**re-expressed** for 10.x, not merely re-anchored. This is the guard working exactly
as designed — it aborts before any edit; no partial writes.

#### `patch_bbb48string.py` Part C — good news, not a problem

The anchor was stock 5.x's per-output-byte loop
(`uint8_t* brightness = ps->m_brightnessMaps[p];` inside the byte loop). Master's
`prepData` is now a 64-byte-tile interleaver that already does
`const uint8_t* br = vs.brightnessMap;` once per virtual string, plus an
`m_vsAffine[]` fast path that skips the channel-map indirection entirely for
contiguous strings. **Upstream independently landed our optimization and went
further — Part C should simply be dropped from any 10.x port.**

#### ⚠️ The `SLOW_WAITNS` trap (anchor match ≠ correct result)

`patch_asm.py` writes `#define SLOW_WAITNS` for the four slow presets
(APA104 `LOW_TIME 1610`, WS2811-400 `2400`, UCS1903-400 `2400`, TM1803 `1950`).
On FPP 5.4 that is correct: `src/pru/FalconUtils.hp` has
`.macro WAITNS / #ifdef SLOW_WAITNS ... register form ... #else QBGT waitloop, treg2,
(ns)/5 #endif`, and the immediate form overflows above ~1275 ns.

**On master, `SLOW_WAITNS` no longer exists anywhere in the tree.** The PRU toolchain
moved from PASM to `clpru`; `FalconUtils.asm` now exposes two separate macros —
`WAITNS` (immediate) and `LONGWAITNS` (register) — and `FalconWS281x.asm` itself
defines `WAIT_AND_CHECK_TIMEOUT` (→ `WAITNS`) and `LONGWAIT_AND_CHECK_TIMEOUT`
(→ `LONGWAITNS`). Our `#define SLOW_WAITNS` becomes a **silent no-op**, so
`QBGT waitloop?, treg2, NS2CLK(1610)` = 322 overflows the 8-bit immediate and the PRU
program **fails to assemble** at runtime (fppd logs a compile error, the output never
starts). Loud rather than silent, but it is a real 10.x port item:
on master the four slow presets must switch their call sites to
`LONGWAIT_AND_CHECK_TIMEOUT`, not `#define SLOW_WAITNS`.

TM1814 (`LOW_TIME 1150`) is under the threshold and is unaffected.

#### Two more master-only notes for the eventual port

- **GPIO register swap is AM335x-specific.** `patch_asm.py` hardcodes
  `GPIO_SETDATAOUT (0x190-0x100)` / `GPIO_CLRDATAOUT (0x194-0x100)` for the TM1814
  inversion. Master's `FalconPRUDefs.hp` uses those values only on AM335x; the AM62x
  branch is `GPIO_SETDATAOUT 4` / `GPIO_CLRDATAOUT 8`. Fine for the BBB, wrong for
  any AM62x board.
- **Master added `PixelString::invertOutput()`**, triggered by a cape pin-config
  `"inverted": true`, which **complements every `brightnessMap` entry**. That would
  also complement our TM1814 preamble bytes (which rely on
  `brightnessMap` being identity over `FPPD_WHITE_CHANNEL`/`FPPD_OFF_CHANNEL`) — a
  correctness interaction to handle in the port.

### Bottom line for the user's BBB

**Nothing needs reworking before the next deploy.** The BBB runs 5.4.1, and every
anchor matches 5.4.1 perfectly. The rework list above only applies the day the BBB is
upgraded to the 9.x/10.x line — and `install.sh` already validates on copies and
aborts cleanly, so an accidental run on a newer FPP cannot corrupt the tree.

---

## 3. Master IC implementation matrix

Every group in `xLights/src-core/models/Pixels.cpp` `__equivalentPixels`, plus the
two ICs xLights doesn't know (WS2805, FW1906). "Mechanism" is how the chip reaches
the wire on **BBB + FPP**; "preset" = the global `pixelTiming` int; "order" = the
per-virtual-string `colorOrder` string.

Legend — **A** works today, no new work · **B** works today via an existing
`fpp-bbb-pixels` preset/sentinel · **C** needs a new patch (scoped below) ·
**D** blocked / not buildable on this hardware · **N/A** wrong output subsystem.

### 3.1 Single-wire, PRU (`BBB48String` + `FalconWS281x.asm`)

| IC (xLights name) | Ch × bits | Mechanism | Status | How |
|---|---|---|---|---|
| **ws2811** group — ws2812/12b/2813/**2815**/2818, apa104, apa106, cs8812, gs8202/8206/8208, ink1002/1003, lb1908, lpd1882, lx1203, p9883, sk6812, sk6813, sk6822, sm16703, sm16711, sm16712, tm1803, tm1804, tm1809, tm1812, **tm1914**, ucs1903/1904/1909/1912, ucs2903/2909/2912, ucs9812 (~36 parts) | 3 × 8 | preset **Normal** | **A** | `RGB`/`GRB`/… Ecosystem treats all of these as one 800 kHz timing; Falcon doesn't separate them either. See tm1914 caveat below. |
| apa104 / apa106 / pl9823 / sk6822 | 3 × 8 | preset **APA104** (2) | **B** | Optional datasheet-tighter refinement (300/1300/1610) if a marginal batch misbehaves. |
| ws2811 @ 400 Kbps (`ws2811 slow`) | 3 × 8 | preset **WS2811-400** (3) | **B** | 450/1150/2400. |
| ucs1903 / ucs2903 @ 400 Kbps | 3 × 8 | preset **UCS1903-400** (4) | **B** | 450/1900/2400. |
| tm1803 | 3 × 8 | preset **TM1803** (5) | **B** | 650/1300/1950 (Titan V1.6). |
| **apa109** group — sk6812rgbw, sk6818, sm16704, sm16804, ucs2904, ws2814 | 4 × 8 | preset **Normal** + 4-char order | **A** | `GRBW`/`RGBW`/`WRGB`… stock FPP already does 4-ch. |
| **tm1814 / tm1814a** | 4 × 8, **inverted** | preset **TM1814** (6) + order `WRGB` | **B** | Inverted waveform via PRU GPIO set/clr swap; 8-byte current preamble auto-prepended. See §4.3. |
| **tm1914** | 3 × 8, **inverted** + 6-byte mode preamble | preset **TM1814** (6) reused | **C (small)** | xLights lumps tm1914 into the ws2811 group, which is **wrong**: NeoPixelBus drives it inverted at 360/720/1250 (identical to TM1814) with a 6-byte leading mode frame `FF FF F5` + ones-complement `00 00 0A` (DIN-only). Timing is already covered by preset 6; only the preamble payload differs. Falls out of the generalized-preamble work in §6. |
| **tm1829** | 3 × 8, **inverted** | — | **C (small)** | NeoPixelBus: inverted, 300 high /900 low for a 0, 800/400 for a 1, 200 µs reset. New preset (invert + T0 250 / T1 750 / LOW 1150). |
| **rm2021** (Minleon) | 3 × 8 | preset **Normal** ≈ | **A/B** | Minleon publishes T0H 300 / T1H 900 / Tbit 1250 / Tres 200 µs. Normal (200/675/1150) is close; a dedicated preset (250/850/1150) would be tighter. |
| **ws2805** *(not in xLights)* | 5 × 8 | **Normal** + order `RGBWC`/`GRBWC` | **B** | `whiteOffset = 5` sentinel. Wire order R,G,B,**WW,CW**. NeoPixelBus uses a dedicated 300/790/1090 timing; Normal is a close-enough approximation, a `WS2805` preset would be tighter. |
| **fw1906** *(not in xLights)* | 6 × 8 (5 used) | **Normal** + order `RGBCWX` | **B** | `whiteOffset = 6`. Wire order R,G,B,**CW,WW**,unused. |
| **ucs8903 / ucs8903 (16)** | 3 × 16 | **Normal** + order `RGB16`/`GRB16` | **B** | `whiteOffset = 103`. 6 bytes/px, value duplicated hi=lo (= ×257). Timing borrowed from WS2812x — the UCS8903 datasheet publishes no bit-timing table. |
| **ucs8904 / ucs8904 (16)** | 4 × 16 | **Normal** + order `RGBW16`/`GRBW16` | **B** | `whiteOffset = 104`. 8 bytes/px. |
| **sm16825 / sm16825 (16)** = **SM16825E** | 5 × **16 only** | **Normal** + order `RGBWC16`/`GRBWC16` | **B**, but **incomplete** | `whiteOffset = 105`, 10 bytes/px — correct. **Missing the mandatory 4-byte current-gain trailer appended after the last pixel.** See §4.2. |
| **ucs7604 / rgbw+2** | 4 × {8,12,14,16} | **Normal** + `RGBW16` (16-bit) or plain `RGBW` (8-bit) **+ a 15-byte config preamble** | **C** | Fully resolved — see §4.1. Needs a generalized literal-byte preamble; the *pixel* half already works. |
| **sj1221 / rgb+2** | 3 × **12** (36 bits/px) | — | **D** | Minleon timing is ordinary (350/700/1250), but 12-bit × 3 = 4.5 bytes/pixel. FPP's output map is **byte-granular** — a non-integer byte count per pixel cannot be expressed by `m_outputMap` at all. Would need bit-level packing in the PRU program. Not worth it. |
| **rgb+** / **rgbw+** (Minleon generic) | 3 or 4 × 16 | **Normal** + `RGB16` / `RGBW16` | **B** | These are Minleon's names for generic 16-bit RGB / RGBW — already covered. |
| **gw6205** | 3 × 12 | preset **UCS1903-400** (4)? | **D (unverified)** | Commonly sold as a 400 Kbps UCS1903-alike, but xLights records 12-bit and no vendor datasheet was locatable. Treat as unsupported until a strip is on the bench. |
| **dm412** | ? | — | **D** | No characteristics recorded anywhere (xLights table has "?, ? bit, ? wire"). |
| **gece** | 3 × 5 | — | **D** | GE Color Effects uses a bespoke ~26-bit frame at a non-ws281x rate. Needs its own driver, not a timing preset. |
| **tlc5973** | 3 × 12 | — | **D** | Single-wire "EasySet" with a 3-byte write command header and a completely different self-clocking scheme. Not producible by the WS281x PRU loop. |
| **tls3001 group** — cy3005, tls3002, qed3001 | 3 × 12 | — | **D** | Variable-length self-clocking protocol with sync/reset commands. Falcon implements it in firmware; the PRU program's fixed 3-phase bit loop can't. |
| **tls3008** | 3 × 8 | — | **D (unverified)** | Undocumented in the ecosystem; not grouped with ws2811. |
| **sm16714** | ? | — | **D** | xLights explicitly notes "I have not researched these". |
| **9pdot**, **9pdot (16)**, **spxl**, **spxl (16)** | 8 / 16 bit | — | **D** | Entec-proprietary; xLights knows only the bit depth. No public protocol. |

### 3.2 Clocked SPI — the `SPIPixels` plugin (`plugins/SPIPixels/`)

Confirmed by reading `plugins/SPIPixels/src/SPIChipFormat.h` and its README. This is
a **separate mechanism** from the PRU path by necessity: clocked SPI and single-wire
RZ timing are different output hardware on this board. The plugin talks generic Linux
`spidev`, is dual-API (5.4 `createOutputSPIPixels` / 6.x–10.x `createPlugin`), and
runs on both Pi and BBB. All per-string behaviour (color order, brightness, gamma,
grouping, zig-zag, reverse, nulls) still comes from FPP's own `PixelString`.

| IC group (xLights) | Members | Mechanism | Status |
|---|---|---|---|
| **apa102** | apa101, apa102, apa102c, **hd107s**, **sk9822** | SPIPixels `apa102` / `sk9822` / `hd107s` | **A** — 8/8/20 MHz defaults, BGR, 4-byte start + `0xE0\|bri` per px + end frames |
| **ws2801** | ws2801, ws2803 | SPIPixels `ws2801` | **A** — 1 MHz, raw 3 bytes/px |
| **lpd8806** | lpd8803, lpd8806, lpd8809, ucs8812 | SPIPixels `lpd8806` | **A** — 2 MHz, 7-bit `0x80\|v>>1`, latch bytes |
| **lpd6803** | d705, lpd1101, lpd6803, ucs6909, ucs6912s | SPIPixels `lpd6803` | **A** — 1 MHz, 15-bit `0x8000\|5:5:5` |
| **p9813** | p9813 (Cool Neon Total Control) | SPIPixels `p9813` | **A** — 1 MHz, 4-byte start/end + checksum byte per px |
| **sm16716 / sm16726** | — | — | **C** — clocked, but needs its own framing (leading zero-bit start marker per pixel). One new `SPIChip` enum + `spiFormat` case. |
| **mib6020 (MBI6020)** | — | — | **C** — 10-bit, 4-wire clocked. New `SPIChip` case. |
| **my9221 / my9231 / my9291** | — | — | **C** — DI/DCKI clocked, 16-bit, 208-bit command-header frames and a clock-hold latch. Doable in `SPIChipFormat.h` but the latch needs GPIO timing, not just a byte stream. |

### 3.3 Not applicable to pixel-string output at all

| IC group | Why | Where it does belong |
|---|---|---|
| **dmx512p** — dmx512, ucs512, ws2822 | These are DMX512 *receiver* chips, driven over RS-485 | FPP serial outputs: `DMX-Pro`/`DMX-Open`/`USBDMX` |
| **dmx512p-4** — ucs512c4 | Same, 4-channel | Same |
| `""` (no protocol) | placeholder | — |

---

## 4. The three previously-open items — resolved

### 4.1 UCS7604 — **RESOLVED.** It is a 4-channel chip, not 6.

Sources: official **UCS (Shenzhen) Microelectronics UCS7604 datasheet VER1.1
(2023-06-02)** (text-extracted in full), plus the hardware-verified reverse
engineering in **FastLED issue #2088** (logic-analyzer captures by `@second-string`,
corroborated by `@uzlonewolf`), cross-checked against xLights' Minleon driver.

**What the chip is.** SOP10, 4 outputs `OUTR/OUTG/OUTB/OUTW` (RGB **or** RGBW,
digitally selected), single-wire data with an **optional redundant second data line**
(`FDIN`/`FDO` — "defective pixel resumable data transfer"; the datasheet explicitly
says FDO may be left unconnected). Grayscale is **selectable 8 / 12 / 14 / 16 bits per
channel**; in 8-bit mode the chip internally expands to 65 536 levels via a built-in
gamma-2.2 curve. Data rate is selectable **800 kbps or 1.6 Mbps**. Per-channel
constant current is set both by an external `REXT` resistor (`IO = 256/RREXT`, 0–60 mA)
and by a **16-step software field per channel**.

**The datasheet publishes no bit-timing table** — same situation as UCS8903/8904.
Only `Fd1 = 800 kHz` / `Fd2 = 1600 kHz`. The data section is confirmed
bit-for-bit identical to UCS2904 (i.e. the ordinary WS281x 800 kHz family); xLights'
own Minleon driver sends **T0H 400 / T1H 800 / Tbit 1250 / Tres 250 µs** for
`rgbw+2`. So **preset `Normal` is correct for the pixel data.**

**The frame — this is the part that was blocked, and it is now known exactly:**

```
[Chunk 1: 8 bytes] --(~260us)--> [Chunk 2: 7 bytes] --(~260us)--> [pixel data]

Chunk 1 (fixed sync/framing, always 800 kbps):
    FF FF FF FF FF FF 00 02
    (last byte 0x02; 0xF0-0xFF there puts the chip into its channel-test mode)

Chunk 2 (configuration, always 800 kbps):
    [CFG] [Rcur] [Gcur] [Bcur] [Wcur] [rsvd 00] [rsvd 00]

    CFG bits (bit 7 first on the wire):
      bit 7 + bit 3 : grayscale depth   00 = 8-bit,  11 = 16-bit
      bit 4         : data-section rate  0 = 800 k,   1 = 1.6 M
      bit 1 + bit 0 : field mode  11 = RGBW (4 ch), 10 = RGB (W off),
                                  01 = RG+BW (2 ch), 00 = all four together
      bits 6,5,2    : no observed effect

    Rcur..Wcur : 4-bit per-channel current, 0x00-0x0F
                 (the near-identical UCS7804 uses 6 bits, 0x00-0x3F; a 7604
                  accepts 0x3F and ignores the high nibble)

    Worked examples:  0x8B = 16-bit, 800 k, RGBW
                      0x9B = 16-bit, 1.6 M, RGBW
                      0x03 = 8-bit,  800 k, RGBW

Pixel data: RGBW byte order; 4 bytes/px in 8-bit mode, 8 bytes/px in 16-bit mode.
```

**Critically for us: the inter-chunk gaps are not required.** The reporter confirmed
on hardware that concatenating the preamble bytes directly onto the front of the pixel
payload works — the chips count bits and ignore the spacing. That makes this
implementable with the *exact same machinery* as our TM1814 preamble.

**Verdict vs. REFERENCE.md's guess.** The guess ("likely 6-ch-16, or RGBW-16 + 2
config bytes") was directionally right on the second half and wrong on the first:
UCS7604 is **RGBW (4 channels)**, and the config is **15 bytes in 2 chunks**, not 2
bytes. **The existing `whiteOffset = 100+N`, N=6 mode is not what UCS7604 needs.**
What it needs is:

- 16-bit RGBW → the already-shipping `RGBW16` order (`whiteOffset = 104`), **plus** the
  preamble with `CFG = 0x8B`; or
- 8-bit RGBW → plain stock `RGBW` order (nothing exotic at all), **plus** the preamble
  with `CFG = 0x03`.

So UCS7604 is now a **preamble problem, not a bit-depth problem** — and the 8-bit
route means it can be driven with *stock* channel handling once the preamble exists.

*Aside on the "+2" alias.* `rgbw+2` is a Minleon marketing name, not a channel count.
Minleon's own per-port pixel budgets (`Minleon.cpp`: 920 px default 3×8-bit,
460 px for `rgbw+2`) imply Minleon runs UCS7604 at **6 bytes/pixel = RGBW 12-bit**,
and `rgb+2` (SJ1221) at 4.5 bytes = RGB 12-bit. Reading "+2" as "6 channels" —
which is what REFERENCE.md did — is a misreading of vendor branding.

### 4.2 SM16825 — **RESOLVED. There is no 8-bit SM16825. It is 16-bit only.**

Determined from the manufacturer product page (chinaasic.com, the SM16825E) and,
decisively, from **NeoPixelBus's `src/internal/features/NeoSm168x5Features.h`**, which
is the implementation WLED actually ships (`TYPE_SM16825` → `NeoRgbcwSm16825eFeature`,
driven by the plain `Ws2812x` 800 kHz method).

```cpp
template<uint8_t V_IC_1, ... V_IC_5>
class NeoRgbwcSm168x5Elements :
    public Neo5WordFeature<V_IC_1, V_IC_2, V_IC_3, V_IC_4, V_IC_5>   // <-- Word, not Byte
```

`Neo5WordFeature` = **5 channels × 16-bit words = 10 bytes per pixel**, unconditionally.
There is no byte-wide variant of this feature and no 8-bit code path. (The `_5` in
WLED's `B_32_RN_SM16825_5` macro is the *channel* count, not a byte count — it is easy
to misread it the other way.)

**Chip facts:** SM16825E — single-wire **RZ-code**, 800 kbps, 5 channels (RGB + WW +
CW, sometimes written RGBWY), 65 536-level grayscale **only**, integrated **5-bit
current-gain field per channel** giving 10.2 – 310.0 mA in 32 steps, over-temperature
protection, DIN-idle standby with auto-wake.

**The current-gain field is a 4-byte trailer appended after the last pixel** — not a
preamble. NeoPixelBus:

```cpp
static const size_t SettingsSize = 4;
static void applySettings(uint8_t* pData, size_t sizeData, const SettingsObject& s) {
    uint8_t* pDest = pData + sizeData - SettingsSize;   // end of the whole stream
    s.Encode(pDest);
}
// Encode(): 5 gains of 5 bits each, packed MSB-first, then 2 action bits + 5 reserved
//   b0 = R<<3 | G>>2
//   b1 = G<<6 | B<<1 | W>>4
//   b2 = W<<4 | Y>>1
//   b3 = Y<<7 | 0b0011111     // bits 6..5 = 00 "action, not standby"; 4..0 reserved 1s
```

**Consequences for `fpp-bbb-pixels`:**

1. **CONFIG.md line 14 is factually wrong about silicon.** Labelling SM16825 "(8-bit)"
   and pairing it with WS2805 on the `RGBWC` 5×8 path describes a part that does not
   exist. Driving a real SM16825E with 5 bytes/pixel will produce garbage (the chip
   consumes 80 bits per pixel and forwards the rest downstream, so the whole string
   smears).
2. **WS2805 on that same line is correct** — NeoPixelBus's `TYPE_WS2805` is
   `NeoGrbwwFeature`, a genuine 5 × 8-bit byte feature. The 5-channel 8-bit path is
   real and useful; it just belongs to WS2805 (and SM16804), not SM16825.
3. **`RGBWC16` (`whiteOffset = 105`, 10 bytes/px) is the right and only mode for
   SM16825E** — and it is already implemented. But it is **incomplete**: the 4-byte
   gain trailer is not emitted. Given the chip's standby/wake behaviour and the fact
   that every reference implementation always sends it, treat the trailer as required.
   This is the same "literal bytes at a fixed position" problem as UCS7604, just at the
   tail instead of the head.
4. xLights' comment table calling SM16825 "**4 wire**" is wrong — it is single-wire RZ.
   And xLights listing both `sm16825` and `sm16825 (16)` (Falcon protocols 18 / 19) is
   a *host-data* distinction (8-bit sequence data vs. 16-bit), exactly like
   `ucs8903`/`ucs8903 (16)` — not a wire-format distinction. On our stack the host data
   is always 8-bit and the ×257 expansion happens in `SetupMap`, so **one mode covers
   both xLights entries.**

### 4.3 TM1814 timing — **CONFIRMED in-spec.**

Known-good datasheet numbers (from the prior research pass): inverted / idles high;
LOW-phase times T0l 310 / **360** / 410 ns (min/typ/max), T1l 650 / **720** / 1000 ns,
cycle 1.25 µs, `Treset` (high) 200 µs – 20 ms; WRGB byte order; C1 = 4 current bytes
(top 2 bits fixed 0, 6.5–38 mA in 64 steps, `(mA×10−65)/5`), C2 = bitwise complement.

Independently corroborated this pass by NeoPixelBus `NeoEsp32RmtSpeedTm1814`
(inverted speed base): bit-0 = 360/890, bit-1 = 720/530, reset 200 µs. Exactly the
datasheet typicals at a 1250 ns period.

**What the patch actually emits, and why it is right.** `patch_asm.py` preset 6 sets
`T0_TIME 350 / T1_TIME 700 / LOW_TIME 1150`. Reading the asm settles the semantics:
`LOW_TIME` is the **full bit cycle** (`// wait for the full cycle to complete`), and
the header comment says *"defines are slightly lower as there is overhead in resetting
the clocks"* — stock "Normal" is `200/675/1150` for a nominal 250/700/1250 WS2812, i.e.
each define sits ~50–75 ns below nominal. So preset 6 lands on the wire at roughly
**T0 ≈ 400 ns, T1 ≈ 750 ns, period ≈ 1200–1250 ns**:

- T0 ≈ 400 ns vs. spec 310–410 → in spec, but **near the top of the window**.
- T1 ≈ 750 ns vs. spec 650–1000 → comfortably in spec.
- period ≈ 1250 ns → nominal.

**Recommendation:** keep as-is, but if a TM1814 strip proves marginal on long runs,
lower `T0_TIME` from 350 → **310** (≈360 ns on the wire, dead on the datasheet typ)
before touching anything else. The TM1814A alias needs no delta (xLights aliases it).

The current preamble the patch prepends is `FF FF FF FF 00 00 00 00` — the chip reads
the low 6 bits of each current byte, so `0xFF` = maximum current on all four channels,
and the complement half is all-zero. Correct, and it consumes zero sequence channels.
Still unverified **on the wire** — the GPIO set/clr swap compiles and loads but has not
been scoped.

---

## 5. CONFIG.md corrections

**The self-contradiction resolves in favour of lines 16–18.** `patch_pixelstring.py`
Part B is fully implemented and ships: it parses any `colorOrder` of length 5–8 ending
in `"16"`, sets `whiteOffset = 100 + len(prefix)` (103–106), makes `channelsPerNode()`
return `(whiteOffset-100)*2`, fixes the per-pixel *source* stride to N (not N×2), and
emits each source channel twice in `SetupMap` (hi = lo = value, arithmetically
identical to ×257). `patch_ui.py` adds `RGB16 GRB16 RGBW16 GRBW16 BRGW16 RGBWC16
GRBWC16` to the dropdown. So **UCS8903-16, UCS8904-16 and SM16825-16 are supported
today.**

| Line | Currently says | Should say |
|---|---|---|
| **14** | `**WS2805** / **SM16825** (8-bit) \| Normal \| RGBWC / GRBWC \| … (SM16825's *16-bit* variant is not supported.)` | Split the row. **WS2805 / SM16804**: `Normal`, `RGBWC`/`GRBWC`, 5 ch/px 8-bit, wire order R,G,B,**WW,CW**. **Delete SM16825 from this row entirely** — no 8-bit SM16825 exists in silicon (§4.2). Delete the "16-bit variant is not supported" parenthetical; it is false. |
| **18** | `**SM16825-16** (16-bit RGBWW) \| Normal \| RGBWC16 / GRBWC16 \| model as 5-ch RGB+WW+CW; FPP emits 10 bytes/px` | Keep, but rename the row to just **SM16825 / SM16825E** (there is no other variant), and add: *"⚠ the chip's mandatory 4-byte current-gain trailer is not yet emitted — see IC_IMPLEMENTATION_STUDY.md §4.2."* |
| **37–40** | `Not yet supported (all need a **16-bit × N-channel** mode we don't have — our 16-bit path is RGBW-only): **SM16825-16**, **UCS7604**, **UCS8903-16**` | **Delete this paragraph.** It is stale — it predates Part B. Replace with: *"Not yet supported: **UCS7604** (needs a 15-byte config preamble — the pixel format itself is already covered by `RGBW` or `RGBW16`); **SJ1221** (12-bit, 4.5 bytes/pixel — not expressible in a byte-granular output map)."* |
| **35** (the "genuinely distinct" list) | ends `**UCS8904** (16-bit)` | → `**UCS8903/8904/SM16825** (16-bit)` |

Also worth adding to CONFIG.md as a known limitation of the 16-bit parser:
**white-first 16-bit orders are not expressible.** The parser does
`colorOrder = b16.substr(0,3)`, so `WRGB16` becomes `"WRG"`, which
`ColorOrderFromString` rejects and silently falls back to `RGB`. Only
`RGB16/RBG16/GRB16/GBR16/BRG16/BGR16` prefixes (± appended whites) are valid; white is
always positional at `ch+3`, `ch+4`, `ch+5`.

Two smaller doc fixes elsewhere:

- **REFERENCE.md §5** — the "⚠ Remaining: UCS7604 … needs a datasheet" bullet and §6's
  two open items are all now resolved; fold in §4 above.
- **README.md "Caveats"** — says "FPP 6.x+ / 9.x". The master line is now **10.x**, and
  the `SLOW_WAITNS` + `prepData` findings in §2 should be recorded there so the port
  isn't re-derived later.

---

## 6. Concrete next steps, ranked by effort

**1. Documentation fixes (minutes, zero risk).** Apply §5 to CONFIG.md, REFERENCE.md
§5–6 and README.md. The SM16825 "(8-bit)" claim is the one that can actively mislead
someone into wiring up a string that will never work.

**2. Generalized literal-byte frame decoration (half a day) — unlocks 3 ICs at once.**
Extend `patch_pixelstring.py` Part C from a hardcoded TM1814 preamble to a small
declarative mechanism, and four chips fall out of one change:

The existing trick is already 90 % of the answer: a synthetic `VirtualString` with
`receiverNum = -3`, `colorOrder = kColorOrderONE`, mapped to `FPPD_WHITE_CHANNEL`
(0xFF) / `FPPD_OFF_CHANNEL` (0x00). Those are the only two constant channels FPP has
(`Sequence.h`: `FPPD_OFF_CHANNEL = FPPD_MAX_CHANNELS`, `FPPD_WHITE_CHANNEL = +4`), so
today the preamble can only contain `0x00` and `0xFF` — which is exactly why TM1814
was easy and UCS7604 was not.

**The unlock:** `prepData` evaluates `brightnessMap[channelData[map[i]]]`, and
`brightnessMap` is **per virtual string**. So a synthetic string whose source is
`FPPD_OFF_CHANNEL` and whose `brightnessMap[0] = K` emits the literal byte `K`. One
synthetic virtual string per *run of equal bytes* gives arbitrary literals with no
sequence channels consumed and no new core machinery:

- **UCS7604** preamble `FF×6, 00, 02, 03, 0F×4, 00×2` → **6** synthetic strings.
- **TM1914** preamble `FF FF F5 00 00 0A` → **4**.
- **TM1814** collapses into the same mechanism (`FF×4, 00×4` → 2 strings), retiring the
  special case.
- **SM16825E** needs the same thing at the **tail** — add an `after` flag so a
  decoration string can be appended after the pixel strings rather than prepended.

Then expose `preambleBytes` / `trailerBytes` (or a per-chip enum) in the strings JSON
and `patch_ui.py`, driven from `pixelTiming` the way `tm1814` already is in
`patch_bbb48string.py` Part B. Note the interaction flagged in §2: on 10.x,
`invertOutput()` complements `brightnessMap`, which would corrupt literal bytes.

**3. SM16825E current-gain trailer (folds into step 2).** Encode 5 × 5-bit gains per
§4.2 into 4 bytes and append. Default all gains to a mid value (index ~15 ≈ 160 mA) or
expose a UI field — do **not** default to 31 (310 mA/channel × 5 channels is a lot of
copper). Until this ships, `RGBWC16` should be documented as "may not light / may
run at the chip's power-on default".

**4. Two cheap new PRU presets (an hour each).** `TM1829` (inverted, T0 250 / T1 750 /
LOW 1150) and `WS2805` (300/790/1090 per NeoPixelBus, tighter than Normal). Both are
one `#elif` in `patch_asm.py` + one `case` in `patch_bbb48string.py` + one `<option>`
in `patch_ui.py`. Note preset numbering is already 0–6; these become 7 and 8.

**5. Bench-verify TM1814 on the wire (blocked on hardware).** The inverted waveform
compiles and loads but has never been scoped. Use `tools/esp32-led-analyzer` or a
FastLED-on-ESP32 reference generator. This is the single highest-value *verification*
item — everything else about TM1814 is now settled on paper.

**6. Extend SPIPixels with SM16716/SM16726 and MBI6020 (half a day each).** Pure
additions to `SPIChipFormat.h` + a `spiChipFromString` entry; the file is
dependency-free and unit-testable natively (`tests/test_format.cpp`), so this is
low-risk work that needs no BBB. MY9221/MY9231/MY9291 are harder — their latch is a
clock-hold, not a byte pattern.

**7. The 10.x port (multi-day; not needed until the BBB is upgraded).** Scope, now
concretely known:
   - `patch_pixelstring.py` — **rewrite, not re-anchor.** Re-express the `whiteOffset`
     5/6 and 100+N sentinels against the class-based `FPPColorOrder`. Cleanest route is
     to extend `FPPColorOrder::Value` with the new orders and teach
     `channelCount()` / `whiteOffset()` / `ColorOrderFromString()` about them, which is
     also the shape most likely to be acceptable upstream. Re-check the
     `receiverNum = -3` sentinel against the new `ReceiverType` enum.
   - `patch_asm.py` — replace `#define SLOW_WAITNS` with `LONGWAIT_AND_CHECK_TIMEOUT`
     at the four slow presets' call sites. Keep the AM335x GPIO swap but guard it so an
     AM62x build doesn't silently pick the wrong register offsets.
   - `patch_bbb48string.py` — **delete Part C** (upstream `8c5bfee` supersedes it);
     Parts A and B still apply verbatim.
   - `patch_ui.py` — applies unchanged.

**8. Genuinely blocked / not worth pursuing.** SJ1221 (12-bit, 4.5 bytes/pixel —
byte-granular output map can't express it), TLS3001 family, TLC5973, GECE (all need
a bespoke bit-generator, not a timing preset), and 9PDOT / SPXL / DM412 / SM16714 /
TLS3008 / GW6205 (no public protocol documentation exists to implement against).

---

## Appendix — upstream status check (task item E)

**Stock FPP has closed none of these gaps, on any branch.** Read from the freshly
fetched `origin/master` (`ba2656df`, 2026-08-11):

- `src/channeloutput/ColorOrder.h` — `FPPColorOrder::Value` has exactly **19** members:
  6 RGB permutations, `kColorOrderONE`, and 12 RGBW variants. `channelCount()` returns
  only 1, 3 or 4. `whiteOffset()` returns only -1, 0 or 3. **No 5/6-channel, no
  16-bit, anywhere.**
- `PixelString::FlipPixels()` on master is still hardcoded to 3-or-4 channels
  (`if (chanCount == 4)`) — our generalized version is still ahead.
- `git grep` across `origin/master:src` and `:www` for tm1814 / ucs8903 / ucs8904 /
  sm16825 / ws2805 / fw1906 hits **only `src/overlays/wled/`** — that is vendored WLED
  *effects* code used for Pixel Overlay Models. Its `bus_manager.h` / `const.h` chip
  constants are dead weight; they drive no FPP output. `ucs7604` appears **nowhere**
  in the FPP tree.
- Nothing equivalent appeared on any other output driver either. The Pi went the other
  way: `e791964` **deleted** the `rpi_ws281x` path and migrated Pi strings to
  DPIPixels, which hardcodes `protocol == "ws2811"` and refuses everything else. Fewer
  protocol knobs upstream, not more.
- The only overlap is performance, not features: `8c5bfee` reimplemented (and
  improved on) our `prepData` optimization.

So the "ahead of stock FPP" claim in REFERENCE.md §5 still holds in full, and now
extends to the 10.x line.

### Sources

- [FPP releases](https://github.com/FalconChristmas/fpp/releases) ·
  [FalconChristmas/fpp](https://github.com/FalconChristmas/fpp)
- [UCS7604 datasheet VER1.1 (PDF)](https://www.led-stuebchen.de/download/UCS7604.pdf) ·
  [Advatek UCS7604 protocol page](https://www.advateklighting.com/pixel-protocols/ucs7604)
- [FastLED issue #2088 — UCS7604 reverse engineering](https://github.com/fastled/fastled/issues/2088)
- [SM16825E product page (chinaasic.com)](https://www.chinaasic.com/en/chipDetails/detail_517.html) ·
  [NeoPixelBus `NeoSm168x5Features.h`](https://github.com/Makuna/NeoPixelBus/blob/master/src/internal/features/NeoSm168x5Features.h)
- [NeoPixelBus `NeoEsp32RmtMethod.h` (TM1814/TM1829/TM1914/WS2805 timings)](https://github.com/Makuna/NeoPixelBus/blob/master/src/internal/methods/NeoEsp32RmtMethod.h) ·
  [NeoPixelBus `NeoTm1914Features.h`](https://github.com/Makuna/NeoPixelBus/blob/master/src/internal/features/NeoTm1914Features.h)
- [WLED `bus_wrapper.h`](https://github.com/wled/WLED/blob/main/wled00/bus_wrapper.h)
- Local: `xLights/src-core/models/Pixels.cpp`, `xLights/src-core/controllers/Falcon.cpp`,
  `xLights/src-core/controllers/Minleon.cpp`, `plugins/SPIPixels/src/SPIChipFormat.h`
