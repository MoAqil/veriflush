"""Laptop logger for the Rev-B rig running firmware/veriflush/veriflush.ino.

    pip install pyserial
    python firmware/logger.py COM5            # Windows (see Device Manager)  /  /dev/ttyACM0 on Linux

Sends 'S' to start one flush, writes every CSV line to data/raw/rig_<timestamp>.csv and the
verdict to rig_<timestamp>_verdict.txt. Data written by this script are MEASURED on the rig
(not simulated). Record the saline-tracer conductivity separately after the verdict.
STATUS: not run against hardware in this session.
"""
from __future__ import annotations

import sys
import time
from datetime import datetime
from pathlib import Path

import serial  # pyserial

ROOT = Path(__file__).resolve().parents[1]


def main(port: str, baud: int = 115200):
    out = ROOT / "data" / "raw"
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path, verdict_path = out / f"rig_{stamp}.csv", out / f"rig_{stamp}_verdict.txt"
    with serial.Serial(port, baud, timeout=2) as s, open(csv_path, "w", encoding="utf-8") as f:
        time.sleep(2.5)                     # Uno resets when the port opens
        s.reset_input_buffer()
        s.write(b"S")
        f.write("# MEASURED on Rev-B rig, firmware veriflush.ino\n")
        while True:
            line = s.readline().decode(errors="replace").strip()
            if not line:
                continue
            print(line)
            if line.startswith("VERDICT"):
                verdict_path.write_text(line + "\n", encoding="utf-8")
                break
            if line.startswith("WARN"):
                with open(verdict_path.with_suffix(".warnings.txt"), "a", encoding="utf-8") as w:
                    w.write(line + "\n")
            elif not line.startswith("#"):
                f.write(line + "\n")
    print(f"saved {csv_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: python firmware/logger.py <serial port>")
    main(sys.argv[1])
