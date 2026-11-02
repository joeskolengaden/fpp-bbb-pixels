#!/bin/bash
# FPP Plugin Manager entry point: put FPP back to stock (restores the *.orig backups, no rebuild needed).
PLUGINDIR="$(cd "$(dirname "$0")/.." && pwd)"
bash "$PLUGINDIR/uninstall.sh"
rm -f /home/fpp/media/config/fbp-needs-reapply
exit 0
