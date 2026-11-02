# Makefile for the FPP "SPIPixels" channel output.
#
#   make / make clean    build / remove the channel-output shared library
# Override FPPDIR if FPP is not at /opt/fpp:  make FPPDIR=/path/to/fpp
#
# Produces libfpp-co-SPIPixels.so. fppd dlopen()s this by name when a channel
# output of type "SPIPixels" is configured, so it must end up on the dynamic
# linker search path (fpp_install.sh copies it to /usr/local/lib + ldconfig).

PLUGIN  := SPIPixels
FPPDIR  ?= /opt/fpp
SRCDIR  ?= $(FPPDIR)/src

UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Darwin)
  # Local syntax/compile check only - the real build happens on the Pi/BBB.
  SHLIB_EXT   := .dylib
  SHLIB_FLAGS := -dynamiclib -undefined dynamic_lookup
  CXX         ?= clang++
else
  SHLIB_EXT   := .so
  SHLIB_FLAGS := -shared
  CXX         ?= g++
endif

TARGET  := libfpp-co-$(PLUGIN)$(SHLIB_EXT)
CXXOBJS := src/SPIPixels.o

CXXFLAGS += -std=gnu++2a -fPIC -O2 -Wall -fvisibility=default -I$(SRCDIR)
CXXFLAGS += $(shell pkg-config --cflags jsoncpp 2>/dev/null)

.PHONY: all clean
all: $(TARGET)

$(TARGET): $(CXXOBJS)
	$(CXX) $(SHLIB_FLAGS) -o $@ $(CXXOBJS) -lpthread

src/%.o: src/%.cpp
	$(CXX) $(CXXFLAGS) -c -o $@ $<

clean:
	rm -f $(CXXOBJS) $(TARGET)
