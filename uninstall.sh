#!/bin/bash
# Revert fpp-bbb-pixels: restore the *.orig backups (sources + prebuilt .so's,
# so no rebuild needed) and remove the SPIPixels library. Run: sudo bash uninstall.sh
set -e
SRC=/opt/fpp/src
echo "== fpp-bbb-pixels uninstall =="
systemctl stop fppd 2>/dev/null || true
for f in "$SRC/pru/FalconWS281x.asm" "$SRC/channeloutput/BBB48String.cpp" \
         "$SRC/channeloutput/PixelString.cpp" /opt/fpp/www/co-pixelStrings.php \
         /opt/fpp/www/api/controllers/system.php /opt/fpp/www/fppjson.php \
         "$SRC/libfpp.so" "$SRC/libfpp-co-BBB48String.so"; do
  if [ -f "$f.orig" ]; then cp -f "$f.orig" "$f" && echo "  restored $f"; else echo "  (no backup for $f)"; fi
done
rm -f /usr/local/lib/libfpp-co-SPIPixels.so "$SRC/libfpp-co-SPIPixels.so" /home/fpp/media/config/fbp-version /home/fpp/media/config/fbp-needs-reapply
/sbin/ldconfig 2>/dev/null || true
systemctl start fppd; sleep 6
echo "restored to stock. fppd: $(pgrep -n fppd >/dev/null && echo up || echo DOWN)"
echo "(Also remove any pixelTiming 2-10 / RGBWC / RGBW16 / RGBWC16 / SPIPixels entries from your channel-output config.)"
