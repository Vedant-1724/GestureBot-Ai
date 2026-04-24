"""
================================================================
 GC-CAR — LIVE REAL-TIME INFERENCE
 File   : esp32_live_inference.py
 Folder : 06_inference/

 Connects to ESP32-CAM MJPEG stream, runs YOLO11m-cls on every
 frame, and displays classification result live on screen.

 Usage:
   python esp32_live_inference.py --ip 192.168.1.xxx

 Test with laptop webcam (no ESP32 needed):
   python esp32_live_inference.py --local

 Requirements:
   pip install ultralytics opencv-python numpy requests torch

 Controls (while window is open):
   Q  — quit
   S  — save current frame screenshot
================================================================
"""

import cv2
import numpy as np
import requests
import argparse
import time
import os
import sys
import torch
from pathlib import Path
from ultralytics import YOLO
from collections import deque, Counter

# ── Configuration ─────────────────────────────────────────────
DEFAULT_ESP32_IP  = "192.168.1.100"          # Change to your ESP32-CAM IP
DEFAULT_MODEL     = "../models/gc_car_trained_model/gc_car_yolo11m_best.pt"
STREAM_PATH       = "/stream"
CONF_THRESHOLD    = 0.65    # Min confidence to show label
SMOOTH_WINDOW     = 5       # Majority-vote over last N frames
IMG_SIZE          = 224     # Must match training imgsz
INFERENCE_SKIP    = 1       # Run AI every N frames (1 = every frame)
RECONNECT_DELAY   = 3.0
SAVE_DIR          = "../../data/captures"

# ── Display colours (BGR) ─────────────────────────────────────
COLORS = {
    "hazardous":     (0,   0,   235),   # Red
    "non_hazardous": (0,   200, 0  ),   # Green
    "unknown":       (128, 128, 128),   # Gray
}
LABELS = {
    "hazardous":     "HAZARDOUS",
    "non_hazardous": "NON-HAZARDOUS",
    "unknown":       "...",
}

# ─────────────────────────────────────────────────────────────
def parse_args():
    p = argparse.ArgumentParser(description="GC-Car Live Garbage Classifier")
    p.add_argument("--ip",    default=DEFAULT_ESP32_IP,
                   help="ESP32-CAM IP address")
    p.add_argument("--model", default=DEFAULT_MODEL,
                   help="Path to best.pt weights file")
    p.add_argument("--conf",  type=float, default=CONF_THRESHOLD,
                   help="Confidence threshold (0–1)")
    p.add_argument("--local", action="store_true",
                   help="Use laptop webcam instead of ESP32 stream")
    return p.parse_args()


# ── Classifier wrapper ────────────────────────────────────────
class GarbageClassifier:
    def __init__(self, model_path: str, device: str):
        script_dir = Path(__file__).parent
        candidates = [
            Path(model_path),
            script_dir / model_path,
            script_dir / "../models/gc_car_trained_model/gc_car_yolo11m_best.pt",
            script_dir / "../../models/gc_car_trained_model/gc_car_yolo11s_fast_best.pt",
            script_dir / "../../models/gc_car_trained_model/gc_car_yolo11m_balanced_best.pt",
            script_dir / "../../models/gc_car_trained_model/gc_car_yolo11m_max_best.pt",
            script_dir / "../../models/gc_car_yolo11m_best.pt",
        ]

        mp = None
        for candidate in candidates:
            candidate = candidate.resolve()
            if candidate.exists():
                mp = candidate
                break

        if mp is None:
            print(f"[ERROR] Model not found: {model_path}")
            print("[INFO] Checked common model locations inside models/.")
            sys.exit(1)

        print(f"[INFO] Loading model: {mp}")
        self.model   = YOLO(str(mp))
        self.device  = device
        self.classes = self.model.names   # {0:'hazardous', 1:'non_hazardous'}
        self.buffer  = deque(maxlen=SMOOTH_WINDOW)
        print(f"[INFO] Classes: {self.classes}")
        print(f"[INFO] Device : {device.upper()}")

    def predict(self, frame: np.ndarray) -> dict:
        res    = self.model(frame, imgsz=IMG_SIZE,
                            device=self.device, verbose=False)
        probs  = res[0].probs
        top1   = int(probs.top1)
        conf   = float(probs.top1conf.cpu())
        label  = self.classes[top1]

        self.buffer.append(top1)
        if len(self.buffer) >= SMOOTH_WINDOW:
            sm_id    = Counter(self.buffer).most_common(1)[0][0]
            sm_label = self.classes[sm_id]
        else:
            sm_label = label

        return {
            "label":    sm_label,
            "raw":      label,
            "conf":     conf,
            "all_probs": {self.classes[i]: float(probs.data[i].cpu())
                          for i in range(len(self.classes))},
        }


# ── MJPEG stream reader ───────────────────────────────────────
class ESP32Streamer:
    def __init__(self, ip, port=80, path="/stream"):
        self.url       = f"http://{ip}:{port}{path}"
        self.stream    = None
        self.connected = False
        self.buffer    = b""

    def connect(self) -> bool:
        print(f"[INFO] Connecting to {self.url}")
        try:
            self.stream = requests.get(self.url, stream=True, timeout=10)
            self.connected = (self.stream.status_code == 200)
            self.buffer = b""
            if self.connected:
                print("[INFO] Stream connected.")
            return self.connected
        except Exception as e:
            print(f"[ERROR] {e}")
            return False

    def read(self):
        try:
            for chunk in self.stream.iter_content(4096):
                self.buffer += chunk
                soi = self.buffer.find(b'\xff\xd8')
                eoi = self.buffer.find(b'\xff\xd9')
                if soi != -1 and eoi > soi:
                    jpg   = self.buffer[soi:eoi + 2]
                    self.buffer = self.buffer[eoi + 2:]
                    arr   = np.frombuffer(jpg, np.uint8)
                    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                    if frame is not None:
                        return True, frame
        except Exception:
            self.connected = False
        return False, None

    def release(self):
        if self.stream:
            self.stream.close()
        self.connected = False
        self.buffer = b""


# ── HUD drawing ───────────────────────────────────────────────
def draw_hud(frame, pred, fps, frame_num, inf_ms, threshold):
    h, w = frame.shape[:2]
    label = pred.get("label", "unknown")
    conf  = pred.get("conf",  0.0)
    color = COLORS.get(label, COLORS["unknown"])
    disp  = LABELS.get(label, label.upper())

    # Top bar
    cv2.rectangle(frame, (0, 0), (w, 48), (10, 10, 10), -1)
    cv2.putText(frame, f"FPS: {fps:.1f}",
                (8, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                (0, 220, 80), 1, cv2.LINE_AA)
    cv2.putText(frame, f"Inf: {inf_ms:.0f}ms",
                (100, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                (160, 160, 160), 1, cv2.LINE_AA)
    cv2.putText(frame, f"Frame: {frame_num}",
                (8, 43), cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                (100, 100, 100), 1, cv2.LINE_AA)
    cv2.putText(frame, "GC-Car Garbage Classifier",
                (w - 240, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                (200, 200, 200), 1, cv2.LINE_AA)

    if conf >= threshold and label != "unknown":
        # Bottom result panel
        cv2.rectangle(frame, (0, h - 72), (w, h), (15, 15, 15), -1)

        # Confidence bar
        bar_w = int((w - 20) * conf)
        cv2.rectangle(frame, (10, h - 20), (w - 10, h - 6), (50, 50, 50), -1)
        cv2.rectangle(frame, (10, h - 20), (10 + bar_w, h - 6), color, -1)

        # Class label text
        cv2.putText(frame, disp,
                    (12, h - 28), cv2.FONT_HERSHEY_DUPLEX, 1.1,
                    color, 2, cv2.LINE_AA)
        cv2.putText(frame, f"{conf * 100:.1f}%",
                    (w - 90, h - 28), cv2.FONT_HERSHEY_SIMPLEX, 0.75,
                    (220, 220, 220), 1, cv2.LINE_AA)

        # Coloured border around frame
        thick = 4 if label == "hazardous" else 2
        cv2.rectangle(frame, (3, 3), (w - 3, h - 3), color, thick)

    # Per-class probability bars (right side)
    all_p = pred.get("all_probs", {})
    y_off = 58
    for cls, prob in all_p.items():
        bar_len = int(150 * prob)
        c       = COLORS.get(cls, COLORS["unknown"])
        cv2.rectangle(frame, (w - 165, y_off),
                      (w - 15, y_off + 12), (40, 40, 40), -1)
        cv2.rectangle(frame, (w - 165, y_off),
                      (w - 165 + bar_len, y_off + 12), c, -1)
        cv2.putText(frame, f"{cls[:9]}: {prob:.2f}",
                    (w - 165, y_off - 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.36,
                    (200, 200, 200), 1, cv2.LINE_AA)
        y_off += 30

    return frame


# ─────────────────────────────────────────────────────────────
def main():
    args = parse_args()
    os.makedirs(SAVE_DIR, exist_ok=True)

    # Device
    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cpu":
        print("[WARN] CUDA not available — using CPU (slower)")

    # Load classifier
    clf = GarbageClassifier(args.model, device)

    # Open video source
    if args.local:
        print("[INFO] Using laptop webcam (--local mode)")
        cap       = cv2.VideoCapture(0)
        use_esp32 = False
    else:
        streamer  = ESP32Streamer(args.ip, path=STREAM_PATH)
        while not streamer.connect():
            print(f"[RETRY] in {RECONNECT_DELAY}s ...")
            time.sleep(RECONNECT_DELAY)
        use_esp32 = True

    fps_t  = time.time()
    fps_n  = 0
    fps    = 0.0
    fnum   = 0
    inf_ms = 0.0
    pred   = {"label": "unknown", "conf": 0.0, "all_probs": {}}
    save_i = 0

    print("\n[INFO] Live inference started!")
    print("[INFO] Q=quit   S=save screenshot\n")

    while True:
        if use_esp32:
            ret, frame = streamer.read()
        else:
            ret, frame = cap.read()

        if not ret or frame is None:
            if use_esp32:
                print("[WARN] Frame lost — reconnecting...")
                streamer.release()
                time.sleep(RECONNECT_DELAY)
                streamer.connect()
            continue

        fnum  += 1
        fps_n += 1
        dt     = time.time() - fps_t
        if dt >= 1.0:
            fps   = fps_n / dt
            fps_n = 0
            fps_t = time.time()

        # Run AI inference
        if fnum % INFERENCE_SKIP == 0:
            t0     = time.time()
            pred   = clf.predict(frame)
            inf_ms = (time.time() - t0) * 1000

        # Draw and show
        display = draw_hud(frame.copy(), pred, fps, fnum, inf_ms, args.conf)
        cv2.imshow("GC-Car | Garbage Classifier  (Q=quit  S=save)", display)

        # Console log every 30 frames
        if fnum % 30 == 0 and pred["conf"] > 0:
            print(f"[{fnum:6d}] FPS:{fps:5.1f} | "
                  f"{pred['label']:15s} | "
                  f"Conf:{pred['conf']:.3f} | "
                  f"Inf:{inf_ms:.1f}ms")

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            print("[INFO] Quit.")
            break
        elif key == ord('s'):
            fname = os.path.join(SAVE_DIR, f"capture_{save_i:05d}.jpg")
            cv2.imwrite(fname, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
            print(f"[SAVED] {fname}")
            save_i += 1

    if use_esp32:
        streamer.release()
    else:
        cap.release()
    cv2.destroyAllWindows()
    print(f"[DONE] Processed {fnum} frames total.")


if __name__ == "__main__":
    main()
