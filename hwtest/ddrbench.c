// [fpp-bbb-pixels hwtest] Write/read cost of the PRU DDR buffer exactly as FPP maps it (open /dev/mem O_RDWR, MAP_SHARED,
// 0x8f000000, 4 MB). Uses the UNUSED upper 1 MB so a running fppd's frame buffers are untouched.
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <time.h>
#include <unistd.h>
static double now_ms() { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec * 1e3 + t.tv_nsec / 1e6; }
int main() {
    int fd = open("/dev/mem", O_RDWR); if (fd < 0) { perror("open"); return 1; }
    uint8_t* base = mmap(0, 0x400000, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0x8f000000);
    if (base == MAP_FAILED) { perror("mmap"); return 2; }
    uint8_t* d = base + 0x300000;
    const int N = 216000, stride = 48, REP = 10;
    uint8_t* src = malloc(N + 64); for (int i = 0; i < N; i++) src[i] = rand();
    double t0, t1;
    t0 = now_ms(); for (int r = 0; r < REP; r++) for (int i = 0; i < N / stride; i++) for (int s = 0; s < stride; s++) d[i * stride + s] = src[s * (N / stride) + i]; t1 = now_ms();
    printf("transposing byte stores (what prepData does now): %6.2f ms / 216 KB  (%.1f ns/byte)\n", (t1 - t0) / REP, (t1 - t0) * 1e6 / REP / N);
    t0 = now_ms(); for (int r = 0; r < REP; r++) for (int i = 0; i < N; i++) d[i] = src[i]; t1 = now_ms();
    printf("sequential byte stores                           : %6.2f ms / 216 KB  (%.1f ns/byte)\n", (t1 - t0) / REP, (t1 - t0) * 1e6 / REP / N);
    t0 = now_ms(); for (int r = 0; r < REP; r++) for (int i = 0; i < N / 4; i++) ((volatile uint32_t*)d)[i] = ((uint32_t*)src)[i]; t1 = now_ms();
    printf("sequential 32-bit stores                         : %6.2f ms / 216 KB  (%.1f ns/byte)\n", (t1 - t0) / REP, (t1 - t0) * 1e6 / REP / N);
    t0 = now_ms(); for (int r = 0; r < REP; r++) memcpy(d, src, N); t1 = now_ms();
    printf("memcpy cached -> DDR                             : %6.2f ms / 216 KB  (%.1f ns/byte)\n", (t1 - t0) / REP, (t1 - t0) * 1e6 / REP / N);
    uint8_t* dst2 = malloc(N + 64);
    t0 = now_ms(); for (int r = 0; r < REP; r++) memcpy(dst2, src, N); t1 = now_ms();
    printf("memcpy cached -> cached (reference)              : %6.2f ms / 216 KB  (%.1f ns/byte)\n", (t1 - t0) / REP, (t1 - t0) * 1e6 / REP / N);
    t0 = now_ms(); int diff = 0; for (int r = 0; r < REP; r++) diff += memcmp(d, src + 1, 24 * 1024) != 0; t1 = now_ms();
    printf("memcmp DDR vs cached, 24 KB                      : %6.2f ms         (%.1f ns/byte)\n", (t1 - t0) / REP, (t1 - t0) * 1e6 / REP / 24576);
    t0 = now_ms(); for (int r = 0; r < REP; r++) memcpy(dst2, d, N); t1 = now_ms();
    printf("memcpy DDR -> cached (read)                      : %6.2f ms / 216 KB  (%.1f ns/byte)\n", (t1 - t0) / REP, (t1 - t0) * 1e6 / REP / N);
    return diff < 0;
}
