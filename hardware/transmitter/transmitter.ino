/*
 * GC-Car Transmitter — Arduino Nano + MPU6050 + nRF24L01+
 * Reads hand tilt, maps to movement commands, sends via RF.
 * Pipe: "GCCAR", Channel 108, 250kbps
 */

#include <SPI.h>
#include <RF24.h>
#include <Wire.h>
#include <MPU6050.h>


#define NRF_CE_PIN   9
#define NRF_CSN_PIN  10


RF24    radio(NRF_CE_PIN, NRF_CSN_PIN);
MPU6050 mpu;


const byte PIPE_ADDRESS[6] = "GCCAR";


struct ControlPacket {
  int16_t xAngle;    // Forward/Backward  –90 to +90 degrees
  int16_t yAngle;    // Left/Right         –90 to +90 degrees
  uint8_t mode;      // 0=STOP 1=FWD 2=REV 3=LEFT 4=RIGHT
  uint8_t throttle;  // Motor speed  0–255
  uint8_t steering;  // Steering mix 0–255  (127 = straight)
};

ControlPacket txData;


int16_t ax_offset = 0;
int16_t ay_offset = 0;
int16_t az_offset = 0;

// Dead-zone (degrees) — prevents jitter at rest
const int DEAD_ZONE = 12;

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

void loop() {
  int16_t ax, ay, az, gx, gy, gz;
  mpu.getMotion6(&ax, &ay, &az, &gx, &gy, &gz);

  // Apply calibration
  ax -= ax_offset;
  ay -= ay_offset;

  // Raw accel ~±17000 → map to ±90 degrees
  int16_t xAngle = constrain(map(ax, -17000, 17000, -90, 90), -90, 90);
  int16_t yAngle = constrain(map(ay, -17000, 17000, -90, 90), -90, 90);


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


  bool ok = radio.write(&txData, sizeof(ControlPacket));


  Serial.print(F("xA:")); Serial.print(xAngle);
  Serial.print(F(" yA:")); Serial.print(yAngle);
  Serial.print(F(" Mode:")); Serial.print(txData.mode);
  Serial.print(F(" Thr:")); Serial.print(txData.throttle);
  Serial.print(F(" TX:")); Serial.println(ok ? F("OK") : F("FAIL"));

  delay(20);   // 50 Hz update rate
}


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
