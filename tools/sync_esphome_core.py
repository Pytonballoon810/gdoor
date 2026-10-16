#!/usr/bin/env python3
# This file is part of the GDoor distribution (https://github.com/gdoor-org).
# Copyright (c) 2024 GDoor authors.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
"""
Copies the bus core of the Arduino firmware into the ESPHome component.

ESPHome only compiles source files that live inside the component directory,
so the component carries copies of the core files. The Arduino firmware in
firmware/esp32/gdoor/src is the single source of truth; edit it there and run

    python tools/sync_esphome_core.py

With --check the script only compares and exits with 1 if the copies differ
(used in CI so the two can not drift apart).
"""
import argparse
import filecmp
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "firmware" / "esp32" / "gdoor" / "src"
TARGET = ROOT / "esphome" / "components" / "gdoor"

# Bus encoding/decoding only, the WiFi, MQTT and web config parts are replaced by ESPHome
CORE_FILES = [
    "defines.h",
    "printer_helper.h",
    "gdoor.h",
    "gdoor.cpp",
    "gdoor_data.h",
    "gdoor_data.cpp",
    "gdoor_rx.h",
    "gdoor_rx.cpp",
    "gdoor_tx.h",
    "gdoor_tx.cpp",
    "gdoor_utils.h",
    "gdoor_utils.cpp",
]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="only compare, exit 1 if the copies are out of date")
    args = parser.parse_args()

    stale = [name for name in CORE_FILES
             if not (TARGET / name).exists() or not filecmp.cmp(SOURCE / name, TARGET / name, shallow=False)]

    if args.check:
        for name in stale:
            print(f"out of date: esphome/components/gdoor/{name}")
        if stale:
            print("Run: python tools/sync_esphome_core.py")
            return 1
        print("ESPHome core files are in sync")
        return 0

    for name in stale:
        shutil.copyfile(SOURCE / name, TARGET / name)
        print(f"updated esphome/components/gdoor/{name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
