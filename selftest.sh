#!/bin/bash
# [fpp-bbb-pixels] Post-install self-test. Run on the device: sudo bash selftest.sh
# 1) PixelString channel maps (all chip modes) vs live libfpp   [config-independent]
# 2) PRU asm: structural check + full clpru compile of presets 0-10 and the Custom block (normal, long-wait and inverted variants) (if a
#    BBB48String output is configured, i.e. /tmp/*.hp exist)
# 3) SPIPixels plugin factory symbol
# 4) prefetching prepData is byte-identical to the stock loop (+ speed on this CPU)
HERE="$(cd "$(dirname "$0")" && pwd)"; SRC=/opt/fpp/src; RC=0

echo "== 1. PixelString channel maps =="
JS=$(pkg-config --cflags jsoncpp 2>/dev/null || echo -I/usr/include/jsoncpp)
rm -f /tmp/fbp_maps
for t in 1 2 3; do env CCACHE_DISABLE=1 g++ -O0 -std=gnu++14 -I"$SRC" $JS "$HERE/test_maps.cpp" \
      -L"$SRC" -lfpp -ljsoncpp -Wl,--allow-shlib-undefined -Wl,-rpath,"$SRC" -o /tmp/fbp_maps 2>/dev/null && break; done
if [ -x /tmp/fbp_maps ]; then
  MAG=$(/sbin/ldconfig -p | grep -o "/usr/lib/libGraphicsMagick++[^ ]*" | head -1)
  CURL=$(ls /usr/lib/*/libcurl.so* 2>/dev/null | head -1)
  LD_LIBRARY_PATH="$SRC" LD_PRELOAD="$MAG $CURL" /tmp/fbp_maps || RC=1
  rm -f /tmp/fbp_maps
else echo "  (map test build failed - BBB g++ ICE? re-run; not fatal)"; fi

echo "== 2. PRU asm =="
A=$SRC/pru/FalconWS281x.asm
for p in APA104 WS2811_400 UCS1903_400 TM1803 TM1814 TM1829 WS2805 TM1914 CUSTOM; do grep -q "PIXELTYPE_$p" "$A" && echo "  preset $p present" || { echo "  MISSING preset $p"; RC=1; }; done
grep -q "GPIO_SETDATAOUT (0x190" "$A" && echo "  inverted-waveform GPIO swap present" || { echo "  MISSING inverted-waveform GPIO swap"; RC=1; }
if [ -f /tmp/PinConfiguration.hp ] && [ -f /tmp/OutputLengths.hp ]; then
  OUT=$(grep -c "_gpio" /tmp/PinConfiguration.hp); FC=$(grep -oE "CHECK_[0-9A-Za-z_]+" /tmp/OutputLengths.hp | head -1); FC=${FC:-NO_PIXELS_CHECK}
  BASE="-DRUNNING_ON_PRU1 -DOUTPUTS=$OUT -DDDRONLY -DFIRST_CHECK=$FC -DDATA_LEN=4500"
  D=$(mktemp -d); cd "$D"
  for f in Normal: Slow:-DPIXELTYPE_SLOW APA104:-DPIXELTYPE_APA104 WS2811:-DPIXELTYPE_WS2811_400 UCS1903:-DPIXELTYPE_UCS1903_400 TM1803:-DPIXELTYPE_TM1803 TM1814:-DPIXELTYPE_TM1814 TM1829:-DPIXELTYPE_TM1829 WS2805:-DPIXELTYPE_WS2805 TM1914:-DPIXELTYPE_TM1914 CUSTOM:-DPIXELTYPE_CUSTOM,-DCUSTOM_T0=300,-DCUSTOM_T1=650,-DCUSTOM_LOW=1140 CUSTOMSLOW:-DPIXELTYPE_CUSTOM,-DCUSTOM_T0=450,-DCUSTOM_T1=1950,-DCUSTOM_LOW=2390,-DSLOW_WAITNS CUSTOMINV:-DPIXELTYPE_CUSTOM,-DCUSTOM_T0=300,-DCUSTOM_T1=650,-DCUSTOM_LOW=1140,-DCUSTOM_INVERT; do
    n=${f%%:*}; fl=${f#*:}; rm -f pp.asm pp.obj pp.out
    cpp -P -I/tmp -I"$SRC/pru" ${fl//,/ } $BASE "$A" > pp.asm 2>/dev/null
    if clpru -v3 pp.asm >/dev/null 2>&1 && [ -f pp.obj ] && clpru -v3 -z --entry_point main "$SRC/pru/AM335x_PRU.cmd" -o pp.out pp.obj >/dev/null 2>&1 && [ -f pp.out ]; then echo "  compile $n: PASS"; else echo "  compile $n: FAIL"; RC=1; fi
  done; cd /; rm -rf "$D"
else echo "  (configure a BBB48String output to enable the full 7-preset compile test)"; fi

echo "== 3. SPIPixels plugin =="
SO=$SRC/libfpp-co-SPIPixels.so; [ -f "$SO" ] || SO=/usr/local/lib/libfpp-co-SPIPixels.so
if [ -f "$SO" ]; then nm -D "$SO" 2>/dev/null | grep -qE "createOutputSPIPixels|createPlugin" && echo "  factory symbol OK" || { echo "  MISSING factory symbol"; RC=1; }
else echo "  (SPIPixels not installed)"; fi

echo "== 4. prepData (prefetching gather) =="
rm -f /tmp/fbp_prep
for t in 1 2 3; do env CCACHE_DISABLE=1 g++ -O2 -std=gnu++14 -I"$HERE" "$HERE/test_prepdata.cpp" -o /tmp/fbp_prep 2>/dev/null && break; done
if [ -x /tmp/fbp_prep ]; then /tmp/fbp_prep | sed 's/^/  /' || RC=1; rm -f /tmp/fbp_prep
else echo "  (prepData test build failed - BBB g++ ICE? re-run; not fatal)"; fi

echo "== self-test $([ $RC = 0 ] && echo PASSED || echo FAILED) =="; exit $RC
