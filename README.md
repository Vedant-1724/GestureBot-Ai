# GC-Car: Gesture Controlled Garbage Classifier Car

GC-Car is a prototype rover that combines gesture-based wireless driving with live AI waste classification. It uses an Arduino Nano hand transmitter with MPU6050 tilt sensing, nRF24L01+ radio control, an ESP32-CAM video stream, and a YOLO11 classifier running on a laptop to label waste as `hazardous` or `non_hazardous`.

## Repository Contents

| Folder | Purpose |
|---|---|
| `01_hardware/` | Arduino Nano transmitter/receiver sketches, ESP32-CAM firmware, and hardware docs |
| `02_esp32_opencv/` | ESP32-CAM stream testing utility |
| `03_dataset/` | Raw and prepared garbage image datasets plus preparation script |
| `04_training/` | Google Colab YOLO training workflow |
| `05_model/` | Trained model weights and result plots |
| `06_inference/` | Live ESP32/webcam inference and validation scripts |
| `07_docs/` | Full project documentation and master guide |

For the complete setup, workflow, wiring, training, validation, and demo instructions, see [`07_docs/README.md`](07_docs/README.md).
