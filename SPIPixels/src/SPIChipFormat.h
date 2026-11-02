/*
 * SPIChipFormat.h - pure, dependency-free wire framing for clocked SPI pixel
 * chips. No FPP or Linux headers so it can be unit-tested natively.
 *
 * Input `rgb` is 3 bytes per pixel already in the desired color order (this is
 * exactly what FPP's PixelString::prepareOutput() returns). Output is the byte
 * stream to clock onto the SPI bus.
 *
 * SM16716/SM16726 use spiAppendBits() because their frame isn't byte-aligned
 * (50-bit start + 25 bits/pixel); every other chip here is byte-granular.
 *
 * MBI6020 was investigated a second time and the frame IS now confirmed --
 * official Macroblock "MBI6020 Preliminary Datasheet V2.00-EN" (2012-03),
 * read in full. SDI samples on CKI's FALLING edge (every other chip here is
 * rising-edge). No latch pin at all; framing is a silent Prefix (CKI+SDI
 * both held low >172 CKI cycles) between packets, not a clocked end frame.
 * Still NOT implemented, and for a structural reason rather than a missing
 * datasheet: MBI6020 needs a stateful 3-phase sequence --
 *   1) Configuration packet (PWM clock, sync mode, etc; sent once)
 *   2) Dot-correction packet (per-channel calibration; sent once, or on change)
 *   3) Gray-scale packets (48 bits/IC in 16-bit mode, 30 bits in 10-bit mode;
 *      repeating, one per frame, LAST IC in the chain sent FIRST)
 * -- each preceded by its own 48/30-bit preamble that encodes the exact
 * chain length N up front (H[5:0] A[9:0]=0 H[5:0] L[9:0]=N-1 P[3:0] X[1:0]=0
 * L[9:0] for 16-bit mode) and, for config/dot-correction, a required
 * duplicate-field parity check the chip uses to reject corrupted data. This
 * doesn't fit `spiWireSize(chip,nPix)`/`spiFormat(chip,rgb,nPix,out)`'s
 * stateless per-frame-blob shape at all -- it needs its own small state
 * machine (chain length known in advance, config/dot-correction sent once
 * before the first gray-scale frame, an idle-based prefix the SPI driver's
 * inter-transfer gap would need to be verified against). Worth doing as its
 * own design task if ever needed, not a `case` squeezed into this file's
 * existing pattern.
 *
 * Covered under GPL v2.
 */
#pragma once

#include <algorithm>
#include <cctype>
#include <cstdint>
#include <cstddef>
#include <cstring>
#include <string>

enum class SPIChip {
    APA102, // end frame of 1-bits, per the APA102 datasheet
    SK9822, // also HD107S: APA102 frame, but zero-valued end frame (FastLED / NeoPixelBus convention)
    WS2801,
    LPD8806,
    LPD6803,
    P9813,
    SM16716, // also SM16726 (identical frame; verified against FastLED sm16716.h)
    APA102HD, // APA102 frame, 5-bit per-pixel brightness chosen from the colour for finer low-light steps
    SK9822HD, // same, with SK9822/HD107S's zero end frame
    HD108,    // 16 bits per channel + 5-bit gains (Rose Lighting HD108 spec V1.2, NS108, Opsco SK9826 family)
    TLC59711, // TI TLC59711 / TLC5971: 4 RGB outputs per chip, 16-bit, 224-bit packet, latches itself when the clock goes idle
    UNKNOWN
};

// Map a protocol string to a chip + its default SPI clock (Hz). The aliases are chips that xLights groups with
// (and FastLED/NeoPixelBus drive identically to) a primary chip: same frame, same defaults.
static inline SPIChip spiChipFromString(std::string p, uint32_t& defaultSpeed) {
    std::transform(p.begin(), p.end(), p.begin(), ::tolower);
    // APA102 family: 4-byte start frame, 0xE0|brightness per pixel, end clocks. SK9822/HD107S end with zeros.
    if (p == "apa102" || p == "apa101" || p == "apa102c") { defaultSpeed = 8000000;  return SPIChip::APA102; }
    if (p == "apa102hd" || p == "apa102chd")              { defaultSpeed = 8000000;  return SPIChip::APA102HD; }
    if (p == "sk9822" || p == "sk9822ec20" || p == "sk9822mini") { defaultSpeed = 8000000;  return SPIChip::SK9822; }   // EC20 / mini = package variants
    if (p == "sk9822hd")                                  { defaultSpeed = 8000000;  return SPIChip::SK9822HD; }
    if (p == "hd107s")                                    { defaultSpeed = 20000000; return SPIChip::SK9822; }
    if (p == "hd107shd")                                  { defaultSpeed = 20000000; return SPIChip::SK9822HD; }
    if (p == "hd108" || p == "ns108")                     { defaultSpeed = 20000000; return SPIChip::HD108; }
    // Opsco SK9826 / SK9826MINI / SK9826-EC20: datasheet frame (Rev 04) is bit-identical to HD108; the part lights in G,R,B order (set the string colour order to GRB)
    if (p == "sk9826" || p == "sk9826mini" || p == "sk9826ec20") { defaultSpeed = 10000000; return SPIChip::HD108; }
    // APA107 datasheet (Rev 01) frame = APA102; LC8822 / LC8823 are sold as APA102-compatible (frame not independently verified)
    if (p == "apa107" || p == "lc8822" || p == "lc8823") { defaultSpeed = 8000000; return SPIChip::APA102; }
    // TI TLC59711 (SBVS181A) / TLC5971 (SBVS146D): same 224-bit packet. 1 MHz is Adafruit's proven clock; the chip allows 10 MHz
    if (p == "tlc59711" || p == "tlc5971")                { defaultSpeed = 1000000;  return SPIChip::TLC59711; }
    if (p == "ws2801" || p == "ws2803")                   { defaultSpeed = 1000000;  return SPIChip::WS2801; }
    if (p == "lpd8806" || p == "lpd8803" || p == "lpd8809" || p == "ucs8812") { defaultSpeed = 2000000; return SPIChip::LPD8806; }
    if (p == "lpd6803" || p == "lpd1101" || p == "d705" || p == "ucs6909" || p == "ucs6912s") { defaultSpeed = 1000000; return SPIChip::LPD6803; }
    if (p == "p9813")                                     { defaultSpeed = 1000000;  return SPIChip::P9813; }
    if (p == "sm16716" || p == "sm16726")                 { defaultSpeed = 16000000; return SPIChip::SM16716; }
    defaultSpeed = 1000000;
    return SPIChip::UNKNOWN;
}

// APA102 "HD": pick the smallest 5-bit brightness b (1..31) that can still reach the brightest channel, then scale the
// channels up by 31/b. The chip outputs c*b/31, so the result equals the input but the 8-bit steps are finer at low levels
// (at brightness 10/255 the colour byte steps by 1/155 of full scale instead of 1/10). b=1 for an all-black pixel.
static inline void spiApa102Hd(uint8_t r, uint8_t g, uint8_t b, uint8_t& bri, uint8_t& c0, uint8_t& c1, uint8_t& c2) {
    unsigned m = std::max(r, std::max(g, b));
    unsigned br = m ? (m * 31 + 254) / 255 : 1;   // ceil(m*31/255)
    auto sc = [br](unsigned c) { unsigned v = (c * 31 + br / 2) / br; return (uint8_t)(v > 255 ? 255 : v); };
    bri = (uint8_t)br; c0 = sc(r); c1 = sc(g); c2 = sc(b);
}

// Appends the low `nBits` of `value` (MSB-first) to a packed bitstream in
// `out`, starting at bit `bitPos` (bit 7 of out[0] is bitPos 0). Used only by
// chips whose frame length isn't byte-aligned (SM16716: 50-bit start + 25
// bits/pixel). Advances bitPos by nBits. Trailing partial bytes are left
// zero-padded, which is harmless -- it just shifts extra 0 bits past the end
// of the chain with no chip left downstream to latch them.
static inline void spiAppendBits(uint8_t* out, size_t& bitPos, uint32_t value, int nBits) {
    for (int b = nBits - 1; b >= 0; b--) {
        size_t byteIdx = bitPos / 8;
        int bitInByte = 7 - (int)(bitPos % 8);
        if (bitInByte == 7) {
            out[byteIdx] = 0; // first bit landing in this byte -- clear it
        }
        if ((value >> b) & 1u) {
            out[byteIdx] |= (uint8_t)(1u << bitInByte);
        }
        bitPos++;
    }
}

// Bytes needed on the wire for nPix pixels of the given chip.
static inline size_t spiWireSize(SPIChip chip, int nPix) {
    switch (chip) {
    case SPIChip::WS2801:
        return (size_t)nPix * 3;
    case SPIChip::APA102:
    case SPIChip::SK9822:
    case SPIChip::APA102HD:
    case SPIChip::SK9822HD: {
        size_t end = (nPix + 15) / 16;
        if (end < 4) end = 4;
        return 4 + (size_t)nPix * 4 + end;
    }
    case SPIChip::TLC59711:
        // one 28-byte packet per chip (4 RGB outputs); a partly filled last chip is padded with zeros
        return (size_t)((nPix + 3) / 4) * 28;
    case SPIChip::HD108:
        // 128-bit start frame + 64 bits per LED + padding clocks (FastLED: n/2+4 bytes of 0xFF; the datasheet
        // needs no end frame, but the cascade needs a few clocks to flush the last LEDs)
        return 16 + (size_t)nPix * 8 + (size_t)(nPix / 2 + 4);
    case SPIChip::LPD8806: {
        size_t latch = (nPix + 31) / 32;
        if (latch < 1) latch = 1;
        return (size_t)nPix * 3 + latch;
    }
    case SPIChip::LPD6803: {
        // one zero clock per pixel, rounded up to bytes: FastLED sends ~n/8 bytes
        // and NeoPixelBus (n+7)/8; half of that left the tail of long chains unlatched
        size_t end = (nPix + 7) / 8;
        if (end < 1) end = 1;
        return 4 + (size_t)nPix * 2 + end;
    }
    case SPIChip::P9813: {
        // Adafruit's original PaintYourDragon/p9813 C library found this
        // empirically (comment dated 2011-07-15, in p9813.c): a fixed
        // 32-bit end/latch frame only reliably drives ~64 pixels; longer
        // strings need an extra 32 bits of latch per additional 64 (or
        // fraction thereof). Not in any P9813 datasheet. Functionally inert
        // either way for this file's own P9813 frame (the flag byte always
        // has bits 7:6 set, so pixel data can never emit 32 consecutive
        // zero bits that could be mistaken for a start frame) -- this is
        // purely about giving downstream chips enough latch clocks.
        size_t end = 4 * std::max((size_t)1, (size_t)((nPix + 63) / 64));
        return 4 + (size_t)nPix * 4 + end;
    }
    case SPIChip::SM16716: {
        size_t bits = 50 + (size_t)nPix * 25;
        return (bits + 7) / 8;
    }
    default:
        return (size_t)nPix * 3;
    }
}

// Build the wire bytes. `out` must hold at least spiWireSize(chip, nPix) bytes.
// Returns the number of bytes written.
static inline size_t spiFormat(SPIChip chip, const uint8_t* rgb, int nPix, uint8_t* out) {
    size_t idx = 0;
    switch (chip) {
    case SPIChip::WS2801:
        memcpy(out, rgb, (size_t)nPix * 3);
        idx = (size_t)nPix * 3;
        break;

    case SPIChip::APA102:
    case SPIChip::SK9822:
    case SPIChip::APA102HD:
    case SPIChip::SK9822HD: {
        const bool hd = (chip == SPIChip::APA102HD || chip == SPIChip::SK9822HD);
        out[idx++] = 0x00; out[idx++] = 0x00; out[idx++] = 0x00; out[idx++] = 0x00; // start frame
        for (int i = 0; i < nPix; i++) {
            if (hd) {
                uint8_t bri, c0, c1, c2;
                spiApa102Hd(rgb[i * 3 + 0], rgb[i * 3 + 1], rgb[i * 3 + 2], bri, c0, c1, c2);
                out[idx++] = 0xE0 | bri;
                out[idx++] = c0; out[idx++] = c1; out[idx++] = c2;
                continue;
            }
            out[idx++] = 0xFF; // 0xE0 | 5-bit global brightness (full); per-px done upstream
            out[idx++] = rgb[i * 3 + 0];
            out[idx++] = rgb[i * 3 + 1];
            out[idx++] = rgb[i * 3 + 2];
        }
        size_t end = (nPix + 15) / 16;
        if (end < 4) end = 4;
        // APA102: 1-bits per datasheet. SK9822/HD107S: zeros (FastLED + NeoPixelBus) -- the
        // SK9822 latches on a zero frame, and APA102 only needs the clock edges anyway.
        uint8_t endByte = (chip == SPIChip::SK9822 || chip == SPIChip::SK9822HD) ? 0x00 : 0xFF;
        for (size_t e = 0; e < end; e++) out[idx++] = endByte; // clock data down the chain
        break;
    }

    case SPIChip::LPD8806: {
        for (int i = 0; i < nPix; i++) {
            out[idx++] = 0x80 | (rgb[i * 3 + 0] >> 1); // 7-bit, MSB set
            out[idx++] = 0x80 | (rgb[i * 3 + 1] >> 1);
            out[idx++] = 0x80 | (rgb[i * 3 + 2] >> 1);
        }
        size_t latch = (nPix + 31) / 32;
        if (latch < 1) latch = 1;
        for (size_t l = 0; l < latch; l++) out[idx++] = 0x00;
        break;
    }

    case SPIChip::LPD6803: {
        out[idx++] = 0x00; out[idx++] = 0x00; out[idx++] = 0x00; out[idx++] = 0x00; // start frame
        for (int i = 0; i < nPix; i++) {
            uint8_t c0 = rgb[i * 3 + 0] >> 3; // 5 bits each
            uint8_t c1 = rgb[i * 3 + 1] >> 3;
            uint8_t c2 = rgb[i * 3 + 2] >> 3;
            uint16_t v = 0x8000 | (c0 << 10) | (c1 << 5) | c2;
            out[idx++] = (v >> 8) & 0xFF;
            out[idx++] = v & 0xFF;
        }
        size_t end = (nPix + 7) / 8;
        if (end < 1) end = 1;
        for (size_t e = 0; e < end; e++) out[idx++] = 0x00;
        break;
    }

    case SPIChip::P9813: {
        out[idx++] = 0x00; out[idx++] = 0x00; out[idx++] = 0x00; out[idx++] = 0x00; // start frame
        for (int i = 0; i < nPix; i++) {
            uint8_t c0 = rgb[i * 3 + 0];
            uint8_t c1 = rgb[i * 3 + 1];
            uint8_t c2 = rgb[i * 3 + 2];
            uint8_t flag = 0xC0;
            flag |= (uint8_t)((~c0 & 0xC0) >> 2);
            flag |= (uint8_t)((~c1 & 0xC0) >> 4);
            flag |= (uint8_t)((~c2 & 0xC0) >> 6);
            out[idx++] = flag;
            out[idx++] = c0;
            out[idx++] = c1;
            out[idx++] = c2;
        }
        // end/latch frame: 32 bits per 64 pixels (or fraction), not a fixed
        // 32 bits -- see spiWireSize.
        size_t end = 4 * std::max((size_t)1, (size_t)((nPix + 63) / 64));
        for (size_t e = 0; e < end; e++) {
            out[idx++] = 0x00;
        }
        break;
    }

    case SPIChip::HD108: {
        // Rose Lighting HD108 spec V1.2: >=128 zero bits start frame; per LED 64 bits = marker '1' + 3x 5-bit gain (we use the
        // maximum, 31, so both header bytes are 0xFF; brightness is carried by the 16-bit values) + R,G,B as 16-bit MSB first.
        // 8-bit input is widened x257 (0x00->0x0000, 0xFF->0xFFFF) so full scale stays full scale.
        for (int i = 0; i < 16; i++) out[idx++] = 0x00;
        for (int i = 0; i < nPix; i++) {
            out[idx++] = 0xFF; out[idx++] = 0xFF;
            for (int c = 0; c < 3; c++) { out[idx++] = rgb[i * 3 + c]; out[idx++] = rgb[i * 3 + c]; }
        }
        for (int e = 0; e < nPix / 2 + 4; e++) out[idx++] = 0xFF;
        break;
    }

    case SPIChip::TLC59711: {
        // TI TLC59711 / TLC5971 (datasheet SBVS181A fig. 31, table 5): per chip a 224-bit packet, MSB first:
        //   write command 100101 | OUTTMG=1 EXTGCK=0 TMGRST=1 DSPRPT=1 BLANK=0 | brightness-control B,G,R = 127 each (7 bits) |
        //   16-bit grayscale OUTB3 OUTG3 OUTR3 ... OUTB0 OUTG0 OUTR0  -> 4 header bytes 96 DF FF FF + 24 data bytes.
        // The chip nearest the controller is the LAST packet in the chain, so packets go out last chip first, and inside a packet
        // output 3 goes first. Input bytes are taken as B,G,R of each output (native order BGR); 8-bit is widened x257.
        // A chip latches by itself when SCLK stays idle for 8 clock periods, so the whole chain must go out in ONE transfer.
        int chips = (nPix + 3) / 4;
        for (int c = chips - 1; c >= 0; c--) {
            out[idx++] = 0x96; out[idx++] = 0xDF; out[idx++] = 0xFF; out[idx++] = 0xFF;
            for (int o = 3; o >= 0; o--) {
                int p = c * 4 + o;
                for (int k = 0; k < 3; k++) {
                    uint8_t v = (p < nPix) ? rgb[p * 3 + k] : 0;
                    out[idx++] = v; out[idx++] = v;
                }
            }
        }
        break;
    }

    case SPIChip::SM16716: {
        // 50 zero start bits, then per pixel: 1 marker bit ('1') + R/G/B
        // (8 bits each, MSB first). Not byte-aligned (25 bits/pixel) --
        // verified against FastLED's sm16716.h reference implementation.
        size_t bitPos = 0;
        spiAppendBits(out, bitPos, 0, 50);
        for (int i = 0; i < nPix; i++) {
            spiAppendBits(out, bitPos, 1, 1);
            spiAppendBits(out, bitPos, rgb[i * 3 + 0], 8);
            spiAppendBits(out, bitPos, rgb[i * 3 + 1], 8);
            spiAppendBits(out, bitPos, rgb[i * 3 + 2], 8);
        }
        idx = (bitPos + 7) / 8;
        break;
    }

    default:
        break;
    }
    return idx;
}
