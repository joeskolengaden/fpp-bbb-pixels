// what is the floor? remove one cost at a time from the prefetch loop
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
    uint8_t* chan = (uint8_t*)malloc(N + 64); int* map = (int*)malloc(N * sizeof(int)); uint8_t* out = (uint8_t*)calloc(N + 64, 1); uint8_t lut[256];
    int8_t* delta = (int8_t*)malloc(N); uint8_t* o2 = (uint8_t*)calloc(N + 64, 1);
    for (int i = 0; i < N; i++) { chan[i] = rand(); map[i] = i; delta[i] = 1; } for (int i = 0; i < 256; i++) lut[i] = i ^ 0x5a;
    const int R = 12; double t0, t1; volatile unsigned sink = 0;
    auto rep = [&](const char* n, double a, double b) { printf("%-52s %6.2f ms  %5.1f ns/byte\n", n, (b - a) / R, (b - a) * 1e6 / R / N); };
    t0 = now_ms(); for (int r = 0; r < R; r++) for (int s = 0; s < S; s++) { uint8_t* c = out + s; const int* m = map + s * L; for (int k = 0; k < L; k++) { __builtin_prefetch(m + k + 32); *c = lut[chan[m[k]]]; c += S; } } t1 = now_ms();
    rep("full (map + chan + lut + stride-48 store), prefetch", t0, t1);
    t0 = now_ms(); for (int r = 0; r < R; r++) for (int s = 0; s < S; s++) { uint8_t* c = out + s; for (int k = 0; k < L; k++) { *c = lut[chan[s * L + k]]; c += S; } } t1 = now_ms();
    rep("no map stream (index computed)", t0, t1);
    t0 = now_ms(); for (int r = 0; r < R; r++) for (int s = 0; s < S; s++) { uint8_t* c = out + s; const int* m = map + s * L; unsigned acc = 0; for (int k = 0; k < L; k++) { __builtin_prefetch(m + k + 32); acc += lut[chan[m[k]]]; } sink += acc; (void)c; } t1 = now_ms();
    rep("no stores (accumulate only)", t0, t1);
    t0 = now_ms(); for (int r = 0; r < R; r++) for (int s = 0; s < S; s++) { uint8_t* c = o2 + s * L; const int* m = map + s * L; for (int k = 0; k < L; k++) { __builtin_prefetch(m + k + 32); c[k] = lut[chan[m[k]]]; } } t1 = now_ms();
    rep("contiguous stores instead of stride-48", t0, t1);
    t0 = now_ms(); for (int r = 0; r < R; r++) for (int s = 0; s < S; s++) { uint8_t* c = out + s; const int8_t* d = delta + s * L; int idx = s * L; for (int k = 0; k < L; k++) { __builtin_prefetch(d + k + 64); idx += d[k]; *c = lut[chan[idx]]; c += S; } } t1 = now_ms();
    rep("1-byte delta map instead of int map", t0, t1);
    return sink == 7;
}
