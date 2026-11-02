// [fpp-bbb-pixels hwtest] Measure the real time the SPI path needs to push a frame, the way SPIPixels does
// (spiFormat() frame, 4096-byte spidev chunks). usage: spibench <dev> <protocol> <pixels> <speed_hz> [frames=20]
#include "SPIChipFormat.h"
#include <fcntl.h>
#include <linux/spi/spidev.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/ioctl.h>
#include <time.h>
#include <unistd.h>
#include <vector>
static double now_ms() { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec * 1e3 + t.tv_nsec / 1e6; }
int main(int argc, char** argv) {
    if (argc < 5) return 2;
    uint32_t dsp; SPIChip chip = spiChipFromString(argv[2], dsp);
    int n = atoi(argv[3]); uint32_t speed = (uint32_t)atoi(argv[4]); int frames = argc > 5 ? atoi(argv[5]) : 20;
    int fd = open(argv[1], O_RDWR); if (fd < 0) { perror("open"); return 3; }
    uint8_t mode = 0, bits = 8;
    ioctl(fd, SPI_IOC_WR_MODE, &mode); ioctl(fd, SPI_IOC_WR_BITS_PER_WORD, &bits); ioctl(fd, SPI_IOC_WR_MAX_SPEED_HZ, &speed);
    std::vector<uint8_t> rgb((size_t)n * 3), wire(spiWireSize(chip, n) + 16);
    for (size_t i = 0; i < rgb.size(); i++) rgb[i] = (uint8_t)(0x11 * (1 + i % 3));
    size_t len = spiFormat(chip, rgb.data(), n, wire.data());
    double sum = 0, mx = 0; int fails = 0;
    for (int f = 0; f < frames; f++) {
        double t0 = now_ms();
        for (size_t off = 0; off < len;) {
            size_t c = len - off < 4096 ? len - off : 4096;
            struct spi_ioc_transfer tr = {}; tr.tx_buf = (unsigned long)(wire.data() + off); tr.len = (uint32_t)c; tr.speed_hz = speed; tr.bits_per_word = 8;
            if (ioctl(fd, SPI_IOC_MESSAGE(1), &tr) < 1) { fails++; break; }
            off += c;
        }
        double d = now_ms() - t0; sum += d; if (d > mx) mx = d;
    }
    printf("{\"dev\":\"%s\",\"protocol\":\"%s\",\"pixels\":%d,\"speed_hz\":%u,\"bytes\":%zu,\"nominal_ms\":%.3f,\"avg_ms\":%.3f,\"max_ms\":%.3f,\"fails\":%d}\n",
           argv[1], argv[2], n, speed, len, len * 8.0 * 1000.0 / speed, sum / frames, mx, fails);
    return 0;
}
