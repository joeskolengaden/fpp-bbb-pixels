# Clocked-chip candidates for the SPIPixels spidev plugin (research report)

Research date: 2026-11-02. Read-only web research plus local reads; nothing in the repo was changed except this file.
Scope: chips NOT already in `plugins/SPIPixels/src/SPIChipFormat.h` (APA102 family, SK9822, HD107S, HD108/NS108, WS2801/2803,
LPD8806/8803/8809/UCS8812, LPD6803/1101/D705/UCS6909/6912S, P9813, SM16716/16726; MBI6020 rejected), plus how to drive
single-wire WS281x-class chips from SPI MOSI.

Confidence legend (as requested): **HIGH** = manufacturer/vendor datasheet read by me (text or rendered page image),
**MEDIUM** = 2+ independent library implementations agree, **LOW** = single/unclear source. "not found" = I could not find a figure.

Local scratch copies of every datasheet/source I read are in
`<scratch dir>`
(`pdf*/`, `src/`); they are not part of the repo.

---------------------------------------------------------------------------------------------------------------------------------

## 0. Executive summary

Of the ~40 chips checked, only **four additions are real, safe wins**:

| Rank | Item | What it is | Effort | Confidence |
|---|---|---|---|---|
| 1 | **SK9826 / SK9826MINI / SK9826-EC20** | 16-bit, 2-wire; wire frame is **identical to our HD108** (>=128 zero start bits, per chip `1` + 3x5-bit gain + 3x16-bit, rising edge, extra clocks at end) | alias only (+ default colour order GRB) | HIGH (Opsco datasheet rev 04, page image read) |
| 2 | **APA107** (and LC8822/LC8823, "APA102-2020"-style clones) | APA102 frame. APA107 datasheet frame diagram read = APA102 byte for byte | alias only | APA107 HIGH (datasheet), but a seller blog contradicts itself; LC8822/LC8823 LOW (no frame found) |
| 3 | **TLC59711 / TLC5971** (TI) | 4 RGB outputs per chip, 16-bit, **no latch pin** (auto-latch on clock idle), 224-bit packet with a 6-bit write command `0x25` | new `case`, ~25 lines, one blob per frame | HIGH (TI datasheet SBVS181A + SBVS146D) and MEDIUM (Adafruit + NeoPixelBus agree) |
| 4 | **WS281x-class over SPI MOSI** (WS2812/B, SK6812, WS2811, TM1814/TM1914 inverted) | bit-encode each data bit into 4/5/8 SPI bits | new "family" (encoder + idle/reset), needs `spidev.bufsiz` raise | math HIGH; BBB behaviour MEDIUM (kernel source read, no scope data) |

Everything else is either **structurally impossible with MOSI+SCLK only** (MY9221/MY9231/MY9291/MY9268: dual-edge clock + DI-pulse
latch; TLC5947/TLC5948, DM633/DM634/DM13A, MBI5xxx, A6282: latch pin, GS clock, or non-PWM; HL1606: latch pin), **needs the SPI CS
line used as a latch** (A6281/ShiftBrite), **is single-wire despite looking clocked** (APA109, UCS9812, LPD1886, GE8822, P943/P9883/P9412 ...),
or I could **not find a datasheet** (DM412, ICND2110, RM2021, LC8822/23 frame, SM16727, HD109, APA102-8192/65536).

---------------------------------------------------------------------------------------------------------------------------------

## 1. What "stateless over spidev" excludes (decision rules I applied)

A chip is feasible only if ALL of these hold:
1. Data is sampled on ONE clock edge per bit (SPI hardware changes MOSI on only one edge, so a dual-edge-sampling chip sees every bit twice).
2. Latch/commit is implied by the frame itself (start/end bits or clock idle), never by a separate pin or by pulsing DI while the clock idles
   (SPI cannot move MOSI without clocking SCLK).
3. Any config (brightness, mode) can be re-sent inside every frame without side effects, in the same shift chain.
4. No mandatory free-running GS clock.

Optional extension considered separately: **CS as latch** (A6281): spidev holds CS low for the whole transfer and releases it high at the end
(omap2-mcspi in single-message mode drives CS via the FORCE bit, see `spi-omap2-mcspi.c` `omap2_mcspi_set_cs`). A chip whose latch is a
LOW->HIGH edge on a pin could be wired to CS. This violates "no extra latch pin" only if you count CS as extra; it is flagged where relevant.

---------------------------------------------------------------------------------------------------------------------------------

## 2. Feasible candidates (per-chip sections)

### 2.1 TLC59711 / TLC5971 (Texas Instruments) -- RECOMMENDED NEW CHIP

* Aliases: TLC59711 (SBVS181A, 3.0-5.5 V logic, 10 MHz); TLC5971 (SBVS146D, same packet, 20 MHz); Adafruit "TLC59711 12-channel 16-bit PWM breakout" boards;
  NeoPixelBus `Tlc59711*Feature`. Not a pixel IC in the WS2812 sense: it is a **constant-current sink driver** (4 RGB LEDs per chip, common-anode LEDs), so the "pixel" is an external RGB LED.
* Manufacturer: Texas Instruments. Channels: 12 (4 x RGB). 16-bit grayscale per channel, 7-bit global brightness per colour (BC), 5 function-control bits.
* SPI: SDTI sampled on **SCKI rising edge**, MSB first -> SPI mode 0 or 3. Max SCKI 10 MHz (TLC59711) / 20 MHz (TLC5971); min 0.007 MHz. tWH/tWL >= 10 ns, setup 5 ns, hold 3 ns (TLC59711).
* **Per-chip packet = 224 bits = 28 bytes** (datasheet Fig. 31, Fig. 24, Table 5; HIGH):
  `[6b write cmd = 100101 (0x25)] [5b FC: OUTTMG, EXTGCK, TMGRST, DSPRPT, BLANK] [7b BC_B][7b BC_G][7b BC_R] [16b GS OUTB3][16b GS OUTG3][16b GS OUTR3] ... [OUTB0][OUTG0][OUTR0]`
  i.e. latch bit numbers 217 (OUTTMG) down to 213 (BLANK), BC 212-206 (B), 205-199 (G), 198-192 (R), GS 191-0 with OUTR0 in bits 15-0.
  If the first 6 bits shifted into a chip are not `100101` at latch time the data is ignored (so garbage frames are harmless).
* FC bits: OUTTMG=1 (rising-edge output switching), EXTGCK=0 (internal oscillator as GS clock), TMGRST=1, DSPRPT=1 (auto display repeat), BLANK=0 (outputs on).
  Both Adafruit (`command |= 0x16`, i.e. 10110) and NeoPixelBus (`Default = EmiRisingEdge|DisplayTimerReset|AutoDisplayRepeat`) use exactly this. BLANK powers up as 1 (outputs off) so BLANK=0 must be in every packet.
* **Stateless header, 4 bytes, all-full-brightness: `96 DF FF FF`** (0x96 = 100101 + OUTTMG=1 + EXTGCK=0; 0xDF = TMGRST 1, DSPRPT 1, BLANK 0, BC_B[6:2]=11111; then BC bits all 1).
  Verified against NeoPixelBus `Tlc59711ElementsSettings::Encode` (byte0 0x94|0x02, byte1 0xC0|BC_B>>2, byte2 BC_B<<6|BC_G>>1, byte3 BC_G<<7|BC_R).
* **Chain order / sequence**: a chain of N chips needs N x 224 bits in one burst; the packet for the **last** chip in the chain is sent first (datasheet "Write the 224-bit packet for the Nth TLC59711 first").
  Inside a chip the order is OUT3 first, OUT0 last, each as **B, G, R** 16-bit big-endian (Adafruit sends channel index 11..0 where index 3n = R of LED n; NeoPixelBus sends the buffer reversed).
  Wire for FPP: for chip c = N-1 down to 0: header, then pixels 4c+3, 4c+2, 4c+1, 4c+0 each as B,G,R (the FPP colour order setting can absorb the channel permutation).
  8-bit -> 16-bit: `v*257` (0xFF -> 0xFFFF).
* **Latch / idle** (datasheet Fig. 25, text): internal latch pulse is generated when SCKI has no rising edge for **8x the period between the last two rising edges**
  (the datasheet clamps this to between 666 ns and 2.74 ms); then the next clock must not start for >= 8 internal-clock periods, printed as **1.34 ms** in Fig. 25/33 and as 1.34 us in the external-clock text (TI inconsistency).
  Use >= 2.74 ms + 1.34 ms ~ 4.1 ms between frames (FPP frame periods are >= 10 ms).  spidev end-of-transfer to next transfer gap is far above 8 clock periods, so latch is automatic.
  Danger: a gap of >= 8 clock periods **inside** the burst would latch a partial shift. Keep the whole chain in one spidev transfer (also see the 4096 byte spidev limit, section 4.6).
* Sizes: `wire = 28 * ceil(nPix/4)` bytes; pad the last chip with zeros. 100 chips = 2800 B.
* Clock advice: Adafruit uses 1 MHz mode 0 plus a 200 us delay after the burst; NeoPixelBus comments that **3.6 MHz works while 3 MHz gave flicker between chips** (its default `SpiSpeed3600Khz`) -- empirical, no explanation given. Default 1-4 MHz; cap 10 MHz.
* Gotchas: TLC5971 and TLC59711 share the 224-bit/25h layout (verified text in both PDFs). Constant-current: IREF resistor sets max current, BC scales it.
* Sources (HIGH): TI TLC59711 SBVS181A https://www.ti.com/lit/ds/symlink/tlc59711.pdf ; TLC5971 SBVS146D https://www.ti.com/lit/ds/symlink/tlc5971.pdf ;
  (MEDIUM) https://github.com/adafruit/Adafruit_TLC59711 (`write()`), https://github.com/Makuna/NeoPixelBus (`Tlc59711RgbFeatures.h`, `Tlc59711GenericMethod.h`).
* **Confidence: HIGH (datasheet) and MEDIUM (two libraries agree). Feasibility: yes.**

### 2.2 SK9826 / SK9826MINI / SK9826-EC20 (Opsco / Dongguan Opsco Optoelectronics) -- RECOMMENDED ALIAS OF HD108

* Aliases: SK9826, SK9826MINI, SK9826-EC20 (all Opsco). Seller blogs also list "APA102-65536" and "SK9826" together as 16-bit parts at 4 kHz refresh (LOW, seller claim only).
* 3 channels (RGB), **16-bit gray + 5-bit gain per channel**, 2-wire (DIN/DCLK, DOUT/DCLKO), max serial input 30 MHz (datasheet text), refresh up to 4 kHz, cascade up to 1024.
* **Frame (HIGH, Opsco SPC/SK9826 Rev 04, section 12 text + rendered page 7)**:
  * Start frame: **>= 128 zero bits**.
  * Per chip 64 bits, MSB first: `1` (start code) + 15 gain bits (5 each, S4..S0) + 48 gray bits. Diagram: b63=1, b62-b48 current gain, **b47-b32 OUTG, b31-b16 OUTR, b15-b0 OUTB** (gray order G,R,B for the GRB-lit part).
  * DCLK **rising edge** samples data (SPI mode 0 or 3).
  * Item C of the datasheet ("the first data frame is the corresponding distance from the end of the nearest LED driver chip") is garbled in translation; behaviour for a relaying chain is the same as HD108/APA102 (each chip keeps the first 64 bits it sees and relays the rest, so the first frame lands on the chip nearest the controller).
  * End: "additional pulses equal to the number of chips ... DIN remains high" (item D) -- this is exactly the 0xFF pad we already send for HD108 (`nPix/2+4` bytes >= nPix bits).
* Gain-order conflict inside the same PDF: text says "red 5 bits first, then green, then blue", the table header says G, R, B. Irrelevant for our use because we send all gains = 31 (bytes `FF FF`).
* Our `SPIChip::HD108` frame (128-bit start, `FF FF` + R,G,B 16-bit each, pad) is **bit-identical** on the wire; only the colour-order default differs (the part lights GRB, so default the string colour order to GRB; FPP already supplies colour order).
* Min/max timing, latch time: no latch time given other than the extra clocks; maximum clock 30 MHz (datasheet), so default 10-20 MHz like HD108.
* Source: https://ecksteinimg.de/Datasheet/LED/LED0032/SK9826_REV04_EN.pdf ; also in https://github.com/HonghongLu/digital-LED-Datasheet (`opsco/SK9826 REV.04 CN.pdf`, `SK9826MINI REV.03 CN.pdf`); Normand SK9826MINI page confirms "1 start bit + 15 gain + 48 gray".
* **Confidence: HIGH. Feasibility: yes (alias).**

### 2.3 APA107 (Newstar / generic) -- ALIAS OF APA102

* Aliases: APA107. Package 5050 SMD, 2-wire SDI/CKI with SDO/CKO relay, 8-bit PWM, 5-bit global (current) brightness.
* **Frame (HIGH, APA107 spec Rev 01, page-5 diagram rendered and read)**: start frame 32 x `0`; LED frame 32 bits = `111` + 5-bit global, then **BLUE, GREEN, RED** 8-bit each; end frame 32 x `1`. Identical to APA102. The datasheet's text paragraph on throughput ("(512000-40)/32 = 15998") is word-for-word the same as in the APA102 PDF, i.e. it was copied from the APA102 sheet.
* Clock rating: datasheet gives no maximum; sellers claim 30 MHz (LOW); oscillator 800-1200 kHz (datasheet table).
* Conflict (LOW sources): Superlighting blog says in one paragraph "slightly different protocol" and in a later one "same protocol as APA102, direct replacement"; no differing field is named. The only datasheet I could read matches APA102, so treat APA107 as APA102 (end frame: ones per its datasheet; zeros also works on APA102-protocol chips, see CROSSREF_LIBRARIES.md).
* Source: https://signliteled.com/wp-content/uploads/2024/08/APA107-Datasheet.pdf ; https://www.superlightingled.com/blog/sk9822-vs-apa102-vs-apa107-vs-hd107-vs-hd107s-vs-hd108/ (seller).
* **Confidence: HIGH for "datasheet = APA102 frame"; MEDIUM overall because of the seller contradiction. Feasibility: yes (alias).**

### 2.4 LC8822 / LC8823 (Shenzhen LED Color Opto) and similar APA102 look-alikes

* Aliases/relatives: LC8822, LC8823 (LED Color), "APA102-2020", "SK9822-EC20", "SK9822 mini", "HD107" (non-S).
* LC8823: SlideShare extract of the LED Color spec: "two-wire synchronous", SDI/CKI/SDO/CKO, 8-bit RGB + 5-bit brightness, "double data transmission", "max 27 kHz" (almost certainly a typo for MHz). **Start frame, LED frame layout and end frame: not found** (the frame figure is an image I could not read).
* SK9822-EC20 / SK9822 mini: package variants of SK9822 (Opsco); frame = SK9822 (already supported; its datasheet is in https://github.com/HonghongLu/digital-LED-Datasheet `opsco/SK9822-EC20 REV.05 EN.pdf`).
* HD107 (non-S): vendor blog only ("similar to APA107", 40 MHz claim); datasheet not found.
* Recommendation: expose `lc8822`, `lc8823` as **documented-unverified aliases** of APA102 (same pinout names, same descriptive spec), default clock <= 8 MHz, and mark "not datasheet-verified" in the UI, or skip them.
* Source: https://www.slideshare.net/slideshow/lc8823-led/238469893 (extract only).
* **Confidence: LOW. Feasibility: yes if APA102-compatible (not proven).**

### 2.5 APA102-8192 / APA102-65536 (APA Electronic) -- NOT RECOMMENDED

* Forum thread (FastLED community): APA's rep describes "APA102-8192" as a new **13-bit** part that "cannot be run in conjunction with the old models"; the posted datasheet looked like the APA102C one but data structure "slightly different". No frame found.
* "APA102-65536" is only named in a seller table (16-bit, 4 kHz). No datasheet found.
* Source: https://forum.makerforums.info/t/hi-does-anybody-know-if-fastled-supports-or-plans-support-for-apa102-8192/61858
* **Confidence: LOW. Feasibility: unknown. Do not implement.**

### 2.6 WS2803 / WS2801 details (already supported; confirmations only)

* WS2803 (Worldsemi): 18-channel (6 RGB) WS2801 with a higher clock; frame identical (raw 8-bit channel bytes, no framing). FastLED defines `WS2803Controller : WS2801Controller` at 25 MHz default (local `~/Documents/Arduino/libraries/FastLED/src/chipsets.h`, lines 296-297). WS2803 datasheet itself: Adafruit PDF URL returned 404, **not read** (MEDIUM from the library only).
* WS2801 datasheet (Adafruit mirror, read): **CLK held low > 500 us resets the chip and latches** the shifted data (text line "CLK pin keeps low more than 500uS ... data in the data shift registers will be latched"); after 24 clocks the chip enters relay mode. Our driver relies on the inter-frame gap for this.
* Source: https://cdn-shop.adafruit.com/datasheets/WS2801.pdf

### 2.7 A6281 (Allegro) / "ShiftBrite", "MegaBrite" -- ONLY WITH CS WIRED TO LATCH; LOW PRIORITY

* 3-channel constant-current driver = **one RGB LED per chip**, 10-bit PWM x3, 7-bit dot-correction x3, internal 800 kHz PWM clock, serial up to 5 MHz (feature list) / fCI max 6 MHz (table).
* 32-bit shift register, MSB (bit 31) first, **SDI sampled on CI rising edge**, SDO updates on falling edge. **Latch input LI: data is latched on a LOW->HIGH transition of LI**; LI must be low before the next CI rising edge. LI is a separate pin (plus OEI output-enable).
* Word 0 (grayscale, bits 31:30 = `00`): `[29:20] PWM counter 2 | [19:10] PWM counter 1 | [9:0] PWM counter 0` (ShiftBrite wiring convention: blue, red, green).
* Word 1 (configuration, bit 30 = `1`, bit 31 X): `[26:20] dot-correction 2 | [16:10] DC 1 | [6:0] DC 0`, `[8:7]` clock mode (`00` internal 800 kHz), `[29:28]` test bits must be 0. **Power-up default current is 36.5 % of max** so a config word must be sent (the datasheet shows Iout = Imax x (Scale/2+36.5)/100; Scale=127 -> 100 %).
* Daisy chain: N words per latch; tSU(LI) must be increased with chain length (datasheet note 3).
* Not stateless-friendly over plain MOSI+SCLK: needs LI toggle after each of two bursts (config, then grayscale) = two spidev transfers per frame with CS->LI wiring and OEI tied low.
* Source (HIGH): https://www.allegromicro.com/-/media/files/datasheets/a6281-datasheet.pdf .
* A6282 is **not** a candidate: it is a 16-channel on/off constant-current driver (no PWM).
* **Confidence: HIGH (datasheet). Feasibility: only with CS-as-latch; I would not implement.**

---------------------------------------------------------------------------------------------------------------------------------

## 3. Rejected / not-applicable candidates (with evidence)

| Chip(s) | Why not | Evidence | Conf. |
|---|---|---|---|
| **MY9221 / MY9231 / MY9291 / MY9268 (MY-Semi)** | **Dual-edge clock**: DI is sampled on BOTH edges of DCKI, so a SPI master (MOSI changes once per SCLK cycle) cannot send arbitrary bits; **latch = hold DCKI low >220 us, then pulse DI 4 times** (or 8/12/16 DI pulses in MY9231 mode switching) -- DI can't move without SCLK. Frame (for reference): MY9221 = 16-bit command word + 12 x 16-bit gray words = 208 bits per chip; MY9231 8-bit-wide command byte per chip: oneshot[6], reaction[5], bit width[4:3] (00=16,01=14,10=12,11=8), divider[2:1], scatter[0]. | FastLED master `src/fl/chipsets/my9221.h` ("samples data on every clock edge ... bit-bangs"; "hold DCKI low >220 us, then pulse DI 4x"); ESPHome `my9231.cpp` (`write_word_` toggles the clock per bit; 8/12/16 DI pulse sequences); Seeed `Grove_LED_Bar.cpp` (`send` toggles clock per bit; `latch` = 2 clocks, 240 us delay, 4 DI pulses). Datasheet MY9221_DS_1.0 URL returned HTML, not read. | MEDIUM (3 independent implementations) |
| **MBI6023 / MBI6024 (Macroblock)** | Same family as the already rejected MBI6020 (preamble + config + dot-correction + gray packets; falling-edge sampling). | Enttec page: "clocked two-wire, 10-bit"; MBI6024 sheet shows the CKI/SDI chain; datasheet MBI6023 not read. | LOW |
| **TLC5947 / TLC5948A (TI), DM633 / DM634 / DM13A (Siti), MBI5024/5030/5124 (Macroblock), STP16CPC26 (ST), TLC5940** | Need an **XLAT/LAT latch pin** and (TLC5947, DM63x) a free-running **GSCLK/GCK** (TLC5947) -- or are on/off only (STP16CPC26, A6282). NeoPixelBus's `Tlc5947GenericMethod` takes a latch pin and OE pin. Only the CS-as-latch trick could serve LOW->HIGH-latch parts and it does not solve GSCLK. | NeoPixelBus method list; DM634 sheet snippet "DAI clocked in on rising edge of DCK" (latch separate LAT). | MEDIUM |
| **HL1606 (Adafruit 2010 strips)** | Separate latch line, 2-bit colour. | https://learn.adafruit.com/hl1606-led-strip | MEDIUM |
| **UCS512 / WS2822 / GS8108 / GS8802 / GS8160 / GS8162** | DMX512-style receivers (RS-485 data line), not a clock+data pixel. GS8160/GS8162: **not found**. | Enttec pages ("DMX512" clock type); xLights Pixels.cpp group "DMX512P". | MEDIUM |
| **APA109, UCS9812, LPD1886, GE8822, P943/P9883/P9412, SK9816, WS2808, TX1818, CS8812, QED3001...** | **Single-wire** despite sometimes being filed as "clocked" (Enttec's auto-generated copy mislabels). UCS9812 datasheet read: "single line data transmission (return to zero code)", 1100 kbps, 20 bits/channel (16-bit gray + 4-bit current), 240-bit frame per 12-ch chip. LPD1886: FastLED treats as clockless (1.25 MHz data). APA109: Enttec "Data-Only". SK9816 datasheet: "single-wire". | UCS9812 PDF (ledyilighting.com); FastLED chipsets.h lines 771-777; enttec.com.cn APA109; SK9816 PDF. | HIGH (UCS9812, SK9816) / MEDIUM |
| **DM412, ICND2110 (Chipone), RM2021, SM16727, SM16726B, HD109, MBI6023 details** | **Datasheet not found** (searches returned only Enttec marketing text: DM412 "clocked RGB/RGBW 16-bit SOP16", ICND2110 "clocked 16-bit QFN20, 5-10 V"). xLights lists DM412 and RM2021 as "?, ? bit, ? wire". Nothing to implement from. | xLights `src-core/models/Pixels.cpp` header table; enttec.com.cn pages. | LOW |
| **SM16716 variants SM16726B/SM16727** | No datasheet found for either; SM16716 itself: 50-bit zero start + `1`+RGB per pixel, rising edge (SM16716 sheet via ledyilighting). Our SM16726 alias is MEDIUM (FastLED + library convention), not datasheet-verified. | https://www.ledyilighting.com/wp-content/uploads/2025/02/SM16716-datasheet.pdf | MEDIUM |
| **P9813 variants (PD9813, P9883)** | PD9813: no datasheet found. P9883 appears to be single-wire (Enttec). | search results | LOW |
| **BP5758D / SM2135 / KP18058 (I2C-like bulb drivers)** | Open-drain START/STOP conditions on a 2-wire bus, not a SPI pixel stream. Not examined further. | general knowledge | LOW |

Cross-checks of enumerated lists: FastLED master `src/fl/chipsets/`: apa102, hd108, lpd880x, **my9221** (bit-banged only), p9813, sm16716, ws2801 (+ `spi_chipsets`, `ucs7604`) -- nothing new beyond MY9221.
NeoPixelBus: DotStar (APA102 family), Hd108, Lpd6803/Lpd8806, P9813, **Tlc59711**, Tlc5947, Neo* single-wire. WLED `TYPE_2PIN`: WS2801, APA102, LPD8806, P9813, LPD6803 only. ESPHome neopixelbus: same set. xLights Pixels.cpp groups: the only clocked groups not already ours are MBI6020, MY9221/9231/9291, DM412, RM2021.

---------------------------------------------------------------------------------------------------------------------------------

## 4. Driving single-wire WS281x-class chips from SPI MOSI

### 4.1 Idea and the "published" encodings

Each data bit becomes `n` SPI bits (cell = 1/f_spi); a '1' is a longer run of high cells than a '0'. SPI clock/CS are unused (leave SCLK/CS unconnected).
* **rpi_ws281x SPI**: clock = 3x desired bit rate (2.4 MHz), `Bit 1 = 110`, `Bit 0 = 100`; README: many distributions cap SPI transfers at 4096 B, raise with `spidev.bufsiz=32768`; Pi 3 needs `core_freq=250`, Pi 4 `core_freq=500` and `core_freq_min=500` (idle CPU scaling changes the SPI clock). (jgarff/rpi_ws281x README, read via `gh api`.)
* **periph.io / Go `nrzled`, mbed neopixel-spi**: same 3-bit scheme at 2.4 MHz ("2.4-2.5 MHz, must be a reliable clock"), reset = 16 zero bytes (~53 us), buffer 12*N+3.
* **Adafruit CircuitPython neopixel_spi**: **6.4 MHz, 8 SPI bits per data bit: `bit0 = 0b11000000` (0xC0), `bit1 = 0b11110000` (0xF0)**, reset_time default 80 us, buffer 8*n*bpp; "for 400 kHz pixels use 3.2 MHz". (read source, `neopixel_spi.py`)
* Mikrocontroller.net thread: mixed reports of flicker on a normal Pi when the SPI clock is unstable (pre-`core_freq` fix).

### 4.2 Datasheet timing windows used (nominal +/-150 ns unless stated)

| Chip | T0H | T1H | T0L | T1L | Reset | Source (conf.) |
|---|---|---|---|---|---|---|
| WS2812 (v1) | 0.35 us | 0.70 us | 0.80 us | 0.60 us | > 50 us | Adafruit mirror WS2812.pdf (HIGH) |
| WS2812B (2015 sheet) | 0.40 | 0.80 | 0.85 | 0.45 | > 50 us | Adafruit WS2812B.pdf; LuxaLight copy identical (HIGH) |
| WS2812B newer revisions | 220-380 ns / 580-1000 / 580-1000 / 220-420, reset > 280 us as widely quoted -- **I could not find/verify this sheet**; treat as "not found" |  |  |  | not found | LOW |
| SK6812 | 0.30 | 0.60 | 0.90 | 0.60 | **80 us** | Adafruit SK6812 sheet (HIGH) |
| WS2811 400 kHz mode | 0.50 | 1.20 | 2.00 | 1.30 | > 50 us | WS2811.pdf (HIGH) |
| WS2811 800 kHz fast mode | half of the above: 0.25 / 0.60 / 1.00 / 0.65 (sheet note: "one half of the time when high speed mode, reset unchanged") | | | | | HIGH |
| TM1814 (inverted, idle HIGH) | **low** time of a 0: typ 360, max 410 ns; **low** time of a 1: min 650, typ 720 ns; period 1.25-2.5 us; **reset = line HIGH >= 200 us (up to 20 ms)**; between bytes HIGH must not exceed 50 us | TM1814 V1.1 section 11 (HIGH) |

### 4.3 BeagleBone McSPI clock reality (read from `drivers/spi/spi-omap2-mcspi.c`, mainline, HIGH for the code, MEDIUM for AM335x ref clock = 48 MHz)

`ref_clk_hz = OMAP2_MCSPI_MAX_FREQ = 48 000 000` unless the DT provides a clock; for requested `f >= 48 MHz/4096` the driver does `div = ceil(ref/f)`, `actual = ref/div` (granularity-1 divider). So **actual <= requested**, always rounded down to 48 MHz/N:

| requested | div | actual |
|---|---|---|
| 2.4 MHz / 2.5 MHz | 20 | 2.400 MHz |
| 3.0 MHz | 16 | 3.000 MHz |
| 3.2 MHz | 15 | 3.200 MHz |
| 3.6 MHz | 14 | 3.429 MHz |
| 4.0 MHz | 12 | 4.000 MHz |
| 4.8 MHz | 10 | 4.800 MHz |
| 6.0 / 6.4 MHz | 8 | **6.000 MHz** (NOT 6.4: Adafruit's 6.4 MHz becomes 6.0) |
| 6.9 MHz | 7 | 6.857 MHz |
| 8 MHz | 6 | 8.000 MHz |

(On Raspberry Pi the core clock sets the grid instead -- that is why `core_freq` fixes appear in the Pi guides.)

### 4.4 Encoding table and strict-window result (script: scratchpad `enc.py`; Y = inside datasheet window)

Cell time = 1/f. "PASS" = all four of T0H,T1H,T0L,T1L inside the +/-150 ns datasheet window.

| Encoding | f (BBB exact?) | bit period | '0' | '1' | T0H / T1H | WS2812 v1 | WS2812B 2015 | SK6812 | WS2811 800k | WS2811 400k | B per px |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 3 bits | 2.4 MHz (yes, div 20) | 1250 | 100 | 110 | 417 / 833 | n (T1L) | **PASS** | n | n | n | 9 |
| 4 bits "a" | 3.2 MHz (yes, div 15) | 1250 | 1000 | 1110 | 313 / 938 | n | **PASS** | n | n | n | 12 |
| 4 bits "b" | 3.2 MHz | 1250 | 1000 | 1100 | 313 / 625 | **PASS** | n (T1H 625 < 650) | **PASS** | **PASS** | n | 12 |
| **5 bits** | **4.0 MHz (yes, div 12)** | 1250 | 10000 | 11100 | **250 / 750** | n (T0L 1000 > 950) | **PASS** | **PASS** | **PASS** | n | 15 |
| 6 bits | 4.8 MHz (yes, div 10) | 1250 | 110000 | 111100 | 417 / 833 | n | PASS | n | n | n | 18 |
| 8 bits (Adafruit) | 6.0 MHz (6.4 requested -> 6.0) | 1333 | 0xC0 | 0xF0 | 333 / 667 | n (T0L) | n (T1L 667 > 600) | **PASS** | **PASS** | n | 24 |
| 8 bits | 3.2 MHz | 2500 | 0xC0 | 0xF0 | 625 / 1250 | n | n | n | n | **PASS** | 24 |

Reading it: **no single encoding passes every chip's strict window**, but real chips decode with a threshold between T0H-max and T1H-min, and the field-proven
3-bit 2.4 MHz and 8-bit 6.4 MHz schemes work on WS2812/WS2812B. Suggested presets for the plugin (all derived, **not yet scoped on a BBB**):
* `ws2812` / `ws2812b` / `sk6812` / `ws2811-fast` universal: **5 bits @ 4.0 MHz, 0=`10000`, 1=`11100`** (exact BBB clock, T0H 250 / T1H 750 -- inside WS2812B 2015, SK6812 and WS2811-800 windows; only misses WS2812 v1 by 50 ns on T0L). Needs bit-packing (5 bits per data bit).
* byte-aligned alternatives: `4 bits @ 3.2 MHz, 1000/1100` (WS2812 v1, SK6812, WS2811-800) or `1000/1110` (WS2812B); `8 bits @ 6.0 MHz, 0xC0/0xF0` (SK6812, WS2811-800; borderline on WS2812B).
* `ws2811-slow` (400 kHz): 8 bits @ 3.2 MHz, `0xC0`/`0xF0`.
* **TM1814 / TM1914 inverted** (MOSI must idle HIGH; patterns invert so that the LOW run carries the bit):
  * 4 bits @ 3.2 MHz: `0`=`0111` (low 312 ns, <=410 OK), `1`=`0001` (low 938 ns, >=650 OK), period 1250 -- **PASS**. A 2-cell '1' (`0011`) = 625 ns FAILS the 650 ns minimum.
  * 8 bits @ 6.0 MHz: `0x3F` (low 333) / `0x07` (low 833) or `0x0F` (low 667, marginal vs 650) -- PASS. 5 bits @ 4.0 MHz: `01111` (250) / `00011` (750) -- PASS.
  * 3 bits @ 2.4 MHz: `011` gives low 417 ns = **7 ns over the 410 ns max -- do not use**.
  * TM1814 reset is line HIGH >= 200 us, so "idle high" is the reset state; the 8-byte current preamble (`3F 3F 3F 3F C0 C0 C0 C0`, project convention) is encoded like data.
* TM1914 values: not re-read (NeoPixelBus equates its timing with TM1814; the TM1913 V1.3 sheet fetched is the wrong chip).

### 4.5 Gap-safety (inter-word gaps) -- why 3-bit and 5-bit patterns are riskier

If the SPI controller inserts a pause between 8-bit words, MOSI **holds the last bit of the word** (assumption, see 4.7) for the gap:
* patterns whose last cell is `0` (WS281x `1000`,`1110`,`11000000`,`11110000`; TM1814 mirrored: last cell `1`) just lengthen the low (high) phase -- harmless up to ~6-50 us.
* 3-bit patterns: byte boundaries fall **inside** a pattern (after bit 2 of the third pattern and after bit 1 of the sixth in each 24-bit group), where the held level is `1` for a '1' bit (`110`) and always `1` after the first cell -> T1H/T0H are stretched. Not gap-safe.
* 5-bit and 6-bit patterns: boundaries inside patterns as well. Not gap-safe.
* 4-bit and 8-bit patterns: gap-safe by construction.
Whether the AM335x actually inserts gaps: kernel PIO loops call `spi_delay_exec(&xfer->word_delay)` (default 0). Transfers `>= DMA_MIN_BYTES = 160` use DMA (when the DT has dma channels, true for mainline BBB spi0/spi1) and FIFO mode is enabled when `len % bytes_per_word == 0` (depth 64, 32 with RX). So **long frames should be gap-free; short (<160 B) PIO frames are the unverified case** (a few pixels). No published BBB scope capture found.

### 4.6 Pitfalls (consolidated)

1. **spidev buffer**: `spidev.bufsiz` default 4096 (verified `spidev.c`: `static unsigned bufsiz = 4096;`). `write()` count > bufsiz -> EMSGSIZE, and for `SPI_IOC_MESSAGE` the **TX total and RX total are each capped at bufsiz** -- splitting into several `spi_ioc_transfer`s in one ioctl does NOT help. FPP's `SPIUtils::xfer` uses one `SPI_IOC_MESSAGE(1)` with `rx_buf = tx_buf` (so the RX bounce buffer must also fit). Max pixels per ioctl at 4096 B: 455 (9 B/px), 341 (12), 273 (15), 227 (18), 170 (24). Raise via kernel cmdline `spidev.bufsiz=65536` (module param; reports that runtime changes sometimes fail: BeagleBoard forum). Splitting across two ioctls opens a multi-microsecond gap (CS toggle + syscall) that WS281x reads as reset if > 50 us, or as stretched low if shorter -- do not split a pixel chain.
2. **MOSI idle level**: mainline uapi defines `SPI_MOSI_IDLE_LOW` / `SPI_MOSI_IDLE_HIGH` (bits 17/18, `include/uapi/linux/spi/spi.h`) but **omap2-mcspi does not reference them** (grep: no match). On McSPI the idle level of D1/SIMO between transfers is **not documented anywhere I found** -> end every frame with the chip's reset level bytes (`0x00` normal, `0xFF` for TM1814) and **verify with a scope** (project has an ESP32 analyser). The first bit of the next frame is otherwise preceded by whatever level MOSI held.
3. **Reset**: append `ceil(300e-6 * f / 8)` bytes of idle level (WS2812B 50 us old sheet, 280 us newer revisions per forums, SK6812 80 us, TM1814 >= 200 us HIGH). At 4 MHz that is 150 B. Zephyr docs note ~6 us is enough on real WS2812 (LOW confidence), but do not rely on it.
4. **Clock accuracy**: BBB divides 48 MHz exactly (table 4.3) -- use only exact-grid requests; a request of 6.4 MHz silently becomes 6.0 MHz (period 1333 ns, T0H 333, T1H 667). On the Pi the clock depends on `core_freq`.
5. **FPP mode**: `SPIUtils` forces SPI mode 0, 8 bits per word; fine (SCLK unused). No CS toggling per word.
6. **Logic level**: 3.3 V MOSI into a 5 V WS281x needs a 74AHCT-class level shifter (VIH = 0.7*VDD; WS2811/SK6812 3.3 V tolerance chip-dependent). Not verified per chip.
7. **BBB pin collision**: SPI0 = P9_17 (CS0), P9_18 (MOSI/D1), P9_21 (MISO/D0), P9_22 (SCLK) (MathWorks BBB SPI page). Per project memory the **WL16/WL48 OLED nav buttons use P9-17/18/21/22/26**, so SPI0 is unavailable on those capes; SPI1 pin conflicts with the PRU pins were not checked here.
8. **Throughput**: 800 kHz chips need 30-32 us per pixel (same as the PRU), so 1000 px/port = ~32 ms/frame; SPI is not faster than the PRU path -- its value is on boards **without a PRU** (Raspberry Pi) and for extra ports.
9. **Memory/CPU**: encoding is a pure LUT (256 x n bytes); a 1000-pixel frame at 15 B/px is 15 kB.

### 4.7 Evidence quality for the BBB-specific claims
* McSPI divider, DMA/FIFO thresholds, `word_delay`: HIGH (source read, `gh api repos/torvalds/linux/contents/drivers/spi/spi-omap2-mcspi.c`, `spidev.c`).
* AM335x ref clock exactly 48 MHz: MEDIUM (driver default constant; the DT clock rate wasn't read).
* "MOSI holds last bit between words": **assumption, not verified**; no source found. This is why 4/8-bit-aligned patterns are the recommended safe choice.
* No published successful BeagleBone WS2812-over-SPI scope capture was found; the BeagleBoard forum thread "WS2812B support (neopixel)" is PRU based.

### 4.8 Stateless encoder sketch (fits `spiFormat(chip, rgb, nPix, out)`)

```c++
// 4-bit encoding @3.2 MHz: each data bit -> one nibble; one input byte -> 4 wire bytes.
static const uint8_t kPat0 = 0x8, kPat1 = 0xC;          // 1000 / 1100  (use 0xE for 1110)
static inline void ws_encode_byte(uint8_t in, uint8_t* o) {
    for (int i = 0; i < 4; i++) {                      // two data bits per output byte
        uint8_t hi = (in & 0x80) ? kPat1 : kPat0, lo = (in & 0x40) ? kPat1 : kPat0;
        o[i] = (hi << 4) | lo;  in <<= 2;
    }
}
// frame = nPix*3 bytes -> nPix*12 bytes, then ceil(300e-6*3.2e6/8)=120 zero bytes (reset, MOSI ends low).
// inverted chips (TM1814): patterns 0x7 / 0x1 and trailing 0xFF.
// 5-bit / 3-bit encodings: use spiAppendBits(out,bitPos,pattern,n) like SM16716 does.
```

---------------------------------------------------------------------------------------------------------------------------------

## 5. Ranked "worth implementing" list

| # | Item | Why | Statelessly feasible | Confidence | Code size |
|---|---|---|---|---|---|
| 1 | **SK9826 family -> HD108 frame** (alias `sk9826`, `sk9826mini`, `sk9826ec20`; default colour order GRB; max 30 MHz, default 10-20 MHz) | Datasheet frame is bit-identical to our HD108; zero new framing code | Yes | HIGH | ~3 lines |
| 2 | **APA107 -> APA102 alias** (`apa107`); optionally `lc8822`,`lc8823` as *unverified* aliases | APA107 datasheet frame diagram = APA102; LC882x frame unverified | Yes | HIGH (APA107) / LOW (LC882x) | ~2 lines |
| 3 | **TLC59711 / TLC5971** (`tlc59711`): 28 B per 4 px, header `96 DF FF FF`, chips sent last-to-first, OUT3..OUT0, B,G,R x257 | New real hardware class (cheap 12-ch 16-bit breakout boards, 4 RGB LEDs/chip); latch is just clock idle | Yes (one transfer/frame, >= 4.1 ms between frames; 1-4 MHz, mode 0) | HIGH + MEDIUM | ~25 lines (+ UI: BC brightness) |
| 4 | **WS281x-over-SPI family** (`ws2812spi`, `sk6812spi`, `ws2811spi`, `tm1814spi`) with 4-bit/3.2 MHz and 5-bit/4.0 MHz presets, idle-level + reset padding, `spidev.bufsiz` check/warning | Only way to drive WS281x on a Pi (no PRU) or extra BBB ports; encoding math is exact; timing windows verified against datasheets | Yes, but needs bufsiz raise and scope verification of MOSI idle + word gaps on the BBB | math HIGH / BBB behaviour MEDIUM | ~60 lines + doc |
| 5 | A6281 (ShiftBrite) with CS-as-latch | Niche; needs 2 transfers/frame and wiring change | Only with CS wired to LI | HIGH datasheet / low value | skip |
| -- | MY9221/9231/9291/9268, MBI6023/24, TLC5947/48, DM63x, HL1606, UCS512/GS81xx | Dual-edge/DI-pulse latch, latch/GSCLK pins, preamble state machines, or DMX | **No** | MEDIUM-HIGH | do not implement |
| -- | DM412, ICND2110, RM2021, SM16727, HD109, APA102-8192/65536 | No datasheet / frame found | unknown | LOW | do not implement until a datasheet exists |

Suggested order: 1 and 2 (minutes), 3 (an hour with a unit test against the `96 DF FF FF` header and a 2-chip golden vector), 4 only after a BBB scope/ESP32-analyser capture of MOSI idle level and word gaps.

---------------------------------------------------------------------------------------------------------------------------------

## 6. Sources (URL; type)

Datasheets read (HIGH):
* TI TLC59711 SBVS181A https://www.ti.com/lit/ds/symlink/tlc59711.pdf ; TI TLC5971 SBVS146D https://www.ti.com/lit/ds/symlink/tlc5971.pdf
* Opsco SK9826 Rev 04 https://ecksteinimg.de/Datasheet/LED/LED0032/SK9826_REV04_EN.pdf ; SK9816 (single-wire) via https://github.com/HonghongLu/digital-LED-Datasheet
* APA107 Rev 01 https://signliteled.com/wp-content/uploads/2024/08/APA107-Datasheet.pdf ; APA102 https://signliteled.com/wp-content/uploads/2024/08/APA102-Datasheet.pdf
* Allegro A6281 / A6282 https://www.allegromicro.com/-/media/files/datasheets/a6281-datasheet.pdf , .../a6282-datasheet.pdf
* Worldsemi WS2812 / WS2812B / WS2811 / WS2801 (Adafruit mirrors) https://cdn-shop.adafruit.com/datasheets/WS2812.pdf , WS2812B.pdf, WS2811.pdf, WS2801.pdf ; LuxaLight WS2812B copy https://www.luxalight.eu/sites/default/files/downloads/2020-03/Datasheet_WS2812B.pdf
* Opsco SK6812 https://cdn-shop.adafruit.com/product-files/1138/SK6812+LED+datasheet+.pdf
* Titan Micro TM1814 V1.1 https://www.lumikit.com.br/firmware/hslc-tm/datasheets/TM1814_V1.1.pdf
* UCS9812 https://www.ledyilighting.com/wp-content/uploads/2025/02/UCS9812-datasheet.pdf
Libraries / source (MEDIUM):
* https://github.com/adafruit/Adafruit_TLC59711 ; https://github.com/Makuna/NeoPixelBus (`Tlc59711RgbFeatures.h`, `Tlc59711GenericMethod.h`)
* https://github.com/FastLED/FastLED `src/fl/chipsets/my9221.h`; local `~/Documents/Arduino/libraries/FastLED/src/chipsets.h`
* https://github.com/esphome/esphome `components/my9231/my9231.cpp` ; https://github.com/Seeed-Studio/Grove_LED_Bar `Grove_LED_Bar.cpp`
* https://github.com/jgarff/rpi_ws281x README ; https://github.com/adafruit/Adafruit_CircuitPython_NeoPixel_SPI `neopixel_spi.py` ; periph.io `nrzled` docs https://pkg.go.dev/periph.io/x/devices/v3@v3.7.0/nrzled
* Linux `drivers/spi/spi-omap2-mcspi.c`, `drivers/spi/spidev.c`, `include/uapi/linux/spi/spi.h` (via `gh api repos/torvalds/linux/contents/...`)
* FPP `src/util/SPIUtils.cpp`, `src/channeloutput/GenericSPI.cpp` (a local clone of the FPP source)
Secondary / seller / marketing (LOW): Enttec pixel-protocol pages https://enttec.com.cn/pixel-protocols/<chip> ; Superlighting blog (APA107/HD107/HD108) ; FastLED community thread (APA102-8192) ; SlideShare LC8823 extract ; mikrocontroller.net WS2812-on-Pi thread ; BeagleBoard forum threads (spidev buffer size, WS2812B support).

Not read / failed: MY9221 datasheet (boxtec URL returned HTML), WS2803 datasheet (404), WS2812B newer-revision datasheet (not located), TM1914 datasheet (fetched TM1913 by mistake), DM412 / ICND2110 / RM2021 / LC8822 / LC8823 frame images.
