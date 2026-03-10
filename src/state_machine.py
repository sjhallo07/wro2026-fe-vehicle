"""
state_machine.py – Finite state machine for the WRO 2026 Future Engineers vehicle.

States
------
INIT         – Wait for start signal.
LANE_FOLLOW  – Normal driving; follow lane using proportional control.
AVOID_LEFT   – Red pillar detected; steer right so the pillar passes on the
               vehicle's LEFT side (vehicle goes to the right of the pillar).
AVOID_RIGHT  – Green pillar detected; steer left so the pillar passes on the
               vehicle's RIGHT side (vehicle goes to the left of the pillar).
PARKING      – Magenta markers detected; execute parallel parking sequence.
STOP         – Run complete.

Transitions
-----------
INIT          → LANE_FOLLOW   : start() called.
LANE_FOLLOW   → AVOID_LEFT    : red pillar area > threshold.
LANE_FOLLOW   → AVOID_RIGHT   : green pillar area > threshold.
LANE_FOLLOW   → PARKING       : magenta area > threshold AND laps == target_laps.
AVOID_LEFT    → LANE_FOLLOW   : pillar no longer visible.
AVOID_RIGHT   → LANE_FOLLOW   : pillar no longer visible.
PARKING       → STOP          : parking sequence complete.
Any           → STOP          : stop() called.
"""

from __future__ import annotations

import logging
import time
from enum import Enum, auto
from typing import Callable, Optional

from controller import PController, PIDController
from serial_comm import ArduinoComm
from vision import DetectionResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tuneable constants (adjust per-vehicle)
# ---------------------------------------------------------------------------

# Minimum contour area to trigger pillar avoidance.
PILLAR_DETECT_THRESHOLD = 2000

# Minimum magenta area to trigger parking.
MAGENTA_DETECT_THRESHOLD = 3000

# Proportional gain for lane-following (pixels → degrees).
LANE_KP = 0.08

# Avoidance steering angle (degrees).
AVOID_ANGLE = 35

# Speed PID: setpoint in arbitrary encoder ticks/s.
SPEED_SETPOINT = 120.0
SPEED_KP, SPEED_KI, SPEED_KD = 1.2, 0.5, 0.05

# Parking timing (seconds).
PARK_STEP1_DURATION = 0.8   # Steer and reverse.
PARK_STEP2_DURATION = 0.6   # Straighten and reverse.
PARK_STEP3_DURATION = 0.4   # Pull forward to centre.

# Number of laps before switching to parking mode.
DEFAULT_TARGET_LAPS = 3

# How long a pillar must be absent before returning to LANE_FOLLOW (s).
PILLAR_LOST_TIMEOUT = 0.4


# ---------------------------------------------------------------------------
# State enum
# ---------------------------------------------------------------------------

class State(Enum):
    INIT = auto()
    LANE_FOLLOW = auto()
    AVOID_LEFT = auto()
    AVOID_RIGHT = auto()
    PARKING = auto()
    STOP = auto()


# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------

class VehicleStateMachine:
    """
    Orchestrates the vehicle's behaviour by reading DetectionResults and
    issuing commands to the Arduino via ArduinoComm.

    The caller is responsible for calling ``update()`` at regular intervals
    (e.g., 20 Hz) with the latest DetectionResult.
    """

    def __init__(
        self,
        arduino: ArduinoComm,
        target_laps: int = DEFAULT_TARGET_LAPS,
        on_state_change: Optional[Callable[[State, State], None]] = None,
    ):
        self._arduino = arduino
        self._target_laps = target_laps
        self._on_state_change = on_state_change

        self._state = State.INIT
        self._lap_count = 0
        self._pillar_lost_time: Optional[float] = None

        self._lane_ctrl = PController(kp=LANE_KP, max_output=90.0)
        self._speed_ctrl = PIDController(
            kp=SPEED_KP,
            ki=SPEED_KI,
            kd=SPEED_KD,
            setpoint=SPEED_SETPOINT,
            max_output=255.0,
        )

        self._parking_step = 0
        self._parking_step_start: float = 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def state(self) -> State:
        return self._state

    @property
    def lap_count(self) -> int:
        return self._lap_count

    def start(self) -> None:
        """Transition from INIT to LANE_FOLLOW."""
        if self._state == State.INIT:
            self._transition(State.LANE_FOLLOW)
            self._arduino.forward()

    def stop(self) -> None:
        """Force transition to STOP and halt the vehicle."""
        self._transition(State.STOP)
        self._arduino.stop()

    def increment_lap(self) -> None:
        """Call this when the vehicle completes a full lap."""
        self._lap_count += 1
        logger.info("Lap %d / %d completed", self._lap_count, self._target_laps)

    def update(self, detection: DetectionResult) -> None:
        """
        Process the latest vision detection and drive the vehicle accordingly.

        Should be called at a regular rate (≥ 10 Hz).
        """
        if self._state == State.INIT:
            return

        if self._state == State.STOP:
            return

        if self._state == State.LANE_FOLLOW:
            self._handle_lane_follow(detection)

        elif self._state == State.AVOID_LEFT:
            self._handle_avoid(detection, direction="left")

        elif self._state == State.AVOID_RIGHT:
            self._handle_avoid(detection, direction="right")

        elif self._state == State.PARKING:
            self._handle_parking()

    # ------------------------------------------------------------------
    # State handlers
    # ------------------------------------------------------------------

    def _handle_lane_follow(self, detection: DetectionResult) -> None:
        # Check for parking trigger (magenta) only on final lap.
        if (
            self._lap_count >= self._target_laps
            and detection.magenta_area > MAGENTA_DETECT_THRESHOLD
        ):
            self._transition(State.PARKING)
            return

        # Red pillar → move right (avoid on the left side of pillar).
        if detection.red_area > PILLAR_DETECT_THRESHOLD:
            self._transition(State.AVOID_LEFT)
            self._arduino.right(AVOID_ANGLE)
            return

        # Green pillar → move left (avoid on the right side of pillar).
        if detection.green_area > PILLAR_DETECT_THRESHOLD:
            self._transition(State.AVOID_RIGHT)
            self._arduino.left(AVOID_ANGLE)
            return

        # Normal lane following.
        steering = self._lane_ctrl.compute(detection.lane_offset)
        if steering > 1.0:
            self._arduino.right(int(abs(steering)))
        elif steering < -1.0:
            self._arduino.left(int(abs(steering)))
        else:
            self._arduino.center()

    def _handle_avoid(self, detection: DetectionResult, direction: str) -> None:
        """Hold avoidance steering until the pillar disappears."""
        pillar_area = (
            detection.red_area if direction == "left" else detection.green_area
        )

        if pillar_area > PILLAR_DETECT_THRESHOLD:
            # Pillar still visible – keep steering.
            self._pillar_lost_time = None
            return

        # Pillar gone – start countdown before returning to lane follow.
        if self._pillar_lost_time is None:
            self._pillar_lost_time = time.monotonic()

        if time.monotonic() - self._pillar_lost_time >= PILLAR_LOST_TIMEOUT:
            self._pillar_lost_time = None
            self._transition(State.LANE_FOLLOW)
            self._arduino.center()
            self._arduino.forward()

    def _handle_parking(self) -> None:
        """
        Execute a pre-programmed parallel parking sequence.

        Step 0: Steer right + reverse.
        Step 1: Steer left + reverse.
        Step 2: Straighten + forward (centre in spot).
        Step 3: Done → STOP.
        """
        now = time.monotonic()

        if self._parking_step == 0:
            self._parking_step_start = now
            self._arduino.back()
            self._arduino.right(40)
            self._parking_step = 1
            return

        elapsed = now - self._parking_step_start

        if self._parking_step == 1 and elapsed >= PARK_STEP1_DURATION:
            self._parking_step_start = now
            self._arduino.left(40)
            self._parking_step = 2

        elif self._parking_step == 2 and elapsed >= PARK_STEP2_DURATION:
            self._parking_step_start = now
            self._arduino.center()
            self._arduino.forward()
            self._parking_step = 3

        elif self._parking_step == 3 and elapsed >= PARK_STEP3_DURATION:
            self._arduino.stop()
            self._transition(State.STOP)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _transition(self, new_state: State) -> None:
        if new_state == self._state:
            return
        old_state = self._state
        self._state = new_state
        logger.info("State: %s → %s", old_state.name, new_state.name)
        if self._on_state_change:
            self._on_state_change(old_state, new_state)
