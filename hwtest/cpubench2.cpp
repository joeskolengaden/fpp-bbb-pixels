// [fpp-bbb-pixels hwtest] DRAM-latency test for the prepData gather: prefetch distance sweep (216 KB per pass, 48 x 4500).
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <initializer_list>
static double now_ms() { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec * 1e3 + t.tv_nsec / 1e6; }
#define S 48
#define L 4500
#define N (S * L)
int main() {
    uint8_t* chan = (uint8_t*)malloc(N + 64); int* map = (int*)malloc(N * sizeof(int)); uint8_t* out = (uint8_t*)malloc(N + 64); uint8_t lut[256];
    for (int i = 0; i < N; i++) { chan[i] = rand(); map[i] = i; } for (int i = 0; i < 256; i++) lut[i] = i ^ 0x5a;
    const int R = 10; double t0, t1; volatile uint8_t sink = 0;
    // small working set (fits L1): the pure-compute cost of the gather
    t0 = now_ms(); for (int r = 0; r < R * 48; r++) for (int i = 0; i < L; i++) out[i] = lut[chan[map[i]]]; t1 = now_ms();
    printf("cache-resident gather (pure compute)       : %5.1f ns/byte\n", (t1 - t0) * 1e6 / (R * 48.0) / L); sink += out[3];
    for (int P : {0, 16, 32, 64, 128, 256}) {
        t0 = now_ms();
        for (int r = 0; r < R; r++) for (int s = 0; s < S; s++) { uint8_t* c = out + s; const int* m = map + s * L; const uint8_t* ch = chan + s * L;
            for (int k = 0; k < L; k++) { if (P) { __builtin_prefetch(m + k + P); __builtin_prefetch(ch + k + P); } *c = lut[chan[m[k]]]; c += S; } }
        t1 = now_ms();
        printf("stock order, prefetch distance %-3d entries : %6.2f ms  %5.1f ns/byte\n", P, (t1 - t0) / R, (t1 - t0) * 1e6 / R / N); sink += out[5];
    }
    return sink == 255;
}
