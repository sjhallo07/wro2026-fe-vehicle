# WRO 2026 Future Engineers Vehicle (Beginner Friendly Guide)

**Language:** English | [Español](README.es.md)

Welcome! 👋  
This repository is designed for students (including mechanical engineering teams)
who may have **little programming experience**.

If you can follow a checklist, you can run this project.

---

## What this project does (in simple words)

- Uses a **Raspberry Pi camera** to detect colors (red, green, magenta).
- Sends commands to an **Arduino Uno** over USB serial.
- Arduino controls:
  - steering servo (`S...` commands)
  - throttle/ESC (`T...` commands)

---

## Visual roadmap (from clone to run)

### 1) Full workflow

![Quick start workflow](docs/diagrams/01_quick_start_workflow.png)

### 2) Connection overview

![Connection overview](docs/diagrams/02_connection_overview.png)

---

## Before you start (hardware + software checklist)

### Hardware

- Raspberry Pi (with Raspberry Pi OS)
- Arduino Uno
- USB cable (Pi ↔ Arduino)
- Camera module or USB camera
- Steering servo
- ESC + motor
- Battery / power source

### Software

- Git installed
- Python 3 installed
- Arduino IDE installed

---

## Step-by-step instructions

## Step 1 — Clone this repository

On Raspberry Pi terminal:

```bash
git clone https://github.com/sjhallo07/wro2026-fe-vehicle.git
cd wro2026-fe-vehicle
```

---

## Step 2 — Install Python dependencies

### Raspberry Pi / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Windows (optional bench testing)

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

---

## Step 3 — Upload Arduino firmware

1. Open Arduino IDE.
2. Open file: `src/arduino/motor_control.ino`
3. Select board: **Arduino Uno**
4. Select the correct port (example: `COM3` on Windows).
5. Click **Upload**.

When connected, Arduino should send `ARDUINO_READY` on serial.

---

## Step 4 — Connect Raspberry Pi and Arduino

Minimum required connections:

- Raspberry Pi to Arduino via **USB** (serial communication).
- Camera connected to Raspberry Pi.
- Servo signal to Arduino pin **10**.
- ESC signal to Arduino pin **9**.
- Use proper power and **common GND**.

⚠️ Safety first: test with wheels off the ground before full driving.

---

## Step 5 — Test serial communication (important)

Run this on Raspberry Pi:

```bash
python3 src/examples/rpi_arduino_serial_test.py --port /dev/ttyACM0
```

Windows example:

```bash
python src/examples/rpi_arduino_serial_test.py --port COM3
```

If working, you should see responses like:

- `STEER:90`
- `THROTTLE:1500`

---

## Step 6 — Calibrate camera colors

Run:

```bash
python3 src/utils/calibration.py
```

How to use:

- Move trackbars until mask detects your target color correctly.
- Press **S** to save.
- Press **Q** to quit.

Do this whenever lighting changes.

---

## Step 7 — Run the main vehicle program

```bash
python3 src/main.py
```

What to expect:

- Camera window opens.
- Color detections appear.
- Actions map to Arduino commands:
  - `FORWARD` → `S90`, `T1600`
  - `LEFT` → `S60`, `T1550`
  - `RIGHT` → `S120`, `T1550`
  - `STOP` → `T1500`, `S90`

---

## Quick troubleshooting (common student issues)

### 1) `Could not connect to Arduino`

- Check USB cable.
- Check port (`/dev/ttyACM0` or `COMx`).
- Close Arduino Serial Monitor (it can lock the port).

### 2) Camera not detected

- Verify camera cable.
- Try another camera index in code if needed.

### 3) Wrong color detection

- Re-run calibration (`src/utils/calibration.py`).
- Improve lighting consistency.

### 4) Servo/motor does not move

- Check power wiring.
- Confirm Arduino pins match sketch (`10` and `9`).
- Confirm ESC/servo grounds are common with Arduino.

### 5) Python package import errors (`cv2`, `serial`, `numpy`)

- Activate `.venv` first.
- Re-run `pip install -r requirements.txt`.

---

## Repository structure

```text
wro2026-fe-vehicle/
├── README.md
├── requirements.txt
├── src/
│   ├── main.py
│   ├── arduino/
│   │   └── motor_control.ino
│   ├── examples/
│   │   └── rpi_arduino_serial_test.py
│   └── utils/
│       └── calibration.py
├── cad/
├── wiring/
└── docs/
    └── diagrams/
        ├── 01_quick_start_workflow.png
        └── 02_connection_overview.png
```

---

## For teachers/mentors

This README is intentionally explicit and procedural so students can follow it
without strong coding background. You can turn each step into a lab checkpoint.
