"""
vision.py – Camera capture and colour/lane detection.

Detects:
  - Red, green, and magenta pillars (for obstacle avoidance / parking).
  - Orange and blue lane lines (for lane following).

Run with ``--calibrate`` to open an interactive HSV tuning window that writes
the final values to ``config/hsv_config.json``.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from dataclasses import dataclass, field
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CONFIG_PATH = os.path.join(_REPO_ROOT, "config", "hsv_config.json")

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class DetectionResult:
    """Contains all detections from a single camera frame."""
    red_area: int = 0
    green_area: int = 0
    magenta_area: int = 0
    lane_offset: float = 0.0        # pixels; negative = left of centre
    frame_width: int = 0
    frame_height: int = 0
    debug_frame: Optional[np.ndarray] = field(default=None, repr=False)


# ---------------------------------------------------------------------------
# HSV config helpers
# ---------------------------------------------------------------------------

def load_hsv_config(path: str = _CONFIG_PATH) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def save_hsv_config(config: dict, path: str = _CONFIG_PATH) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(config, fh, indent=2)
    logger.info("HSV config saved to %s", path)


# ---------------------------------------------------------------------------
# Vision pipeline
# ---------------------------------------------------------------------------

class VisionPipeline:
    """
    Captures frames from the Pi Camera (or a USB webcam) and runs the
    colour-detection and lane-following pipeline.
    """

    # Minimum contour area (pixels²) to count as a valid detection.
    MIN_PILLAR_AREA = 500
    MIN_LANE_AREA = 1000

    def __init__(self, camera_index: int = 0, config_path: str = _CONFIG_PATH):
        self._config = load_hsv_config(config_path)
        self._cap: Optional[cv2.VideoCapture] = None
        self._camera_index = camera_index

    # ------------------------------------------------------------------
    # Camera lifecycle
    # ------------------------------------------------------------------

    def open(self) -> None:
        self._cap = cv2.VideoCapture(self._camera_index)
        if not self._cap.isOpened():
            raise RuntimeError(f"Cannot open camera index {self._camera_index}")
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        logger.info("Camera opened (index=%d)", self._camera_index)

    def close(self) -> None:
        if self._cap:
            self._cap.release()
            logger.info("Camera closed")

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *_):
        self.close()

    # ------------------------------------------------------------------
    # Frame processing
    # ------------------------------------------------------------------

    def read_frame(self) -> Optional[np.ndarray]:
        """Read one frame from the camera. Returns None on failure."""
        if self._cap is None or not self._cap.isOpened():
            return None
        ok, frame = self._cap.read()
        return frame if ok else None

    def process(self, frame: np.ndarray, debug: bool = False) -> DetectionResult:
        """
        Run the full detection pipeline on *frame*.

        Parameters
        ----------
        frame : BGR image (numpy array).
        debug : If True, annotate the frame and attach it to the result.

        Returns
        -------
        DetectionResult with all detections filled in.
        """
        h, w = frame.shape[:2]
        result = DetectionResult(frame_width=w, frame_height=h)

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        debug_frame = frame.copy() if debug else None

        # --- Pillar detection -------------------------------------------------
        result.red_area = self._detect_pillar(
            hsv, "red", debug_frame, color_bgr=(0, 0, 255)
        )
        result.green_area = self._detect_pillar(
            hsv, "green", debug_frame, color_bgr=(0, 255, 0)
        )
        result.magenta_area = self._detect_pillar(
            hsv, "magenta", debug_frame, color_bgr=(255, 0, 255)
        )

        # --- Lane-line offset -------------------------------------------------
        result.lane_offset = self._detect_lane_offset(hsv, w, h, debug_frame)

        if debug:
            result.debug_frame = debug_frame

        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _mask_from_config(self, hsv: np.ndarray, color: str) -> np.ndarray:
        """Build a binary mask for *color* using the loaded HSV config."""
        cfg = self._config[color]
        if "lower1" in cfg:
            # Red wraps around 180; use two ranges.
            m1 = cv2.inRange(
                hsv,
                np.array(cfg["lower1"], dtype=np.uint8),
                np.array(cfg["upper1"], dtype=np.uint8),
            )
            m2 = cv2.inRange(
                hsv,
                np.array(cfg["lower2"], dtype=np.uint8),
                np.array(cfg["upper2"], dtype=np.uint8),
            )
            return cv2.bitwise_or(m1, m2)
        return cv2.inRange(
            hsv,
            np.array(cfg["lower"], dtype=np.uint8),
            np.array(cfg["upper"], dtype=np.uint8),
        )

    def _detect_pillar(
        self,
        hsv: np.ndarray,
        color: str,
        debug_frame: Optional[np.ndarray],
        color_bgr: tuple,
    ) -> int:
        """Return the largest contour area for *color* pillar (0 if none found)."""
        mask = self._mask_from_config(hsv, color)
        mask = cv2.erode(mask, None, iterations=2)
        mask = cv2.dilate(mask, None, iterations=2)

        contours, _ = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        if not contours:
            return 0

        largest = max(contours, key=cv2.contourArea)
        area = int(cv2.contourArea(largest))
        if area < self.MIN_PILLAR_AREA:
            return 0

        if debug_frame is not None:
            cv2.drawContours(debug_frame, [largest], -1, color_bgr, 2)

        return area

    def _detect_lane_offset(
        self,
        hsv: np.ndarray,
        width: int,
        height: int,
        debug_frame: Optional[np.ndarray],
    ) -> float:
        """
        Estimate lateral offset from the lane centre.

        Strategy:
          1. Mask orange (right boundary) and blue (left boundary) lines.
          2. Find the centroid of each mask in the bottom third of the frame.
          3. Offset = (midpoint of the two centroids) − (frame centre).

        Returns the offset in pixels (positive = vehicle is to the left of centre).
        """
        roi_y = height * 2 // 3
        orange_mask = self._mask_from_config(hsv, "orange")[roi_y:, :]
        blue_mask = self._mask_from_config(hsv, "blue")[roi_y:, :]

        orange_cx = self._mask_centroid_x(orange_mask)
        blue_cx = self._mask_centroid_x(blue_mask)

        cx = width / 2

        if orange_cx is not None and blue_cx is not None:
            lane_centre = (orange_cx + blue_cx) / 2.0
        elif orange_cx is not None:
            lane_centre = orange_cx - width * 0.25
        elif blue_cx is not None:
            lane_centre = blue_cx + width * 0.25
        else:
            return 0.0

        offset = lane_centre - cx

        if debug_frame is not None:
            y_draw = roi_y + (height - roi_y) // 2
            if orange_cx is not None:
                cv2.circle(
                    debug_frame,
                    (int(orange_cx), y_draw),
                    8,
                    (0, 165, 255),
                    -1,
                )
            if blue_cx is not None:
                cv2.circle(
                    debug_frame,
                    (int(blue_cx), y_draw),
                    8,
                    (255, 0, 0),
                    -1,
                )
            cv2.line(
                debug_frame,
                (int(cx), 0),
                (int(cx), height),
                (255, 255, 255),
                1,
            )

        return float(offset)

    @staticmethod
    def _mask_centroid_x(mask: np.ndarray) -> Optional[float]:
        M = cv2.moments(mask)
        if M["m00"] == 0:
            return None
        return M["m10"] / M["m00"]


# ---------------------------------------------------------------------------
# Interactive HSV calibration tool
# ---------------------------------------------------------------------------

_CALIBRATE_COLORS = ["red", "green", "magenta", "orange", "blue"]


def run_calibration(camera_index: int = 0) -> None:
    """Open an interactive trackbar window to tune HSV thresholds."""
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open camera index {camera_index}")

    config = load_hsv_config()
    current_color_idx = [0]

    window = "HSV Calibration"
    cv2.namedWindow(window)

    def _nothing(_):
        pass

    def _create_trackbars(color: str) -> None:
        cv2.destroyWindow(window)
        cv2.namedWindow(window)
        cfg = config[color]
        if "lower1" in cfg:
            cv2.createTrackbar("H_lo1", window, cfg["lower1"][0], 180, _nothing)
            cv2.createTrackbar("S_lo1", window, cfg["lower1"][1], 255, _nothing)
            cv2.createTrackbar("V_lo1", window, cfg["lower1"][2], 255, _nothing)
            cv2.createTrackbar("H_hi1", window, cfg["upper1"][0], 180, _nothing)
            cv2.createTrackbar("S_hi1", window, cfg["upper1"][1], 255, _nothing)
            cv2.createTrackbar("V_hi1", window, cfg["upper1"][2], 255, _nothing)
            cv2.createTrackbar("H_lo2", window, cfg["lower2"][0], 180, _nothing)
            cv2.createTrackbar("S_lo2", window, cfg["lower2"][1], 255, _nothing)
            cv2.createTrackbar("V_lo2", window, cfg["lower2"][2], 255, _nothing)
            cv2.createTrackbar("H_hi2", window, cfg["upper2"][0], 180, _nothing)
            cv2.createTrackbar("S_hi2", window, cfg["upper2"][1], 255, _nothing)
            cv2.createTrackbar("V_hi2", window, cfg["upper2"][2], 255, _nothing)
        else:
            cv2.createTrackbar("H_lo", window, cfg["lower"][0], 180, _nothing)
            cv2.createTrackbar("S_lo", window, cfg["lower"][1], 255, _nothing)
            cv2.createTrackbar("V_lo", window, cfg["lower"][2], 255, _nothing)
            cv2.createTrackbar("H_hi", window, cfg["upper"][0], 180, _nothing)
            cv2.createTrackbar("S_hi", window, cfg["upper"][1], 255, _nothing)
            cv2.createTrackbar("V_hi", window, cfg["upper"][2], 255, _nothing)

    _create_trackbars(_CALIBRATE_COLORS[0])
    print("HSV Calibration – press 'n' next color, 's' save & quit, 'q' quit without saving.")

    while True:
        color = _CALIBRATE_COLORS[current_color_idx[0]]
        ok, frame = cap.read()
        if not ok:
            break

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        cfg = config[color]

        if "lower1" in cfg:
            cfg["lower1"] = [
                cv2.getTrackbarPos("H_lo1", window),
                cv2.getTrackbarPos("S_lo1", window),
                cv2.getTrackbarPos("V_lo1", window),
            ]
            cfg["upper1"] = [
                cv2.getTrackbarPos("H_hi1", window),
                cv2.getTrackbarPos("S_hi1", window),
                cv2.getTrackbarPos("V_hi1", window),
            ]
            cfg["lower2"] = [
                cv2.getTrackbarPos("H_lo2", window),
                cv2.getTrackbarPos("S_lo2", window),
                cv2.getTrackbarPos("V_lo2", window),
            ]
            cfg["upper2"] = [
                cv2.getTrackbarPos("H_hi2", window),
                cv2.getTrackbarPos("S_hi2", window),
                cv2.getTrackbarPos("V_hi2", window),
            ]
            m1 = cv2.inRange(
                hsv,
                np.array(cfg["lower1"], dtype=np.uint8),
                np.array(cfg["upper1"], dtype=np.uint8),
            )
            m2 = cv2.inRange(
                hsv,
                np.array(cfg["lower2"], dtype=np.uint8),
                np.array(cfg["upper2"], dtype=np.uint8),
            )
            mask = cv2.bitwise_or(m1, m2)
        else:
            cfg["lower"] = [
                cv2.getTrackbarPos("H_lo", window),
                cv2.getTrackbarPos("S_lo", window),
                cv2.getTrackbarPos("V_lo", window),
            ]
            cfg["upper"] = [
                cv2.getTrackbarPos("H_hi", window),
                cv2.getTrackbarPos("S_hi", window),
                cv2.getTrackbarPos("V_hi", window),
            ]
            mask = cv2.inRange(
                hsv,
                np.array(cfg["lower"], dtype=np.uint8),
                np.array(cfg["upper"], dtype=np.uint8),
            )

        masked = cv2.bitwise_and(frame, frame, mask=mask)
        label = f"Color: {color}  (n=next, s=save+quit, q=quit)"
        cv2.putText(masked, label, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.imshow(window, masked)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("n"):
            current_color_idx[0] = (current_color_idx[0] + 1) % len(_CALIBRATE_COLORS)
            _create_trackbars(_CALIBRATE_COLORS[current_color_idx[0]])
        elif key == ord("s"):
            save_hsv_config(config)
            print("Saved.")
            break
        elif key == ord("q"):
            print("Quit without saving.")
            break

    cap.release()
    cv2.destroyAllWindows()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Vision pipeline / calibration tool")
    parser.add_argument("--calibrate", action="store_true", help="Run interactive HSV calibration")
    parser.add_argument("--camera", type=int, default=0, help="Camera index (default: 0)")
    args = parser.parse_args()

    if args.calibrate:
        run_calibration(camera_index=args.camera)
    else:
        with VisionPipeline(camera_index=args.camera) as vp:
            while True:
                frame = vp.read_frame()
                if frame is None:
                    break
                result = vp.process(frame, debug=True)
                print(result)
                if result.debug_frame is not None:
                    cv2.imshow("Vision Debug", result.debug_frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
        cv2.destroyAllWindows()
