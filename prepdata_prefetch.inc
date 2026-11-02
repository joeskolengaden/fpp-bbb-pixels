void BBB48StringOutput::prepData(FrameData& d, unsigned char* channelData) {
    // [fpp-bbb-pixels] Prefetching gather. The Cortex-A8 has no L1 hardware prefetcher and every miss goes to DDR
    // (~300 ns on the AM335x), and this loop streams a 4-byte channel map entry plus a channel byte per output byte
    // from DDR. Prefetching the map ahead of use takes the loop from ~30 to ~20 ns/byte (measured, 48 x 1500 px).
    // The LUT pointer is hoisted per virtual string. Output is byte-for-byte identical to the stock loop.
    uint8_t* out = d.curData;
    const int numStrings = d.gpioStringMap.size();
    for (int s = 0; s < numStrings; s++) {
        int idx = d.gpioStringMap[s];
        if (idx < 0) {
            continue;
        }
        PixelString* ps = m_strings[idx];
        const int* map = ps->m_outputMap.data();
        uint8_t* c = out + s;
        for (auto& vs : ps->m_virtualStrings) {
            const uint8_t* brightness = vs.brightnessMap;
            const int vsChans = (vs.startNulls + vs.pixelCount + vs.endNulls) * vs.channelsPerNode();
            for (int k = 0; k < vsChans; k++) {
                __builtin_prefetch(map + 32); // a hint: harmless past the end of the map
                *c = brightness[channelData[*map++]];
                c += numStrings;
            }
        }
    }
}
