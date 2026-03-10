#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Basic color detection for WRO Future Engineers 2026.
This script runs on a Raspberry Pi, captures video, detects red, green and magenta
pillars, and sends simple commands to an Arduino via serial.
"""

import cv2
import numpy as np
import serial
import time

# Serial port configuration (adjust to your setup)
SERIAL_PORT = '/dev/ttyACM0'  # Typical port for Arduino
BAUD_RATE = 115200

# High-level action to low-level Arduino protocol mapping.
ACTION_TO_SERIAL = {
    "FORWARD": ("S90", "T1600"),
    "LEFT": ("S60", "T1550"),
    "RIGHT": ("S120", "T1550"),
    "STOP": ("T1500", "S90"),
}

# Initialize camera (use 0 for default camera, or adjust)
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)

# Connect to Arduino
try:
    arduino = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)  # Wait for connection to establish
    print("Connected to Arduino")
except:
    print("Could not connect to Arduino")
    arduino = None

# Define HSV color ranges (calibrate these with actual lighting)
# Red (hue wraps around 0/180)
red_lower1 = np.array([0, 100, 100])
red_upper1 = np.array([10, 255, 255])
red_lower2 = np.array([160, 100, 100])
red_upper2 = np.array([179, 255, 255])

# Green
green_lower = np.array([40, 50, 50])
green_upper = np.array([80, 255, 255])

# Magenta
magenta_lower = np.array([140, 50, 50])
magenta_upper = np.array([170, 255, 255])

def detect_color(frame, lower, upper):
    """Return binary mask for a given HSV color range."""
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, lower, upper)
    # Optional morphological operations can be added later if needed.
    return mask

def find_largest_contour_center(mask):
    """Find the largest contour in the mask and return its center (cx, cy)."""
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        c = max(contours, key=cv2.contourArea)
        if cv2.contourArea(c) > 500:  # Filter noise (adjust threshold)
            M = cv2.moments(c)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                return (cx, cy)
    return None

def decide_action(red_pos, green_pos, magenta_pos):
    """
    Very simple decision logic:
    - If magenta (parking delimiter) is detected, stop.
    - If red pillar is detected, turn right.
    - If green pillar is detected, turn left.
    - Otherwise go forward.
    In a real robot, replace this with a state machine.
    """
    if magenta_pos is not None:
        return "STOP"
    elif red_pos is not None:
        return "RIGHT"
    elif green_pos is not None:
        return "LEFT"
    else:
        return "FORWARD"

def send_command(cmd):
    """Send a high-level command to Arduino using S/T serial protocol."""
    if arduino:
        payloads = ACTION_TO_SERIAL.get(cmd, ACTION_TO_SERIAL["STOP"])
        for payload in payloads:
            arduino.write((payload + '\n').encode())
            print(f"Sent: {payload} ({cmd})")
            time.sleep(0.01)

# Main loop
try:
    last_command = None
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Detect colors
        mask_red1 = detect_color(frame, red_lower1, red_upper1)
        mask_red2 = detect_color(frame, red_lower2, red_upper2)
        mask_red = cv2.bitwise_or(mask_red1, mask_red2)

        mask_green = detect_color(frame, green_lower, green_upper)
        mask_magenta = detect_color(frame, magenta_lower, magenta_upper)

        # Find centers of largest objects
        red_center = find_largest_contour_center(mask_red)
        green_center = find_largest_contour_center(mask_green)
        magenta_center = find_largest_contour_center(mask_magenta)

        # Decide action
        command = decide_action(red_center, green_center, magenta_center)

        # Send command to Arduino only when action changes.
        if command != last_command:
            send_command(command)
            last_command = command

        # Optional display for debugging
        if red_center:
            cv2.circle(frame, red_center, 5, (0,0,255), -1)
        if green_center:
            cv2.circle(frame, green_center, 5, (0,255,0), -1)
        if magenta_center:
            cv2.circle(frame, magenta_center, 5, (255,0,255), -1)
        cv2.imshow('Detector', frame)

        # Press 'q' to quit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    cap.release()
    cv2.destroyAllWindows()
    if arduino:
        arduino.close()