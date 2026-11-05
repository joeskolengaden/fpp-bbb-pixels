// [fpp-bbb-pixels] limits panel v2 BEGIN
// Shows, for the chip you pick, how many pixels one port can drive at each frame rate, checks every port against the
// frame rate you plan to run, highlights ports that are too long, and asks before saving a layout that would cut a string off.
// Numbers are measured on a BeagleBone Green (bit periods include the ~110 ns the PRU adds); keep in sync with BBB48String.cpp.
var fbpBitNs  = [1260, 1331, 1726, 2518, 2518, 2074, 1258, 1256, 1102, 1256, 1260];   // presets 0-10, measured
var fbpResetUs = [300, 300, 50, 50, 50, 50, 200, 200, 300, 200, 300];
function fbpBit(pt) { return pt === 11 ? Math.min(4000, Math.max(1000, parseInt($('#fbpCustPer').val()) || 1250)) : (pt === 12 ? 1300 : (pt > 11 ? 1250 : fbpBitNs[pt])); }   // 11 = the period you type, 12 = 1300 ns, 13-18 = 1250 ns
function fbpReset(pt) { return pt > 10 ? 300 : fbpResetUs[pt]; }
var fbpPreamble = {6: 8, 9: 6, 10: 15, 16: 9};                 // setup bytes sent at the start of every port
var fbpStepMs = {20: 50, 25: 40, 30: 33, 40: 25};      // FPP step time for each frame rate
var fbpFpsList = [20, 25, 30, 40];
var fbpPresets = [
    {name: 'Normal', chips: 'WS2811 (800 kHz), WS2812/B, WS2813, WS2813B-RGBW, WS2815, WS2818, SK6812, SK6813, GS8208, GS8608, SM16703, CS8812, HC2912C, UCS1903B, UCS2904 and most other WS281x-style pixels. Also the 16-bit chips WS2816 (colour order GRB16), UCS8903, UCS8904 and SM16825E (pick a 16-bit colour order).',
     rows: [[3, 'RGB pixels (3 bytes)'], [4, 'RGBW pixels (4 bytes)'], [6, '16-bit RGB: UCS8903, or 6-channel FW1906 (6 bytes)'], [8, '16-bit RGBW: UCS8904 (8 bytes)'], [10, '16-bit RGBWC: SM16825E (10 bytes)']],
     note: 'SM16825E automatically gets a fixed current setting of about 58 mA per channel. GS8608 uses this same waveform, and it plays its own test pattern if the data line goes quiet (WLED keeps a signal on it about twice a second). FPP sends frames while a sequence or test mode is running, including all-black frames. It does not send a keepalive after the output stops.'},
    {name: 'Slow', chips: 'WS281x variants that need a longer high time (800 kHz).', rows: [[3, 'RGB pixels (3 bytes)'], [4, 'RGBW pixels (4 bytes)']], note: ''},
    {name: 'APA104 / APA106 / PL9823 / SK6822', chips: 'The slower 1.7 microsecond-per-bit pixels.', rows: [[3, 'RGB pixels (3 bytes)']], note: ''},
    {name: 'WS2811 400 kHz', chips: 'Old low-speed WS2811. About half the speed of a WS2812.', rows: [[3, 'RGB pixels (3 bytes)']], note: ''},
    {name: 'UCS1903 400 kHz', chips: 'Old low-speed UCS1903/UCS2903. About half the speed of a WS2812.', rows: [[3, 'RGB pixels (3 bytes)']], note: ''},
    {name: 'TM1803', chips: 'TM1803 pixels (2 microseconds per bit).', rows: [[3, 'RGB pixels (3 bytes)']], note: ''},
    {name: 'TM1814 (inverted)', chips: 'TM1814 RGBW pixels. Use colour order WRGB.', rows: [[4, 'WRGB pixels (4 bytes)']],
     note: 'Sends an 8-byte setup frame (maximum current) at the start of EVERY port, so all ports on this board must be TM1814.'},
    {name: 'TM1829 (inverted)', chips: 'TM1829 RGB pixels.', rows: [[3, 'RGB pixels (3 bytes)']], note: ''},
    {name: 'WS2805', chips: 'WS2805 pixels with 5 channels: RGB plus warm and cool white. Use colour order RGBWC.', rows: [[5, 'RGBWC pixels (5 bytes)']], note: ''},
    {name: 'TM1914 (inverted)', chips: 'TM1914 RGB pixels.', rows: [[3, 'RGB pixels (3 bytes)']],
     note: 'Sends a 6-byte setup frame at the start of EVERY port, so all ports on this board must be TM1914.'},
    {name: 'UCS7604', chips: 'UCS7604 RGBW pixels. Colour order RGBW = 8-bit, RGBW16 = 16-bit.', rows: [[4, '8-bit RGBW (4 bytes)'], [8, '16-bit RGBW (8 bytes)']],
     note: 'Sends a 15-byte setup frame at the start of EVERY port, so all ports on this board must be UCS7604.'},
    {name: 'Custom timing', chips: 'Any single-wire pixel chip: type the three pulse times from its datasheet (T0H, T1H and the full bit period, in nanoseconds). Pick the colour order that matches the chip.',
     rows: [[3, 'RGB pixels (3 bytes)'], [4, 'RGBW pixels (4 bytes)'], [6, '16-bit RGB (6 bytes)']],
     note: 'Anything with a bit period under about 1,000 ns is outside what this hardware can produce. Tick "Inverted" for chips that idle high (TM18xx style). Every port on this board uses the same timing.'},
    {name: 'TM1903 / TM1824 / TM1934', chips: 'Titan Micro TM1903 and TM1934 (RGB) and TM1824 (RGBW, colour order RGBW). Same pulses as TM1814 but NOT inverted.', rows: [[3, 'RGB pixels (3 bytes)'], [4, 'RGBW pixels (4 bytes)']],
     note: 'TM1934 can also take an optional mode-setting frame at power-up; its bytes are not printed in the datasheet text, so none is sent.'},
    {name: 'UCS2912', chips: 'UCS2912 12-channel RGB driver (4 RGB groups per chip; set 4 pixels per chip as 4 pixels on the port). Needs a longer 0-pulse than Normal.', rows: [[3, 'RGB pixels (3 bytes)']], note: ''},
    {name: 'UCS1912', chips: 'UCS1912 12-channel RGB driver. Needs a longer 1-pulse (1 microsecond) than Normal.', rows: [[3, 'RGB pixels (3 bytes)']], note: ''},
    {name: 'TX1812 / TX1818 / LC8816E / GS8208B', chips: 'The 0.3 / 0.9 microsecond pixel family: TX1812, TX1818, LC8816E (RGBW, order GRBW), GS8208B, SM16703SP, SM16824E (RGBW).', rows: [[3, 'RGB pixels (3 bytes)'], [4, 'RGBW pixels (4 bytes)']], note: 'TX1812 and LC8816E want colour order GRB / GRBW. SM16824E wants RGBW. Its datasheet also puts a 16-bit current-gain word after the last pixel; that word is not sent, so the current stays at whatever the REXT resistor set.'},
    {name: 'TM1908', chips: 'TM1908 RGB pixels (Titan Micro).', rows: [[3, 'RGB pixels (3 bytes)']],
     note: 'Sends a 9-byte setup frame (auto-switch mode and current) at the start of EVERY port, so all ports on this board must be TM1908. Chip current is adjustable (2-25 mA).'},
    {name: 'LPD1886 (8-bit)', chips: 'LPD1886 in 8-bit mode (leave its GM pin floating). The 12-bit mode cannot be driven.', rows: [[3, 'RGB pixels (3 bytes)']], note: ''},
    {name: 'LC8812 / LC8812B', chips: 'LC8812 and LC8812B RGB pixels (order GRB). One timing that is inside both datasheet versions.', rows: [[3, 'RGB pixels (3 bytes)']], note: ''}
];

function fbpBytesPerPixel(order) {
    order = order || 'RGB';
    var sixteen = /16$/.test(order);
    var n = sixteen ? order.length - 2 : order.length;
    return sixteen ? n * 2 : n;
}
function fbpFixedBytes(pt, order) {                    // setup/trailer bytes added to the port
    var f = fbpPreamble[pt] || 0;
    if (/^(RGBWC16|GRBWC16)$/.test(order || '')) { f += 4; }   // SM16825E current trailer
    return f;
}
// Largest pixel count one port can drive: (bytes that fit in the frame - fixed bytes) / bytes per pixel.
function fbpMaxPixels(pt, bpp, fixed, fps) {
    var budgetUs = fbpStepMs[fps] * 1000 - fbpReset(pt) - 200;
    var bytes = Math.floor(budgetUs * 1000 / fbpBit(pt) / 8) - fixed;
    return Math.max(0, Math.floor(bytes / bpp));
}
function fbpFmt(n) { return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ','); }
function fbpTargetFps() { return parseInt($('#fbpTargetFps').val()) || 20; }

// Chip current (percent of the chip's own range) and what it means, per chip. Mirrors PixelString.cpp.
var fbpSm16825eMa = [10.2, 20.3, 30.4, 40.5, 50.6, 60.7, 70.8, 80.9, 91.0, 101.1, 111.2, 121.3, 130.7, 140.6, 150.5, 160.2,
                     170.0, 179.0, 188.5, 198.0, 207.8, 216.8, 226.4, 235.8, 245.0, 254.4, 263.6, 272.8, 282.0, 291.0, 300.0, 310.0];
function fbpCurrentHint(pt, sm, raw) {
    var pct = (raw === '' || raw === undefined) ? null : Math.max(0, Math.min(100, parseInt(raw) || 0));
    if (pt === 6) { return pct === null ? 'default: maximum (38 mA per channel)' : 'about ' + (6.5 + pct * 0.315).toFixed(1) + ' mA per channel (range 6.5-38)'; }
    if (pt === 16) { return pct === null ? 'default: maximum (25 mA per channel)' : 'about ' + (2 + pct * 0.23).toFixed(1) + ' mA per channel (range 2-25)'; }
    if (pt === 10) { return pct === null ? 'default: level 8 of 15' : 'level ' + Math.max(1, Math.round(pct * 15 / 100)) + ' of 15 per channel'; }
    if (sm) {
        if (pct === null) { return 'default: gain 5 = ' + fbpSm16825eMa[5] + ' mA per channel'; }
        var t = 10.2 + pct * (310 - 10.2) / 100, best = 0;
        for (var i = 1; i < 32; i++) { if (Math.abs(fbpSm16825eMa[i] - t) < Math.abs(fbpSm16825eMa[best] - t)) { best = i; } }
        return 'gain ' + best + ' = ' + fbpSm16825eMa[best] + ' mA per channel (range 10-310)';
    }
    return '';
}
// Custom timing: the PRU can only make pulses it has time for; say so before the board silently misbehaves.
function fbpCustCheck() {
    var t0 = parseInt($('#fbpCustT0').val()) || 0, t1 = parseInt($('#fbpCustT1').val()) || 0, per = parseInt($('#fbpCustPer').val()) || 0, msg = '';
    if (t0 < 250 || t0 > 3000) { msg = 'T0H must be 250-3000 ns.'; }
    else if (t1 <= t0 + 50) { msg = 'T1H must be at least 100 ns longer than T0H.'; }
    else if (per < 1000) { msg = 'Bit period under 1000 ns is faster than this board can generate.'; }
    else if (per < t1 + 150) { msg = 'The bit period must be at least 150 ns longer than T1H.'; }
    else if (per > 4000) { msg = 'Bit period over 4000 ns is not supported.'; }
    $('#fbpCustMsg').text(msg ? '\u26a0 ' + msg : '= ' + Math.round(1e6 / per) / 1000 + ' Mbit/s').css('color', msg ? '#c00' : '');
    return !msg;
}
function fbpHasSm16825e() {
    var yes = false;
    $('[id^="BBB48String_Output_"] .vsColorOrder').each(function () { if (/^(RGBWC16|GRBWC16)$/.test($(this).val() || '')) { yes = true; } });
    return yes;
}
function fbpUpdateChipOpts() {
    var pt = parseInt($('#BBB48StringPixelTiming').val()) || 0, sm = (pt === 0) && fbpHasSm16825e();
    var showCur = (pt === 6 || pt === 10 || pt === 16 || sm);
    $('#fbpCurWrap').toggle(showCur);
    $('#fbpModeWrap').toggle(pt === 9);
    $('#fbpCustWrap').toggle(pt === 11);
    if (pt === 11) { fbpCustCheck(); }
    if (showCur) { $('#fbpCurHint').text('(' + fbpCurrentHint(pt, sm, $('#fbpChipCurrent').val()) + ')'); }
}

function fbpRenderInfo() {
    var card = $('#fbpInfo');
    if (!card.length) { return; }
    var pt = parseInt($('#BBB48StringPixelTiming').val()) || 0, p = fbpPresets[pt] || fbpPresets[0], tf = fbpTargetFps();
    var h = '<div style="border:1px solid #ccc;border-radius:6px;padding:8px 12px;margin:6px 0;font-size:90%">' +
            '<b>' + p.name + '</b> &mdash; ' + p.chips +
            '<table class="table table-sm" style="width:auto;margin:6px 0 4px"><thead><tr><th>One port can drive up to</th>';
    for (var i = 0; i < fbpFpsList.length; i++) {
        h += '<th style="text-align:right' + (fbpFpsList[i] === tf ? ';background:rgba(255,193,7,0.28)' : '') + '">' + fbpFpsList[i] + ' fps</th>';
    }
    h += '</tr></thead><tbody>';
    for (var r = 0; r < p.rows.length; r++) {
        var bpp = p.rows[r][0], fixed = fbpPreamble[pt] || 0;
        if (pt === 0 && bpp === 10) { fixed += 4; }
        h += '<tr><td>' + p.rows[r][1] + '</td>';
        for (var j = 0; j < fbpFpsList.length; j++) {
            h += '<td style="text-align:right' + (fbpFpsList[j] === tf ? ';background:rgba(255,193,7,0.28)' : '') + '"><b>' +
                 fbpFmt(fbpMaxPixels(pt, bpp, fixed, fbpFpsList[j])) + '</b> pixels</td>';
        }
        h += '</tr>';
    }
    h += '</tbody></table>' +
         '<span class="text-muted">This is a limit per port, however many ports you use (up to 48). Going over it does not cause an error: ' +
         'the pixels at the far end of the string simply stop updating. A faster sequence needs shorter strings.' +
         (p.note ? '<br><b>Note:</b> ' + p.note : '') + '</span></div>';
    card.html(h);
}

// Walk the page's rows: bytes per port and the rows that belong to it.
function fbpScanPorts() {
    var pt = parseInt($('#BBB48StringPixelTiming').val()) || 0, ports = {};
    $('[id^="BBB48String_Output_"]').each(function () {
        var m = this.id.match(/_Output_(\d+)_(\d+)_(\d+)$/), row = $(this);
        if (!m || !row.is(':visible')) { return; }
        var px = parseInt(row.find('.vsPixelCount').val()) || 0;
        if (!px) { return; }
        var nulls = (parseInt(row.find('.vsStartNulls').val()) || 0) + (parseInt(row.find('.vsEndNulls').val()) || 0);
        var order = row.find('.vsColorOrder').val(), bpp = fbpBytesPerPixel(order);
        var P = ports[m[2]] = ports[m[2]] || {rows: [], bytes: 0, fixed: 0, bpp: bpp, port: parseInt(m[2]) + 1};
        P.rows.push({el: row, px: px + nulls, bpp: bpp, order: order});
        P.bytes += (px + nulls) * bpp;
        P.fixed = Math.max(P.fixed, fbpFixedBytes(pt, order));
        P.bpp = Math.max(P.bpp, bpp);
    });
    return ports;
}
function fbpFindOver() {
    var pt = parseInt($('#BBB48StringPixelTiming').val()) || 0, tf = fbpTargetFps(), over = [], ports = fbpScanPorts();
    for (var k in ports) {
        var P = ports[k], maxBytes = fbpMaxPixels(pt, 1, P.fixed, tf);       // bytes the frame has room for
        P.maxBytes = maxBytes;
        P.maxPx = Math.floor(maxBytes / P.bpp);
        P.totalPx = P.rows.reduce(function (a, r) { return a + r.px; }, 0);
        if (P.bytes > maxBytes) { over.push(P); }
    }
    return {ports: ports, over: over, pt: pt, fps: tf};
}
function fbpUpdateBudget() {
    var el = $('#fbpBudget');
    if (!el.length) { return; }
    if (!$('#fbpTargetFps').length) { fbpInstall(); }
    fbpUpdateChipOpts();
    var res = fbpFindOver(), n = 0;
    $('[id^="BBB48String_Output_"] .vsPixelCount').css('outline', '').attr('title', '');
    for (var k in res.ports) { n++; }
    if (!n) { el.html(''); fbpRenderInfo(); return; }
    var worst = null;
    for (var k2 in res.ports) {
        var P = res.ports[k2];
        if (!worst || P.bytes > worst.bytes) { worst = P; }
    }
    if (!res.over.length) {
        el.html('<span style="color:#198754"><b>&#10003; All ports fit at ' + res.fps + ' fps.</b></span> Longest: port ' + worst.port + ', ' + fbpFmt(worst.totalPx) +
                ' pixels (limit ' + fbpFmt(worst.maxPx) + ').');
    } else {
        var list = res.over.slice(0, 3).map(function (P) { return 'port ' + P.port + ': ' + fbpFmt(P.totalPx) + ' px, limit ' + fbpFmt(P.maxPx); }).join('; ');
        el.html('<span style="color:#c00"><b>&#9888; ' + res.over.length + ' port(s) too long for ' + res.fps + ' fps</b></span> (' + list +
                (res.over.length > 3 ? '; ...' : '') + '). The end of those strings will not update. ' +
                '<input type="button" id="fbpFixBtn" class="buttons" value="Fix automatically" onclick="fbpAutoFix()" title="Shortens the over-long strings so every port fits at this frame rate">');
        res.over.forEach(function (P) {
            P.rows.forEach(function (r) {
                r.el.find('.vsPixelCount').css('outline', '2px solid #c00')
                    .attr('title', 'Port ' + P.port + ' can drive at most ' + fbpFmt(P.maxPx) + ' pixels at ' + res.fps + ' fps with these settings (it has ' + fbpFmt(P.totalPx) + ').');
            });
        });
    }
    fbpRenderInfo();
}
// Shorten the last strings on each over-long port until it fits.
function fbpAutoFix() {
    var res = fbpFindOver();
    res.over.forEach(function (P) {
        var excess = P.bytes - P.maxBytes;
        for (var i = P.rows.length - 1; i >= 0 && excess > 0; i--) {
            var r = P.rows[i], inp = r.el.find('.vsPixelCount'), cur = parseInt(inp.val()) || 0;
            var cut = Math.min(cur, Math.ceil(excess / r.bpp));
            inp.val(cur - cut).trigger('change');
            excess -= cut * r.bpp;
        }
    });
    fbpUpdateBudget();
}
function fbpInstall() {
    if (!$('#fbpStyle').length) {   // the Fix automatically button: solid red, white bold text, gently pulsing so it cannot be missed
        $('head').append('<style id="fbpStyle">#fbpFixBtn{background:#d00!important;color:#fff!important;font-weight:bold;border:2px solid #900!important;' +
            'padding:4px 16px;border-radius:5px;margin-left:8px;cursor:pointer;animation:fbpPulse 1.4s ease-in-out infinite}' +
            '#fbpFixBtn:hover{background:#a00!important}' +
            '@keyframes fbpPulse{0%,100%{box-shadow:0 0 0 0 rgba(221,0,0,.55)}50%{box-shadow:0 0 0 7px rgba(221,0,0,0)}}</style>');
    }
    var sel = $('#BBB48StringPixelTiming');
    if (!sel.length || $('#fbpTargetFps').length) { return; }
    var saved = window.fbpLoadedFps || 20;                   // the frame rate stored in this board's saved config wins
    if (!window.fbpLoadedFps) { try { saved = parseInt(localStorage.getItem('fbpTargetFps')) || 20; } catch (e) {} }
    var opts = fbpFpsList.map(function (f) { return '<option value="' + f + '">' + f + ' fps</option>'; }).join('');
    sel.closest('.col-md-auto').append('<span style="margin-left:14px"><b>Plan for:</b> <select id="fbpTargetFps" title="The sequence frame rate you intend to run. Ports longer than this frame rate allows are flagged.">' + opts + '</select></span>');
    $('#fbpTargetFps').val(saved).on('change', function () {
        try { localStorage.setItem('fbpTargetFps', $(this).val()); } catch (e) {}
        fbpUpdateBudget();
    });
    sel.closest('.col-md-auto').append('<span id="fbpChipOpts" style="margin-left:14px">' +
        '<span id="fbpCurWrap" style="display:none"><b>Chip current:</b> <input id="fbpChipCurrent" type="number" min="0" max="100" step="5" placeholder="default" style="width:78px" ' +
        'title="Percent of this chip\'s own current range. Leave empty for the default."> % <span id="fbpCurHint" class="text-muted"></span></span> ' +
        '<span id="fbpModeWrap" style="display:none"><b>TM1914 mode:</b> <select id="fbpTm1914Mode" title="DIN only is the normal wiring; Auto-switch uses the backup signal line if the main one fails.">' +
        '<option value="din">DIN only</option><option value="auto">Auto-switch (backup signal)</option><option value="fdin">FDIN only</option></select></span></span>');
    sel.closest('.col-md-auto').append('<span id="fbpCustWrap" style="display:none;margin-left:14px"><b>Custom timing (ns):</b> ' +
        'T0H <input id="fbpCustT0" type="number" min="250" max="3000" step="10" value="350" style="width:70px" title="High time of a 0 bit (datasheet T0H)"> ' +
        'T1H <input id="fbpCustT1" type="number" min="300" max="3500" step="10" value="700" style="width:70px" title="High time of a 1 bit (datasheet T1H)"> ' +
        'Bit period <input id="fbpCustPer" type="number" min="1000" max="4000" step="10" value="1250" style="width:78px" title="Full time of one bit (T0H+T0L, or 1/baud)"> ' +
        '<label style="margin:0 0 0 6px"><input id="fbpCustInv" type="checkbox"> Inverted (idle high)</label> <span id="fbpCustMsg" class="text-muted"></span></span>');
    if (window.fbpLoadedCust) { $('#fbpCustT0').val(window.fbpLoadedCust.t0); $('#fbpCustT1').val(window.fbpLoadedCust.t1); $('#fbpCustPer').val(window.fbpLoadedCust.per); $('#fbpCustInv').prop('checked', !!window.fbpLoadedCust.inv); }
    $('#fbpCustT0,#fbpCustT1,#fbpCustPer,#fbpCustInv').on('input change', fbpUpdateBudget);
    if (window.fbpLoadedCur !== undefined) { $('#fbpChipCurrent').val(window.fbpLoadedCur); }
    if (window.fbpLoadedMode) { $('#fbpTm1914Mode').val(window.fbpLoadedMode); }
    $('#fbpChipCurrent').on('input change', fbpUpdateChipOpts);
    sel.on('change', fbpUpdateBudget);
    if (!$('#fbpInfo').length) { $('#fbpBudget').after('<div id="fbpInfo" class="col-12"></div>'); }
}
// Ask before saving a layout that would cut strings off.
var fbpOrigSave = (typeof saveBBBOutputs === 'function') ? saveBBBOutputs : null;
if (fbpOrigSave) {
    saveBBBOutputs = function () {
        var res = fbpFindOver();
        if (res.over.length) {
            var msg = 'These ports are longer than ' + res.fps + ' fps allows, so the end of each string would NOT light:\n\n' +
                res.over.map(function (P) { return '  Port ' + P.port + ': ' + fbpFmt(P.totalPx) + ' pixels (limit ' + fbpFmt(P.maxPx) + ')'; }).join('\n') +
                '\n\nPress OK to save anyway, or Cancel to go back (the red "Fix automatically" button shortens them for you).';
            if (!confirm(msg)) { return; }
        }
        return fbpOrigSave.apply(this, arguments);
    };
}
$(function () { fbpInstall(); });
setInterval(fbpUpdateBudget, 1500);
// [fpp-bbb-pixels] limits panel v2 END
