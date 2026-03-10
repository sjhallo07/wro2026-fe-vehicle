"""
tests/test_state_machine.py – Unit tests for VehicleStateMachine.

Uses a mock ArduinoComm so no hardware is required.
"""

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from unittest.mock import MagicMock, call, patch
import pytest

from state_machine import (
    VehicleStateMachine,
    State,
    PILLAR_DETECT_THRESHOLD,
    MAGENTA_DETECT_THRESHOLD,
    PILLAR_LOST_TIMEOUT,
    AVOID_ANGLE,
)
from vision import DetectionResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_sm(target_laps: int = 3) -> tuple[VehicleStateMachine, MagicMock]:
    arduino = MagicMock()
    sm = VehicleStateMachine(arduino=arduino, target_laps=target_laps)
    return sm, arduino


def empty_detection(**kwargs) -> DetectionResult:
    defaults = dict(
        red_area=0, green_area=0, magenta_area=0,
        lane_offset=0.0, frame_width=640, frame_height=480,
    )
    defaults.update(kwargs)
    return DetectionResult(**defaults)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestInitState:
    def test_starts_in_init(self):
        sm, _ = make_sm()
        assert sm.state == State.INIT

    def test_update_in_init_does_nothing(self):
        sm, arduino = make_sm()
        sm.update(empty_detection())
        arduino.forward.assert_not_called()

    def test_start_transitions_to_lane_follow(self):
        sm, arduino = make_sm()
        sm.start()
        assert sm.state == State.LANE_FOLLOW
        arduino.forward.assert_called_once()

    def test_double_start_no_effect(self):
        sm, arduino = make_sm()
        sm.start()
        sm.start()
        assert sm.state == State.LANE_FOLLOW


class TestLaneFollow:
    def test_red_pillar_triggers_avoid_left(self):
        sm, arduino = make_sm()
        sm.start()
        sm.update(empty_detection(red_area=PILLAR_DETECT_THRESHOLD + 1))
        assert sm.state == State.AVOID_LEFT
        arduino.right.assert_called_with(AVOID_ANGLE)

    def test_green_pillar_triggers_avoid_right(self):
        sm, arduino = make_sm()
        sm.start()
        sm.update(empty_detection(green_area=PILLAR_DETECT_THRESHOLD + 1))
        assert sm.state == State.AVOID_RIGHT
        arduino.left.assert_called_with(AVOID_ANGLE)

    def test_small_red_area_no_transition(self):
        sm, _ = make_sm()
        sm.start()
        sm.update(empty_detection(red_area=PILLAR_DETECT_THRESHOLD - 1))
        assert sm.state == State.LANE_FOLLOW

    def test_magenta_no_parking_before_target_laps(self):
        sm, _ = make_sm(target_laps=3)
        sm.start()
        sm.update(empty_detection(magenta_area=MAGENTA_DETECT_THRESHOLD + 1))
        assert sm.state == State.LANE_FOLLOW  # lap_count is 0

    def test_magenta_triggers_parking_on_target_lap(self):
        sm, _ = make_sm(target_laps=1)
        sm.start()
        sm.increment_lap()  # lap_count == 1 == target_laps
        sm.update(empty_detection(magenta_area=MAGENTA_DETECT_THRESHOLD + 1))
        assert sm.state == State.PARKING

    def test_lane_offset_right_calls_right(self):
        sm, arduino = make_sm()
        sm.start()
        sm.update(empty_detection(lane_offset=100.0))  # offset > 0 → steer right
        arduino.right.assert_called()

    def test_lane_offset_left_calls_left(self):
        sm, arduino = make_sm()
        sm.start()
        sm.update(empty_detection(lane_offset=-100.0))
        arduino.left.assert_called()

    def test_zero_offset_centres_steering(self):
        sm, arduino = make_sm()
        sm.start()
        sm.update(empty_detection(lane_offset=0.0))
        arduino.center.assert_called()


class TestAvoidState:
    def test_returns_to_lane_follow_when_pillar_gone(self):
        sm, arduino = make_sm()
        sm.start()
        # Trigger avoid.
        sm.update(empty_detection(red_area=PILLAR_DETECT_THRESHOLD + 1))
        assert sm.state == State.AVOID_LEFT

        # Pillar gone; wait long enough.
        with patch("state_machine.time") as mock_time:
            mock_time.monotonic.side_effect = [0.0, PILLAR_LOST_TIMEOUT + 0.1]
            sm.update(empty_detection(red_area=0))

        assert sm.state == State.LANE_FOLLOW
        arduino.center.assert_called()
        arduino.forward.assert_called()

    def test_stays_in_avoid_while_pillar_visible(self):
        sm, _ = make_sm()
        sm.start()
        sm.update(empty_detection(red_area=PILLAR_DETECT_THRESHOLD + 1))
        sm.update(empty_detection(red_area=PILLAR_DETECT_THRESHOLD + 1))
        assert sm.state == State.AVOID_LEFT


class TestStopState:
    def test_stop_halts_vehicle(self):
        sm, arduino = make_sm()
        sm.start()
        sm.stop()
        assert sm.state == State.STOP
        arduino.stop.assert_called()

    def test_update_in_stop_does_nothing(self):
        sm, arduino = make_sm()
        sm.start()
        sm.stop()
        arduino.reset_mock()
        sm.update(empty_detection(red_area=9999))
        arduino.right.assert_not_called()


class TestLapCount:
    def test_increment_lap(self):
        sm, _ = make_sm()
        assert sm.lap_count == 0
        sm.increment_lap()
        assert sm.lap_count == 1
        sm.increment_lap()
        assert sm.lap_count == 2


class TestOnStateChange:
    def test_callback_fires_on_transition(self):
        callback = MagicMock()
        arduino = MagicMock()
        sm = VehicleStateMachine(
            arduino=arduino, target_laps=3, on_state_change=callback
        )
        sm.start()
        callback.assert_called_once_with(State.INIT, State.LANE_FOLLOW)
