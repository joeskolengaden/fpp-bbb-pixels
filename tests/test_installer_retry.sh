#!/bin/bash
# The installer's py() wrapper: retry a Python step that crashed by signal, never retry a normal failure.
HERE="$(cd "$(dirname "$0")/.." && pwd)"; FAILS=0
eval "$(sed -n '/^py(){/p' "$HERE/install.sh")"
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
sleep() { :; }                                    # no waiting in the test
python3() { n=$(cat "$T/n" 2>/dev/null || echo 0); echo $((n+1)) > "$T/n"
            case "$MODE" in crash2) [ "$n" -lt 2 ] && return 139 || return 0 ;; crash_always) return 139 ;; fail) return 1 ;; ok) return 0 ;; esac; }
t() { MODE=$1; echo 0 > "$T/n"; py x 2>/dev/null; rc=$?; n=$(cat "$T/n")
      if [ "$rc" = "$2" ] && [ "$n" = "$3" ]; then echo "ok   $1: rc=$rc after $n attempt(s)"; else echo "FAIL $1: rc=$rc attempts=$n (want rc=$2 attempts=$3)"; FAILS=$((FAILS+1)); fi; }
t ok 0 1                 # works first time
t crash2 0 3             # crashes twice by SIGSEGV, third attempt succeeds
t crash_always 139 5     # gives up after 5 attempts and reports the crash
t fail 1 1               # a normal failure (anchors do not match) is final, no retry
exit $FAILS
