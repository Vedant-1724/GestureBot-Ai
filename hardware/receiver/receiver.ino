/*
 * GC-Car Receiver — Arduino Nano + nRF24L01+ + L298N
 * Receives gesture packets and drives 4 DC motors.
 * Pipe: "GCCAR", Channel 108, 250kbps
 */

#include <SPI.h>
#include <RF24.h>


#define NRF_CE_PIN   9
#define NRF_CSN_PIN  10


#define ENA   3    // PWM speed
#define IN1   2    // Forward
#define IN2   4    // Reverse


#define ENB   5    // PWM speed
#define IN3   7    // Forward
#define IN4   8    // Reverse


const unsigned long SIGNAL_TIMEOUT_MS = 500;  // Stop if no packet for 500 ms
unsigned long lastSignalTime = 0;


RF24 radio(NRF_CE_PIN, NRF_CSN_PIN);


const byte PIPE_ADDRESS[6] = "GCCAR";


struct ControlPacket {
  int16_t xAngle;
  int16_t yAngle;
  uint8_t mode;
  uint8_t throttle;
  uint8_t steering;
};

ControlPacket rxData;

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

void loop() {
  if (millis() - lastSignalTime > SIGNAL_TIMEOUT_MS) {
    stopAllMotors();
  }


  if (radio.available()) {
    radio.read(&rxData, sizeof(ControlPacket));
    lastSignalTime = millis();
    executeMovement(rxData.mode, rxData.throttle, rxData.steering);

    Serial.print(F("Mode:")); Serial.print(rxData.mode);
    Serial.print(F(" Thr:")); Serial.print(rxData.throttle);
    Serial.print(F(" Str:")); Serial.println(rxData.steering);
  }
}


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


void moveForward(uint8_t spd, uint8_t steer) {
  int lSpd = spd, rSpd = spd;
  if      (steer > 147) rSpd = map(steer, 147, 255, spd, spd / 3);
  else if (steer < 107) lSpd = map(steer, 107,   0, spd, spd / 3);
  lSpd = constrain(lSpd, 0, 255);
  rSpd = constrain(rSpd, 0, 255);

  digitalWrite(IN1, HIGH); digitalWrite(IN2, LOW);  analogWrite(ENA, lSpd);
  digitalWrite(IN3, HIGH); digitalWrite(IN4, LOW);  analogWrite(ENB, rSpd);
}


void moveBackward(uint8_t spd, uint8_t steer) {
  int lSpd = spd, rSpd = spd;
  if      (steer > 147) rSpd = map(steer, 147, 255, spd, spd / 3);
  else if (steer < 107) lSpd = map(steer, 107,   0, spd, spd / 3);
  lSpd = constrain(lSpd, 0, 255);
  rSpd = constrain(rSpd, 0, 255);

  digitalWrite(IN1, LOW); digitalWrite(IN2, HIGH);  analogWrite(ENA, lSpd);
  digitalWrite(IN3, LOW); digitalWrite(IN4, HIGH);  analogWrite(ENB, rSpd);
}


void pivotLeft(uint8_t spd) {
  digitalWrite(IN1, LOW);  digitalWrite(IN2, HIGH); analogWrite(ENA, spd);
  digitalWrite(IN3, HIGH); digitalWrite(IN4, LOW);  analogWrite(ENB, spd);
}


void pivotRight(uint8_t spd) {
  digitalWrite(IN1, HIGH); digitalWrite(IN2, LOW);  analogWrite(ENA, spd);
  digitalWrite(IN3, LOW);  digitalWrite(IN4, HIGH); analogWrite(ENB, spd);
}


void stopAllMotors() {
  digitalWrite(IN1, LOW); digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW); digitalWrite(IN4, LOW);
  analogWrite(ENA, 0);    analogWrite(ENB, 0);
}
