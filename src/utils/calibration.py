"""Interactive color calibration helpers for the WRO 2026 FE vehicle.

This module exposes two public helpers:

``load_calibration``
    Used by ``src/main.py`` to fetch the last saved HSV ranges.

``interactive_calibration``
    Launches a trackbar based OpenCV UI to tune HSV values live.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Tuple

import cv2
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
CALIBRATION_DIR = Path(__file__).resolve().parent
CALIBRATION_FILE = CALIBRATION_DIR / "calibration_data.json"

# Default HSV ranges (H, S, V) tuned for a reasonably lit indoor field.
DEFAULT_RANGES: Dict[str, Tuple[Tuple[int, int, int], Tuple[int, int, int]]] = {
    "red": ((0, 140, 120), (10, 255, 255)),
    "green": ((35, 60, 120), (85, 255, 255)),
    "magenta": ((140, 80, 120), (170, 255, 255)),
}


@dataclass
class HSVRange:
    name: str
    lower: Tuple[int, int, int]
    upper: Tuple[int, int, int]

    def to_dict(self) -> Dict[str, Tuple[int, int, int]]:
        return {"lower": self.lower, "upper": self.upper}


def load_calibration(path: Path | None = None) -> Dict[str, HSVRange]:
    """Return persisted HSV ranges or fallback to defaults."""
    target = path or CALIBRATION_FILE
    if not target.exists():
        return {name: HSVRange(name, *bounds) for name, bounds in DEFAULT_RANGES.items()}

    with target.open("r", encoding="utf-8") as stream:
        payload = json.load(stream)

    ranges: Dict[str, HSVRange] = {}
    for name, bounds in payload.items():
        lower = tuple(bounds["lower"])  # type: ignore[arg-type]
        upper = tuple(bounds["upper"])
        ranges[name] = HSVRange(name, lower, upper)  # type: ignore[arg-type]
    return ranges


def save_calibration(ranges: Iterable[HSVRange], path: Path | None = None) -> None:
    """Persist HSV ranges as JSON."""
    target = path or CALIBRATION_FILE
    data = {item.name: item.to_dict() for item in ranges}
    with target.open("w", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2)


# --- Interactive helper ---------------------------------------------------- #

def _create_trackbars(window: str) -> None:
    cv2.createTrackbar("H low", window, 0, 180, lambda _: None)
    cv2.createTrackbar("S low", window, 0, 255, lambda _: None)
    cv2.createTrackbar("V low", window, 0, 255, lambda _: None)
    cv2.createTrackbar("H high", window, 180, 180, lambda _: None)
    cv2.createTrackbar("S high", window, 255, 255, lambda _: None)
    cv2.createTrackbar("V high", window, 255, 255, lambda _: None)


def _read_trackbars(window: str) -> Tuple[np.ndarray, np.ndarray]:
    lower = np.array(
        [
            cv2.getTrackbarPos("H low", window),
            cv2.getTrackbarPos("S low", window),
            cv2.getTrackbarPos("V low", window),
        ]
    )
    upper = np.array(
        [
            cv2.getTrackbarPos("H high", window),
            cv2.getTrackbarPos("S high", window),
            cv2.getTrackbarPos("V high", window),
        ]
    )
    return lower, upper


def interactive_calibration(camera_index: int = 0) -> None:
    """Launch an OpenCV window with trackbars to tune HSV thresholds."""
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        raise RuntimeError("Could not open camera. Check connections and permissions.")

    window = "HSV Calibration"
    cv2.namedWindow(window)
    _create_trackbars(window)

    print("Press 's' to save the current values, 'q' to quit without saving.")
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError("Failed to read frame from camera.")

            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            lower, upper = _read_trackbars(window)
            mask = cv2.inRange(hsv, lower, upper)
            cv2.imshow(window, mask)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            if key == ord("s"):
                ranges = [
                    HSVRange("custom", tuple(lower.tolist()), tuple(upper.tolist()))
                ]
                save_calibration(ranges)
                print(f"Saved HSV values to {CALIBRATION_FILE.relative_to(REPO_ROOT)}")
    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    interactive_calibration()
