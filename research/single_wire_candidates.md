# Single-wire pixel ICs not yet supported by the BBB PRU driver: datasheet-verified candidates

Research date: 2026-11-02. Read-only web research. Nothing in the driver was changed.

**PRU envelope used for the "fits PRU?" column:** bit period about 1.0 to 2.6 us, T0H/T1H settable in about 10 ns steps (min T0H about 200 ns), optional inverted (idle-high) waveform, 3-8 bytes/pixel, optional preamble bytes. Not possible: bit period below about 1.0 us, 12-bit (non byte-granular) pixels, two-wire or return-to-zero bidirectional signalling.
"Wire" values below are the on-wire targets. Our preset defines sit about 50 ns lower than the wire target (see `CROSSREF_LIBRARIES.md` section 1), so subtract about 50 ns from T0H/T1H when writing a preset.
Existing reference: stock "Normal" is about 250 / 725 / 1200 ns on the wire (T0H / T1H / period).

**Confidence key** (as requested): HIGH = manufacturer datasheet text read; MEDIUM = 2+ independent library/secondary sources agree; LOW = single or unclear source. Where a chip has both a datasheet and library values that disagree, both are listed and the confidence refers to the datasheet row.

**How the datasheets were obtained.** All PDFs were read as text with `pdftotext` after fetching from the URL shown. "Mfr datasheet copy" means a PDF of the manufacturer's own document hosted by a reseller or archive (the manufacturer's own site was not reachable for these parts). Translations (DeepL) are flagged.

---

## 0. Headline findings

1. **Four chips have a published window that the current Normal preset (T0H about 250 ns, T1H about 725 ns) does not satisfy, yet xLights lumps them into the "ws2811 group":** UCS2912 (T0H 400 +/-40), UCS1912 (T1H 1000 +/-150), TM1903/TM1824/TM1934 (T0H min 310 ns) and the "0.3 / 0.9 us" family (TX1812, TX1818, LC8816E, GS8208B: T1H 850-950 ns). They may still work in practice, but there is no datasheet margin.
2. **TM1908 is genuinely new and in range.** Datasheet states it works at any bit period from 830 ns to 2.5 us provided T0H is 200-280 ns and T1H is 400-560 ns. So it can be driven at 1.0-1.25 us. It needs a TM1914-style 9-byte preamble (C1 C2 C3).
3. **LPD1886 is in range on timing** (T0L/T1L allowed up to 10 us, only the sums must be >= 800 ns), but it is a 12-bit (36 bits/pixel) chip, so only its 8-bit/GM-floating mode could fit, and that mode's bit count is not stated in the datasheet.
4. **No datasheet could be found for:** TM1830, TM1815, UCS2109, UCS2114, UCS5604, XL-2812, SM16803P/SM16813PB/SM16823E, WS2851, GS8608, UCS2909/UCS1909, INK1003 timing. These are marked "not found".

---

## 1. Ranked "worth implementing" list

| Rank | Candidate | Feasible on PRU | Confidence | What it takes |
|---|---|---|---|---|
| 1 | **TM1903 / TM1824 (RGBW) / TM1934 timing preset** (T0H 360, T1H 720, period 1250, non-inverted, reset >= 200 us) | Yes | HIGH (3 Titan Micro datasheets read) | Effectively the existing TM1814 preset (360/720/1250) with inversion switched off, no preamble (TM1934 mode bytes unverified, see 2.7). TM1824 is 4 bytes R,G,B,W. |
| 2 | **UCS2912 preset** (T0H 400, T1H 800, period 1200-1300, reset > 24 us) | Yes | HIGH (datasheet ver2.2 copy) | New timing row only. Normal's 250 ns T0H is 110 ns below the datasheet minimum. |
| 3 | **UCS1912 preset** (T0H 250, T1H 1000, period 1250, reset 24 us) | Yes | HIGH (translated datasheet) | New timing row only. FastLED disagrees (T1H 1250); see 2.3. |
| 4 | **"300/900/1250" preset** for TX1812, TX1818CA, LC8816E (GRBW), GS8208B, SM16703SP, SK6813 | Yes | HIGH (5 datasheets) | One preset covers the whole "RZ 0.3/0.9 us" family tightly; Normal's 725 ns T1H sits outside the +/-50 ns windows of TX1818CA, LC8816E and GS8208B. |
| 5 | **TM1908** (T0H 240, T1H 480, period 1000-1250; preamble `FF FF FF 00 00 00` + 3 current bytes) | Yes at period >= 1.0 us | HIGH (V1.2 datasheet) | New preset + 9-byte preamble (same mechanism as TM1914's 6 bytes). Niche part. |
| 6 | **LC8812 / LC8812B** compromise T1H about 750 ns | Yes | MEDIUM (two datasheet variants conflict, windows overlap at 750) | Covered by rank-4 preset except the 3535 variant (T1H 0.6). |
| 7 | **LPD1886 8-bit (GM floating)**: T0H 200, T1H 600, period 1000-1250, reset >= 24 us | Probably, 8-bit mode only | LOW for the 24-bit assumption (timing itself is HIGH) | Bit count in 8-bit mode is not stated; FastLED assumes 24 bits. 12-bit mode is not byte-granular. |
| 8 | **DP1903** | Probably covered by existing UCS1903-400 preset | LOW | Only a forum quote of the datasheet; FastLED disagrees. |
| - | HC2912C, CS8812, LB1908, SK6813/HV, WS2811C, WS2812C, WS2813B-RGBW | Already inside Normal | HIGH | Label/colour-order documentation only (section 3). |
| - | UCS5603, UCS9812, SM16803P/13PB/23E, GE8822, INK1003, UCS2603/7804, WS2851, GS8608 | Not implementable now | n/a | No usable timing/frame published (section 4). |

---

## 2. Per-chip tables

### 2.1 TM1908 (Titan Micro)

| Field | Value |
|---|---|
| Aliases / maker | TM1908, Titan Micro Electronics (Shenzhen) |
| Channels x bits | 3 x 8 (PWM 256 levels), plus a 3 x 7-bit current-set word |
| Wire order | R, G, B (data format table: R7..R0, G7..G0, B7..B0, MSB first) |
| T0H | 200 / 240 / 280 ns (min/typ/max) |
| T1H | 400 / 480 / 560 ns |
| T0L, T1L | not tabulated; implied by period |
| Output T0H' / T1H' | 200 / 240 / 280 ns and 400 / 480 / 560 ns |
| Bit period | 830 ns typ (1.2 MHz). **Datasheet footnote: chip works from 830 ns to 2.5 us (400 kHz) as long as T0H/T1H stay in the table ranges.** |
| Reset | >= 80 us low (min). Byte-to-byte low gap must stay <= 25 us or the chip resets. |
| Idle level | Low, not inverted (reset is "active low") |
| Frame | **Per frame, before pixels:** C1 = `FF FF FF`, C2 = `00 00 00` (48-bit mode command: 24-bit command + 24-bit complement; this pair = normal DIN/FDIN auto-switch mode). Alternates: `FF FF FA 00 00 05` = DIN only, `FF FF F5 00 00 0A` = FDIN only, `FF FF F0 00 00 0F` = test mode. Then **C3** (24 bits): R, G, B each = 0 + 7-bit current (0x00 = 2 mA, 0x7F = 25 mA), so max current = `7F 7F 7F`. Then D1..Dn pixels (3 bytes each). Each chip receives and forwards C1, C2, C3. Then reset. |
| Fits PRU? | **Yes**, run at 1.0-1.25 us period with T0H 240 / T1H 480. FastLED's 240/240/350 (830 ns) is below our floor, which is why it looks infeasible. |
| Confidence | **HIGH** |
| Source | https://github.com/cheemsHe/LEDdatasheet/blob/main/TM1908_V1.2_EN.pdf (Titan Micro V1.2 English datasheet, mirrored on GitHub) |
| Cross-check | FastLED master `fl/chipsets/led_timing.h` TIMING_TM1908: T1=240, T2=240, T3=350, RESET 80 us, encoder CLOCKLESS_ENCODER_TM1908 (library constant, agrees with the datasheet typicals). |

### 2.2 UCS2912 (12-channel driver)

| Field | Value |
|---|---|
| Aliases / maker | UCS2912 (12-channel "RGB x4" driver, SOP16). The maker is not named on the copy (UCS-series part number); the sibling UCS1912 copy is watermarked www.icdemi.com. |
| Channels x bits | 12 outputs = 4 RGB groups per IC; 8 bits/channel, **96 bits per IC** (R1 G1 B1 R2 G2 B2 ... R4 G4 B4), MSB first |
| Wire order | R, G, B |
| T0H / T0L / T1H / T1L (forwarded code) | 0.4 us +/-40 / 0.8 us +/-80 / 0.8 us +/-80 / 0.4 us +/-40 |
| T0H / T0L / T1H / T1L (controller-sent) | 0.4 / 0.9 / 0.8 / 0.5 us typ (no tolerance given) |
| Bit period | 1.2 us (forwarded) or 1.3 us (controller table); FMAX 800 kbps min |
| Reset | > 24 us low |
| Idle level | Low, not inverted |
| Frame | Reset, then n x 96 bits, then reset. No config/preamble. |
| Fits PRU? | **Yes.** Needs T0H about 400 ns; Normal's 250 ns T0H is outside the 360-440 window. |
| Confidence | **HIGH** |
| Source | https://www.ledlightinghut.com/files/UCS2912.pdf (datasheet "ver2.2", reseller copy of manufacturer document) |
| Conflicts | xLights treats UCS2912 as plain ws2811 group (Pixels.cpp). FastLED has no UCS2912; its UCS1912 class (250/1000/350) is a different chip. |

### 2.3 UCS1912

| Field | Value |
|---|---|
| Aliases / maker | UCS1912, marked "TR" (UCS series); datasheet title "12-way LED Driver Circuit-UCS1912" (www.icdemi.com watermark). dmx4all lists it as 4-channel SOP16 which conflicts with the "12-way" wording. |
| Channels x bits | 12 outputs = 4 RGB groups per IC; 8 bits/channel; 96 bits per IC; MSB first |
| Wire order | R, G, B |
| T0H / T0L / T1H / T1L | 250 ns / 1000 ns / 1000 ns / 250 ns typ, each +/-150 ns |
| Treset | 24000 ns +/-1000 ns (24 us low) |
| Bit period | 1.25 us; data rate 800 kbps |
| Idle level | Low, not inverted |
| Frame | Reset first (needed before frame 1), then n x 96 bits, then reset. Series resistor 39-50 ohm required in DIN/DOUT per datasheet. |
| Fits PRU? | **Yes.** Needs T1H about 1000 ns (window 850-1150). Normal's 725 ns T1H is outside. |
| Confidence | **HIGH** for the table (DeepL translation of the manufacturer PDF; the page carries a "Subscribe to DeepL Pro" banner, so numbers are as translated) |
| Source | https://www.docdroid.net/file/download/iKyrKek/ucs1912-tr-en-pdf.pdf (linked from https://github.com/FastLED/FastLED/issues/1480) |
| Conflicting value | **FastLED** `TIMING_UCS1912`: T1=250, T2=1000, T3=350 -> T0H 250, **T1H 1250**, period 1600 ns, reset 0 (header comment: "TH0=250ns, TH1=1250ns, TL0=1350ns, TL1=350ns"; older source marked "never been tested, according to the datasheet"). The datasheet above says T1H = 1000 ns, T1L = 250 ns, so FastLED's T1H 1250 / period 1600 is about 250 ns longer than this datasheet. Both lie inside the PRU's period range. |

### 2.4 TX1812 (TCWIN / Shenzhen Tiancheng Lighting)

| Field | Value |
|---|---|
| Aliases / maker | TX1812 (variants TX1812-1010A, TX1812CXA-F01 5050, TX1812Z5, TX1812MXA5-F01); TCWIN (Shenzhen Tiancheng Lighting, tczmled.com) |
| Channels x bits | 3 x 8; 24 bits/pixel |
| Wire order | **G, R, B**, MSB first ("按照GRB的顺序发送") |
| T0H | 220 / 300 / 380 ns |
| T1H | 800 / 900 / 1000 ns |
| T0L (listed as TOH') | 800 / 900 / 1000 ns |
| T1L (listed as TIH') | 220 / 300 / 380 ns |
| Bit period | 1.2 us derived (T0H+T0L); data rate 800 kHz typ |
| Reset | 80 us typ (no min listed) |
| Idle level | Low, not inverted |
| Frame | None beyond reset; 3.5-7.5 V supply; 500 ns typ DIN-DO delay |
| Fits PRU? | **Yes** |
| Confidence | **HIGH** for the 1010A datasheet (web transcription of the TCWIN datasheet, section 12 table; original PDF not directly read) |
| Source | http://www.tczmled.com/index.php?id=867 ("TX1812-1010A internal-IC datasheet") |
| Conflicting value | **NeoPixelBus** `NeoEsp32RmtSpeedTx1812`: T0H 300, T0L 600, T1H 600, T1L 300 (bit 900 ns), reset 80 us. That is T1H 600 vs the datasheet's 900 and a 900 ns bit that our PRU cannot do. The 5050 TX1812CXA-F01 retailer listing (item.szlcsc.com/839896.html) gives only 800 kbit/s and 200 ns propagation, no T0H/T1H. Do not trust the NeoPixelBus row for the 1010A part. |

### 2.5 TX1818CA (TCWIN, 12 V 5050) and LC8816E (Shenzhen LED Color, 12 V RGBW)

| Field | TX1818CA | LC8816E-RGBX |
|---|---|---|
| Channels x bits | 3 x 8, 24 bits/pixel | 4 x 8, 32 bits/pixel |
| Wire order | **R, G, B** (datasheet note: "按照RGB的顺序"), MSB first | **G, R, B, W** (datasheet 13: "GRBW (G7..W0)"), MSB first |
| T0H / T0L | 0.3 / 0.9 us +/-0.05 | 0.3 / 0.9 us +/-0.05 |
| T1H / T1L | 0.9 / 0.3 us +/-0.05 | 0.9 / 0.3 us +/-0.05 |
| Bit period | 1.2 us; FDIN 800 kHz | 1.2 us; FDIN 800 kbps |
| Reset | >= 80 us low | >= 80 us low |
| Idle level | Low | Low |
| Fits PRU? | Yes (needs T1H 900) | Yes (needs T1H 900) |
| Confidence | **HIGH** | **HIGH** |
| Source | https://file.elecfans.com/web1/M00/F1/E3/o4YBAGC28yaAS9FwABbMuIu_Vgg976.pdf (TCWIN datasheet, 15 pp, www.tczmled.com) | https://addressable-led.com/UploadFile/upi/file/20250703/LC8816E-RGBW.pdf (cited in FastLED led_timing.h) |
| Library cross-check | no library | FastLED `TIMING_LC8816E` 300/600/300, reset 80 us, native GRBW (agrees) |

### 2.6 LC8812 / LC8812B (Shenzhen LED Color Opto)

| Field | Value |
|---|---|
| Aliases / maker | LC8812, LC8812B-3535 (5050-style), LC8812B-3210 (side view); Shenzhen LED Color Co. |
| Channels x bits | 3 x 8 |
| Wire order | G, R, B, MSB first |
| T0H / T0L | 0.3 us +/-0.15 / 0.9 us +/-0.15 (both variants) |
| T1H / T1L | **3535 variant: 0.6 / 0.6 us +/-0.15; 3210 variant: 0.9 / 0.3 us +/-0.15** |
| Bit period | printed "TH+TL = 1.25 us +/-600 ns" (actual sums = 1.2 us); fDIN 800 kHz |
| Reset | 80 us low (printed; its tolerance text is garbled in the source) |
| Idle level | Low |
| Fits PRU? | **Yes** |
| Confidence | HIGH for each variant's own table; MEDIUM overall because the two variants disagree on T1H |
| Sources | https://www.slideshare.net/slideshow/lc8812b-3535-led/238469951 and https://www.slideshare.net/slideshow/lc8812b-3210-side-led/238469964 (slideshare uploads of the manufacturer spec) |
| Library values | NeoPixelBus aliases Lc8812 to `Sk6812` timing (400/850/800/450 ns, reset 80 us). That sits inside neither T1H window, but is what ESP32 users run. |
| Practical note | T1H of about 750 ns lies inside both variants' windows (0.6+0.15 = 0.75 and 0.9-0.15 = 0.75). |

### 2.7 TM1903, TM1934, TM1824 (Titan Micro, same timing table)

| Field | TM1903 | TM1934 | TM1824 |
|---|---|---|---|
| Channels x bits | 3 x 8 | 3 x 8 | **4 x 8 (RGBW)** |
| Wire order | R, G, B (text of refresh-rate section) | R, G, B (same text) | **R, G, B, W** (bit table), MSB first |
| T0H | 310 / 360 / 410 ns | 310 / 360 / 410 ns | 310 / 360 / 410 ns |
| T1H | 650 / 720 / 1000 ns | 650 / 720 / 1000 ns | 650 / 720 / 1000 ns |
| T0L, T1L | not tabulated; period minus T?H | same | same |
| Output T0H' / T1H' | 350 ns / (T1H' typ 700) | 350 / 700 ns | 360 / 720 ns |
| Bit period | 1.25 us typ; **works 1.25-2.5 us** | same | same |
| Reset | 200 us min, 20000 us max (printed "200 ... 20000") | 200 us (typ column) | 200 us |
| Max low gap inside a frame | 50 us | 50 us | 50 us |
| Idle level | Low (reset low active), **not inverted** | Low, not inverted | Low, not inverted |
| Frame | D1..Dn, reset. No preamble in TM1903 text. | Datasheet says "after power-on reset and reception of a mode setting command" and mentions "C1, C2" in the refresh-rate note, **but the command values are not printed in the text** (figures are images). Probably the TM1914 set (`FF FF FF 00 00 00` normal mode). | D1..Dn, reset (32-bit packets) |
| Fits PRU? | Yes | Yes (preamble value unverified) | Yes |
| Confidence | **HIGH** | HIGH timing, LOW for preamble | **HIGH** |
| Source | https://www.ledyilighting.com/wp-content/uploads/2025/02/TM1903-datasheet.pdf (V1.0) | https://www.ledyilighting.com/wp-content/uploads/2025/02/TM1934-datasheet.pdf (V1.0) | https://www.lumikit.com.br/firmware/hslc-tm/datasheets/TM1824_V1.1.pdf (V1.1, Chinese) |

Note: the **existing** TM1814/TM1914 preset (inverted, 360/720/1250) already matches these timings; TM1903/TM1824/TM1934 are its non-inverted twin. Normal's 250 ns T0H is below the 310 ns minimum of all three.

### 2.8 LPD1886 (and 8-bit mode)

| Field | Value |
|---|---|
| Aliases / maker | LPD1886; datasheet copy branded "Insomnia Lighting" (dmx4all). Original maker (Lisheng/LPD) not named in the copy. |
| Channels x bits | 3 channels. **12-bit mode (GM pin pulled low): 36 bits/pixel**, each channel "4 bits + 8 bits", high bit first. **GM floating = "256 levels"**; the datasheet does not say how many bits that mode consumes. |
| Wire order | not stated in text (R = OUT1) |
| T0H | 150 min / 200 recommended / 280 max ns |
| T0L | 500 min / 600 recommended / 10000 max ns |
| T1H | 450 min / 600 recommended / 9000 max ns |
| T1L | 150 min / 200 recommended / 10000 max ns |
| Bit period | T0H+T0L and T1H+T1L must be >= 800 ns; recommended 200+600 = 800 ns; data tempo 0.1-1.6 MHz; "recommended 1.25 MHz" |
| Reset / latch | >= 24 us low = frame-start reset. >10 us low after the data latches the PWM. |
| Idle level | Low, not inverted |
| Fits PRU? | **Timing: yes** (run at a 1.0-1.25 us period, T0H 200, T1H 600, which is inside every window). **Format: 8-bit mode only**, because 36 bits = 4.5 bytes/pixel cannot be byte-granular. |
| Confidence | HIGH (timing); LOW (8-bit mode = 24 bits/pixel, an assumption borrowed from FastLED's `LPD1886Controller1250Khz_8bit`) |
| Source | https://www.dmx4all.de/download/manuals_english/datasheet_lpd1886_english.pdf |
| Library values | FastLED local (Mar 2025) `ClocklessController<200,400,200>` and master `C_NS(200),C_NS(400),C_NS(200)` = T0H 200, T1H 600, period 800 ns; the 12-bit variant passes XTRA0=4 (sends 8 data bits + 4 zero bits per channel = 36 bits). Agrees with the datasheet recommended values, but the 800 ns period is below our 1.0 us floor, so use the datasheet's wider windows. |

### 2.9 DP1903

| Field | Value |
|---|---|
| Aliases / maker | DP1903 (Depuw, depuw.com); "WS2811 variant" |
| Channels x bits | 3 x 8 (single-line 3-channel RGB driver) |
| Wire order | not found |
| Timings | **Forum quote of the datasheet:** T0H 0.5 us, T0L 2 us, T1H 2 us, T1L 0.5 us, each +/-150 ns; Treset >= 24 us (bit period 2.5 us = 400 kbps) |
| FastLED (conflict) | 800 kHz: T0H 400, T1H 1400, period 1800 ns. "400 kHz": T0H 800, T1H 2400, **period 3200 ns (outside our 2.6 us ceiling)**. The FastLED comments are inconsistent with their own constants. |
| Idle level | Low (assumed) |
| Fits PRU? | The forum-quoted datasheet values are the same as our UCS1903-400 preset (about 500/2000/2500), so probably already covered; FastLED's 800 kHz row is also inside range. |
| Confidence | **LOW** |
| Sources | https://forum.arduino.cc/t/understanding-dp1903-timing-ws2811-variant/476444 (quotes the datasheet; datasheet URL http://www.depuw.com/Public/images/pdf/depuw/DP1903.pdf returned 404); FastLED `fl/chipsets/led_timing.h` |

### 2.10 GE8822 (library constant only)

| Field | Value |
|---|---|
| Timing | FastLED: T1=350, T2=660, T3=350 ns (T0H 350, T1H 1010, period 1360), reset 0. The header comment "TH0=350, TH1=1010, TL0=1010, TL1=350" is consistent with that. |
| Format | 12-bit per channel (FastLED passes XTRA0=4): 36 bits/pixel |
| Fits PRU? | Timing yes; format **no** (4.5 bytes/pixel) |
| Confidence | **LOW** (single library source; no datasheet found) |

---

## 3. Chips that already fit "Normal" (label/order documentation only)

All read from datasheet text. None needs a new preset, but several define a colour order or reset time worth recording.

| Chip | Order | T0H | T1H | Period | Reset | Source (datasheet copy) |
|---|---|---|---|---|---|---|
| SK6813E-A-003 (OPSCO 12 mA) | GRB (note: "G7-G6-...B0") | 0.2/0.3/0.4 us | 0.58/0.65/1.0 us | >= 1.2 us (T0L >= 0.6, T1L >= 0.2) | >= 80 us | ledyilighting.com/.../SK6813-datasheet.pdf |
| SK6813HV-09-6P (12 V) | **RGB** per its own note ("R7-R6-...B0"; may be a copy error) | 0.2/0.25/0.4 us | 0.65/0.75/1.0 us | >= 1.2 us (T0L >= 0.8) | >= 80 us | ledyilighting.com/.../SK6813HV-datasheet.pdf |
| HC2912C-2020 | GRB | 200-400 ns (units printed "us", clearly typo) | 800-1000 ns | >= 1200 ns (T0L 800-1000, T1L 200-400) | >= 200 (units garbled, assume us) | ledyilighting hub: HC2912C-2020 datasheet |
| CS8812 (12 V, e-RZ) | not stated (Ch00..Ch02) | 1/4 T = 312 ns | 3/4 T = 937 ns | T = 1/800 kHz = 1.25 us (max 1 MHz) | > 300 us; gap between codes < 10 us | ledyilighting.com/.../CS8812-datasheet.pdf |
| GS8206 / GS8208 / GS8208B | RGB for 8208B ("R7 -> B0"); not stated for 8206/8208 | 25% duty = 312 ns (8208B: 0.3 +/-0.05 us) | 75% duty = 937 ns (8208B: 0.9 +/-0.05 us) | 1.25 us | 8208B >= 80 us; 8206/8208 text says > 300 us | ledyilighting.com/.../GS8208B-datasheet.pdf etc. |
| LB1908 (12 V) | R, G, B | 250/300/350 ns | 700/800/900 ns | 1.1/1.2/1.3 us | >= 200 us; low gap <= 80 us | ledyilighting.com/.../LB1908-datasheet.pdf. Has a "mode setting command" (DIN/FDIN) whose bytes are not printed in the text. |
| SM16703SP | RGB | 200/300/400 ns | >= 700 (typ 900) ns | not tabulated | >= 200 us | ledyilighting hub: SM16703SP datasheet |
| WS2811C | RGB | 220-380 ns | 580-1000 ns | >= 1.25 us | not extracted | ledyilighting hub |
| WS2812C | GRB | 220-380 ns | 580-1000 ns | not extracted | > 280 us | ledyilighting hub |
| WS2813B-RGBW | **GRBW** (4 ch) | 220-380 ns | 580-1000 ns | not extracted | > 280 us | ledyilighting hub |

Of these, **WS2813B-RGBW** and **LC8816E** are the only 4-channel parts not already in the "supported" list; both just need the existing 4-character order `GRBW` on a suitable timing.

---

## 4. Found but not implementable (or not documented)

| Chip | What was found | Why not |
|---|---|---|
| **UCS5603** (UCS) | 3 ch, **12-bit** (4096 levels), 800 kbps, dual-input redundant (DIN/FDIN), 16-level current set per channel. Datasheet has no T0H/T1H table and no frame format. https://www.ledyilighting.com/wp-content/uploads/2025/02/UCS5603-datasheet.pdf | 12-bit and undocumented protocol. UCS5604: not found. |
| **UCS9812** (UCS) | 12 outputs = 4 RGB groups, **16-bit grey + 4-bit current = 20 bits per channel**, RGB order, MSB first, FMAX >= 1100 kbps (bit <= 0.91 us at the stated max). No timing table. https://www.ledyilighting.com/wp-content/uploads/2025/02/UCS9812-datasheet.pdf | No timing published; max rate is faster than our floor; 20-bit channels are not byte-granular. |
| **SM16803P / SM16813PB / SM16823E** (Sunmoon/chinaasic) | Only NeoPixelBus `NeoSm168x3Features.h`: 3 ch RGB, 2-byte trailer of 4-bit current gains (SM16803PB/813PB trailer `0RGB`, SM16823E `RGB0`); NeoPixelBus itself says "need spec sheet" for SM16803P. No datasheet or wire timing found (searches returned only SM16703P/SM16704PB/SM16825E). | No verified timing; confidence LOW. |
| **GE8822** | see 2.10 | 12-bit, no datasheet |
| **INK1003 / INK1002** (Greeled) | INK1002 datasheet: single-wire "AUTO-ZERO" code, 800 kHz, no T0H/T1H table. https://embdev.net/attachment/199047/INK1002_RGB_LED__GEINK1002RGB_.pdf. Community notes call INK1003 "WS281x/UCS1903 compatible" with different timings (auschristmaslighting wiki, makerforums). | No numeric timing found. |
| **UCS2603, UCS7804, TM1934 etc.** (Enttec protocol pages) | UCS2603: 3 ch 8-bit, redundant DIN, 8 kHz PWM. UCS7804: 3 or 4 ch 8-bit, single data line, 16 kHz PWM. WS2851: 3 ch 8-bit, 400 Hz PWM. All "no timing published". Pages: enttec.com.cn/pixel-protocols/UCS2603, /UCS7804, /WS2851 | Marketing pages only. |
| **GS8512, GS8526, SM18522P, TM512AC, UCS512x** | DMX512 receivers (RS-485), not single-wire pixels | Use FPP serial/DMX outputs |
| **ICND2110** | 16-bit, **two-wire clocked** (Enttec) | SPI path, not PRU |
| **GS8608** | WLED `TYPE_GS8608` comment: "same driver as WS2812, but will require signal 2x per second (else displays test pattern)" | No timing; behaves like Normal. A frame-refresh requirement, not a protocol difference. |
| **TM1830, TM1815, UCS2109, UCS2114, UCS5604, XL-2812, UCS2909, UCS1909** | **Not found** (no datasheet, no library constants located). | Cannot be specified. |

---

## 5. Library / vendor lists consulted (to enumerate chips)

| Source | What it contributed |
|---|---|
| FastLED master `chipsets.h`, `fl/chipsets/led_timing.h` (raw GitHub) | TM1908, LC8816E, GS1903, DP1903, UCS1912, GE8822, LPD1886 (+8-bit), WS2818, WS2814 timing constants. Local copy `~/Documents/Arduino/libraries/FastLED/src/chipsets.h` (Mar 2025) predates TM1908/LC8816E/GS1903. |
| NeoPixelBus `NeoEsp32RmtMethod.h`, `NeoSm168x3Features.h` | TX1812 (300/600/600/300, 80 us), GS1903 (300/900/900/300, 40 us), Lc8812 -> Sk6812 alias, SM168x3 gain trailer layout. |
| WLED `const.h` / `bus_wrapper.h` | Chip list: WS2812, WS2811-400k, TM1829, UCS8903/8904, APA106, FW1906, SK6812, TM1814, WS2805, TM1914, SM16825, GS8608 (all others already supported or covered above). |
| xLights `src-core/models/Pixels.cpp` `__equivalentPixels` | Vocabulary: cs8812, gs8202, ink1002/1003, lb1908, lpd1882, lx1203, p9883, sk6813, sm16711/12, ucs1909/1912, ucs2909/2912, ucs9812 (all lumped into ws2811 group). Datasheets located for cs8812, lb1908, ucs1912, ucs2912, ucs9812, sk6813; **none found for lpd1882, lx1203, p9883, sm16711/12, ucs1909, ucs2909, gs8202.** |
| ENTTEC pixel-protocol index (enttec.com.cn/pixel-protocols/, 102 parts) | Enumeration only (no timing). New names beyond the lists above: GS8108, GS8303-8319, GS8523-8525, P9412, P943, SM16511, TM1824, TM1934, TX1818, UCS2603, UCS7804, WS2808, WS2851, WS2816A/B/C. |
| ledyilighting.com "Addressable Pixel IC Datasheet Hub" | Source of ~70 manufacturer datasheet copies (SK6813, TM1903, TM1934, UCS5603, UCS9812, CS8812, LB1908, HC2912C etc.). |
| ESPixelStick | Its protocol list is on the project wiki, which could not be fetched in this session; not independently enumerated. |

## 6. Suggested next steps

1. Add the four presets with HIGH-confidence datasheets: **TM1903-family (non-inverted TM1814)**, **UCS2912 (400/800/1300)**, **UCS1912 (250/1000/1250)** and the shared **300/900/1250** preset. Each is a single timing row on the existing PRU loop.
2. Consider **TM1908** (new preset + 9-byte preamble `FF FF FF 00 00 00 7F 7F 7F`) if a part can be sourced to verify on a scope.
3. Do **not** add DP1903, UCS5603, UCS9812, SM168x3 or GE8822 until a real datasheet with a timing table is found.
4. Verify any new preset on an ESP32 analyser capture before shipping, as was done for TM1814/TM1914.
