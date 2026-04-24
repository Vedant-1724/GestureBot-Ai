# Hardware Specifications
## GC-Car — Report-Ready Notes

These specifications combine official device data with practical module-level notes for this exact project build.

---

## 1. Arduino Nano (ATmega328P)
| Item | Value |
|---|---|
| Microcontroller | ATmega328P |
| Operating voltage | `5V` |
| Input voltage | `7–12V` via `VIN`, or regulated `5V` via `5V` pin |
| Clock speed | `16 MHz` |
| Flash memory | `32 KB` total, about `2 KB` used by bootloader |
| SRAM | `2 KB` |
| EEPROM | `1 KB` |
| Digital I/O | `14` primary digital pins |
| PWM pins | `6` |
| Analog inputs | `8` |
| DC current per I/O pin | `20 mA` |
| Board size | `18 mm × 45 mm` |
| Typical use here | One Nano for transmitter, one Nano for receiver |

Why it fits this project:

- Small and easy to mount on a hand-held transmitter and a compact rover.
- Enough GPIO for nRF24L01+, MPU6050, and L298N.
- Well supported in Arduino IDE and beginner-friendly for reports and demonstrations.

---

## 2. nRF24L01+ 2.4 GHz Transceiver
| Item | Value |
|---|---|
| Frequency band | `2.4–2.525 GHz` |
| Air data rates | `250 kbps`, `1 Mbps`, `2 Mbps` |
| Interface | SPI |
| Supply voltage | `1.9–3.6V` at chip level |
| Logic level | `3.3V` |
| TX power levels | Programmable |
| Typical project setting | `250 kbps` for better range and stability |
| Role in project | Wireless command link from gesture transmitter to car |

Important practical notes:

- The bare radio is sensitive to supply noise.
- Use an adapter board with onboard regulator and decoupling capacitor.
- Keep the radio away from motor wiring and high-current traces.

---

## 3. nRF24L01+ Adapter Board
| Item | Typical value / role |
|---|---|
| Input voltage | `5V` |
| Output to radio | Regulated `3.3V` |
| Extra parts | Usually onboard capacitor + regulator |
| Why used | Makes the nRF24L01+ stable with Arduino Nano |

Practical importance:

- This adapter is not optional in a motorized rover project.
- Without it, the radio often resets or drops packets due to voltage dips.

---

## 4. MPU6050 IMU
| Item | Value |
|---|---|
| Sensor type | 6-axis IMU |
| Axes | 3-axis accelerometer + 3-axis gyroscope |
| Accelerometer ranges | `±2g`, `±4g`, `±8g`, `±16g` |
| Gyroscope ranges | `±250`, `±500`, `±1000`, `±2000 dps` |
| Interface | I2C |
| Sensor supply | `2.375–3.46V` at chip level |
| Typical breakout power | Usually accepts `3.3V` or `5V` depending on module |
| Use in project | Detects hand tilt and converts it into car motion commands |

Why it fits this project:

- Gives stable tilt information.
- Easy to read through I2C.
- Cheap and widely used for gesture-control demos.

---

## 5. L298N Dual H-Bridge Motor Driver
| Item | Value |
|---|---|
| Driver type | Dual full-bridge motor driver |
| Motor supply voltage | Up to `46V` at IC level |
| Total DC current | Up to `4A` total at IC level |
| Logic input | TTL compatible |
| Channels | 2 full bridges |
| Common use in rover | Drive left motor pair and right motor pair |
| Use in project | Controls four DC motors as left and right pairs |

Practical notes for this project:

- The popular L298N module is convenient but not very efficient.
- It causes a noticeable voltage drop and heat loss.
- It is fine for a student prototype, but a modern MOSFET driver is better for final performance.

---

## 6. 4 DC Gear Motors
| Item | Typical role |
|---|---|
| Count | 4 |
| Mounting | 2 on left side, 2 on right side |
| Wiring style | Left pair in parallel, right pair in parallel |
| Use in project | 4WD movement for dump-yard rover |

Selection guideline:

- Choose motors whose stall current does not exceed what your driver and battery can safely supply.
- For rough garbage-yard paths, metal gear motors with decent torque are better than very high-speed motors.

---

## 7. ESP32-CAM (AI Thinker type)
| Item | Typical value |
|---|---|
| Main SoC | ESP32 dual-core Xtensa |
| CPU clock | Up to `240 MHz` |
| Wireless | Wi-Fi `2.4 GHz` + Bluetooth/BLE |
| Camera | OV2640 |
| Camera max still resolution | Up to `1600 × 1200` |
| External PSRAM | Commonly `8 MB` on AI Thinker variants |
| Flash memory | Commonly `4 MB` |
| Board supply | `5V` input on module pin |
| Use in project | Sends live MJPEG video feed to laptop |

Practical notes:

- Streaming is much more stable with a dedicated `5V` buck converter.
- ESP32-CAM should not be powered from the Nano `5V` pin in the final build.
- Wi-Fi video streaming and camera capture create high current peaks.

---

## 8. Power System Recommendation

### Transmitter
Recommended:

- `5V` USB power bank or regulated `5V` battery pack to Nano `5V`
- Common ground between Nano, MPU6050 and nRF adapter

Acceptable but weaker:

- `9V` battery to `VIN`

### Receiver / Rover
Recommended:

- `7.4V` 2-cell Li-ion / LiPo battery for motors
- Separate `5V` buck converter rated around `3A`
- Buck converter powers Nano, nRF adapter and ESP32-CAM
- L298N motor supply connected directly to battery

Why this is better:

- Prevents radio resets.
- Prevents ESP32-CAM brownout during streaming.
- Reduces noise from motor current spikes.

---

## 9. Why These Parts Match the Project

This hardware split is sensible for a student rover:

- `Arduino Nano + MPU6050 + nRF24L01+` gives a low-cost gesture remote.
- `Arduino Nano + nRF24L01+ + L298N` keeps motor control simple and easy to debug.
- `ESP32-CAM` moves the heavy video pipeline off the Nano and onto Wi-Fi.
- `Laptop GPU` runs the AI model, so the car stays lightweight and cheaper than doing onboard AI.
