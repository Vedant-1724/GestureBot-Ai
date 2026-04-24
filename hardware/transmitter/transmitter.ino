/*
 * ============================================================
 *  GESTURE CONTROLLED CAR — TRANSMITTER
 *  File   : transmitter.ino
 *  Folder : 01_hardware/transmitter/
 * ============================================================
 *  Hardware : Arduino Nano + MPU6050 + nRF24L01+ (via adapter)
 *
 *  Required Libraries (install via Library Manager):
 *    • RF24 by TMRh20          (v1.4.x)
 *    • MPU6050 by Electronic Cats
 *
 *  Pin Connections:
 *    MPU6050 : SDA→A4  SCL→A5  VCC→5V  GND→GND
 *    nRF24L01+: CE→D9  CSN→D10  SCK→D13  MOSI→D11  MISO→D12
 *    Power   : Recommended → regulated 5V to Nano 5V pin
 *              Alternate   → 7–12V battery to VIN
 * ============================================================
 */

#include <SPI.h>
#include <RF24.h>
#include <Wire.h>
#include <MPU6050.h>

// ── Pin Definitions ──────────────────────────────────────────
#define NRF_CE_PIN   9
#define NRF_CSN_PIN  10

// ── Objects ──────────────────────────────────────────────────
RF24    radio(NRF_CE_PIN, NRF_CSN_PIN);
MPU6050 mpu;

// ── RF Pipe Address (must match receiver exactly) ─────────────
const byte PIPE_ADDRESS[6] = "GCCAR";

// ── Data Packet (must match receiver struct exactly) ──────────
struct ControlPacket {
  int16_t xAngle;    // Forward/Backward  –90 to +90 degrees
  int16_t yAngle;    // Left/Right         –90 to +90 degrees
  uint8_t mode;      // 0=STOP 1=FWD 2=REV 3=LEFT 4=RIGHT
  uint8_t throttle;  // Motor speed  0–255
  uint8_t steering;  // Steering mix 0–255  (127 = straight)
};

ControlPacket txData;

// ── Calibration offsets (filled by calibrateMPU) ─────────────
int16_t ax_offset = 0;
int16_t ay_offset = 0;
int16_t az_offset = 0;

// ── Dead-zone (degrees) — prevents jitter at rest ─────────────
const int DEAD_ZONE = 12;

// ─────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(9600);
  Wire.begin();

  // --- MPU6050 init ---
  Serial.println(F("Initializing MPU6050..."));
  mpu.initialize();
  if (!mpu.testConnection()) {
    Serial.println(F("[ERROR] MPU6050 not found. Check wiring!"));
    while (1);
  }
  Serial.println(F("MPU6050 OK"));

  // --- Calibrate (keep transmitter flat for 2 s) ---
  Serial.println(F("Calibrating... Keep transmitter FLAT for 2 seconds."));
  delay(2000);
  calibrateMPU();
  Serial.println(F("Calibration done!"));

  // --- nRF24L01+ init ---
  if (!radio.begin()) {
    Serial.println(F("[ERROR] nRF24L01+ not detected. Check wiring!"));
    while (1);
  }
  radio.setPALevel(RF24_PA_HIGH);
  radio.setDataRate(RF24_250KBPS);
  radio.setChannel(108);             // Above WiFi channels
  radio.setRetries(5, 15);
  radio.openWritingPipe(PIPE_ADDRESS);
  radio.stopListening();             // TX mode

  Serial.println(F("Transmitter READY — Tilt to drive!"));
  Serial.println(F("===================================="));
}

// ─────────────────────────────────────────────────────────────
void loop() {
  int16_t ax, ay, az, gx, gy, gz;
  mpu.getMotion6(&ax, &ay, &az, &gx, &gy, &gz);

  // Apply calibration
  ax -= ax_offset;
  ay -= ay_offset;

  // Raw accel ~±17000 → map to ±90 degrees
  int16_t xAngle = constrain(map(ax, -17000, 17000, -90, 90), -90, 90);
  int16_t yAngle = constrain(map(ay, -17000, 17000, -90, 90), -90, 90);

  // ── Decide movement mode ────────────────────────────────────
  if (abs(xAngle) <= DEAD_ZONE && abs(yAngle) <= DEAD_ZONE) {
    // STOP
    txData.mode     = 0;
    txData.throttle = 0;
    txData.steering = 127;

  } else if (abs(xAngle) >= abs(yAngle)) {
    // FORWARD or BACKWARD (dominant tilt)
    if (xAngle > DEAD_ZONE) {
      txData.mode     = 1;   // FORWARD
      txData.throttle = (uint8_t)map(xAngle,  DEAD_ZONE, 90, 80, 255);
    } else {
      txData.mode     = 2;   // BACKWARD
      txData.throttle = (uint8_t)map(-xAngle, DEAD_ZONE, 90, 80, 255);
    }
    txData.steering = (uint8_t)map(yAngle, -90, 90, 0, 255);

  } else {
    // PIVOT LEFT or PIVOT RIGHT (dominant side tilt)
    if (yAngle < -DEAD_ZONE) {
      txData.mode     = 3;   // LEFT
      txData.throttle = (uint8_t)map(-yAngle, DEAD_ZONE, 90, 80, 200);
    } else {
      txData.mode     = 4;   // RIGHT
      txData.throttle = (uint8_t)map(yAngle,  DEAD_ZONE, 90, 80, 200);
    }
    txData.steering = (yAngle < 0) ? 0 : 255;
  }

  txData.xAngle = xAngle;
  txData.yAngle = yAngle;

  // ── Transmit ────────────────────────────────────────────────
  bool ok = radio.write(&txData, sizeof(ControlPacket));

  // ── Serial debug ────────────────────────────────────────────
  Serial.print(F("xA:")); Serial.print(xAngle);
  Serial.print(F(" yA:")); Serial.print(yAngle);
  Serial.print(F(" Mode:")); Serial.print(txData.mode);
  Serial.print(F(" Thr:")); Serial.print(txData.throttle);
  Serial.print(F(" TX:")); Serial.println(ok ? F("OK") : F("FAIL"));

  delay(20);   // 50 Hz update rate
}

// ── Calibration helper ────────────────────────────────────────
void calibrateMPU() {
  const int SAMPLES = 200;
  int32_t sx = 0, sy = 0, sz = 0;
  for (int i = 0; i < SAMPLES; i++) {
    int16_t ax, ay, az, gx, gy, gz;
    mpu.getMotion6(&ax, &ay, &az, &gx, &gy, &gz);
    sx += ax; sy += ay; sz += az;
    delay(5);
  }
  ax_offset = sx / SAMPLES;
  ay_offset = sy / SAMPLES;
  az_offset = (sz / SAMPLES) - 16384;   // Remove 1g from Z

  Serial.print(F("Offsets → ax:")); Serial.print(ax_offset);
  Serial.print(F(" ay:")); Serial.print(ay_offset);
  Serial.print(F(" az:")); Serial.println(az_offset);
}
