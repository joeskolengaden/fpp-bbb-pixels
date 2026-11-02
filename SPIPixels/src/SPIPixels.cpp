/*
 * SPIPixels - FPP channel output for clocked (SPI) LED pixel chips.
 *
 * Drives APA102 / SK9822 / HD107S, WS2801, LPD8806, LPD6803 and P9813 pixels
 * over a standard Linux spidev device (/dev/spidevX.Y).  Because it talks the
 * generic spidev interface it works unchanged on both Raspberry Pi and
 * BeagleBone.
 *
 * It builds as libfpp-co-SPIPixels.so and is loaded by fppd when a channel
 * output of type "SPIPixels" is configured.  The same source compiles against
 * BOTH the FPP 5.4 API and the modern (6.x-9.x) API:
 *
 *   FPP 5.4 : base class ChannelOutputBase, loaded via dlsym("createOutputSPIPixels")
 *   FPP 6+  : base class ChannelOutput,     loaded via dlsym("createPlugin") ->
 *             ChannelOutputPlugin::createChannelOutput()
 *
 * Single-wire chips (WS2811/WS2812/SK6812/TM1814...) are intentionally NOT
 * handled here - those need precise sub-microsecond bit timing that FPP drives
 * from core code (the BeagleBone PRU assembly and the Pi rpi_ws281x library).
 *
 * All per-string smarts (color order, brightness, gamma, grouping, zig-zag,
 * reverse, null pixels) come from FPP's own PixelString class, so behaviour is
 * identical to the built-in pixel string outputs.  This only adds chip framing.
 *
 * Covered under GPL v2 (same terms as FPP's own rpi_ws281x / spixels outputs).
 */

#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <list>
#include <string>
#include <vector>

#include <fcntl.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <linux/spi/spidev.h>
#include <linux/types.h>

// Plugin.h defines FPP_PLUGIN_API_VERSION only on the modern (6.x+) API.
// On 5.4 it just declares the old FPPPlugin base (no channel-output plugins).
#include "Plugin.h"

#if defined(FPP_PLUGIN_API_VERSION)
#define SPIPIXELS_NEW_API 1
#include "channeloutput/ChannelOutput.h"
#include "overlays/PixelOverlay.h"
using FPPOutputBase = ChannelOutput;
#else
#include "channeloutput/ChannelOutputBase.h"
using FPPOutputBase = ChannelOutputBase;
#endif

#include "Sequence.h"
#include "common.h"
#include "log.h"
#include "channeloutput/PixelString.h"

#include "SPIChipFormat.h"

/////////////////////////////////////////////////////////////////////////////

struct SPIPort {
    PixelString* string = nullptr;
    int fd = -1;
    std::string device;
    SPIChip chip = SPIChip::UNKNOWN;
    uint32_t speedHz = 1000000;
    int nPix = 0;
    std::vector<uint8_t> rgb;  // PixelString output: 3 bytes/px, color-ordered
    std::vector<uint8_t> wire; // chip-framed bytes ready for the bus
    size_t wireLen = 0;
    size_t chunk = 4096;        // largest single spidev transfer (kernel spidev.bufsiz)
};

class SPIPixelsOutput : public FPPOutputBase {
public:
    SPIPixelsOutput(unsigned int startChannel, unsigned int channelCount) :
        FPPOutputBase(startChannel, channelCount) {
        LogDebug(VB_CHANNELOUT, "SPIPixelsOutput::SPIPixelsOutput(%u, %u)\n",
                 startChannel, channelCount);
    }

    virtual ~SPIPixelsOutput() {
        for (auto& p : m_ports) {
            if (p.fd >= 0)
                close(p.fd);
            delete p.string;
        }
    }

    int Init(Json::Value config) override {
        LogDebug(VB_CHANNELOUT, "SPIPixelsOutput::Init()\n");

        for (int i = 0; i < (int)config["outputs"].size(); i++) {
            Json::Value s = config["outputs"][i];

            SPIPort port;
            port.string = new PixelString();
            if (!port.string->Init(s)) {
                LogErr(VB_CHANNELOUT, "SPIPixels: PixelString init failed for output %d\n", i);
                delete port.string;
                return 0;
            }
            if (port.string->m_outputChannels == 0) {
                delete port.string; // nothing on this port
                continue;
            }

            std::string protocol = s["protocol"].asString();
            uint32_t def = 1000000;
            port.chip = spiChipFromString(protocol, def);
            if (port.chip == SPIChip::UNKNOWN) {
                LogErr(VB_CHANNELOUT, "SPIPixels: unknown protocol '%s'\n", protocol.c_str());
                delete port.string;
                return 0;
            }
            port.speedHz = (s.isMember("spiSpeed") && s["spiSpeed"].asUInt() > 0)
                               ? s["spiSpeed"].asUInt()
                               : def;

            std::string dev = s["device"].asString();
            if (dev.empty()) {
                LogErr(VB_CHANNELOUT, "SPIPixels: output %d has no 'device'\n", i);
                delete port.string;
                return 0;
            }
            if (dev.rfind("/dev/", 0) != 0) {
                if (dev.rfind("spidev", 0) != 0)
                    dev = "spidev" + dev;
                dev = "/dev/" + dev;
            }
            port.device = dev;

            port.nPix = port.string->m_outputChannels / 3;
            port.rgb.assign(port.string->m_outputChannels, 0);
            port.wireLen = spiWireSize(port.chip, port.nPix);
            port.wire.assign(port.wireLen, 0);
            port.chunk = spidevBufsiz();
            if (port.chip == SPIChip::TLC59711) {
                // the chip latches whenever the clock pauses, so a chain split over several transfers shows a half-updated frame
                port.chunk = std::max<size_t>(28, port.chunk / 28 * 28);
                if (port.wireLen > port.chunk)
                    LogWarn(VB_CHANNELOUT, "SPIPixels: %s: %zu bytes (%d pixels) do not fit one spidev transfer (%zu bytes); the frame will be "
                            "latched in pieces and flicker. Use at most %zu pixels per output, or raise spidev.bufsiz on the kernel command line.\n",
                            protocol.c_str(), port.wireLen, port.nPix, port.chunk, port.chunk / 28 * 4);
            }

            if (!openSPI(port)) {
                delete port.string;
                return 0;
            }

            LogInfo(VB_CHANNELOUT, "SPIPixels: %s on %s, %d pixels @ %u Hz\n",
                    protocol.c_str(), port.device.c_str(), port.nPix, port.speedHz);
            m_ports.push_back(std::move(port));
            m_strings.push_back(m_ports.back().string);
        }

        if (m_ports.empty())
            LogWarn(VB_CHANNELOUT, "SPIPixels: no usable outputs configured\n");

#ifdef SPIPIXELS_NEW_API
        PixelString::AutoCreateOverlayModels(m_strings, m_autoCreatedModelNames);
#else
        PixelString::AutoCreateOverlayModels(m_strings);
#endif
        return FPPOutputBase::Init(config);
    }

    int Close(void) override {
#ifdef SPIPIXELS_NEW_API
        for (auto& n : m_autoCreatedModelNames)
            PixelOverlayManager::INSTANCE.removeAutoOverlayModel(n);
#endif
        for (auto& p : m_ports) {
            if (p.fd >= 0) {
                close(p.fd);
                p.fd = -1;
            }
        }
        return FPPOutputBase::Close();
    }

    void GetRequiredChannelRanges(const std::function<void(int, int)>& addRange) override {
        for (auto& p : m_ports) {
            PixelString* ps = p.string;
            int min = FPPD_MAX_CHANNELS;
            int max = -1;
            for (int c = 0; c < ps->m_outputChannels; c++) {
                int ch = ps->m_outputMap[c];
                if (ch < FPPD_MAX_CHANNELS) {
                    if (ch < min)
                        min = ch;
                    if (ch > max)
                        max = ch;
                }
            }
            if (min <= max)
                addRange(min, max);
        }
    }

    void PrepData(unsigned char* channelData) override {
        for (auto& p : m_ports) {
            PixelString* ps = p.string;
            // Apply the channel map + brightness/gamma exactly like the built-in
            // pixel outputs (this is what PixelString::prepareOutput does on 6+,
            // done inline here so it also works on 5.4 which lacks that helper).
            for (int c = 0; c < ps->m_outputChannels; c++)
                p.rgb[c] = ps->m_brightnessMaps[c][channelData[ps->m_outputMap[c]]];
            spiFormat(p.chip, p.rgb.data(), p.nPix, p.wire.data());
        }
    }

    int SendData(unsigned char* channelData) override {
        for (auto& p : m_ports)
            writeSPI(p);
        return m_channelCount;
    }

private:
    bool openSPI(SPIPort& p) {
        p.fd = open(p.device.c_str(), O_WRONLY);
        if (p.fd < 0) {
            LogErr(VB_CHANNELOUT, "SPIPixels: cannot open %s (is SPI enabled?)\n", p.device.c_str());
            return false;
        }
        uint8_t mode = SPI_MODE_0; // all supported chips: idle-low clock, sample on rising edge
        uint8_t bits = 8;
        if (ioctl(p.fd, SPI_IOC_WR_MODE, &mode) < 0 ||
            ioctl(p.fd, SPI_IOC_WR_BITS_PER_WORD, &bits) < 0 ||
            ioctl(p.fd, SPI_IOC_WR_MAX_SPEED_HZ, &p.speedHz) < 0) {
            LogErr(VB_CHANNELOUT, "SPIPixels: failed to configure %s\n", p.device.c_str());
            close(p.fd);
            p.fd = -1;
            return false;
        }
        return true;
    }

    // the kernel's spidev transfer limit (module parameter bufsiz, 4096 unless raised on the kernel command line)
    static size_t spidevBufsiz() {
        size_t v = 4096;
        if (FILE* f = fopen("/sys/module/spidev/parameters/bufsiz", "r")) {
            unsigned long x = 0;
            if (fscanf(f, "%lu", &x) == 1 && x >= 256)
                v = x;
            fclose(f);
        }
        return v;
    }

    void writeSPI(SPIPort& p) {
        if (p.fd < 0 || p.wireLen == 0)
            return;
        // spidev caps a single transfer at its module bufsiz (default 4096); chunk larger frames.
        const size_t MAXCHUNK = p.chunk;
        size_t off = 0;
        while (off < p.wireLen) {
            size_t n = std::min(MAXCHUNK, p.wireLen - off);
            struct spi_ioc_transfer tr;
            memset(&tr, 0, sizeof(tr));
            tr.tx_buf = (unsigned long)(p.wire.data() + off);
            tr.rx_buf = 0;
            tr.len = (uint32_t)n;
            tr.speed_hz = p.speedHz;
            tr.bits_per_word = 8;
            if (ioctl(p.fd, SPI_IOC_MESSAGE(1), &tr) < 1) {
                ssize_t w = write(p.fd, p.wire.data() + off, n);
                (void)w;
            }
            off += n;
        }
    }

    std::vector<SPIPort> m_ports;
    std::vector<PixelString*> m_strings;
#ifdef SPIPIXELS_NEW_API
    std::list<std::string> m_autoCreatedModelNames;
#endif
};

/////////////////////////////////////////////////////////////////////////////
// Factory entry points - one per FPP API generation.

#ifdef SPIPIXELS_NEW_API

// FPP 6.x - 9.x: fppd loads libfpp-co-SPIPixels.so, calls createPlugin(), and
// uses the ChannelOutputPlugin interface to build the output.
class SPIPixelsPlugin : public FPPPlugins::Plugin, public FPPPlugins::ChannelOutputPlugin {
public:
    SPIPixelsPlugin() :
        FPPPlugins::Plugin("SPIPixels") {}
    ChannelOutput* createChannelOutput(unsigned int startChannel, unsigned int channelCount) override {
        return new SPIPixelsOutput(startChannel, channelCount);
    }
};

extern "C" {
FPPPlugins::Plugin* createPlugin() {
    return new SPIPixelsPlugin();
}
}

#else

// FPP 5.4: fppd loads libfpp-co-SPIPixels.so and calls createOutputSPIPixels().
extern "C" {
ChannelOutputBase* createOutputSPIPixels(unsigned int startChannel, unsigned int channelCount) {
    return new SPIPixelsOutput(startChannel, channelCount);
}
}

#endif
