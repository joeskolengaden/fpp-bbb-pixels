// [fpp-bbb-pixels self-test] Verify PixelString channel maps against the live
// libfpp for every chip mode + the generalized decoration-byte preambles/
// trailer (TM1814/TM1914/UCS7604 preambles, SM16825E trailer).
// Prints PASS/BAD per check; exit 0 iff all PASS.
#include "channeloutput/PixelString.h"
#include "Sequence.h" // FPPD_OFF_CHANNEL / FPPD_WHITE_CHANNEL
#include <jsoncpp/json/json.h>
#include <cstdio>
static int fails = 0;
static PixelString* build(const char* order, int pix, const char* preambleProfile = nullptr) {
    Json::Value c; c["portNumber"] = 0;
    if (preambleProfile) c["preambleProfile"] = preambleProfile;
    Json::Value vs; vs["startChannel"] = 0; vs["pixelCount"] = pix;
    vs["brightness"] = 100; vs["gamma"] = "1.0"; vs["colorOrder"] = order;
    c["virtualStrings"].append(vs);
    PixelString* ps = new PixelString(true); ps->Init(c); return ps;
}
static void run(const char* order, int pix, int expect) {
    PixelString* ps = build(order, pix);
    int t = ps->m_outputChannels, pn = pix ? t / pix : 0;
    bool ok = (pn == expect); if (!ok) fails++;
    printf("  %-8s ch/node=%d %-4s map(px0):", order, pn, ok ? "PASS" : "BAD");
    for (int i = 0; i < pn && i < 8; i++) printf(" %d", ps->m_outputMap[i]);
    printf("\n");
    delete ps;
}
static void order(const char* o, int expect) {  // no-regression check for xLights uploads
    PixelString* ps = build(o, 2);
    int pn = ps->m_outputChannels / 2;
    if (pn != expect) { fails++; printf("  xLights order %s -> %d (want %d) BAD\n", o, pn, expect); }
    delete ps;
}
// Checks a decoration byte run at the FRONT of the output (a preamble):
// every mapped index must be FPPD_OFF_CHANNEL, and that string's own
// brightnessMap[0] (what channelData[FPPD_OFF_CHANNEL]==0 reads back as)
// must equal the expected literal -- this is the whole point of the
// generalized mechanism, so it's the one thing worth checking per byte.
static bool checkDecorationBytes(PixelString* ps, int startIdx, const uint8_t* want, int n) {
    bool ok = true;
    for (int i = 0; i < n && ok; i++) {
        ok = ps->m_outputMap[startIdx + i] == FPPD_OFF_CHANNEL &&
             ps->m_brightnessMaps[startIdx + i][0] == want[i];
    }
    return ok;
}
static void decorationTest(const char* name, const char* order, int pix,
                            const char* preambleProfile, const uint8_t* preWant, int preLen,
                            const uint8_t* trailWant, int trailLen) {
    PixelString* ps = build(order, pix, preambleProfile);
    int expectTotal = preLen + trailLen + ps->m_outputChannels - preLen - trailLen; // filled below
    (void)expectTotal;
    bool ok = true;
    if (preLen) ok = ok && checkDecorationBytes(ps, 0, preWant, preLen);
    if (trailLen) ok = ok && checkDecorationBytes(ps, ps->m_outputChannels - trailLen, trailWant, trailLen);
    if (!ok) fails++;
    printf("  %-28s %s (outCh=%d)\n", name, ok ? "PASS" : "BAD", ps->m_outputChannels);
    delete ps;
}
int main() {
    run("RGB", 2, 3); run("GRBW", 2, 4); run("WRGB", 2, 4);
    run("RGBWC", 2, 5);   // WS2805 / SM16804 (8-bit)
    run("RGBWCX", 2, 6);  // FW1906
    run("RGB16", 2, 6);   // UCS8903 (16-bit RGB)
    run("RGBW16", 2, 8);  // UCS8904 (16-bit RGBW)
    // RGBWC16 (SM16825E) is checked separately below -- it now carries an
    // auto-appended 4-byte trailer, so total channels isn't pix-divisible.
    // Regression guard: every color order xLights' FPP.cpp can emit must still
    // parse to the right channel count (our 5/6/16 sentinels must not collide).
    { const char* rgb[] = {"RGB","RBG","GRB","GBR","BRG","BGR"};
      for (auto o : rgb) order(o, 3);
      const char* rgbw[] = {"RGBW","RBGW","GRBW","GBRW","BRGW","BGRW","WRGB","WRBG","WGRB","WGBR","WBRG","WBGR"};
      for (auto o : rgbw) order(o, 4);
      order("W", 1);
      printf("  xLights color-order regression: %s\n", fails ? "FAILED" : "all 19 orders OK"); }

    // TM1814: 8-byte preamble via the generalized decoration mechanism (every
    // byte maps to FPPD_OFF_CHANNEL; the literal comes from that string's own
    // brightnessMap[0] -- not FPPD_WHITE_CHANNEL, which the pre-refactor
    // version used directly).
    { static const uint8_t pre[] = {0x3F,0x3F,0x3F,0x3F,0xC0,0xC0,0xC0,0xC0};
      decorationTest("TM1814 preamble", "WRGB", 2, "tm1814", pre, 8, nullptr, 0); }

    // TM1914: distinct 6-byte preamble, same underlying mechanism.
    { static const uint8_t pre[] = {0xFF,0xFF,0xF5,0x00,0x00,0x0A};
      decorationTest("TM1914 preamble", "RGB", 2, "tm1914", pre, 6, nullptr, 0); }

    // UCS7604 8-bit: colorOrder "RGBW" (no "16" suffix) -> CFG 0x03.
    { static const uint8_t pre[] = {0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0x00,0x02,
                                     0x03,0x08,0x08,0x08,0x08,0x00,0x00};
      decorationTest("UCS7604 8-bit preamble", "RGBW", 2, "ucs7604", pre, 15, nullptr, 0); }

    // UCS7604 16-bit: colorOrder "RGBW16" -> CFG 0x8B. Also checks that the
    // bit-depth auto-detect looks past a leading empty/short string.
    { static const uint8_t pre[] = {0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0x00,0x02,
                                     0x8B,0x08,0x08,0x08,0x08,0x00,0x00};
      decorationTest("UCS7604 16-bit preamble", "RGBW16", 2, "ucs7604", pre, 15, nullptr, 0); }

    // SM16825E: RGBWC16 (10 bytes/px), auto-detected trailer (no
    // preambleProfile needed -- triggered purely by whiteOffset==105).
    { PixelString* ps = build("RGBWC16", 2);
      bool ok = ps->m_outputChannels == 24; // 2*10 pixel + 4 trailer
      static const uint8_t trailWant[] = {0x29,0x4A,0x52,0x9F}; // g=5 gain packing (~58mA/ch)
      if (ok) ok = checkDecorationBytes(ps, 20, trailWant, 4);
      if (!ok) fails++;
      printf("  %-28s %s (outCh=%d)\n", "SM16825E trailer", ok ? "PASS" : "BAD", ps->m_outputChannels);
      delete ps; }

    // Per-port noPreamble opt-out: same TM1814 config as above, but with
    // noPreamble set -- must emit the pixel data straight away, zero
    // decoration bytes.
    {
        Json::Value c; c["portNumber"] = 0; c["preambleProfile"] = "tm1814"; c["noPreamble"] = true;
        Json::Value vs; vs["startChannel"] = 0; vs["pixelCount"] = 1;
        vs["brightness"] = 100; vs["gamma"] = "1.0"; vs["colorOrder"] = "WRGB";
        c["virtualStrings"].append(vs);
        PixelString* ps = new PixelString(true); ps->Init(c);
        bool ok = ps->m_outputChannels == 4; // just the 1 WRGB pixel, no preamble
        if (!ok) fails++;
        printf("  %-28s %s (outCh=%d, want 4)\n", "noPreamble opt-out", ok ? "PASS" : "BAD", ps->m_outputChannels);
        delete ps;
    }

    // Preamble ordering vs. a smart-receiver lead-in: the 36-channel v1
    // smart-receiver toggle/lead-out string (VirtualString(0): leadIn 0 +
    // toggle 18 + leadOut 18) must come FIRST, then the TM1814 preamble,
    // then the real pixel -- not preamble-before-receiver-sync.
    {
        Json::Value c; c["portNumber"] = 0; c["preambleProfile"] = "tm1814"; c["differentialType"] = 1;
        Json::Value vs; vs["startChannel"] = 0; vs["pixelCount"] = 1;
        vs["brightness"] = 100; vs["gamma"] = "1.0"; vs["colorOrder"] = "WRGB";
        c["virtualStrings"].append(vs);
        PixelString* ps = new PixelString(true); ps->Init(c);
        bool ok = ps->m_outputChannels == 36 + 8 + 4; // receiver sync + preamble + pixel
        static const uint8_t pre[] = {0x3F,0x3F,0x3F,0x3F,0xC0,0xC0,0xC0,0xC0};
        if (ok) ok = checkDecorationBytes(ps, 36, pre, 8); // preamble starts AFTER the 36-ch receiver block
        if (!ok) fails++;
        printf("  %-28s %s (outCh=%d, want 48)\n", "preamble after smart-recv", ok ? "PASS" : "BAD", ps->m_outputChannels);
        delete ps;
    }

    // ---- user-settable chip current (chipCurrent, % of the chip's range) and TM1914 mode (tm1914Mode) ----------------------
    {
        auto buildX = [](const char* order, int pix, const char* profile, const Json::Value& extras) {
            Json::Value c; c["portNumber"] = 0;
            if (profile) c["preambleProfile"] = profile;
            for (auto& k : extras.getMemberNames()) c[k] = extras[k];
            Json::Value vs; vs["startChannel"] = 0; vs["pixelCount"] = pix;
            vs["brightness"] = 100; vs["gamma"] = "1.0"; vs["colorOrder"] = order;
            c["virtualStrings"].append(vs);
            PixelString* ps = new PixelString(true); ps->Init(c); return ps;
        };
        auto pre = [&](const char* name, const char* order, const char* profile, const Json::Value& ex, const uint8_t* want, int n) {
            PixelString* ps = buildX(order, 2, profile, ex);
            bool ok = checkDecorationBytes(ps, 0, want, n); if (!ok) fails++;
            printf("  %-34s %s\n", name, ok ? "PASS" : "BAD"); delete ps;
        };
        auto trail = [&](const char* name, const Json::Value& ex, const uint8_t* want) {
            PixelString* ps = buildX("RGBWC16", 2, nullptr, ex);
            bool ok = ps->m_outputChannels == 24 && checkDecorationBytes(ps, 20, want, 4); if (!ok) fails++;
            printf("  %-34s %s\n", name, ok ? "PASS" : "BAD"); delete ps;
        };
        Json::Value e;
        e["chipCurrent"] = 100; { static const uint8_t w[] = {0x3F,0x3F,0x3F,0x3F,0xC0,0xC0,0xC0,0xC0}; pre("TM1814 current 100% (=default)", "WRGB", "tm1814", e, w, 8); }
        e["chipCurrent"] = 50;  { static const uint8_t w[] = {0x1F,0x1F,0x1F,0x1F,0xE0,0xE0,0xE0,0xE0}; pre("TM1814 current 50%", "WRGB", "tm1814", e, w, 8); }
        e["chipCurrent"] = 0;   { static const uint8_t w[] = {0x00,0x00,0x00,0x00,0xFF,0xFF,0xFF,0xFF}; pre("TM1814 current 0% (6.5 mA)", "WRGB", "tm1814", e, w, 8); }
        Json::Value m; m["tm1914Mode"] = "auto"; { static const uint8_t w[] = {0xFF,0xFF,0xFF,0x00,0x00,0x00}; pre("TM1914 mode auto-switch", "RGB", "tm1914", m, w, 6); }
        m["tm1914Mode"] = "fdin"; { static const uint8_t w[] = {0xFF,0xFF,0xFA,0x00,0x00,0x05}; pre("TM1914 mode FDIN only", "RGB", "tm1914", m, w, 6); }
        m["tm1914Mode"] = "din";  { static const uint8_t w[] = {0xFF,0xFF,0xF5,0x00,0x00,0x0A}; pre("TM1914 mode DIN only (default)", "RGB", "tm1914", m, w, 6); }
        Json::Value u;
        u["chipCurrent"] = 100; { static const uint8_t w[] = {0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0x00,0x02,0x03,0x0F,0x0F,0x0F,0x0F,0x00,0x00}; pre("UCS7604 current 100%", "RGBW", "ucs7604", u, w, 15); }
        u["chipCurrent"] = 50;  { static const uint8_t w[] = {0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0x00,0x02,0x03,0x08,0x08,0x08,0x08,0x00,0x00}; pre("UCS7604 current 50% (=0x08)", "RGBW", "ucs7604", u, w, 15); }
        u["chipCurrent"] = 0;   { static const uint8_t w[] = {0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0x00,0x02,0x03,0x01,0x01,0x01,0x01,0x00,0x00}; pre("UCS7604 current 0% (lowest step 1)", "RGBW", "ucs7604", u, w, 15); }
        Json::Value g;
        g["chipCurrent"] = 100; { static const uint8_t w[] = {0xFF,0xFF,0xFF,0x9F}; trail("SM16825E current 100% (gain 31)", g, w); }
        g["chipCurrent"] = 50;  { static const uint8_t w[] = {0x7B,0xDE,0xF7,0x9F}; trail("SM16825E current 50% (gain 15)", g, w); }
        g["chipCurrent"] = 0;   { static const uint8_t w[] = {0x00,0x00,0x00,0x1F}; trail("SM16825E current 0% (gain 0)", g, w); }
        { Json::Value none; static const uint8_t w[] = {0x29,0x4A,0x52,0x9F}; trail("SM16825E unset (gain 5, as before)", none, w); }
    }

    printf(fails ? "MAP TEST: %d FAILED\n" : "MAP TEST: all passed\n", fails);
    return fails ? 1 : 0;
}
