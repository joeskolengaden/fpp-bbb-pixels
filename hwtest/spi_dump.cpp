// [fpp-bbb-pixels hwtest] Native dump of the SPIPixels framing: spi_dump <protocol> <pixels> <hex rgb bytes>
// Prints the exact wire bytes plugins/SPIPixels/src/SPIChipFormat.h produces.
#include "SPIChipFormat.h"
#include <cstdio>
#include <cstdlib>
#include <vector>
int main(int argc, char** argv) {
    if (argc < 4) return 2;
    uint32_t sp; SPIChip chip = spiChipFromString(argv[1], sp);
    if (chip == SPIChip::UNKNOWN) { printf("UNKNOWN\n"); return 0; }
    int n = atoi(argv[2]);
    std::vector<uint8_t> rgb;
    for (const char* p = argv[3]; p[0] && p[1]; p += 2) { char b[3] = {p[0], p[1], 0}; rgb.push_back((uint8_t)strtoul(b, nullptr, 16)); }
    if ((int)rgb.size() < n * 3) return 3;
    std::vector<uint8_t> out(spiWireSize(chip, n) + 16, 0xEE);
    size_t w = spiFormat(chip, rgb.data(), n, out.data());
    if (w != spiWireSize(chip, n)) { printf("SIZEMISMATCH %zu %zu\n", w, spiWireSize(chip, n)); return 0; }
    for (size_t i = 0; i < w; i++) printf("%02X", out[i]);
    printf(" %u\n", sp);
    return 0;
}
