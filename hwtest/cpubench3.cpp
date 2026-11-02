// [fpp-bbb-pixels hwtest] Candidate inner loops for prepData, string-major, stride-48 stores (the real layout).
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
static double now_ms() { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec * 1e3 + t.tv_nsec / 1e6; }
#define S 48
#define L 4500
#define N (S * L)
typedef void (*Fn)(uint8_t*, const int*, const uint8_t*, const uint8_t*, int);
static void v0(uint8_t* c, const int* m, const uint8_t* ch, const uint8_t* lut, int n) { for (int k = 0; k < n; k++) { *c = lut[ch[m[k]]]; c += S; } }
static void v1(uint8_t* c, const int* m, const uint8_t* ch, const uint8_t* lut, int n) { for (int k = 0; k < n; k++) { __builtin_prefetch(m + k + 32); *c = lut[ch[m[k]]]; c += S; } }
static void v2(uint8_t* c, const int* m, const uint8_t* ch, const uint8_t* lut, int n) {   // unroll x4
    int k = 0;
    for (; k + 4 <= n; k += 4) { int a = m[k], b = m[k + 1], d = m[k + 2], e = m[k + 3]; uint8_t x = ch[a], y = ch[b], z = ch[d], w = ch[e];
        c[0] = lut[x]; c[S] = lut[y]; c[2 * S] = lut[z]; c[3 * S] = lut[w]; c += 4 * S; }
    for (; k < n; k++) { *c = lut[ch[m[k]]]; c += S; } }
static void v3(uint8_t* c, const int* m, const uint8_t* ch, const uint8_t* lut, int n) {   // unroll x8
    int k = 0;
    for (; k + 8 <= n; k += 8) { int a0 = m[k], a1 = m[k + 1], a2 = m[k + 2], a3 = m[k + 3], a4 = m[k + 4], a5 = m[k + 5], a6 = m[k + 6], a7 = m[k + 7];
        uint8_t b0 = ch[a0], b1 = ch[a1], b2 = ch[a2], b3 = ch[a3], b4 = ch[a4], b5 = ch[a5], b6 = ch[a6], b7 = ch[a7];
        c[0] = lut[b0]; c[S] = lut[b1]; c[2 * S] = lut[b2]; c[3 * S] = lut[b3]; c[4 * S] = lut[b4]; c[5 * S] = lut[b5]; c[6 * S] = lut[b6]; c[7 * S] = lut[b7]; c += 8 * S; }
    for (; k < n; k++) { *c = lut[ch[m[k]]]; c += S; } }
static void v4(uint8_t* c, const int* m, const uint8_t* ch, const uint8_t* lut, int n) {   // unroll x8 + prefetch
    int k = 0;
    for (; k + 8 <= n; k += 8) { __builtin_prefetch(m + k + 32); __builtin_prefetch(ch + m[k] + 64);
        int a0 = m[k], a1 = m[k + 1], a2 = m[k + 2], a3 = m[k + 3], a4 = m[k + 4], a5 = m[k + 5], a6 = m[k + 6], a7 = m[k + 7];
        uint8_t b0 = ch[a0], b1 = ch[a1], b2 = ch[a2], b3 = ch[a3], b4 = ch[a4], b5 = ch[a5], b6 = ch[a6], b7 = ch[a7];
        c[0] = lut[b0]; c[S] = lut[b1]; c[2 * S] = lut[b2]; c[3 * S] = lut[b3]; c[4 * S] = lut[b4]; c[5 * S] = lut[b5]; c[6 * S] = lut[b6]; c[7 * S] = lut[b7]; c += 8 * S; }
    for (; k < n; k++) { *c = lut[ch[m[k]]]; c += S; } }
static void v5(uint8_t* c, const int* m, const uint8_t* ch, const uint8_t* lut, int n) {   // unroll x16 + prefetch
    int k = 0;
    for (; k + 16 <= n; k += 16) { __builtin_prefetch(m + k + 48); __builtin_prefetch(ch + m[k] + 96);
        int a[16]; uint8_t b[16];
        for (int j = 0; j < 16; j++) a[j] = m[k + j];
        for (int j = 0; j < 16; j++) b[j] = ch[a[j]];
        for (int j = 0; j < 16; j++) c[j * S] = lut[b[j]];
        c += 16 * S; }
    for (; k < n; k++) { *c = lut[ch[m[k]]]; c += S; } }
int main() {
    uint8_t* chan = (uint8_t*)malloc(N + 64); int* map = (int*)malloc(N * sizeof(int)); uint8_t* out = (uint8_t*)calloc(N + 64, 1); uint8_t* ref = (uint8_t*)calloc(N + 64, 1); uint8_t lut[256];
    for (int i = 0; i < N; i++) { chan[i] = rand(); map[i] = i; } for (int i = 0; i < 256; i++) lut[i] = i ^ 0x5a;
    for (int s = 0; s < S; s++) v0(ref + s, map + s * L, chan, lut, L);
    struct { const char* name; Fn f; } V[] = {{"v0 stock", v0}, {"v1 prefetch", v1}, {"v2 unroll x4", v2}, {"v3 unroll x8", v3}, {"v4 unroll x8 + prefetch", v4}, {"v5 unroll x16 + prefetch", v5}};
    for (auto& v : V) {
        memset(out, 0, N); for (int s = 0; s < S; s++) v.f(out + s, map + s * L, chan, lut, L);
        bool same = memcmp(out, ref, N) == 0;
        const int R = 12; double t0 = now_ms();
        for (int r = 0; r < R; r++) for (int s = 0; s < S; s++) v.f(out + s, map + s * L, chan, lut, L);
        double t1 = now_ms();
        printf("%-26s %6.2f ms  %5.1f ns/byte  %s\n", v.name, (t1 - t0) / R, (t1 - t0) * 1e6 / R / N, same ? "identical" : "MISMATCH");
    }
    return 0;
}
