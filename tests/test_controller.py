"""
tests/test_controller.py – Unit tests for the P and PID controllers.
"""

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
from controller import PController, PIDController


# ---------------------------------------------------------------------------
# PController tests
# ---------------------------------------------------------------------------

class TestPController:
    def test_zero_error(self):
        ctrl = PController(kp=0.1)
        assert ctrl.compute(0.0) == 0.0

    def test_positive_error(self):
        ctrl = PController(kp=0.1)
        result = ctrl.compute(100.0)
        assert result == pytest.approx(10.0)

    def test_negative_error(self):
        ctrl = PController(kp=0.1)
        result = ctrl.compute(-100.0)
        assert result == pytest.approx(-10.0)

    def test_clamp_positive(self):
        ctrl = PController(kp=1.0, max_output=30.0)
        assert ctrl.compute(9999) == pytest.approx(30.0)

    def test_clamp_negative(self):
        ctrl = PController(kp=1.0, max_output=30.0)
        assert ctrl.compute(-9999) == pytest.approx(-30.0)

    def test_kp_zero(self):
        ctrl = PController(kp=0.0)
        assert ctrl.compute(500.0) == 0.0


# ---------------------------------------------------------------------------
# PIDController tests
# ---------------------------------------------------------------------------

class TestPIDController:
    def test_zero_error_no_output(self):
        ctrl = PIDController(kp=1.0, ki=0.0, kd=0.0, setpoint=100.0)
        output = ctrl.compute(100.0)
        assert output == pytest.approx(0.0, abs=1e-6)

    def test_proportional_only(self):
        ctrl = PIDController(kp=2.0, ki=0.0, kd=0.0, setpoint=50.0)
        output = ctrl.compute(0.0)   # error = 50
        assert output == pytest.approx(100.0, abs=1.0)

    def test_integrator_winds_up(self):
        ctrl = PIDController(
            kp=0.0, ki=1.0, kd=0.0, setpoint=10.0, sample_time=0.1
        )
        # Call multiple times to accumulate integral.
        for _ in range(5):
            ctrl.compute(0.0)
            time.sleep(0.01)
        output = ctrl.compute(0.0)
        # Integral should be positive (setpoint - measured = 10 > 0).
        assert output > 0

    def test_output_clamped(self):
        ctrl = PIDController(kp=1000.0, ki=0.0, kd=0.0, setpoint=1.0, max_output=100.0)
        output = ctrl.compute(0.0)
        assert output == pytest.approx(100.0)

    def test_output_clamped_negative(self):
        ctrl = PIDController(kp=1000.0, ki=0.0, kd=0.0, setpoint=-1.0, max_output=100.0)
        output = ctrl.compute(0.0)
        assert output == pytest.approx(-100.0)

    def test_reset_clears_integral(self):
        ctrl = PIDController(kp=0.0, ki=1.0, kd=0.0, setpoint=10.0)
        for _ in range(10):
            ctrl.compute(0.0)
        ctrl.reset()
        # After reset, integral is zero; with ki only and zero error: output ~ 0.
        output = ctrl.compute(10.0)  # error = 0 after reset setpoint=10, measured=10
        assert output == pytest.approx(0.0, abs=0.5)
