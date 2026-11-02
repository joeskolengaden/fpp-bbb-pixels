// [fpp-bbb-pixels self-test] Proves the prefetching prepData is byte-identical to the stock/hoisted loop on random strings
// (mixed virtual-string lengths, nulls, null strings, different per-string LUTs) and benchmarks both.
//   g++ -O2 -std=gnu++14 test_prepdata.cpp -o /tmp/prep && /tmp/prep
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <chrono>
#include <vector>
#include <fcntl.h>
#include <sys/mman.h>
#include <unistd.h>
struct VS { int startNulls, pixelCount, endNulls, cpn; uint8_t brightnessMap[256]; int channelsPerNode() const { return cpn; } };
struct PixelString { std::vector<int> m_outputMap; std::vector<VS> m_virtualStrings; int m_outputChannels = 0; };
struct FrameData { uint8_t* curData; std::vector<int> gpioStringMap; };
struct BBB48StringOutput { std::vector<PixelString*> m_strings; void prepData(FrameData&, unsigned char*); void prepDataRef(FrameData&, unsigned char*); };
void BBB48StringOutput::prepDataRef(FrameData& d, unsigned char* channelData) {   // the hoisted loop, as shipped before
    uint8_t* out = d.curData; int numStrings = d.gpioStringMap.size();
    for (int s = 0; s < numStrings; s++) {
        int idx = d.gpioStringMap[s];
        if (idx >= 0) {
            PixelString* ps = m_strings[idx]; uint8_t* c = out + s; int inCh = 0;
            for (auto& vs : ps->m_virtualStrings) {
                const uint8_t* brightness = vs.brightnessMap;
                int vsChans = (vs.startNulls + vs.pixelCount + vs.endNulls) * vs.channelsPerNode();
                for (int k = 0; k < vsChans; k++) { *c = brightness[channelData[ps->m_outputMap[inCh++]]]; c += numStrings; }
            }
        }
    }
}
#include "prepdata_prefetch.inc"
static double now() { return std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count(); }
int main() {
    srand(42); int bad = 0;
    for (int trial = 0; trial < 300; trial++) {
        BBB48StringOutput o; int ns = 1 + rand() % 50; FrameData d; std::vector<int> lens(ns);
        int maxLen = 0;
        for (int s = 0; s < ns; s++) {
            if (rand() % 8 == 0) { d.gpioStringMap.push_back(-1); continue; }
            PixelString* ps = new PixelString; int nv = rand() % 4;                       // 0..3 virtual strings
            int total = 0;
            for (int v = 0; v < nv; v++) {
                VS vs; vs.cpn = 1 + rand() % 8; vs.startNulls = rand() % 3; vs.endNulls = rand() % 3; vs.pixelCount = rand() % 40;
                for (int i = 0; i < 256; i++) vs.brightnessMap[i] = (uint8_t)(rand() % 256);
                total += (vs.startNulls + vs.pixelCount + vs.endNulls) * vs.cpn; ps->m_virtualStrings.push_back(vs);
            }
            for (int i = 0; i < total; i++) ps->m_outputMap.push_back(rand() % 1000);
            ps->m_outputChannels = total; if (total > maxLen) maxLen = total;
            o.m_strings.push_back(ps); d.gpioStringMap.push_back((int)o.m_strings.size() - 1);
        }
        std::vector<uint8_t> chan(1000); for (auto& c : chan) c = rand();
        std::vector<uint8_t> a((size_t)ns * maxLen + 64, 0), b = a;   // the PRU buffer is zeroed at start-up (BBBPruUtils memset)
        d.curData = a.data(); o.prepDataRef(d, chan.data()); d.curData = b.data(); o.prepData(d, chan.data());
        if (a != b) { bad++; printf("MISMATCH trial %d (ns=%d maxLen=%d)\n", trial, ns, maxLen); }
        for (auto p : o.m_strings) delete p;
    }
    printf("equivalence: %s (300 random configurations)\n", bad ? "FAILED" : "identical");
    // benchmark: 48 strings x 1500 px x {3,4,8} bytes/px, one virtual string each
    for (int bpp : {3, 4, 8}) {
        BBB48StringOutput o; FrameData d; int len = 1500 * bpp;
        for (int s = 0; s < 48; s++) {
            PixelString* ps = new PixelString; VS vs; vs.cpn = bpp; vs.startNulls = vs.endNulls = 0; vs.pixelCount = 1500;
            for (int i = 0; i < 256; i++) vs.brightnessMap[i] = i;
            ps->m_virtualStrings.push_back(vs); for (int i = 0; i < len; i++) ps->m_outputMap.push_back(s * len / 2 + i / 2);   // 16-bit-ish doubling
            o.m_strings.push_back(ps); d.gpioStringMap.push_back(s);
        }
        std::vector<uint8_t> chan(48 * len), out((size_t)48 * len); for (auto& c : chan) c = rand();
        d.curData = out.data();
        const char* ddrEnv = getenv("FBP_DDR");                       // FBP_DDR=1: write to the real PRU DDR window (run on the board)
        if (ddrEnv) { int fd = open("/dev/mem", O_RDWR); uint8_t* base = (uint8_t*)mmap(0, 0x400000, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0x8f000000); if (base != MAP_FAILED) d.curData = base + 0x300000; }
        double t0 = now(); for (int i = 0; i < 20; i++) o.prepDataRef(d, chan.data()); double t1 = now();
        for (int i = 0; i < 20; i++) o.prepData(d, chan.data()); double t2 = now();
        printf("48 x 1500 px x %d B/px (%d KB/frame, %s): stock-hoisted %.2f ms, prefetch %.2f ms  (%.1fx)\n", bpp, 48 * len / 1000, getenv("FBP_DDR") ? "PRU DDR window" : "cached memory", (t1 - t0) * 50, (t2 - t1) * 50, (t1 - t0) / (t2 - t1));
    }
    return bad ? 1 : 0;
}
