#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Basic color detection and command bridge for WRO Future Engineers 2026.

This script runs on Raspberry Pi, detects red/green/magenta pillars, decides a
simple action, and sends S/T protocol commands to Arduino.
"""

from __future__ import annotations

import argparse
import time
from dataclasses import dataclass
from typing import Optional, Tuple

import cv2
import numpy as np
import serial

DEFAULT_SERIAL_PORT = "/dev/ttyACM0"
DEFAULT_BAUD_RATE = 115200
DEFAULT_CAMERA_INDEX = 0
FRAME_WIDTH = 320
FRAME_HEIGHT = 240
MIN_CONTOUR_AREA = 500


@dataclass(frozen=True)
class ColorRange:
    lower1: np.ndarray
    upper1: np.ndarray
    lower2: Optional[np.ndarray] = None
    upper2: Optional[np.ndarray] = None


COLOR_RANGES = {
    "red": ColorRange(
        lower1=np.array([0, 100, 100]),
        upper1=np.array([10, 255, 255]),
        lower2=np.array([160, 100, 100]),
        upper2=np.array([179, 255, 255]),
    ),
    "green": ColorRange(
        lower1=np.array([40, 50, 50]),
        upper1=np.array([80, 255, 255]),
    ),
    "magenta": ColorRange(
        lower1=np.array([140, 50, 50]),
        upper1=np.array([170, 255, 255]),
    ),
}

# High-level action to low-level Arduino protocol mapping.
ACTION_TO_SERIAL = {
    "FORWARD": ("S90", "T1600"),
    "LEFT": ("S60", "T1550"),
    "RIGHT": ("S120", "T1550"),
    "STOP": ("T1500", "S90"),
}


def create_camera(camera_index: int) -> cv2.VideoCapture:
    cap = cv2.VideoCapture(camera_index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    if not cap.isOpened():
        raise RuntimeError(f"Camera index {camera_index} could not be opened.")
    return cap


def create_serial_link(port: str, baud_rate: int) -> Optional[serial.Serial]:
    try:
        link = serial.Serial(port, baud_rate, timeout=1)
        time.sleep(2)  # wait for Arduino auto-reset on serial open
        print(f"Connected to Arduino on {port} @ {baud_rate}")
        return link
    except serial.SerialException as exc:
        print(f"Could not connect to Arduino ({port}): {exc}")
        return None


def detect_color(frame: np.ndarray, color_range: ColorRange) -> np.ndarray:
    """Return binary mask for one color (supports optional second HSV band)."""
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask1 = cv2.inRange(hsv, color_range.lower1, color_range.upper1)
    if color_range.lower2 is not None and color_range.upper2 is not None:
        mask2 = cv2.inRange(hsv, color_range.lower2, color_range.upper2)
        return cv2.bitwise_or(mask1, mask2)
    return mask1


def find_largest_contour_center(mask: np.ndarray) -> Optional[Tuple[int, int]]:
    """Find largest contour center in mask if area is above threshold."""
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    contour = max(contours, key=cv2.contourArea)
    if cv2.contourArea(contour) <= MIN_CONTOUR_AREA:
        return None

    moments = cv2.moments(contour)
    if moments["m00"] == 0:
        return None

    cx = int(moments["m10"] / moments["m00"])
    cy = int(moments["m01"] / moments["m00"])
    return (cx, cy)


def decide_action(
    red_pos: Optional[Tuple[int, int]],
    green_pos: Optional[Tuple[int, int]],
    magenta_pos: Optional[Tuple[int, int]],
) -> str:
    """Simple priority policy for demonstration.

    Priority:
      1) STOP when magenta is detected.
      2) RIGHT when red is detected.
      3) LEFT when green is detected.
      4) FORWARD otherwise.
    """
    if magenta_pos is not None:
        return "STOP"
    if red_pos is not None:
        return "RIGHT"
    if green_pos is not None:
        return "LEFT"
    return "FORWARD"


def send_command(link: Optional[serial.Serial], cmd: str) -> None:
    """Send high-level command to Arduino using S/T payload sequence."""
    if link is None:
        return

    payloads = ACTION_TO_SERIAL.get(cmd, ACTION_TO_SERIAL["STOP"])
    for payload in payloads:
        link.write((payload + "\n").encode("utf-8"))
        print(f"Sent: {payload} ({cmd})")
        time.sleep(0.01)


def run_dry_test() -> None:
    """Quick no-hardware test for action mapping and payloads."""
    samples = [
        (None, None, None),
        ((10, 20), None, None),
        (None, (10, 20), None),
        (None, None, (10, 20)),
    ]
    print("Dry test results:")
    for red, green, magenta in samples:
        action = decide_action(red, green, magenta)
        print(f"  red={red}, green={green}, magenta={magenta} -> {action} -> {ACTION_TO_SERIAL[action]}")


def run_main_loop(camera_index: int, port: str, baud_rate: int, no_serial: bool) -> None:
    cap = create_camera(camera_index)
    link = None if no_serial else create_serial_link(port, baud_rate)

    try:
        last_command: Optional[str] = None
        while True:
            ok, frame = cap.read()
            if not ok:
                print("Camera frame capture failed. Exiting loop.")
                break

            # Detect colors
            mask_red = detect_color(frame, COLOR_RANGES["red"])
            mask_green = detect_color(frame, COLOR_RANGES["green"])
            mask_magenta = detect_color(frame, COLOR_RANGES["magenta"])

            # Find centers
            red_center = find_largest_contour_center(mask_red)
            green_center = find_largest_contour_center(mask_green)
            magenta_center = find_largest_contour_center(mask_magenta)

            # Decide and send
            command = decide_action(red_center, green_center, magenta_center)
            if command != last_command:
                send_command(link, command)
                last_command = command

            # Optional overlay for debugging
            if red_center:
                cv2.circle(frame, red_center, 5, (0, 0, 255), -1)
            if green_center:
                cv2.circle(frame, green_center, 5, (0, 255, 0), -1)
            if magenta_center:
                cv2.circle(frame, magenta_center, 5, (255, 0, 255), -1)

            cv2.imshow("Detector", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()
        if link:
            link.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="WRO FE 2026 color detector + Arduino command bridge")
    parser.add_argument("--camera", type=int, default=DEFAULT_CAMERA_INDEX, help="OpenCV camera index")
    parser.add_argument("--port", default=DEFAULT_SERIAL_PORT, help="Serial port (e.g. /dev/ttyACM0 or COM3)")
    parser.add_argument("--baud", type=int, default=DEFAULT_BAUD_RATE, help="Serial baud rate")
    parser.add_argument("--no-serial", action="store_true", help="Run vision only; do not open serial link")
    parser.add_argument("--dry-run", action="store_true", help="Run a no-hardware action mapping test and exit")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.dry_run:
        run_dry_test()
        return
    run_main_loop(args.camera, args.port, args.baud, args.no_serial)


if __name__ == "__main__":
    main()