#!/bin/bash
# [fpp-bbb-pixels] OS-level fixes for a BeagleBone with no real-time clock and no internet, running FPP.
#   sudo bash system-fixes.sh --check                       what is wrong / already fixed (default, changes nothing)
#   sudo bash system-fixes.sh --apply [--set-time EPOCH]    fix it (idempotent); EPOCH = the true current Unix time
#   sudo bash system-fixes.sh --undo                        put everything back
#
# 1. CLOCK. The board has no RTC, so every boot starts in the past (a fresh image says 2019) and nothing corrects it when the only
#    link is USB. Consequences seen here: logrotate refuses to run ("last rotated in the future"), file timestamps and FPP's
#    schedules are wrong, and `make` thinks freshly patched sources are older than the prebuilt objects. Fix: a tiny service that
#    saves the time every 10 minutes and at shutdown, and at boot restores it if the clock is behind it (the same idea as
#    fake-hwclock, which this image lacks). It only ever moves the clock FORWARD, and real time sync (NTP) still wins when online.
#    `--set-time EPOCH` sets the clock once, only if it is currently before 2024.
# 2. MODULES. systemd-modules-load fails at every boot because /etc/modules and /etc/modules-load.d/modules.conf name modules this
#    kernel does not have (their function is built in). Those lines are commented out (and restored by --undo).
# 3. USB CONSOLE. serial-getty@ttyGS0 restarts instantly while no PC has the port open, hits systemd's start limit and shows as a
#    failed unit. A drop-in makes it wait 10 s between attempts so it stays healthy (a PC can still open the console).
MODE=--check; SETTIME=""
while [ $# -gt 0 ]; do
  case "$1" in --check|--apply|--undo) MODE=$1;; --set-time) shift; SETTIME=${1:-};; *) echo "usage: $0 [--check|--apply|--undo] [--set-time EPOCH]"; exit 2;; esac; shift
done
[ "$MODE" = --check ] || [ "$(id -u)" = 0 ] || { echo "run with sudo for $MODE"; exit 1; }
SB=/usr/local/sbin/fbp-clock; STATE=/var/lib/fbp-clock/last; UNITDIR=/etc/systemd/system
MODFILES="/etc/modules-load.d/modules.conf /etc/modules"; MARK="#fbp-disabled# "
GETTY_D=$UNITDIR/serial-getty@ttyGS0.service.d; MIN_SANE=1704067200   # 2024-01-01
ok(){ printf "  OK    %s\n" "$*"; }; todo(){ printf "  TODO  %s\n" "$*"; PENDING=$((PENDING+1)); }; PENDING=0

clock_script(){ cat <<'EOS'
#!/bin/sh
# fbp-clock: persist the clock on a board without an RTC.   fbp-clock save | restore
F=/var/lib/fbp-clock/last
case "$1" in
  save)    now=$(date +%s); [ "$now" -gt 1704067200 ] || exit 0       # never save a bogus (pre-2024) time
           mkdir -p /var/lib/fbp-clock && echo "$now" > "$F.tmp" && mv "$F.tmp" "$F" ;;
  restore) saved=$(cat "$F" 2>/dev/null || echo 0); now=$(date +%s)
           if [ "$saved" -gt "$now" ]; then date -u -s "@$saved" >/dev/null && logger -t fbp-clock "clock was behind ($now); restored to $saved"; fi ;;
  *) echo "usage: fbp-clock save|restore"; exit 2 ;;
esac
EOS
}

echo "== 1. clock =="
NOW=$(date +%s)
if [ "$NOW" -lt "$MIN_SANE" ]; then todo "system clock reads $(date '+%F %T') (before 2024): wrong"; else ok "system clock reads $(date '+%F %T')"; fi
if [ -x "$SB" ] && systemctl is-enabled fbp-clock.service >/dev/null 2>&1 && systemctl is-enabled fbp-clock-save.timer >/dev/null 2>&1; then
  ok "clock persistence installed (last saved: $( [ -f $STATE ] && date -d @$(cat $STATE) '+%F %T' || echo never ))"
else todo "clock persistence not installed"; fi
if [ "$MODE" = --apply ]; then
  clock_script > "$SB"; chmod 755 "$SB"
  cat > $UNITDIR/fbp-clock.service <<'EOS'
[Unit]
Description=Restore the system clock from its last saved time (no RTC on this board)
DefaultDependencies=no
After=local-fs.target
Before=fppd.service apache2.service logrotate.service sysinit.target
[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/local/sbin/fbp-clock restore
ExecStop=/usr/local/sbin/fbp-clock save
[Install]
WantedBy=sysinit.target
EOS
  cat > $UNITDIR/fbp-clock-save.service <<'EOS'
[Unit]
Description=Save the system clock for the next boot
[Service]
Type=oneshot
ExecStart=/usr/local/sbin/fbp-clock save
EOS
  cat > $UNITDIR/fbp-clock-save.timer <<'EOS'
[Unit]
Description=Save the system clock every 10 minutes
[Timer]
OnBootSec=5min
OnUnitActiveSec=10min
[Install]
WantedBy=timers.target
EOS
  systemctl daemon-reload
  if [ -n "$SETTIME" ] && [ "$NOW" -lt "$MIN_SANE" ] && [ "$SETTIME" -gt "$MIN_SANE" ]; then
    date -u -s "@$SETTIME" >/dev/null && echo "  set the clock to $(date '+%F %T %Z')"
  elif [ -n "$SETTIME" ]; then echo "  (clock not changed: it already looks right, or the supplied time is not plausible)"; fi
  systemctl enable fbp-clock.service fbp-clock-save.timer >/dev/null 2>&1
  systemctl start fbp-clock.service fbp-clock-save.timer 2>/dev/null
  "$SB" save
  systemctl reset-failed logrotate.service 2>/dev/null; systemctl start logrotate.service 2>/dev/null \
    && echo "  logrotate now runs cleanly" || echo "  (logrotate still failing - check: journalctl -u logrotate)"
fi
if [ "$MODE" = --undo ]; then
  systemctl disable --now fbp-clock-save.timer fbp-clock.service >/dev/null 2>&1
  rm -f "$SB" $UNITDIR/fbp-clock.service $UNITDIR/fbp-clock-save.service $UNITDIR/fbp-clock-save.timer; systemctl daemon-reload
  echo "  clock persistence removed (the clock itself is left as it is)"
fi

echo "== 2. kernel modules list =="
for f in $MODFILES; do
  [ -f "$f" ] || continue
  bad=""
  while read -r m rest; do
    case "$m" in ""|\#*) continue;; esac
    modprobe -n "$m" >/dev/null 2>&1 || bad="$bad $m"
  done < "$f"
  if [ -f "$f.fbp-orig" ] && grep -q "^$MARK" "$f"; then ok "$f: unloadable entries already disabled"
  elif [ -n "$bad" ]; then todo "$f lists modules this kernel cannot load:$bad"
  else ok "$f: every entry loads"; fi
  if [ "$MODE" = --apply ] && [ -n "$bad" ]; then
    [ -f "$f.fbp-orig" ] || cp -p "$f" "$f.fbp-orig"
    for m in $bad; do sed -i "s/^$m\([[:space:]].*\)\{0,1\}$/$MARK$m/" "$f"; done
    echo "  disabled in $f:$bad"
  fi
  if [ "$MODE" = --undo ] && [ -f "$f.fbp-orig" ]; then cp -p "$f.fbp-orig" "$f" && rm -f "$f.fbp-orig" && echo "  restored $f"; fi
done
if [ "$MODE" = --apply ]; then systemctl reset-failed systemd-modules-load.service 2>/dev/null; systemctl restart systemd-modules-load.service 2>/dev/null && echo "  module loader now succeeds" || echo "  (module loader still failing)"; fi

echo "== 3. USB serial console =="
if [ -f $GETTY_D/fbp-restart.conf ]; then ok "restart back-off drop-in installed"; else todo "serial-getty@ttyGS0 has no restart back-off (fails with 'start-limit-hit')"; fi
systemctl is-failed --quiet serial-getty@ttyGS0.service && todo "serial-getty@ttyGS0 is currently in the failed state"
if [ "$MODE" = --apply ]; then
  mkdir -p $GETTY_D; printf '[Unit]\nStartLimitIntervalSec=0\n[Service]\nRestartSec=10\n' > $GETTY_D/fbp-restart.conf
  systemctl daemon-reload; systemctl reset-failed serial-getty@ttyGS0.service 2>/dev/null; systemctl restart serial-getty@ttyGS0.service 2>/dev/null; echo "  USB console back-off installed"
fi
if [ "$MODE" = --undo ]; then rm -rf $GETTY_D; systemctl daemon-reload; echo "  USB console drop-in removed"; fi

echo "== 4. UDP receive buffers (only matters when you stream sACN / ArtNet / DDP into the board) =="
SYSCTL_F=/etc/sysctl.d/90-fbp-udp.conf; WANT=2097152
CUR=$(cat /proc/sys/net/core/rmem_default 2>/dev/null || echo 0)
if [ -f $SYSCTL_F ] && [ "$CUR" -ge "$WANT" ]; then ok "receive buffer default $CUR bytes (stress test: 192 KB dropped packets at ~9,000 packets/s, 2 MB dropped none)"
else todo "UDP receive buffer is $CUR bytes: sACN/ArtNet at full-board rates (~9,000 packets/s) overflowed it; 2 MB removed every drop"; fi
if [ "$MODE" = --apply ]; then
  printf '# fpp-bbb-pixels: bigger UDP receive buffers for streamed input. previous: %s %s\nnet.core.rmem_default=%s\nnet.core.rmem_max=%s\n' "$CUR" "$(cat /proc/sys/net/core/rmem_max)" "$WANT" "$((WANT*2))" > $SYSCTL_F
  sysctl -q -p $SYSCTL_F && echo "  UDP receive buffer set to $WANT bytes (restart FPPD so its sockets use it)"
fi
if [ "$MODE" = --undo ] && [ -f $SYSCTL_F ]; then
  prev=$(sed -n 's/^# .*previous: \([0-9]*\) \([0-9]*\)$/\1 \2/p' $SYSCTL_F); rm -f $SYSCTL_F
  [ -n "$prev" ] && sysctl -q -w net.core.rmem_default=${prev% *} net.core.rmem_max=${prev#* }; echo "  UDP receive buffer back to ${prev:-the kernel default}"
fi

echo
if [ "$MODE" = --check ]; then
  [ "$PENDING" = 0 ] && echo "system-fixes: nothing to do" || echo "system-fixes: $PENDING item(s) can be fixed - run: sudo bash system-fixes.sh --apply --set-time \$(date -u +%s)  (from a machine with the right time)"
else echo "system-fixes: $MODE done. Failed units now: $(systemctl --failed --no-legend 2>/dev/null | wc -l)"; fi
