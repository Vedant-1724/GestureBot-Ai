# Pin Connections Reference
## GC-Car — Gesture Controlled Garbage Classifier Car

This file lists every practical connection used in the project, including
power, signal, optional pins, and unused pins that should remain open.

---

## 1. Transmitter Side

### 1.1 Arduino Nano ↔ MPU6050 module
| MPU6050 pin | Connect to | Status | Notes |
|---|---|---|---|
| VCC | Nano `5V` | Used | Most breakout boards include regulation and level support. If your board is bare-sensor only, use `3.3V` instead. |
| GND | Nano `GND` | Used | Common ground |
| SDA | Nano `A4` | Used | I2C data |
| SCL | Nano `A5` | Used | I2C clock |
| INT | Nano `D2` | Optional | Not used by the current sketch |
| AD0 / XDA / XCL | NC | Not used | Leave unconnected unless you expand the design |

### 1.2 Arduino Nano ↔ nRF24L01+ via adapter board
| nRF adapter pin | nRF24L01+ pin | Connect to Nano | Status | Notes |
|---|---|---|---|---|
| VCC | VCC | `5V` | Used | Adapter regulates to clean `3.3V` for radio |
| GND | GND | `GND` | Used | Common ground |
| CE | CE | `D9` | Used | Chip enable |
| CSN | CSN | `D10` | Used | SPI chip select |
| SCK | SCK | `D13` | Used | SPI clock |
| MOSI | MOSI | `D11` | Used | SPI master-out |
| MISO | MISO | `D12` | Used | SPI master-in |
| IRQ | IRQ | NC | Not used | Leave open in this project |

### 1.3 Transmitter power
| Source | Destination | Recommended? | Notes |
|---|---|---|---|
| `5V` regulated source or USB power bank | Nano `5V` | Yes | Best stability for Nano + MPU6050 + nRF adapter |
| `7–12V` battery | Nano `VIN` | Acceptable | Works, but 9V rectangular batteries are usually weak for long use |
| Battery/Regulator GND | Nano `GND` | Required | Ground return |

### 1.4 Nano pins still free on transmitter
`D3, D4, D5, D6, D7, D8, A0, A1, A2, A3, A6, A7` remain free in the current build.

---

## 2. Receiver Side (Car)

### 2.1 Arduino Nano ↔ nRF24L01+ via adapter board
| nRF adapter pin | Connect to Nano | Status |
|---|---|---|
| VCC | `5V` | Used |
| GND | `GND` | Used |
| CE | `D9` | Used |
| CSN | `D10` | Used |
| SCK | `D13` | Used |
| MOSI | `D11` | Used |
| MISO | `D12` | Used |
| IRQ | NC | Not used |

### 2.2 Arduino Nano ↔ L298N driver
| L298N pin | Connect to Nano | Status | Function |
|---|---|---|---|
| ENA | `D3` (PWM) | Used | Left-side speed control |
| IN1 | `D2` | Used | Left forward |
| IN2 | `D4` | Used | Left reverse |
| IN3 | `D7` | Used | Right forward |
| IN4 | `D8` | Used | Right reverse |
| ENB | `D5` (PWM) | Used | Right-side speed control |
| GND | `GND` | Used | Common ground |
| `+5V` logic | `5V` from buck converter | Recommended | Stable logic supply |
| `12V` / motor VIN | Battery `+` | Used | Motor supply input |

### 2.3 L298N ↔ 4 DC motors
| L298N output | Connect to motors |
|---|---|
| `OUT1` | Left front motor `+` and left rear motor `+` in parallel |
| `OUT2` | Left front motor `-` and left rear motor `-` in parallel |
| `OUT3` | Right front motor `+` and right rear motor `+` in parallel |
| `OUT4` | Right front motor `-` and right rear motor `-` in parallel |

If wheel direction is reversed during testing, swap that motor pair's two wires.

### 2.4 Receiver power distribution
| Source | Destination | Notes |
|---|---|---|
| `7.4V` Li-ion / LiPo battery `+` | L298N motor VIN / `12V` terminal | Motor power |
| `7.4V` battery `-` | L298N `GND` | Motor ground |
| `7.4V` battery → `5V` buck converter | Nano `5V`, nRF adapter `VCC`, ESP32-CAM `5V` | Recommended final design |
| Buck converter `GND` | Nano `GND`, ESP32-CAM `GND`, L298N `GND` | All grounds must be common |

### 2.5 L298N module jumpers and extra pins
| Pin / jumper | Status | Notes |
|---|---|---|
| ENA jumper | Remove | Needed because Nano drives PWM on ENA |
| ENB jumper | Remove | Needed because Nano drives PWM on ENB |
| `5V-EN` jumper | Depends on module | Keep only if you intentionally use onboard regulator; for final build, an external buck converter is safer |
| Sense pins | Not exposed / not used | Leave as module default |

### 2.6 Nano pins still free on receiver
`D6, A0, A1, A2, A3, A4, A5, A6, A7` remain free in the current car controller.

---

## 3. ESP32-CAM

### 3.1 ESP32-CAM flashing connections using FTDI / USB-TTL
| ESP32-CAM pin | Connect to FTDI | Status | Notes |
|---|---|---|---|
| `5V` | `5V` | Used | Power during upload |
| `GND` | `GND` | Used | Common ground |
| `U0R` / `GPIO3` | FTDI `TX` | Used | Serial RX on ESP32-CAM |
| `U0T` / `GPIO1` | FTDI `RX` | Used | Serial TX on ESP32-CAM |
| `GPIO0` | `GND` | Used only for flashing | Hold low while resetting to enter bootloader |
| `RST` | Reset button / optional momentary to GND | Optional | Press after wiring `GPIO0` low |

After upload, remove the `GPIO0` to `GND` short and press reset again.

### 3.2 ESP32-CAM operating power
| ESP32-CAM pin | Connect to | Notes |
|---|---|---|
| `5V` | `5V` buck converter output | Use a regulator rated around `2A` peak for stability |
| `GND` | Common ground | Required |

### 3.3 Internal AI Thinker ESP32-CAM camera pin map
These are already wired on the board/module and are listed for completeness:

| Camera signal | ESP32 GPIO |
|---|---|
| PWDN | `GPIO32` |
| RESET | `-1` (not connected) |
| XCLK | `GPIO0` |
| SIOD | `GPIO26` |
| SIOC | `GPIO27` |
| Y9 | `GPIO35` |
| Y8 | `GPIO34` |
| Y7 | `GPIO39` |
| Y6 | `GPIO36` |
| Y5 | `GPIO21` |
| Y4 | `GPIO19` |
| Y3 | `GPIO18` |
| Y2 | `GPIO5` |
| VSYNC | `GPIO25` |
| HREF | `GPIO23` |
| PCLK | `GPIO22` |

### 3.4 ESP32-CAM pins to avoid in this project
| Pin | Why |
|---|---|
| `GPIO0` | Boot-mode pin; avoid external loads during normal use |
| `GPIO1`, `GPIO3` | Used by serial programming |
| `GPIO4` | Often shared with flash LED / SD features on many boards |
| `GPIO16` | Often tied to PSRAM on ESP32-CAM variants |

---

## 4. Grounding Rule

The following must share one common ground:

- Receiver Nano
- nRF receiver adapter
- L298N
- Battery negative
- ESP32-CAM
- 5V buck converter ground

Without common ground, motor control and camera streaming become unreliable.
