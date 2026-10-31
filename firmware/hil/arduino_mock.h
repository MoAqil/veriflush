// Minimal host stand-ins for Arduino.h, OneWire, DallasTemperature and Servo, so veriflush.ino
// compiles with g++ and can be fed sensor traces from the Python simulation (firmware replay test).
// Only what veriflush.ino uses is implemented.
#pragma once
#include <cctype>
#include <cmath>
#include <cstdint>
#include <cstdio>

using std::isnan;
typedef uint8_t byte;
#define INPUT_PULLUP 2
#define INPUT 0
#define LOW 0
#define HIGH 1
#define FALLING 2
#define A0 14
#define DEVICE_DISCONNECTED_C -127
#define digitalPinToInterrupt(p) (p)
#define noInterrupts()
#define interrupts()
template <class A, class B> auto max(A a, B b) -> decltype(a + b) { return a > b ? a : b; }

class __FlashStringHelper;
#define F(s) (reinterpret_cast<const __FlashStringHelper *>(s))

struct MockState {
  unsigned long ms = 0;
  int pins[20] = {1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1};
  int analog = 0;
  float t100 = 20, t101 = 20;
  int servo_deg = -1;
  void (*isr)() = nullptr;
};
inline MockState MOCK;

inline unsigned long millis() { return MOCK.ms; }
inline void pinMode(int, int) {}
inline int digitalRead(int p) { return MOCK.pins[p]; }
inline int analogRead(int) { return MOCK.analog; }
inline void attachInterrupt(int, void (*f)(), int) { MOCK.isr = f; }

struct MockSerial {
  void begin(long) {}
  int available() { return 0; }
  int read() { return -1; }
  void print(const __FlashStringHelper *s) { std::fputs(reinterpret_cast<const char *>(s), stdout); }
  void print(const char *s) { std::fputs(s, stdout); }
  void print(char c) { std::putchar(c); }
  void print(int v) { std::printf("%d", v); }
  void print(unsigned v) { std::printf("%u", v); }
  void print(long v) { std::printf("%ld", v); }
  void print(unsigned long v) { std::printf("%lu", v); }
  void print(bool v) { std::printf("%d", v ? 1 : 0); }
  void print(double v, int d = 2) {
    if (std::isnan(v)) std::fputs("nan", stdout);
    else std::printf("%.*f", d, v);
  }
  template <class T> void println(T v) { print(v); std::putchar('\n'); }
  void println(double v, int d) { print(v, d); std::putchar('\n'); }
  void println() { std::putchar('\n'); }
};
inline MockSerial Serial;

typedef uint8_t DeviceAddress[8];
struct OneWire {
  explicit OneWire(int) {}
};
struct DallasTemperature {
  explicit DallasTemperature(OneWire *) {}
  void begin() {}
  void setResolution(int) {}
  void setWaitForConversion(bool) {}
  void requestTemperatures() {}
  int getDeviceCount() { return 2; }
  bool getAddress(DeviceAddress a, int i) { a[0] = 0x28; a[1] = (uint8_t)i; return true; }
  float getTempC(const DeviceAddress a) { return a[1] == 0 ? MOCK.t100 : MOCK.t101; }
};
struct Servo {
  void attach(int) {}
  void write(int deg) { MOCK.servo_deg = deg; }
};
