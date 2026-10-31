// VeriFlush rig emulator: Wokwi custom chip standing in for the Rev-B rig's hydraulics around the controller.
//  - reads the XV-101 servo signal (pulse width > 1000 us = open command),
//  - moves a virtual ball valve at 2 travel/s (90 deg in 0.5 s, as model/params.py),
//  - drives LS-OPEN / LS-CLOSED (active LOW, like microswitches to GND with INPUT_PULLUP),
//  - emits FT-101 Hall pulses at 5880 pulses/L x branch flow x meter bias.
// Sliders (chip controls): flow at full opening, valve jam position, meter bias, LS-OPEN wire break, FT-101 dropout.
// Endpoint/feed temperatures are NOT produced here: set them on the two DS18B20 parts during the run.
// SIMULATED. Flow vs opening uses a simple approximation of the Python model's valve curve (K ~ 1/x^4).
#include "wokwi-api.h"
#include <math.h>
#include <stdlib.h>

#define K_PULSES_PER_L 5880.0
#define TICK_US 1000

typedef struct {
  pin_t servo, ls_open, ls_closed, flow;
  uint32_t a_flow, a_jam, a_bias, a_lsbroken, a_dropout;
  uint64_t rise_ns;
  float target, pos, phase;
  int pulse_low;
} chip_t;

static void on_servo(void *user_data, pin_t pin, uint32_t value) {
  chip_t *c = (chip_t *)user_data;
  uint64_t now = get_sim_nanos();
  if (value) {
    c->rise_ns = now;
  } else if (c->rise_ns) {
    float width_us = (now - c->rise_ns) / 1000.0f;
    if (width_us > 400 && width_us < 2600) c->target = width_us > 1000 ? 1.0f : 0.0f;
  }
}

static void on_tick(void *user_data) {
  chip_t *c = (chip_t *)user_data;
  const float dt = TICK_US / 1e6f;
  // valve travel (jammed valve cannot pass its jam position)
  float jam = attr_read_float(c->a_jam);
  float goal = c->target > 0.5f ? jam : 0.0f;
  float step = 2.0f * dt;
  if (c->pos < goal) c->pos = fminf(goal, c->pos + step);
  else if (c->pos > goal) c->pos = fmaxf(goal, c->pos - step);
  // limit switches: LOW = made
  int broken = attr_read_float(c->a_lsbroken) > 0.5f;
  pin_write(c->ls_open, (c->pos >= 0.95f && !broken) ? LOW : HIGH);
  pin_write(c->ls_closed, c->pos <= 0.05f ? LOW : HIGH);
  // branch flow: ~ full flow above half opening, falling steeply below (approximation of K = K_open / x^4)
  float x4 = c->pos * c->pos * c->pos * c->pos;
  float q_lpm = attr_read_float(c->a_flow) * sqrtf(fminf(1.0f, 30.0f * x4));
  float f_hz = q_lpm * K_PULSES_PER_L / 60.0f * attr_read_float(c->a_bias);
  if (c->pulse_low) {                       // end of a 1 ms pulse
    pin_write(c->flow, HIGH);
    c->pulse_low = 0;
  }
  if (attr_read_float(c->a_dropout) > 0.5f) return;
  c->phase += f_hz * dt;
  if (c->phase >= 1.0f) {
    c->phase -= 1.0f;
    pin_write(c->flow, LOW);                // falling edge counted by the Uno interrupt
    c->pulse_low = 1;
  }
}

void chip_init(void) {
  chip_t *c = calloc(1, sizeof(chip_t));
  c->servo = pin_init("SERVO", INPUT);
  c->ls_open = pin_init("LS_OPEN", OUTPUT_HIGH);
  c->ls_closed = pin_init("LS_CLOSED", OUTPUT_LOW);
  c->flow = pin_init("FLOW", OUTPUT_HIGH);
  c->a_flow = attr_init_float("flowLpm", 0.63);
  c->a_jam = attr_init_float("valveJam", 1.0);
  c->a_bias = attr_init_float("meterBias", 1.0);
  c->a_lsbroken = attr_init_float("lsOpenBroken", 0);
  c->a_dropout = attr_init_float("flowDropout", 0);
  const pin_watch_config_t w = {.edge = BOTH, .pin_change = on_servo, .user_data = c};
  pin_watch(c->servo, &w);
  const timer_config_t t = {.callback = on_tick, .user_data = c};
  timer_start(timer_init(&t), TICK_US, true);
}
