"""
main.py – Entry point for the WRO 2026 Future Engineers autonomous vehicle.

Usage
-----
    python3 src/main.py [--port /dev/ttyACM0] [--baud 115200] [--debug] [--laps 3]

The script:
  1. Opens the serial connection to the Arduino.
  2. Opens the camera and starts the vision pipeline.
  3. Waits for the operator to press Enter (or the physical start button on the car).
  4. Runs the state machine at ~20 Hz until STOP state is reached.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time

import cv2

# Allow running directly from the src/ directory or from the repo root.
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from serial_comm import ArduinoComm
from state_machine import VehicleStateMachine
from vision import VisionPipeline

logger = logging.getLogger(__name__)

LOOP_HZ = 20
LOOP_PERIOD = 1.0 / LOOP_HZ


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="WRO 2026 Future Engineers – Autonomous Vehicle"
    )
    parser.add_argument(
        "--port",
        default="/dev/ttyACM0",
        help="Serial port for Arduino (default: /dev/ttyACM0)",
    )
    parser.add_argument(
        "--baud",
        type=int,
        default=115200,
        help="Serial baud rate (default: 115200)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Show live camera feed with detection overlays",
    )
    parser.add_argument(
        "--laps",
        type=int,
        default=3,
        help="Number of laps to complete before parking (default: 3)",
    )
    parser.add_argument(
        "--camera",
        type=int,
        default=0,
        help="Camera index (default: 0)",
    )
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    args = parse_args()

    logger.info("Starting WRO 2026 vehicle controller")
    logger.info("  Port : %s  Baud: %d", args.port, args.baud)
    logger.info("  Laps : %d  Debug: %s", args.laps, args.debug)

    with ArduinoComm(port=args.port, baud=args.baud) as arduino:
        with VisionPipeline(camera_index=args.camera) as vision:
            sm = VehicleStateMachine(arduino=arduino, target_laps=args.laps)

            # Wait for start signal.
            print("\nPress Enter to start the vehicle…", end="", flush=True)
            input()

            sm.start()
            logger.info("Vehicle started – running state machine at %d Hz", LOOP_HZ)

            try:
                while True:
                    loop_start = time.monotonic()

                    frame = vision.read_frame()
                    if frame is None:
                        logger.warning("Failed to read camera frame")
                        time.sleep(LOOP_PERIOD)
                        continue

                    detection = vision.process(frame, debug=args.debug)
                    sm.update(detection)

                    if args.debug and detection.debug_frame is not None:
                        info = (
                            f"State: {sm.state.name}  "
                            f"Laps: {sm.lap_count}  "
                            f"R:{detection.red_area} "
                            f"G:{detection.green_area} "
                            f"M:{detection.magenta_area} "
                            f"Offset:{detection.lane_offset:.1f}"
                        )
                        cv2.putText(
                            detection.debug_frame,
                            info,
                            (10, 20),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.5,
                            (0, 255, 255),
                            1,
                        )
                        cv2.imshow("WRO 2026 – Debug", detection.debug_frame)

                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        logger.info("Quit key pressed")
                        sm.stop()

                    from state_machine import State
                    if sm.state == State.STOP:
                        logger.info("Run complete – vehicle stopped")
                        break

                    # Maintain loop frequency.
                    elapsed = time.monotonic() - loop_start
                    sleep_time = LOOP_PERIOD - elapsed
                    if sleep_time > 0:
                        time.sleep(sleep_time)

            except KeyboardInterrupt:
                logger.info("Interrupted by user")
                sm.stop()
            finally:
                cv2.destroyAllWindows()

    logger.info("Shutdown complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
