// Basic Arduino sketch for driving throttle and steering from the Raspberry Pi.
// The protocol is text based:
//   S<angle> sets steering (0-180 degrees)
//   T<pwm>   sets throttle ESC output (1000-2000 microseconds)
// Example: "S90" centers the steering servo.

#if defined(__has_include)
#if __has_include(<stdint.h>)
#include <stdint.h>
#elif __has_include(<cstdint>)
#include <cstdint>
#endif
#endif

#ifndef UINT8_MAX
typedef unsigned char uint8_t;
#endif

#ifndef UINT32_MAX
typedef unsigned long uint32_t;
#endif

#if __has_include(<Servo.h>)
#include <Servo.h>
#elif __has_include(<ESP32Servo.h>)
#include <ESP32Servo.h>
#else
// IntelliSense fallback when Arduino library includePath is not configured.
class Servo
{
public:
    uint8_t attach(int) { return 0; }
    void write(int) {}
    void writeMicroseconds(int) {}
};
#endif

constexpr uint8_t kSteeringPin = 10;
constexpr uint8_t kThrottlePin = 9;
constexpr uint32_t kBaudRate = 115200;

Servo steeringServo;
Servo throttleServo;

int steeringAngle = 90;
int throttlePwm = 1500;

void setup()
{
    Serial.begin(kBaudRate);
    steeringServo.attach(kSteeringPin);
    throttleServo.attach(kThrottlePin);

    steeringServo.write(steeringAngle);
    throttleServo.writeMicroseconds(throttlePwm);

    Serial.println(F("ARDUINO_READY"));
}

void loop()
{
    if (!Serial.available())
    {
        return;
    }

    char prefix = Serial.read();
    String payload = Serial.readStringUntil('\n');
    int value = payload.toInt();

    if (prefix == 'S')
    {
        steeringAngle = constrain(value, 0, 180);
        steeringServo.write(steeringAngle);
        Serial.print(F("STEER:"));
        Serial.println(steeringAngle);
    }
    else if (prefix == 'T')
    {
        throttlePwm = constrain(value, 1000, 2000);
        throttleServo.writeMicroseconds(throttlePwm);
        Serial.print(F("THROTTLE:"));
        Serial.println(throttlePwm);
    }
}
