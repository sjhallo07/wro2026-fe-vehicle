# wro2026-fe-vehicle
├── README.md # This file
├── requirements.txt # Python dependencies
├── src/
│ ├── main.py # Main vision & decision script (Raspberry Pi)
│ ├── arduino/
│ │ └── motor_control.ino # Arduino firmware
│ └── utils/
│ ├── calibrate_color.py # Interactive color calibration
│ └── pid_tuner.py # PID tuning helper
├── cad/ # 3D models (STEP, STL)
│ ├── chassis.step
│ ├── steering_arm.stl
│ └── ...
├── wiring/
│ ├── wiring_diagram.pdf # Fritzing/Excel diagram
│ └── pinout.txt # Pin assignments
├── docs/
│ └── engineering_journal.pdf # Full engineering journal
└── videos/
├── open_challenge.mp4 # Demo of open challenge
└── obstacle_challenge.mp4 # Demo with obstacles and parking

text

---

## Setup & Installation

### Raspberry Pi Setup
1. Flash Raspberry Pi OS (Bullseye) to an SD card.
2. Install dependencies:
   ```bash
   sudo apt update
   sudo apt install python3-opencv python3-pip
   pip3 install -r requirements.txt
Enable serial interface (raspi-config → Interface Options → Serial).

Connect camera and test with raspistill.

Arduino Setup
Open src/arduino/motor_control.ino in Arduino IDE.

Install required libraries (Servo, etc.).

Upload to Arduino Uno.

Usage
Calibration
Before running, calibrate the HSV color ranges for your lighting:

bash
python3 src/utils/calibrate_color.py
Use the trackbars to find the best values for red, green, and magenta. Save them in main.py.

Running the Vehicle
Power up Raspberry Pi and Arduino.

SSH into Pi (or use a monitor).

Start the main program:

bash
python3 src/main.py
Press the physical start button (connected to Arduino) to begin.

Engineering Journal
The engineering journal (in docs/engineering_journal.pdf) documents our entire design process:

Initial concepts and sketches.

Component selection trade‑offs.

Iterations and test results (with photos/videos).

Challenges faced and solutions.

Final design justifications.

It follows the WRO scoring rubric (see Appendix C of the rules).
