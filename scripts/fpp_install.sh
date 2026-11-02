#!/bin/bash
# FPP Plugin Manager entry point: apply every fpp-bbb-pixels patch (PRU timing presets, Custom timing, chip current,
# UI limits panel, SPIPixels library) and rebuild the two FPP libraries. Same installer as running it by hand.
# FPP runs this as root right after cloning the plugin; it takes a few minutes on a BeagleBone (fppd is stopped during the compile).
PLUGINDIR="$(cd "$(dirname "$0")/.." && pwd)"
LOG=/home/fpp/media/logs/fbp-install.log
mkdir -p "$(dirname "$LOG")" 2>/dev/null
echo "fpp-bbb-pixels: installing from $PLUGINDIR (log: $LOG)"
bash "$PLUGINDIR/install.sh" 2>&1 | tee "$LOG"
rc=${PIPESTATUS[0]}
if [ "$rc" -eq 0 ]; then rm -f /home/fpp/media/config/fbp-needs-reapply; else echo "fpp-bbb-pixels: install FAILED (rc=$rc); FPP was rolled back to stock by the installer. See $LOG"; fi
exit $rc
