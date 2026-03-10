"""
tests/test_serial_comm.py – Unit tests for ArduinoComm.

Uses a mock Serial object so no hardware is required.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from unittest.mock import MagicMock, patch, call
import pytest

from serial_comm import ArduinoComm


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_mock_serial(ack: str = "OK") -> MagicMock:
    """Return a mock serial.Serial that returns *ack* from readline()."""
    mock_serial = MagicMock()
    mock_serial.is_open = True
    mock_serial.readline.return_value = (ack + "\n").encode("ascii")
    return mock_serial


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSendCommand:
    def _make_comm(self, ack: str = "OK") -> tuple[ArduinoComm, MagicMock]:
        comm = ArduinoComm(port="/dev/null", baud=115200)
        mock_serial = make_mock_serial(ack)
        comm._serial = mock_serial
        return comm, mock_serial

    def test_sends_newline_terminated_command(self):
        comm, mock_serial = self._make_comm()
        comm.send_command("FORWARD")
        mock_serial.write.assert_called_once_with(b"FORWARD\n")

    def test_returns_true_on_ok(self):
        comm, _ = self._make_comm(ack="OK")
        assert comm.send_command("STOP") is True

    def test_returns_false_on_err(self):
        comm, _ = self._make_comm(ack="ERR")
        assert comm.send_command("BADCMD") is False

    def test_returns_false_on_unexpected_response(self):
        comm, _ = self._make_comm(ack="UNKNOWN")
        assert comm.send_command("FORWARD") is False

    def test_raises_if_not_connected(self):
        comm = ArduinoComm(port="/dev/null", baud=115200)
        with pytest.raises(RuntimeError):
            comm.send_command("FORWARD")


class TestConvenienceMethods:
    def _make_comm(self) -> ArduinoComm:
        comm = ArduinoComm(port="/dev/null", baud=115200)
        comm._serial = make_mock_serial("OK")
        return comm

    def test_forward(self):
        comm = self._make_comm()
        assert comm.forward() is True
        comm._serial.write.assert_called_with(b"FORWARD\n")

    def test_back(self):
        comm = self._make_comm()
        comm.back()
        comm._serial.write.assert_called_with(b"BACK\n")

    def test_stop(self):
        comm = self._make_comm()
        comm.stop()
        comm._serial.write.assert_called_with(b"STOP\n")

    def test_left_clamps_to_90(self):
        comm = self._make_comm()
        comm.left(200)
        comm._serial.write.assert_called_with(b"LEFT 90\n")

    def test_left_clamps_to_zero(self):
        comm = self._make_comm()
        comm.left(-10)
        comm._serial.write.assert_called_with(b"LEFT 0\n")

    def test_right_clamps_to_90(self):
        comm = self._make_comm()
        comm.right(200)
        comm._serial.write.assert_called_with(b"RIGHT 90\n")

    def test_right_clamps_to_zero(self):
        comm = self._make_comm()
        comm.right(-5)
        comm._serial.write.assert_called_with(b"RIGHT 0\n")

    def test_center_sends_left_0(self):
        comm = self._make_comm()
        comm.center()
        comm._serial.write.assert_called_with(b"LEFT 0\n")


class TestConnectionState:
    def test_is_connected_true_when_open(self):
        comm = ArduinoComm()
        comm._serial = make_mock_serial()
        assert comm.is_connected() is True

    def test_is_connected_false_without_serial(self):
        comm = ArduinoComm()
        assert comm.is_connected() is False

    def test_is_connected_false_when_closed(self):
        comm = ArduinoComm()
        mock_serial = make_mock_serial()
        mock_serial.is_open = False
        comm._serial = mock_serial
        assert comm.is_connected() is False

    def test_disconnect_closes_serial(self):
        comm = ArduinoComm()
        comm._serial = make_mock_serial()
        comm.disconnect()
        comm._serial.close.assert_called_once()
