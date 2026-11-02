// [fpp-bbb-pixels hwtest] Which access pattern makes prepData slow on the AM335x? 216 KB (48 strings x 4500 B) per variant.
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
static double now_ms() { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec * 1e3 + t.tv_nsec / 1e6; }
#define S 48
#define L 4500
#define N (S * L)
int main() {
    uint8_t* chan = (uint8_t*)malloc(N + 64); int* map = (int*)malloc(N * sizeof(int)); uint8_t* out = (uint8_t*)malloc(N + 64); uint8_t lut[256];
    for (int i = 0; i < N; i++) { chan[i] = rand(); map[i] = i; } for (int i = 0; i < 256; i++) lut[i] = i ^ 0x5a;
    const int R = 10; double t0, t1; volatile uint8_t sink = 0;
    // A: one pass, sequential in and out
    t0 = now_ms(); for (int r = 0; r < R; r++) for (int i = 0; i < N; i++) out[i] = lut[chan[map[i]]]; t1 = now_ms();
    printf("A sequential gather, sequential store      : %6.2f ms  %5.1f ns/byte\n", (t1 - t0) / R, (t1 - t0) * 1e6 / R / N); sink += out[7];
    // B: stock order: string by string, store stride 48
    t0 = now_ms(); for (int r = 0; r < R; r++) for (int s = 0; s < S; s++) { uint8_t* c = out + s; const int* m = map + s * L; for (int k = 0; k < L; k++) { *c = lut[chan[m[k]]]; c += S; } } t1 = now_ms();
    printf("B stock order (string-major, stride-48 st.)  : %6.2f ms  %5.1f ns/byte\n", (t1 - t0) / R, (t1 - t0) * 1e6 / R / N); sink += out[9];
    // C: tiled (tile = 64 rows), per-string columns
    for (int T : (int[]){16, 64, 256}) {
        t0 = now_ms(); for (int r = 0; r < R; r++) for (int b = 0; b < L; b += T) for (int s = 0; s < S; s++) { uint8_t* c = out + (size_t)b * S + s; const int* m = map + s * L + b; int n = L - b < T ? L - b : T; for (int k = 0; k < n; k++) { *c = lut[chan[m[k]]]; c += S; } } t1 = now_ms();
        printf("C tiled TILE=%-3d                            : %6.2f ms  %5.1f ns/byte\n", T, (t1 - t0) / R, (t1 - t0) * 1e6 / R / N); sink += out[11];
    }
    // D: row-major (i outer, s inner): contiguous 48-byte stores, 48 read streams
    t0 = now_ms(); for (int r = 0; r < R; r++) for (int i = 0; i < L; i++) { uint8_t* c = out + (size_t)i * S; for (int s = 0; s < S; s++) c[s] = lut[chan[map[s * L + i]]]; } t1 = now_ms();
    printf("D row-major (contiguous store, 48 streams)  : %6.2f ms  %5.1f ns/byte\n", (t1 - t0) / R, (t1 - t0) * 1e6 / R / N); sink += out[13];
    // E: transpose-free: sequential output but the same gather via string-major with contiguous out
    t0 = now_ms(); for (int r = 0; r < R; r++) for (int s = 0; s < S; s++) { uint8_t* c = out + s * L; const int* m = map + s * L; for (int k = 0; k < L; k++) c[k] = lut[chan[m[k]]]; } t1 = now_ms();
    printf("E string-major with contiguous store         : %6.2f ms  %5.1f ns/byte\n", (t1 - t0) / R, (t1 - t0) * 1e6 / R / N); sink += out[15];
    return sink == 255;
}
