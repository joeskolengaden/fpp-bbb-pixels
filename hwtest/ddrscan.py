#!/usr/bin/env python3
# [hwtest] board-side, READ-ONLY: find a byte pattern anywhere in one port's data in the PRU output window.
# Port data is interleaved: byte i of string s lives at i*stride + s. usage: ddrscan.py <hexpattern> -> "hits: [(stride, offset, index)]"
import mmap, os, sys
pat = bytes.fromhex(sys.argv[1])
fd = os.open("/dev/mem", os.O_RDONLY)
data = mmap.mmap(fd, 0x40000, mmap.MAP_SHARED, mmap.PROT_READ, offset=0x8f000000)[:]
hits = []
for stride in range(1, 49):
    for off in range(stride):
        col = data[off::stride]
        i = col.find(pat)
        if i >= 0:
            hits.append((stride, off, i))
print("hits:", hits[:4] if hits else "none")
