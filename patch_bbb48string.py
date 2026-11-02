#!/usr/bin/env python3
# [fpp-bbb-pixels] Patch BBB48String.cpp. Three independent, idempotent parts:
#   A  map pixelTiming 2-10 -> -DPIXELTYPE_* compile flags for the PRU program
#      (7=TM1829 8=WS2805 9=TM1914 10=UCS7604, the last two sharing existing
#      timing; 10 pushes no flag at all -- WS2812x-equivalent, same as 0/Normal)
#   B  pixelTiming 6/9/10 -> set config["preambleProfile"] on each string's
#      config so PixelString prepends the matching native preamble
#      (6=tm1814 9=tm1914 10=ucs7604). The SM16825E trailer needs no flag here
#      -- PixelString auto-detects it from the RGBWC16 color order instead.
#   C  prepData hot-path: hoist the brightness-LUT pointer per virtual string
#      (stock 5.x re-reads the m_brightnessMaps[] pointer table for EVERY output
#      byte; this removes one memory access per byte across all ports)
#   D  prepData prefetching gather (prepdata_prefetch.inc): same bytes, ~1.5x faster on the Cortex-A8 (DDR-latency bound);
#      replaces the stock or hoisted loop, and also upgrades the interim tiled version
#   F  per-port limit check at start-up against the planned frame rate (config key targetFps, saved by the UI)
#   E  frame-budget report at start-up: how long the longest port takes on the wire and the highest frame rate
#      the configuration can sustain (a faster sequence silently cuts the end of the longest strings off)
# Rebuild libfpp-co-BBB48String.so after. FPP 5.x anchors; aborts on mismatch.
import os, re, sys
P = sys.argv[1] if len(sys.argv) > 1 else "/opt/fpp/src/channeloutput/BBB48String.cpp"
s = open(P).read()
changed = False

def repl(old, new, label):
    global s, changed
    n = s.count(old)
    assert n == 1, "  BBB48String ERROR: [%s] matched %d (expected 1)" % (label, n)
    s = s.replace(old, new); changed = True
    print("  BBB48String:", label)

# ---- A: timing flag map ----------------------------------------------------
if "PIXELTYPE_TM1814" in s:
    print("  BBB48String: timing cases already present")
else:
    repl('        if (pixelTiming) {\n'
         '            args.push_back("-DPIXELTYPE_SLOW");',
         '        switch (pixelTiming) {\n'
         '            case 1: args.push_back("-DPIXELTYPE_SLOW"); break;\n'
         '            case 2: args.push_back("-DPIXELTYPE_APA104"); break;\n'
         '            case 3: args.push_back("-DPIXELTYPE_WS2811_400"); break;\n'
         '            case 4: args.push_back("-DPIXELTYPE_UCS1903_400"); break;\n'
         '            case 5: args.push_back("-DPIXELTYPE_TM1803"); break;\n'
         '            case 6: args.push_back("-DPIXELTYPE_TM1814"); break;\n'
         '            case 7: args.push_back("-DPIXELTYPE_TM1829"); break;\n'
         '            case 8: args.push_back("-DPIXELTYPE_WS2805"); break;\n'
         '            case 9: args.push_back("-DPIXELTYPE_TM1914"); break;\n'
         '            case 10: break; // UCS7604: WS2812x-equivalent, no flag needed',
         "pixelTiming cases 2-10")

# ---- B: preamble profile flag ------------------------------------------------
if 's["preambleProfile"]' in s:
    print("  BBB48String: preambleProfile flag inject already present")
else:
    repl('        Json::Value s = config["outputs"][i];\n'
         '        PixelString* newString = new PixelString(true);',
         '        Json::Value s = config["outputs"][i];\n'
         '        switch (config["pixelTiming"].asInt()) {\n'
         '            case 6: s["preambleProfile"] = "tm1814"; break;\n'
         '            case 9: s["preambleProfile"] = "tm1914"; break;\n'
         '            case 10: s["preambleProfile"] = "ucs7604"; break;\n'
         '            default: break;\n'
         '        }\n'
         '        PixelString* newString = new PixelString(true);',
         "preambleProfile flag inject")

# ---- C: prepData LUT-pointer hoist ------------------------------------------
if "Walk per virtual string" in s or "Prefetching gather" in s or "Tiled transpose" in s:
    print("  BBB48String: prepData optimization already present")
else:
    repl("""            inCh = 0;

            for (int p = 0; p < ps->m_outputChannels; p++) {
                uint8_t* brightness = ps->m_brightnessMaps[p];
                *c = brightness[channelData[ps->m_outputMap[inCh++]]];
                c += numStrings;
            }""",
"""            inCh = 0;

            // Walk per virtual string so the brightness LUT pointer loads once
            // per string instead of once per output byte.
            for (auto& vs : ps->m_virtualStrings) {
                const uint8_t* brightness = vs.brightnessMap;
                int vsChans = (vs.startNulls + vs.pixelCount + vs.endNulls) * vs.channelsPerNode();
                for (int k = 0; k < vsChans; k++) {
                    *c = brightness[channelData[ps->m_outputMap[inCh++]]];
                    c += numStrings;
                }
            }""", "prepData LUT hoist")

# ---- D: tiled prepData ---------------------------------------------------------
if "Prefetching gather" in s:
    print("  BBB48String: prefetching prepData already present")
else:
    inc = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "prepdata_prefetch.inc")).read()
    head = "void BBB48StringOutput::prepData(FrameData& d, unsigned char* channelData) {"
    a = s.find(head)
    assert a >= 0 and s.count(head) == 1, "  BBB48String ERROR: [tiled prepData] function head not found"
    b = s.find("\n}\n", a)
    assert b > a, "  BBB48String ERROR: [tiled prepData] function end not found"
    s = s[:a] + inc.rstrip("\n") + s[b + 2:]; changed = True
    print("  BBB48String: prepData prefetching gather")

# ---- E: frame-budget report ------------------------------------------------------
if "frame budget" in s:
    print("  BBB48String: frame-budget report already present")
else:
    repl("    // give each area two chunks (frame flipping) of DDR memory\n",
"""    {   // [fpp-bbb-pixels] frame budget: wire time of the longest port vs. the frame rates FPP will ask for.
        // bit period = programmed LOW_TIME + ~110ns PRU overhead, measured per preset on a BeagleBone Green.
        static const int bitNs[11] = { 1260, 1331, 1726, 2518, 2518, 2074, 1258, 1256, 1102, 1256, 1260 };
        int pt = config.isMember("pixelTiming") ? config["pixelTiming"].asInt() : 0;
        if (pt < 0 || pt > 10) pt = 0;
        int longest = std::max(m_gpioData.maxStringLen, m_gpio0Data.maxStringLen);
        double ms = longest * 8.0 * bitNs[pt] / 1000000.0;
        double maxFps = 1000.0 / (ms + 0.5);
        LogInfo(VB_CHANNELOUT, "BBB48String frame budget: longest port = %d bytes -> %.1f ms on the wire, sustains up to ~%.0f fps. "
                               "A sequence faster than that cuts off the end of the longest strings.\\n", longest, ms, maxFps);
        if (maxFps < 20.0) {
            LogWarn(VB_CHANNELOUT, "BBB48String frame budget: this configuration cannot sustain even 20 fps (needs %.1f ms per frame) -- "
                                   "shorten the longest port, or use a 10 fps sequence.\\n", ms);
        }
    }
    // give each area two chunks (frame flipping) of DDR memory
""", "frame-budget report")

# ---- F: per-port limit check against the planned frame rate -----------------------
if "per-port limit check" in s:
    print("  BBB48String: per-port limit check already present")
else:
    repl("    // give each area two chunks (frame flipping) of DDR memory\n",
"""    {   // [fpp-bbb-pixels] per-port limit check against the frame rate the user planned for (the UI saves it as "targetFps")
        static const int bitNs2[11] = { 1260, 1331, 1726, 2518, 2518, 2074, 1258, 1256, 1102, 1256, 1260 };
        static const int resetUs2[11] = { 300, 300, 50, 50, 50, 50, 200, 200, 300, 200, 300 };
        int pt2 = config.isMember("pixelTiming") ? config["pixelTiming"].asInt() : 0;
        if (pt2 < 0 || pt2 > 10) pt2 = 0;
        int tfps = config.isMember("targetFps") ? config["targetFps"].asInt() : 20;
        if (tfps < 1) tfps = 20;
        double availMs = (1000 / tfps) - (resetUs2[pt2] + 200) / 1000.0;
        int tooLong = 0;
        for (size_t x = 0; x < m_strings.size(); x++) {
            int bytes = m_strings[x]->m_outputChannels;
            if (bytes <= 0) continue;
            double ms = bytes * 8.0 * bitNs2[pt2] / 1000000.0;
            if (ms > availMs) {
                tooLong++;
                LogWarn(VB_CHANNELOUT, "BBB48String LIMIT: port %d sends %d bytes = %.1f ms, but %d fps leaves only %.1f ms. "
                                       "Only the first %d%% of that port will update. Shorten it or plan for a lower frame rate.\\n",
                        (int)x + 1, bytes, ms, tfps, availMs, (int)(100.0 * availMs / ms));
            }
        }
        if (!tooLong) {
            LogInfo(VB_CHANNELOUT, "BBB48String limit check: every port fits at %d fps (%.1f ms available per frame).\\n", tfps, availMs);
        }
    }
    // give each area two chunks (frame flipping) of DDR memory
""", "per-port limit check")

# ---- G: pass chipCurrent / tm1914Mode from the output config down to every string --------------
if 's["chipCurrent"]' in s:
    print("  BBB48String: chipCurrent/tm1914Mode pass-through already present")
else:
    repl("        PixelString* newString = new PixelString(true);",
"""        if (config.isMember("chipCurrent")) {
            s["chipCurrent"] = config["chipCurrent"];
        }
        if (config.isMember("tm1914Mode")) {
            s["tm1914Mode"] = config["tm1914Mode"];
        }
        PixelString* newString = new PixelString(true);""", "chipCurrent/tm1914Mode pass-through")

# ---- H: "Custom" timing (11) + datasheet presets 12-18, all driven by the same PRU defines -------------------------------------
#      pixelTiming 11 = user-entered T0H / T1H / bit period (ns, as printed in the chip's datasheet) + invert flag;
#      12 = TM1903/TM1824/TM1934   13 = UCS2912   14 = UCS1912   15 = TX1812/TX1818/LC8816E/GS8208B (0.3/0.9 us)
#      16 = TM1908   17 = LPD1886 (8-bit)   18 = LC8812/LC8812B.
#      Datasheet times are converted to PRU defines with the same compensation the presets use (high times ~50 ns, bit period ~110 ns
#      of overhead); waits above the 8-bit immediate (1275 ns) need the register form, so -DSLOW_WAITNS is added when needed.
#      All values are clamped; a non-number in the JSON falls back to the default (a bad config must never abort fppd).
HELPERS = r"""
// [fpp-bbb-pixels] read an integer config value; anything that is not a number falls back to the default
static int fbpCfgInt(const Json::Value& c, const char* k, int d) { return (c.isMember(k) && c[k].isNumeric()) ? c[k].asInt() : d; }
// [fpp-bbb-pixels] timing for pixelTiming 11 (Custom, from the config) and 12-18 (datasheet presets). Returns false for 0-10.
// Outputs the PRU defines (already compensated for the PRU overhead), the invert flag and whether the long-wait form is needed.
static bool fbpCustomDefines(int pt, const Json::Value& c, int& T0, int& T1, int& LOW, int& inv) {
    static const int tab[7][4] = {  // wire T0H, T1H, bit period (ns, datasheet), inverted
        { 360,  720, 1300, 0 },     // 12 TM1903 / TM1824 / TM1934 (datasheet: period at least 1.25 us)
        { 400,  800, 1250, 0 },     // 13 UCS2912
        { 250, 1000, 1250, 0 },     // 14 UCS1912
        { 300,  900, 1250, 0 },     // 15 TX1812 / TX1818 / LC8816E / GS8208B
        { 240,  480, 1250, 0 },     // 16 TM1908
        { 200,  600, 1250, 0 },     // 17 LPD1886 (8-bit mode)
        { 300,  750, 1250, 0 } };   // 18 LC8812 / LC8812B (T1H inside both datasheet variants)
    int t0h, t1h, per;
    if (pt == 11) {
        t0h = fbpCfgInt(c, "customT0", 350); t1h = fbpCfgInt(c, "customT1", 700);
        per = fbpCfgInt(c, "customPeriod", 1250); inv = fbpCfgInt(c, "customInvert", 0) ? 1 : 0;
    } else if (pt >= 12 && pt <= 18) {
        t0h = tab[pt - 12][0]; t1h = tab[pt - 12][1]; per = tab[pt - 12][2]; inv = tab[pt - 12][3];
    } else {
        return false;
    }
    T0 = std::min(std::max(t0h - 50, 200), 3000);
    T1 = std::min(std::max(t1h - 50, T0 + 50), 3500);
    LOW = std::min(std::max(per - 110, T1 + 100), 4000);
    return true;
}
"""
CASE = r"""            case 11: case 12: case 13: case 14: case 15: case 16: case 17: case 18: { // Custom / datasheet presets
                int T0, T1, LOW, inv;
                fbpCustomDefines(pixelTiming, config, T0, T1, LOW, inv);
                args.push_back("-DPIXELTYPE_CUSTOM");
                args.push_back("-DCUSTOM_T0=" + std::to_string(T0));
                args.push_back("-DCUSTOM_T1=" + std::to_string(T1));
                args.push_back("-DCUSTOM_LOW=" + std::to_string(LOW));
                if (T1 > 1250 || LOW > 1250) args.push_back("-DSLOW_WAITNS");
                if (inv) args.push_back("-DCUSTOM_INVERT");
                break;
            }"""
if "fbpCustomDefines" in s:
    old12 = "{ 360,  720, 1250, 0 },     // 12 TM1903 / TM1824 / TM1934"
    if old12 in s:     # upgrade: preset 12 period 1250 -> 1300 (the datasheet minimum is 1.25 us; 1250 measured 1242)
        s = s.replace(old12, "{ 360,  720, 1300, 0 },     // 12 TM1903 / TM1824 / TM1934 (datasheet: period at least 1.25 us)"); changed = True
        print("  BBB48String: TM1903 preset period raised to 1300 ns")
    print("  BBB48String: custom/datasheet timing (11-18) already present")
else:
    # 1) helpers after the last #include
    inc = [m for m in re.finditer(r'^#include [^\n]*\n', s, re.M)]
    assert inc, "  BBB48String ERROR: [custom timing] no #include anchor"
    if "fbpCfgInt" in s:     # v1 left a one-line helper behind: drop it, HELPERS has it
        s = re.sub(r'\n// \[fpp-bbb-pixels\] read an integer config value[^\n]*\nstatic int fbpCfgInt[^\n]*\n', '\n', s)
        inc = [m for m in re.finditer(r'^#include [^\n]*\n', s, re.M)]
    s = s[:inc[-1].end()] + HELPERS + s[inc[-1].end():]
    # 2) the switch case: a fresh file gets it after case 10; a v1 file has the old case 11 block to replace
    m = re.search(r'            case 11: \{ // Custom:.*?\n                break;\n            \}', s, re.S)
    if m:
        s = s[:m.start()] + CASE.lstrip() .join(["            ", ""]) + s[m.end():]
    else:
        repl('            case 10: break; // UCS7604: WS2812x-equivalent, no flag needed',
             '            case 10: break; // UCS7604: WS2812x-equivalent, no flag needed\n' + CASE, "custom timing flags (pixelTiming 11-18)")
    # 3) frame budget + limit check use the custom period; the preset tables stay at 11 entries and are never indexed above 10
    if "int bitV =" not in s:      # fresh file: the budget blocks still read the tables directly
        s = s.replace('        if (pt < 0 || pt > 10) pt = 0;\n', '        if (pt < 0 || pt > 10) pt = 0;\n        int bitV = 0;\n', 1)
        assert "int bitV = 0;" in s, "  BBB48String ERROR: [custom timing] budget anchor not found"
        s = s.replace('double ms = longest * 8.0 * bitNs[pt] / 1000000.0;', 'double ms = longest * 8.0 * bitV / 1000000.0;', 1)
        s = s.replace('        int bitV = 0;\n', '        int bitV;\n', 1)
        s = s.replace('        int longest', '        int cT0, cT1, cLOW, cInv;\n        bitV = fbpCustomDefines(pt, config, cT0, cT1, cLOW, cInv) ? cLOW + 110 : bitNs[pt];\n        int longest', 1)
    if "int bitV2 =" not in s and "int bitV2;" not in s:
        s = s.replace('        if (pt2 < 0 || pt2 > 10) pt2 = 0;\n', '        if (pt2 < 0 || pt2 > 10) pt2 = 0;\n        int cT02, cT12, cLOW2, cInv2;\n        int bitV2 = fbpCustomDefines(pt2, config, cT02, cT12, cLOW2, cInv2) ? cLOW2 + 110 : bitNs2[pt2];\n', 1)
        s = s.replace('double ms = bytes * 8.0 * bitNs2[pt2] / 1000000.0;', 'double ms = bytes * 8.0 * bitV2 / 1000000.0;', 1)
    n = 0
    s, k = re.subn(r'if \(pt < 0 \|\| pt > 1[01]\) pt = 0;', 'if (pt < 0 || pt > 18) pt = 0;', s); n += k
    s, k = re.subn(r'if \(pt2 < 0 \|\| pt2 > 1[01]\) pt2 = 0;', 'if (pt2 < 0 || pt2 > 18) pt2 = 0;', s); n += k
    s, k = re.subn(r'\n        int bitV = [^\n]*;', '\n        int cT0, cT1, cLOW, cInv;\n        int bitV = fbpCustomDefines(pt, config, cT0, cT1, cLOW, cInv) ? cLOW + 110 : bitNs[pt];', s); n += k
    s, k = re.subn(r'\n        int bitV2 = [^\n]*;', '\n        int cT02, cT12, cLOW2, cInv2;\n        int bitV2 = fbpCustomDefines(pt2, config, cT02, cT12, cLOW2, cInv2) ? cLOW2 + 110 : bitNs2[pt2];', s); n += k
    s, k = re.subn(r'bitNs\[1[12]\]', 'bitNs[11]', s); n += k
    s, k = re.subn(r'bitNs2\[1[12]\]', 'bitNs2[11]', s); n += k
    s, k = re.subn(r'resetUs2\[1[12]\]', 'resetUs2[11]', s); n += k
    s = re.sub(r'(static const int (?:bitNs|bitNs2|resetUs2)\[11\] = \{[^}]*?),\s*[0-9]+\s*\};', r'\1 };', s) if re.search(r'(static const int (?:bitNs|bitNs2|resetUs2)\[11\] = \{(?:[^,}]*,){11}[^,}]*\};)', s) else s
    s = s.replace('(resetUs2[pt2] + 200)', '((pt2 <= 10 ? resetUs2[pt2] : 300) + 200)')
    assert "fbpCustomDefines(pt, config" in s and "fbpCustomDefines(pt2, config" in s, "  BBB48String ERROR: [custom timing] budget hooks not applied"
    changed = True
    print("  BBB48String: custom/datasheet timing (11-18) added (%d table/budget edits)" % n)

# ---- I: pixelTiming 16 (TM1908) selects the tm1908 preamble profile -----------------------------------------------------
if 'case 16: s["preambleProfile"]' in s:
    print("  BBB48String: TM1908 preamble flag already present")
else:
    repl('            case 10: s["preambleProfile"] = "ucs7604"; break;\n',
         '            case 10: s["preambleProfile"] = "ucs7604"; break;\n            case 16: s["preambleProfile"] = "tm1908"; break;\n', "TM1908 preamble flag")

if changed:
    open(P, "w").write(s)
print("  BBB48String: done")
