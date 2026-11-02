// [fpp-bbb-pixels hwtest] Duty cycle of one BeagleBone output pad while the PRU sends a frame, from the GPIO input register.
//
// pinprobe.c timestamps every sample; on this CPU clock_gettime costs ~1 us, which is far too coarse for 250-900 ns pulses.
// Here the loop only reads the register and counts: samples that fall in a "high" or "low" run shorter than the gap limit are
// data (counted as hi / lo); a run longer than the gap limit is the idle gap between frames and is skipped. For an all-zero
// or all-one test pattern the high fraction of the data samples is T0H/period or T1H/period (T1H for ones). The
// sample phase is random relative to the waveform (the loop is interrupted by the scheduler and the bus), so the average
// is unbiased; the bit period itself comes from the frame duration measured by pinprobe.
//
// usage: pinduty [ms=1200] [bankBase=0x481AC000] [bit=25] [gap_us=15] [spin=0]
//   spin = busy-loop iterations between reads: fewer reads per second means less bus contention with the PRU's own GPIO writes
//   prints: duty hi=<n> lo=<n> frac=<hi/(hi+lo)> interval_ns=<mean sample interval> frames=<n> idle=<level during the gaps>
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <time.h>
#include <unistd.h>
#include <sys/resource.h>

static inline uint64_t now_ns(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return (uint64_t)t.tv_sec * 1000000000ull + t.tv_nsec; }

int main(int argc, char** argv) {
    int ms = argc > 1 ? atoi(argv[1]) : 1200;
    uint32_t base = argc > 2 ? (uint32_t)strtoul(argv[2], 0, 0) : 0x481AC000;
    int bit = argc > 3 ? atoi(argv[3]) : 25;
    double gap_us = argc > 4 ? atof(argv[4]) : 15.0;
    int spin = argc > 5 ? atoi(argv[5]) : 0;
    setpriority(PRIO_PROCESS, 0, -5);
    mlockall(MCL_CURRENT | MCL_FUTURE);
    int fd = open("/dev/mem", O_RDONLY | O_SYNC);
    if (fd < 0) { perror("open /dev/mem"); return 2; }
    volatile uint32_t* g = mmap(0, 4096, PROT_READ, MAP_SHARED, fd, base);
    if (g == MAP_FAILED) { perror("mmap"); return 3; }
    volatile uint32_t* din = g + (0x138 / 4);
    const uint32_t m = 1u << bit;

    // calibrate the sample interval on 200k reads
    uint64_t c0 = now_ns(); uint32_t sink = 0;
    for (int i = 0; i < 200000; i++) { sink += *din; for (volatile int q = 0; q < spin; q++) { } }
    double interval = (double)(now_ns() - c0) / 200000.0;
    long gapN = (long)(gap_us * 1000.0 / interval) + 1;

    long hi = 0, lo = 0, run = 0, frames = 0, samples = 0, idleHi = 0, idleLo = 0;
    int last = (*din & m) != 0;
    uint64_t end = now_ns() + (uint64_t)ms * 1000000ull;
    int inGap = 0;
    static double dur[8192]; long nd = 0; uint64_t tStart = 0;       // frame durations: a clock read only at each frame edge
    while (1) {
        for (int k = 0; k < 4096; k++) {
            int v = (*din & m) != 0;
            for (volatile int q = 0; q < spin; q++) { }
            samples++;
            if (v == last) {
                run++;
                if (run == gapN && !inGap) {    // the current run is long enough to be idle: take its samples back out
                    inGap = 1;
                    if (last) { hi -= run - 1; idleHi++; } else { lo -= run - 1; idleLo++; }
                    frames++;
                    if (tStart && nd < 8192) { dur[nd++] = (double)(now_ns() - (uint64_t)(gapN * interval) - tStart); }
                    tStart = 0;
                }
                if (run < gapN) { if (v) hi++; else lo++; }
            } else {
                if (inGap) tStart = now_ns();
                last = v; run = 1; inGap = 0;
                if (v) hi++; else lo++;
            }
        }
        if (now_ns() > end) break;
    }
    (void)sink;
    double best = 0; long good = 0;
    for (long i = 0; i < nd; i++) if (dur[i] > best) best = dur[i];
    double sum = 0; for (long i = 0; i < nd; i++) if (dur[i] > 0.97 * best) { sum += dur[i]; good++; }
    printf("frame_dur_us=%.2f intact=%ld of %ld\n", good ? sum / good / 1000.0 : 0.0, good, nd);
    printf("duty hi=%ld lo=%ld frac=%.4f interval_ns=%.0f samples=%ld frames=%ld idle=%d\n", hi, lo, (double)hi / (double)(hi + lo > 0 ? hi + lo : 1),
           interval, samples, frames, idleHi > idleLo ? 1 : 0);
    return 0;
}
