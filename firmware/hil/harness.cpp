// Firmware replay harness: runs the unmodified veriflush.ino logic on the host and feeds it, once per
// simulated second, the observations (pulses, temperatures, switches, pressure) that the Python
// simulation produced for the same event. Prints the firmware's serial output.
//   usage: harness < trace.txt     trace rows: t pulses tt100 tt101 ls_open ls_closed p_kpa
#include "arduino_mock.h"
#include "../veriflush/veriflush.ino"

int main() {
  setup();
  MOCK.pins[PIN_START] = LOW;                 // press START
  MOCK.ms = 0;
  loop();
  MOCK.pins[PIN_START] = HIGH;
  int t;
  long pulses;
  float tt100, tt101, p;
  int lso, lsc;
  while (std::scanf("%d %ld %f %f %d %d %f", &t, &pulses, &tt100, &tt101, &lso, &lsc, &p) == 7) {
    for (long k = 0; k < pulses; k++) MOCK.isr();
    MOCK.t100 = tt100;
    MOCK.t101 = tt101;
    MOCK.pins[PIN_LS_OPEN] = lso ? LOW : HIGH;
    MOCK.pins[PIN_LS_CLOSED] = lsc ? LOW : HIGH;
    MOCK.analog = (int)std::lround(p / 10.0 * 1023.0);
    MOCK.ms = 1000UL * (unsigned long)t;
    loop();
    if (!running) break;
  }
  return 0;
}
