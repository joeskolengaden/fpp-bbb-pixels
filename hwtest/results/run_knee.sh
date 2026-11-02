#!/bin/bash
cd "$(dirname "$0")/.."
python3 measure_limits.py --case normal-grb --pixels 1560,1600,1640,1700,2000 --out results/knee-normal.json
python3 measure_limits.py --case ws2811-400 --pixels 780,820,860,900 --out results/knee-ws2811-400.json
python3 measure_limits.py --case normal-grb --pixels 400,1000,1500,1600 --ports 48 --out results/allports-normal.json
echo KNEE-DONE
