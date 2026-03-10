# wro2026-fe-vehicle

Starter repository for the WRO 2026 Future Engineers vehicle. It bundles the
vision prototype (Raspberry Pi), the Arduino firmware stub for the drivetrain,
and folders for CAD, wiring, and documentation assets.

## Repository layout

```text
wro2026-fe-vehicle/
├── README.md
├── requirements.txt         # Python dependencies for the Pi
├── src/
│   ├── main.py              # Core vision & decision loop
│   ├── arduino/
│   │   └── motor_control.ino# Arduino sketch for steering/throttle
│   ├── examples/
│   │   └── rpi_arduino_serial_test.py # Serial handshake test
│   └── utils/
│       └── calibration.py   # HSV calibration helpers
├── cad/                     # 3D files (STEP, STL)
├── wiring/                  # Wiring diagrams & pinouts
└── docs/                    # Engineering journal & reports
```

Add your CAD, wiring, and documentation artifacts in their respective folders
as they become available.

## Raspberry Pi setup

1. Flash Raspberry Pi OS (Bullseye recommended) and boot the Pi.
2. Install packages:

   ```bash
   sudo apt update
   sudo apt install python3-opencv python3-pip
   pip3 install -r requirements.txt
   ```

3. Enable the serial interface (``raspi-config → Interface Options → Serial``).
4. Connect the camera module and verify it works (``libcamera-still`` test).

## Arduino setup

* Open `src/arduino/motor_control.ino` with the Arduino IDE.
* Board: Arduino Uno (or adjust pins in the sketch to match your hardware).
* Required library: `Servo` (bundled with the IDE).
* Upload and monitor the serial console (`115200` baud). The sketch expects
  newline-terminated commands such as `S90` (steer) or `T1500` (throttle).

## Quick hardware test (Raspberry Pi + Arduino)

After uploading `motor_control.ino`, run this from Raspberry Pi to verify the
serial link and servo/ESC reactions:

```bash
python3 src/examples/rpi_arduino_serial_test.py --port /dev/ttyACM0
```

Windows equivalent (if needed while bench-testing):

```bash
python src/examples/rpi_arduino_serial_test.py --port COM3
```

Expected serial replies include lines like `STEER:90` and `THROTTLE:1500`.

## Calibrating colors

Lighting changes drastically between venues, so tune HSV ranges before every
session:

```bash
python3 src/utils/calibration.py
```

Use the OpenCV trackbars to enclose the target color. Press **s** to store the
current bounds or **q** to exit without saving. Calibration files are saved next
to the script and automatically loaded by `src/main.py`.

## Running the vehicle

```bash
python3 src/main.py
```

The script will open a preview window and highlight every calibrated color. Use
this as the foundation for your decision layer (lane keeping, obstacle
avoidance, start button detection, etc.). It now maps vision actions to Arduino
serial commands (`S...` for steering and `T...` for throttle).

## Documentation

* `cad/` – CAD sources for the chassis, steering linkages, and add-ons.
* `wiring/` – Fritzing diagrams, PDFs, and pinout spreadsheets.
* `docs/` – Engineering journal (PDF) plus any supporting appendices.

Keep these folders synchronized with your latest design iterations so judges can
reconstruct the entire build from this repository.
