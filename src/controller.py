"""
controller.py – Control algorithms for lane following and speed control.

Classes
-------
PController   – Simple proportional controller (lane lateral offset → steering angle).
PIDController – Full PID controller (encoder ticks → motor PWM for speed control).
"""

import time


class PController:
    """
    Proportional controller that maps a lateral offset to a steering angle.

    The output is clamped to [-max_output, +max_output].
    """

    def __init__(self, kp: float, max_output: float = 90.0):
        self.kp = kp
        self.max_output = max_output

    def compute(self, error: float) -> float:
        """Return steering correction in degrees given a lateral *error* in pixels."""
        output = self.kp * error
        return max(-self.max_output, min(self.max_output, output))


class PIDController:
    """
    Discrete PID controller suitable for fixed-rate control loops.

    Parameters
    ----------
    kp, ki, kd   : PID gains.
    setpoint     : Desired value (e.g., target speed in encoder ticks/s).
    max_output   : Output clamp (e.g., 255 for 8-bit PWM).
    sample_time  : Expected loop period (seconds); used for integral/derivative.
    """

    def __init__(
        self,
        kp: float,
        ki: float,
        kd: float,
        setpoint: float = 0.0,
        max_output: float = 255.0,
        sample_time: float = 0.05,
    ):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.setpoint = setpoint
        self.max_output = max_output
        self.sample_time = sample_time

        self._integral = 0.0
        self._prev_error = 0.0
        self._last_time = time.monotonic()

    def reset(self) -> None:
        """Reset integrator and derivative state."""
        self._integral = 0.0
        self._prev_error = 0.0
        self._last_time = time.monotonic()

    def compute(self, measured_value: float) -> float:
        """
        Compute PID output given the current *measured_value*.

        Returns the control signal clamped to [-max_output, +max_output].
        """
        now = time.monotonic()
        dt = now - self._last_time
        if dt <= 0:
            dt = self.sample_time

        error = self.setpoint - measured_value
        self._integral += error * dt
        derivative = (error - self._prev_error) / dt

        output = self.kp * error + self.ki * self._integral + self.kd * derivative
        output = max(-self.max_output, min(self.max_output, output))

        self._prev_error = error
        self._last_time = now
        return output
