// [fpp-bbb-pixels hwtest] Dump the exact byte stream the patched PixelString hands the PRU
// for one chip configuration: wire_dump <colorOrder> <pixels> [preambleProfile] [extra-json].
// Source channel n carries the pattern 0x11,0x22,0x33,... (same as the RGBFill test pattern), and
// each output byte is looked up through the string's brightness map exactly as BBB48String does,
// so decoration bytes (preambles/trailers, FPPD_OFF_CHANNEL) come out as their literal values.
#include "channeloutput/PixelString.h"
#include "Sequence.h"
#include <jsoncpp/json/json.h>
#include <cstdio>
#include <cstdlib>
int main(int argc, char** argv) {
    if (argc < 3) { fprintf(stderr, "usage: wire_dump <order> <pixels> [profile]\n"); return 2; }
    int pix = atoi(argv[2]);
    Json::Value c; c["portNumber"] = 0;
    if (argc > 3 && argv[3][0]) c["preambleProfile"] = argv[3];
    if (argc > 4 && argv[4][0]) {                       // extra per-string config keys, e.g. {"chipCurrent":50}
        Json::Value extra; Json::Reader rd;
        if (rd.parse(argv[4], extra)) for (auto& k : extra.getMemberNames()) c[k] = extra[k];
    }
    Json::Value vs; vs["startChannel"] = 0; vs["pixelCount"] = pix;
    vs["brightness"] = 100; vs["gamma"] = "1.0"; vs["colorOrder"] = argv[1];
    c["virtualStrings"].append(vs);
    PixelString* ps = new PixelString(true); ps->Init(c);
    static const unsigned char pat[3] = {0x11, 0x22, 0x33};
    for (int i = 0; i < ps->m_outputChannels; i++) {
        int src = ps->m_outputMap[i];
        unsigned char v = (src == FPPD_OFF_CHANNEL) ? 0 : pat[src % 3];
        printf("%02X ", ps->m_brightnessMaps[i][v]);
    }
    printf("\n");
    return 0;
}
