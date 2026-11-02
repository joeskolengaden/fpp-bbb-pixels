#!/usr/bin/env python3
# [fpp-bbb-pixels] Silence FPP 5.4.1's PHP "Undefined index" notices (about 100,000 a day in Apache's error log).
#
# Cause: fppd writes /home/fpp/media/fpp-info.json from its multisync system list. A board whose only link is USB (or no
# network at all) has an empty list, so the file holds just {"addresses": ""}. The status/info API then reads
# $json['channelRanges'], ['majorVersion'], ['minorVersion'] and ['typeId'] without checking they exist, and raises four
# notices on EVERY poll (the dashboard polls every second or two). Upstream bug; harmless to results (the values are null
# either way) but it floods the log, burns CPU and disk, and hides real errors.
# Fix: `?? null` -- identical result, no notice. Idempotent. Usage: patch_php_notices.py <php file> [<php file> ...]
import re, sys

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

PAT = re.compile(r"(\$json\['(?:channelRanges|majorVersion|minorVersion|typeId)'\])(\s*;)")
total = 0
for path in sys.argv[1:] or ["/opt/fpp/www/api/controllers/system.php", "/opt/fpp/www/fppjson.php"]:
    s = open(path).read()
    new, n = PAT.subn(r"\1 ?? null\2", s)
    if n == 0:
        print("  php notices: %s already patched (or no such reads)" % path)
        continue
    _atomic_write(path, new)
    total += n
    print("  php notices: %s - guarded %d reads" % (path, n))
print("  php notices: done")
