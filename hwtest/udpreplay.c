// [fpp-bbb-pixels hwtest] Board-side UDP frame replayer: sends one pre-built frame set (file of [u16 len][bytes]...) to <ip>:<port> at <fps> for <secs>,
// patching the sequence byte each frame. Packets leave in groups of <group> spread over ~80% of the frame, like a real sender on a 100 Mbit link
// (a loopback burst of hundreds of packets would overflow the receive buffer in a way a wire never does).
// usage: udpreplay <file> <ip> <port> <fps> <secs> <seq_offset> <seq_mod> <group> <data_offset> ; prints sent packets and the sender's own CPU seconds
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <time.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <sys/resource.h>
static double now(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec + t.tv_nsec * 1e-9; }
int main(int argc, char** argv) {
    if (argc < 10) return 2;
    FILE* f = fopen(argv[1], "rb"); if (!f) return 3;
    int port = atoi(argv[3]), fps = atoi(argv[4]), seqoff = atoi(argv[6]), seqmod = atoi(argv[7]), group = atoi(argv[8]), hdr = atoi(argv[9]);
    double secs = atof(argv[5]);
    static uint8_t buf[1 << 22]; size_t n = fread(buf, 1, sizeof(buf), f); fclose(f);
    int np = 0; static uint8_t* pk[4096]; static int len[4096];
    for (size_t o = 0; o + 2 <= n;) { int l = buf[o] | (buf[o + 1] << 8); pk[np] = buf + o + 2; len[np++] = l; o += 2 + l; }
    int s = socket(AF_INET, SOCK_DGRAM, 0);
    int sb = 4 << 20; setsockopt(s, SOL_SOCKET, SO_SNDBUF, &sb, sizeof(sb));
    struct sockaddr_in a = {0}; a.sin_family = AF_INET; a.sin_port = htons(port); inet_pton(AF_INET, argv[2], &a.sin_addr);
    connect(s, (struct sockaddr*)&a, sizeof(a));
    double per = 1.0 / fps, t0 = now(), nxt = t0; long sent = 0, frames = 0, late = 0, errs = 0;
    int groups = (np + group - 1) / group;
    while (now() - t0 < secs) {
        int seq = (int)(frames % seqmod) + 1;
        for (int g = 0; g < groups; g++) {
            double due = nxt + per * 0.8 * g / groups;
            double d = due - now();
            if (d > 0) { struct timespec ts = {(time_t)d, (long)((d - (time_t)d) * 1e9)}; nanosleep(&ts, 0); }
            for (int i = g * group; i < np && i < (g + 1) * group; i++) {
                pk[i][seqoff] = (uint8_t)seq;
                pk[i][hdr] ^= 0x5A;                 // data changes every frame, so the PRU copy path runs every frame
                if (send(s, pk[i], len[i], 0) < 0) errs++; else sent++;
            }
        }
        frames++; nxt += per;
        double d = nxt - now();
        if (d > 0) { struct timespec ts = {(time_t)d, (long)((d - (time_t)d) * 1e9)}; nanosleep(&ts, 0); } else { late++; if (d < -per) nxt = now(); }
    }
    struct rusage ru; getrusage(RUSAGE_SELF, &ru);
    printf("{\"sent\":%ld,\"errors\":%ld,\"frames\":%ld,\"late_frames\":%ld,\"elapsed\":%.2f,\"pps\":%.0f,\"pkts_per_frame\":%d,\"sender_cpu_s\":%.2f}\n",
           sent, errs, frames, late, now() - t0, sent / (now() - t0), np, ru.ru_utime.tv_sec + ru.ru_utime.tv_usec * 1e-6 + ru.ru_stime.tv_sec + ru.ru_stime.tv_usec * 1e-6);
    return 0;
}
