#!/usr/bin/env python3
# [fpp-bbb-pixels] Patch PixelString.cpp (in core libfpp) for extra channel modes.
# Reuses existing int fields as sentinels (NO header change -> no ABI cascade):
#   whiteOffset  5 = 5-ch (WS2805/SM16825 RGB+WW+CW)   6 = 6-ch (FW1906)
#   whiteOffset  100+N = 16-bit with N source channels (2 wire bytes each):
#       103 = RGB-16 (UCS8903)   104 = RGBW-16 (UCS8904)   105 = RGBWW-16 (SM16825E)
#   receiverNum -3 = generalized literal-byte decoration string (protocol
#       preamble/trailer). Source is always the constant always-zero
#       FPPD_OFF_CHANNEL; the literal byte comes from THIS string's own
#       brightnessMap[0..255] (all entries set to the same value at
#       construction), so distinct decoration strings emit distinct bytes
#       without touching FPP's global constant channels. Runs of equal bytes
#       collapse into one string each (see the addDecorationBytes lambda in
#       Init()). Used for: TM1814 (8B preamble), TM1914 (6B preamble),
#       UCS7604 (15B preamble), SM16825E (4B trailer, appended after pixels).
#   config["noPreamble"] = true -> per-port opt-out from a preamble the
#       global pixelTiming preset would otherwise apply (see CONFIG.md).
#
# Parts (each independently guarded / idempotent):
#   A  5/6-channel color orders + generalized FlipPixels (reverse/zig-zag any width)
#   B  16-bit x N-channel ("<order>16"): each channel -> 2 wire bytes (value,value = x257)
#   C  generalized literal-byte preamble/trailer mechanism (TM1814/TM1914/UCS7604
#      preambles + SM16825E trailer, keyed off config["preambleProfile"]); the
#      preamble is applied AFTER any smart-receiver lead-in/sync (it configures
#      the pixel chip, not the receiver) and honors a per-port "noPreamble"
#      opt-out; + a latent FPP bug fix (default VirtualString ctor left
#      brightnessMap uninitialized)
#
# Rebuild libfpp.so after. Anchors match FPP 5.x. Aborts (no partial edit) on mismatch.
import sys
P = sys.argv[1] if len(sys.argv) > 1 else "/opt/fpp/src/channeloutput/PixelString.cpp"
s = open(P).read()
changed = False
OLDC = '            // c=0xFF (chip reads the low 6 bits -> max current on all 4 channels).\n            addDecorationBytes({ 0xFF, 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00 });'
NEWC = '            // c=0x3F: 6-bit current code (mA*10-65)/5 at its 38 mA maximum, top two bits 0,\n            // exactly what NeoPixelBus sends at max current -> 3F x4 then ~c = C0 x4.\n            addDecorationBytes({ 0x3F, 0x3F, 0x3F, 0x3F, 0xC0, 0xC0, 0xC0, 0xC0 });'

def repl(old, new, label):
    global s, changed
    n = s.count(old)
    assert n == 1, "  PixelString ERROR: [%s] matched %d (expected 1)" % (label, n)
    s = s.replace(old, new); changed = True
    print("  PixelString:", label)

# ============================ Part A: 5/6-channel ============================
if "whiteOffset >= 5" in s:
    print("  PixelString: 5/6-ch already present")
else:
    repl("    return whiteOffset == -1 ? 3 : 4;",
"""    if (whiteOffset == -1) {
        return 3;
    }
    if (whiteOffset >= 5) {
        return whiteOffset; // 5 or 6 channel (RGB + extra whites)
    }
    return 4;""", "channelsPerNode 5/6")

    repl("        } else if (colorOrder.length() == 1) {",
"""        } else if (colorOrder.length() == 5 || colorOrder.length() == 6) {
            // 5/6-channel: first 3 chars = RGB order, rest = extra white channels
            vs.whiteOffset = colorOrder.length();
            colorOrder = colorOrder.substr(0, 3);
        } else if (colorOrder.length() == 1) {""", "parse 5/6-char orders")

    repl("""            if (vs.whiteOffset == 3) {
                m_outputMap[offset++] = ch + 3;
            }
        }""",
"""            if (vs.whiteOffset == 3) {
                m_outputMap[offset++] = ch + 3;
            }
            if (vs.whiteOffset >= 5) {
                m_outputMap[offset++] = ch + 3;
                m_outputMap[offset++] = ch + 4;
                if (vs.whiteOffset == 6) {
                    m_outputMap[offset++] = ch + 5;
                }
            }
        }""", "SetupMap append 5/6")

    repl("""    int ch1 = 0;
    int ch2 = 0;
    int ch3 = 0;
    int ch4 = 0;
    int flipPixels = (offset2 - offset1 + chanCount) / chanCount / 2;

    for (int i = 0; i < flipPixels; i++) {
        ch1 = m_outputMap[offset1];
        ch2 = m_outputMap[offset1 + 1];
        ch3 = m_outputMap[offset1 + 2];
        if (chanCount == 4) {
            ch4 = m_outputMap[offset1 + 3];
        }

        m_outputMap[offset1] = m_outputMap[offset2];
        m_outputMap[offset1 + 1] = m_outputMap[offset2 + 1];
        m_outputMap[offset1 + 2] = m_outputMap[offset2 + 2];
        if (chanCount == 4) {
            m_outputMap[offset1 + 3] = m_outputMap[offset2 + 3];
        }

        m_outputMap[offset2] = ch1;
        m_outputMap[offset2 + 1] = ch2;
        m_outputMap[offset2 + 2] = ch3;
        if (chanCount == 4) {
            m_outputMap[offset2 + 3] = ch4;
        }

        offset1 += chanCount;
        offset2 -= chanCount;
    }""",
"""    int flipPixels = (offset2 - offset1 + chanCount) / chanCount / 2;

    for (int i = 0; i < flipPixels; i++) {
        for (int c = 0; c < chanCount; c++) {
            int tmp = m_outputMap[offset1 + c];
            m_outputMap[offset1 + c] = m_outputMap[offset2 + c];
            m_outputMap[offset2 + c] = tmp;
        }
        offset1 += chanCount;
        offset2 -= chanCount;
    }""", "FlipPixels generalize")

# ==================== Part B: 16-bit x N-channel ============================
# whiteOffset 100+N (N source channels -> N*2 wire bytes). N=3 RGB, 4 RGBW, 5 RGBWW.
if "whiteOffset >= 100" in s:
    print("  PixelString: 16-bit already present")
else:
    # channelsPerNode: 16-bit returns N*2 wire bytes (check before the 5/6 branch)
    repl("""    if (whiteOffset >= 5) {
        return whiteOffset; // 5 or 6 channel (RGB + extra whites)
    }""",
"""    if (whiteOffset >= 100) {
        return (whiteOffset - 100) * 2; // 16-bit: 2 wire bytes per source channel
    }
    if (whiteOffset >= 5) {
        return whiteOffset; // 5 or 6 channel (RGB + extra whites)
    }""", "channelsPerNode 16-bit")

    # parser: any color order ending in "16" -> 16-bit; prefix (3/4/5 chars) = layout.
    # Must precede the length==4 / 5/6 checks (e.g. "RGB16" is length 5).
    repl("        if (colorOrder.length() == 4) {",
"""        if (colorOrder.length() >= 5 && colorOrder.length() <= 8 && colorOrder.substr(colorOrder.length() - 2) == "16") {
            // 16-bit N-channel: "RGB16"(UCS8903) "RGBW16"(UCS8904) "RGBWC16"(SM16825)
            std::string b16 = colorOrder.substr(0, colorOrder.length() - 2);
            vs.whiteOffset = 100 + (int)b16.length(); // 103..106
            colorOrder = b16.substr(0, 3);
        } else if (colorOrder.length() == 4) {""", "parse 16-bit orders")

    # per-pixel source stride = N for 16-bit (output is N*2 bytes, source is N channels)
    repl("ch = vs.startChannel + (group * vs.channelsPerNode());",
         "ch = vs.startChannel + (group * (vs.whiteOffset >= 100 ? vs.whiteOffset - 100 : vs.channelsPerNode()));",
         "16-bit group stride")
    repl("ch = vs.startChannel + (p * vs.channelsPerNode());",
         "ch = vs.startChannel + (p * (vs.whiteOffset >= 100 ? vs.whiteOffset - 100 : vs.channelsPerNode()));",
         "16-bit pixel stride")

    # SetupMap: emit N channels, each doubled (high,low both = value -> value*257 MSB-first)
    repl("""            if (vs.whiteOffset == 0) {
                m_outputMap[offset++] = ch;
                ch1++;
                ch2++;
                ch3++;
            }
            m_outputMap[offset++] = ch1;
            m_outputMap[offset++] = ch2;
            m_outputMap[offset++] = ch3;
            if (vs.whiteOffset == 3) {
                m_outputMap[offset++] = ch + 3;
            }
            if (vs.whiteOffset >= 5) {
                m_outputMap[offset++] = ch + 3;
                m_outputMap[offset++] = ch + 4;
                if (vs.whiteOffset == 6) {
                    m_outputMap[offset++] = ch + 5;
                }
            }""",
"""            if (vs.whiteOffset >= 100) {
                // 16-bit: each of N channels -> 2 bytes (high,low both = value)
                int b16 = vs.whiteOffset - 100;
                m_outputMap[offset++] = ch1;
                m_outputMap[offset++] = ch1;
                m_outputMap[offset++] = ch2;
                m_outputMap[offset++] = ch2;
                m_outputMap[offset++] = ch3;
                m_outputMap[offset++] = ch3;
                if (b16 >= 4) {
                    m_outputMap[offset++] = ch + 3;
                    m_outputMap[offset++] = ch + 3;
                }
                if (b16 >= 5) {
                    m_outputMap[offset++] = ch + 4;
                    m_outputMap[offset++] = ch + 4;
                }
                if (b16 >= 6) {
                    m_outputMap[offset++] = ch + 5;
                    m_outputMap[offset++] = ch + 5;
                }
            } else {
                if (vs.whiteOffset == 0) {
                    m_outputMap[offset++] = ch;
                    ch1++;
                    ch2++;
                    ch3++;
                }
                m_outputMap[offset++] = ch1;
                m_outputMap[offset++] = ch2;
                m_outputMap[offset++] = ch3;
                if (vs.whiteOffset == 3) {
                    m_outputMap[offset++] = ch + 3;
                }
                if (vs.whiteOffset == 5 || vs.whiteOffset == 6) {
                    m_outputMap[offset++] = ch + 3;
                    m_outputMap[offset++] = ch + 4;
                    if (vs.whiteOffset == 6) {
                        m_outputMap[offset++] = ch + 5;
                    }
                }
            }""", "SetupMap 16-bit branch")

# ============= Part C: generalized literal-byte preamble/trailer ============
if "receiverNum == -3" in s:
    print("  PixelString: decoration-byte mechanism already present")
else:
    repl("""    leadInCount(0),
    toggleCount(0),
    leadOutCount(0)
{
}""",
"""    leadInCount(0),
    toggleCount(0),
    leadOutCount(0)
{
    // identity map so synthetic strings (null pixels, decoration bytes) emit
    // exact byte values instead of uninitialized garbage
    for (int x = 0; x < 256; x++) {
        brightnessMap[x] = x;
    }
}""", "default-ctor brightnessMap init (latent bug fix)")

    repl("""    m_portNumber = config["portNumber"].asInt();
    m_outputChannels = 0;

    int receiverType = 0;""",
"""    m_portNumber = config["portNumber"].asInt();
    m_outputChannels = 0;

    // Emits an arbitrary literal byte sequence as one synthetic VirtualString
    // per run of equal bytes. Each string's source channel is always the
    // constant always-zero FPPD_OFF_CHANNEL (see SetupMap); the literal value
    // comes from that string's OWN brightnessMap (every entry set to the same
    // byte), so distinct strings emit distinct constants without consuming
    // any sequence channels or touching FPP's global constant channels.
    // Applied further down (see "preamble application"), after any
    // smart-receiver lead-in -- defined here so both that and the SM16825E
    // trailer below can use it.
    auto addDecorationBytes = [this](const std::vector<uint8_t>& bytes) {
        size_t i = 0;
        while (i < bytes.size()) {
            size_t j = i;
            while (j < bytes.size() && bytes[j] == bytes[i]) {
                j++;
            }
            VirtualString vs;
            vs.receiverNum = -3; // decoration marker (see SetupMap)
            vs.colorOrder = kColorOrderONE;
            vs.pixelCount = (int)(j - i);
            vs.description = "decoration";
            for (int x = 0; x < 256; x++) {
                vs.brightnessMap[x] = bytes[i];
            }
            AddVirtualString(vs);
            i = j;
        }
    };

    int receiverType = 0;""", "Init decoration-byte lambda")

    repl("""    m_isSmartReceiver = receiverType > 0;
    if (receiverType == 1) {
        AddVirtualString(VirtualString(0));
    } else if (receiverType == 2) {
        //v2 smart receiver, no lead in
    }
    int startMaxChan = m_outputChannels;""",
"""    m_isSmartReceiver = receiverType > 0;
    if (receiverType == 1) {
        AddVirtualString(VirtualString(0));
    } else if (receiverType == 2) {
        //v2 smart receiver, no lead in
    }

    // Preamble application: deliberately placed AFTER any smart-receiver
    // lead-in/sync above (it configures the downstream pixel chip, not the
    // receiver) and BEFORE the real pixel data below.
    //
    // Per-port opt-out: set "noPreamble":true on this port's own JSON config
    // to skip even when the global Pixel Timing preset would otherwise apply
    // one. Useful for mixing chips across ports on the same BBB that share
    // compatible wire timing but not the same preamble need -- e.g. UCS7604
    // (preset 10, WS2812x-equivalent timing + a 15-byte preamble) on one
    // port and plain WS2812 (no preamble) on another: pixelTiming is global,
    // so both ports get "Normal"-equivalent timing either way, but only the
    // UCS7604 port should get the extra bytes.
    if (!config["noPreamble"].asBool()) {
        std::string preambleProfile = config["preambleProfile"].asString();
        if (preambleProfile == "tm1814") {
            // TM1814 leading 8-byte current-config frame: [c1,c2,c3,c4,~c1,~c2,~c3,~c4].
            // c=0x3F: 6-bit current code (mA*10-65)/5 at its 38 mA maximum, top two bits 0,
            // exactly what NeoPixelBus sends at max current -> 3F x4 then ~c = C0 x4.
            addDecorationBytes({ 0x3F, 0x3F, 0x3F, 0x3F, 0xC0, 0xC0, 0xC0, 0xC0 });
        } else if (preambleProfile == "tm1914") {
            // TM1914 6-byte mode-select frame (NeoPixelBus NeoTm1914Features.h):
            // FF FF F5 (mode byte) then its ones-complement 00 00 0A.
            addDecorationBytes({ 0xFF, 0xFF, 0xF5, 0x00, 0x00, 0x0A });
        } else if (preambleProfile == "ucs7604") {
            // UCS7604 15-byte config: 8-byte sync (FF x6, 00, 02) + 7-byte config
            // ([CFG][Rcur][Gcur][Bcur][Wcur][rsvd 00][rsvd 00]). CFG is picked by
            // scanning ALL virtual strings' raw color orders (not just the
            // first -- a leading 0-pixel placeholder or a differently-ordered
            // string must not silently pick the wrong bit depth, the same
            // reasoning as the SM16825E whiteOffset==105 scan below) for a
            // "...16" suffix: 16-bit/800k/RGBW if any is found, else 8-bit.
            uint8_t cfg = 0x03; // 8-bit, 800 kbps, RGBW
            for (int vi = 0; vi < (int)config["virtualStrings"].size(); vi++) {
                std::string coN = config["virtualStrings"][vi]["colorOrder"].asString();
                if (coN.length() >= 2 && coN.substr(coN.length() - 2) == "16") {
                    cfg = 0x8B; // 16-bit, 800 kbps, RGBW
                    break;
                }
            }
            uint8_t cur = 0x08; // 0x00-0x0F per channel; mid-range safe default
            addDecorationBytes({ 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0x00, 0x02,
                                  cfg, cur, cur, cur, cur, 0x00, 0x00 });
        }
    }

    int startMaxChan = m_outputChannels;""", "Init preamble application after smart-receiver lead-in")

    repl("""    if (!hasChannels[0]) {
        //empty, no strings
        m_outputChannels = 0;
        m_virtualStrings.clear();
        AddVirtualString(VirtualString());
    }

    m_outputMap.resize(m_outputChannels);""",
"""    if (!hasChannels[0]) {
        //empty, no strings
        m_outputChannels = 0;
        m_virtualStrings.clear();
        AddVirtualString(VirtualString());
    }

    // SM16825E mandatory 4-byte current-gain trailer, appended after every
    // real pixel string on this port (NeoPixelBus NeoSm168x5Features.h): 5x
    // 5-bit gains packed MSB-first, then 2 action bits (00=active, not
    // standby) + 5 reserved bits (all 1). Auto-detected from whiteOffset==105
    // (RGBWC16/GRBWC16) rather than a preambleProfile flag, since that color
    // order is unique to this chip -- no separate UI selection needed.
    //
    // SAFETY: this trailer is sent every frame and OVERRIDES whatever
    // current the chip/module powered up with -- there is no opt-out short
    // of not using RGBWC16/GRBWC16. g is 0-31 mapping to ~10-310mA PER
    // CHANNEL (5 channels): g=5 below is a deliberately conservative
    // ~58mA/channel (~290mA/pixel total), not the mid-scale ~155mA a naive
    // "middle of the range" pick would give. If your modules are rated
    // higher, raise g here and rebuild -- there is no UI field for this yet
    // (same limitation as TM1814's fixed-max current, see CONFIG.md).
    bool sawSm16825e = false;
    for (auto& vsScan : m_virtualStrings) {
        if (vsScan.whiteOffset == 105) {
            sawSm16825e = true;
            break;
        }
    }
    if (sawSm16825e) {
        uint8_t g = 5; // 0-31; conservative default, see SAFETY note above
        uint8_t b0 = (uint8_t)((g << 3) | (g >> 2));
        uint8_t b1 = (uint8_t)((g << 6) | (g << 1) | (g >> 4));
        uint8_t b2 = (uint8_t)((g << 4) | (g >> 1));
        uint8_t b3 = (uint8_t)((g << 7) | 0x1F);
        addDecorationBytes({ b0, b1, b2, b3 });
    }

    m_outputMap.resize(m_outputChannels);""", "SM16825E trailer at end of Init")

    repl("""void PixelString::SetupMap(int vsOffset, const VirtualString& vs) {
    if (vs.receiverNum >= 0) {""",
"""void PixelString::SetupMap(int vsOffset, const VirtualString& vs) {
    if (vs.receiverNum == -3) {
        // Decoration string: every "pixel" is one literal byte, sourced from
        // the constant always-zero FPPD_OFF_CHANNEL and remapped through this
        // string's own brightnessMap (see the addDecorationBytes lambda).
        for (int x = 0; x < vs.pixelCount; x++) {
            m_outputMap[vsOffset++] = FPPD_OFF_CHANNEL;
        }
        return;
    }
    if (vs.receiverNum >= 0) {""", "SetupMap decoration-byte branch")

    # Keep decoration/smart-receiver synthetic strings out of Pixel Overlay
    # auto-create (they'd otherwise show up as a phantom "decoration" model
    # sourced from FPPD_OFF_CHANNEL). receiverNum == -1 is a real string.
    repl("""            for (int vs = 0; vs < strings[s]->m_virtualStrings.size(); vs++) {
                std::string desc = strings[s]->m_virtualStrings[vs].description;""",
"""            for (int vs = 0; vs < strings[s]->m_virtualStrings.size(); vs++) {
                if (strings[s]->m_virtualStrings[vs].receiverNum != -1) {
                    continue; // smart-receiver or decoration string, not a real model
                }
                std::string desc = strings[s]->m_virtualStrings[vs].description;""",
         "AutoCreateOverlayModels skip synthetic strings")

# Upgrade: a file patched by an earlier version carries the old FF x4 / 00 x4 TM1814 preamble.
if OLDC in s:
    s = s.replace(OLDC, NEWC); changed = True
    print("  PixelString: TM1814 preamble upgraded to 3F x4 / C0 x4")

# ============== Part D: user-settable chip current + TM1914 mode ================
# Config keys (set on the pixel-strings page, copied onto every string by patch_bbb48string.py):
#   chipCurrent  0-100  % of the chip's own current range. Unset keeps each chip's previous fixed default.
#                  TM1814: 6.5-38 mA, code (mA*10-65)/5   UCS7604: 4-bit per channel   SM16825E: 5-bit gain, 10.2-310 mA
#   tm1914Mode   "din" (default) | "fdin" | "auto"   -> mode byte F5 | FA | FF  (NeoPixelBus NeoTm1914_Mode)
D_ITEMS = [
 ("chipCurrent", """            addDecorationBytes({ 0x3F, 0x3F, 0x3F, 0x3F, 0xC0, 0xC0, 0xC0, 0xC0 });""",
"""            // chipCurrent = % of the chip's 6.5-38 mA range (unset = maximum, as before); code = (mA*10 - 65) / 5, 0..63
            int pct = config.isMember("chipCurrent") ? config["chipCurrent"].asInt() : 100;
            if (pct < 0) pct = 0;
            if (pct > 100) pct = 100;
            uint8_t c = (uint8_t)(((pct * 315 + 50) / 100) / 5);
            addDecorationBytes({ c, c, c, c, (uint8_t)~c, (uint8_t)~c, (uint8_t)~c, (uint8_t)~c });""", "TM1814 current"),
 ("tm1914Mode", """            addDecorationBytes({ 0xFF, 0xFF, 0xF5, 0x00, 0x00, 0x0A });""",
"""            // mode byte: F5 = DIN only (default), FA = FDIN only, FF = auto-switch (backup-signal wiring)
            std::string m1914 = config["tm1914Mode"].asString();
            uint8_t mode = (m1914 == "auto") ? 0xFF : (m1914 == "fdin") ? 0xFA : 0xF5;
            addDecorationBytes({ 0xFF, 0xFF, mode, 0x00, 0x00, (uint8_t)~mode });""", "TM1914 mode"),
 ("UCS7604 current", """            uint8_t cur = 0x08; // 0x00-0x0F per channel; mid-range safe default""",
"""            // chipCurrent = % of the 4-bit per-channel range (unset = 0x08, mid-range as before); the lowest step is 1
            uint8_t cur = 0x08;
            if (config.isMember("chipCurrent")) {
                int pct = config["chipCurrent"].asInt();
                if (pct < 0) pct = 0;
                if (pct > 100) pct = 100;
                cur = (uint8_t)((pct * 15 + 50) / 100);
                if (cur < 1) cur = 1;
            }""", "UCS7604 current"),
 ("SM16825E gain", """        uint8_t g = 5; // 0-31; conservative default, see SAFETY note above""",
"""        uint8_t g = 5; // 0-31; conservative default (60.7 mA/channel), see SAFETY note above
        if (config.isMember("chipCurrent")) {
            // chipCurrent = % of the 10.2-310 mA range: pick the gain whose current is nearest (NeoPixelBus table, tenths of mA)
            static const int tab[32] = { 102, 203, 304, 405, 506, 607, 708, 809, 910, 1011, 1112, 1213, 1307, 1406, 1505, 1602,
                                         1700, 1790, 1885, 1980, 2078, 2168, 2264, 2358, 2450, 2544, 2636, 2728, 2820, 2910, 3000, 3100 };
            int pct = config["chipCurrent"].asInt();
            if (pct < 0) pct = 0;
            if (pct > 100) pct = 100;
            int target = 102 + (pct * (3100 - 102) + 50) / 100;
            int best = 0;
            for (int i = 1; i < 32; i++) {
                int di = tab[i] > target ? tab[i] - target : target - tab[i];
                int db = tab[best] > target ? tab[best] - target : target - tab[best];
                if (di < db) best = i;
            }
            g = (uint8_t)best;
        }""", "SM16825E gain"),
]
for marker, old, new, label in D_ITEMS:
    if new in s:
        print("  PixelString: %s control already present" % label)
    else:
        repl(old, new, label + " control")

# ============== Part E: TM1908 preamble (pixelTiming 16) ======================================================
# Datasheet (Titan Micro TM1908 V1.2): every frame starts with C1 = FF FF FF, C2 = 00 00 00 (normal mode: DIN/FDIN auto-switch;
# C2 is the complement of C1), then C3 = three current bytes (R, G, B), each 0 + 7-bit code (0x00 = 2 mA ... 0x7F = 25 mA).
if 'preambleProfile == "tm1908"' in s:
    print("  PixelString: TM1908 preamble already present")
else:
    repl("""        } else if (preambleProfile == "ucs7604") {""",
"""        } else if (preambleProfile == "tm1908") {
            // TM1908 9-byte frame header: C1 = FF FF FF, C2 = 00 00 00 (auto-switch mode), C3 = per-channel current (0x7F = 25 mA, default)
            uint8_t cur = 0x7F;
            if (config.isMember("chipCurrent")) {
                int pct = config["chipCurrent"].asInt();
                if (pct < 0) pct = 0;
                if (pct > 100) pct = 100;
                cur = (uint8_t)((pct * 127 + 50) / 100);
            }
            addDecorationBytes({ 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0x00, cur, cur, cur });
        } else if (preambleProfile == "ucs7604") {""", "TM1908 preamble")

if changed:
    open(P, "w").write(s)
print("  PixelString: done")
