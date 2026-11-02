#!/usr/bin/env python3
# [hwtest] board-side: write an uncompressed v2 FSEQ of <channels> x <frames> at <step_ms>, data changing every frame
# (two alternating pseudo-random frames, so FPP's change-detect path and the PRU copy are exercised every frame).
import os, random, struct, sys
path, channels, frames, step = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
rnd = random.Random(7)
seedbuf = bytes(rnd.randrange(256) for _ in range(4096))
a = (seedbuf * (channels // 4096 + 1))[:channels]
b = bytes((x ^ 0x5A) for x in a)
h = bytearray(32)
h[0:4] = b"PSEQ"
struct.pack_into("<H", h, 4, 32); h[6] = 0; h[7] = 2
struct.pack_into("<H", h, 8, 32); struct.pack_into("<I", h, 10, channels); struct.pack_into("<I", h, 14, frames)
h[18] = step
struct.pack_into("<Q", h, 24, 0x786C696768740001)
with open(path, "wb") as f:
    f.write(h)
    for i in range(frames):
        f.write(a if i % 2 == 0 else b)
