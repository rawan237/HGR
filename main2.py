import cv2
import sys
import time
import serial
import numpy as np
from collections import deque, Counter
from ultralytics import YOLO


# ─────────────────────────────────────────
#  YAPILANDIRMA
# ─────────────────────────────────────────
MODEL_PATH    = "best(2).pt"
CONF_THRESH   = 0.60
IMG_SIZE      = 320
SMOOTH_FRAMES = 7
CAMERA_INDEX  = 0
SERIAL_PORT   = "COM11"     
BAUD_RATE     = 9600
COOLDOWN      = 1.5

SELECTED_GESTURES = {
    1:  "Begenme  (Dislike)",
    3:  "Avuc ici (Palm)",
    4:  "Ters avuc (Palm Ters)",
    11: "Yumruk   (Fist)",
    13: "Begeni   (Like)",
}

GESTURE_COMMANDS = {
    1:  "ALARM",
    3:  "WAIT",
    4:  "CANCEL",
    11: "LOCK",
    13: "UNLOCK",
}

GESTURE_COLORS = {
    1:  (0,   80,  220),
    3:  (0,  200,  100),
    4:  (0,  170,  230),
    11: (50,  50,  200),
    13: (0,  220,   50),
}
DEFAULT_COLOR = (180, 180, 180)


# ─────────────────────────────────────────
#  ARDUINO
# ─────────────────────────────────────────
class ArduinoController:
    def __init__(self, port: str, baud: int):
        self.ser       = None
        self.last_cmd  = ""
        self.last_time = 0.0
        try:
            self.ser = serial.Serial(port, baud, timeout=1)
            time.sleep(2)
            print(f"✅ Arduino connected on {port}")
        except Exception as exc:
            print(f"⚠️  Arduino bağlanamadı: {exc}")
            print("    Simulation modu aktif.")

    def send(self, class_id: int) -> None:
        cmd = GESTURE_COMMANDS.get(class_id)
        if not cmd:
            return
        now = time.time()
        if cmd == self.last_cmd and now - self.last_time < COOLDOWN:
            return
        self.last_cmd  = cmd
        self.last_time = now
        if self.ser and self.ser.is_open:
            self.ser.write((cmd + "\n").encode())
            print(f"📤 Sent: {cmd}")
        else:
            print(f"📤 [SIM] Would send: {cmd}")

    def close(self) -> None:
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("✅ Arduino bağlantısı kapatıldı.")


# ─────────────────────────────────────────
#  SMOOTHING
# ─────────────────────────────────────────
class GestureSmoothing:
    def __init__(self, window: int = SMOOTH_FRAMES):
        self._buf: deque = deque(maxlen=window)

    def update(self, class_id: int | None) -> int | None:
        self._buf.append(class_id)
        filled = [x for x in self._buf if x is not None]
        if not filled:
            return None
        most_common, count = Counter(filled).most_common(1)[0]
        return most_common if count >= len(self._buf) // 2 + 1 else None


# ─────────────────────────────────────────
#  DRAWING
# ─────────────────────────────────────────
def draw_info_bar(frame: np.ndarray, fps: float,
                  gesture: str | None, cmd: str | None) -> None:
    h, w = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 50), (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
    cv2.putText(frame, f"FPS: {fps:.1f}",
                (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 230, 0), 2)
    cv2.putText(frame,
                f"Jest: {gesture}" if gesture else "Jest: No gesture detected",
                (w // 4, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
    cv2.putText(frame, f"CMD: {cmd}" if cmd else "CMD: —",
                (w // 4, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 200, 255), 2)


def draw_detection(frame: np.ndarray, x1: int, y1: int,
                   x2: int, y2: int, label: str,
                   conf: float, color: tuple) -> None:
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
    text = f"{label}  {conf*100:.0f}%"
    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
    ty = max(y1 - 8, th + 4)
    cv2.rectangle(frame, (x1, ty - th - 4), (x1 + tw + 6, ty + 2), color, -1)
    cv2.putText(frame, text, (x1 + 3, ty - 2),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)


# ─────────────────────────────────────────
#  ANA FONKSİYON
# ─────────────────────────────────────────
def run_gesture_system() -> None:

    print("⏳ Model yükleniyor...")
    try:
        model = YOLO(MODEL_PATH)
        print("✅ Model başarıyla yüklendi.")
    except Exception as exc:
        print(f"❌ Model yüklenemedi: {exc}")
        sys.exit(1)

    arduino = ArduinoController(SERIAL_PORT, BAUD_RATE)

    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(CAMERA_INDEX + 1)
    if not cap.isOpened():
        print("❌ Hiçbir kamera bulunamadı.")
        arduino.close()
        sys.exit(1)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_BUFFERSIZE,   1)

    smoother        = GestureSmoothing(SMOOTH_FRAMES)
    fps_timer       = time.time()
    frame_count     = 0
    fps             = 0.0
    last_stable_cmd = None

    print("🚀 Sistem başlatıldı. Çıkmak için 'Q' tuşuna basın.\n")

    try:
        while True:
            success, frame = cap.read()
            if not success:
                time.sleep(0.05)
                continue

            frame = cv2.flip(frame, 1)

            frame_count += 1
            elapsed = time.time() - fps_timer
            if elapsed >= 0.5:
                fps         = frame_count / elapsed
                frame_count = 0
                fps_timer   = time.time()

            results = model.predict(
                source  = frame,
                conf    = CONF_THRESH,
                imgsz   = IMG_SIZE,
                verbose = False,
                stream  = False,
            )

            best_class: int | None = None
            best_conf  = 0.0

            for r in results:
                for box in r.boxes:
                    class_id = int(box.cls[0])
                    if class_id not in SELECTED_GESTURES:
                        continue
                    conf  = float(box.conf[0])
                    label = SELECTED_GESTURES[class_id]
                    color = GESTURE_COLORS.get(class_id, DEFAULT_COLOR)
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    draw_detection(frame, x1, y1, x2, y2, label, conf, color)
                    if conf > best_conf:
                        best_conf  = conf
                        best_class = class_id

            stable_class    = smoother.update(best_class)
            stable_label    = SELECTED_GESTURES.get(stable_class) if stable_class is not None else None
            last_stable_cmd = GESTURE_COMMANDS.get(stable_class)  if stable_class is not None else None

            if stable_class is not None:
                arduino.send(stable_class)

            draw_info_bar(frame, fps, stable_label, last_stable_cmd)
            cv2.imshow("El Hareketi Tanıma Sistemi", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:
                break

    except KeyboardInterrupt:
        print("\n🛑 Program kullanıcı tarafından durduruldu.")
    except Exception as exc:
        print(f"⚠️  Beklenmedik hata: {exc}")
    finally:
        cap.release()
        arduino.close()
        cv2.destroyAllWindows()
        print("✅ Sistem kapatıldı.")


if __name__ == "__main__":
    run_gesture_system()