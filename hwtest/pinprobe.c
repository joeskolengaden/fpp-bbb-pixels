// [fpp-bbb-pixels hwtest] Self-capture of a BeagleBone output pad via the GPIO input register.
// Samples GPIO bank DATAIN (default P8-30 = gpio2[25]) in a tight loop for <ms> and reports frames:
//   gap threshold (default 25 us of constant level) separates frames; per frame prints start time,
//   duration, rising-edge count (= bits sent if the sampling is fast enough) and the idle level.
// usage: pinprobe [ms=300] [bankBase=0x481AC000] [bit=25] [gap_us=25]
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <time.h>
#include <unistd.h>
#include <sys/resource.h>
#include <string.h>
static uint32_t* hp; static long hpn;
static int cmpu(const void* a, const void* b) { uint32_t x = *(const uint32_t*)a, y = *(const uint32_t*)b; return x < y ? -1 : x > y; }
#include <sys/mman.h>
static inline uint64_t now_ns(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC_RAW, &t); return (uint64_t)t.tv_sec * 1000000000ull + t.tv_nsec; }
int main(int argc, char** argv) {
    int ms = argc > 1 ? atoi(argv[1]) : 300;
    uint32_t base = argc > 2 ? (uint32_t)strtoul(argv[2], 0, 0) : 0x481AC000;
    int bit = argc > 3 ? atoi(argv[3]) : 25;
    int gap_ns = (argc > 4 ? atoi(argv[4]) : 25) * 1000;
    setpriority(PRIO_PROCESS, 0, -5);    // modest boost only: a SCHED_FIFO sampler starves fppd on this single core
    mlockall(MCL_CURRENT | MCL_FUTURE);
    int fd = open("/dev/mem", O_RDONLY | O_SYNC);
    if (fd < 0) { perror("open /dev/mem"); return 2; }
    volatile uint32_t* g = mmap(0, 4096, PROT_READ, MAP_SHARED, fd, base);
    if (g == MAP_FAILED) { perror("mmap"); return 3; }
    volatile uint32_t* din = g + (0x138 / 4);
    uint32_t m = 1u << bit;
    uint64_t t0 = now_ns(), end = t0 + (uint64_t)ms * 1000000ull;
    int last = (*din & m) != 0, seen[2] = {0, 0};
    uint64_t frameStart = 0, frameLast = 0, lastEdge = t0, prevStart = 0, prevT = t0;
    long rises = 0, samples = 0, edges = 0, totalStalls = 0;
    int inFrame = 0, nframes = 0, idle = -1;
    hp = malloc(sizeof(uint32_t) * 400000);
    uint64_t minHigh = ~0ull, maxHigh = 0, hiSum = 0, riseAt = 0; long hiN = 0;
    // Frame boundary = a level held longer than gap_ns between two observed edges. If the sampler is preempted
    // (single core shared with fppd) a frame can fragment into shorter pieces, so callers should rely on the
    // LONGEST frames (an intact frame is never longer than the truth) and ignore the shorter ones.
    while (1) {
        int v = (*din & m) != 0; uint64_t t = now_ns(); samples++; seen[v]++;
        if (t - prevT > 20000) totalStalls++;
        prevT = t;
        if (v != last) {
            edges++;
            if (inFrame && t - lastEdge > (uint64_t)gap_ns) {
                printf("frame %d start=%.3fms dur=%.1fus rises=%ld period=%.2fms idle=%d stalls=0\n", nframes, (frameStart - t0) / 1e6,
                       (frameLast - frameStart) / 1e3, rises, nframes ? (frameStart - prevStart) / 1e6 : 0.0, idle);
                prevStart = frameStart; nframes++; inFrame = 0; rises = 0;
            }
            if (!inFrame) { inFrame = 1; frameStart = t; rises = 0; idle = last; }
            if (v) { rises++; riseAt = t; }
            else if (riseAt) { uint64_t h = t - riseAt; if (h < 5000 && hpn < 400000) hp[hpn++] = (uint32_t)h; hiSum += h; hiN++; if (h < minHigh) minHigh = h; if (h > maxHigh) maxHigh = h; }
            frameLast = t; lastEdge = t; last = v;
        }
        if (t > end && !inFrame) break;
        if (t > end + 200000000ull) break;
    }
    printf("stalls=%ld samples=%ld edges=%ld seen0=%d seen1=%d avg_sample=%.0fns\n", totalStalls, samples, edges, seen[0], seen[1], (double)(now_ns() - t0) / samples);
    if (hiN) printf("high pulses: n=%ld min=%.0fns avg=%.0fns max=%.0fns\n", hiN, (double)minHigh, (double)hiSum / hiN, (double)maxHigh);
    if (hpn > 30) {   // pulse-width clusters: sorted, mean of the shortest/longest thirds (for a 2:1 zero:one pattern, see live_custom.py)
        qsort(hp, hpn, sizeof(uint32_t), cmpu);
        double a = 0, b = 0, c = 0, d = 0; long n1 = hpn / 3, n2 = hpn - n1;
        for (long i = 0; i < n1; i++) a += hp[i];
        for (long i = n1; i < hpn; i++) b += hp[i];
        long m1 = hpn - n1, m2 = n1;
        for (long i = 0; i < m1; i++) c += hp[i];
        for (long i = m1; i < hpn; i++) d += hp[i];
        printf("clusters: n=%ld lo_third=%.0f hi_two_thirds=%.0f lo_two_thirds=%.0f hi_third=%.0f p5=%u p95=%u\n", hpn, a / n1, b / n2, c / m1, d / m2, hp[hpn / 20], hp[hpn - 1 - hpn / 20]);
    }
    return 0;
}
