/*
 * ============================================================
 *  GESTURE CONTROLLED CAR — RECEIVER (CAR)
 *  File   : receiver.ino
 *  Folder : 01_hardware/receiver/
 * ============================================================
 *  Hardware : Arduino Nano + nRF24L01+ (via adapter) +
 *             L298N Motor Driver + 4× DC Gear Motors
 *
 *  Required Libraries:
 *    • RF24 by TMRh20  (v1.4.x)
 *
 *  Pin Connections:
 *    nRF24L01+ : CE→D9  CSN→D10  SCK→D13  MOSI→D11  MISO→D12
 *    L298N     : ENA→D3(PWM) IN1→D2 IN2→D4
 *                ENB→D5(PWM) IN3→D7 IN4→D8
 *    Power     : LiPo 7.4V → L298N motor supply
 *                Recommended → separate 5V buck converter
 *                for Arduino Nano + nRF adapter
 *
 *  Motor wiring:
 *    OUT1/OUT2 → Left  Front + Left  Rear (parallel)
 *    OUT3/OUT4 → Right Front + Right Rear (parallel)
 * ============================================================
 */

#include <SPI.h>
#include <RF24.h>

// ── Pin Definitions ──────────────────────────────────────────
#define NRF_CE_PIN   9
#define NRF_CSN_PIN  10

// L298N channel A — left motors
#define ENA   3    // PWM speed
#define IN1   2    // Forward
#define IN2   4    // Reverse

// L298N channel B — right motors
#define ENB   5    // PWM speed
#define IN3   7    // Forward
#define IN4   8    // Reverse

// ── Safety timeout ────────────────────────────────────────────
const unsigned long SIGNAL_TIMEOUT_MS = 500;  // Stop if no packet for 500 ms
unsigned long lastSignalTime = 0;

// ── Objects ──────────────────────────────────────────────────
RF24 radio(NRF_CE_PIN, NRF_CSN_PIN);

// ── RF Pipe Address (must match transmitter exactly) ──────────
const byte PIPE_ADDRESS[6] = "GCCAR";

// ── Data Packet (must match transmitter struct exactly) ───────
struct ControlPacket {
  int16_t xAngle;
  int16_t yAngle;
  uint8_t mode;
  uint8_t throttle;
  uint8_t steering;
};

ControlPacket rxData;

// ─────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(9600);

  // Motor pins
  pinMode(ENA, OUTPUT); pinMode(IN1, OUTPUT); pinMode(IN2, OUTPUT);
  pinMode(ENB, OUTPUT); pinMode(IN3, OUTPUT); pinMode(IN4, OUTPUT);
  stopAllMotors();  // Safety: start stopped

  // nRF24L01+
  if (!radio.begin()) {
    Serial.println(F("[ERROR] nRF24L01+ not detected!"));
    while (1);
  }
  radio.setPALevel(RF24_PA_HIGH);
  radio.setDataRate(RF24_250KBPS);
  radio.setChannel(108);
  radio.openReadingPipe(1, PIPE_ADDRESS);
  radio.startListening();   // RX mode

  Serial.println(F("Car Receiver READY!"));
}

// ─────────────────────────────────────────────────────────────
void loop() {
  // ── Signal timeout safety ──────────────────────────────────
  if (millis() - lastSignalTime > SIGNAL_TIMEOUT_MS) {
    stopAllMotors();
  }

  // ── Read incoming packet ───────────────────────────────────
  if (radio.available()) {
    radio.read(&rxData, sizeof(ControlPacket));
    lastSignalTime = millis();
    executeMovement(rxData.mode, rxData.throttle, rxData.steering);

    Serial.print(F("Mode:")); Serial.print(rxData.mode);
    Serial.print(F(" Thr:")); Serial.print(rxData.throttle);
    Serial.print(F(" Str:")); Serial.println(rxData.steering);
  }
}

// ── Movement dispatcher ───────────────────────────────────────
void executeMovement(uint8_t mode, uint8_t spd, uint8_t steer) {
  switch (mode) {
    case 0: stopAllMotors();             break;
    case 1: moveForward(spd, steer);     break;
    case 2: moveBackward(spd, steer);    break;
    case 3: pivotLeft(spd);              break;
    case 4: pivotRight(spd);             break;
    default: stopAllMotors();
  }
}

// ── Forward with differential steering ───────────────────────
void moveForward(uint8_t spd, uint8_t steer) {
  int lSpd = spd, rSpd = spd;
  if      (steer > 147) rSpd = map(steer, 147, 255, spd, spd / 3);
  else if (steer < 107) lSpd = map(steer, 107,   0, spd, spd / 3);
  lSpd = constrain(lSpd, 0, 255);
  rSpd = constrain(rSpd, 0, 255);

  digitalWrite(IN1, HIGH); digitalWrite(IN2, LOW);  analogWrite(ENA, lSpd);
  digitalWrite(IN3, HIGH); digitalWrite(IN4, LOW);  analogWrite(ENB, rSpd);
}

// ── Backward with differential steering ──────────────────────
void moveBackward(uint8_t spd, uint8_t steer) {
  int lSpd = spd, rSpd = spd;
  if      (steer > 147) rSpd = map(steer, 147, 255, spd, spd / 3);
  else if (steer < 107) lSpd = map(steer, 107,   0, spd, spd / 3);
  lSpd = constrain(lSpd, 0, 255);
  rSpd = constrain(rSpd, 0, 255);

  digitalWrite(IN1, LOW); digitalWrite(IN2, HIGH);  analogWrite(ENA, lSpd);
  digitalWrite(IN3, LOW); digitalWrite(IN4, HIGH);  analogWrite(ENB, rSpd);
}

// ── Pivot left (left motors back, right motors fwd) ───────────
void pivotLeft(uint8_t spd) {
  digitalWrite(IN1, LOW);  digitalWrite(IN2, HIGH); analogWrite(ENA, spd);
  digitalWrite(IN3, HIGH); digitalWrite(IN4, LOW);  analogWrite(ENB, spd);
}

// ── Pivot right (left motors fwd, right motors back) ──────────
void pivotRight(uint8_t spd) {
  digitalWrite(IN1, HIGH); digitalWrite(IN2, LOW);  analogWrite(ENA, spd);
  digitalWrite(IN3, LOW);  digitalWrite(IN4, HIGH); analogWrite(ENB, spd);
}

// ── Full stop ─────────────────────────────────────────────────
void stopAllMotors() {
  digitalWrite(IN1, LOW); digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW); digitalWrite(IN4, LOW);
  analogWrite(ENA, 0);    analogWrite(ENB, 0);
}
