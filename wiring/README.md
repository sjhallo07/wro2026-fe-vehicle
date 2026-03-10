# Wiring

This directory contains the wiring diagram and notes for the vehicle's
electrical system.

## Files

| File | Description |
|------|-------------|
| `wiring_diagram.pdf` | Full wiring diagram (motors, servo, sensors, power) |

## Power Distribution Summary

```
LiPo 3S (11.1 V)
  ├── Cytron 13A Motor Driver → DC Drive Motor
  ├── LM2596 Step-down (5 V/3A)
  │     ├── Arduino Uno (via VIN)
  │     ├── MPU6050 IMU (3.3 V via Arduino)
  │     ├── HC-SR04 × 2
  │     └── MG996R Servo (via Arduino 5 V rail)
  └── (Independent motor power switch)

USB Power Bank (5 V)
  └── Raspberry Pi 4 (via USB-C)
      └── Pi Camera v2 (CSI ribbon)
```

## Arduino Pin Summary

| Pin | Connection |
|-----|------------|
| 2   | Encoder (Hall effect) interrupt |
| 3   | Servo signal (MG996R) |
| 5   | Motor PWM (Cytron) |
| 6   | Motor direction (Cytron) |
| 7   | Front HC-SR04 TRIG |
| 8   | Front HC-SR04 ECHO |
| 9   | Side HC-SR04 TRIG |
| 10  | Side HC-SR04 ECHO |
| A4  | MPU6050 SDA |
| A5  | MPU6050 SCL |

## Raspberry Pi GPIO

The Raspberry Pi communicates with the Arduino exclusively over USB serial;
no GPIO pins are used for vehicle control.
