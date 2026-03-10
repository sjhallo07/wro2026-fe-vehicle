/*
 * wro2026_arduino.ino
 * Arduino Uno sketch for WRO 2026 Future Engineers – low-level vehicle control.
 *
 * Responsibilities
 * ----------------
 *  - Receive ASCII commands from the Raspberry Pi via USB serial (115200 baud).
 *  - Control the drive DC motor via PWM (Cytron 13A driver: DIR + PWM pins).
 *  - Control the steering servo (MG996R).
 *  - Read wheel encoder (Hall effect) for speed feedback.
 *  - Read two HC-SR04 ultrasonic sensors for emergency obstacle detection.
 *  - Report "OK\n" or "ERR\n" for each received command.
 *
 * Pin Assignment
 * --------------
 *  2  – Encoder interrupt (Hall effect sensor)
 *  3  – Steering servo signal
 *  5  – Motor PWM (Cytron PWM pin)
 *  6  – Motor direction (Cytron DIR pin)
 *  7  – Front ultrasonic TRIG
 *  8  – Front ultrasonic ECHO
 *  9  – Side ultrasonic TRIG
 * 10  – Side ultrasonic ECHO
 *
 * Command Protocol
 * ----------------
 *  "FORWARD\n"  – Drive forward at cruise speed.
 *  "BACK\n"     – Drive backward at reverse speed.
 *  "STOP\n"     – Stop motor and centre steering.
 *  "LEFT n\n"   – Steer left n degrees (0–90).
 *  "RIGHT n\n"  – Steer right n degrees (0–90).
 *
 * The sketch also performs autonomous emergency stop if the front ultrasonic
 * sensor detects an obstacle closer than OBSTACLE_DISTANCE_CM.
 */

#include <Servo.h>

// ---------------------------------------------------------------------------
// Pin definitions
// ---------------------------------------------------------------------------
static const uint8_t PIN_ENCODER    = 2;
static const uint8_t PIN_SERVO      = 3;
static const uint8_t PIN_MOTOR_PWM  = 5;
static const uint8_t PIN_MOTOR_DIR  = 6;
static const uint8_t PIN_FRONT_TRIG = 7;
static const uint8_t PIN_FRONT_ECHO = 8;
static const uint8_t PIN_SIDE_TRIG  = 9;
static const uint8_t PIN_SIDE_ECHO  = 10;

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------
static const uint32_t BAUD_RATE          = 115200;
static const uint8_t  CRUISE_PWM         = 160;  // 0–255
static const uint8_t  REVERSE_PWM        = 140;
static const uint8_t  SERVO_CENTRE       = 90;   // degrees (straight ahead)
static const uint8_t  SERVO_MAX_LEFT     = 55;   // hard-left limit
static const uint8_t  SERVO_MAX_RIGHT    = 125;  // hard-right limit
static const uint16_t OBSTACLE_DISTANCE_CM = 15; // emergency stop threshold

// ---------------------------------------------------------------------------
// Globals
// ---------------------------------------------------------------------------
Servo steeringServo;
volatile uint32_t encoderTicks = 0;

// ---------------------------------------------------------------------------
// ISR – encoder pulse counter
// ---------------------------------------------------------------------------
void encoderISR() {
  encoderTicks++;
}

// ---------------------------------------------------------------------------
// Motor helpers
// ---------------------------------------------------------------------------
void motorForward(uint8_t pwmVal) {
  digitalWrite(PIN_MOTOR_DIR, HIGH);
  analogWrite(PIN_MOTOR_PWM, pwmVal);
}

void motorBack(uint8_t pwmVal) {
  digitalWrite(PIN_MOTOR_DIR, LOW);
  analogWrite(PIN_MOTOR_PWM, pwmVal);
}

void motorStop() {
  analogWrite(PIN_MOTOR_PWM, 0);
}

// ---------------------------------------------------------------------------
// Steering helper
// ---------------------------------------------------------------------------
void setSteeringAngle(int angleDeg) {
  // angleDeg: negative = left, positive = right, 0 = centre
  int servoAngle = SERVO_CENTRE + angleDeg;
  servoAngle = constrain(servoAngle, SERVO_MAX_LEFT, SERVO_MAX_RIGHT);
  steeringServo.write(servoAngle);
}

// ---------------------------------------------------------------------------
// Ultrasonic distance measurement
// ---------------------------------------------------------------------------
uint16_t measureDistance(uint8_t trigPin, uint8_t echoPin) {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  unsigned long duration = pulseIn(echoPin, HIGH, 30000UL); // 30 ms timeout
  if (duration == 0) return 9999; // no echo → treat as clear
  return (uint16_t)(duration / 58); // cm
}

// ---------------------------------------------------------------------------
// Command parser
// ---------------------------------------------------------------------------
void handleCommand(const String& cmd) {
  if (cmd == "FORWARD") {
    motorForward(CRUISE_PWM);
    Serial.println("OK");

  } else if (cmd == "BACK") {
    motorBack(REVERSE_PWM);
    Serial.println("OK");

  } else if (cmd == "STOP") {
    motorStop();
    setSteeringAngle(0);
    Serial.println("OK");

  } else if (cmd.startsWith("LEFT ")) {
    int angle = cmd.substring(5).toInt();
    angle = constrain(angle, 0, 90);
    setSteeringAngle(-angle);
    Serial.println("OK");

  } else if (cmd.startsWith("RIGHT ")) {
    int angle = cmd.substring(6).toInt();
    angle = constrain(angle, 0, 90);
    setSteeringAngle(angle);
    Serial.println("OK");

  } else {
    Serial.println("ERR");
  }
}

// ---------------------------------------------------------------------------
// Arduino setup
// ---------------------------------------------------------------------------
void setup() {
  Serial.begin(BAUD_RATE);

  // Motor driver pins
  pinMode(PIN_MOTOR_PWM, OUTPUT);
  pinMode(PIN_MOTOR_DIR, OUTPUT);
  motorStop();

  // Servo
  steeringServo.attach(PIN_SERVO);
  setSteeringAngle(0);

  // Encoder
  pinMode(PIN_ENCODER, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(PIN_ENCODER), encoderISR, RISING);

  // Ultrasonic sensors
  pinMode(PIN_FRONT_TRIG, OUTPUT);
  pinMode(PIN_FRONT_ECHO, INPUT);
  pinMode(PIN_SIDE_TRIG, OUTPUT);
  pinMode(PIN_SIDE_ECHO, INPUT);

  Serial.println("READY");
}

// ---------------------------------------------------------------------------
// Arduino main loop
// ---------------------------------------------------------------------------
void loop() {
  // --- Emergency obstacle check -----------------------------------------
  uint16_t frontDist = measureDistance(PIN_FRONT_TRIG, PIN_FRONT_ECHO);
  if (frontDist < OBSTACLE_DISTANCE_CM) {
    motorStop();
    // Do not send anything here; the Pi controls the state machine.
  }

  // --- Serial command processing ----------------------------------------
  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    line.trim();
    if (line.length() > 0) {
      handleCommand(line);
    }
  }
}
