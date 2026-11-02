## SPI chips at 1,500 px per output (BeagleBone Green, 4 spidev chip-selects on 2 buses)

Each cell: ✅/❌ cadence held · SPI send ms per frame (all outputs, they are sent one after another) · fppd CPU · achieved fps · late frames in 6 s.

| chip | clock | wire bytes @1,500 px | outputs | 20 fps (50 ms) | 30 fps (33 ms) | 40 fps (25 ms) |
|---|---|---|---|---|---|---|
| apa102 | 8 MHz | 6098 | 1 | ✅ 7.87 ms · 3.4% · 20.0 fps · 0 late | ✅ 7.81 ms · 4.6% · 30.2 fps · 0 late | ✅ 7.88 ms · 5.4% · 39.9 fps · 0 late |
|  | 8 MHz | 6098 | 2 | ✅ 15.69 ms · 4.8% · 20.0 fps · 0 late | ✅ 15.59 ms · 6.5% · 30.2 fps · 0 late | ✅ 15.75 ms · 7.9% · 39.9 fps · 0 late |
|  | 8 MHz | 6098 | 4 | ✅ 31.56 ms · 7.7% · 20.0 fps · 0 late | ❌ 31.87 ms · 11.5% · 30.2 fps · 47 late | ❌ 31.71 ms · 14.9% · None fps · 189 late |
| apa102hd | 8 MHz | 6098 | 1 | ✅ 8.02 ms · 4.1% · 20.0 fps · 0 late | ✅ 7.9 ms · 5.3% · 30.2 fps · 0 late | ✅ 8.86 ms · 6.6% · 39.9 fps · 0 late |
|  | 8 MHz | 6098 | 2 | ✅ 16.08 ms · 6.1% · 20.0 fps · 0 late | ✅ 15.84 ms · 8.1% · 30.2 fps · 0 late | ✅ 17.14 ms · 10.1% · 39.9 fps · 1 late |
|  | 8 MHz | 6098 | 4 | ✅ 32.15 ms · 9.9% · 20.0 fps · 0 late | ❌ 31.37 ms · 16.6% · 30.2 fps · 173 late | ❌ 31.71 ms · 17.8% · None fps · 183 late |
| sk9822hd | 8 MHz | 6098 | 1 | ✅ 8.08 ms · 4.2% · 20.0 fps · 0 late | ✅ 7.94 ms · 5.3% · 30.2 fps · 0 late | ✅ 8.05 ms · 6.5% · 39.9 fps · 0 late |
|  | 8 MHz | 6098 | 2 | ✅ 16.18 ms · 6.0% · 20.0 fps · 0 late | ✅ 15.88 ms · 8.2% · 30.2 fps · 0 late | ✅ 15.64 ms · 10.2% · 39.8 fps · 0 late |
|  | 8 MHz | 6098 | 4 | ✅ 31.55 ms · 9.7% · 20.0 fps · 0 late | ❌ 31.44 ms · 16.7% · None fps · 177 late | ❌ 31.7 ms · 18.0% · None fps · 185 late |
| hd107s | 20 MHz | 6098 | 1 | ✅ 4.58 ms · 3.2% · 20.0 fps · 0 late | ✅ 4.55 ms · 4.2% · 30.2 fps · 0 late | ✅ 4.62 ms · 5.3% · 39.9 fps · 0 late |
|  | 20 MHz | 6098 | 2 | ✅ 9.16 ms · 4.8% · 20.0 fps · 0 late | ✅ 8.99 ms · 5.9% · 30.2 fps · 0 late | ✅ 9.07 ms · 7.4% · 39.9 fps · 0 late |
|  | 20 MHz | 6098 | 4 | ✅ 18.2 ms · 7.0% · 20.0 fps · 0 late | ✅ 17.85 ms · 9.4% · 30.2 fps · 0 late | ✅ 19.97 ms · 12.2% · 39.9 fps · 3 late |
| hd108 | 20 MHz | 12770 | 1 | ✅ 9.34 ms · 4.1% · 20.0 fps · 0 late | ✅ 9.35 ms · 5.1% · 30.2 fps · 0 late | ✅ 9.28 ms · 5.8% · 39.9 fps · 0 late |
|  | 20 MHz | 12770 | 2 | ✅ 18.69 ms · 5.2% · 20.0 fps · 0 late | ✅ 18.6 ms · 7.0% · 30.2 fps · 0 late | ✅ 18.85 ms · 8.9% · 40.0 fps · 0 late |
|  | 20 MHz | 12770 | 4 | ✅ 37.62 ms · 8.9% · 20.0 fps · 0 late | ❌ 37.7 ms · 14.6% · None fps · 162 late | ❌ 37.8 ms · 15.4% · None fps · 162 late |
| ws2801 | 1 MHz | 4500 | 1 | ✅ 39.48 ms · 5.4% · 20.0 fps · 0 late | ❌ 39.35 ms · 9.3% · None fps · 158 late | ❌ 39.45 ms · 10.3% · None fps · 158 late |
|  | 1 MHz | 4500 | 2 | ❌ 79.01 ms · 9.0% · None fps · 82 late | ❌ 78.7 ms · 9.9% · None fps · 83 late | ❌ 79.01 ms · 10.1% · None fps · 82 late |
|  | 1 MHz | 4500 | 4 | ❌ 157.79 ms · 9.4% · None fps · 38 late | ❌ 158.19 ms · 10.4% · None fps · 38 late | ❌ 157.85 ms · 11.1% · None fps · 39 late |
| lpd8806 | 2 MHz | 4547 | 1 | ✅ 20.5 ms · 4.6% · 20.0 fps · 0 late | ✅ 20.4 ms · 5.8% · 30.2 fps · 0 late | ✅ 20.48 ms · 7.0% · 39.9 fps · 0 late |
|  | 2 MHz | 4547 | 2 | ✅ 41.19 ms · 6.6% · 20.0 fps · 0 late | ❌ 41.05 ms · 10.7% · None fps · 153 late | ❌ 40.9 ms · 11.3% · None fps · 153 late |
|  | 2 MHz | 4547 | 4 | ❌ 81.8 ms · 10.7% · None fps · 76 late | ❌ 81.93 ms · 11.5% · None fps · 77 late | ❌ 82.1 ms · 11.9% · None fps · 75 late |
| lpd6803 | 1 MHz | 3192 | 1 | ✅ 27.99 ms · 4.2% · 20.0 fps · 0 late | ✅ 27.93 ms · 5.3% · 30.2 fps · 0 late | ❌ 27.91 ms · 9.6% · None fps · 226 late |
|  | 1 MHz | 3192 | 2 | ❌ 55.69 ms · 8.5% · None fps · 114 late | ❌ 55.91 ms · 9.7% · None fps · 117 late | ❌ 55.81 ms · 10.0% · None fps · 115 late |
|  | 1 MHz | 3192 | 4 | ❌ 111.82 ms · 8.8% · None fps · 57 late | ❌ 111.55 ms · 9.5% · None fps · 58 late | ❌ 111.85 ms · 10.2% · None fps · 59 late |
| p9813 | 1 MHz | 6100 | 1 | ❌ 53.35 ms · 8.2% · None fps · 120 late | ❌ 53.28 ms · 8.9% · None fps · 122 late | ❌ 53.25 ms · 9.4% · None fps · 122 late |
|  | 1 MHz | 6100 | 2 | ❌ 106.69 ms · 8.3% · None fps · 61 late | ❌ 106.81 ms · 8.8% · None fps · 61 late | ❌ 106.69 ms · 9.4% · None fps · 61 late |
|  | 1 MHz | 6100 | 4 | ❌ 213.1 ms · 8.5% · 23.3 fps · 29 late | ❌ 213.13 ms · 9.7% · 23.3 fps · 31 late | ❌ 213.31 ms · 10.4% · 23.3 fps · 29 late |
| sm16716 | 16 MHz | 4694 | 1 | ✅ 3.8 ms · 4.2% · 20.0 fps · 0 late | ✅ 3.68 ms · 5.4% · 30.2 fps · 0 late | ✅ 3.82 ms · 6.4% · 39.8 fps · 0 late |
|  | 16 MHz | 4694 | 2 | ✅ 7.75 ms · 6.3% · 20.0 fps · 0 late | ✅ 7.29 ms · 8.5% · 30.2 fps · 0 late | ✅ 7.27 ms · 10.4% · 39.9 fps · 0 late |
|  | 16 MHz | 4694 | 4 | ✅ 15.8 ms · 10.7% · 20.1 fps · 0 late | ✅ 16.02 ms · 15.0% · 30.2 fps · 1 late | ✅ 15.25 ms · 18.9% · 40.0 fps · 0 late |
