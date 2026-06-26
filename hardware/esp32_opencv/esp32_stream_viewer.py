"""OpenCV viewer for ESP32-CAM MJPEG stream.
Press Q to quit, S to save a frame."""

import cv2
import numpy as np
import requests
import argparse
import time
import os
import sys


DEFAULT_ESP32_IP   = "10.167.179.197"   # Change to your ESP32-CAM IP
STREAM_PORT        = 81
STREAM_PATH        = "/stream"
DISPLAY_SCALE      = 1.0               # 1.0 = native, 1.5 = larger
RECONNECT_DELAY    = 3.0               # Seconds before reconnect attempt
SAVE_DIR           = "../06_inference/../../data/captures"


def parse_args():
    p = argparse.ArgumentParser(description="GC-Car ESP32-CAM Stream Viewer")
    p.add_argument("--ip",    type=str, default=DEFAULT_ESP32_IP,
                   help="ESP32-CAM IP address (default: %(default)s)")
    p.add_argument("--port",  type=int, default=STREAM_PORT,
                   help="HTTP port (default: %(default)s)")
    p.add_argument("--scale", type=float, default=DISPLAY_SCALE,
                   help="Display scale factor (default: %(default)s)")
    return p.parse_args()



class ESP32StreamReader:
    def __init__(self, ip, port=80, path="/stream"):
        self.url       = f"http://{ip}:{port}{path}"
        self.stream    = None
        self.connected = False
        self.buffer    = b""
        self.fps       = 0.0
        self.frame_count = 0
        self._fps_t    = time.time()
        self._fps_n    = 0

    def connect(self) -> bool:
        print(f"[INFO] Connecting to {self.url} ...")
        try:
            self.stream = requests.get(self.url, stream=True, timeout=10)
            self.connected = (self.stream.status_code == 200)
            self.buffer = b""
            if self.connected:
                print("[INFO] Connected!")
            else:
                print(f"[ERROR] HTTP status {self.stream.status_code}")
            return self.connected
        except Exception as e:
            print(f"[ERROR] {e}")
            return False

    def read(self):
        """Return (True, BGR frame) or (False, None)."""
        try:
            for chunk in self.stream.iter_content(4096):
                self.buffer += chunk
                soi = self.buffer.find(b'\xff\xd8')
                eoi = self.buffer.find(b'\xff\xd9')
                if soi != -1 and eoi > soi:
                    jpg   = self.buffer[soi:eoi + 2]
                    self.buffer = self.buffer[eoi + 2:]
                    arr   = np.frombuffer(jpg, dtype=np.uint8)
                    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                    if frame is not None:
                        self.frame_count += 1
                        self._update_fps()
                        return True, frame
        except Exception as e:
            print(f"[WARN] Stream error: {e}")
            self.connected = False
        return False, None

    def _update_fps(self):
        self._fps_n += 1
        dt = time.time() - self._fps_t
        if dt >= 1.0:
            self.fps   = self._fps_n / dt
            self._fps_n = 0
            self._fps_t = time.time()

    def release(self):
        if self.stream:
            self.stream.close()
        self.connected = False
        self.buffer = b""
        print("[INFO] Stream released.")


def draw_overlay(frame, fps, frame_count):
    """Draw FPS and frame count on frame."""
    h, w = frame.shape[:2]
    cv2.rectangle(frame, (0, 0), (w, 40), (0, 0, 0), -1)
    cv2.putText(frame, f"FPS: {fps:.1f}",
                (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 100), 1, cv2.LINE_AA)
    cv2.putText(frame, f"Frame: {frame_count}",
                (120, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (180, 180, 180), 1, cv2.LINE_AA)
    cv2.putText(frame, "GC-Car | ESP32-CAM Live",
                (w - 230, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1, cv2.LINE_AA)
    return frame


def main():
    args = parse_args()
    os.makedirs(SAVE_DIR, exist_ok=True)
    save_idx = 0

    cam = ESP32StreamReader(ip=args.ip, port=args.port, path=STREAM_PATH)

    while not cam.connected:
        if not cam.connect():
            print(f"[RETRY] Waiting {RECONNECT_DELAY}s...")
            time.sleep(RECONNECT_DELAY)

    print("[INFO] Stream open. Press Q=quit  S=save frame")

    while True:
        ret, frame = cam.read()

        if not ret or frame is None:
            print("[WARN] Lost frame — reconnecting...")
            cam.release()
            time.sleep(RECONNECT_DELAY)
            cam.connect()
            continue

        display = frame.copy()

        # Scale for display
        if args.scale != 1.0:
            w = int(display.shape[1] * args.scale)
            h = int(display.shape[0] * args.scale)
            display = cv2.resize(display, (w, h))

        draw_overlay(display, cam.fps, cam.frame_count)
        cv2.imshow("GC-Car | ESP32-CAM  (Q=quit  S=save)", display)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            print("[INFO] Quit by user.")
            break
        elif key == ord('s'):
            fname = os.path.join(SAVE_DIR, f"frame_{save_idx:05d}.jpg")
            cv2.imwrite(fname, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
            print(f"[SAVED] {fname}")
            save_idx += 1

    cam.release()
    cv2.destroyAllWindows()
    print(f"[DONE] Total frames seen: {cam.frame_count}")


if __name__ == "__main__":
    main()
