#!/usr/bin/env python3
# [fpp-bbb-pixels] Patch co-pixelStrings.php (BBB): Pixel Timing dropdown (0-10)
# + chip color orders (5/6-ch WS2805/FW1906, 16-bit UCS8903/8904/SM16825E).
# TM1829/WS2805/TM1914/UCS7604 (7-10) reuse existing color orders (plain
# RGB/GRB or RGBW/RGBW16) -- no new order strings needed. Idempotent.
# Core www file - overwritten on FPP upgrade, so re-run after upgrading.
import os, sys, re

def _atomic_write(path, data):
    """write to a temp file, then rename over the target: a crash (this board has random ones) can never leave a half-written FPP file"""
    import os as _os
    tmp = path + ".fbp-tmp"
    try:
        st = _os.stat(path)
    except OSError:
        st = None
    with open(tmp, "w") as f:
        f.write(data); f.flush(); _os.fsync(f.fileno())
    if st is not None:
        _os.chmod(tmp, st.st_mode & 0o7777)
        try:
            _os.chown(tmp, st.st_uid, st.st_gid)
        except OSError:
            pass
    _os.replace(tmp, path)

P = sys.argv[1] if len(sys.argv) > 1 else "/opt/fpp/www/co-pixelStrings.php"
s = open(P).read()
IND = "                        "  # option-line indentation

# 1) Pixel Timing dropdown -> 11 datasheet-labelled presets
if 'value="10">UCS7604' in s:
    print("  ui timings: already patched")
else:
    m0 = re.search(r'<option value="0">[^<]*</option>', s)
    m1 = re.search(r'<option value="1">[^<]*</option>', s)
    if not (m0 and m1):
        sys.exit("  ui ERROR: timing option anchors not found")
    block = ('<option value="0">Normal - WS2811(800Kbps)/WS2812/WS2813/WS2815/SK6812/GS8208/GS8608/most WS281x</option>\n'
             + IND + '<option value="1">Slow - ws281x variant (longer high time, 800Kbps)</option>\n'
             + IND + '<option value="2">APA104 / APA106 / PL9823 / SK6822</option>\n'
             + IND + '<option value="3">WS2811 400Kbps</option>\n'
             + IND + '<option value="4">UCS1903 400Kbps</option>\n'
             + IND + '<option value="5">TM1803</option>\n'
             + IND + '<option value="6">TM1814 (RGBW, inverted)</option>\n'
             + IND + '<option value="7">TM1829 (RGB, inverted)</option>\n'
             + IND + '<option value="8">WS2805 (RGBWWCW, 5ch)</option>\n'
             + IND + '<option value="9">TM1914 (RGB, inverted)</option>\n'
             + IND + '<option value="10">UCS7604 (RGBW, 8/16-bit)</option>')
    s = s[:m0.start()] + block + s[m1.end():]
    print("  ui timings: patched (0-10)")

# 1a) options 11-18: Custom timing + datasheet presets (inserted after the last existing option; idempotent)
NEWOPT = {
    11: "Custom timing (type the pulse times from the datasheet)",
    12: "TM1903 / TM1824 (RGBW) / TM1934 (RGB, 800 kHz)",
    13: "UCS2912 (RGB, 12-channel driver)",
    14: "UCS1912 (RGB, 12-channel driver)",
    15: "TX1812 / TX1818 / LC8816E (RGBW) / GS8208B / SM16824E (0.3 / 0.9 us pulses)",
    16: "TM1908 (RGB, current-set frame)",
    17: "LPD1886 (8-bit mode)",
    18: "LC8812 / LC8812B (RGB)",
}
for n, text in NEWOPT.items():
    if '<option value="%d"' % n in s:
        continue
    m = re.search(r'<option value="%d">[^<]*</option>' % (n - 1), s)
    if m:
        s = s[:m.end()] + '\n' + IND + '<option value="%d">%s</option>' % (n, text) + s[m.end():]
        print("  ui option %d: added" % n)
    else:
        print("  ui option %d: WARN option %d not found - skipped" % (n, n - 1))

# 1b) menu labels: name the extra chips each timing covers (idempotent: only rewrites a label that differs)
LABELS = {
    0: "Normal - WS2811/WS2812/WS2813/WS2815/WS2818, SK6812, GS8208, GS8608, SM16703, SK6813, CS8812, HC2912C, WS2813B-RGBW, UCS1903B/UCS2904, WS2816 (16-bit) and most 800 kHz chips",
    1: "Slow - ws281x variant (longer high time, 800 kHz)",
    2: "APA104 / APA106 / PL9823 / SK6822",
    3: "WS2811 400 kHz",
    4: "UCS1903 / UCS2903 400 kHz",
    5: "TM1803",
    6: "TM1814 (RGBW, inverted)",
    7: "TM1829 (RGB, inverted)",
    8: "WS2805 (RGB + warm + cool white, 5 channels)",
    9: "TM1914 (RGB, inverted)",
    10: "UCS7604 (RGBW, 8/16-bit)",
}
LABELS.update(NEWOPT)
_a = s.find("id='BBB48StringPixelTiming'>")
_b = s.find("</select>", _a) if _a >= 0 else -1
if _a >= 0 and _b > _a:
    seg, changed_labels = s[_a:_b], 0
    for n, text in LABELS.items():
        pat = re.compile(r'(<option value="%d">)[^<]*(</option>)' % n)
        m = pat.search(seg)
        if m and m.group(0) != '<option value="%d">%s</option>' % (n, text):
            seg = seg[:m.start()] + '<option value="%d">%s</option>' % (n, text) + seg[m.end():]; changed_labels += 1
    s = s[:_a] + seg + s[_b:]
    print("  ui labels: %s" % ("updated %d" % changed_labels if changed_labels else "already current"))
else:
    print("  ui labels: WARN timing menu not found - skipped")

# 2) chip color orders (5/6-ch + 16-bit) appended after the single-'W' option.
# These JS lines use 8-space indent (inside a function), not the option indent.
OIND = "        "
anchor = OIND + "result += pixelOutputTableInputOrderOption('W', colorOrder);\n"
if "RGBWC" in s:
    print("  ui colororders: already patched")
elif anchor in s:
    orders = ["RGBWC", "GRBWC", "RGBCW", "GRBCW",       # WS2805 / SM16825 8-bit (RGB+WW+CW)
              "RGBCWX", "GRBCWX", "RGBWCX",              # FW1906 (RGB+CW+WW+unused); RGBWCX kept for compat
              "RGB16", "GRB16",                          # UCS8903 (16-bit RGB)
              "RGBW16", "GRBW16", "BRGW16",              # UCS8904 (16-bit RGBW)
              "RGBWC16", "GRBWC16"]                      # SM16825-16 (16-bit RGB+WW+CW)
    add = "".join(OIND + "result += pixelOutputTableInputOrderOption('%s', colorOrder);\n" % o for o in orders)
    s = s.replace(anchor, anchor + add)
    print("  ui colororders: patched (WS2805/FW1906/UCS8904 orders)")
else:
    print("  ui colororders: WARN anchor not found (single-'W' option) - skipped")

# 3) live frame-budget readout: wire time of the longest port and the highest frame rate it can sustain.
#    A port whose frame does not fit the sequence's frame interval is cut off mid-frame by the PRU (measured), which
#    is silent otherwise. Bit periods = programmed LOW_TIME + ~110ns PRU overhead, measured per preset.
JS = """
// [fpp-bbb-pixels] live frame-budget readout (keep bit periods in sync with BBB48String.cpp)
var fbpBitNs = [1256, 1331, 1726, 2517, 2518, 2074, 1258, 1256, 1102, 1256, 1257];
function fbpBytesPerPixel(order) {
    order = order || 'RGB';
    var sixteen = /16$/.test(order);
    var n = sixteen ? order.length - 2 : order.length;
    return sixteen ? n * 2 : n;
}
function fbpUpdateBudget() {
    var el = $('#fbpBudget');
    if (!el.length) { return; }
    var pt = parseInt($('#BBB48StringPixelTiming').val()) || 0;
    var pre = {6: 8, 9: 6, 10: 15}[pt] || 0;
    var ports = {};
    $('[id^="BBB48String_Output_"]').each(function () {
        var m = this.id.match(/_Output_(\\d+)_(\\d+)_(\\d+)$/);
        var row = $(this);
        if (!m || !row.is(':visible')) { return; }
        var px = parseInt(row.find('.vsPixelCount').val()) || 0;
        if (!px) { return; }
        px += (parseInt(row.find('.vsStartNulls').val()) || 0) + (parseInt(row.find('.vsEndNulls').val()) || 0);
        ports[m[2]] = (ports[m[2]] || 0) + px * fbpBytesPerPixel(row.find('.vsColorOrder').val());
    });
    var worst = -1, wp = 0;
    for (var p in ports) { var b = ports[p] + pre; if (b > worst) { worst = b; wp = parseInt(p) + 1; } }
    if (worst < 0) { el.html(''); return; }
    var ms = worst * 8 * fbpBitNs[pt] / 1000000, fps = Math.floor(1000 / (ms + 0.5));
    var color = fps >= 40 ? '#198754' : (fps >= 20 ? '#b8860b' : '#c00');
    el.html('<b>Frame budget:</b> longest port (port ' + wp + ') = ' + worst + ' bytes, ' + ms.toFixed(1) +
            ' ms on the wire &middot; sustains up to <b style="color:' + color + '">' + fps + ' fps</b>' +
            (fps < 20 ? ' &mdash; too long for a 20 fps sequence: the end of that port will not update' : ''));
}
setInterval(fbpUpdateBudget, 1500);
"""
JSANCHOR = "var maxVirtualStringsPerOutput = 30;"
def add_js():
    """Install ui_limits.js. Replaces an older panel (v1 readout or an earlier v2) so re-running the installer upgrades it."""
    global s
    new = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui_limits.js")).read().rstrip("\n")
    BEGIN, END = "// [fpp-bbb-pixels] limits panel v2 BEGIN", "// [fpp-bbb-pixels] limits panel v2 END"
    if BEGIN in s and END in s:
        a, b = s.index(BEGIN), s.index(END) + len(END)
        if s[a:b] == new:
            print("  ui limits panel: already patched")
        else:
            s = s[:a] + new + s[b:]; print("  ui limits panel: updated")
        return
    m = re.search(r"// \[fpp-bbb-pixels\] live frame-budget readout.*?setInterval\(fbpUpdateBudget, 1500\);\n?", s, re.S)
    if m:
        s = s[:m.start()] + s[m.end():]; print("  ui limits panel: replaced the earlier frame-budget readout")
    if s.count(JSANCHOR) == 1:
        s = s.replace(JSANCHOR, new + "\n\n" + JSANCHOR); print("  ui limits panel: patched")
    else:
        print("  ui limits panel: WARN anchor not found - skipped")

def add_json_hooks():
    """Save the planned frame rate with the config (so BBB48String can check each port at start-up) and restore it on load."""
    global s
    a = "        output.pixelTiming = parseInt(GetPixelStringTiming());\n"
    if "output.targetFps" in s:
        print("  ui targetFps save: already patched")
    elif s.count(a) == 1:
        s = s.replace(a, a + "        output.targetFps = parseInt($('#fbpTargetFps').val()) || 20;\n"); print("  ui targetFps save: patched")
    else:
        print("  ui targetFps save: WARN anchor not found - skipped")
    b = "                $('#BBB48StringPixelTiming').val(pixelTiming);\n"
    if "window.fbpLoadedFps = output.targetFps" in s:
        print("  ui targetFps load: already patched")
    elif s.count(b) == 1:
        s = s.replace(b, b + "                if ('targetFps' in output) { window.fbpLoadedFps = output.targetFps; $('#fbpTargetFps').val(output.targetFps); }\n"); print("  ui targetFps load: patched")
    else:
        print("  ui targetFps load: WARN anchor not found - skipped")

    c = "        output.targetFps = parseInt($('#fbpTargetFps').val()) || 20;\n"
    if "output.chipCurrent = Math.max" in s:
        print("  ui chip current save: already patched")
    elif s.count(c) == 1:
        s = s.replace(c, c + """        var fbpCc = $('#fbpChipCurrent').val();
        if (fbpCc !== undefined && fbpCc !== '' && $('#fbpCurWrap').is(':visible')) { output.chipCurrent = Math.max(0, Math.min(100, parseInt(fbpCc) || 0)); }
        if (parseInt(GetPixelStringTiming()) == 9 && $('#fbpTm1914Mode').val() && $('#fbpTm1914Mode').val() != 'din') { output.tm1914Mode = $('#fbpTm1914Mode').val(); }
"""); print("  ui chip current save: patched")
    else:
        print("  ui chip current save: WARN anchor not found - skipped")
    e = "        output.targetFps = parseInt($('#fbpTargetFps').val()) || 20;\n"
    if "output.customT0" in s:
        print("  ui custom timing save: already patched")
    elif s.count(e) == 1:
        s = s.replace(e, e + """        if (parseInt(GetPixelStringTiming()) == 11) {
            output.customT0 = parseInt($('#fbpCustT0').val()) || 350; output.customT1 = parseInt($('#fbpCustT1').val()) || 700;
            output.customPeriod = parseInt($('#fbpCustPer').val()) || 1250; output.customInvert = $('#fbpCustInv').prop('checked') ? 1 : 0;
        }
"""); print("  ui custom timing save: patched")
    else:
        print("  ui custom timing save: WARN anchor not found - skipped")
    d = "                if ('targetFps' in output) { window.fbpLoadedFps = output.targetFps; $('#fbpTargetFps').val(output.targetFps); }\n"
    f = "                if ('targetFps' in output) { window.fbpLoadedFps = output.targetFps; $('#fbpTargetFps').val(output.targetFps); }\n"
    if "'customPeriod' in output" in s:
        print("  ui custom timing load: already patched")
    elif s.count(f) == 1:
        s = s.replace(f, f + "                if ('customPeriod' in output) { window.fbpLoadedCust = {t0: output.customT0, t1: output.customT1, per: output.customPeriod, inv: output.customInvert}; if ($('#fbpCustT0').length) { $('#fbpCustT0').val(output.customT0); $('#fbpCustT1').val(output.customT1); $('#fbpCustPer').val(output.customPeriod); $('#fbpCustInv').prop('checked', !!output.customInvert); } }\n"); print("  ui custom timing load: patched")
    else:
        print("  ui custom timing load: WARN anchor not found - skipped")
    if "window.fbpLoadedCur = output.chipCurrent" in s:
        print("  ui chip current load: already patched")
    elif s.count(d) == 1:
        s = s.replace(d, d + """                if ('chipCurrent' in output) { window.fbpLoadedCur = output.chipCurrent; $('#fbpChipCurrent').val(output.chipCurrent); }
                if ('tm1914Mode' in output) { window.fbpLoadedMode = output.tm1914Mode; $('#fbpTm1914Mode').val(output.tm1914Mode); }
"""); print("  ui chip current load: patched")
    else:
        print("  ui chip current load: WARN anchor not found - skipped")

def add_html():
    global s
    if 'id="fbpBudget"' in s:
        print("  ui frame budget readout: already patched")
        return
    m = re.search(r'<option value="1[0-8]">[^<]*</option>\s*</select>\s*</div>\s*</div>', s)
    if m:
        s = s[:m.end()] + '\n                <div id="fbpBudget" class="col-md-auto" style="font-size: 90%; align-self: center;"></div>' + s[m.end():]
        print("  ui frame budget readout: patched")
    else:
        print("  ui frame budget readout: WARN anchor not found - skipped")

add_js()
add_html()
add_json_hooks()

_atomic_write(P, s)
print("  ui: done")
