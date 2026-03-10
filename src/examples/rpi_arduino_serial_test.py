#!/usr/bin/env python3
"""Quick Raspberry Pi -> Arduino serial test for WRO FE vehicle.

Usage example:
    python3 src/examples/rpi_arduino_serial_test.py --port /dev/ttyACM0
"""

from __future__ import annotations

import argparse
import time

import serial


def run_test(port: str, baud: int, delay: float, repeats: int) -> None:
    sequence = [
        "S90",    # center steering
        "T1500",  # neutral throttle
        "T1600",  # small forward throttle
        "S60",    # left steer
        "S120",   # right steer
        "S90",    # center again
        "T1500",  # stop / neutral
    ]

    with serial.Serial(port, baud, timeout=1) as link:
        time.sleep(2.0)  # allow Arduino reset

        print(f"Connected to {port} @ {baud}")
        print(f"Starting command sequence ({repeats} cycle(s))...\n")

        for cycle in range(1, repeats + 1):
            print(f"--- Cycle {cycle}/{repeats} ---")
            for cmd in sequence:
                link.write((cmd + "\n").encode("utf-8"))
                print(f">>> {cmd}")
                time.sleep(delay)

                line = link.readline().decode("utf-8", errors="ignore").strip()
                if line:
                    print(f"<<< {line}")

        print("\nDone. If steering and throttle reacted, link is good.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test serial link with Arduino motor_control.ino")
    parser.add_argument(
        "--port",
        required=True,
        help="Serial port (Pi/Linux: /dev/ttyACM0, Windows: COM3)",
    )
    parser.add_argument("--baud", type=int, default=115200, help="Serial baud rate")
    parser.add_argument("--delay", type=float, default=0.8, help="Delay between commands (seconds)")
    parser.add_argument("--repeats", type=int, default=1, help="How many times to repeat the full sequence")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_test(port=args.port, baud=args.baud, delay=args.delay, repeats=max(1, args.repeats))
