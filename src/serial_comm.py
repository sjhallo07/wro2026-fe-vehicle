"""
serial_comm.py – Serial communication with the Arduino.

Sends ASCII commands over USB serial and reads acknowledgements.
Protocol (baud 115200):
  Pi → Arduino : "FORWARD\n", "BACK\n", "LEFT 30\n", "RIGHT 30\n", "STOP\n"
  Arduino → Pi : "OK\n" on success, "ERR\n" on unknown command.
"""

import logging
import threading
import time

import serial

logger = logging.getLogger(__name__)

_TIMEOUT_S = 1.0
_ACK_OK = "OK"
_ACK_ERR = "ERR"


class ArduinoComm:
    """Thread-safe wrapper around a pyserial Serial connection."""

    def __init__(self, port: str = "/dev/ttyACM0", baud: int = 115200):
        self._port = port
        self._baud = baud
        self._serial: serial.Serial | None = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """Open the serial port and wait for the Arduino to reset."""
        self._serial = serial.Serial(self._port, self._baud, timeout=_TIMEOUT_S)
        # Arduino resets on serial open; give it time to boot.
        time.sleep(2.0)
        self._serial.reset_input_buffer()
        logger.info("Connected to Arduino on %s @ %d baud", self._port, self._baud)

    def disconnect(self) -> None:
        """Close the serial port."""
        with self._lock:
            if self._serial and self._serial.is_open:
                self._serial.close()
                logger.info("Disconnected from Arduino")

    def is_connected(self) -> bool:
        return self._serial is not None and self._serial.is_open

    # ------------------------------------------------------------------
    # Command helpers
    # ------------------------------------------------------------------

    def send_command(self, command: str) -> bool:
        """
        Send *command* terminated with a newline and wait for ACK.

        Returns True on success (ACK == "OK"), False otherwise.
        Raises RuntimeError if the port is not open.
        """
        if not self.is_connected():
            raise RuntimeError("Serial port is not open")

        line = command.strip() + "\n"
        with self._lock:
            self._serial.write(line.encode("ascii"))
            self._serial.flush()
            response = self._serial.readline().decode("ascii", errors="ignore").strip()

        if response == _ACK_OK:
            logger.debug("CMD %r → OK", command)
            return True

        logger.warning("CMD %r → unexpected response: %r", command, response)
        return False

    # ------------------------------------------------------------------
    # Convenience command methods
    # ------------------------------------------------------------------

    def forward(self) -> bool:
        return self.send_command("FORWARD")

    def back(self) -> bool:
        return self.send_command("BACK")

    def stop(self) -> bool:
        return self.send_command("STOP")

    def left(self, angle: int) -> bool:
        """Steer left by *angle* degrees (0–90)."""
        angle = max(0, min(90, int(angle)))
        return self.send_command(f"LEFT {angle}")

    def right(self, angle: int) -> bool:
        """Steer right by *angle* degrees (0–90)."""
        angle = max(0, min(90, int(angle)))
        return self.send_command(f"RIGHT {angle}")

    def center(self) -> bool:
        """Return steering to centre (0 degrees)."""
        return self.send_command("LEFT 0")

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *_):
        self.disconnect()
