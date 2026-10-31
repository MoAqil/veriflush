// VeriFlush Rev-B rig controller: port of model/decisions.py (VeriFlush rules) to Arduino Uno R3.
//
// STATUS: mirrors the Python decision engine. Not yet run on the physical rig. Needs libraries:
// OneWire, DallasTemperature, Servo.
//
// Pins: FT-101 pulses D2 (INT0) | 1-Wire bus D4 (TT-100 + TT-101, 4.7k pull-up) | LS-OPEN D5 |
//       LS-CLOSED D6 (INPUT_PULLUP, switch to GND = made) | XV-101 servo D9 (6 V from XL4015) |
//       optional low-range pressure transducer A0 (the 0-3 bar PI-101 gauge cannot be read).
// Serial 115200: one CSV line per second, then a VERDICT line.  Start a flush with the START button (D7) or by
// sending 'S'. Tested in the Wokwi project in ../../wokwi (see wokwi/README.md for what was and was not verified).
#include <OneWire.h>
#include <DallasTemperature.h>
#include <Servo.h>

// ---------------- configuration (keep in sync with model/params.py) ----------------
const float K_PULSES_PER_L   = 5880.0;   // calibrate with a jug
const float V_CFG_L          = 0.3016;   // configured branch volume (6 m x 8 mm); 0.4021 for 8 m
const float V_UP_CFG_L       = 0.040;    // configured upstream dead volume
const float N_TARGET         = 3.0;
const float Q_DESIGN_LPM     = 0.60;
const float MIN_CONTRAST_C   = 1.5;
const float PHI_ARRIVAL      = 0.5;
const float PHI_PLATEAU      = 0.85;
const float PLATEAU_HOLD_S   = 10;
const float RATIO_WARN_HIGH  = 1.4, RATIO_WARN_LOW = 0.6, RATIO_FAIL = 3.0;
const float NO_FLOW_LPM      = 0.05;
const float BLOCK_CONFIRM_S  = 30, DROPOUT_CONFIRM_S = 10, VALVE_CONFIRM_S = 3;
const float DP_DRAW_MIN_KPA  = 0.15;
#ifndef VF_HAVE_PRESSURE
#define VF_HAVE_PRESSURE 0                  // 1 only with a low-range (0-10 kPa) transducer on A0
#endif
const bool  HAVE_PRESSURE    = VF_HAVE_PRESSURE;
const float T_VALVE_CMD_S    = 2, T_MAX_S = 300;
const int   SERVO_OPEN_DEG   = 90, SERVO_CLOSED_DEG = 0;

const byte PIN_FLOW = 2, PIN_ONEWIRE = 4, PIN_LS_OPEN = 5, PIN_LS_CLOSED = 6, PIN_START = 7, PIN_SERVO = 9;
const byte TT100_INDEX = 0, TT101_INDEX = 1;   // bus search order; check the boot printout once and swap if needed

OneWire oneWire(PIN_ONEWIRE);
DallasTemperature temps(&oneWire);
DeviceAddress addr100, addr101;
Servo xv101;
volatile unsigned long pulses = 0;
void onPulse() { pulses++; }

enum Verdict { NONE, VERIFIED, FAILED, UNCERTAIN };
// ---------------- state ----------------
bool running = false, cmdOpen = false;
float t = 0, v = 0;                       // s, metered litres
float pre100 = 0, pre101 = 0, preP = 0; int nPre100 = 0, nPre101 = 0, nPreP = 0;
float t0_100 = NAN, t0_101 = NAN, p0 = NAN, contrast = NAN;
bool endpointOk = true, weak = false, hadFlow = false, dropout = false;
float vArr = NAN, phi = NAN, plateauS = 0, zeroFlowS = 0, lastGoodQ = NAN, qSum = 0; int qN = 0;
int same101 = 0; float last101 = NAN;
byte valveState = 0;                      // 0 unknown,1 pending,2 confirmed,3 not_open,4 partial,5 switch_fault
unsigned long lastTick = 0;

bool validTemp(float x) { return !isnan(x) && x != DEVICE_DISCONNECTED_C && x != 85.0 && x >= -10 && x <= 60; }
float vEst() { return isnan(vArr) ? NAN : max(vArr - V_UP_CFG_L, 0.2 * V_CFG_L); }
float ratio() { return vEst() / V_CFG_L; }
float nEff() { return isnan(vArr) ? v / V_CFG_L : v / vEst(); }
float readPressureKpa() { return HAVE_PRESSURE ? analogRead(A0) * (10.0 / 1023.0) : NAN; }  // 0-10 kPa, calibrate

void warn(const __FlashStringHelper* w) { Serial.print(F("WARN,")); Serial.print(t, 0); Serial.print(','); Serial.println(w); }

void finish(int vd, const __FlashStringHelper* reason) {   // int, not Verdict: Arduino puts auto-prototypes above the enum
  cmdOpen = false; xv101.write(SERVO_CLOSED_DEG); running = false;
  Serial.print(F("VERDICT,"));
  Serial.print(vd == VERIFIED ? F("Verified") : vd == FAILED ? F("Failed") : F("Uncertain"));
  Serial.print(','); Serial.print(t, 0); Serial.print(','); Serial.print(v, 3);
  Serial.print(','); Serial.print(ratio(), 2); Serial.print(','); Serial.print(nEff(), 2);
  Serial.print(','); Serial.println(reason);
}

void startFlush() {
  t = 0; v = 0; pre100 = pre101 = preP = 0; nPre100 = nPre101 = nPreP = 0;
  t0_100 = t0_101 = p0 = contrast = vArr = phi = lastGoodQ = last101 = NAN;
  endpointOk = true; weak = hadFlow = dropout = false; plateauS = zeroFlowS = qSum = 0; qN = 0; same101 = 0; valveState = 0;
  noInterrupts(); pulses = 0; interrupts();
  running = true;
  Serial.println(F("t_s,cmd,pulses,q_lpm,v_l,p_kpa,tt100_c,tt101_c,ls_open,ls_closed,phi"));
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_FLOW, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(PIN_FLOW), onPulse, FALLING);
  pinMode(PIN_LS_OPEN, INPUT_PULLUP); pinMode(PIN_LS_CLOSED, INPUT_PULLUP); pinMode(PIN_START, INPUT_PULLUP);
  xv101.attach(PIN_SERVO); xv101.write(SERVO_CLOSED_DEG);
  temps.begin(); temps.setResolution(12); temps.setWaitForConversion(false);
  temps.getAddress(addr100, TT100_INDEX); temps.getAddress(addr101, TT101_INDEX);
  temps.setWaitForConversion(true); temps.requestTemperatures(); temps.setWaitForConversion(false);
  Serial.print(F("# 1-Wire devices: ")); Serial.print(temps.getDeviceCount());
  Serial.print(F(" | TT-100 ")); Serial.print(temps.getTempC(addr100), 2);
  Serial.print(F(" C | TT-101 ")); Serial.print(temps.getTempC(addr101), 2); Serial.println(F(" C"));
  Serial.println(F("# VeriFlush Rev-B ready. Press START (or send S)."));
}

void loop() {
  if (!running && ((Serial.available() && toupper(Serial.read()) == 'S') || digitalRead(PIN_START) == LOW)) startFlush();
  if (!running || millis() - lastTick < 1000) return;
  lastTick = millis();
  const float dt = 1.0;
  t += dt;
  // ---- sample
  noInterrupts(); unsigned long n = pulses; pulses = 0; interrupts();
  float q = n / K_PULSES_PER_L / dt * 60.0;
  float tt100 = temps.getTempC(addr100), tt101 = temps.getTempC(addr101);
  temps.requestTemperatures();                         // next conversion ready within 750 ms
  float pk = readPressureKpa();
  int lsOpen = digitalRead(PIN_LS_OPEN) == LOW, lsClosed = digitalRead(PIN_LS_CLOSED) == LOW;

  if (t < T_VALVE_CMD_S) {                             // ---- phase 0: baseline
    if (validTemp(tt100)) { pre100 += tt100; nPre100++; }
    if (validTemp(tt101)) { pre101 += tt101; nPre101++; }
    if (!isnan(pk)) { preP += pk; nPreP++; }
  } else if (!cmdOpen && valveState == 0) {            // ---- open XV-101
    cmdOpen = true; xv101.write(SERVO_OPEN_DEG);
    t0_100 = nPre100 ? pre100 / nPre100 : NAN; t0_101 = nPre101 ? pre101 / nPre101 : NAN; p0 = nPreP ? preP / nPreP : NAN;
    if (isnan(t0_101) || isnan(t0_100)) endpointOk = false;
    else { contrast = t0_101 - t0_100; weak = fabs(contrast) < MIN_CONTRAST_C; }
  } else {
    v += q * dt / 60.0;
    if (q > NO_FLOW_LPM) { hadFlow = true; lastGoodQ = q; zeroFlowS = 0; qSum += q; qN++; } else zeroFlowS += dt;
    // valve feedback
    if (t >= T_VALVE_CMD_S + VALVE_CONFIRM_S && valveState <= 1) {
      if (lsOpen && !lsClosed) valveState = 2; else if (lsClosed) valveState = 3; else valveState = 1;
    }
    if (valveState == 1 && qN >= 5) {
      if (qSum / qN < 0.8 * Q_DESIGN_LPM) { valveState = 4; warn(F("LS-OPEN not made and flow low: XV-101 partly open?")); }
      else { valveState = 5; warn(F("LS-OPEN not made although flow normal: switch/wiring fault")); }
    }
    // endpoint health
    if (endpointOk && !validTemp(tt101)) endpointOk = false;
    if (endpointOk) { same101 = (tt101 == last101) ? same101 + 1 : 0; last101 = tt101; }
    if (endpointOk && !weak && validTemp(tt100)) {
      float den = tt100 - t0_101;
      phi = fabs(den) > 1e-6 ? (tt101 - t0_101) / den : NAN;
      if (isnan(vArr) && phi >= PHI_ARRIVAL) {
        vArr = v;
        if (ratio() > RATIO_WARN_HIGH) warn(F("branch volume estimate high: diversion/leak, meter over-reading or V_cfg too small"));
        else if (ratio() < RATIO_WARN_LOW) warn(F("branch volume estimate low: meter under-reading or V_cfg too large"));
      }
      plateauS = (phi >= PHI_PLATEAU) ? plateauS + dt : 0;
      if (isnan(vArr) && same101 >= 15 && v > 1.5 * (V_CFG_L + V_UP_CFG_L)) endpointOk = false;   // frozen
    }
    float dp = (isnan(pk) || isnan(p0)) ? NAN : p0 - pk;
    bool drawing = !isnan(dp) && dp > DP_DRAW_MIN_KPA;
    if (hadFlow && !dropout && zeroFlowS >= DROPOUT_CONFIRM_S && drawing) { dropout = true; warn(F("FT-101 signal lost while branch still draws")); }

    // ---- decisions (same order as decisions.py)
    bool usable = endpointOk && !weak;
    float need = N_TARGET * V_CFG_L;
    if (valveState == 3 && zeroFlowS >= 10) return finish(FAILED, F("XV-101 did not open"));
    if (!hadFlow && zeroFlowS >= BLOCK_CONFIRM_S && valveState != 3)
      return drawing ? finish(UNCERTAIN, F("no pulses but pressure drawn: flow sensor fault"))
                     : finish(FAILED, F("no flow and no pressure drop: blockage or closed isolation valve"));
    if (!isnan(vArr) && ratio() > RATIO_FAIL) return finish(FAILED, F("fresh water needed > 3x configured volume: water not reaching endpoint"));
    if (usable && isnan(vArr) && !dropout && v > RATIO_FAIL * (V_CFG_L + V_UP_CFG_L))
      return finish(FAILED, F("metered water but no endpoint response"));
    if (usable && !isnan(vArr) && !dropout && nEff() >= N_TARGET && plateauS >= PLATEAU_HOLD_S)
      return valveState == 2 ? finish(VERIFIED, F("valve confirmed; endpoint reached feed temperature; target volumes exchanged"))
                             : finish(UNCERTAIN, F("exchange evidence complete but valve feedback inconsistent"));
    if (!usable && v >= need) return finish(UNCERTAIN, F("metered target reached but endpoint evidence unavailable"));
    if (dropout && usable) {
      float est = v + (isnan(lastGoodQ) ? 0 : lastGoodQ * zeroFlowS / 60.0);
      if (plateauS >= PLATEAU_HOLD_S && est / V_CFG_L >= N_TARGET) return finish(UNCERTAIN, F("endpoint fresh but volume only estimated (FT-101 failed)"));
    }
    if (t >= T_MAX_S) {
      if (!usable || dropout) return finish(UNCERTAIN, F("time limit; evidence unavailable"));
      return isnan(vArr) ? finish(FAILED, F("time limit; fresh water never reached endpoint"))
                         : finish(FAILED, F("time limit; too few endpoint-anchored volumes"));
    }
  }
  // ---- log
  Serial.print(t, 0); Serial.print(','); Serial.print(cmdOpen); Serial.print(','); Serial.print(n); Serial.print(',');
  Serial.print(q, 3); Serial.print(','); Serial.print(v, 4); Serial.print(','); Serial.print(pk, 2); Serial.print(',');
  Serial.print(tt100, 4); Serial.print(','); Serial.print(tt101, 4); Serial.print(','); Serial.print(lsOpen); Serial.print(',');
  Serial.print(lsClosed); Serial.print(','); Serial.println(phi, 3);
}
