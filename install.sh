#!/bin/bash
# ============================================================================
# fpp-bbb-pixels  -  extended pixel-IC protocol support for FPP on BeagleBone
# ----------------------------------------------------------------------------
# Single-wire (PRU): APA104/APA106/PL9823/SK6822, WS2811-400, UCS1903-400,
#   TM1803, TM1814 (RGBW inverted), RGBW, WS2805 (5-ch), FW1906 (6-ch),
#   UCS8904 (16-bit RGBW).  Plus SPIPixels plugin (APA102/SK9822/WS2801/LPD/P9813).
#
# Target: BeagleBone, FPP 5.4+ (5.x line). Idempotent. Keeps *.orig backups.
#   sudo bash install.sh          # install
#   sudo bash install.sh --test   # install, then run the full self-test
#   sudo bash install.sh --check  # preflight + anchor dry-run only; changes nothing
#   sudo bash uninstall.sh        # revert
#
# Safety: preflight validates ALL patch anchors on copies first (all-or-nothing),
# and if the rebuild fails the box is auto-rolled-back to stock and fppd restarted.
#
# Small boards (e.g. BeagleBone Green: 480MB RAM, ~1GB free on a 4GB eMMC): the
# compile needs swap. If < COMFORT_MB (default 1300) is free the installer reclaims
# regenerable caches (apt .debs, ccache), sizes the swapfile to what is actually
# free (512MB-1GB), and adds best-effort zram swap on top. Nothing is kept afterward.
# ============================================================================
set -Eeuo pipefail   # -E: the ERR-trap rollback must also fire for failures inside functions
HERE="$(cd "$(dirname "$0")" && pwd)"
SRC=/opt/fpp/src
ASM=$SRC/pru/FalconWS281x.asm
CPP=$SRC/channeloutput/BBB48String.cpp
PS=$SRC/channeloutput/PixelString.cpp
PHP=/opt/fpp/www/co-pixelStrings.php
APIPHP="/opt/fpp/www/api/controllers/system.php /opt/fpp/www/fppjson.php"   # get the PHP-notice guard (optional)
LIBDIR=/usr/local/lib
RUN_TEST=0; CHECK_ONLY=0
for a in "$@"; do
  case "$a" in
    --test)  RUN_TEST=1 ;;
    --check) CHECK_ONLY=1 ;;
    --version) echo "fpp-bbb-pixels $(cat "$(cd "$(dirname "$0")" && pwd)/VERSION" 2>/dev/null || echo unknown)"; exit 0 ;;
    *) echo "unknown option: $a (use --test, --check or --version)" >&2; exit 2 ;;
  esac
done

say(){ echo "== $* =="; }
die(){ echo "ERROR: $*" >&2; exit 1; }

# ---- 0. preflight (environment) -----------------------------------------
say "preflight"
[ "$(id -u)" = 0 ] || die "run as root (sudo)"
[ -d "$SRC" ] || die "$SRC not found - not an FPP source install"
MODEL="$(tr -d '\0' < /proc/device-tree/model 2>/dev/null || echo '')"
echo "$MODEL" | grep -qiE "beaglebone|pocketbeagle|am335|am62" \
  || die "this system is not a BeagleBone ('$MODEL'); the PRU driver is BBB-only"
for t in g++ make php /usr/bin/clpru; do command -v "$t" >/dev/null 2>&1 || command -v "$(basename "$t")" >/dev/null 2>&1 || die "missing tool: $t"; done
COMFORT_MB="${COMFORT_MB:-1300}"
# A /swapfile left behind by an earlier interrupted run is ours: the rebuild step recreates it, so count
# its space as free (--check) or reclaim it now (real run) instead of tripping the disk preflight on it.
LEFTOVER_MB=0
if [ -f /swapfile ]; then
  LEFTOVER_MB=$(( $(stat -c %s /swapfile) / 1048576 ))
  if [ "$CHECK_ONLY" != 1 ]; then swapoff /swapfile 2>/dev/null || true; rm -f /swapfile; LEFTOVER_MB=0; echo "  removed leftover /swapfile from an earlier run"; fi
fi
AVAIL_MB=$(( $(df -Pm / | awk 'NR==2{print $4}') + LEFTOVER_MB ))
if [ "$AVAIL_MB" -lt "$COMFORT_MB" ]; then
  if [ "$CHECK_ONLY" = 1 ]; then
    echo "  only ${AVAIL_MB}MB free (< ${COMFORT_MB}MB): a real run would first reclaim apt/ccache caches"
  else
    echo "  only ${AVAIL_MB}MB free (< ${COMFORT_MB}MB): reclaiming apt/ccache caches (regenerable, not user data)"
    apt-get clean >/dev/null 2>&1 || true
    rm -rf /root/.ccache /home/fpp/.ccache 2>/dev/null || true
    journalctl --vacuum-size=8M >/dev/null 2>&1 || true
    AVAIL_MB=$(( $(df -Pm / | awk 'NR==2{print $4}') + LEFTOVER_MB ))
  fi
fi
# Swap sized to what is actually free, leaving ~350MB for objects/.so/backups.
if [ "$AVAIL_MB" -ge "$COMFORT_MB" ]; then SWAP_MB=1024; else SWAP_MB=$(( AVAIL_MB - 350 )); fi
[ "$SWAP_MB" -ge 512 ] || die "only ${AVAIL_MB}MB free on / - need >=862MB (512MB swap + ~350MB build headroom). Free some space first."
for f in "$ASM" "$CPP" "$PS" "$PHP"; do [ -f "$f" ] || die "missing $f"; done
VER=$(cat /etc/fpp/rfs_version 2>/dev/null || echo unknown); echo "FPP: $VER  |  $MODEL  |  ${AVAIL_MB}MB free  |  swap plan: ${SWAP_MB}MB"
# An offline board with no RTC boots with a stale clock (a fresh FPP image says 2019, its prebuilt
# objects are 2021). Then freshly patched sources look OLDER than their .o files and plain `make -n`
# says "up to date" - so the build below forces targets with `make -W` instead of trusting mtimes.
OBJ_T=$(stat -c %Y "$SRC/libfpp.so" 2>/dev/null || echo 0)
[ "$(date +%s)" -lt "$OBJ_T" ] && echo "  NOTE: system clock ($(date +%F)) is earlier than FPP's prebuilt files ($(date -d @"$OBJ_T" +%F)); build uses 'make -W', independent of timestamps" || true
case "$VER" in *v5.*) : ;; *) echo "  WARN: single-wire patchers target FPP 5.x; on 6.x+ they will fail the anchor check below (safe).";; esac

# ---- 0b. ALL-OR-NOTHING gate: dry-run every patcher on copies ------------
say "validating patch anchors (dry-run on copies)"
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
cp "$ASM" "$T/a"; cp "$CPP" "$T/c"; cp "$PS" "$T/p"; cp "$PHP" "$T/u"
python3 "$HERE/patch_asm.py"         "$T/a" >/dev/null || die "asm anchors don't match this FPP version - aborting (no changes made)"
python3 "$HERE/patch_bbb48string.py" "$T/c" >/dev/null || die "BBB48String anchors don't match - aborting"
python3 "$HERE/patch_pixelstring.py" "$T/p" >/dev/null || die "PixelString anchors don't match - aborting"
python3 "$HERE/patch_ui.py"          "$T/u" >/dev/null || die "co-pixelStrings.php anchors don't match - aborting"
php -l "$T/u" >/dev/null || die "patched PHP fails lint - aborting"
for f in $APIPHP; do
  [ -f "$f" ] || continue
  cp "$f" "$T/n"; python3 "$HERE/patch_php_notices.py" "$T/n" >/dev/null || die "$f: notice-guard patch failed - aborting"
  php -l "$T/n" >/dev/null || die "$f: patched PHP fails lint - aborting"
done
echo "  all anchors OK - safe to apply"
if [ "$CHECK_ONLY" = 1 ]; then say "check only - nothing was changed"; exit 0; fi

# ---- 1. backup -----------------------------------------------------------
say "backup (*.orig)"
for f in "$ASM" "$CPP" "$PS" "$PHP" $APIPHP "$SRC/libfpp.so" "$SRC/libfpp-co-BBB48String.so"; do
  [ -f "$f" ] || continue
  cp -n "$f" "$f.orig" 2>/dev/null && echo "  $f" || true
done

# ---- 2. apply patches ----------------------------------------------------
say "patch"
python3 "$HERE/patch_asm.py" "$ASM"; python3 "$HERE/patch_bbb48string.py" "$CPP"
python3 "$HERE/patch_pixelstring.py" "$PS"; python3 "$HERE/patch_ui.py" "$PHP"
for f in $APIPHP; do [ -f "$f" ] && python3 "$HERE/patch_php_notices.py" "$f"; done

# ---- 3. rebuild (with auto-rollback on failure) --------------------------
ADDED_SWAP=0; ADDED_ZRAM=0
# Best-effort compressed-RAM swap on top of the swapfile (never fatal).
setup_zram(){
  modprobe zram num_devices=1 2>/dev/null || return 0
  [ -e /sys/block/zram0/disksize ] || return 0
  if grep -q '^/dev/zram0 ' /proc/swaps; then ADDED_ZRAM=1; echo "  zram swap already active (will be torn down at the end)"; return 0; fi
  if [ "$(cat /sys/block/zram0/disksize)" != 0 ]; then echo 1 > /sys/block/zram0/reset 2>/dev/null || return 0; fi
  echo 192M > /sys/block/zram0/disksize || return 0
  mkswap /dev/zram0 >/dev/null 2>&1 || return 0
  swapon -p 100 /dev/zram0 2>/dev/null || return 0
  ADDED_ZRAM=1; echo "  zram swap 192MB enabled"
}
teardown_swap(){
  [ "$ADDED_ZRAM" = 1 ] && { swapoff /dev/zram0 2>/dev/null || true; echo 1 > /sys/block/zram0/reset 2>/dev/null || true; }
  [ "$ADDED_SWAP" = 1 ] && { swapoff /swapfile 2>/dev/null || true; rm -f /swapfile; }
  return 0
}
rollback(){
  set +e   # every restore step must run, whatever fails
  echo "!! build failed - rolling back to stock" >&2
  rm -f /home/fpp/media/config/fbp-version
  for f in "$SRC/libfpp.so" "$SRC/libfpp-co-BBB48String.so" "$ASM" "$CPP" "$PS" "$PHP"; do
    [ -f "$f.orig" ] && cp -f "$f.orig" "$f"; done
  systemctl start fppd 2>/dev/null || true
  teardown_swap
  echo "!! restored. fix the error and re-run." >&2
}
trap 'rollback; rm -rf "$T"' ERR

say "rebuild (swap + stop fppd for the compile)"
if [ "$(free -m | awk '/Mem:/{print $7}')" -lt 400 ]; then
  swapoff /swapfile 2>/dev/null || true; rm -f /swapfile   # discard any stale/inactive one
  dd if=/dev/zero of=/swapfile bs=1M count="$SWAP_MB" status=none; chmod 600 /swapfile; mkswap /swapfile >/dev/null; swapon /swapfile; ADDED_SWAP=1
  echo "  swapfile ${SWAP_MB}MB enabled"
  setup_zram || true
fi
systemctl stop fppd; sleep 2; cd "$SRC"
build_obj(){ # build_obj <target.so> <rel/path/File.cpp>  - compile one object, retrying the BBB's low-RAM ICE
  local tgt="$1" cpp="$2" cc obj t
  cc=$(make -n -W "$cpp" "$tgt" 2>/dev/null | grep -F -- " -c " | grep -F -- "$(basename "$cpp")" | head -1 | sed 's/^ccache //') || true
  [ -n "$cc" ] || { echo "  ERROR: could not extract the compile command for $cpp (make -n -W printed nothing)" >&2; return 1; }
  obj=$(echo "$cc" | grep -oE '[^ ]+\.o' | head -1) || true
  [ -n "$obj" ] && rm -f "$obj"
  for t in 1 2 3 4; do env CCACHE_DISABLE=1 bash -c "$cc" && return 0; echo "  $(basename "$cpp") compile failed/ICE (attempt $t)"; done
  echo "  ERROR: $cpp did not compile after 4 attempts" >&2; return 1; }
link_so(){ # link_so <target.so> <rel/path/File.o>  - link only (a full make would recompile ~80 files)
  local tgt="$1" obj="$2" ln
  ln=$(make -n -W "$obj" "$tgt" 2>/dev/null | grep -E -- " -o ${tgt}\$" | head -1 | sed 's/^ccache //') || true
  [ -n "$ln" ] || { echo "  ERROR: could not extract the link command for $tgt" >&2; return 1; }
  env CCACHE_DISABLE=1 bash -c "$ln"
  [ -s "$tgt" ] || { echo "  ERROR: $tgt missing/empty after link" >&2; return 1; }
  if cmp -s "$tgt" "$tgt.orig"; then echo "  ERROR: $tgt is byte-identical to stock - the rebuild changed nothing" >&2; return 1; fi
  echo "  linked $tgt ($(stat -c %s "$tgt") bytes)"; }
build_obj libfpp.so channeloutput/PixelString.cpp
build_obj libfpp-co-BBB48String.so channeloutput/BBB48String.cpp
link_so libfpp.so channeloutput/PixelString.o
link_so libfpp-co-BBB48String.so channeloutput/BBB48String.o
echo "  rebuilt libfpp.so + libfpp-co-BBB48String.so"

# ---- 4. SPIPixels plugin (optional) --------------------------------------
for d in "$HERE/SPIPixels" "$HERE/../plugins/SPIPixels" /home/fpp/media/plugins/SPIPixels; do
  [ -d "$d" ] || continue; say "SPIPixels plugin ($d)"
  ( cd "$d" && make clean >/dev/null 2>&1; make >/tmp/spipixels-build.log 2>&1 \
      && install -m0755 libfpp-co-SPIPixels.so "$LIBDIR/" && install -m0755 libfpp-co-SPIPixels.so "$SRC/" && echo "  installed" ) \
    || { echo "  SPIPixels build FAILED (log: /tmp/spipixels-build.log):"; tail -15 /tmp/spipixels-build.log 2>/dev/null | sed 's/^/    /'; }
  break
done
/sbin/ldconfig 2>/dev/null || true

# ---- 5. restart + validate ----------------------------------------------
systemctl start fppd; sleep 10
teardown_swap
trap - ERR                  # the rebuild succeeded: from here on a failing command must NOT roll the install back
trap 'rm -rf "$T"' EXIT
PID=$(pgrep -n fppd || true)
[ -n "$PID" ] || die "fppd did not start - check logs; run uninstall.sh to revert"
say "validate"
nm -D "$SRC/libfpp.so" 2>/dev/null | grep -q PixelString && echo "  libfpp.so OK"
php -l "$PHP" >/dev/null && echo "  php OK"
echo "  fppd up (pid $PID)"
VER_FBP=$(cat "$HERE/VERSION" 2>/dev/null || echo unknown)
COMMIT_FBP=$(git -C "$HERE" rev-parse --short HEAD 2>/dev/null || echo "-")
FPPV=$(curl -s -m5 localhost/api/fppd/version 2>/dev/null | python3 -c 'import sys,json;print(json.load(sys.stdin)["version"])' 2>/dev/null || echo unknown)
{ printf 'fbp_version=%s\nfbp_commit=%s\ninstalled=%s\nfpp=%s\n' "$VER_FBP" "$COMMIT_FBP" "$(date '+%F %T')" "$FPPV" > /home/fpp/media/config/fbp-version; } 2>/dev/null || true
chown fpp:fpp /home/fpp/media/config/fbp-version 2>/dev/null || true
echo "  fpp-bbb-pixels $VER_FBP ($COMMIT_FBP) recorded in /home/fpp/media/config/fbp-version"
if [ "$RUN_TEST" = 1 ]; then say "self-test"; bash "$HERE/selftest.sh" || echo "  (self-test reported issues - see above)"; fi
say "done"
echo "Pixel-strings page -> Pixel Timing lists 0-18 (incl. Custom timing); colour orders incl RGBW/RGBWC/RGBWCX/RGBW16/RGBWC16."
echo "See CONFIG.md for per-chip setup (esp. TM1814/TM1914/UCS7604 preambles, SM16825E current)."
