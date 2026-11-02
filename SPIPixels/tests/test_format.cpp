// Native unit test for SPIChipFormat.h wire framing.
//   c++ -std=gnu++2a -I../src test_format.cpp -o t && ./t
#include "../src/SPIChipFormat.h"
#include <cstdio>
#include <vector>

static int failures = 0;

static void check(const char* name, const std::vector<uint8_t>& got, const std::vector<uint8_t>& want) {
    bool ok = (got == want);
    if (!ok) {
        ++failures;
        printf("FAIL %s\n  got :", name);
        for (auto b : got) printf(" %02X", b);
        printf("\n  want:");
        for (auto b : want) printf(" %02X", b);
        printf("\n");
    } else {
        printf("ok   %s (%zu bytes)\n", name, got.size());
    }
}

static std::vector<uint8_t> run(SPIChip chip, std::vector<uint8_t> rgb) {
    int n = (int)rgb.size() / 3;
    std::vector<uint8_t> out(spiWireSize(chip, n), 0xAA); // 0xAA fill to catch under-writes
    size_t len = spiFormat(chip, rgb.data(), n, out.data());
    out.resize(len);
    return out;
}

int main() {
    // size sanity
    if (spiWireSize(SPIChip::APA102, 2) != 16) { printf("FAIL APA102 size\n"); ++failures; }
    if (spiWireSize(SPIChip::WS2801, 3) != 9)  { printf("FAIL WS2801 size\n"); ++failures; }
    if (spiWireSize(SPIChip::P9813, 1)  != 12) { printf("FAIL P9813 size\n");  ++failures; }

    // WS2801 - raw passthrough
    check("WS2801 passthrough",
          run(SPIChip::WS2801, {1, 2, 3, 4, 5, 6}),
          {1, 2, 3, 4, 5, 6});

    // APA102 - start(4x00) + [FF c0 c1 c2] per px + 4x FF end (n=2 -> end=max(4,1)=4)
    check("APA102 2px",
          run(SPIChip::APA102, {0x0A, 0x14, 0x1E, 0x28, 0x32, 0x3C}),
          {0x00, 0x00, 0x00, 0x00,
           0xFF, 0x0A, 0x14, 0x1E,
           0xFF, 0x28, 0x32, 0x3C,
           0xFF, 0xFF, 0xFF, 0xFF});

    // SK9822 / HD107S - identical to APA102 except the end frame is zeros (FastLED, NeoPixelBus)
    check("SK9822 2px",
          run(SPIChip::SK9822, {0x0A, 0x14, 0x1E, 0x28, 0x32, 0x3C}),
          {0x00, 0x00, 0x00, 0x00, 0xFF, 0x0A, 0x14, 0x1E, 0xFF, 0x28, 0x32, 0x3C, 0x00, 0x00, 0x00, 0x00});

    // LPD6803 end frame is one zero clock per pixel: ceil(n/8) bytes (17 px -> 3), as FastLED / NeoPixelBus
    if (spiWireSize(SPIChip::LPD6803, 17) != 4 + 17 * 2 + 3) { printf("FAIL LPD6803 17px size\n"); ++failures; }
    if (spiWireSize(SPIChip::LPD6803, 8) != 4 + 8 * 2 + 1)   { printf("FAIL LPD6803 8px size\n"); ++failures; }
    if (spiWireSize(SPIChip::LPD6803, 9) != 4 + 9 * 2 + 2)   { printf("FAIL LPD6803 9px size\n"); ++failures; }

    // LPD8806 - 0x80|(v>>1) per channel, then ceil(n/32)=1 latch byte
    check("LPD8806 1px",
          run(SPIChip::LPD8806, {0x00, 0xFF, 0x02}),
          {0x80, 0xFF, 0x81, 0x00});

    // LPD6803 - start(4x00) + 16bit 1.5.5.5, end ceil(n/8)=1 zero
    // {0xFF,0x00,0x08} -> 5bit 0x1F,0x00,0x01 -> 0x8000|0x7C00|0x0001 = 0xFC01
    check("LPD6803 1px",
          run(SPIChip::LPD6803, {0xFF, 0x00, 0x08}),
          {0x00, 0x00, 0x00, 0x00, 0xFC, 0x01, 0x00});

    // P9813 - start(4x00) + [flag c0 c1 c2] + end(4x00)
    // {0x00,0xFF,0x80}: flag=0xC0 | (~00&C0)>>2 | (~FF&C0)>>4 | (~80&C0)>>6
    //                       = 0xC0 | 0x30 | 0x00 | 0x01 = 0xF1
    check("P9813 1px",
          run(SPIChip::P9813, {0x00, 0xFF, 0x80}),
          {0x00, 0x00, 0x00, 0x00, 0xF1, 0x00, 0xFF, 0x80, 0x00, 0x00, 0x00, 0x00});

    // P9813 end-frame scaling (Adafruit's empirical >64px finding): a bug
    // fix -- the end frame used to be a fixed 4 bytes regardless of length.
    if (spiWireSize(SPIChip::P9813, 64)  != 4 + 64*4 + 4) { printf("FAIL P9813 end-frame size @64\n"); ++failures; }
    if (spiWireSize(SPIChip::P9813, 65)  != 4 + 65*4 + 8) { printf("FAIL P9813 end-frame size @65 (should grow past 64px)\n"); ++failures; }
    if (spiWireSize(SPIChip::P9813, 128) != 4 + 128*4 + 8) { printf("FAIL P9813 end-frame size @128\n"); ++failures; }
    if (spiWireSize(SPIChip::P9813, 129) != 4 + 129*4 + 12) { printf("FAIL P9813 end-frame size @129\n"); ++failures; }

    // SM16716/SM16726 - 50 zero start bits, then per pixel: 1 marker bit +
    // 24-bit RGB (MSB first). Not byte-aligned. Expected bytes independently
    // computed bit-by-bit in Python (see commit notes), not hand-derived.
    if (spiWireSize(SPIChip::SM16716, 1) != 10) { printf("FAIL SM16716 size 1px\n"); ++failures; }
    if (spiWireSize(SPIChip::SM16716, 2) != 13) { printf("FAIL SM16716 size 2px\n"); ++failures; }
    check("SM16716 1px",
          run(SPIChip::SM16716, {0xAA, 0x55, 0xFF}),
          {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x35, 0x4A, 0xBF, 0xE0});
    check("SM16716 2px",
          run(SPIChip::SM16716, {0x00, 0xFF, 0x80, 0x01, 0x02, 0x03}),
          {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x20, 0x1F, 0xF0, 0x10, 0x10, 0x20, 0x30});

    // APA102 "HD": smallest 5-bit brightness that reaches the brightest channel, channels scaled up by 31/b.
    // {10,20,30}: m=30 -> b=ceil(30*31/255)=4 -> c'=(c*31+2)/4 = 78,155,233 (0x4E,0x9B,0xE9); header 0xE0|4.
    check("APA102HD 1px", run(SPIChip::APA102HD, {0x0A, 0x14, 0x1E}),
          {0x00, 0x00, 0x00, 0x00, 0xE4, 0x4E, 0x9B, 0xE9, 0xFF, 0xFF, 0xFF, 0xFF});
    check("APA102HD white+black", run(SPIChip::APA102HD, {255, 255, 255, 0, 0, 0}),
          {0x00, 0x00, 0x00, 0x00, 0xFF, 255, 255, 255, 0xE1, 0, 0, 0, 0xFF, 0xFF, 0xFF, 0xFF});
    check("SK9822HD zero end frame", run(SPIChip::SK9822HD, {255, 255, 255}),
          {0x00, 0x00, 0x00, 0x00, 0xFF, 255, 255, 255, 0x00, 0x00, 0x00, 0x00});
    {   // reconstruction property: channel*bri/31 reproduces the input to within half a step, for a grid of colours
        int worst = 0; bool ok = true;
        for (int r = 0; r < 256; r += 5) for (int g = 0; g < 256; g += 17) for (int b = 0; b < 256; b += 13) {
            uint8_t bri, c0, c1, c2; spiApa102Hd(r, g, b, bri, c0, c1, c2);
            if (bri < 1 || bri > 31) ok = false;
            int in[3] = {r, g, b}, outc[3] = {c0, c1, c2};
            for (int k = 0; k < 3; k++) {
                int recon = (outc[k] * bri + 15) / 31; int d = recon > in[k] ? recon - in[k] : in[k] - recon;
                if (d > worst) worst = d;
            }
        }
        if (!ok || worst > 1) { printf("FAIL APA102HD reconstruction (worst error %d)\n", worst); ++failures; }
        else printf("ok   APA102HD reconstruction error <= %d/255 over the colour grid\n", worst);
    }

    // HD108 (Rose Lighting spec V1.2): 128-bit start, per LED FF FF + R,G,B as 16-bit (x257), padding FF x (n/2+4).
    if (spiWireSize(SPIChip::HD108, 1) != 16 + 8 + 4) { printf("FAIL HD108 size 1px\n"); ++failures; }
    if (spiWireSize(SPIChip::HD108, 10) != 16 + 80 + 9) { printf("FAIL HD108 size 10px\n"); ++failures; }
    check("HD108 1px", run(SPIChip::HD108, {0x11, 0x22, 0x33}),
          {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
           0xFF, 0xFF, 0x11, 0x11, 0x22, 0x22, 0x33, 0x33,
           0xFF, 0xFF, 0xFF, 0xFF});
    check("HD108 full scale 0xFF -> 0xFFFF", run(SPIChip::HD108, {255, 0, 255, 1, 2, 3}),
          {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
           0xFF, 0xFF, 255, 255, 0, 0, 255, 255,
           0xFF, 0xFF, 1, 1, 2, 2, 3, 3,
           0xFF, 0xFF, 0xFF, 0xFF, 0xFF});

    // protocol mapping + default speeds
    uint32_t sp = 0;
    if (spiChipFromString("HD107S", sp) != SPIChip::SK9822 || sp != 20000000) { printf("FAIL hd107s map\n"); ++failures; }
    if (spiChipFromString("sk9822", sp) != SPIChip::SK9822 || sp != 8000000)  { printf("FAIL sk9822 map\n"); ++failures; }
    if (spiChipFromString("apa102", sp) != SPIChip::APA102 || sp != 8000000)  { printf("FAIL apa102 map\n"); ++failures; }
    if (spiChipFromString("sm16716", sp) != SPIChip::SM16716 || sp != 16000000) { printf("FAIL sm16716 map\n"); ++failures; }
    if (spiChipFromString("sm16726", sp) != SPIChip::SM16716 || sp != 16000000) { printf("FAIL sm16726 map\n"); ++failures; }
    // names and aliases (xLights groups; same frame as the primary chip)
    struct { const char* n; SPIChip c; uint32_t hz; } M[] = {
        {"apa101", SPIChip::APA102, 8000000}, {"APA102C", SPIChip::APA102, 8000000},
        {"apa102hd", SPIChip::APA102HD, 8000000}, {"sk9822hd", SPIChip::SK9822HD, 8000000}, {"hd107shd", SPIChip::SK9822HD, 20000000},
        {"hd108", SPIChip::HD108, 20000000}, {"NS108", SPIChip::HD108, 20000000},
        {"ws2803", SPIChip::WS2801, 1000000},
        {"lpd8803", SPIChip::LPD8806, 2000000}, {"lpd8809", SPIChip::LPD8806, 2000000}, {"ucs8812", SPIChip::LPD8806, 2000000},
        {"d705", SPIChip::LPD6803, 1000000}, {"lpd1101", SPIChip::LPD6803, 1000000}, {"ucs6909", SPIChip::LPD6803, 1000000}, {"ucs6912s", SPIChip::LPD6803, 1000000}};
    for (auto& m : M) {
        if (spiChipFromString(m.n, sp) != m.c || sp != m.hz) { printf("FAIL alias %s\n", m.n); ++failures; }
    }
    // new names: Opsco SK9826 family = HD108 frame at 10 MHz; APA107 / LC8822 / LC8823 = APA102; TLC59711 / TLC5971
    struct M2 { const char* n; SPIChip c; uint32_t hz; };
    const M2 N[] = {{"sk9826", SPIChip::HD108, 10000000}, {"sk9826mini", SPIChip::HD108, 10000000}, {"sk9826ec20", SPIChip::HD108, 10000000},
                    {"apa107", SPIChip::APA102, 8000000}, {"sk9822ec20", SPIChip::SK9822, 8000000}, {"sk9822mini", SPIChip::SK9822, 8000000}, {"lc8822", SPIChip::APA102, 8000000}, {"lc8823", SPIChip::APA102, 8000000},
                    {"tlc59711", SPIChip::TLC59711, 1000000}, {"TLC5971", SPIChip::TLC59711, 1000000}};
    for (auto& m : N) {
        if (spiChipFromString(m.n, sp) != m.c || sp != m.hz) { printf("FAIL alias %s\n", m.n); ++failures; }
    }

    // TLC59711: 28 bytes per chip = header 96 DF FF FF + OUT3..OUT0 as B,G,R 16-bit; chips sent last first; last chip zero padded
    if (spiWireSize(SPIChip::TLC59711, 1) != 28 || spiWireSize(SPIChip::TLC59711, 4) != 28 || spiWireSize(SPIChip::TLC59711, 5) != 56) {
        printf("FAIL TLC59711 size\n"); ++failures;
    }
    check("TLC59711 1px (3 outputs padded)",
          run(SPIChip::TLC59711, {0x01, 0x02, 0x03}),
          {0x96, 0xDF, 0xFF, 0xFF,
           0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0,    // outputs 3, 2, 1 are empty
           0x01, 0x01, 0x02, 0x02, 0x03, 0x03});                       // output 0
    check("TLC59711 5px (2 chips, last chip first)",
          run(SPIChip::TLC59711, {10, 11, 12, 20, 21, 22, 30, 31, 32, 40, 41, 42, 50, 51, 52}),
          {0x96, 0xDF, 0xFF, 0xFF,                                      // chip 1 holds pixel 4 in output 0
           0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0,
           50, 50, 51, 51, 52, 52,
           0x96, 0xDF, 0xFF, 0xFF,                                      // chip 0: outputs 3..0 = pixels 3..0
           40, 40, 41, 41, 42, 42,  30, 30, 31, 31, 32, 32,  20, 20, 21, 21, 22, 22,  10, 10, 11, 11, 12, 12});
    check("TLC59711 full scale",
          run(SPIChip::TLC59711, {255, 255, 255, 0, 0, 0, 255, 0, 255, 1, 2, 3}),
          {0x96, 0xDF, 0xFF, 0xFF, 1, 1, 2, 2, 3, 3,  255, 255, 0, 0, 255, 255,  0, 0, 0, 0, 0, 0,  255, 255, 255, 255, 255, 255});
    if (spiChipFromString("bogus",  sp) != SPIChip::UNKNOWN) { printf("FAIL unknown map\n"); ++failures; }

    printf(failures ? "\n%d FAILURE(S)\n" : "\nALL TESTS PASSED\n", failures);
    return failures ? 1 : 0;
}
