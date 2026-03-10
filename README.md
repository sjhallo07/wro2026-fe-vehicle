# WRO 2026 Future Engineers – Autonomous Vehicle Project

[![WRO](https://img.shields.io/badge/WRO-2026-blue)](https://wro-association.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Team Name:** [Your Team Name]  
**Country:** [Your Country]  
**Institution:** [Your School/Organization]  
**Members:** [Name1, Name2, Name3]  
**Coach:** [Coach Name]  

---

## 📖 Table of Contents
- [Overview](#overview)
- [Hardware Design](#hardware-design)
  - [Chassis & Drivetrain](#chassis--drivetrain)
  - [Steering Mechanism](#steering-mechanism)
  - [Sensors](#sensors)
  - [Power System](#power-system)
- [Software Architecture](#software-architecture)
  - [Vision Pipeline](#vision-pipeline)
  - [State Machine](#state-machine)
  - [Control Algorithms](#control-algorithms)
  - [Communication with Arduino](#communication-with-arduino)
- [Repository Structure](#repository-structure)
- [Setup & Installation](#setup--installation)
  - [Raspberry Pi Setup](#raspberry-pi-setup)
  - [Arduino Setup](#arduino-setup)
- [Usage](#usage)
  - [Calibration](#calibration)
  - [Running the Vehicle](#running-the-vehicle)
- [Engineering Journal](#engineering-journal)
- [Videos](#videos)
- [License](#license)

---

## Overview

This repository contains the complete software and hardware documentation for our autonomous vehicle competing in the **WRO 2026 Future Engineers** category. The vehicle must complete three laps on a randomly configured track while obeying traffic signals (red/green pillars) and finally park in a parallel parking spot.

Our solution uses a **Raspberry Pi 4** for high-level vision processing and decision making, and an **Arduino Uno** for low‑level motor control and sensor reading. The two boards communicate via USB serial.

---

## Hardware Design

### Chassis & Drivetrain
- **Chassis:** Custom 3D‑printed frame (STL files in `cad/`).
- **Dimensions:** 280 mm × 180 mm (within the 300×200 mm limit).
- **Drive:** Single DC motor with gearbox (12V, 300 RPM) connected to rear axle.  
  - Motor driver: Cytron 13A (PWM controlled).
- **Wheels:** Four 65 mm diameter rubber wheels.  
  - No omnidirectional wheels allowed.
- **Weight:** ~1.2 kg (under 1.5 kg limit).

### Steering Mechanism
- **Type:** Ackermann steering.
- **Actuator:** MG996R servo motor connected to front wheels.
- **Geometry:** Optimised for tight turns (see CAD files).

### Sensors
| Sensor | Model | Purpose |
|--------|-------|---------|
| Camera | Raspberry Pi Camera v2 (with wide‑angle lens) | Detecting pillars (red/green/magenta) and lane lines. |
| IMU | MPU6050 | Orientation estimation (yaw) for dead reckoning. |
| Encoder | Hall effect + magnetic disc | Wheel speed measurement for PID velocity control. |
| Distance (x2) | HC‑SR04 | Emergency obstacle detection (backup for vision). |

### Power System
- **Main Battery:** 3‑cell LiPo (2200 mAh, 11.1V) for motors and Arduino.
- **Secondary Battery:** 5V USB power bank for Raspberry Pi.
- **Voltage Regulator:** LM2596 step‑down (5V/3A) for Pi and sensors.
- **Switches:** Two independent switches (one for motors, one for logic).
- **Wiring diagram:** See `wiring/wiring_diagram.pdf`.

---

## Software Architecture

### Vision Pipeline
- **Language:** Python 3.9
- **Libraries:** OpenCV, NumPy
- **Color Detection:** HSV thresholding (calibrated for competition lighting).
- **Lane Following:** Detects orange and blue lines, computes offset, sends correction to Arduino.

### State Machine
We implemented a finite state machine with the following states:
1. `INIT` – Wait for start button.
2. `LANE_FOLLOW` – Normal driving, follow lane.
3. `AVOID_LEFT` – Red pillar detected → pass on right (turn right).
4. `AVOID_RIGHT` – Green pillar detected → pass on left (turn left).
5. `PARKING` – Magenta markers detected → execute parallel parking.
6. `STOP` – End of run.

Transitions are based on pillar detection and lap count.

### Control Algorithms
- **Lane Following:** Proportional controller (P) based on lateral offset.
- **Speed Control:** PID controller using encoder feedback (maintains constant speed).
- **Parking Maneuver:** Pre‑programmed sequence using odometry and IMU.

### Communication with Arduino
- **Protocol:** Simple ASCII commands over USB serial (baud 115200).
- **Commands:** `FORWARD`, `BACK`, `LEFT n`, `RIGHT n`, `STOP` (n = turn angle in degrees).
- Arduino acknowledges each command and executes it using PWM and servo control.

---

## Repository Structure

```
wro2026-fe-vehicle/
├── README.md
├── LICENSE
├── requirements.txt
├── config/
│   └── hsv_config.json          # HSV colour thresholds for vision
├── src/
│   ├── main.py                  # Entry point – starts the state machine
│   ├── vision.py                # Camera capture & colour/lane detection
│   ├── state_machine.py         # Finite state machine
│   ├── controller.py            # P/PID controllers
│   └── serial_comm.py           # Serial communication with Arduino
├── arduino/
│   └── wro2026_arduino/
│       └── wro2026_arduino.ino  # Arduino sketch
├── cad/
│   └── README.md                # CAD file descriptions
└── wiring/
    └── README.md                # Wiring diagram notes
```

---

## Setup & Installation

### Raspberry Pi Setup

1. **Flash OS:** Use Raspberry Pi OS Lite (64-bit) on an SD card.

2. **Enable camera:**
   ```bash
   sudo raspi-config
   # Interface Options → Camera → Enable
   ```

3. **Install dependencies:**
   ```bash
   sudo apt-get update && sudo apt-get install -y python3-pip python3-opencv
   pip3 install -r requirements.txt
   ```

4. **Clone repository:**
   ```bash
   git clone https://github.com/sjhallo07/wro2026-fe-vehicle.git
   cd wro2026-fe-vehicle
   ```

5. **Connect Arduino** via USB; note the port (usually `/dev/ttyACM0`).

### Arduino Setup

1. Open `arduino/wro2026_arduino/wro2026_arduino.ino` in the Arduino IDE (≥ 2.0).
2. Install required libraries via Library Manager:
   - **Servo** (built-in)
3. Select **Board:** Arduino Uno, **Port:** your COM/ttyACM port.
4. Upload the sketch.

---

## Usage

### Calibration

Before the first run, calibrate the HSV colour thresholds for your competition lighting:

```bash
cd wro2026-fe-vehicle
python3 src/vision.py --calibrate
```

An interactive window will appear with trackbars for each HSV channel. Adjust until each colour (red, green, magenta, orange, blue) is cleanly segmented. The values are saved automatically to `config/hsv_config.json`.

### Running the Vehicle

1. Power on the vehicle (motors switch first, then logic switch).
2. SSH into the Raspberry Pi or open a terminal:
   ```bash
   cd wro2026-fe-vehicle
   python3 src/main.py --port /dev/ttyACM0
   ```
3. Press the start button on the vehicle (or press **Enter** in the terminal).
4. The vehicle will complete three laps and park autonomously.

**Optional flags:**
```
--port PORT    Serial port for Arduino (default: /dev/ttyACM0)
--baud BAUD    Baud rate (default: 115200)
--debug        Show live camera feed with overlays
--laps N       Number of laps to complete (default: 3)
```

---

## Engineering Journal

| Date | Entry |
|------|-------|
| TBD  | Initial hardware assembly and motor testing. |
| TBD  | First camera calibration run. |
| TBD  | State machine implemented and bench-tested. |
| TBD  | First full lap completed. |
| TBD  | Parking maneuver tuned. |

---

## Videos

| Round | Link |
|-------|------|
| Qualification run (3 laps, open challenge) | TBD |
| Final run (3 laps + parking) | TBD |

---

## License

This project is licensed under the MIT License – see the [LICENSE](LICENSE) file for details.